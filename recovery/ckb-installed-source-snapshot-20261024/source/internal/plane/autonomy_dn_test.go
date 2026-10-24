package plane

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

func TestDNMaterializationRecordsProgressBeforePrepare(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DN_MATERIALIZATION_PROGRESS")

	originalPrepare := prepareWorkspace
	checked := make(chan error, 1)
	prepareWorkspace = func(ctx context.Context, tool, source, root string, order WorkOrder) (string, RepoState, error) {
		var observed string
		err := p.Store.DB.QueryRow("SELECT observed FROM worker_progress WHERE work_order_id=?", q.ID).Scan(&observed)
		if err != nil {
			checked <- err
		} else if strings.TrimSpace(observed) == "" {
			checked <- errors.New("empty materialization progress heartbeat")
		} else {
			checked <- nil
		}
		return "", RepoState{Baseline: order.Baseline.SHA, SourceRefs: "source refs pending"}, errors.New("forced DN materialization failure")
	}
	defer func() { prepareWorkspace = originalPrepare }()

	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}

	select {
	case e := <-checked:
		if e != nil {
			t.Fatalf("materialization started without progress heartbeat: %v", e)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("prepare was not reached")
	}

	j := wait(t, p, q.ID)
	if j.State != "BLOCKED" {
		t.Fatalf("expected blocked materialization fixture, got %+v", j)
	}
	if !strings.HasPrefix(j.Reason, "WORKSPACE_MATERIALIZATION_FAILED:") {
		t.Fatalf("expected materialization blocker, got %+v", j)
	}
}
