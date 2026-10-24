package plane

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const preWorkerRetryAuthorizedReason = "OPERATOR_PREWORKER_RETRY_AUTHORIZED"
const workerCancelRetryAuthorizedReason = "OPERATOR_WORKER_CANCEL_RETRY_AUTHORIZED"

// RetryQueueOffline only schedules a retry. The controller performs the normal
// authorization, dependency, baseline and dispatch checks on its next tick.
func (p *Engine) RetryQueueOffline(ctx context.Context, id, auth, mode string) (any, error) {
	f, e := p.controllerLock()
	if e != nil {
		if !strings.HasPrefix(e.Error(), "SERVICE_LOCKED:") {
			return nil, e
		}
		v, er := p.callLocalController(ctx, NativeRequest{Action: "retry", ID: id, Authorization: auth, Mode: mode})
		if er != nil {
			return nil, errors.Join(e, er)
		}
		return v, nil
	}
	defer f.Close()
	return p.QueueRetry(ctx, id, auth, mode)
}

func (p *Engine) QueueRetry(ctx context.Context, id, auth, mode string) (any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	return p.queueRetryLocked(ctx, id, auth, mode)
}

func (p *Engine) queueRetryLocked(ctx context.Context, id, auth, mode string) (any, error) {
	if e := p.objectiveRetryGuard(id); e != nil {
		return nil, e
	}
	if !safeID.MatchString(id) {
		return nil, errors.New("WORK_ORDER_ID_INVALID")
	}
	if auth != "operator" || mode != "source" {
		return nil, errors.New("RETRY_REQUIRES_OPERATOR_SOURCE")
	}
	if p.Config.Policy.AcceptedRefMutation {
		return nil, errors.New("ACCEPTED_REF_MUTATION_FORBIDDEN")
	}
	if e := p.sourceAuthority(ctx); e != nil {
		return nil, e
	}
	if e := p.noLiveSupervisors(); e != nil {
		return nil, e
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var raw, native []byte
	var hash, state, jobState string
	var attempt, leases int
	if e = tx.QueryRow("SELECT raw,hash,state FROM queue_items WHERE id=?", id).Scan(&raw, &hash, &state); e != nil {
		return nil, e
	}
	if digest(raw) != hash {
		return nil, errors.New("QUEUE_RAW_HASH_MISMATCH")
	}
	switch state {
	case "FAILED", "BLOCKED", "PENDING", "RETRY_WAIT":
	default:
		return nil, fmt.Errorf("QUEUE_RETRY_STATE_INVALID: %s", state)
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		return nil, e
	}
	if q.Kind != "source" {
		return nil, errors.New("RETRY_REQUIRES_SOURCE")
	}
	if e = tx.QueryRow("SELECT yaml,state,attempt FROM work_orders WHERE id=?", id).Scan(&native, &jobState, &attempt); e != nil {
		return nil, e
	}
	if !bytes.Equal(native, []byte(q.WorkOrderYAML)) {
		return nil, errors.New("QUEUE_NATIVE_ORDER_MISMATCH")
	}
	switch jobState {
	case "FAILED", "BLOCKED", "PENDING", "RETRY_WAIT", "REJECTED_RETRYABLE", "DRAFT", "AUTHORIZED", "READY":
	default:
		return nil, fmt.Errorf("WORK_ORDER_RETRY_STATE_INVALID: %s", jobState)
	}
	var jobReason string
	if e = tx.QueryRow("SELECT reason FROM work_orders WHERE id=?", id).Scan(&jobReason); e != nil {
		return nil, e
	}
	preWorkerRetryEscape := false
	workerCancelRetryEscape := false
	workerAuthRetryEscape := false
	retryDecision := p.retryDecisionNow(id, attempt, jobReason)
	if retryDecision.ExternalHandoff {
		return nil, errors.New("EXTERNAL_ORCHESTRATOR_REQUIRED")
	}
	if retryDecision.HardStop {
		ok, er := p.preWorkerRetryEscapeAllowed(tx, id, hash)
		if er != nil {
			return nil, er
		}
		if ok {
			preWorkerRetryEscape = true
		} else {
			ok, er = p.workerCancelRetryEscapeAllowed(tx, id, hash)
			if er != nil {
				return nil, er
			}
			workerCancelRetryEscape = ok
			if !ok {
				workerAuthRetryEscape, er = p.workerAuthRetryEscapeAllowed(tx, id, hash)
				if er != nil {
					return nil, er
				}
				if !workerAuthRetryEscape {
					return nil, errors.New("RETRY_LIMIT_REACHED")
				}
			}
		}
	}
	if e = tx.QueryRow("SELECT count(*) FROM worker_leases WHERE work_order_id=?", id).Scan(&leases); e != nil {
		return nil, e
	}
	if leases != 0 {
		return nil, errors.New("ATTEMPT_STILL_OWNED")
	}
	// Validate every existing envelope; never replace edited bytes with a retry.
	for _, dir := range []string{"pending", "failed", "completed"} {
		path, er := p.queuePath(dir, id)
		if er != nil {
			return nil, er
		}
		b, er := os.ReadFile(path)
		if er == nil {
			if digest(b) != hash {
				return nil, errors.New("QUEUE_INPUT_CHANGED")
			}
			if dir == "completed" {
				return nil, errors.New("QUEUE_ALREADY_COMPLETED")
			}
		} else if !os.IsNotExist(er) {
			return nil, er
		}
	}
	path, e := p.queuePath("pending", id)
	if e != nil {
		return nil, e
	}
	if _, e = os.Stat(path); os.IsNotExist(e) {
		if e = durableNew(path, raw); e != nil {
			return nil, e
		}
	} else if e != nil {
		return nil, e
	}
	retryReason := "OPERATOR_RETRY_AUTHORIZED"
	if preWorkerRetryEscape {
		retryReason = preWorkerRetryAuthorizedReason
	} else if workerCancelRetryEscape {
		retryReason = workerCancelRetryAuthorizedReason
	} else if workerAuthRetryEscape {
		retryReason = workerAuthRetryAuthorizedReason
	}
	if _, e = tx.Exec("UPDATE work_orders SET state='DRAFT',reason=? WHERE id=?", retryReason, id); e != nil {
		return nil, e
	}
	if _, e = tx.Exec("DELETE FROM authorization_contracts WHERE work_order_id=?", id); e != nil {
		return nil, e
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='QUEUED',authorization='operator',mode='source',reason=?,next_retry='',receipt='',updated=? WHERE id=?", retryReason, now(), id); e != nil {
		return nil, e
	}
	eventMessage := fmt.Sprintf("queue=%s -> QUEUED; work_order=%s -> DRAFT; sha256=%s", state, jobState, hash)
	if preWorkerRetryEscape {
		eventMessage += "; pre_worker_retry_escape=true"
	}
	if workerCancelRetryEscape {
		eventMessage += "; worker_cancel_retry_escape=true"
	}
	if workerAuthRetryEscape {
		eventMessage += "; worker_auth_retry_escape=true"
	}
	eventMessage += fmt.Sprintf("; retry_policy_window_active=%t; retry_budget=%d; retry_window_expires_at=%s; retry_exhaustion_class=%s", retryDecision.WindowActive, retryDecision.EffectiveBudget, retryDecision.WindowExpiresAt, retryDecision.ExhaustionClass)
	if e = event(tx, id, attempt, retryReason, eventMessage); e != nil {
		return nil, e
	}
	if e = tx.Commit(); e != nil {
		return nil, e
	}
	return map[string]any{"id": id, "queue_state_before": state, "queue_state_after": "QUEUED", "work_order_state_before": jobState, "work_order_state_after": "DRAFT", "sha256": hash, "pre_worker_retry_escape": preWorkerRetryEscape, "worker_cancel_retry_escape": workerCancelRetryEscape, "worker_auth_retry_escape": workerAuthRetryEscape, "retry_budget": retryDecision.EffectiveBudget, "retry_budget_override": false, "retry_policy_window_active": retryDecision.WindowActive, "retry_window_expires_at": retryDecision.WindowExpiresAt, "retry_exhaustion_class": retryDecision.ExhaustionClass, "production_accepted": false}, nil
}

func (p *Engine) preWorkerRetryEscapeAllowed(tx *sql.Tx, id, inputHash string) (bool, error) {
	var state, receiptPath string
	if e := tx.QueryRow("SELECT state,receipt FROM queue_items WHERE id=?", id).Scan(&state, &receiptPath); e != nil {
		return false, e
	}
	if state != "BLOCKED" {
		return false, nil
	}

	var receiptHash string
	var receiptRaw []byte
	e := tx.QueryRow("SELECT hash,raw FROM queue_receipts WHERE work_order_id=?", id).Scan(&receiptHash, &receiptRaw)
	if errors.Is(e, sql.ErrNoRows) {
		if receiptPath == "" {
			return false, nil
		}
		data, er := os.ReadFile(receiptPath)
		if er != nil {
			return false, nil
		}
		receiptRaw = data
		receiptHash = digest(data)
	} else if e != nil {
		return false, e
	}
	if len(receiptRaw) == 0 || digest(receiptRaw) != receiptHash {
		return false, nil
	}

	var result QueueResult
	if e = json.Unmarshal(receiptRaw, &result); e != nil {
		return false, nil
	}
	if result.WorkOrderID != id || result.InputSHA256 != inputHash || result.ProductionAccepted {
		return false, nil
	}
	if result.WorkerLaunchAttempted || result.SourceHygieneRan {
		return false, nil
	}
	blocker := result.Blocker
	if blocker == "" {
		blocker = result.Reason
	}
	return strings.HasPrefix(blocker, "REPO_UNAVAILABLE") || strings.HasPrefix(blocker, "WORKSPACE_MATERIALIZATION_FAILED"), nil
}

func (p *Engine) workerCancelRetryEscapeAllowed(tx *sql.Tx, id, inputHash string) (bool, error) {
	var state, receiptPath, evidence string
	if e := tx.QueryRow("SELECT state,receipt FROM queue_items WHERE id=?", id).Scan(&state, &receiptPath); e != nil {
		return false, e
	}
	if state != "FAILED" && state != "BLOCKED" {
		return false, nil
	}
	var used int
	if e := tx.QueryRow("SELECT count(*) FROM events WHERE work_order_id=? AND type=?", id, workerCancelRetryAuthorizedReason).Scan(&used); e != nil {
		return false, e
	}
	if used != 0 {
		// A retry authorization event is not the same as a consumed worker
		// attempt. Controller false-starts can re-block before Store.Lease records
		// a new attempt; those must remain replayable after the underlying
		// controller bug is fixed. If a later worker attempt did launch and then
		// produced fresh WORKER_CANCELLED/no-candidate evidence, allow one new
		// operator-bound replay for that newer attempt.
		if ok, er := p.workerCancelRetryAfterConsumedAttemptAllowed(tx, id, inputHash); er != nil || ok {
			return ok, er
		}
		return p.workerCancelRetryFalseStartAllowed(tx, id, inputHash, receiptPath)
	}

	var receiptHash string
	var receiptRaw []byte
	e := tx.QueryRow("SELECT hash,raw FROM queue_receipts WHERE work_order_id=?", id).Scan(&receiptHash, &receiptRaw)
	if errors.Is(e, sql.ErrNoRows) {
		if receiptPath == "" {
			return false, nil
		}
		data, er := os.ReadFile(receiptPath)
		if er != nil {
			return false, nil
		}
		receiptRaw = data
		receiptHash = digest(data)
	} else if e != nil {
		return false, e
	}
	if len(receiptRaw) == 0 || digest(receiptRaw) != receiptHash {
		return false, nil
	}
	var result QueueResult
	if e = json.Unmarshal(receiptRaw, &result); e != nil {
		return false, nil
	}
	blocker := result.Blocker
	if blocker == "" {
		blocker = result.Reason
	}
	if result.WorkOrderID != id || result.InputSHA256 != inputHash || result.ProductionAccepted || !result.WorkerLaunchAttempted || result.SourceHygieneRan || !strings.Contains(blocker, "WORKER_CANCELLED") {
		return false, nil
	}
	if e = tx.QueryRow("SELECT evidence FROM work_orders WHERE id=?", id).Scan(&evidence); e != nil {
		return false, e
	}
	return p.workerCancelEvidenceStillRetryable(evidence)
}

func (p *Engine) workerCancelRetryAfterConsumedAttemptAllowed(tx *sql.Tx, id, inputHash string) (bool, error) {
	var retryAtRaw string
	if e := tx.QueryRow("SELECT timestamp FROM events WHERE work_order_id=? AND type=? ORDER BY id DESC LIMIT 1", id, workerCancelRetryAuthorizedReason).Scan(&retryAtRaw); e != nil {
		return false, e
	}
	retryAt, e := time.Parse(time.RFC3339Nano, retryAtRaw)
	if e != nil {
		return false, e
	}

	var attempt int
	var reason, evidence string
	if e = tx.QueryRow("SELECT attempt,reason,evidence FROM work_orders WHERE id=?", id).Scan(&attempt, &reason, &evidence); e != nil {
		return false, e
	}
	if attempt < 1 || !strings.Contains(reason, "WORKER_CANCELLED") {
		return false, nil
	}

	var startedRaw string
	if e = tx.QueryRow("SELECT started FROM worker_attempts WHERE work_order_id=? AND attempt=?", id, attempt).Scan(&startedRaw); errors.Is(e, sql.ErrNoRows) {
		return false, nil
	} else if e != nil {
		return false, e
	}
	started, e := time.Parse(time.RFC3339Nano, startedRaw)
	if e != nil {
		return false, e
	}
	if !started.After(retryAt) {
		return false, nil
	}

	return p.workerCancelEvidenceStillRetryable(evidence)
}

func (p *Engine) workerCancelRetryFalseStartAllowed(tx *sql.Tx, id, inputHash, receiptPath string) (bool, error) {
	var reason, evidence string
	if e := tx.QueryRow("SELECT reason,evidence FROM work_orders WHERE id=?", id).Scan(&reason, &evidence); e != nil {
		return false, e
	}
	if reason != "RETRY_LIMIT_REACHED" {
		return false, nil
	}
	var retryAt string
	if e := tx.QueryRow("SELECT timestamp FROM events WHERE work_order_id=? AND type=? ORDER BY id DESC LIMIT 1", id, workerCancelRetryAuthorizedReason).Scan(&retryAt); e != nil {
		return false, e
	}
	var laterAttempts int
	if e := tx.QueryRow("SELECT count(*) FROM worker_attempts WHERE work_order_id=? AND started>?", id, retryAt).Scan(&laterAttempts); e != nil {
		return false, e
	}
	if laterAttempts != 0 {
		return false, nil
	}
	if receiptPath != "" {
		data, e := os.ReadFile(receiptPath)
		if e != nil {
			return false, nil
		}
		var result QueueResult
		if e = json.Unmarshal(data, &result); e != nil {
			return false, nil
		}
		blocker := result.Blocker
		if blocker == "" {
			blocker = result.Reason
		}
		if result.WorkOrderID != id || result.InputSHA256 != inputHash || result.ProductionAccepted || result.WorkerLaunchAttempted || result.SourceHygieneRan || blocker != "RETRY_LIMIT_REACHED" {
			return false, nil
		}
	}
	return p.workerCancelEvidenceStillRetryable(evidence)
}

func (p *Engine) workerCancelEvidenceStillRetryable(evidence string) (bool, error) {
	if evidence == "" {
		return false, nil
	}
	if e := bridgeContained(p.Root, evidence); e != nil {
		return false, nil
	}
	var workerExit struct {
		FailureClass  string `json:"failure_class"`
		FailureReason string `json:"failure_reason"`
	}
	data, e := os.ReadFile(filepath.Join(evidence, "worker_exit.json"))
	if e != nil {
		return false, nil
	}
	if e = json.Unmarshal(data, &workerExit); e != nil {
		return false, nil
	}
	if workerExit.FailureClass != "WORKER_CANCELLED" && !strings.HasPrefix(workerExit.FailureReason, "WORKER_CANCELLED") {
		return false, nil
	}
	for _, name := range []string{"candidate.diff", "changed_files.txt"} {
		data, e = os.ReadFile(filepath.Join(evidence, name))
		if e != nil {
			return false, nil
		}
		if strings.TrimSpace(string(data)) != "" {
			return false, nil
		}
	}
	return true, nil
}

func (p *Engine) queueBlockers(items []QueueItem) ([]string, error) {
	var blockers []string
	for _, item := range items {
		if p.Config.Autonomy.ObjectiveController && item.State == "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
			blockers = append(blockers, "WAITING_FOR_EXTERNAL_ORCHESTRATOR: "+item.ID)
			continue
		}
		var state, reason string
		e := p.Store.DB.QueryRow("SELECT state,reason FROM work_orders WHERE id=?", item.ID).Scan(&state, &reason)
		if e != nil && !errors.Is(e, sql.ErrNoRows) {
			return nil, e
		}
		if (item.State == "PENDING" || item.State == "RETRY_WAIT" || item.State == "QUEUED") && (state == "BLOCKED" || state == "FAILED") {
			blockers = append(blockers, fmt.Sprintf("QUEUE_JOB_STATE_MISMATCH: %s queue_items=%s work_orders=%s blocker=%s", item.ID, item.State, state, reason))
		} else if item.State == "BLOCKED" || item.State == "FAILED" {
			blockers = append(blockers, fmt.Sprintf("OPERATOR_BLOCKED: %s queue_items=%s work_orders=%s blocker=%s", item.ID, item.State, state, item.Reason))
		} else if item.State == "PENDING" && item.Authorization == "operator" && item.Mode == "source" {
			blockers = append(blockers, fmt.Sprintf("QUEUE_RECONCILIATION_REQUIRED: %s queue_items=PENDING work_orders=%s blocker=%s", item.ID, state, reason))
		}
	}
	return blockers, nil
}

