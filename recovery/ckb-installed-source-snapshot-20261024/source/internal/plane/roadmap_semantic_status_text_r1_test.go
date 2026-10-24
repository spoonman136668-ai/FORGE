package plane

import "testing"

func TestRoadmapSemanticStatusTextPathIgnoresTestAssertionProse(t *testing.T) {
	const testPath = "pkg/paper_account_execution_risk_v11110_stage_dzn_test.go"
	if roadmapSemanticStatusTextPath(testPath) {
		t.Fatalf("test-source prose must not be treated as authoritative roadmap status: %s", testPath)
	}
	if !roadmapSemanticStatusTextPath("docs/KTRADE_R8_1_COMPATIBILITY.md") {
		t.Fatal("roadmap documentation must remain eligible for semantic status-marker scanning")
	}
	if roadmapSemanticStatusTextPath("pkg/chart.go") {
		t.Fatal("production source must not be scanned as roadmap status prose")
	}
}
