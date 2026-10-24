package plane

import (
	"context"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

type r4aProofRunner struct{}

func (r4aProofRunner) Run(ctx context.Context, spec ProcessSpec, out, stderr io.Writer) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}
	doc := filepath.Join(spec.Dir, filepath.FromSlash(r4aDocPath))
	if err := os.MkdirAll(filepath.Dir(doc), 0o700); err != nil {
		return err
	}
	if err := os.WriteFile(doc, []byte("# CKB Plane R4a Source-Only Worker Proof\n\nMarker: CKB_R4A_SOURCE_ONLY_WORKER_PROOF_R1\n\nThis file proves an isolated worker can create a source-only candidate without touching runtime systems.\n"), 0o600); err != nil {
		return err
	}
	testFile := filepath.Join(spec.Dir, filepath.FromSlash(r4aTestPath))
	if err := os.MkdirAll(filepath.Dir(testFile), 0o700); err != nil {
		return err
	}
	content := `package pkg

import "testing"

func TestR4aSourceOnlyWorkerProofMarker(t *testing.T) {
	const marker = "CKB_R4A_SOURCE_ONLY_WORKER_PROOF_R1"
	if marker == "" {
		t.Fatal("missing R4a marker")
	}
}
`
	if err := os.WriteFile(testFile, []byte(content), 0o600); err != nil {
		return err
	}
	_, _ = io.WriteString(out, "r4a fake codex runner wrote docs marker and pkg test\n")
	return nil
}

func TestR4aSourceOnlyWorkerProofUsesIsolatedWorkspaceAndFocusedGate(t *testing.T) {
	if runtime.GOOS != "windows" || runtime.GOARCH != "amd64" {
		t.Skip("R4a worker proof acceptance is Windows-source authoritative")
	}
	realGo := realGoForAcceptanceTest(t)
	gitTool := r4aLookPath(t, "git")

	root := filepath.Join(t.TempDir(), "plane")
	retainWindowsFailureEvidence(t, root)
	repo := filepath.Join(t.TempDir(), "ckb-repo")
	sha := initR4aSourceRepo(t, gitTool, repo)
	profileDir := filepath.Join(root, "profiles")
	if err := os.MkdirAll(profileDir, 0o700); err != nil {
		t.Fatal(err)
	}
	codexHome := filepath.Join(root, "codex-home")
	if err := os.MkdirAll(codexHome, 0o700); err != nil {
		t.Fatal(err)
	}
	writeTestFile(t, filepath.Join(codexHome, "config.toml"), "remove me")
	runAll := false
	writeProfileJSON(t, filepath.Join(profileDir, r4aProfileName+".json"), DispatchProfile{
		ProfileName:                r4aProfileName,
		Mode:                       r4aProfileMode,
		RepoPath:                   repo,
		WorkOrderID:                r4aWorkOrderID,
		WorkOrderTitle:             "R4a source-only worker proof test",
		Instructions:               []string{"create marker doc", "create focused test only"},
		WorkerBranch:               "codex/r4a-source-only-worker-proof-r1",
		RequiredBaselineRef:        r4aBaselineRef,
		RequiredBaselineSHA:        sha,
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{r4aFocusedTest},
		RunGoTestAll:               &runAll,
		GoPackages:                 []string{"./pkg"},
		AllowedPaths:               []string{r4aDocPath, r4aTestPath},
		ForbiddenPaths:             []string{".git/**", "runtime/**", "**/*credential*", "**/*secret*", "**/*broker*", "**/*coinbase*"},
		AcceptedRefsPolicy:         "never create, move, update, checkout, reset, or push accepted CKB refs during R4a",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
		CodexProfilePath:           codexHome,
		ScrubDenylist:              []string{"config.toml", "skills", "plugins"},
		AllowSHAFallback:           false,
		FetchMissingRefAllowed:     false,
	})

	var c Config
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 18084
	c.State.SQLitePath = "state/r4a-test.db"
	c.Tools.Git = gitTool
	c.Tools.Go = realGo
	c.Tools.Codex = realGo
	c.Tools.Powershell = "powershell.exe"
	c.Policy.MaxAttempts = 3
	c.Execution.TimeoutSeconds = 120
	c.Profile.Name = r4aProfileName
	p, err := NewEngine(c, root)
	if err != nil {
		t.Fatal(err)
	}
	defer p.Store.DB.Close()
	p.runner = r4aProofRunner{}
	oldR4aStrictBaseline := r4aRequireExactBQBaseline
	r4aRequireExactBQBaseline = false
	defer func() { r4aRequireExactBQBaseline = oldR4aStrictBaseline }()
	ev, err := p.WorkerProofSelectedProfile(context.Background(), filepath.Join(root, "artifacts", "r4a"))
	if err != nil {
		t.Fatalf("WorkerProofSelectedProfile failed: %v; evidence=%+v", err, ev)
	}
	if ev.Status != "ACCEPTED" || ev.FinalState != "ACCEPTED" || ev.WorkOrderID != r4aWorkOrderID {
		t.Fatalf("R4a proof not accepted: %+v", ev)
	}
	if !ev.WorkerLaunched || !ev.CandidateAccepted || ev.RuntimeLaunched || ev.DeploymentRan || ev.AcceptedRefPromotionRan {
		t.Fatalf("unexpected execution flags: %+v", ev)
	}
	if !ev.DiffTouchesOnlyAllowlist || !ev.RequiredFilesPresent || !ev.MarkerContentPresent || !ev.FocusedTestPassed {
		t.Fatalf("missing R4a deterministic evidence: %+v", ev)
	}
	if !ev.SourceStatusUnchanged || !ev.SourceHeadUnchanged || !ev.SourceBranchUnchanged || !ev.AcceptedRefsUnchanged || !ev.BranchRefsUnchanged {
		t.Fatalf("source repo mutation detected: %+v", ev)
	}
	if !ev.WorkspaceInsidePlane || ev.WorkspaceInsideSourceRepo || ev.SourceRepoInsideWorkspace {
		t.Fatalf("workspace isolation failed: %+v", ev)
	}
	if _, err := os.Lstat(filepath.Join(codexHome, "config.toml")); !os.IsNotExist(err) {
		t.Fatalf("codex profile scrub did not remove config.toml")
	}
	if _, err := os.Lstat(filepath.Join(repo, filepath.FromSlash(r4aDocPath))); !os.IsNotExist(err) {
		t.Fatal("source CKB repo was modified with R4a doc")
	}
	if _, err := os.Lstat(filepath.Join(repo, filepath.FromSlash(r4aTestPath))); !os.IsNotExist(err) {
		t.Fatal("source CKB repo was modified with R4a test")
	}
}

