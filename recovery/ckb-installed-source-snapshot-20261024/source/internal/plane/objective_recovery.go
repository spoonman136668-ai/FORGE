package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
	"strconv"
)

// Final dispatch gate lives in the existing lease transaction. A pause arriving
// after Engine preflight but before lease acquisition still prevents launch.
func objectiveLeaseGate(tx *sql.Tx, id string, attempt int) error {
	var tables int
	if e := tx.QueryRow("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='objective_stages'").Scan(&tables); e != nil {
		return e
	}
	if tables == 0 {
		return nil
	}
	var raw []byte
	e := tx.QueryRow("SELECT o.raw FROM objectives o JOIN objective_stages s ON s.objective_id=o.id WHERE s.work_id=?", id).Scan(&raw)
	if errors.Is(e, sql.ErrNoRows) {
		return nil
	}
	if e != nil {
		return e
	}
	var o Objective
	if e = json.Unmarshal(raw, &o); e != nil {
		return e
	}
	if o.Schema != objectiveSchema || o.Status != "RUNNING" || o.Paused || o.Current != id || (o.StopAfterCurrent && attempt == 0) {
		return errors.New("OBJECTIVE_LEASE_HELD")
	}
	var generation string
	if e = tx.QueryRow("SELECT value FROM settings WHERE key='autonomy_generation'").Scan(&generation); e != nil {
		return e
	}
	g, e := strconv.ParseInt(generation, 10, 64)
	if e != nil || g < 1 || g != o.Generation {
		return errors.New("AUTHORITY_GENERATION_CHANGED")
	}
	return nil
}

// Crash recovery never turns an interrupted retained continuation, or recorded
// Codex exhaustion, into the ordinary controller-interrupted retry path. A
// partial capture remains a hard evidence-repair boundary with retained paths.
func (p *Engine) recoverObjectiveHold(j Job) (bool, error) {
	if !p.Config.Autonomy.ObjectiveController {
		return false, nil
	}
	reason := ""
	var raw []byte
	e := p.Store.DB.QueryRow("SELECT handoff FROM objective_continuations WHERE work_id=? AND next_attempt=?", j.ID, j.Attempt).Scan(&raw)
	if e == nil {
		reason = "CONTINUATION_INTERRUPTED_REVIEW_REQUIRED"
	} else if !errors.Is(e, sql.ErrNoRows) {
		return false, e
	}
	if j.Order.Worker.Preferred == "codex" && codexExhaustion(j.Evidence) {
		reason = "CODEX_QUOTA_EXHAUSTED"
	}
	if reason == "" {
		return false, nil
	}
	workspace := j.Workspace
	if len(raw) > 0 {
		var h ObjectiveHandoff
		if e = json.Unmarshal(raw, &h); e != nil {
			return true, e
		}
		workspace = h.Workspace
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return true, e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("UPDATE work_orders SET state='BLOCKED',reason=?,workspace=? WHERE id=?", reason, workspace, j.ID); e != nil {
		return true, e
	}
	queueState := "BLOCKED"
	if reason == "CODEX_QUOTA_EXHAUSTED" {
		queueState = "WAITING_FOR_EXTERNAL_ORCHESTRATOR"
	}
	if _, e = tx.Exec("UPDATE queue_items SET state=?,reason=?,next_retry='',updated=? WHERE id=?", queueState, reason, now(), j.ID); e != nil {
		return true, e
	}
	var objectiveRaw []byte
	e = tx.QueryRow("SELECT o.raw FROM objectives o JOIN objective_stages s ON s.objective_id=o.id WHERE s.work_id=?", j.ID).Scan(&objectiveRaw)
	if e != nil && !errors.Is(e, sql.ErrNoRows) {
		return true, e
	}
	if e == nil {
		var o Objective
		if e = json.Unmarshal(objectiveRaw, &o); e != nil {
			return true, e
		}
		if o.Status != "CANCELLED" {
			o.Status = queueState
			o.Blocker = reason
			if reason == "CODEX_QUOTA_EXHAUSTED" {
				o.Handoff = &ObjectiveHandoff{Schema: "ckb-plane.external-orchestrator-handoff.v1", WorkOrderID: j.ID, Attempt: j.Attempt, Workspace: workspace, Evidence: j.Evidence, BaselineRef: j.Order.Baseline.Ref, BaselineSHA: j.Order.Baseline.SHA, EvidenceComplete: false, RequiredAction: "Crash interrupted exhaustion capture. Preserve workspace; bounded evidence repair required before continuation."}
			}
			if e = saveObjective(tx, &o, "RECOVERY_HELD: "+reason, false); e != nil {
				return true, e
			}
		}
	}
	if _, e = tx.Exec("DELETE FROM worker_leases WHERE work_order_id=?", j.ID); e != nil {
		return true, e
	}
	if e = event(tx, j.ID, j.Attempt, "OBJECTIVE_RECOVERY_HELD", reason+"; retained workspace and evidence require verification"); e != nil {
		return true, e
	}
	return true, tx.Commit()
}
