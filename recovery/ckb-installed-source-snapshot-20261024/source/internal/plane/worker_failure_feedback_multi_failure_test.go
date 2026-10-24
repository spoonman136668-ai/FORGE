package plane

import (
	"strconv"
	"strings"
	"testing"
)

func TestWorkerFailureFeedback_MultipleGoFailuresCarryEveryReferencedArtifact(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_MULTI_GO"
	attempt := 6

	checks := `[
		{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-0.jsonl"},
		{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-1.jsonl"},
		{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-2.jsonl"},
		{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-3.jsonl"},
		{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"duplicate go-focused-0.jsonl"},
		{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"see go-all.jsonl"}
	]`
	writeRetryFeedbackFixture(t, root, id, attempt, "acceptance_checks.json", []byte(checks))
	writeRetryFeedbackFixture(t, root, id, attempt, "acceptance_result.json", []byte(`{"state":"REJECTED_RETRYABLE","reason":"FOCUSED_TEST_FAILED","attempt":6}`))

	for i := 0; i < 4; i++ {
		name := "go-focused-" + strconv.Itoa(i) + ".jsonl"
		writeRetryFeedbackFixture(t, root, id, attempt, name, []byte("FOCUSED_MARKER_"+strconv.Itoa(i)+"\n"))
		writeRetryFeedbackFixture(t, root, id, attempt, name+".stderr.log", []byte("FOCUSED_STDERR_"+strconv.Itoa(i)+"\n"))
	}
	writeRetryFeedbackFixture(t, root, id, attempt, "go-focused-9.jsonl", []byte("UNREFERENCED_FOCUSED_9\n"))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl", []byte("FULL_SUITE_MARKER\n"))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl.stderr.log", []byte("FULL_SUITE_STDERR\n"))

	got := previousAttemptFeedback(root, id, attempt+1)
	for _, want := range []string{
		"FOCUSED_MARKER_0", "FOCUSED_STDERR_0",
		"FOCUSED_MARKER_1", "FOCUSED_STDERR_1",
		"FOCUSED_MARKER_2", "FOCUSED_STDERR_2",
		"FOCUSED_MARKER_3", "FOCUSED_STDERR_3",
		"FULL_SUITE_MARKER", "FULL_SUITE_STDERR",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("multi-failure feedback missing %q: %q", want, got)
		}
	}
	if strings.Contains(got, "UNREFERENCED_FOCUSED_9") {
		t.Fatalf("unreferenced focused evidence escaped allowlist: %q", got)
	}
	if strings.Count(got, "PREVIOUS FOCUSED GO TEST OUTPUT go-focused-0.jsonl") != 1 {
		t.Fatalf("duplicate focused artifact was not deduplicated: %q", got)
	}
	if len([]byte(got)) > workerRetryFeedbackMaxBytes {
		t.Fatalf("multi-failure feedback exceeded aggregate cap: got=%d max=%d", len([]byte(got)), workerRetryFeedbackMaxBytes)
	}
}
