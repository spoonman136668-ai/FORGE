package plane

import (
	"context"
	"testing"
)

func prepareRetryWaitAcknowledgeFixture(t *testing.T) (*Engine, string) {
	t.Helper()
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "ACK_RETRY_WAIT")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec(
		"UPDATE work_orders SET state='REJECTED_RETRYABLE',reason='GO_TEST_ASSERTION_FAILED' WHERE id=?",
		q.ID,
	); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec(
		"UPDATE queue_items SET state='RETRY_WAIT',reason='bounded-repair',next_retry=?,updated=? WHERE id=?",
		now(), now(), q.ID,
	); e != nil {
		t.Fatal(e)
	}
	return p, q.ID
}

func TestAcknowledgePausedRetryWaitReviewsWithoutConsumingAttempt(t *testing.T) {
	p, id := prepareRetryWaitAcknowledgeFixture(t)
	if e := p.Store.Pause(false); e != nil {
		t.Fatal(e)
	}
	if _, e := p.LocalControl(context.Background(), "acknowledge", id); e == nil || e.Error() != "ACKNOWLEDGE_REQUIRES_BLOCKED_OR_FAILED" {
		t.Fatalf("unpaused retry-wait acknowledgement must fail closed: %v", e)
	}
	if e := p.Store.Pause(true); e != nil {
		t.Fatal(e)
	}
	result, e := p.LocalControl(context.Background(), "acknowledge", id)
	if e != nil {
		t.Fatal(e)
	}
	m, ok := result.(map[string]string)
	if !ok || m["state"] != "REVIEWED" {
		t.Fatalf("unexpected acknowledge result: %#v", result)
	}
	var queueState, jobState string
	if e = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", id).Scan(&queueState); e != nil {
		t.Fatal(e)
	}
	if e = p.Store.DB.QueryRow("SELECT state FROM work_orders WHERE id=?", id).Scan(&jobState); e != nil {
		t.Fatal(e)
	}
	if queueState != "REVIEWED" || jobState != "REJECTED_RETRYABLE" {
		t.Fatalf("unexpected states queue=%s job=%s", queueState, jobState)
	}
}

func TestAcknowledgePausedRetryWaitRefusesActiveAttempt(t *testing.T) {
	p, id := prepareRetryWaitAcknowledgeFixture(t)
	if e := p.Store.Pause(true); e != nil {
		t.Fatal(e)
	}
	p.mu.Lock()
	p.cancels[id] = func() {}
	p.mu.Unlock()
	t.Cleanup(func() {
		p.mu.Lock()
		delete(p.cancels, id)
		p.mu.Unlock()
	})
	if _, e := p.LocalControl(context.Background(), "acknowledge", id); e == nil || e.Error() != "ACKNOWLEDGE_RETRY_WAIT_ACTIVE_ATTEMPT" {
		t.Fatalf("active retry-wait acknowledgement must fail closed: %v", e)
	}
	var queueState string
	if e := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", id).Scan(&queueState); e != nil {
		t.Fatal(e)
	}
	if queueState != "RETRY_WAIT" {
		t.Fatalf("active attempt changed queue state: %s", queueState)
	}
}
