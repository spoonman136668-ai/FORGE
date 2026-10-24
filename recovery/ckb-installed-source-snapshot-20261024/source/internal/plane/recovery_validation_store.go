package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
	"path/filepath"
	"strconv"
)

const recoveryValidationSchema = "ckb-plane.recovery-validation.v1"
const recoveryValidationBudgetHardMax = 3

var errRecoveryValidationDisabled = errors.New("RECOVERY_VALIDATION_DISABLED")

type RecoveryValidationConfig struct {
	Enabled               bool
	MaxValidationAttempts int
}

type RecoveryValidationResult struct {
	Schema                   string  `json:"schema"`
	RecoveryID               string  `json:"recovery_id"`
	PlanID                   string  `json:"plan_id"`
	RepairAttempt            int     `json:"repair_attempt"`
	ValidationAttempt        int     `json:"validation_attempt"`
	Status                   string  `json:"status"`
	FirstFailedCheck         string  `json:"first_failed_check,omitempty"`
	Evidence                 string  `json:"evidence"`
	WorkspaceRoot            string  `json:"workspace_root"`
	BaselineDir              string  `json:"baseline_dir"`
	CandidateDir             string  `json:"candidate_dir"`
	CandidateManifestSHA256  string  `json:"candidate_manifest_sha256"`
	EvidenceManifestSHA256   string  `json:"evidence_manifest_sha256,omitempty"`
	ProductionAccepted       bool    `json:"production_accepted"`
	ResumeAuthorized         bool    `json:"resume_authorized"`
	Created                  string  `json:"created_at"`
	Updated                  string  `json:"updated_at"`
}

func validateRecoveryValidationConfig(cfg RecoveryValidationConfig) error {
	if !cfg.Enabled {
		return errRecoveryValidationDisabled
	}
	if cfg.MaxValidationAttempts < 0 || cfg.MaxValidationAttempts > recoveryValidationBudgetHardMax {
		return errors.New("RECOVERY_VALIDATION_BUDGET_INVALID")
	}
	return nil
}

func recoveryValidationBudget(cfg RecoveryValidationConfig) int {
	if cfg.MaxValidationAttempts == 0 {
		return 1
	}
	return cfg.MaxValidationAttempts
}

