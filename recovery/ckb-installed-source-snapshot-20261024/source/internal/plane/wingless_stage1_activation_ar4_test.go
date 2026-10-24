package plane

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func ar4ValidOrder() WorkOrder {
	var o WorkOrder
	o.ID = "AR4_STAGE1"
	o.Title = "bounded Stage-1 worker preflight"
	o.Repo = "fixture"
	o.Baseline.Ref = "accepted/fixture"
	o.Baseline.SHA = strings.Repeat("a", 40)
	o.Worker.Branch = "codex/ar4-stage1"
	o.Worker.Preferred = winglessStage1RegisteredWorkerName
	o.Scope.Allowed = []string{"calc.go"}
	o.Scope.Forbidden = []string{"calc_test.go"}
	o.Acceptance.ProtectRefs = true
	o.Acceptance.Clean = true
	return o
}

func ar4RegisteredConfig(t *testing.T) WinglessStage1RegisteredConfig {
	t.Helper()
	root := t.TempDir()
	makeFile := func(name string) string {
		p := filepath.Join(root, name)
		if err := os.WriteFile(p, []byte("ar4"), 0600); err != nil {
			t.Fatal(err)
		}
		abs, err := filepath.Abs(p)
		if err != nil {
			t.Fatal(err)
		}
		return abs
	}
	return WinglessStage1RegisteredConfig{
		ServiceProgram: makeFile("service.exe"),
		ServiceSHA256:  strings.Repeat("1", 64),
		ModelPath:      makeFile("model.gguf"),
		ModelSHA256:    strings.Repeat("2", 64),
		ModelBytes:     4,
		RuntimePath:    makeFile("llama-server.exe"),
		RuntimeSHA256:  strings.Repeat("3", 64),
	}
}

func TestWinglessStage1ActivationExplicitRegistrationOnly(t *testing.T) {
	store, err := OpenStore(filepath.Join(t.TempDir(), "state.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.DB.Close()
	e := &Engine{Store: store, workers: map[string]Worker{"fake": FakeWorker{}, "codex": CodexAdapter{}}}
	if _, ok := e.workers[winglessStage1RegisteredWorkerName]; ok {
		t.Fatal("Wingless Stage-1 must not be registered by default")
	}
	if err := e.RegisterWinglessStage1(ar4RegisteredConfig(t)); err != nil {
		t.Fatal(err)
	}
	w, ok := e.workers[winglessStage1RegisteredWorkerName]
	if !ok || w == nil || w.Name() != winglessStage1RegisteredWorkerName {
		t.Fatalf("explicit registration missing: %#v", w)
	}
}

func TestWinglessStage1ActivationRegistrationDoesNotLaunchService(t *testing.T) {
	store, err := OpenStore(filepath.Join(t.TempDir(), "state.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.DB.Close()
	e := &Engine{
		Store:   store,
		workers: map[string]Worker{"fake": FakeWorker{}, "codex": CodexAdapter{}},
		runner: ProcessRunnerFunc(func(_ context.Context, _ ProcessSpec, _, _ io.Writer) error {
			t.Fatal("registration must not launch a process")
			return nil
		}),
	}
	if err := e.RegisterWinglessStage1(ar4RegisteredConfig(t)); err != nil {
		t.Fatal(err)
	}
}

func TestWinglessStage1ActivationWorkOrderValidation(t *testing.T) {
	o := ar4ValidOrder()
	if err := o.Validate(); err != nil {
		t.Fatalf("explicit Stage-1 work order should validate: %v", err)
	}
	o.Worker.Preferred = "wingless-stage2"
	if err := o.Validate(); err == nil {
		t.Fatal("unknown Wingless worker must fail closed")
	}
}

func TestWinglessStage1ActivationReplayFence(t *testing.T) {
	store, err := OpenStore(filepath.Join(t.TempDir(), "state.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.DB.Close()
	e := &Engine{Store: store, workers: map[string]Worker{}}
	if err := e.RegisterWinglessStage1(ar4RegisteredConfig(t)); err != nil {
		t.Fatal(err)
	}
	w := e.workers[winglessStage1RegisteredWorkerName].(*winglessStage1RegisteredWorker)
	b := WinglessStage1Binding{
		WorkOrderID: "AR4_STAGE1", Attempt: 1, Workspace: filepath.Join(t.TempDir(), "w"),
		BaselineSHA: strings.Repeat("a", 40), WorkOrderDigest: strings.Repeat("b", 64),
	}
	if err := w.claimFence(b); err != nil {
		t.Fatal(err)
	}
	err = w.claimFence(b)
	if err == nil || !retainWorkerLease(err) {
		t.Fatalf("same-attempt replay must fail closed and retain ownership: %v", err)
	}
}

func TestWinglessStage1ActivationOwnershipUncertaintyRetainsLease(t *testing.T) {
	err := winglessStage1Retain("WINGLESS_STAGE1_SERVICE_OWNERSHIP_UNCERTAIN", errors.New("proof"))
	if !retainWorkerLease(err) {
		t.Fatal("ownership uncertainty must retain worker lease")
	}
	if retainWorkerLease(errors.New("ordinary")) {
		t.Fatal("ordinary errors must not retain worker lease")
	}
}

func TestWinglessStage1ActivationRollbackDefaultDisabled(t *testing.T) {
	var c WinglessStage1Config
	if c.Enabled {
		t.Fatal("zero-value rollback configuration must disable Wingless")
	}
}
