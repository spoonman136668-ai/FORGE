package plane

import (
	"context"
	"strings"
	"testing"
)

func TestDWPlaywrightFailureSchedulesBoundedRepair(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "PLAYWRIGHT_REPAIR")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='REJECTED_RETRYABLE',attempt=1,reason='PLAYWRIGHT_FAILED' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',reason='',next_retry='' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}

	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}

	var action, queueState, queueReason, nextRetry string
	if e := p.Store.DB.QueryRow("SELECT action FROM recovery_decisions WHERE work_order_id=? AND attempt=1", q.ID).Scan(&action); e != nil {
		t.Fatal(e)
	}
	if action != "bounded-repair" {
		t.Fatalf("PLAYWRIGHT_FAILED recovery action=%q, want bounded-repair", action)
	}
	if e := p.Store.DB.QueryRow("SELECT state,reason,next_retry FROM queue_items WHERE id=?", q.ID).Scan(&queueState, &queueReason, &nextRetry); e != nil {
		t.Fatal(e)
	}
	if queueState != "RETRY_WAIT" || queueReason != "bounded-repair" || strings.TrimSpace(nextRetry) == "" {
		t.Fatalf("unexpected queue recovery state: state=%q reason=%q next_retry=%q", queueState, queueReason, nextRetry)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.State != "REJECTED_RETRYABLE" || j.Reason != "PLAYWRIGHT_FAILED" || j.Attempt != 1 {
		t.Fatalf("recovery mutated failed attempt unexpectedly: %+v", j)
	}

	if e = p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	if got := p.setting("autonomy_status"); !strings.HasPrefix(got, "RECOVERY_WAIT: ") {
		t.Fatalf("autonomy status=%q, want RECOVERY_WAIT", got)
	}
	var decisions int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM recovery_decisions WHERE work_order_id=? AND attempt=1", q.ID).Scan(&decisions); e != nil {
		t.Fatal(e)
	}
	if decisions != 1 {
		t.Fatalf("recovery decision count=%d, want 1", decisions)
	}
}
