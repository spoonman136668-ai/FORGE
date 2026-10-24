package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
)

const blockerResolverModeSetting = "blocker_resolver_mode"
const blockerResolverStatusSetting = "blocker_resolver_status"
const blockerResolverModeOff = "off"
const blockerResolverModeShadow = "shadow"
const blockerResolverModeActive = "active"

const (
	recoveryShadowPlanned           = "PLANNED"
	recoveryShadowCandidateRunning  = "CANDIDATE_RUNNING"
	recoveryShadowCandidateReady    = "CANDIDATE_READY"
	recoveryShadowValidationRunning = "VALIDATION_RUNNING"
	recoveryShadowValidated         = "SHADOW_VALIDATED"
	recoveryShadowRejected          = "SHADOW_REJECTED"
	recoveryShadowEscalated         = "SHADOW_ESCALATED"
	recoveryShadowFailed            = "SHADOW_FAILED"
	recoveryActiveRetryQueued       = "ACTIVE_RETRY_QUEUED"
	recoveryActiveRetryRefused      = "ACTIVE_RETRY_REFUSED"
)

type BlockerRecoveryShadowRun struct {
	RecoveryID        string `json:"recovery_id"`
	WorkOrderID       string `json:"work_order_id"`
	PlanID            string `json:"plan_id"`
	Phase             string `json:"phase"`
	CandidateAttempt  int    `json:"candidate_attempt,omitempty"`
	ValidationAttempt int    `json:"validation_attempt,omitempty"`
	LastError         string `json:"last_error,omitempty"`
	Created           string `json:"created_at"`
	Updated           string `json:"updated_at"`
}

func blockerResolverMode(p *Engine) string {
	switch p.setting(blockerResolverModeSetting) {
	case blockerResolverModeShadow:
		return blockerResolverModeShadow
	case blockerResolverModeActive:
		return blockerResolverModeActive
	default:
		return blockerResolverModeOff
	}
}

func initBlockerRecoveryShadowStore(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS blocker_recovery_shadow_runs(
	recovery_id TEXT PRIMARY KEY,
	work_order_id TEXT NOT NULL,
	plan_id TEXT NOT NULL,
	phase TEXT NOT NULL,
	raw BLOB NOT NULL,
	created TEXT NOT NULL,
	updated TEXT NOT NULL
);
`)
	return err
}

func ensureBlockerRecoveryShadowRun(db *sql.DB, tx BlockerRecoveryTransaction, plan RecoveryPlan) (BlockerRecoveryShadowRun, error) {
	var out BlockerRecoveryShadowRun
	if tx.RecoveryID == "" || plan.RecoveryID != tx.RecoveryID || plan.PlanID == "" || tx.WorkOrderID == "" {
		return out, errors.New("RECOVERY_SHADOW_IDENTITY_INVALID")
	}
	if err := initBlockerRecoveryShadowStore(db); err != nil {
		return out, err
	}
	var raw []byte
	var phase string
	err := db.QueryRow(
		"SELECT raw,phase FROM blocker_recovery_shadow_runs WHERE recovery_id=?",
		tx.RecoveryID,
	).Scan(&raw, &phase)
	if err == nil {
		if json.Unmarshal(raw, &out) != nil ||
			out.RecoveryID != tx.RecoveryID ||
			out.WorkOrderID != tx.WorkOrderID ||
			out.PlanID != plan.PlanID ||
			out.Phase != phase {
			return BlockerRecoveryShadowRun{}, errors.New("RECOVERY_SHADOW_STATE_CORRUPT")
		}
		return out, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return out, err
	}
	at := now()
	out = BlockerRecoveryShadowRun{
		RecoveryID:  tx.RecoveryID,
		WorkOrderID: tx.WorkOrderID,
		PlanID:      plan.PlanID,
		Phase:       recoveryShadowPlanned,
		Created:     at,
		Updated:     at,
	}
	raw, err = json.Marshal(out)
	if err != nil {
		return BlockerRecoveryShadowRun{}, err
	}
	_, err = db.Exec(
		"INSERT INTO blocker_recovery_shadow_runs(recovery_id,work_order_id,plan_id,phase,raw,created,updated) VALUES(?,?,?,?,?,?,?)",
		out.RecoveryID, out.WorkOrderID, out.PlanID, out.Phase, raw, out.Created, out.Updated,
	)
	return out, err
}

func getBlockerRecoveryShadowRun(db *sql.DB, recoveryID string) (BlockerRecoveryShadowRun, error) {
	var out BlockerRecoveryShadowRun
	var raw []byte
	var phase string
	if err := db.QueryRow(
		"SELECT raw,phase FROM blocker_recovery_shadow_runs WHERE recovery_id=?",
		recoveryID,
	).Scan(&raw, &phase); err != nil {
		return out, err
	}
	if json.Unmarshal(raw, &out) != nil || out.RecoveryID != recoveryID || out.Phase != phase {
		return BlockerRecoveryShadowRun{}, errors.New("RECOVERY_SHADOW_STATE_CORRUPT")
	}
	return out, nil
}

func recoveryShadowTransitionAllowed(from, to string) bool {
	allowed := map[string]map[string]bool{
		recoveryShadowPlanned: {
			recoveryShadowCandidateRunning: true,
			recoveryShadowEscalated:        true,
			recoveryShadowFailed:           true,
			recoveryActiveRetryQueued:      true,
			recoveryActiveRetryRefused:     true,
		},
		recoveryShadowCandidateRunning: {
			recoveryShadowCandidateReady: true,
			recoveryShadowRejected:       true,
			recoveryShadowFailed:         true,
		},
		recoveryShadowCandidateReady: {
			recoveryShadowValidationRunning: true,
			recoveryShadowFailed:            true,
		},
		recoveryShadowValidationRunning: {
			recoveryShadowValidated: true,
			recoveryShadowRejected:  true,
			recoveryShadowFailed:    true,
		},
		recoveryShadowRejected: {
			recoveryShadowValidationRunning: true,
		},
		recoveryShadowEscalated: {
			recoveryActiveRetryQueued:  true,
			recoveryActiveRetryRefused: true,
		},
	}
	return allowed[from][to]
}

func moveBlockerRecoveryShadowRun(db *sql.DB, current BlockerRecoveryShadowRun, from, to string, candidateAttempt, validationAttempt int, detail string) (BlockerRecoveryShadowRun, error) {
	if current.Phase != from || !recoveryShadowTransitionAllowed(from, to) {
		return BlockerRecoveryShadowRun{}, errors.New("RECOVERY_SHADOW_TRANSITION_INVALID")
	}
	next := current
	next.Phase = to
	if candidateAttempt > 0 {
		next.CandidateAttempt = candidateAttempt
	}
	if validationAttempt > 0 {
		next.ValidationAttempt = validationAttempt
	}
	next.LastError = errorText(errors.New(detail))
	if detail == "" {
		next.LastError = ""
	}
	next.Updated = now()
	raw, err := json.Marshal(next)
	if err != nil {
		return BlockerRecoveryShadowRun{}, err
	}
	res, err := db.Exec(
		"UPDATE blocker_recovery_shadow_runs SET phase=?,raw=?,updated=? WHERE recovery_id=? AND phase=?",
		next.Phase, raw, next.Updated, next.RecoveryID, from,
	)
	if err != nil {
		return BlockerRecoveryShadowRun{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return BlockerRecoveryShadowRun{}, err
	}
	if n != 1 {
		return BlockerRecoveryShadowRun{}, errors.New("RECOVERY_SHADOW_OWNERSHIP_LOST")
	}
	return next, nil
}
