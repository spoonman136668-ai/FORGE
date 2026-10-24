package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const recoverySnapshotChangedFilesLimit = 64 << 10
const recoverySnapshotValidationDiagnosticLimit = 32 << 10


type recoveryObjectiveIdentity struct {
	Schema     string `json:"schema"`
	ID         string `json:"objective_id"`
	Generation int64  `json:"authority_generation"`
	Status     string `json:"status"`
	Priority   int    `json:"priority"`
	Revision   int64  `json:"revision"`
	Next       int    `json:"next_stage"`
	Total      int    `json:"stage_count"`
	Current    string `json:"current_work_order_id,omitempty"`
}

// BuildRecoveryEvidenceSnapshot is read-only. It proves the blocked attempt's
// queue/order/contract/objective/authority/evidence identity before exposing a
// typed snapshot to the deterministic Stage-3 observer.
func (p *Engine) BuildRecoveryEvidenceSnapshot(id string) (RecoveryEvidenceSnapshot, error) {
	var out RecoveryEvidenceSnapshot
	if !safeID.MatchString(id) {
		return out, errors.New("RECOVERY_WORK_ORDER_ID_INVALID")
	}

	j, err := p.Store.Get(id)
	if err != nil {
		return out, err
	}
	if j.State != "BLOCKED" || j.Attempt < 1 {
		return out, errors.New("RECOVERY_REQUIRES_BLOCKED_ATTEMPT")
	}

	expectedEvidence := filepath.Join(p.Root, "evidence", id, strconv.Itoa(j.Attempt))
	if err = bridgeContained(p.Root, expectedEvidence); err != nil {
		return out, err
	}
	if filepath.Clean(j.Evidence) != filepath.Clean(expectedEvidence) {
		return out, errors.New("RECOVERY_EVIDENCE_PATH_CHANGED")
	}
	if err = p.VerifyEvidence(j); err != nil {
		return out, errors.New("RECOVERY_EVIDENCE_INVALID")
	}

	var queueRaw []byte
	var queueHash, queueState string
	if err = p.Store.DB.QueryRow(
		"SELECT raw,hash,state FROM queue_items WHERE id=?",
		id,
	).Scan(&queueRaw, &queueHash, &queueState); err != nil {
		return out, err
	}
	if queueState != "FAILED" && queueState != "BLOCKED" {
		return out, errors.New("RECOVERY_QUEUE_STATE_INVALID")
	}
	if digest(queueRaw) != queueHash {
		return out, errors.New("RECOVERY_QUEUE_HASH_MISMATCH")
	}

	q, err := p.parseQueue(queueRaw, id)
	if err != nil {
		return out, err
	}
	if q.Kind != "source" {
		return out, errors.New("RECOVERY_SOURCE_ORDER_REQUIRED")
	}

	var native []byte
	if err = p.Store.DB.QueryRow("SELECT yaml FROM work_orders WHERE id=?", id).Scan(&native); err != nil {
		return out, err
	}
	if q.ID != id || string(native) != q.WorkOrderYAML {
		return out, errors.New("RECOVERY_WORK_ORDER_BYTES_CHANGED")
	}
	order, err := ParseOrder(native)
	if err != nil {
		return out, err
	}
	if order.ID != id || jsonText(order) != jsonText(j.Order) {
		return out, errors.New("RECOVERY_WORK_ORDER_IDENTITY_CHANGED")
	}

	var contract string
	if err = p.Store.DB.QueryRow(
		"SELECT digest FROM authorization_contracts WHERE work_order_id=?",
		id,
	).Scan(&contract); err != nil {
		return out, err
	}
	if !hexDigest(contract, 64) {
		return out, errors.New("RECOVERY_AUTHORIZATION_CONTRACT_INVALID")
	}
	if err = p.verifyContract(order); err != nil {
		return out, errors.New("RECOVERY_AUTHORIZATION_CONTRACT_CHANGED")
	}

	var manifestSHA string
	if err = p.Store.DB.QueryRow(
		"SELECT manifest_sha256 FROM evidence_seals WHERE work_order_id=? AND attempt=?",
		id, j.Attempt,
	).Scan(&manifestSHA); err != nil {
		return out, err
	}
	if !hexDigest(manifestSHA, 64) {
		return out, errors.New("RECOVERY_EVIDENCE_ANCHOR_INVALID")
	}

	generation, err := strconv.ParseInt(p.setting("autonomy_generation"), 10, 64)
	if err != nil || generation < 1 {
		return out, errors.New("RECOVERY_AUTHORITY_GENERATION_INVALID")
	}

	out = RecoveryEvidenceSnapshot{
		WorkOrderID:              id,
		BlockedAttempt:           j.Attempt,
		QueueInputSHA256:         queueHash,
		WorkOrderSHA256:          digest(native),
		AuthorizationContractSHA: contract,
		BaselineRef:              order.Baseline.Ref,
		BaselineSHA:              order.Baseline.SHA,
		AuthorityGeneration:      generation,
		OriginalBlocker:          j.Reason,
		EvidenceManifestSHA256:   manifestSHA,
	}

	if err = p.bindRecoveryObjectiveIdentity(id, queueHash, contract, &out); err != nil {
		return RecoveryEvidenceSnapshot{}, err
	}
	if err = loadRecoveryAttemptEvidence(p.Root, expectedEvidence, &out); err != nil {
		return RecoveryEvidenceSnapshot{}, err
	}
	return canonicalRecoveryEvidence(out), nil
}

