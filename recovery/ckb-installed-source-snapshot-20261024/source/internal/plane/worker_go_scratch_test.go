package plane

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type workerGoScratchCaptureRunner struct {
	t         *testing.T
	workspace string
	gocache   *string
	gotmp     *string
}

func (r workerGoScratchCaptureRunner) Run(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
	r.t.Helper()
	env := map[string]string{}
	for _, entry := range spec.Env {
		name, value, ok := strings.Cut(entry, "=")
		if ok {
			env[name] = value
		}
	}
	gc := env["GOCACHE"]
	gt := env["GOTMPDIR"]
	if gc == "" || gt == "" {
		r.t.Fatalf("missing worker Go scratch env: GOCACHE=%q GOTMPDIR=%q", gc, gt)
	}
	if bridgeContained(r.workspace, gc) == nil || bridgeContained(r.workspace, gt) == nil {
		r.t.Fatalf("worker Go scratch must stay outside candidate workspace: GOCACHE=%q GOTMPDIR=%q", gc, gt)
	}
	for _, path := range []string{gc, gt} {
		info, err := os.Stat(path)
		if err != nil || !info.IsDir() {
			r.t.Fatalf("worker scratch unavailable: %q %v", path, err)
		}
		probe := filepath.Join(path, "write-probe")
		if err := os.WriteFile(probe, []byte("ok"), 0600); err != nil {
			r.t.Fatalf("worker scratch not writable: %q %v", path, err)
		}
	}
	if !strings.Contains(spec.Input, "Do not create build caches or temporary directories inside the worktree.") ||
		!strings.Contains(spec.Input, "do not override them") {
		r.t.Fatal("worker prompt does not preserve external Go scratch contract")
	}
	if !strings.Contains(spec.Input, "REPAIR CONTINUATION:") ||
		!strings.Contains(spec.Input, "PREVIOUS ATTEMPT DIAGNOSTICS") {
		r.t.Fatal("worker repair-continuation diagnostics contract was lost")
	}
	scratchPolicy := ""
	for i, arg := range spec.Args {
		if arg == "-c" && i+1 < len(spec.Args) && strings.HasPrefix(spec.Args[i+1], "sandbox_workspace_write.writable_roots=") {
			scratchPolicy = spec.Args[i+1]
			break
		}
	}
	if scratchPolicy == "" || !strings.Contains(scratchPolicy, fmt.Sprintf("%q", gc)) || !strings.Contains(scratchPolicy, fmt.Sprintf("%q", gt)) {
		r.t.Fatalf("worker scratch writable roots missing: policy=%q args=%v", scratchPolicy, spec.Args)
	}

	modelIndex := -1
	for i, arg := range spec.Args {
		if arg == "-m" {
			modelIndex = i
			break
		}
	}
	if modelIndex < 0 || modelIndex+1 >= len(spec.Args) || spec.Args[modelIndex+1] != codexWorkerModel {
		r.t.Fatalf("worker model pin lost: args=%v", spec.Args)
	}
	*r.gocache = gc
	*r.gotmp = gt
	return nil
}

func TestCodexWorkerGoScratchOutsideCandidateTree(t *testing.T) {
	workspace := t.TempDir()
	home := t.TempDir()
	var gocache, gotmp string
	runner := workerGoScratchCaptureRunner{
		t:         t,
		workspace: workspace,
		gocache:   &gocache,
		gotmp:     &gotmp,
	}
	adapter := CodexAdapter{
		Tool:     "codex",
		Home:     home,
		Runner:   runner,
		Feedback: "concrete prior diagnostic",
	}
	var stdout bytes.Buffer
	if err := adapter.Run(context.Background(), workspace, WorkOrder{}, &stdout, io.Discard); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(stdout.String(), "CKB_PLANE_CODEX_MODEL="+codexWorkerModel) {
		t.Fatalf("worker model evidence missing: %q", stdout.String())
	}
	for _, path := range []string{gocache, gotmp} {
		if path == "" {
			t.Fatal("worker scratch path not captured")
		}
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("worker scratch not cleaned up: %q %v", path, err)
		}
	}
	matches, err := filepath.Glob(filepath.Join(workspace, ".gocache*"))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 0 {
		t.Fatalf("candidate workspace polluted by Go cache: %v", matches)
	}
}
