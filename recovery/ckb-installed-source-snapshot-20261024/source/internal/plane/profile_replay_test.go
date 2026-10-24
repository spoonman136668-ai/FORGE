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

type r2fToyProcessRunner struct{}

func (r2fToyProcessRunner) Run(ctx context.Context, spec ProcessSpec, out, stderr io.Writer) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}
	path := filepath.Join(spec.Dir, "toy.go")
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	text := strings.Replace(string(b), `return "before"`, `return "after"`, 1)
	if text == string(b) {
		return os.ErrInvalid
	}
	if err := os.WriteFile(path, []byte(text), 0o600); err != nil {
		return err
	}
	for _, env := range spec.Env {
		if strings.HasPrefix(env, "CODEX_HOME=") {
			home := strings.TrimPrefix(env, "CODEX_HOME=")
			if home != "" {
				if err := os.WriteFile(filepath.Join(home, "config.toml"), []byte("# recreated by fake Codex during replay\n"), 0o600); err != nil {
					return err
				}
				if err := os.MkdirAll(filepath.Join(home, "skills"), 0o700); err != nil {
					return err
				}
			}
		}
	}
	_, _ = io.WriteString(out, "r2f fake codex runner changed toy.go\n")
	return nil
}

func TestR2fToyProfileReplayUsesSelectedProfile(t *testing.T) {
	if runtime.GOOS != "windows" || runtime.GOARCH != "amd64" {
		t.Skip("R2f profile replay acceptance is Windows-source authoritative")
	}
	realGo := realGoForAcceptanceTest(t)
	gitTool := r2fLookPath(t, "git")

	root := filepath.Join(t.TempDir(), "plane")
	retainWindowsFailureEvidence(t, root)
	repo := filepath.Join(t.TempDir(), "toy-repo")
	sha := initR2fToyRepo(t, gitTool, repo)
	profileDir := filepath.Join(root, "profiles")
	if err := os.MkdirAll(profileDir, 0o700); err != nil {
		t.Fatal(err)
	}
	codexHome := filepath.Join(root, "codex-home")
	if err := os.MkdirAll(codexHome, 0o700); err != nil {
		t.Fatal(err)
	}
	writeTestFile(t, filepath.Join(codexHome, "config.toml"), "remove me")
	writeProfileJSON(t, filepath.Join(profileDir, "toy.json"), DispatchProfile{
		ProfileName:                "toy",
		Mode:                       "toy-proof-profile",
		RepoPath:                   repo,
		WorkOrderID:                "TOY_CODEX_FIXTURE_R1",
		WorkOrderTitle:             "R2f toy fixture - change Message from before to after",
		WorkerBranch:               "codex/toy-fixture-r1",
		RequiredBaselineRef:        "accepted/toy",
		RequiredBaselineSHA:        sha,
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{"TestMessage"},
		AllowedPaths:               []string{"toy.go"},
		ForbiddenPaths:             []string{"go.mod", "toy_test.go"},
		AcceptedRefsPolicy:         "toy proof only; never create or move accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
		CodexProfilePath:           codexHome,
		ScrubDenylist:              []string{"config.toml", "skills", "plugins"},
		AllowSHAFallback:           true,
		FetchMissingRefAllowed:     false,
	})

	var c Config
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 8791
	c.State.SQLitePath = "state/r2f-test.db"
	c.Tools.Git = gitTool
	c.Tools.Go = realGo
	c.Tools.Codex = realGo
	c.Tools.Powershell = "powershell.exe"
	c.Policy.MaxAttempts = 3
	c.Execution.TimeoutSeconds = 120
	c.Profile.Name = "toy"
	p, err := NewEngine(c, root)
	if err != nil {
		t.Fatal(err)
	}
	defer p.Store.DB.Close()
	p.runner = r2fToyProcessRunner{}

	ev, err := p.ReplaySelectedProfile(context.Background(), filepath.Join(root, "artifacts", "r2f"))
	if err != nil {
		t.Fatalf("ReplaySelectedProfile failed: %v; evidence=%+v", err, ev)
	}
	if ev.ProfileName != "toy" || ev.WorkOrderID != "TOY_CODEX_FIXTURE_R1" || ev.FinalState != "ACCEPTED" || ev.Status != "ACCEPTED" {
		t.Fatalf("profile replay not accepted through toy profile: %+v", ev)
	}
	if ev.Preflight.WorkerLaunchAllowed != true || ev.Preflight.CandidateAcceptanceAllowed != true {
		t.Fatalf("profile policy not represented in preflight evidence: %+v", ev.Preflight)
	}
	if !ev.CandidateDiffOnlyToyGo || !ev.CandidateDiffBeforeAfter || !ev.FocusedTestMessagePass || !ev.AllTestMessagePass {
		t.Fatalf("missing deterministic toy evidence: %+v", ev)
	}
	if !ev.CodexDenylistCleanAfterReplay || ev.PostReplayScrub.Status != "SCRUBBED" {
		t.Fatalf("post-replay Codex profile scrub was not proven: %+v", ev.PostReplayScrub)
	}
	if !ev.AcceptanceInputUnchanged || !ev.AcceptedRefsUnchanged || !ev.AcceptedRefCheckPassed {
		t.Fatalf("acceptance/ref invariants not proven: %+v", ev)
	}
	if _, err := os.Lstat(filepath.Join(codexHome, "config.toml")); !os.IsNotExist(err) {
		t.Fatalf("codex profile scrub did not remove config.toml")
	}
	if _, err := os.Lstat(filepath.Join(codexHome, "skills")); !os.IsNotExist(err) {
		t.Fatalf("skills directory remained after post-replay scrub")
	}
	b, err := os.ReadFile(filepath.Join(repo, "toy.go"))
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(b), `return "after"`) {
		t.Fatal("source toy repository was modified")
	}
}

