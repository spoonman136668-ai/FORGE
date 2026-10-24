package plane

import (
	"context"
	"testing"
)

func TestObjectiveBlockedStageResumeAfterExplicitQueueRetry(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	const failure = "WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_UNAVAILABLE"
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason=?,attempt=2 WHERE id=?", failure, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason=? WHERE id=?", "OPERATOR_DECISION_REQUIRED: "+failure, q.ID); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	o := ocGet(t, p, plan.ID)
	if o.Status != "BLOCKED" {
		t.Fatal(o)
	}
	if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "resume", ID: o.ID, ExpectedRevision: o.Revision}); e == nil {
		t.Fatal("blocked objective resumed before queue reconciliation")
	}
	if _, e := p.QueueRetry(context.Background(), q.ID, "operator", "source"); e != nil {
		t.Fatal(e)
	}
	o = ocGet(t, p, plan.ID)
	res, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "resume", ID: o.ID, ExpectedRevision: o.Revision})
	if e != nil {
		t.Fatal(e)
	}
	got := res.(Objective)
	if got.Status != "RUNNING" || got.Blocker != "" || got.Paused {
		t.Fatal(got)
	}
	p.queueMu.Lock()
	allowed, e := p.objectiveMayStart(context.Background(), q.ID)
	p.queueMu.Unlock()
	if e != nil || !allowed {
		t.Fatalf("reconciled objective did not restore normal start gate: allowed=%v error=%v", allowed, e)
	}
}

func TestObjectiveBlockedStageResumeRejectsTamperedRetryState(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason='SOURCE_HYGIENE_FAILED',attempt=1 WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason='SOURCE_HYGIENE_FAILED' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	if _, e := p.QueueRetry(context.Background(), q.ID, "operator", "source"); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET reason='NOT_AN_OPERATOR_RETRY' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	o := ocGet(t, p, plan.ID)
	if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "resume", ID: o.ID, ExpectedRevision: o.Revision}); e == nil {
		t.Fatal("tampered retry state cleared blocked objective")
	}
}
