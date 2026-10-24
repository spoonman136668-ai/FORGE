package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestDPCancelReasonRecordedForNoProgress(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.MaxNoProgressSeconds = 1

	ctx, cancel := context.WithCancel(context.Background())
	p.mu.Lock()
	p.cancels["STALLED"] = cancel
	p.mu.Unlock()
	defer func() {
		p.mu.Lock()
		delete(p.cancels, "STALLED")
		delete(p.cancelReasons, "STALLED")
		p.mu.Unlock()
	}()

	if _, e := p.Store.DB.Exec("INSERT INTO worker_progress VALUES(?,?)", "STALLED", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if e := p.monitorProgress("STALLED"); e != nil {
		t.Fatal(e)
	}
	if ctx.Err() == nil {
		t.Fatal("no progress did not cancel owned process")
	}
	if got := p.attemptCancelReason("STALLED"); got != "NO_PROGRESS_TIMEOUT" {
		t.Fatalf("cancel reason = %q", got)
	}
}

func TestDPWorkerCancelledDetailRemainsRetryable(t *testing.T) {
	if !retryable("WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE") {
		t.Fatal("detailed worker-cancel reason must remain retryable")
	}
	if got := failureClass("WORKER_CANCELLED: NO_PROGRESS_TIMEOUT"); got != "WORKER_CANCELLED" {
		t.Fatalf("failure class = %q", got)
	}
}

func TestDPWorkerCancelRetryEscapeIsOneShotAndRequiresNoCandidate(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DP_WORKER_CANCEL_RETRY")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason=?,evidence=? WHERE id=?", p.Config.Policy.MaxAttempts, "RETRY_LIMIT_REACHED: WORKER_CANCELLED", filepath.Join(p.Root, "evidence", q.ID, "cancel"), q.ID); e != nil {
		t.Fatal(e)
	}
	evidence := filepath.Join(p.Root, "evidence", q.ID, "cancel")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "worker_exit.json"), []byte(`{"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: test"}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "candidate.diff"), nil, 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte("\n"), 0600); e != nil {
		t.Fatal(e)
	}
	var raw []byte
	var hash string
	if e := p.Store.DB.QueryRow("SELECT raw,hash FROM queue_items WHERE id=?", q.ID).Scan(&raw, &hash); e != nil {
		t.Fatal(e)
	}
	result := QueueResult{Schema: "ckb-plane.queue-result.v1", WorkOrderID: q.ID, InputSHA256: hash, Mode: "source", Authorization: "operator", Disposition: "failed", Reason: "RETRY_LIMIT_REACHED: WORKER_CANCELLED", Blocker: "RETRY_LIMIT_REACHED: WORKER_CANCELLED", WorkerLaunchAttempted: true, SourceHygieneRan: false, ProductionAccepted: false}
	receiptRaw, _ := json.Marshal(result)
	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", q.ID, digest(receiptRaw), receiptRaw); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='FAILED',reason=?,receipt='' WHERE id=?", result.Reason, q.ID); e != nil {
		t.Fatal(e)
	}

	v, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e != nil {
		t.Fatal(e)
	}
	out := v.(map[string]any)
	if out["worker_cancel_retry_escape"] != true {
		t.Fatalf("worker cancel retry escape not reported: %#v", out)
	}
	if _, e = p.QueueRetry(context.Background(), q.ID, "operator", "source"); e == nil {
		t.Fatal("worker cancel retry escape must be one-shot")
	}
}

func TestDPWorkerCancelRetryReasonSurvivesAuthorizeReadyAndLease(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DP_WORKER_CANCEL_REASON_SURVIVES")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='DRAFT',attempt=?,reason=? WHERE id=?", p.Config.Policy.MaxAttempts, workerCancelRetryAuthorizedReason, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',authorization='operator',mode='source' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(q.ID); e != nil {
		t.Fatal(e)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.Reason != workerCancelRetryAuthorizedReason {
		t.Fatalf("worker cancel retry reason lost after Authorize: %q", j.Reason)
	}
	if e := p.Ready(q.ID); e != nil {
		t.Fatal(e)
	}
	j, e = p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.Reason != workerCancelRetryAuthorizedReason {
		t.Fatalf("worker cancel retry reason lost after Ready: %q", j.Reason)
	}
	if _, e := p.Store.Lease(q.ID, "codex", p.Config.Policy.MaxAttempts); e != nil {
		t.Fatal(e)
	}
}

func TestDPWorkerCancelRetryFalseStartCanReplayOnce(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DP_WORKER_CANCEL_FALSE_START")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	evidence := filepath.Join(p.Root, "evidence", q.ID, "cancel")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "worker_exit.json"), []byte(`{"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: test"}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "candidate.diff"), nil, 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte("\n"), 0600); e != nil {
		t.Fatal(e)
	}
	var raw []byte
	var hash string
	if e := p.Store.DB.QueryRow("SELECT raw,hash FROM queue_items WHERE id=?", q.ID).Scan(&raw, &hash); e != nil {
		t.Fatal(e)
	}
	falseStart := QueueResult{Schema: "ckb-plane.queue-result.v1", WorkOrderID: q.ID, InputSHA256: hash, Mode: "source", Authorization: "operator", Disposition: "blocked", Reason: "RETRY_LIMIT_REACHED", Blocker: "RETRY_LIMIT_REACHED", WorkerLaunchAttempted: false, SourceHygieneRan: false, ProductionAccepted: false}
	receiptRaw, _ := json.Marshal(falseStart)
	receipt := filepath.Join(p.Root, "evidence", "queue", q.ID, "false-start", "queue-result.json")
	if e := os.MkdirAll(filepath.Dir(receipt), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(receipt, receiptRaw, 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", q.ID, digest(receiptRaw), receiptRaw); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason='RETRY_LIMIT_REACHED',evidence=? WHERE id=?", p.Config.Policy.MaxAttempts, evidence, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason='RETRY_LIMIT_REACHED',receipt=? WHERE id=?", receipt, q.ID); e != nil {
		t.Fatal(e)
	}
	if e := eventMust(p, q.ID, p.Config.Policy.MaxAttempts, workerCancelRetryAuthorizedReason, "prior false-start worker cancel retry"); e != nil {
		t.Fatal(e)
	}

	v, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e != nil {
		t.Fatal(e)
	}
	out := v.(map[string]any)
	if out["worker_cancel_retry_escape"] != true {
		t.Fatalf("false-start worker cancel replay not reported: %#v", out)
	}
}

