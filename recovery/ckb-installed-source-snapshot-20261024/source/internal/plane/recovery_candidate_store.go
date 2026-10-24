package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
	"path/filepath"
	"strconv"
)

const recoveryCandidateSchema = "ckb-plane.recovery-candidate.v1"
const recoveryCandidateBudgetHardMax = 3

var errRecoveryRepairDisabled = errors.New("RECOVERY_REPAIR_DISABLED")

type RecoveryRepairConfig struct {
	Enabled           bool
	MaxRepairAttempts int
	TimeoutSeconds    int
}

type RecoveryCandidateResult struct {
	Schema              string   `json:"schema"`
	RecoveryID          string   `json:"recovery_id"`
	PlanID              string   `json:"plan_id"`
	RepairAttempt       int      `json:"repair_attempt"`
	Status              string   `json:"status"`
	WorkspaceRoot       string   `json:"workspace_root"`
	Worktree            string   `json:"worktree,omitempty"`
	Evidence            string   `json:"evidence"`
	ChangedFiles        []string `json:"changed_files,omitempty"`
	CandidateDiffSHA256    string   `json:"candidate_diff_sha256,omitempty"`
	EvidenceManifestSHA256 string   `json:"evidence_manifest_sha256,omitempty"`
	WorkerExitCode         int      `json:"worker_exit_code"`
	ProductionAccepted  bool     `json:"production_accepted"`
	ResumeAuthorized    bool     `json:"resume_authorized"`
	Created             string   `json:"created_at"`
	Updated             string   `json:"updated_at"`
}

type RecoveryCandidateEntry struct {
	Path    string `json:"path"`
	SHA256  string `json:"sha256,omitempty"`
	Deleted bool   `json:"deleted,omitempty"`
}

func validateRecoveryRepairConfig(cfg RecoveryRepairConfig) error {
	if !cfg.Enabled {
		return errRecoveryRepairDisabled
	}
	if cfg.MaxRepairAttempts < 1 || cfg.MaxRepairAttempts > recoveryCandidateBudgetHardMax {
		return errors.New("RECOVERY_REPAIR_BUDGET_INVALID")
	}
	if cfg.TimeoutSeconds < 1 || cfg.TimeoutSeconds > 1200 {
		return errors.New("RECOVERY_REPAIR_TIMEOUT_INVALID")
	}
	return nil
}

func initBlockerRecoveryCandidateStore(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS blocker_recovery_candidates(
	recovery_id TEXT NOT NULL,
	repair_attempt INTEGER NOT NULL,
	status TEXT NOT NULL,
	raw BLOB NOT NULL,
	created TEXT NOT NULL,
	updated TEXT NOT NULL,
	PRIMARY KEY(recovery_id,repair_attempt)
);
`)
	return err
}

func claimRecoveryCandidate(db *sql.DB, recoveryID, planID, workspaceBase, evidenceBase string, max int) (RecoveryCandidateResult, error) {
	var out RecoveryCandidateResult
	if !hexDigest(recoveryID, 64) || !hexDigest(planID, 64) || max < 1 || max > recoveryCandidateBudgetHardMax {
		return out, errors.New("RECOVERY_CANDIDATE_CLAIM_INVALID")
	}
	tx, err := db.Begin()
	if err != nil {
		return out, err
	}
	defer tx.Rollback()

	var running int
	if err = tx.QueryRow(
		"SELECT count(*) FROM blocker_recovery_candidates WHERE recovery_id=? AND status='RUNNING'",
		recoveryID,
	).Scan(&running); err != nil {
		return out, err
	}
	if running != 0 {
		return out, errors.New("RECOVERY_REPAIR_ALREADY_OWNED")
	}

	var used int
	if err = tx.QueryRow(
		"SELECT count(*) FROM blocker_recovery_candidates WHERE recovery_id=?",
		recoveryID,
	).Scan(&used); err != nil {
		return out, err
	}
	if used >= max {
		return out, errors.New("RECOVERY_REPAIR_BUDGET_EXHAUSTED")
	}

	attempt := used + 1
	workspace := filepath.Join(workspaceBase, strconv.Itoa(attempt))
	evidence := filepath.Join(evidenceBase, strconv.Itoa(attempt))
	at := now()
	out = RecoveryCandidateResult{
		Schema:             recoveryCandidateSchema,
		RecoveryID:         recoveryID,
		PlanID:             planID,
		RepairAttempt:      attempt,
		Status:             "RUNNING",
		WorkspaceRoot:      workspace,
		Evidence:           evidence,
		WorkerExitCode:     -1,
		ProductionAccepted: false,
		ResumeAuthorized:   false,
		Created:            at,
		Updated:            at,
	}
	raw, err := json.Marshal(out)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if _, err = tx.Exec(
		"INSERT INTO blocker_recovery_candidates(recovery_id,repair_attempt,status,raw,created,updated) VALUES(?,?,?,?,?,?)",
		out.RecoveryID, out.RepairAttempt, out.Status, raw, out.Created, out.Updated,
	); err != nil {
		return RecoveryCandidateResult{}, err
	}
	if err = tx.Commit(); err != nil {
		return RecoveryCandidateResult{}, err
	}
	return out, nil
}

func finishRecoveryCandidate(db *sql.DB, out RecoveryCandidateResult) (RecoveryCandidateResult, error) {
	if out.Status == "RUNNING" {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_TERMINAL_STATUS_REQUIRED")
	}
	switch out.Status {
	case "CANDIDATE_PREPARED", "WORKER_FAILED", "NO_DIFF", "FORBIDDEN_PATH", "REF_MUTATION", "EVIDENCE_FAILED":
	default:
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_STATUS_INVALID")
	}
	if out.ProductionAccepted || out.ResumeAuthorized {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_AUTHORITY_INVALID")
	}
	out.Updated = now()
	raw, err := json.Marshal(out)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	tx, err := db.Begin()
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	defer tx.Rollback()
	result, err := tx.Exec(
		"UPDATE blocker_recovery_candidates SET status=?,raw=?,updated=? WHERE recovery_id=? AND repair_attempt=? AND status='RUNNING'",
		out.Status, raw, out.Updated, out.RecoveryID, out.RepairAttempt,
	)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	n, err := result.RowsAffected()
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if n != 1 {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_OWNERSHIP_LOST")
	}
	if err = tx.Commit(); err != nil {
		return RecoveryCandidateResult{}, err
	}
	return out, nil
}

func loadPersistedRecoveryPlan(db *sql.DB, recoveryID string) (RecoveryPlan, error) {
	var out RecoveryPlan
	var raw []byte
	if err := db.QueryRow(
		"SELECT raw FROM blocker_recovery_plans WHERE recovery_id=?",
		recoveryID,
	).Scan(&raw); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return RecoveryPlan{}, err
	}
	if err := validateRecoveryPlan(out); err != nil {
		return RecoveryPlan{}, err
	}
	if out.RecoveryID != recoveryID {
		return RecoveryPlan{}, errors.New("RECOVERY_PLAN_IDENTITY_CONFLICT")
	}
	return out, nil
}