func initBlockerRecoveryValidationStore(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS blocker_recovery_validations(
	recovery_id TEXT NOT NULL,
	repair_attempt INTEGER NOT NULL,
	validation_attempt INTEGER NOT NULL,
	status TEXT NOT NULL,
	raw BLOB NOT NULL,
	created TEXT NOT NULL,
	updated TEXT NOT NULL,
	PRIMARY KEY(recovery_id,repair_attempt,validation_attempt)
);
`)
	return err
}

// claimRecoveryValidation preserves Stage-6 replay semantics: the first terminal
// validation is returned idempotently and never spends another validation attempt.
func claimRecoveryValidation(db *sql.DB, in RecoveryValidationResult) (RecoveryValidationResult, error) {
	return claimRecoveryValidationMode(db, in, 1, false)
}

// claimRecoveryValidationMode is the only path that may allocate another
// revalidation attempt. allowNext must be an explicit controller decision.
func claimRecoveryValidationMode(db *sql.DB, in RecoveryValidationResult, max int, allowNext bool) (RecoveryValidationResult, error) {
	if !hexDigest(in.RecoveryID, 64) || !hexDigest(in.PlanID, 64) || in.RepairAttempt < 1 ||
		!hexDigest(in.CandidateManifestSHA256, 64) || in.WorkspaceRoot == "" || in.Evidence == "" ||
		max < 1 || max > recoveryValidationBudgetHardMax {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_CLAIM_INVALID")
	}
	if err := initBlockerRecoveryValidationStore(db); err != nil {
		return RecoveryValidationResult{}, err
	}

	tx, err := db.Begin()
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	defer tx.Rollback()

	var running int
	if err = tx.QueryRow(
		"SELECT count(*) FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=? AND status='RUNNING'",
		in.RecoveryID, in.RepairAttempt,
	).Scan(&running); err != nil {
		return RecoveryValidationResult{}, err
	}
	if running != 0 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_ALREADY_OWNED")
	}

	var used int
	if err = tx.QueryRow(
		"SELECT count(*) FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=?",
		in.RecoveryID, in.RepairAttempt,
	).Scan(&used); err != nil {
		return RecoveryValidationResult{}, err
	}

	if used > 0 {
		var raw []byte
		var status string
		var attempt int
		if err = tx.QueryRow(
			"SELECT raw,status,validation_attempt FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=? ORDER BY validation_attempt DESC LIMIT 1",
			in.RecoveryID, in.RepairAttempt,
		).Scan(&raw, &status, &attempt); err != nil {
			return RecoveryValidationResult{}, err
		}
		var existing RecoveryValidationResult
		if json.Unmarshal(raw, &existing) != nil ||
			existing.Schema != recoveryValidationSchema ||
			existing.RecoveryID != in.RecoveryID ||
			existing.PlanID != in.PlanID ||
			existing.RepairAttempt != in.RepairAttempt ||
			existing.ValidationAttempt != attempt ||
			existing.CandidateManifestSHA256 != in.CandidateManifestSHA256 ||
			existing.Status != status ||
			existing.ProductionAccepted || existing.ResumeAuthorized {
			return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_STATE_CORRUPT")
		}
		if !allowNext {
			return existing, nil
		}
		if existing.Status == "VALIDATED" {
			return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_ALREADY_PASSED")
		}
	}
	if used >= max {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_BUDGET_EXHAUSTED")
	}

	attempt := used + 1
	in.Schema = recoveryValidationSchema
	in.ValidationAttempt = attempt
	in.Status = "RUNNING"
	in.FirstFailedCheck = ""
	in.ProductionAccepted = false
	in.ResumeAuthorized = false
	in.EvidenceManifestSHA256 = ""
	in.WorkspaceRoot = filepath.Join(in.WorkspaceRoot, strconv.Itoa(attempt))
	in.Evidence = filepath.Join(in.Evidence, strconv.Itoa(attempt))
	in.BaselineDir = filepath.Join(in.WorkspaceRoot, "baseline")
	in.CandidateDir = filepath.Join(in.WorkspaceRoot, "candidate")
	in.Created = now()
	in.Updated = in.Created
	raw, err := json.Marshal(in)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if _, err = tx.Exec(
		"INSERT INTO blocker_recovery_validations(recovery_id,repair_attempt,validation_attempt,status,raw,created,updated) VALUES(?,?,?,?,?,?,?)",
		in.RecoveryID, in.RepairAttempt, in.ValidationAttempt, in.Status, raw, in.Created, in.Updated,
	); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err = tx.Commit(); err != nil {
		return RecoveryValidationResult{}, err
	}
	return in, nil
}

func finishRecoveryValidation(db *sql.DB, out RecoveryValidationResult) (RecoveryValidationResult, error) {
	switch out.Status {
	case "VALIDATED", "REJECTED", "EVIDENCE_FAILED":
	default:
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_STATUS_INVALID")
	}
	if out.ValidationAttempt < 1 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_ATTEMPT_INVALID")
	}
	if out.ProductionAccepted || out.ResumeAuthorized {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_AUTHORITY_INVALID")
	}
	out.Updated = now()
	raw, err := json.Marshal(out)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	res, err := db.Exec(
		"UPDATE blocker_recovery_validations SET status=?,raw=?,updated=? WHERE recovery_id=? AND repair_attempt=? AND validation_attempt=? AND status='RUNNING'",
		out.Status, raw, out.Updated, out.RecoveryID, out.RepairAttempt, out.ValidationAttempt,
	)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if n != 1 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_OWNERSHIP_LOST")
	}
	return out, nil
}

func loadRecoveryValidation(db *sql.DB, recoveryID string, repairAttempt, validationAttempt int) (RecoveryValidationResult, error) {
	var out RecoveryValidationResult
	var raw []byte
	var status string
	if !hexDigest(recoveryID, 64) || repairAttempt < 1 || validationAttempt < 1 {
		return out, errors.New("RECOVERY_VALIDATION_ID_INVALID")
	}
	if err := db.QueryRow(
		"SELECT raw,status FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=? AND validation_attempt=?",
		recoveryID, repairAttempt, validationAttempt,
	).Scan(&raw, &status); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return RecoveryValidationResult{}, err
	}
	if out.Schema != recoveryValidationSchema || out.RecoveryID != recoveryID ||
		out.RepairAttempt != repairAttempt || out.ValidationAttempt != validationAttempt ||
		out.Status != status || out.ProductionAccepted || out.ResumeAuthorized {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_STATE_CORRUPT")
	}
	return out, nil
}
