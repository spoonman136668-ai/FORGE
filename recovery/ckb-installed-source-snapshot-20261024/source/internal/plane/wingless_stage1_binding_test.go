package plane

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func winglessStage1Fixture(t *testing.T) (WorkOrder, string, string) {
	t.Helper()
	workspace := filepath.Clean(t.TempDir())
	productionPath := "internal/plane/stage1_fixture.go"
	target := filepath.Join(workspace, filepath.FromSlash(productionPath))
	if err := os.MkdirAll(filepath.Dir(target), 0700); err != nil {
		t.Fatal(err)
	}
	const source = "package plane\n\nfunc stage1Fixture() {}\n"
	if err := os.WriteFile(target, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}

	var order WorkOrder
	order.ID = "WINGLESS_STAGE1_R1"
	order.Repo = "fixture"
	order.Title = "Inactive Wingless Stage-1 binding proof"
	order.Baseline.Ref = "accepted/fixture"
	order.Baseline.SHA = strings.Repeat("a", 40)
	order.Worker.Branch = "codex/wingless-stage1-r1"
	order.Worker.Preferred = "codex"
	order.Scope.Allowed = []string{productionPath}
	order.Acceptance.ProtectRefs = true
	order.Acceptance.Clean = true
	return order, workspace, source
}

func TestWinglessStage1BindingAcceptsSealedSource(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if binding.SourceCommit != WinglessStage1FrozenSource || binding.WorkOrderID != order.ID || binding.Workspace != workspace || binding.BaselineSHA != order.Baseline.SHA {
		t.Fatal(binding)
	}
}

func TestWinglessStage1BindingRejectsSourceIdentityMismatch(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	if _, err := NewWinglessStage1Binding(strings.Repeat("b", 40), order, 1, workspace); err == nil {
		t.Fatal("source mismatch accepted")
	}
}

func TestWinglessStage1BindingComputesExactCurrentFileSHA256(t *testing.T) {
	order, workspace, source := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	h := sha256.Sum256([]byte(source))
	want := hex.EncodeToString(h[:])
	if binding.BeforeSHA256 != want {
		t.Fatalf("before sha got=%s want=%s", binding.BeforeSHA256, want)
	}
}

func TestWinglessStage1BindingUsesPlaneIdentity(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 7, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if binding.WorkOrderID != order.ID || binding.Attempt != 7 || binding.Workspace != workspace || binding.BaselineSHA != order.Baseline.SHA || binding.WorkOrderDigest != digest([]byte(jsonText(order))) {
		t.Fatal(binding)
	}
}

func TestWinglessStage1BindingRequiresExactlyOneProductionPath(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	order.Scope.Allowed = []string{"internal/plane/stage1_fixture.go", "internal/plane/other.go"}
	if _, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace); err == nil {
		t.Fatal("multiple allowed paths accepted")
	}
}

func TestWinglessStage1BindingRejectsGlobProductionPath(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	order.Scope.Allowed = []string{"internal/plane/*.go"}
	if _, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace); err == nil {
		t.Fatal("glob accepted")
	}
}

func TestWinglessStage1BindingRejectsTestPath(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	production := filepath.Join(workspace, "internal", "plane", "stage1_fixture_test.go")
	if err := os.WriteFile(production, []byte("package plane\n"), 0600); err != nil {
		t.Fatal(err)
	}
	order.Scope.Allowed = []string{"internal/plane/stage1_fixture_test.go"}
	if _, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace); err == nil {
		t.Fatal("test path accepted")
	}
}

func TestWinglessStage1BindingRejectsForbiddenPath(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	order.Scope.Forbidden = []string{order.Scope.Allowed[0]}
	if _, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace); err == nil {
		t.Fatal("forbidden path accepted")
	}
}

