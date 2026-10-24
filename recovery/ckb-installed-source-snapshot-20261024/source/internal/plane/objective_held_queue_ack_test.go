package plane

import (
	"context"
	"testing"
)

func TestObjectiveAbandonBlockedHeldQueueReviewsWithoutAcceptance(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	q := plan.Orders[0]

	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	o := ocGet(t, p, plan.ID)
	o.Status = "BLOCKED"
	o.Blocker = "AUTHORITY_LEASE_NOT_ACQUIRED"
	if e := p.objectiveSave(&o, "BLOCKED: AUTHORITY_LEASE_NOT_ACQUIRED", false); e != nil {
		t.Fatal(e)
	}
	o = ocGet(t, p, plan.ID)

	v, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{
		Action:           "abandon-blocked",
		ID:               o.ID,
		ExpectedRevision: o.Revision,
	})
	if e != nil {
		t.Fatal(e)
	}
	got := v.(Objective)
	if got.Status != "CANCELLED" || !got.Paused {
		t.Fatalf("objective=%+v", got)
	}
	if got.Blocker != "OBJECTIVE_BLOCKED_RECONCILED: AUTHORITY_LEASE_NOT_ACQUIRED" {
		t.Fatalf("blocker=%q", got.Blocker)
	}

	var queueState, queueReason string
	if e = p.Store.DB.QueryRow("SELECT state,reason FROM queue_items WHERE id=?", q.ID).Scan(&queueState, &queueReason); e != nil {
		t.Fatal(e)
	}
	if queueState != "REVIEWED" || queueReason != got.Blocker {
		t.Fatalf("queue state=%q reason=%q", queueState, queueReason)
	}

	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.State != "DRAFT" || j.State == "ACCEPTED" {
		t.Fatalf("native job changed unexpectedly: %+v", j)
	}

	var stageState string
	if e = p.Store.DB.QueryRow("SELECT state FROM objective_stages WHERE work_id=?", q.ID).Scan(&stageState); e != nil {
		t.Fatal(e)
	}
	if stageState != "QUEUED" {
		t.Fatalf("stage audit state=%q", stageState)
	}

	busy, e := p.objectiveBusy()
	if e != nil {
		t.Fatal(e)
	}
	if busy {
		t.Fatal("reviewed held stage still blocks successor publication")
	}
}

func TestObjectiveAbandonBlockedRefusesRunningObjectiveAndActiveJob(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	q := plan.Orders[0]

	o := ocGet(t, p, plan.ID)
	if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{
		Action:           "abandon-blocked",
		ID:               o.ID,
		ExpectedRevision: o.Revision,
	}); e == nil || e.Error() != "OBJECTIVE_ABANDON_REQUIRES_BLOCKED" {
		t.Fatalf("running objective abandon error=%v", e)
	}

	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='ENGINEERING' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	o = ocGet(t, p, plan.ID)
	o.Status = "BLOCKED"
	o.Blocker = "AUTHORITY_LEASE_NOT_ACQUIRED"
	if e := p.objectiveSave(&o, "BLOCKED: AUTHORITY_LEASE_NOT_ACQUIRED", false); e != nil {
		t.Fatal(e)
	}
	o = ocGet(t, p, plan.ID)

	if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{
		Action:           "abandon-blocked",
		ID:               o.ID,
		ExpectedRevision: o.Revision,
	}); e == nil || e.Error() != "OBJECTIVE_ABANDON_WORK_STATE_INVALID" {
		t.Fatalf("active job abandon error=%v", e)
	}

	var queueState string
	if e := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", q.ID).Scan(&queueState); e != nil {
		t.Fatal(e)
	}
	if queueState != "QUEUED" {
		t.Fatalf("refused abandon mutated queue state=%q", queueState)
	}
}