func (p *Engine) bindRecoveryObjectiveIdentity(id, queueHash, contract string, out *RecoveryEvidenceSnapshot) error {
	var tables int
	if err := p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='objective_stages'",
	).Scan(&tables); err != nil {
		return err
	}
	if tables == 0 {
		return nil
	}

	var objectiveID, stageHash, stageContract string
	var stage int
	err := p.Store.DB.QueryRow(
		"SELECT objective_id,stage,hash,contract FROM objective_stages WHERE work_id=?",
		id,
	).Scan(&objectiveID, &stage, &stageHash, &stageContract)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return err
	}
	if stageHash != queueHash || stageContract != contract {
		return errors.New("RECOVERY_OBJECTIVE_STAGE_IDENTITY_CHANGED")
	}

	o, err := loadRecoveryObjectiveIdentity(p.Store.DB, objectiveID)
	if err != nil {
		return err
	}
	if o.Current != id || o.Next != stage || o.Generation != out.AuthorityGeneration {
		return errors.New("RECOVERY_OBJECTIVE_IDENTITY_CHANGED")
	}
	out.ObjectiveID = o.ID
	out.ObjectiveStage = stage
	out.ObjectiveRevision = o.Revision
	return nil
}

func loadRecoveryObjectiveIdentity(db *sql.DB, id string) (recoveryObjectiveIdentity, error) {
	var out recoveryObjectiveIdentity
	var raw []byte
	var revision int64
	var priority int
	if err := db.QueryRow(
		"SELECT raw,revision,priority FROM objectives WHERE id=?",
		id,
	).Scan(&raw, &revision, &priority); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return recoveryObjectiveIdentity{}, errors.New("RECOVERY_OBJECTIVE_STATE_CORRUPT")
	}
	if out.ID != id ||
		out.Schema != "ckb-plane.objective.v1" ||
		out.Revision != revision ||
		out.Priority != priority ||
		out.Next < 0 ||
		out.Next > out.Total ||
		out.Total < 1 {
		return recoveryObjectiveIdentity{}, errors.New("RECOVERY_OBJECTIVE_STATE_CORRUPT")
	}
	switch out.Status {
	case "PENDING", "RUNNING", "PAUSED", "WAITING_FOR_EXTERNAL_ORCHESTRATOR", "BLOCKED", "COMPLETED", "CANCELLED":
	default:
		return recoveryObjectiveIdentity{}, errors.New("RECOVERY_OBJECTIVE_STATE_CORRUPT")
	}
	return out, nil
}

