package plane

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestR3cReadonlyWorkspaceMaterializeCreatesIsolatedBaselineWorktree(t *testing.T) {
	gitTool := r3bLookPath(t, "git")
	root := filepath.Join(t.TempDir(), "plane")
	repo := filepath.Join(t.TempDir(), "ckb-repo")
	sha := initR3bRepo(t, gitTool, repo)
	profileDir := filepath.Join(root, "profiles")
	if err := os.MkdirAll(profileDir, 0o700); err != nil {
		t.Fatal(err)
	}
	writeProfileJSON(t, filepath.Join(profileDir, "ckb-readonly.json"), DispatchProfile{
		ProfileName:                "ckb-readonly",
		Mode:                       "readonly-baseline-verification",
		RepoPath:                   repo,
		WorkOrderID:                "CKB_READONLY_BASELINE_VERIFY_R1",
		WorkerBranch:               "none-readonly",
		RequiredBaselineRef:        "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1",
		RequiredBaselineSHA:        sha,
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{},
		AllowedPaths:               []string{},
		ForbiddenPaths:             []string{"**", ".git/**"},
		AcceptedRefsPolicy:         "never create, move, update, checkout, reset, or push accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        false,
		CandidateAcceptanceAllowed: false,
		CodexProfilePath:           filepath.Join(root, "codex-home"),
		ScrubDenylist:              []string{"config.toml", "skills", "plugins"},
		AllowSHAFallback:           false,
		FetchMissingRefAllowed:     false,
	})

	var c Config
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 18084
	c.State.SQLitePath = "state/r3c-test.db"
	c.Tools.Git = gitTool
	c.Tools.Go = "go"
	c.Tools.Codex = "codex"
	c.Tools.Powershell = "powershell.exe"
	c.Policy.MaxAttempts = 1
	c.Execution.Enabled = false
	c.Profile.Name = "ckb-readonly"

	p, err := NewEngine(c, root)
	if err != nil {
		t.Fatal(err)
	}
	defer p.Store.DB.Close()

	beforeStatus := r3bGit(t, gitTool, repo, "status", "--porcelain=v1", "-uall")
	beforeRefs := r3bGit(t, gitTool, repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/accepted/", "refs/tags/accepted/", "refs/remotes/origin/accepted/")
	ev, err := p.MaterializeReadonlyWorkspaceSelectedProfile(context.Background(), filepath.Join(root, "artifacts", "r3c"))
	if err != nil {
		t.Fatalf("MaterializeReadonlyWorkspaceSelectedProfile failed: %v evidence=%+v", err, ev)
	}
	afterStatus := r3bGit(t, gitTool, repo, "status", "--porcelain=v1", "-uall")
	afterRefs := r3bGit(t, gitTool, repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/accepted/", "refs/tags/accepted/", "refs/remotes/origin/accepted/")
	if beforeStatus != afterStatus || beforeRefs != afterRefs {
		t.Fatalf("source repo changed: beforeStatus=%q afterStatus=%q beforeRefs=%q afterRefs=%q", beforeStatus, afterStatus, beforeRefs, afterRefs)
	}
	if ev.Status != "WORKSPACE_MATERIALIZED_READONLY" || ev.ProfileName != "ckb-readonly" {
		t.Fatalf("unexpected R3c status: %+v", ev)
	}
	if ev.Baseline.ResolvedSHA != sha || !ev.AcceptedRefsUnchanged || !ev.GitStatusUnchanged || !ev.HeadUnchanged || !ev.BranchUnchanged || !ev.BranchRefsUnchanged {
		t.Fatalf("repo invariants not proven: %+v", ev)
	}
	if !ev.Workspace.WorkspaceCreatedByR3c || !ev.Workspace.PrivateRepositoryCreatedByR3c || !ev.Workspace.PrivateWorktreeCreatedByR3c || !ev.Workspace.WorkspaceExists {
		t.Fatalf("workspace was not materialized: %+v", ev.Workspace)
	}
	if ev.Workspace.WorkspaceHead != sha || ev.Workspace.WorkspaceStatus != "" {
		t.Fatalf("workspace baseline/status invalid: %+v", ev.Workspace)
	}
	if ev.Workspace.PrivateRepositoryRemotes != "" || !ev.Workspace.PrivateRepositoryRemoteRemoved {
		t.Fatalf("private repository remote not removed: %+v", ev.Workspace)
	}
	if !ev.Workspace.WorkspaceInsidePlane || ev.Workspace.WorkspaceInsideSourceRepo || ev.Workspace.SourceRepoInsideWorkspace {
		t.Fatalf("source/workspace separation invalid: %+v", ev.Workspace)
	}
	if ev.WorkerLaunched || ev.CandidateAccepted || ev.RuntimeLaunched {
		t.Fatalf("materialization claimed forbidden execution: %+v", ev)
	}
	if ev.Workspace.SourceRepoMutationAllowed || ev.Workspace.AcceptedRefMutationAllowed || ev.Workspace.WorkerLaunchAllowed || ev.Workspace.CandidateAcceptanceAllowed || ev.Workspace.RuntimeLaunchAllowed || ev.Workspace.RemotePushAllowed {
		t.Fatalf("workspace policy allows forbidden operation: %+v", ev.Workspace)
	}
	if _, err := os.Stat(ev.Workspace.PrivateWorktreePath); err != nil {
		t.Fatalf("private worktree missing: %v", err)
	}
	if _, err := os.Stat(ev.Workspace.PrivateRepositoryPath); err != nil {
		t.Fatalf("private repository missing: %v", err)
	}
	if ev.EvidencePath == "" {
		t.Fatal("R3c evidence path was not recorded")
	}
	if _, err := os.Stat(ev.EvidencePath); err != nil {
		t.Fatalf("R3c evidence file missing: %v", err)
	}
}

func TestR3cWorkspaceMaterializeRefusesExecutableProfile(t *testing.T) {
	profile := DispatchProfile{
		ProfileName:                "toy",
		Mode:                       "toy-proof-profile",
		RepoPath:                   filepath.Join(t.TempDir(), "repo"),
		WorkOrderID:                "TOY_CODEX_FIXTURE_R1",
		WorkerBranch:               "codex/toy-fixture-r1",
		RequiredBaselineRef:        "accepted/toy",
		RequiredBaselineSHA:        "6de24be52f773f674681930aaa9ca162bb0e2caf",
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{"TestMessage"},
		AllowedPaths:               []string{"toy.go"},
		ForbiddenPaths:             []string{"go.mod"},
		AcceptedRefsPolicy:         "toy proof only; never create or move accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
	}
	p := &Engine{Root: t.TempDir(), Profile: &profile}
	ev, err := p.MaterializeReadonlyWorkspaceSelectedProfile(context.Background(), filepath.Join(t.TempDir(), "r3c"))
	if err == nil || !strings.Contains(err.Error(), "WORKSPACE_MATERIALIZE_FORBIDDEN") {
		t.Fatalf("executable profile was not refused: err=%v ev=%+v", err, ev)
	}
}