func TestWinglessStage1BindingPinsSealedPolicy(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if binding.TaskClass != "bounded_single_file_repair" || binding.CandidateFormat != "write_text_json_schema" || !binding.ExactPreimage || binding.TestsMutable || binding.ApplicationAuthority != "external" || binding.AcceptanceAuthority != "external_required" || binding.ModelRepairRetries != 0 || binding.PreferredModel != "qwen3-coder-30ba3b-q3km" || binding.SecondaryModel != "devstral-small-2-24b-iq3m" || binding.TrustCeiling != "stage_1_only" {
		t.Fatal(binding)
	}
	if binding.LiveAction || binding.ArbitraryShell || binding.ModelEditAuthority || binding.ModelTestAuthority || binding.ChangesArchitecture || binding.ChangesAuthority {
		t.Fatal("authority widened")
	}
}

func TestWinglessStage1BindingRejectsStalePreimageCandidate(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: strings.Repeat("f", 64), Content: "package plane\n"}
	if err := ValidateWinglessStage1WriteText(binding, candidate); err == nil {
		t.Fatal("stale preimage accepted")
	}
}

func TestWinglessStage1BindingRejectsDeleteAndMultipleOperationSurrogates(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	for _, kind := range []string{"delete_file", "apply_patch", "write_files"} {
		candidate := WinglessStage1WriteText{Type: kind, Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "replacement"}
		if err := ValidateWinglessStage1WriteText(binding, candidate); err == nil {
			t.Fatalf("operation %s accepted", kind)
		}
	}
}

func TestWinglessStage1BindingRejectsCandidatePathMismatch(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: "internal/plane/other.go", ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "replacement"}
	if err := ValidateWinglessStage1WriteText(binding, candidate); err == nil {
		t.Fatal("path mismatch accepted")
	}
}

func TestWinglessStage1BindingAcceptsExactWriteTextCandidateWithoutApplying(t *testing.T) {
	order, workspace, source := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(workspace, filepath.FromSlash(binding.ProductionPath))
	before, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package plane\n\nfunc changed() {}\n"}
	if err := ValidateWinglessStage1WriteText(binding, candidate); err != nil {
		t.Fatal(err)
	}
	after, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != source || string(after) != source {
		t.Fatal("validator mutated workspace")
	}
}

func TestWinglessStage1BindingRejectsWorkspaceChangedAfterBinding(t *testing.T) {
	order, workspace, _ := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(workspace, filepath.FromSlash(binding.ProductionPath))
	if err := os.WriteFile(target, []byte("package plane\n\nfunc externallyChanged() {}\n"), 0600); err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package plane\n\nfunc candidate() {}\n"}
	if _, err := BuildWinglessStage1PlaneEdit(binding, candidate); err == nil {
		t.Fatal("changed workspace preimage accepted")
	}
}

func TestWinglessStage1BindingRejectsNoopCandidate(t *testing.T) {
	order, workspace, source := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: source}
	if _, err := BuildWinglessStage1PlaneEdit(binding, candidate); err == nil {
		t.Fatal("noop candidate accepted")
	}
}

func TestWinglessStage1BindingBuildsSingleNonExecutingPlaneEdit(t *testing.T) {
	order, workspace, source := winglessStage1Fixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(workspace, filepath.FromSlash(binding.ProductionPath))
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package plane\n\nfunc replacement() {}\n"}
	plan, err := BuildWinglessStage1PlaneEdit(binding, candidate)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Type != "write_text" || plan.Path != binding.ProductionPath || plan.ExpectedBeforeSHA256 != binding.BeforeSHA256 || plan.Content != candidate.Content || len(plan.AfterSHA256) != 64 {
		t.Fatal(plan)
	}
	after, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(after) != source {
		t.Fatal("plan builder applied edit")
	}
}

func TestWinglessStage1BindingNotRegisteredByDefault(t *testing.T) {
	p, _ := setup(t)
	if p.workers["wingless"] != nil || p.workers["wingless-stage1"] != nil {
		t.Fatal("Stage-1 worker unexpectedly registered")
	}
}
