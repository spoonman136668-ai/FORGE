package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
)

type RecoveryPlannerConfig struct {
	Enabled bool
}

var errRecoveryPlannerDisabled = errors.New("RECOVERY_PLANNER_DISABLED")

func initBlockerRecoveryPlannerStore(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS blocker_recovery_plans(
	recovery_id TEXT PRIMARY KEY,
	plan_id TEXT NOT NULL UNIQUE,
	raw BLOB NOT NULL,
	created TEXT NOT NULL
);
`)
	return err
}

// PrepareRecoveryPlan is Stage-4-only. It reads an already-classified recovery
// transaction and persists one deterministic proposal. It does not update
// queue/work-order/objective state and does not authorize execution.
func PrepareRecoveryPlan(cfg RecoveryPlannerConfig, db *sql.DB, recoveryID string) (RecoveryPlan, error) {
	var out RecoveryPlan
	if !cfg.Enabled {
		return out, errRecoveryPlannerDisabled
	}
	txState, err := getBlockerRecoveryTransaction(db, recoveryID)
	if err != nil {
		return out, err
	}
	out, err = PlanRecovery(txState)
	if err != nil {
		return RecoveryPlan{}, err
	}
	if err = initBlockerRecoveryPlannerStore(db); err != nil {
		return RecoveryPlan{}, err
	}

	raw, err := json.Marshal(out)
	if err != nil {
		return RecoveryPlan{}, err
	}
	tx, err := db.Begin()
	if err != nil {
		return RecoveryPlan{}, err
	}
	defer tx.Rollback()

	var existingPlanID string
	var existingRaw []byte
	err = tx.QueryRow(
		"SELECT plan_id,raw FROM blocker_recovery_plans WHERE recovery_id=?",
		recoveryID,
	).Scan(&existingPlanID, &existingRaw)
	if err == nil {
		if existingPlanID != out.PlanID {
			return RecoveryPlan{}, errors.New("RECOVERY_PLAN_IDENTITY_CONFLICT")
		}
		var existing RecoveryPlan
		if json.Unmarshal(existingRaw, &existing) != nil || validateRecoveryPlan(existing) != nil || existing.PlanID != out.PlanID {
			return RecoveryPlan{}, errors.New("RECOVERY_PLAN_STATE_CORRUPT")
		}
		return existing, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return RecoveryPlan{}, err
	}

	if _, err = tx.Exec(
		"INSERT INTO blocker_recovery_plans(recovery_id,plan_id,raw,created) VALUES(?,?,?,?)",
		out.RecoveryID, out.PlanID, raw, now(),
	); err != nil {
		return RecoveryPlan{}, err
	}
	if err = tx.Commit(); err != nil {
		return RecoveryPlan{}, err
	}
	return out, nil
}