func (p *Engine) queueStates(id string) (string, string) {
	queue, job := "ABSENT", "ABSENT"
	_ = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", id).Scan(&queue)
	_ = p.Store.DB.QueryRow("SELECT state FROM work_orders WHERE id=?", id).Scan(&job)
	return queue, job
}

func (p *Engine) blockOperatorDecision(j Job) error {
	reason := j.Reason
	if !strings.HasPrefix(reason, "OPERATOR_DECISION_REQUIRED") {
		reason = "OPERATOR_DECISION_REQUIRED: " + reason
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("UPDATE work_orders SET state='BLOCKED',reason=? WHERE id=?", reason, j.ID); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='BLOCKED',reason=?,next_retry='',updated=? WHERE id=?", reason, now(), j.ID); e != nil {
		return e
	}
	if e = event(tx, j.ID, j.Attempt, "OPERATOR_DECISION_REQUIRED", reason); e != nil {
		return e
	}
	return tx.Commit()
}

// Journal the failure without moving the envelope or consuming an operator decision.
func (p *Engine) preWorkerFailure(item QueueItem, queueBefore, jobBefore, reason string) error {
	r := QueueResult{Schema: "ckb-plane.queue-result.v1", RunID: randomID(), WorkOrderID: item.ID,
		InputSHA256: item.Hash, Mode: item.Mode, Authorization: item.Authorization,
		Disposition: "blocked", Reason: reason, Blocker: reason, ObservedAt: now(),
		QueueStateBefore: queueBefore, QueueStateAfter: "BLOCKED", WorkOrderStateBefore: jobBefore, WorkOrderStateAfter: "BLOCKED"}
	if current, er := p.Store.Get(item.ID); er == nil {
		r.Workspace = current.Workspace
		r.BaselineRef = current.Order.Baseline.Ref
		r.BaselineSHA = current.Order.Baseline.SHA
	}
	_, jobAfter := p.queueStates(item.ID)
	if jobAfter == "ABSENT" {
		r.WorkOrderStateAfter = "ABSENT"
	}
	r.Evidence = filepath.Join(p.Root, "evidence", "queue", item.ID, r.RunID)
	data, e := json.MarshalIndent(r, "", "  ")
	if e != nil {
		return e
	}
	path := filepath.Join(r.Evidence, "queue-result.json")
	if e = durableNew(path, data); e != nil {
		return e
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("UPDATE work_orders SET state='BLOCKED',reason=? WHERE id=?", reason, item.ID); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='BLOCKED',reason=?,receipt=?,updated=? WHERE id=?", reason, path, now(), item.ID); e != nil {
		return e
	}
	if _, e = tx.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", item.ID, digest(data), data); e != nil {
		return e
	}
	if e = event(tx, item.ID, 0, "PRE_WORKER_FAILURE", reason+"; evidence="+path); e != nil {
		return e
	}
	return tx.Commit()
}
