package plane

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func dmWritePreWorkerReceipt(t *testing.T, p *Engine, q QueueOrder, raw []byte, workerLaunched, hygieneRan bool, blocker string) {
	t.Helper()
	if blocker == "" {
		blocker = "REPO_UNAVAILABLE"
	}
	receipt := QueueResult{
		Schema:                "ckb-plane.queue-result.v1",
		RunID:                 "dm-preworker-retry",
		WorkOrderID:           q.ID,
		InputSHA256:           digest(raw),
		Mode:                  "source",
		Authorization:         "operator",
		Disposition:           "blocked",
		Reason:                blocker,
		Blocker:               blocker,
		QueueStateBefore:      "RUNNING",
		QueueStateAfter:       "BLOCKED",
		WorkOrderStateBefore:  "DISPATCHED",
		WorkOrderStateAfter:   "BLOCKED",
		WorkerLaunchAttempted: workerLaunched,
		SourceHygieneRan:      hygieneRan,
		ObservedAt:            now(),
		Evidence:              filepath.Join(p.Root, "evidence", "queue", q.ID, "dm-preworker-retry"),
		ProductionAccepted:    false,
	}
	data, e := json.MarshalIndent(receipt, "", "  ")
	if e != nil {
		t.Fatal(e)
	}
	path := filepath.Join(receipt.Evidence, "queue-result.json")
	if e = durableNew(path, data); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", q.ID, digest(data), data); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason=?,receipt=? WHERE id=?", blocker, path, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason=?,attempt=? WHERE id=?", blocker, p.Config.Policy.MaxAttempts, q.ID); e != nil {
		t.Fatal(e)
	}
}

func TestDMPreWorkerRetryEscapesAttemptCeiling(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")

	result, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e != nil {
		t.Fatal(e)
	}
	text := jsonText(result)
	if !strings.Contains(text, `"pre_worker_retry_escape":true`) {
		t.Fatalf("missing escape marker: %s", text)
	}
	qs, js := p.queueStates(q.ID)
	if qs != "QUEUED" || js != "DRAFT" {
		t.Fatalf("retry did not requeue safely: queue=%s job=%s", qs, js)
	}
	var reason string
	if e = p.Store.DB.QueryRow("SELECT reason FROM work_orders WHERE id=?", q.ID).Scan(&reason); e != nil {
		t.Fatal(e)
	}
	if reason != preWorkerRetryAuthorizedReason {
		t.Fatalf("reason=%q", reason)
	}
}

func TestDMPreWorkerRetryDoesNotBypassLaunchedAttemptLimit(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, true, false, "WORKER_EXIT_NONZERO")

	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("expected retry limit, got %v", e)
	}
	qs, js := p.queueStates(q.ID)
	if qs != "BLOCKED" || js != "BLOCKED" {
		t.Fatalf("refusal mutated states: queue=%s job=%s", qs, js)
	}
}

func TestDMPreWorkerRetryReasonSurvivesReadyAndLease(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "WORKSPACE_MATERIALIZATION_FAILED: path collision")

	if _, e := p.QueueRetry(context.Background(), q.ID, "operator", "source"); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(q.ID); e != nil {
		t.Fatal(e)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.State != "AUTHORIZED" || j.Reason != preWorkerRetryAuthorizedReason {
		t.Fatalf("authorization lost pre-worker marker: %+v", j)
	}
	if e = p.Ready(q.ID); e != nil {
		t.Fatal(e)
	}
	j, e = p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.State != "READY" || j.Reason != preWorkerRetryAuthorizedReason {
		t.Fatalf("ready lost pre-worker marker: %+v", j)
	}
	n, e := p.Store.Lease(q.ID, "codex", p.Config.Policy.MaxAttempts)
	if e != nil {
		t.Fatal(e)
	}
	if n != p.Config.Policy.MaxAttempts+1 {
		t.Fatalf("attempt=%d want %d", n, p.Config.Policy.MaxAttempts+1)
	}
}

func TestDMPreWorkerRetryRejectsReceiptHashMismatch(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")
	if _, e := p.Store.DB.Exec("UPDATE queue_receipts SET hash='wrong' WHERE work_order_id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("receipt mismatch should not bypass limit: %v", e)
	}
}

func TestDMPreWorkerRetryFallbacksToReceiptPath(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")
	if _, e := p.Store.DB.Exec("DELETE FROM queue_receipts WHERE work_order_id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.QueueRetry(context.Background(), q.ID, "operator", "source"); e != nil {
		t.Fatal(e)
	}
	qs, js := p.queueStates(q.ID)
	if qs != "QUEUED" || js != "DRAFT" {
		t.Fatalf("path fallback did not requeue: queue=%s job=%s", qs, js)
	}
}

func TestDMPreWorkerRetryStillRequiresSourceReceipt(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "FOCUSED_TEST_FAILED")
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("non-materialization blocker should stay capped: %v", e)
	}
}

func TestDMPreWorkerRetryMissingReceiptStaysCapped(t *testing.T) {
	p, q, _ := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET attempt=? WHERE id=?", p.Config.Policy.MaxAttempts, q.ID); e != nil {
		t.Fatal(e)
	}
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("missing receipt should stay capped: %v", e)
	}
}

func TestDMPreWorkerRetryBadReceiptPathStaysCapped(t *testing.T) {
	p, q, _ := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET attempt=? WHERE id=?", p.Config.Policy.MaxAttempts, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET receipt=? WHERE id=?", filepath.Join(p.Root, "missing", "queue-result.json"), q.ID); e != nil {
		t.Fatal(e)
	}
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("bad receipt path should stay capped: %v", e)
	}
}

func TestDMPreWorkerRetryReceiptMustMatchInputHash(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET hash='different' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "QUEUE_RAW_HASH_MISMATCH") {
		t.Fatalf("queue hash mismatch should be caught first: %v", e)
	}
}

func TestDMPreWorkerRetryDoesNotMaskAuthorityRefusal(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")
	p.authorityVerifier = func(context.Context) error { return errors.New("ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS") }
	_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
	if e == nil || !strings.Contains(e.Error(), "ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS") {
		t.Fatalf("authority refusal was masked: %v", e)
	}
}

func TestDMPreWorkerRetryDoesNotRequireReceiptDirectoryListing(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "BLOCKED", "BLOCKED")
	dmWritePreWorkerReceipt(t, p, q, raw, false, false, "REPO_UNAVAILABLE")
	receiptDir := filepath.Join(p.Root, "evidence", "queue", q.ID, "dm-preworker-retry")
	if _, e := os.Stat(receiptDir); e != nil {
		t.Fatal(e)
	}
	if _, e := p.QueueRetry(context.Background(), q.ID, "operator", "source"); e != nil {
		t.Fatal(e)
	}
}
