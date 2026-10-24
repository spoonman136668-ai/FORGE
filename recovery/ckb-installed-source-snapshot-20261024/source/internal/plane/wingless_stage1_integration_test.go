package plane

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func winglessStage1IntegrationFixture(t *testing.T) (WorkOrder, string, string, string) {
	t.Helper()
	workspace := filepath.Clean(t.TempDir())
	productionPath := "calc.go"
	production := filepath.Join(workspace, productionPath)
	testPath := filepath.Join(workspace, "calc_test.go")
	const before = "package fixture\n\nfunc Add(a, b int) int { return a - b }\n"
	const tests = "package fixture\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) { if got := Add(2, 3); got != 5 { t.Fatalf(\"got %d want 5\", got) } }\n"
	if err := os.WriteFile(filepath.Join(workspace, "go.mod"), []byte("module stage1fixture\n\ngo 1.25\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(production, []byte(before), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(testPath, []byte(tests), 0600); err != nil {
		t.Fatal(err)
	}

	var order WorkOrder
	order.ID = "WINGLESS_STAGE1_R2"
	order.Repo = "fixture"
	order.Title = "Deterministic isolated Stage-1 integration proof"
	order.Instructions = []string{"Fix Add without modifying tests"}
	order.Baseline.Ref = "accepted/fixture"
	order.Baseline.SHA = strings.Repeat("a", 40)
	order.Worker.Branch = "codex/wingless-stage1-r2"
	order.Worker.Preferred = "codex"
	order.Scope.Allowed = []string{productionPath}
	order.Scope.Forbidden = []string{"calc_test.go"}
	order.Acceptance.ProtectRefs = true
	order.Acceptance.Clean = true
	return order, workspace, before, tests
}

func stage1NestedGoTest(workspace string) ([]byte, error) {
	cmd := exec.Command("go", "test", "./...", "-count=1")
	cmd.Dir = workspace
	cmd.Env = append(os.Environ(), "GOFLAGS=-buildvcs=false")
	return cmd.CombinedOutput()
}

func TestWinglessStage1IntegrationDeterministicIsolatedProof(t *testing.T) {
	order, workspace, before, tests := winglessStage1IntegrationFixture(t)
	if out, err := stage1NestedGoTest(workspace); err == nil {
		t.Fatalf("fixture unexpectedly passed before repair: %s", out)
	}

	testPath := filepath.Join(workspace, "calc_test.go")
	testBefore, err := os.ReadFile(testPath)
	if err != nil {
		t.Fatal(err)
	}
	testHashBefore := sha256.Sum256(testBefore)

	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if binding.BeforeSHA256 != winglessStage1SHA256([]byte(before)) {
		t.Fatal("plane preimage binding mismatch")
	}

	candidate := WinglessStage1WriteText{
		Type:                 "write_text",
		Path:                 binding.ProductionPath,
		ExpectedBeforeSHA256: binding.BeforeSHA256,
		Content:              "package fixture\n\nfunc Add(a, b int) int { return a + b }\n",
	}
	raw, err := json.Marshal(candidate)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PrepareWinglessStage1ExternalPlan(binding, raw)
	if err != nil {
		t.Fatal(err)
	}
	if plan.RequestID != order.ID+"-wingless-1" || plan.ApplicationAuthority != "external" || plan.AcceptanceAuthority != "external_required" || plan.TrustCeiling != "stage_1_only" {
		t.Fatal(plan)
	}
	if err := ApplyWinglessStage1ExternalPlan(binding, plan); err != nil {
		t.Fatal(err)
	}

	testAfter, err := os.ReadFile(testPath)
	if err != nil {
		t.Fatal(err)
	}
	testHashAfter := sha256.Sum256(testAfter)
	if hex.EncodeToString(testHashBefore[:]) != hex.EncodeToString(testHashAfter[:]) || string(testAfter) != tests {
		t.Fatal("tests were modified")
	}

	if out, err := stage1NestedGoTest(workspace); err != nil {
		t.Fatalf("deterministic verification failed: %v\n%s", err, out)
	}
	observed, err := os.ReadFile(filepath.Join(workspace, binding.ProductionPath))
	if err != nil {
		t.Fatal(err)
	}
	evidence, err := VerifyWinglessStage1ExternalApplication(binding, plan, observed)
	if err != nil {
		t.Fatal(err)
	}
	if evidence.Status != "postimage_verified" || evidence.Acceptance != "external_required" || evidence.TrustCeiling != "stage_1_only" || evidence.ObservedAfterSHA256 != plan.ExpectedAfterSHA256 {
		t.Fatal(evidence)
	}
}

func TestWinglessStage1IntegrationRejectsUnknownCandidateField(t *testing.T) {
	order, workspace, _, _ := winglessStage1IntegrationFixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	raw := []byte(`{"type":"write_text","path":"calc.go","expected_before_sha256":"` + binding.BeforeSHA256 + `","content":"package fixture\\n","accepted":true}`)
	if _, err := PrepareWinglessStage1ExternalPlan(binding, raw); err == nil {
		t.Fatal("unknown authority field accepted")
	}
}

func TestWinglessStage1IntegrationRejectsTrailingCandidateValue(t *testing.T) {
	order, workspace, _, _ := winglessStage1IntegrationFixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	raw := []byte(`{"type":"write_text","path":"calc.go","expected_before_sha256":"` + binding.BeforeSHA256 + `","content":"package fixture\\n"} {}`)
	if _, err := PrepareWinglessStage1ExternalPlan(binding, raw); err == nil {
		t.Fatal("trailing candidate value accepted")
	}
}

func TestWinglessStage1IntegrationRejectsStalePreimageAtApply(t *testing.T) {
	order, workspace, _, _ := winglessStage1IntegrationFixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package fixture\n\nfunc Add(a,b int) int { return a+b }\n"}
	raw, _ := json.Marshal(candidate)
	plan, err := PrepareWinglessStage1ExternalPlan(binding, raw)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(workspace, binding.ProductionPath), []byte("package fixture\n\nfunc Add(a,b int) int { return 99 }\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := ApplyWinglessStage1ExternalPlan(binding, plan); err == nil {
		t.Fatal("stale preimage applied")
	}
}

func TestWinglessStage1IntegrationRejectsPostimageMismatch(t *testing.T) {
	order, workspace, _, _ := winglessStage1IntegrationFixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package fixture\n\nfunc Add(a,b int) int { return a+b }\n"}
	raw, _ := json.Marshal(candidate)
	plan, err := PrepareWinglessStage1ExternalPlan(binding, raw)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := VerifyWinglessStage1ExternalApplication(binding, plan, []byte("different")); err == nil {
		t.Fatal("postimage mismatch accepted")
	}
}

func TestWinglessStage1IntegrationPlanCannotClaimAcceptance(t *testing.T) {
	order, workspace, _, _ := winglessStage1IntegrationFixture(t)
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, order, 1, workspace)
	if err != nil {
		t.Fatal(err)
	}
	candidate := WinglessStage1WriteText{Type: "write_text", Path: binding.ProductionPath, ExpectedBeforeSHA256: binding.BeforeSHA256, Content: "package fixture\n\nfunc Add(a,b int) int { return a+b }\n"}
	raw, _ := json.Marshal(candidate)
	plan, err := PrepareWinglessStage1ExternalPlan(binding, raw)
	if err != nil {
		t.Fatal(err)
	}
	plan.AcceptanceAuthority = "accepted"
	if err := ApplyWinglessStage1ExternalPlan(binding, plan); err == nil {
		t.Fatal("acceptance authority widening applied")
	}
}
