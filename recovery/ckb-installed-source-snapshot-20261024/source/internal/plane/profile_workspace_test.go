package plane

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestR3bReadonlyWorkspaceDryRunPlanIsNonMutating(t *testing.T) {
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
	// NewEngine validates that the server bind is loopback even for non-serving dry-run tests.
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 18083
	c.State.SQLitePath = "state/r3b-test.db"
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

	before := r3bGit(t, gitTool, repo, "status", "--porcelain=v1", "-uall")
	ev, err := p.WorkspaceDryRunSelectedProfile(context.Background(), filepath.Join(root, "artifacts", "r3b"))
	if err != nil {
		t.Fatalf("WorkspaceDryRunSelectedProfile failed: %v evidence=%+v", err, ev)
	}
	after := r3bGit(t, gitTool, repo, "status", "--porcelain=v1", "-uall")
	if before != after || after != "" {
		t.Fatalf("source repo status changed: before=%q after=%q", before, after)
	}
	if ev.Status != "WORKSPACE_DRY_RUN_READY" || ev.ProfileName != "ckb-readonly" {
		t.Fatalf("unexpected R3b status: %+v", ev)
	}
	if ev.Baseline.ResolvedSHA != sha || !ev.AcceptedRefsUnchanged || !ev.GitStatusUnchanged || !ev.HeadUnchanged || !ev.BranchUnchanged || !ev.BranchRefsUnchanged {
		t.Fatalf("repo invariants not proven: %+v", ev)
	}
	if ev.WorkerLaunched || ev.CandidateAccepted || ev.RuntimeLaunched {
		t.Fatalf("dry run claimed forbidden execution: %+v", ev)
	}
	if ev.WorkspacePlan.WorkspaceCreatedByR3b || ev.WorkspacePlan.PrivateCloneCreatedByR3b || ev.WorkspacePlan.PrivateWorktreeCreatedByR3b {
		t.Fatalf("workspace dry run created workspace: %+v", ev.WorkspacePlan)
	}
	if ev.WorkspacePlan.SourceRepoMutationAllowed || ev.WorkspacePlan.AcceptedRefMutationAllowed || ev.WorkspacePlan.WorkerLaunchAllowed || ev.WorkspacePlan.CandidateAcceptanceAllowed || ev.WorkspacePlan.RuntimeLaunchAllowed || ev.WorkspacePlan.RemotePushAllowed {
		t.Fatalf("workspace plan allows forbidden operation: %+v", ev.WorkspacePlan)
	}
	if _, err := os.Lstat(ev.WorkspacePlan.WorkspaceRoot); !os.IsNotExist(err) {
		t.Fatalf("workspace plan path exists after dry run: %s", ev.WorkspacePlan.WorkspaceRoot)
	}
	if ev.EvidencePath == "" {
		t.Fatal("R3b evidence path was not recorded")
	}
	if _, err := os.Stat(ev.EvidencePath); err != nil {
		t.Fatalf("R3b evidence file missing: %v", err)
	}
}

func TestR3bWorkspaceDryRunRefusesExecutableProfile(t *testing.T) {
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
	ev, err := p.WorkspaceDryRunSelectedProfile(context.Background(), filepath.Join(t.TempDir(), "r3b"))
	if err == nil || !strings.Contains(err.Error(), "WORKSPACE_DRY_RUN_FORBIDDEN") {
		t.Fatalf("executable profile was not refused: err=%v ev=%+v", err, ev)
	}
}

func initR3bRepo(t *testing.T, gitTool, repo string) string {
	t.Helper()
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	r3bGit(t, gitTool, repo, "init")
	r3bGit(t, gitTool, repo, "config", "user.email", "r3b@example.invalid")
	r3bGit(t, gitTool, repo, "config", "user.name", "R3b Test")
	writeTestFile(t, filepath.Join(repo, "go.mod"), "module ckb-readonly-r3b\n\ngo 1.25.5\n")
	writeTestFile(t, filepath.Join(repo, "README.md"), "# R3b fixture\n")
	r3bGit(t, gitTool, repo, "add", ".")
	r3bGit(t, gitTool, repo, "commit", "-m", "accepted CKB readonly baseline")
	sha := r3bGit(t, gitTool, repo, "rev-parse", "HEAD")
	r3bGit(t, gitTool, repo, "branch", "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1", sha)
	return sha
}

func r3bLookPath(t *testing.T, name string) string {
	t.Helper()
	path, err := exec.LookPath(name)
	if err != nil {
		t.Skipf("%s not available: %v", name, err)
	}
	if !filepath.IsAbs(path) {
		abs, err := filepath.Abs(path)
		if err == nil {
			path = abs
		}
	}
	return path
}

func r3bGit(t *testing.T, gitTool, dir string, args ...string) string {
	t.Helper()
	out, err := gitContext(context.Background(), gitTool, dir, args...)
	if err != nil {
		t.Fatalf("git %v failed: %v", args, err)
	}
	return strings.TrimSpace(out)
}
