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

// acknowledgeExternalWaiting provides an operator-reviewed terminal disposition
// for a retained external-orchestrator handoff that cannot be accepted under
// its immutable work-order scope. It never accepts the work order, satisfies a
// dependency, mutates accepted refs, or deletes retained evidence.
func (p *Engine) acknowledgeExternalWaiting(id string) (map[string]string, bool, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()

	var queueState, queueReason string
	err := p.Store.DB.QueryRow("SELECT state,reason FROM queue_items WHERE id=?", id).Scan(&queueState, &queueReason)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, false, nil
	}
	if err != nil {
		return nil, true, err
	}
	if queueState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		return nil, false, nil
	}

	j, err := p.Store.Get(id)
	if err != nil {
		return nil, true, err
	}
	if j.State == "ACCEPTED" || j.Attempt < 1 || j.Workspace == "" || j.Evidence == "" {
		return nil, true, errors.New("ACKNOWLEDGE_EXTERNAL_WAIT_STATE_INVALID")
	}
	if failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" &&
		!strings.HasPrefix(queueReason, "EXTERNAL_REPAIR_ACCEPTANCE_FAILED") {
		return nil, true, errors.New("ACKNOWLEDGE_EXTERNAL_WAIT_REASON_INVALID")
	}

	var active int
	if err = p.Store.DB.QueryRow(
		"SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)",
		id, id,
	).Scan(&active); err != nil {
		return nil, true, err
	}
	p.mu.Lock()
	_, owned := p.cancels[id]
	p.mu.Unlock()
	if active != 0 || owned {
		return nil, true, errors.New("ACKNOWLEDGE_EXTERNAL_WAIT_REQUIRES_RELEASED_WORKER")
	}

	if err = p.VerifyEvidence(j); err != nil {
		return nil, true, err
	}
	handoffPath := filepath.Join(p.Root, "evidence", "external-handoff", id, strconv.Itoa(j.Attempt)+".json")
	if err = bridgeContained(p.Root, handoffPath); err != nil {
		return nil, true, err
	}
	if err = regularPath(filepath.Dir(handoffPath), filepath.Base(handoffPath)); err != nil {
		return nil, true, err
	}
	raw, err := os.ReadFile(handoffPath)
	if err != nil {
		return nil, true, err
	}
	var h ObjectiveHandoff
	if err = json.Unmarshal(raw, &h); err != nil {
		return nil, true, err
	}
	if h.Schema != "ckb-plane.external-orchestrator-handoff.v1" ||
		h.WorkOrderID != id ||
		h.Attempt != j.Attempt ||
		h.Workspace != j.Workspace ||
		h.Evidence != j.Evidence ||
		!h.EvidenceComplete {
		return nil, true, errors.New("ACKNOWLEDGE_EXTERNAL_WAIT_HANDOFF_INVALID")
	}

	tx, err := p.Store.DB.Begin()
	if err != nil {
		return nil, true, err
	}
	defer tx.Rollback()
	result, err := tx.Exec(
		"UPDATE queue_items SET state='REVIEWED',updated=? WHERE id=? AND state='WAITING_FOR_EXTERNAL_ORCHESTRATOR'",
		now(), id,
	)
	if err != nil {
		return nil, true, err
	}
	n, err := result.RowsAffected()
	if err != nil {
		return nil, true, err
	}
	if n != 1 {
		return nil, true, errors.New("ACKNOWLEDGE_EXTERNAL_WAIT_STATE_CHANGED")
	}
	if err = event(
		tx,
		id,
		j.Attempt,
		"EXTERNAL_ORCHESTRATOR_REVIEWED",
		"Operator reviewed retained external-orchestrator handoff without acceptance; dependencies remain unsatisfied",
	); err != nil {
		return nil, true, err
	}
	if err = tx.Commit(); err != nil {
		return nil, true, err
	}
	return map[string]string{
		"id":    id,
		"state": "REVIEWED",
		"note":  "Not accepted; retained external handoff preserved; dependent stages remain ineligible.",
	}, true, nil
}