func TestR2fProfileReplayRefusesReadonlyProfilePolicy(t *testing.T) {
	profile := DispatchProfile{
		ProfileName:                "ckb-readonly",
		Mode:                       "readonly-baseline-verification",
		RepoPath:                   filepath.Join(t.TempDir(), "repo"),
		WorkOrderID:                "CKB_READONLY_BASELINE_VERIFY_R1",
		WorkerBranch:               "none-readonly",
		RequiredBaselineRef:        "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1",
		RequiredBaselineSHA:        "01260dda4bdebc454921cdf0c5d3d0eeafef7629",
		AcceptanceAuthority:        "windows-source",
		ForbiddenPaths:             []string{"**"},
		AcceptedRefsPolicy:         "never create, move, update, checkout, reset, or push accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        false,
		CandidateAcceptanceAllowed: false,
	}
	p := &Engine{Root: t.TempDir(), Profile: &profile}
	ev, err := p.ReplaySelectedProfile(context.Background(), filepath.Join(t.TempDir(), "r2f"))
	if err == nil || !strings.Contains(err.Error(), "PROFILE_REPLAY_FORBIDDEN") {
		t.Fatalf("readonly profile was not refused: err=%v ev=%+v", err, ev)
	}
}

func initR2fToyRepo(t *testing.T, gitTool, repo string) string {
	t.Helper()
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	r2fGit(t, gitTool, repo, "init")
	r2fGit(t, gitTool, repo, "config", "user.email", "r2f@example.invalid")
	r2fGit(t, gitTool, repo, "config", "user.name", "R2f Test")
	writeTestFile(t, filepath.Join(repo, "go.mod"), "module ckb-plane-codex-toy\n\ngo 1.25.5\n")
	writeTestFile(t, filepath.Join(repo, "toy.go"), "package toy\n\nfunc Message() string {\nreturn \"before\"\n}\n")
	writeTestFile(t, filepath.Join(repo, "toy_test.go"), "package toy\n\nimport \"testing\"\n\nfunc TestMessage(t *testing.T) {\n\tif Message() != \"after\" {\n\t\tt.Fatalf(\"bad message: %s\", Message())\n\t}\n}\n")
	r2fGit(t, gitTool, repo, "add", ".")
	r2fGit(t, gitTool, repo, "commit", "-m", "accepted toy baseline")
	sha := r2fGit(t, gitTool, repo, "rev-parse", "HEAD")
	r2fGit(t, gitTool, repo, "branch", "accepted/toy", sha)
	return sha
}

func r2fLookPath(t *testing.T, name string) string {
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

func r2fGit(t *testing.T, gitTool, dir string, args ...string) string {
	t.Helper()
	out, err := gitContext(context.Background(), gitTool, dir, args...)
	if err != nil {
		t.Fatalf("git %v failed: %v", args, err)
	}
	return strings.TrimSpace(out)
}