func TestR4aWorkerProofRefusesReadonlyProfile(t *testing.T) {
	profile := DispatchProfile{
		ProfileName:                "ckb-readonly",
		Mode:                       "readonly-baseline-verification",
		RepoPath:                   filepath.Join(t.TempDir(), "repo"),
		WorkOrderID:                "CKB_READONLY_BASELINE_VERIFY_R1",
		WorkerBranch:               "none-readonly",
		RequiredBaselineRef:        r4aBaselineRef,
		RequiredBaselineSHA:        r4aBaselineSHA,
		AcceptanceAuthority:        "windows-source",
		ForbiddenPaths:             []string{"**"},
		AcceptedRefsPolicy:         "never create, move, update, checkout, reset, or push accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        false,
		CandidateAcceptanceAllowed: false,
	}
	p := &Engine{Root: t.TempDir(), Profile: &profile}
	ev, err := p.WorkerProofSelectedProfile(context.Background(), filepath.Join(t.TempDir(), "r4a"))
	if err == nil || !strings.Contains(err.Error(), "PROFILE_WORKER_PROOF_FORBIDDEN") {
		t.Fatalf("readonly profile was not refused: err=%v ev=%+v", err, ev)
	}
}

func initR4aSourceRepo(t *testing.T, gitTool, repo string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Join(repo, "pkg"), 0o700); err != nil {
		t.Fatal(err)
	}
	r4aGit(t, gitTool, repo, "init")
	r4aGit(t, gitTool, repo, "config", "user.email", "r4a@example.invalid")
	r4aGit(t, gitTool, repo, "config", "user.name", "R4a Test")
	writeTestFile(t, filepath.Join(repo, "go.mod"), "module ckb-r4a-fixture\n\ngo 1.25.5\n")
	writeTestFile(t, filepath.Join(repo, "pkg", "base.go"), "package pkg\n\nfunc Base() string { return \"base\" }\n")
	writeTestFile(t, filepath.Join(repo, "pkg", "base_test.go"), "package pkg\n\nimport \"testing\"\n\nfunc TestBase(t *testing.T) { if Base() != \"base\" { t.Fatal(Base()) } }\n")
	r4aGit(t, gitTool, repo, "add", ".")
	r4aGit(t, gitTool, repo, "commit", "-m", "accepted r4a baseline")
	sha := r4aGit(t, gitTool, repo, "rev-parse", "HEAD")
	r4aGit(t, gitTool, repo, "branch", r4aBaselineRef, sha)
	return sha
}

func r4aLookPath(t *testing.T, name string) string {
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

func r4aGit(t *testing.T, gitTool, dir string, args ...string) string {
	t.Helper()
	out, err := gitContext(context.Background(), gitTool, dir, args...)
	if err != nil {
		t.Fatalf("git %v failed: %v", args, err)
	}
	return strings.TrimSpace(out)
}
