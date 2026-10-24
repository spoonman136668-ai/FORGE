package plane

import (
	"context"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestDULocalCandidateBaselineRefValidation(t *testing.T) {
	_, w := setup(t)
	w.Baseline.Ref = "local-candidate/PARENT_STAGE"
	if e := w.Validate(); e != nil {
		t.Fatalf("valid local candidate baseline rejected: %v", e)
	}
	w.Baseline.Ref = "local-candidate/../escape"
	if e := w.Validate(); e == nil {
		t.Fatal("unsafe local candidate baseline accepted")
	}
}

func TestDULocalCandidateBaselineImportsVerifiedExportWithoutAcceptedRefMutation(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)

	// Produce and deterministically accept a parent candidate using the normal
	// DemoInit fake-worker path while the synthetic repository remains mode=demo.
	sourceQueue(t, p, w, "DU_PARENT")
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	parent := wait(t, p, "DU_PARENT")
	if parent.State != "ACCEPTED" {
		t.Fatalf("parent not accepted: %+v", parent)
	}
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}

	exported, e := p.ExportCandidateOffline(context.Background(), "DU_PARENT")
	if e != nil {
		t.Fatal(e)
	}
	candidateSHA, _ := exported["candidate_sha"].(string)
	if candidateSHA == "" {
		t.Fatal("missing exported candidate sha")
	}

	// DU imports sealed local candidates only into engineering repositories.
	// Make that configuration change before child authorization so the immutable
	// authorization contract records the exact production configuration that
	// Ready() will verify.
	repo := p.Config.Repos[w.Repo]
	repo.Mode = "engineering"
	p.Config.Repos[w.Repo] = repo

	acceptedBefore, e := refs(p.Config.Tools.Git, repo.LocalPath)
	if e != nil {
		t.Fatal(e)
	}

	child := w
	child.ID = "DU_CHILD"
	child.Worker.Branch = "codex/du_child"
	child.Baseline.Ref = "local-candidate/DU_PARENT"
	child.Baseline.SHA = candidateSHA

	// Do not use the legacy load() test helper here: it calls Store.Authorize()
	// and intentionally relies on the demo/fake authorization exception. This
	// fixture is proving the engineering path, so record the real immutable
	// Engine.Authorize() contract after the repo is already mode=engineering.
	childYAML, e := yaml.Marshal(child)
	if e != nil {
		t.Fatal(e)
	}
	if e = p.Store.Load(childYAML); e != nil {
		t.Fatal(e)
	}
	if e = p.Authorize(child.ID); e != nil {
		t.Fatal(e)
	}
	if e = p.Ready(child.ID); e != nil {
		t.Fatal(e)
	}

	got, e := p.Store.Get("DU_CHILD")
	if e != nil {
		t.Fatal(e)
	}
	if got.State != "READY" {
		t.Fatalf("child not ready from local candidate baseline: %+v", got)
	}

	localRef, e := git(p.Config.Tools.Git, repo.LocalPath, "rev-parse", "--verify", "refs/ckb-plane/candidates/DU_PARENT^{commit}")
	if e != nil || localRef != candidateSHA {
		t.Fatalf("local candidate ref mismatch: %q %v", localRef, e)
	}
	acceptedAfter, e := refs(p.Config.Tools.Git, repo.LocalPath)
	if e != nil || acceptedAfter != acceptedBefore {
		t.Fatal("accepted refs changed during local candidate import", e)
	}
	status, e := git(p.Config.Tools.Git, repo.LocalPath, "status", "--porcelain")
	if e != nil || status != "" {
		t.Fatalf("source working tree changed: %q %v", status, e)
	}
}

func TestDULocalCandidateBaselineRejectsUnacceptedParent(t *testing.T) {
	p, w := setup(t)
	w.ID = "DU_DRAFT_PARENT"
	if e := p.Store.Load(mustYAMLForDUTest(t, w)); e != nil {
		t.Fatal(e)
	}
	child := w
	child.ID = "DU_CHILD"
	child.Baseline.Ref = "local-candidate/DU_DRAFT_PARENT"
	if e := p.ensureLocalCandidateBaseline(context.Background(), child); e == nil || e.Error() != "LOCAL_CANDIDATE_ACCEPTANCE_REQUIRED" {
		t.Fatalf("unexpected result: %v", e)
	}
}

func mustYAMLForDUTest(t *testing.T, w WorkOrder) []byte {
	t.Helper()
	b, e := yaml.Marshal(w)
	if e != nil {
		t.Fatal(e)
	}
	return b
}
