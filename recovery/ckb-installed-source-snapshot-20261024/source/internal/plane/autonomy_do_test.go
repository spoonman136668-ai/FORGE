package plane

import (
	"context"
	"errors"
	"testing"
)

func TestDOControllerLoopIsExplicit(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.Enabled = true
	if p.shouldRunAutonomyLoop() {
		t.Fatal("legacy serve path must not consume the source queue")
	}
	p.controllerLoop = true
	if !p.shouldRunAutonomyLoop() {
		t.Fatal("controller run path must enable queue consumption")
	}
}

func TestDOMaterializationIgnoresCanceledAttemptParent(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DO_MATERIALIZATION_CONTEXT")
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.Ready(q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',authorization='operator',mode='source' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	n, e := p.Store.Lease(q.ID, "codex", p.Config.Policy.MaxAttempts)
	if e != nil {
		t.Fatal(e)
	}

	originalPrepare := prepareWorkspace
	checked := make(chan error, 1)
	prepareWorkspace = func(ctx context.Context, tool, source, root string, order WorkOrder) (string, RepoState, error) {
		if err := ctx.Err(); err != nil {
			checked <- err
		} else {
			checked <- nil
		}
		return "", RepoState{Baseline: order.Baseline.SHA, SourceRefs: "source refs captured"}, errors.New("forced DO materialization failure")
	}
	defer func() { prepareWorkspace = originalPrepare }()

	attemptCtx, cancel := context.WithCancel(context.Background())
	cancel()
	p.run(attemptCtx, q.ID, n)

	if err := <-checked; err != nil {
		t.Fatalf("materialization inherited canceled attempt context: %v", err)
	}
	j := wait(t, p, q.ID)
	if j.State != "BLOCKED" || j.Reason == "WORKSPACE_MATERIALIZATION_FAILED: context canceled" {
		t.Fatalf("unexpected materialization result: %+v", j)
	}
}
