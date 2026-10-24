package plane

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestDLSourcePrepareFailureKeepsExactBlockerAndEvidence(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DL_MATERIALIZATION_FAILURE")

	// Force prepare to fail after repository validation. This exercises the source
	// worker path that previously collapsed every materialization error into a
	// generic REPO_UNAVAILABLE blocker.
	originalPrepare := prepareWorkspace
	prepareWorkspace = func(context.Context, string, string, string, WorkOrder) (string, RepoState, error) {
		return "", RepoState{Baseline: w.Baseline.SHA, SourceRefs: "source refs captured"}, errors.New("forced worktree materialization failure")
	}
	defer func() { prepareWorkspace = originalPrepare }()

	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, q.ID)
	if j.State != "BLOCKED" {
		t.Fatal(j)
	}
	if !strings.HasPrefix(j.Reason, "WORKSPACE_MATERIALIZATION_FAILED:") {
		t.Fatalf("generic or missing blocker: %+v", j)
	}
	if strings.Contains(j.Reason, "REPO_UNAVAILABLE") {
		t.Fatalf("prepare failure collapsed to repo blocker: %s", j.Reason)
	}
	if strings.Contains(j.Workspace, q.ID) || !strings.Contains(j.Workspace, filepath.Join("workspaces", "s")) {
		t.Fatalf("workspace root is not short run-id path: %q", j.Workspace)
	}

	materializationPath := filepath.Join(j.Evidence, "materialization-error.json")
	b, e := os.ReadFile(materializationPath)
	if e != nil {
		t.Fatal(e)
	}
	var detail map[string]any
	if e = json.Unmarshal(b, &detail); e != nil {
		t.Fatal(e)
	}
	for _, key := range []string{"blocker", "underlying_error", "source_repo_path", "workspace_root", "private_repo_path", "worktree_path", "baseline_ref", "baseline_sha", "worker_branch", "attempt", "run_id"} {
		if _, ok := detail[key]; !ok {
			t.Fatalf("missing %s in %s", key, b)
		}
	}
	if detail["blocker"] != j.Reason {
		t.Fatalf("materialization blocker mismatch: %q != %q", detail["blocker"], j.Reason)
	}
	if strings.Contains(detail["workspace_root"].(string), q.ID) {
		t.Fatalf("long ID leaked into workspace root: %s", detail["workspace_root"])
	}

	var receiptPath string
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if e = p.Store.DB.QueryRow("SELECT receipt FROM queue_items WHERE id=?", q.ID).Scan(&receiptPath); e == nil && receiptPath != "" {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	if receiptPath == "" {
		t.Fatal("missing queue receipt for pre-worker blocker")
	}
	receiptBytes, e := os.ReadFile(receiptPath)
	if e != nil {
		t.Fatal(e)
	}
	var receipt QueueResult
	if e = json.Unmarshal(receiptBytes, &receipt); e != nil {
		t.Fatal(e)
	}
	if receipt.Blocker != j.Reason || receipt.Reason != j.Reason || receipt.WorkerLaunchAttempted || receipt.SourceHygieneRan || receipt.ProductionAccepted {
		t.Fatalf("receipt did not preserve exact pre-worker blocker: %s", receiptBytes)
	}
	if receipt.Workspace != j.Workspace || strings.Contains(receipt.Workspace, q.ID) {
		t.Fatalf("receipt workspace not preserved as short path: %s", receiptBytes)
	}
}

func TestDLRealMissingRepoKeyRemainsRepoUnavailable(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DL_MISSING_REPO_KEY")
	delete(p.Config.Repos, w.Repo)
	if e := p.AutonomyTick(context.Background()); e == nil || !strings.Contains(e.Error(), "REPO_UNAVAILABLE") {
		t.Fatalf("missing repo key should surface REPO_UNAVAILABLE: %v", e)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if j.State != "BLOCKED" || j.Reason != "REPO_UNAVAILABLE" {
		t.Fatalf("missing repo key should remain REPO_UNAVAILABLE: %+v", j)
	}
}
