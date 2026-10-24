package plane

import "testing"

func TestAcceptanceReplayReasonAllowed(t *testing.T) {
	for _, reason := range []string{"BROWSER_CRITICAL_CONTROL", "PLAYWRIGHT_FAILED", "PLANE_AUTHORITY_LOST"} {
		if !acceptanceReplayReasonAllowed(reason) {
			t.Fatalf("expected %q to reach replay validation", reason)
		}
	}
	for _, reason := range []string{"", "CODEX_QUOTA_EXHAUSTED", "GO_TEST_FAILED", "AUTHORITY_REPOSITORY_MISMATCH"} {
		if acceptanceReplayReasonAllowed(reason) {
			t.Fatalf("unexpected replayable reason %q", reason)
		}
	}
}
