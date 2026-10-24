package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestR2eProfileLoadAndWorkOrderNeutral(t *testing.T) {
	root := t.TempDir()
	profileDir := filepath.Join(root, "profiles")
	if err := os.Mkdir(profileDir, 0700); err != nil {
		t.Fatal(err)
	}
	repo := filepath.Join(root, "repo")
	codexHome := filepath.Join(root, "codex-home")
	if err := os.MkdirAll(repo, 0700); err != nil {
		t.Fatal(err)
	}
	writeProfileJSON(t, filepath.Join(profileDir, "toy.json"), DispatchProfile{
		ProfileName:                "toy",
		Mode:                       "toy-proof-profile",
		RepoPath:                   repo,
		WorkOrderID:                "TOY_CODEX_FIXTURE_R1",
		WorkerBranch:               "codex/toy-fixture-r1",
		RequiredBaselineRef:        "accepted/toy",
		RequiredBaselineSHA:        "6de24be52f773f674681930aaa9ca162bb0e2caf",
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{"TestMessage"},
		AllowedPaths:               []string{"toy.go"},
		ForbiddenPaths:             []string{"go.mod", "toy_test.go"},
		AcceptedRefsPolicy:         "toy proof only; no accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
		CodexProfilePath:           codexHome,
		ScrubDenylist:              []string{"config.toml", "skills", "plugins"},
		AllowSHAFallback:           true,
		FetchMissingRefAllowed:     false,
	})
	profile, err := LoadDispatchProfile(root, "toy")
	if err != nil {
		t.Fatal(err)
	}
	order, err := profile.WorkOrder()
	if err != nil {
		t.Fatal(err)
	}
	if order.Repo != "toy" || order.ID != "TOY_CODEX_FIXTURE_R1" || order.Worker.Branch != "codex/toy-fixture-r1" {
		t.Fatalf("profile did not drive work order: %#v", order)
	}
	if strings.Join(order.RequiredTests.FocusedGo, ",") != "^TestMessage$" {
		t.Fatal(order.RequiredTests.FocusedGo)
	}
	if !order.Allows("toy.go") || order.Allows("go.mod") {
		t.Fatal("profile path policy was not applied")
	}
}

func TestR2eReadonlyProfileCannotBecomeWorkOrder(t *testing.T) {
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
		FetchMissingRefAllowed:     true,
	}
	if err := profile.Validate(); err != nil {
		t.Fatal(err)
	}
	if _, err := profile.WorkOrder(); err == nil || !strings.Contains(err.Error(), "PROFILE_READONLY") {
		t.Fatalf("readonly profile became executable: %v", err)
	}
}

func TestR2eProfileScrubDenylist(t *testing.T) {
	home := t.TempDir()
	writeTestFile(t, filepath.Join(home, "auth.json"), "keep")
	writeTestFile(t, filepath.Join(home, "config.toml"), "remove")
	if err := os.Mkdir(filepath.Join(home, "skills"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(home, "plugins"), 0700); err != nil {
		t.Fatal(err)
	}
	ev, err := scrubCodexProfile(home, []string{"config.toml", "skills", "plugins"})
	if err != nil {
		t.Fatal(err)
	}
	if ev.Status != "SCRUBBED" || len(ev.PresentAfter) != 0 || len(ev.Removed) != 3 {
		t.Fatalf("bad scrub evidence: %#v", ev)
	}
	if _, err := os.Stat(filepath.Join(home, "auth.json")); err != nil {
		t.Fatal("auth material should not be removed")
	}
	for _, name := range []string{"config.toml", "skills", "plugins"} {
		if _, err := os.Lstat(filepath.Join(home, name)); !os.IsNotExist(err) {
			t.Fatalf("denylisted artifact remains: %s", name)
		}
	}
}

func TestR2eApplyProfileToEngineConfig(t *testing.T) {
	p := DispatchProfile{
		ProfileName:                "toy",
		Mode:                       "toy-proof-profile",
		RepoPath:                   filepath.Join(t.TempDir(), "repo"),
		WorkOrderID:                "TOY_CODEX_FIXTURE_R1",
		WorkerBranch:               "codex/toy-fixture-r1",
		RequiredBaselineRef:        "accepted/toy",
		RequiredBaselineSHA:        "6de24be52f773f674681930aaa9ca162bb0e2caf",
		AcceptanceAuthority:        "windows-source",
		FocusedTests:               []string{"^TestMessage$"},
		AllowedPaths:               []string{"toy.go"},
		ForbiddenPaths:             []string{"go.mod"},
		AcceptedRefsPolicy:         "toy proof only; no accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
		CodexProfilePath:           filepath.Join(t.TempDir(), "codex-home"),
	}
	c := Config{}
	c, err := ApplyDispatchProfile(c, p)
	if err != nil {
		t.Fatal(err)
	}
	if c.Profile.Name != "toy" || !c.Execution.Enabled || c.Execution.CodexHome != p.CodexProfilePath {
		t.Fatalf("profile not applied to config: %#v", c)
	}
	if got := c.Repos["toy"].LocalPath; got != p.RepoPath {
		t.Fatalf("repo path=%q want %q", got, p.RepoPath)
	}
}

func TestR2eProfilePreflightEvidenceShape(t *testing.T) {
	p, w := setup(t)
	profile := DispatchProfile{
		ProfileName:                w.Repo,
		Mode:                       "toy-proof-profile",
		RepoPath:                   p.Config.Repos[w.Repo].LocalPath,
		WorkOrderID:                w.ID,
		WorkerBranch:               "codex/toy-fixture-r1",
		RequiredBaselineRef:        w.Baseline.Ref,
		RequiredBaselineSHA:        w.Baseline.SHA,
		AcceptanceAuthority:        "demo",
		FocusedTests:               []string{"TestDemo"},
		AllowedPaths:               []string{"demo.txt"},
		ForbiddenPaths:             []string{},
		AcceptedRefsPolicy:         "toy proof only; no accepted CKB refs",
		RuntimeForbidden:           true,
		WorkerLaunchAllowed:        true,
		CandidateAcceptanceAllowed: true,
		CodexProfilePath:           filepath.Join(t.TempDir(), "codex-home"),
		AllowSHAFallback:           false,
		FetchMissingRefAllowed:     false,
	}
	ev, err := p.PreflightDispatchProfile(context.Background(), profile, filepath.Join(t.TempDir(), "r2e"))
	if err != nil {
		t.Fatal(err)
	}
	if ev.ProfileName != w.Repo || ev.Baseline.ResolvedSHA != w.Baseline.SHA || ev.Status != "DRY_DISPATCH_READY" || ev.EvidencePath == "" {
		t.Fatalf("bad profile evidence: %#v", ev)
	}
	if _, err := os.Stat(ev.EvidencePath); err != nil {
		t.Fatal(err)
	}
}

func writeProfileJSON(t *testing.T, path string, p DispatchProfile) {
	t.Helper()
	b, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, b, 0600); err != nil {
		t.Fatal(err)
	}
}