func loadRecoveryAttemptEvidence(root, evidence string, out *RecoveryEvidenceSnapshot) error {
	if err := bridgeContained(root, evidence); err != nil {
		return err
	}

	if raw, _, ok := readRetryFeedbackFile(root, evidence, "changed_files.txt", recoverySnapshotChangedFilesLimit, false); ok {
		for _, line := range strings.Split(raw, "\n") {
			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}
			if !safePath(line) {
				return errors.New("RECOVERY_CHANGED_PATH_INVALID")
			}
			out.ChangedFiles = append(out.ChangedFiles, line)
		}
	}

	goAllFailed := false
	if raw, _, ok := readRetryFeedbackFile(root, evidence, "acceptance_checks.json", workerRetryAcceptanceMaxBytes, false); ok {
		var checks []Check
		if err := json.Unmarshal([]byte(raw), &checks); err != nil {
			return errors.New("RECOVERY_ACCEPTANCE_EVIDENCE_INVALID")
		}
		for _, check := range checks {
			if !check.Pass {
				out.FailedChecks = append(out.FailedChecks, check.Name)
				if check.Name == "GO_TEST_FAILED" {
					goAllFailed = true
				}
			}
		}
	}
	if goAllFailed {
		if raw, truncated, ok := readRetryFeedbackFile(
			root, evidence, "go-all.jsonl", recoverySnapshotValidationDiagnosticLimit, true,
		); ok {
			prefix := "GO_TEST_FAILED deterministic output"
			if truncated {
				prefix += " (bounded tail)"
			}
			out.ControllerDiagnostic = prefix + ":\n" + raw
		}
	}

	if raw, _, ok := readRetryFeedbackFile(root, evidence, "worker_exit.json", workerRetryExitMaxBytes, false); ok {
		var exit struct {
			FailureClass string `json:"failure_class"`
			FailureReason string `json:"failure_reason"`
		}
		if err := json.Unmarshal([]byte(raw), &exit); err != nil {
			return errors.New("RECOVERY_WORKER_EXIT_EVIDENCE_INVALID")
		}
		out.WorkerFailureClass = strings.TrimSpace(exit.FailureClass)
		if out.WorkerFailureClass == "" {
			out.WorkerFailureClass = strings.TrimSpace(exit.FailureReason)
		}
	}

	if raw, _, ok := readRetryFeedbackFile(root, evidence, "worker_stderr.log", workerRetryStderrMaxBytes, true); ok {
		out.WorkerDiagnosticExcerpt = raw
	}

	statusPath := filepath.Join(evidence, "attempt_result.json")
	if err := bridgeContained(root, statusPath); err != nil {
		return err
	}
	if info, err := os.Lstat(statusPath); err == nil {
		if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 || info.Size() > workerRetryExitMaxBytes {
			return errors.New("RECOVERY_ATTEMPT_RESULT_INVALID")
		}
		raw, err := os.ReadFile(statusPath)
		if err != nil {
			return err
		}
		var result struct {
			State  string `json:"state"`
			Reason string `json:"reason"`
			Attempt int   `json:"attempt"`
		}
		if err = json.Unmarshal(raw, &result); err != nil {
			return errors.New("RECOVERY_ATTEMPT_RESULT_INVALID")
		}
		if result.Attempt != out.BlockedAttempt || result.State != "BLOCKED" || strings.TrimSpace(result.Reason) != strings.TrimSpace(out.OriginalBlocker) {
			return errors.New("RECOVERY_ATTEMPT_RESULT_MISMATCH")
		}
	} else if !os.IsNotExist(err) {
		return err
	}
	return nil
}
