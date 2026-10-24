package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
)

const blockerRecoveryTransactionSchema = "ckb-plane.blocker-recovery-transaction.v1"

const (
	blockerRecoveryPending   = "RECOVERY_PENDING"
	blockerRecoveryDiagnosing = "DIAGNOSING"
	blockerRecoveryEscalated = "ESCALATED"
)

type BlockerRecoveryTransaction struct {
	Schema                     string                    `json:"schema"`
	RecoveryID                 string                    `json:"recovery_id"`
	WorkOrderID                string                    `json:"work_order_id"`
	BlockedAttempt             int                       `json:"blocked_attempt"`
	State                      string                    `json:"state"`
	Revision                   int64                     `json:"revision"`
	ControllerRecoveryAttempts int                       `json:"controller_recovery_attempts"`
	DiagnosticAttempts         int                       `json:"diagnostic_attempts"`
	Snapshot                   RecoveryEvidenceSnapshot  `json:"snapshot"`
	Observation                *RecoveryObservation      `json:"observation,omitempty"`
	Created                    string                    `json:"created_at"`
	Updated                    string                    `json:"updated_at"`
}

func initBlockerRecoveryObserverStore(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS blocker_recovery_transactions(
	recovery_id TEXT PRIMARY KEY,
	work_order_id TEXT NOT NULL,
	blocked_attempt INTEGER NOT NULL,
	state TEXT NOT NULL,
	revision INTEGER NOT NULL,
	raw BLOB NOT NULL,
	created TEXT NOT NULL,
	updated TEXT NOT NULL,
	UNIQUE(work_order_id,blocked_attempt)
);
CREATE TABLE IF NOT EXISTS blocker_recovery_decisions(
	recovery_id TEXT NOT NULL,
	revision INTEGER NOT NULL,
	created TEXT NOT NULL,
	decision TEXT NOT NULL,
	structured_json TEXT NOT NULL,
	PRIMARY KEY(recovery_id,revision)
);
`)
	return err
}

func createBlockerRecoveryPending(cfg RecoveryObserverConfig, db *sql.DB, in RecoveryEvidenceSnapshot) (BlockerRecoveryTransaction, error) {
	var out BlockerRecoveryTransaction
	if !cfg.Enabled {
		return out, errRecoveryObserverDisabled
	}
	in = canonicalRecoveryEvidence(in)
	recoveryID, err := recoveryIDForEvidence(in)
	if err != nil {
		return out, err
	}
	tx, err := db.Begin()
	if err != nil {
		return out, err
	}
	defer tx.Rollback()

	existing, err := getBlockerRecoveryTransactionTx(tx, in.WorkOrderID, in.BlockedAttempt)
	if err == nil {
		if existing.RecoveryID != recoveryID {
			return out, errors.New("RECOVERY_IDENTITY_CONFLICT")
		}
		return existing, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return out, err
	}

	at := now()
	out = BlockerRecoveryTransaction{
		Schema:                     blockerRecoveryTransactionSchema,
		RecoveryID:                 recoveryID,
		WorkOrderID:                in.WorkOrderID,
		BlockedAttempt:             in.BlockedAttempt,
		State:                      blockerRecoveryPending,
		Revision:                   1,
		ControllerRecoveryAttempts: 1,
		DiagnosticAttempts:         0,
		Snapshot:                   in,
		Created:                    at,
		Updated:                    at,
	}
	raw, err := json.Marshal(out)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if _, err = tx.Exec(
		"INSERT INTO blocker_recovery_transactions(recovery_id,work_order_id,blocked_attempt,state,revision,raw,created,updated) VALUES(?,?,?,?,?,?,?,?)",
		out.RecoveryID, out.WorkOrderID, out.BlockedAttempt, out.State, out.Revision, raw, out.Created, out.Updated,
	); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err = insertBlockerRecoveryDecision(tx, out, "RECOVERY_PENDING", map[string]any{
		"evidence_manifest_sha256": in.EvidenceManifestSHA256,
		"authority_generation":      in.AuthorityGeneration,
		"original_blocker":          in.OriginalBlocker,
	}); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err = tx.Commit(); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return out, nil
}

func classifyBlockerRecoveryPending(cfg RecoveryObserverConfig, db *sql.DB, recoveryID string) (BlockerRecoveryTransaction, error) {
	var out BlockerRecoveryTransaction
	if !cfg.Enabled {
		return out, errRecoveryObserverDisabled
	}
	tx, err := db.Begin()
	if err != nil {
		return out, err
	}
	defer tx.Rollback()

	out, err = getBlockerRecoveryTransactionByIDTx(tx, recoveryID)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if out.State == blockerRecoveryDiagnosing || out.State == blockerRecoveryEscalated {
		if out.Observation == nil {
			return BlockerRecoveryTransaction{}, errors.New("RECOVERY_STATE_CORRUPT")
		}
		return out, nil
	}
	if out.State != blockerRecoveryPending || out.Observation != nil {
		return BlockerRecoveryTransaction{}, errors.New("RECOVERY_STATE_INVALID")
	}

	observation, err := ObserveRecovery(cfg, out.Snapshot)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if observation.RecoveryID != out.RecoveryID {
		return BlockerRecoveryTransaction{}, errors.New("RECOVERY_IDENTITY_CHANGED")
	}

	previous := out.Revision
	out.Revision++
	out.ControllerRecoveryAttempts++
	out.DiagnosticAttempts++
	out.Observation = &observation
	out.Updated = now()
	decision := "RECOVERY_CLASSIFIED"
	if observation.AuthorityRequired {
		out.State = blockerRecoveryEscalated
		decision = "RECOVERY_ESCALATED"
	} else {
		out.State = blockerRecoveryDiagnosing
	}
	raw, err := json.Marshal(out)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	result, err := tx.Exec(
		"UPDATE blocker_recovery_transactions SET state=?,revision=?,raw=?,updated=? WHERE recovery_id=? AND revision=?",
		out.State, out.Revision, raw, out.Updated, out.RecoveryID, previous,
	)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	changed, err := result.RowsAffected()
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if changed != 1 {
		return BlockerRecoveryTransaction{}, errors.New("RECOVERY_REVISION_CONFLICT")
	}
	if err = insertBlockerRecoveryDecision(tx, out, decision, map[string]any{
		"normalized_class":   observation.NormalizedClass,
		"subtype":            observation.Subtype,
		"authority_required": observation.AuthorityRequired,
		"automatic_mutation": observation.AutomaticMutation,
	}); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err = tx.Commit(); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return out, nil
}

func getBlockerRecoveryTransaction(db *sql.DB, recoveryID string) (BlockerRecoveryTransaction, error) {
	var out BlockerRecoveryTransaction
	var raw []byte
	var revision int64
	var state string
	if err := db.QueryRow("SELECT raw,revision,state FROM blocker_recovery_transactions WHERE recovery_id=?", recoveryID).Scan(&raw, &revision, &state); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err := validateBlockerRecoveryTransaction(out, recoveryID, revision, state); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return out, nil
}

func getBlockerRecoveryTransactionTx(tx *sql.Tx, workOrderID string, attempt int) (BlockerRecoveryTransaction, error) {
	var out BlockerRecoveryTransaction
	var raw []byte
	var revision int64
	var state string
	if err := tx.QueryRow(
		"SELECT raw,revision,state FROM blocker_recovery_transactions WHERE work_order_id=? AND blocked_attempt=?",
		workOrderID, attempt,
	).Scan(&raw, &revision, &state); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err := validateBlockerRecoveryTransaction(out, out.RecoveryID, revision, state); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return out, nil
}

func getBlockerRecoveryTransactionByIDTx(tx *sql.Tx, recoveryID string) (BlockerRecoveryTransaction, error) {
	var out BlockerRecoveryTransaction
	var raw []byte
	var revision int64
	var state string
	if err := tx.QueryRow("SELECT raw,revision,state FROM blocker_recovery_transactions WHERE recovery_id=?", recoveryID).Scan(&raw, &revision, &state); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err := validateBlockerRecoveryTransaction(out, recoveryID, revision, state); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return out, nil
}

func validateBlockerRecoveryTransaction(v BlockerRecoveryTransaction, recoveryID string, revision int64, state string) error {
	if v.Schema != blockerRecoveryTransactionSchema || v.RecoveryID != recoveryID || v.Revision != revision || v.State != state {
		return errors.New("RECOVERY_STATE_CORRUPT")
	}
	if v.WorkOrderID == "" || v.BlockedAttempt < 0 || v.ControllerRecoveryAttempts < 1 || v.DiagnosticAttempts < 0 {
		return errors.New("RECOVERY_STATE_CORRUPT")
	}
	switch v.State {
	case blockerRecoveryPending:
		if v.Observation != nil || v.DiagnosticAttempts != 0 {
			return errors.New("RECOVERY_STATE_CORRUPT")
		}
	case blockerRecoveryDiagnosing, blockerRecoveryEscalated:
		if v.Observation == nil || v.DiagnosticAttempts < 1 {
			return errors.New("RECOVERY_STATE_CORRUPT")
		}
	default:
		return errors.New("RECOVERY_STATE_UNKNOWN")
	}
	return nil
}

func insertBlockerRecoveryDecision(tx *sql.Tx, v BlockerRecoveryTransaction, decision string, structured any) error {
	raw, err := json.Marshal(structured)
	if err != nil {
		return err
	}
	_, err = tx.Exec(
		"INSERT INTO blocker_recovery_decisions(recovery_id,revision,created,decision,structured_json) VALUES(?,?,?,?,?)",
		v.RecoveryID, v.Revision, v.Updated, decision, string(raw),
	)
	return err
}
