package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoopHardening_DirtySourceWorkingTreeDoesNotBlockExactBaseline(t *testing.T) {
	p, w := setup(t)
	r := p.Config.Repos[w.Repo]
	dirty := filepath.Join(r.LocalPath, "operator-local-untracked.txt")
	if e := os.WriteFile(dirty, []byte("must never enter worker workspace\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := checkRepo(p.Config.Tools.Git, r, w); e != nil {
		t.Fatalf("irrelevant source working-tree dirt blocked exact-baseline materialization: %v", e)
	}
	root := filepath.Join(t.TempDir(), "attempt")
	work, before, e := prepareWorkspace(context.Background(), p.Config.Tools.Git, r.LocalPath, root, w)
	if e != nil {
		t.Fatal(e)
	}
	if before.Head != w.Baseline.SHA || before.Status != "" {
		t.Fatalf("materialized workspace is not the clean pinned baseline: %+v", before)
	}
	if _, e = os.Stat(filepath.Join(work, filepath.Base(dirty))); !os.IsNotExist(e) {
		t.Fatal("source working-tree dirt contaminated isolated worker workspace")
	}
}

func TestLoopHardening_SourceWorkerBranchDoesNotContaminateExactBaseline(t *testing.T) {
	p, w := setup(t)
	r := p.Config.Repos[w.Repo]
	if _, e := git(p.Config.Tools.Git, r.LocalPath, "checkout", "-b", w.Worker.Branch, w.Baseline.SHA); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(r.LocalPath, "branch-only.txt"), []byte("must stay out of worker workspace\n"), 0600); e != nil {
		t.Fatal(e)
	}
	for _, args := range [][]string{{"add", "branch-only.txt"}, {"-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "source branch divergence"}} {
		if _, e := git(p.Config.Tools.Git, r.LocalPath, args...); e != nil {
			t.Fatal(e)
		}
	}
	if e := checkRepo(p.Config.Tools.Git, r, w); e != nil {
		t.Fatalf("irrelevant source branch state blocked pinned-baseline materialization: %v", e)
	}
	root := filepath.Join(t.TempDir(), "attempt")
	work, before, e := prepareWorkspace(context.Background(), p.Config.Tools.Git, r.LocalPath, root, w)
	if e != nil {
		t.Fatal(e)
	}
	if before.Head != w.Baseline.SHA {
		t.Fatalf("got materialized head %s want %s", before.Head, w.Baseline.SHA)
	}
	if _, e = os.Stat(filepath.Join(work, "branch-only.txt")); !os.IsNotExist(e) {
		t.Fatal("source worker branch contaminated exact-baseline workspace")
	}
}

func TestLoopHardening_PreWorkerLeaseDoesNotConsumeWorkerBudget(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 1
	load(t, p, w)

	first, e := p.Store.Lease(w.ID, "fake", p.Config.Policy.MaxAttempts)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("DELETE FROM worker_leases WHERE work_order_id=?", w.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='READY' WHERE id=?", w.ID); e != nil {
		t.Fatal(e)
	}
	second, e := p.Store.Lease(w.ID, "fake", p.Config.Policy.MaxAttempts)
	if e != nil {
		t.Fatalf("pre-worker lease consumed model retry budget: first=%d err=%v", first, e)
	}
	if second != first+1 {
		t.Fatalf("attempt sequence did not remain monotonic: first=%d second=%d", first, second)
	}

	if _, e = p.Store.DB.Exec("INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES(?,?,?,'WORKER_LAUNCH_ATTEMPTED','INFO','test launch','{}')", now(), w.ID, second); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("DELETE FROM worker_leases WHERE work_order_id=?", w.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='READY',reason='Baseline verified; awaiting dispatch' WHERE id=?", w.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.Lease(w.ID, "fake", p.Config.Policy.MaxAttempts); e == nil || !strings.Contains(e.Error(), "RETRY_LIMIT_REACHED") {
		t.Fatalf("actual worker launch did not consume retry budget: %v", e)
	}
}

func TestLoopHardening_BaselineBrowserContractFailsBeforeWorkerLease(t *testing.T) {
	p, w := setup(t)
	r := p.Config.Repos[w.Repo]
	if e := os.MkdirAll(filepath.Join(r.LocalPath, "web"), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(r.LocalPath, "web", "index.html"), []byte("<!doctype html><div id=present></div>\n"), 0600); e != nil {
		t.Fatal(e)
	}
	for _, args := range [][]string{{"add", "web/index.html"}, {"-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "browser baseline"}} {
		if _, e := git(p.Config.Tools.Git, r.LocalPath, args...); e != nil {
			t.Fatal(e)
		}
	}
	head, e := git(p.Config.Tools.Git, r.LocalPath, "rev-parse", "HEAD")
	if e != nil {
		t.Fatal(e)
	}
	w.Baseline.SHA = head
	w.RequiredPaths = nil
	w.Preserve = nil
	w.Acceptance.Browser = true
	w.UI.Root = "web"
	w.UI.Pages = []UIPage{{Path: "index.html", CriticalIDs: []string{"missingControl"}}}
	w.UI.Markers = nil
	if e = p.validateBaselineAcceptanceContract(r, w); e == nil || !strings.Contains(e.Error(), "BROWSER_CRITICAL_CONTROL") {
		t.Fatalf("stale browser critical control was not rejected in baseline preflight: %v", e)
	}
}

func TestLoopHardening_RequiredPathMayBeCreatedByWorker(t *testing.T) {
	p, w := setup(t)
	r := p.Config.Repos[w.Repo]
	head, e := git(p.Config.Tools.Git, r.LocalPath, "rev-parse", "HEAD")
	if e != nil {
		t.Fatal(e)
	}
	w.Baseline.SHA = head
	w.RequiredPaths = []string{"definitely/missing.go"}
	w.Preserve = nil
	w.Acceptance.Browser = false
	if e = p.validateBaselineAcceptanceContract(r, w); e != nil {
		t.Fatalf("worker-created required path was incorrectly required in baseline: %v", e)
	}
}

func TestLoopHardening_NativeStatusShowsActualWorkerBudget(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 3
	load(t, p, w)
	if _, e := p.Store.DB.Exec("INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES(?,?,1,'WORKER_LAUNCH_ATTEMPTED','INFO','test launch','{}')", now(), w.ID); e != nil {
		t.Fatal(e)
	}
	status, e := p.AutonomyStatus()
	if e != nil {
		t.Fatal(e)
	}
	raw, e := json.Marshal(status)
	if e != nil {
		t.Fatal(e)
	}
	var decoded struct {
		Jobs []struct {
			ID                     string `json:"id"`
			Attempt                int    `json:"attempt"`
			WorkerLaunches         int    `json:"worker_launches"`
			AttemptBudget          int    `json:"attempt_budget"`
			AttemptBudgetRemaining int    `json:"attempt_budget_remaining"`
			Workspace              string `json:"workspace"`
			Evidence               string `json:"evidence"`
			LastEvent              string `json:"last_event"`
		} `json:"jobs"`
	}
	if e = json.Unmarshal(raw, &decoded); e != nil {
		t.Fatal(e)
	}
	if len(decoded.Jobs) != 1 {
		t.Fatalf("jobs=%d raw=%s", len(decoded.Jobs), string(raw))
	}
	j := decoded.Jobs[0]
	if j.ID != w.ID || j.WorkerLaunches != 1 || j.AttemptBudget != 3 || j.AttemptBudgetRemaining != 2 || j.LastEvent != "WORKER_LAUNCH_ATTEMPTED" {
		t.Fatalf("unexpected native attempt visibility: %+v", j)
	}
}
