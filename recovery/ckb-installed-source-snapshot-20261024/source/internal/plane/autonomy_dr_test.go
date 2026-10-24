package plane

import (
	"strings"
	"testing"
	"time"
)

func TestDRStatusNormalizesStaleRunningAfterCompletedPaused(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DR_STATUS_COMPLETED")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='ACCEPTED',reason='All required deterministic gates passed',attempt=3 WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='COMPLETED',reason='LOCAL_CANDIDATE_ACCEPTED',updated=? WHERE id=?", now(), q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.Store.Pause(true); e != nil {
		t.Fatal(e)
	}
	if e := p.setSetting("autonomy_status", "RUNNING: "+q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.setSetting("autonomy_heartbeat", time.Now().UTC().Add(-time.Hour).Format(time.RFC3339Nano)); e != nil {
		t.Fatal(e)
	}

	status, e := p.AutonomyStatus()
	if e != nil {
		t.Fatal(e)
	}
	got := status["controller_status"].(string)
	if got != "PAUSED" {
		t.Fatalf("completed paused queue must not display stale RUNNING: %q", got)
	}
	if stale, ok := status["heartbeat_stale"].(bool); !ok || !stale {
		t.Fatalf("expected stale heartbeat flag: %#v", status["heartbeat_stale"])
	}
}

func TestDRStatusKeepsObservedActiveEngineering(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DR_STATUS_ENGINEERING")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='ENGINEERING',reason='Worker editing isolated attempt worktree',attempt=1 WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',reason='operator run',updated=? WHERE id=?", now(), q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.Store.Pause(true); e != nil {
		t.Fatal(e)
	}
	if e := p.setSetting("autonomy_status", "PAUSED"); e != nil {
		t.Fatal(e)
	}

	status, e := p.AutonomyStatus()
	if e != nil {
		t.Fatal(e)
	}
	got := status["controller_status"].(string)
	if !strings.Contains(got, "RUNNING: "+q.ID) || !strings.Contains(got, "Worker editing isolated attempt worktree") {
		t.Fatalf("active engineering state must be surfaced: %q", got)
	}
}

func TestDRStatusShowsAcceptedRunningEnvelopeAsFinalizing(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DR_STATUS_FINALIZING")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='ACCEPTED',reason='All required deterministic gates passed',attempt=2 WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',reason='operator acceptance replay',updated=? WHERE id=?", now(), q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.setSetting("autonomy_status", "RUNNING: "+q.ID); e != nil {
		t.Fatal(e)
	}

	status, e := p.AutonomyStatus()
	if e != nil {
		t.Fatal(e)
	}
	got := status["controller_status"].(string)
	if !strings.Contains(got, "FINALIZING: "+q.ID) {
		t.Fatalf("accepted work with a RUNNING queue envelope must report finalization, not stale RUNNING: %q", got)
	}
}

func TestDRHeartbeatFreshnessBudget(t *testing.T) {
	if !autonomyHeartbeatStale("", 5) {
		t.Fatal("blank heartbeat must be stale")
	}
	fresh := time.Now().UTC().Format(time.RFC3339Nano)
	if autonomyHeartbeatStale(fresh, 5) {
		t.Fatal("fresh heartbeat should not be stale")
	}
	old := time.Now().UTC().Add(-time.Hour).Format(time.RFC3339Nano)
	if !autonomyHeartbeatStale(old, 5) {
		t.Fatal("old heartbeat must be stale")
	}
}
