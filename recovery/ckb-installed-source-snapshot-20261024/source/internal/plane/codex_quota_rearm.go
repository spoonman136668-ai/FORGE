package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const codexQuotaRestoredRearmReason = "CODEX_QUOTA_RESTORED_REARM"

// RearmCodexQuotaRestoredOffline coordinates with the live controller when it
// owns the root. The service remains the only queue mutator while running.
func (p *Engine) RearmCodexQuotaRestoredOffline(ctx context.Context, id string) (any, error) {
	f, err := p.controllerLock()
	if err != nil {
		if !strings.HasPrefix(err.Error(), "SERVICE_LOCKED:") {
			return nil, err
		}
		v, callErr := p.callLocalController(ctx, NativeRequest{Action: "quota-restored", ID: id})
		if callErr != nil {
			return nil, errors.Join(err, callErr)
		}
		return v, nil
	}
	defer f.Close()
	return p.rearmCodexQuotaRestored(ctx, id)
}

func (p *Engine) rearmCodexQuotaRestored(ctx context.Context, id string) (map[string]any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()

	if !safeID.MatchString(id) {
		return nil, errors.New("WORK_ORDER_ID_INVALID")
	}
	if !p.Config.Autonomy.ObjectiveController {
		return nil, errors.New("OBJECTIVE_CONTROLLER_DISABLED")
	}
	if p.Config.Policy.AcceptedRefMutation {
		return nil, errors.New("ACCEPTED_REF_MUTATION_FORBIDDEN")
	}
	if err := p.sourceAuthority(ctx); err != nil {
		return nil, err
	}
	if err := p.noLiveSupervisors(); err != nil {
		return nil, err
	}

	j, err := p.Store.Get(id)
	if err != nil {
		return nil, err
	}
	if j.State != "BLOCKED" || failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" || j.Attempt < 1 {
		return nil, errors.New("CODEX_QUOTA_REARM_JOB_STATE_INVALID")
	}
	rearmRetryDecision := p.retryDecisionNow(id, j.Attempt, codexQuotaRestoredRearmReason)
	if rearmRetryDecision.HardStop {
		return nil, errors.New("RETRY_LIMIT_REACHED")
	}

	var raw, native []byte
	var hash, queueState, queueReason, kind, mode, authorization string
	if err = p.Store.DB.QueryRow(
		"SELECT raw,hash,state,reason,kind,mode,authorization FROM queue_items WHERE id=?",
		id,
	).Scan(&raw, &hash, &queueState, &queueReason, &kind, &mode, &authorization); err != nil {
		return nil, err
	}
	if queueState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" || queueReason != "CODEX_QUOTA_EXHAUSTED" {
		return nil, fmt.Errorf("CODEX_QUOTA_REARM_QUEUE_STATE_INVALID: state=%s reason=%s", queueState, queueReason)
	}
	if kind != "source" || mode != "source" || authorization != "operator" {
		return nil, errors.New("CODEX_QUOTA_REARM_SOURCE_CONTRACT_INVALID")
	}
	if digest(raw) != hash {
		return nil, errors.New("QUEUE_RAW_HASH_MISMATCH")
	}
	q, err := p.parseQueue(raw, id)
	if err != nil {
		return nil, err
	}
	if q.Kind != "source" {
		return nil, errors.New("CODEX_QUOTA_REARM_REQUIRES_SOURCE")
	}
	if err = p.Store.DB.QueryRow("SELECT yaml FROM work_orders WHERE id=?", id).Scan(&native); err != nil {
		return nil, err
	}
	if !bytes.Equal(native, []byte(q.WorkOrderYAML)) {
		return nil, errors.New("QUEUE_NATIVE_ORDER_MISMATCH")
	}

	var active int
	if err = p.Store.DB.QueryRow(
		"SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)",
		id, id,
	).Scan(&active); err != nil {
		return nil, err
	}
	p.mu.Lock()
	_, owned := p.cancels[id]
	p.mu.Unlock()
	if active != 0 || owned {
		return nil, errors.New("CODEX_QUOTA_REARM_REQUIRES_RELEASED_WORKER")
	}
	if err = p.VerifyEvidence(j); err != nil {
		return nil, err
	}

	handoffPath := filepath.Join(p.Root, "evidence", "external-handoff", id, strconv.Itoa(j.Attempt)+".json")
	if err = bridgeContained(p.Root, handoffPath); err != nil {
		return nil, err
	}
	if err = regularPath(filepath.Dir(handoffPath), filepath.Base(handoffPath)); err != nil {
		return nil, err
	}
	handoffRaw, err := os.ReadFile(handoffPath)
	if err != nil {
		return nil, err
	}
	var h ObjectiveHandoff
	if err = json.Unmarshal(handoffRaw, &h); err != nil {
		return nil, err
	}
	if h.Schema != "ckb-plane.external-orchestrator-handoff.v1" ||
		h.WorkOrderID != id ||
		h.Attempt != j.Attempt ||
		h.Workspace != j.Workspace ||
		h.Evidence != j.Evidence ||
		h.BaselineRef != j.Order.Baseline.Ref ||
		h.BaselineSHA != j.Order.Baseline.SHA ||
		h.QueueSHA != hash ||
		!h.EvidenceComplete {
		return nil, errors.New("CODEX_QUOTA_REARM_HANDOFF_INVALID")
	}
	if h.DeltaSHA != "" {
		data, readErr := os.ReadFile(filepath.Join(j.Evidence, "candidate.diff"))
		if readErr != nil || digest(data) != h.DeltaSHA {
			return nil, errors.New("CODEX_QUOTA_REARM_DELTA_CHANGED")
		}
	}
	if h.InventorySHA != "" {
		data, readErr := os.ReadFile(filepath.Join(j.Evidence, "candidate_inventory.json"))
		if readErr != nil || digest(data) != h.InventorySHA {
			return nil, errors.New("CODEX_QUOTA_REARM_INVENTORY_CHANGED")
		}
	}

	tx, err := p.Store.DB.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	result, err := tx.Exec(
		"UPDATE work_orders SET state='DRAFT',reason=? WHERE id=? AND state='BLOCKED' AND attempt=?",
		codexQuotaRestoredRearmReason, id, j.Attempt,
	)
	if err != nil {
		return nil, err
	}
	if n, rowsErr := result.RowsAffected(); rowsErr != nil || n != 1 {
		if rowsErr != nil {
			return nil, rowsErr
		}
		return nil, errors.New("CODEX_QUOTA_REARM_JOB_STATE_CHANGED")
	}
	if _, err = tx.Exec("DELETE FROM authorization_contracts WHERE work_order_id=?", id); err != nil {
		return nil, err
	}
	result, err = tx.Exec(
		"UPDATE queue_items SET state='QUEUED',authorization='operator',mode='source',reason=?,next_retry='',receipt='',updated=? WHERE id=? AND state='WAITING_FOR_EXTERNAL_ORCHESTRATOR' AND reason='CODEX_QUOTA_EXHAUSTED'",
		codexQuotaRestoredRearmReason, now(), id,
	)
	if err != nil {
		return nil, err
	}
	if n, rowsErr := result.RowsAffected(); rowsErr != nil || n != 1 {
		if rowsErr != nil {
			return nil, rowsErr
		}
		return nil, errors.New("CODEX_QUOTA_REARM_QUEUE_STATE_CHANGED")
	}
	if err = event(tx, id, j.Attempt, codexQuotaRestoredRearmReason,
		"Verified quota-held handoff re-armed for the normal plane-owned source loop; preserved prior workspace/evidence; next worker attempt must use the immutable work order"); err != nil {
		return nil, err
	}
	if err = tx.Commit(); err != nil {
		return nil, err
	}
	return map[string]any{
		"id":                                    id,
		"queue_state_before":                    queueState,
		"queue_state_after":                     "QUEUED",
		"work_order_state_before":               j.State,
		"work_order_state_after":                "DRAFT",
		"attempt_before":                        j.Attempt,
		"next_worker_attempt":                   j.Attempt + 1,
		"attempt_budget_remaining_before_rearm": rearmRetryDecision.EffectiveBudget - j.Attempt,
		"handoff_sha256":                        digest(handoffRaw),
		"preserved_handoff":                     true,
		"accepted_ref_mutated":                  false,
		"runtime_launched":                      false,
	}, nil
}
