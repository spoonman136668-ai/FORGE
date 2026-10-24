package plane

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestAcceptanceRunningEnvelopeIsNotWorkerMonitored(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "ACCEPTANCE_SCHEDULER_ISOLATION")
	if err := p.Store.Load([]byte(q.WorkOrderYAML)); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec("UPDATE work_orders SET state='ACCEPTING',reason='Running deterministic gates',attempt=1 WHERE id=?", q.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',reason='maintenance acceptance replay',updated=? WHERE id=?", now(), q.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", q.ID, time.Now().UTC().Add(-time.Hour).Format(time.RFC3339Nano)); err != nil {
		t.Fatal(err)
	}

	owned, cancel := context.WithCancel(context.Background())
	p.mu.Lock()
	p.cancels[q.ID] = cancel
	p.mu.Unlock()
	defer func() {
		p.mu.Lock()
		delete(p.cancels, q.ID)
		p.mu.Unlock()
		cancel()
	}()

	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if owned.Err() != nil {
		t.Fatalf("acceptance context was canceled by worker supervision: %v", owned.Err())
	}
	if got := p.setting("autonomy_status"); got != "ACCEPTING: "+q.ID {
		t.Fatalf("autonomy status=%q, want accepting envelope", got)
	}
	j, err := p.Store.Get(q.ID)
	if err != nil {
		t.Fatal(err)
	}
	if j.State != "ACCEPTING" || !strings.Contains(j.Reason, "deterministic gates") {
		t.Fatalf("acceptance job mutated unexpectedly: %+v", j)
	}
}