func TestDPWorkerCancelRetryMultipleFalseStartsReplayUntilLease(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DP_WORKER_CANCEL_MULTI_FALSE_START")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	evidence := filepath.Join(p.Root, "evidence", q.ID, "cancel")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "worker_exit.json"), []byte(`{"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: test"}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "candidate.diff"), nil, 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte("\n"), 0600); e != nil {
		t.Fatal(e)
	}
	var raw []byte
	var hash string
	if e := p.Store.DB.QueryRow("SELECT raw,hash FROM queue_items WHERE id=?", q.ID).Scan(&raw, &hash); e != nil {
		t.Fatal(e)
	}
	falseStart := QueueResult{Schema: "ckb-plane.queue-result.v1", WorkOrderID: q.ID, InputSHA256: hash, Mode: "source", Authorization: "operator", Disposition: "blocked", Reason: "RETRY_LIMIT_REACHED", Blocker: "RETRY_LIMIT_REACHED", WorkerLaunchAttempted: false, SourceHygieneRan: false, ProductionAccepted: false}
	receiptRaw, _ := json.Marshal(falseStart)
	receipt := filepath.Join(p.Root, "evidence", "queue", q.ID, "false-start", "queue-result.json")
	if e := os.MkdirAll(filepath.Dir(receipt), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(receipt, receiptRaw, 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", q.ID, digest(receiptRaw), receiptRaw); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason='RETRY_LIMIT_REACHED',evidence=? WHERE id=?", p.Config.Policy.MaxAttempts, evidence, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason='RETRY_LIMIT_REACHED',receipt=? WHERE id=?", receipt, q.ID); e != nil {
		t.Fatal(e)
	}
	if e := eventMust(p, q.ID, p.Config.Policy.MaxAttempts, workerCancelRetryAuthorizedReason, "first false-start worker cancel retry"); e != nil {
		t.Fatal(e)
	}
	if e := eventMust(p, q.ID, p.Config.Policy.MaxAttempts, workerCancelRetryAuthorizedReason, "second false-start worker cancel retry"); e != nil {
		t.Fatal(e)
	}

	v, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e != nil {
		t.Fatal(e)
	}
	out := v.(map[string]any)
	if out["worker_cancel_retry_escape"] != true {
		t.Fatalf("multi false-start worker cancel replay not reported: %#v", out)
	}

	var retryAt string
	if e := p.Store.DB.QueryRow("SELECT timestamp FROM events WHERE work_order_id=? AND type=? ORDER BY id DESC LIMIT 1", q.ID, workerCancelRetryAuthorizedReason).Scan(&retryAt); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason='RETRY_LIMIT_REACHED',evidence=? WHERE id=?", p.Config.Policy.MaxAttempts, evidence, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason='RETRY_LIMIT_REACHED',receipt=? WHERE id=?", receipt, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO worker_attempts(work_order_id,attempt,worker,started) VALUES(?,?,?,?)", q.ID, p.Config.Policy.MaxAttempts+1, "codex", time.Now().Add(time.Second).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE worker_attempts SET started=? WHERE work_order_id=? AND attempt=?", time.Now().Add(time.Second).UTC().Format(time.RFC3339Nano), q.ID, p.Config.Policy.MaxAttempts+1); e != nil {
		t.Fatal(e)
	}
	if retryAt == "" {
		t.Fatal("empty retry timestamp")
	}
	if _, e = p.QueueRetry(context.Background(), q.ID, "operator", "source"); e == nil {
		t.Fatal("worker cancel retry must stop after a replayed worker lease exists")
	}
}

