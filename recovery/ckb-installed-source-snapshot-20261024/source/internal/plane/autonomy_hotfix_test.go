package plane

import (
	"bytes"
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type forbiddenAcceptanceWorker struct{ called bool }

func (w *forbiddenAcceptanceWorker) Run(context.Context, ProcessSpec, io.Writer, io.Writer) error {
	w.called = true
	return errors.New("worker must not execute acceptance")
}

func TestAcceptanceSupervisorDoesNotUseWorkerAdapter(t *testing.T) {
	p, _ := setup(t)
	fake := &forbiddenAcceptanceWorker{}
	p.runner = fake
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	var out bytes.Buffer
	j := Job{ID: "ACCEPTANCE_LANE", Attempt: 1}
	e = p.supervisedRunnerFor(j).Run(context.Background(), ProcessSpec{Program: exe, Args: []string{"__fixture-process", "echo"}, Input: "real acceptance child", Env: minimalEnv()}, &out, io.Discard)
	if e != nil || out.String() != "real acceptance child" || fake.called {
		t.Fatal(out.String(), e, fake.called)
	}
	var count int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=1", j.ID).Scan(&count); e != nil || count != 1 {
		t.Fatal(count, e)
	}
	if p.runnerFor(j) != fake {
		t.Fatal("worker adapter was not retained for worker execution")
	}
}

func TestProofWorkspaceKeepsGitMetadataCompact(t *testing.T) {
	p, q, _ := proofFixture(t)
	result, e := p.QueueRun(context.Background(), q.ID, "test", "controlled-proof", false)
	if e != nil {
		t.Fatal(e)
	}
	relative, e := filepath.Rel(p.Root, result.Workspace)
	if e != nil {
		t.Fatal(e)
	}
	parts := strings.Split(filepath.ToSlash(relative), "/")
	if len(parts) != 4 || parts[0] != "workspaces" || parts[1] != "q" || parts[2] != result.RunID || parts[3] != "worktree" {
		t.Fatal(relative)
	}
	branch, e := git(p.Config.Tools.Git, result.Workspace, "symbolic-ref", "--short", "HEAD")
	if e != nil || branch != "codex/plane-proof" {
		t.Fatal(branch, e)
	}
	// The reported Windows fixture root previously generated a 264-character
	// Git branch lock filename; preserve headroom without modifying global Git.
	windowsRoot := `C:\Users\camar\AppData\Local\Temp\TestAutonomyProofMaterializesExactBaselinecontrolled-proof1683493773\001\plane`
	path := windowsRoot + `\workspaces\q\` + result.RunID + `\repository\.git\refs\heads\` + strings.ReplaceAll(branch, "/", `\`) + ".lock"
	if len(path) >= 240 {
		t.Fatal("Git metadata path no longer has Windows headroom", len(path))
	}
}

func TestGitErrorsRetainBoundedLocalDiagnostics(t *testing.T) {
	tool := "git"
	_, e := git(tool, t.TempDir(), "rev-parse", "--verify", "HEAD")
	var failure *gitCommandError
	if !errors.As(e, &failure) || failure.operation != "rev-parse" || failure.output == "" || len(failure.output) > 4096 {
		t.Fatal(e)
	}
	if strings.Contains(e.Error(), failure.output) {
		t.Fatal("raw Git output leaked into ordinary status")
	}
	// Native configuration is command-scoped and never written to either clone.
	value, e := git(tool, t.TempDir(), "config", "--get", "core.longpaths")
	if e != nil || value != "true" {
		t.Fatal(value, e)
	}
}

func retainWindowsFailureEvidence(t *testing.T, root string) {
	t.Helper()
	t.Cleanup(func() {
		if !t.Failed() {
			return
		}
		destination := os.Getenv("CKB_PLANE_TEST_EVIDENCE_ROOT")
		if destination == "" || !filepath.IsAbs(destination) {
			return
		}
		destination = filepath.Join(destination, digest([]byte(t.Name()))[:16])
		wanted := map[string]bool{"status.json": true, "materialization-error.json": true, "queue-result.json": true, "go-focused-0.jsonl": true, "go-focused-0.jsonl.stderr.log": true, "go-focused-0.jsonl.launch.json": true, "go-all.jsonl": true, "go-all.jsonl.stderr.log": true, "go-all.jsonl.launch.json": true, "acceptance_checks.json": true, "acceptance_result.json": true}
		copied := 0
		for _, dir := range []string{"evidence", "artifacts"} {
			_ = filepath.Walk(filepath.Join(root, dir), func(path string, info os.FileInfo, err error) error {
				if err != nil || !info.Mode().IsRegular() || !wanted[info.Name()] || info.Size() > 16<<20 {
					return nil
				}
				relative, e := filepath.Rel(root, path)
				if e != nil {
					return nil
				}
				target := filepath.Join(destination, relative)
				data, e := os.ReadFile(path)
				if e != nil {
					return nil
				}
				if e = os.MkdirAll(filepath.Dir(target), 0700); e != nil {
					return nil
				}
				if e = os.WriteFile(target, data, 0600); e == nil {
					copied++
				}
				return nil
			})
		}
		if copied > 0 {
			t.Logf("Current failed-fixture diagnostics retained: %s (%d files)", destination, copied)
		}
	})
}