func eventMust(p *Engine, id string, attempt int, typ, msg string) error {
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if e = event(tx, id, attempt, typ, msg); e != nil {
		return e
	}
	return tx.Commit()
}

func TestDPNoProgressHonorsRecentWorkerStartupGrace(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.MaxNoProgressSeconds = 1
	p.Config.Autonomy.PollSeconds = 5

	ctx, cancel := context.WithCancel(context.Background())
	p.mu.Lock()
	p.cancels["STARTING"] = cancel
	p.mu.Unlock()
	defer func() {
		p.mu.Lock()
		delete(p.cancels, "STARTING")
		delete(p.cancelReasons, "STARTING")
		p.mu.Unlock()
	}()

	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", "STARTING", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO worker_attempts(work_order_id,attempt,worker,started) VALUES(?,?,?,?)", "STARTING", 7, "codex", now()); e != nil {
		t.Fatal(e)
	}
	if e := p.monitorProgress("STARTING"); e != nil {
		t.Fatal(e)
	}
	if ctx.Err() != nil {
		t.Fatal("startup grace did not protect a just-leased worker")
	}
}

func TestDPNoProgressHonorsRecentWorkerLaunchEvent(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.MaxNoProgressSeconds = 1
	p.Config.Autonomy.PollSeconds = 5

	ctx, cancel := context.WithCancel(context.Background())
	p.mu.Lock()
	p.cancels["LAUNCHING"] = cancel
	p.mu.Unlock()
	defer func() {
		p.mu.Lock()
		delete(p.cancels, "LAUNCHING")
		delete(p.cancelReasons, "LAUNCHING")
		p.mu.Unlock()
	}()

	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", "LAUNCHING", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES(?,?,?,'WORKER_LAUNCH_ATTEMPTED','INFO','Worker invocation begins','{}')", now(), "LAUNCHING", 7); e != nil {
		t.Fatal(e)
	}
	if e := p.monitorProgress("LAUNCHING"); e != nil {
		t.Fatal(e)
	}
	if ctx.Err() != nil {
		t.Fatal("startup grace did not protect a just-launched worker")
	}
}

func TestDPNoProgressHonorsLiveProcessRecord(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.MaxNoProgressSeconds = 1

	ctx, cancel := context.WithCancel(context.Background())
	p.mu.Lock()
	p.cancels["LIVEPROC"] = cancel
	p.mu.Unlock()
	defer func() {
		p.mu.Lock()
		delete(p.cancels, "LIVEPROC")
		delete(p.cancelReasons, "LIVEPROC")
		p.mu.Unlock()
	}()

	if _, e := p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", "LIVEPROC", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO process_records(work_order_id,attempt,pid,finished) VALUES(?,?,?,0)", "LIVEPROC", 7, 12345); e != nil {
		t.Fatal(e)
	}
	if e := p.monitorProgress("LIVEPROC"); e != nil {
		t.Fatal(e)
	}
	if ctx.Err() != nil {
		t.Fatal("no-progress cancelled an active supervised process")
	}
}

func TestDPWorkerCancelRetryAfterConsumedAttemptAllowsFreshCancelEvidence(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DP_WORKER_CANCEL_FRESH_ATTEMPT")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}

	evidence := filepath.Join(p.Root, "evidence", q.ID, "7")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "worker_exit.json"), []byte(`{"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: NO_PROGRESS_TIMEOUT","cancel_reason":"NO_PROGRESS_TIMEOUT"}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "candidate.diff"), nil, 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte("\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := eventMust(p, q.ID, p.Config.Policy.MaxAttempts, workerCancelRetryAuthorizedReason, "consumed retry authorization"); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO worker_attempts(work_order_id,attempt,worker,started,finished,exit_code) VALUES(?,?,?,?,?,-1)", q.ID, p.Config.Policy.MaxAttempts+1, "codex", time.Now().Add(time.Second).UTC().Format(time.RFC3339Nano), time.Now().Add(2*time.Second).UTC().Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason=?,evidence=? WHERE id=?", p.Config.Policy.MaxAttempts+1, "RETRY_LIMIT_REACHED: WORKER_CANCELLED: NO_PROGRESS_TIMEOUT", evidence, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason=? WHERE id=?", "RETRY_LIMIT_REACHED: WORKER_CANCELLED: NO_PROGRESS_TIMEOUT", q.ID); e != nil {
		t.Fatal(e)
	}

	v, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e != nil {
		t.Fatal(e)
	}
	out := v.(map[string]any)
	if out["worker_cancel_retry_escape"] != true {
		t.Fatalf("fresh worker-cancel attempt retry escape not reported: %#v", out)
	}
}
