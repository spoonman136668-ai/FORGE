package plane

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"unicode/utf8"
)

func writeRetryFeedbackFixture(t *testing.T, root, id string, attempt int, name string, data []byte) {
	t.Helper()
	dir := filepath.Join(root, "evidence", id, strconv.Itoa(attempt))
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, name), data, 0600); err != nil {
		t.Fatal(err)
	}
}

func TestWorkerFailureFeedback_PreservesAcceptanceAndAddsWorkerDiagnostics(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_R1"
	writeRetryFeedbackFixture(t, root, id, 1, "acceptance_checks.json", []byte(`[{"name":"focused","pass":false,"detail":"compile failed"}]`))
	writeRetryFeedbackFixture(t, root, id, 1, "worker_exit.json", []byte(`{"exit_code":1,"failure_class":"WORKER_EXIT_NONZERO","failure_reason":"WORKER_EXIT_NONZERO"}`))
	writeRetryFeedbackFixture(t, root, id, 1, "worker_stderr.log", []byte("fatal: deterministic worker failure\n"))
	writeRetryFeedbackFixture(t, root, id, 1, "worker_stdout.log", []byte("STDOUT_MUST_NOT_BE_INCLUDED\n"))

	got := previousAttemptFeedback(root, id, 2)
	for _, want := range []string{
		"<<<UNTRUSTED_PREVIOUS_ATTEMPT_DIAGNOSTICS>>>",
		"PREVIOUS ACCEPTANCE CHECKS",
		"compile failed",
		"PREVIOUS WORKER EXIT",
		"WORKER_EXIT_NONZERO",
		"PREVIOUS WORKER STDERR",
		"deterministic worker failure",
		"<<<END_UNTRUSTED_PREVIOUS_ATTEMPT_DIAGNOSTICS>>>",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("feedback missing %q: %q", want, got)
		}
	}
	if strings.Contains(got, "STDOUT_MUST_NOT_BE_INCLUDED") {
		t.Fatalf("worker stdout escaped fixed evidence allowlist: %q", got)
	}
}

func TestWorkerFailureFeedback_EmptyAcceptanceStillFeedsWorkerFailure(t *testing.T) {
	root := t.TempDir()
	id := "V11110_STAGE_DZN_KTRADE_PAPER_ACCOUNT_EXECUTION_RISK_STATE_R2"
	writeRetryFeedbackFixture(t, root, id, 12, "acceptance_checks.json", []byte("[]\n"))
	writeRetryFeedbackFixture(t, root, id, 12, "worker_exit.json", []byte(`{"exit_code":1,"failure_class":"WORKER_EXIT_NONZERO","failure_reason":"WORKER_EXIT_NONZERO"}`+"\n"))
	writeRetryFeedbackFixture(t, root, id, 12, "worker_stderr.log", []byte("codex: previous worker failed before deterministic acceptance\n"))

	got := previousAttemptFeedback(root, id, 13)
	for _, want := range []string{"[]", "WORKER_EXIT_NONZERO", "failed before deterministic acceptance"} {
		if !strings.Contains(got, want) {
			t.Fatalf("pre-acceptance retry feedback missing %q: %q", want, got)
		}
	}
}

func TestWorkerFailureFeedback_GoAcceptanceCarriesDeterministicFailureEvidence(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_R64_GO"
	writeRetryFeedbackFixture(t, root, id, 3, "acceptance_result.json", []byte(`{"state":"REJECTED_RETRYABLE","reason":"GO_TEST_FAILED","attempt":3}`))
	writeRetryFeedbackFixture(t, root, id, 3, "acceptance_checks.json", []byte(`[{"name":"GO_TEST_FAILED","pass":false,"detail":"Go test failed: exit status 1; see go-all.jsonl and sandbox launch/stderr evidence"}]`))
	writeRetryFeedbackFixture(t, root, id, 3, "go-all.jsonl", []byte("{\"Action\":\"output\",\"Output\":\"--- FAIL: TestR64Continuity (0.00s)\\n\"}\n"))
	writeRetryFeedbackFixture(t, root, id, 3, "go-all.jsonl.stderr.log", []byte("sandbox stderr marker for R6.4\n"))
	writeRetryFeedbackFixture(t, root, id, 3, "candidate.diff", []byte("CANDIDATE_DIFF_MUST_NOT_BE_INCLUDED\n"))

	got := previousAttemptFeedback(root, id, 4)
	for _, want := range []string{
		"PREVIOUS ACCEPTANCE RESULT",
		"GO_TEST_FAILED",
		"PREVIOUS GO TEST OUTPUT",
		"TestR64Continuity",
		"PREVIOUS GO TEST STDERR",
		"sandbox stderr marker for R6.4",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("R6.4 feedback missing %q: %q", want, got)
		}
	}
	if strings.Contains(got, "CANDIDATE_DIFF_MUST_NOT_BE_INCLUDED") {
		t.Fatalf("candidate diff escaped R6.4 evidence allowlist: %q", got)
	}
}

func TestWorkerFailureFeedback_FocusedAcceptanceUsesOnlyReferencedArtifact(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_R64_FOCUSED"
	writeRetryFeedbackFixture(t, root, id, 4, "acceptance_checks.json", []byte(`[{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"Go test failed: exit status 1; see go-focused-7.jsonl and sandbox launch/stderr evidence"}]`))
	writeRetryFeedbackFixture(t, root, id, 4, "go-focused-7.jsonl", []byte("REFERENCED_FOCUSED_FAILURE\n"))
	writeRetryFeedbackFixture(t, root, id, 4, "go-focused-7.jsonl.stderr.log", []byte("REFERENCED_FOCUSED_STDERR\n"))
	writeRetryFeedbackFixture(t, root, id, 4, "go-focused-8.jsonl", []byte("UNREFERENCED_FOCUSED_MUST_NOT_BE_INCLUDED\n"))

	got := previousAttemptFeedback(root, id, 5)
	for _, want := range []string{"go-focused-7.jsonl", "REFERENCED_FOCUSED_FAILURE", "REFERENCED_FOCUSED_STDERR"} {
		if !strings.Contains(got, want) {
			t.Fatalf("focused R6.4 feedback missing %q: %q", want, got)
		}
	}
	if strings.Contains(got, "UNREFERENCED_FOCUSED_MUST_NOT_BE_INCLUDED") {
		t.Fatalf("unreferenced focused evidence escaped allowlist: %q", got)
	}
}

func TestWorkerFailureFeedback_StderrUsesBoundedTailAndAggregateCap(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_R2"
	body := "HEAD_MARKER\n" + strings.Repeat("x", workerRetryStderrMaxBytes*2) + "\nTAIL_MARKER\n"
	writeRetryFeedbackFixture(t, root, id, 1, "worker_stderr.log", []byte(body))
	writeRetryFeedbackFixture(t, root, id, 1, "worker_exit.json", []byte(`{"failure_reason":"WORKER_EXIT_NONZERO"}`))

	got := previousAttemptFeedback(root, id, 2)
	if strings.Contains(got, "HEAD_MARKER") {
		t.Fatalf("stderr prefix should be discarded when tail is truncated")
	}
	if !strings.Contains(got, "TAIL_MARKER") {
		t.Fatalf("stderr tail marker missing")
	}
	if !strings.Contains(got, "truncated") {
		t.Fatalf("truncation was not disclosed")
	}
	if len([]byte(got)) > workerRetryFeedbackMaxBytes {
		t.Fatalf("feedback exceeded aggregate cap: got=%d max=%d", len([]byte(got)), workerRetryFeedbackMaxBytes)
	}
}

func TestWorkerFailureFeedback_MissingFirstAttemptAndInvalidIDAreEmpty(t *testing.T) {
	root := t.TempDir()
	if got := previousAttemptFeedback(root, "WORKER_FEEDBACK_R3", 1); got != "" {
		t.Fatalf("first attempt unexpectedly received feedback: %q", got)
	}
	if got := previousAttemptFeedback(root, "../escape", 2); got != "" {
		t.Fatalf("invalid work order id unexpectedly received feedback: %q", got)
	}
	if got := previousAttemptFeedback(root, "WORKER_FEEDBACK_R3", 2); got != "" {
		t.Fatalf("missing previous evidence unexpectedly received feedback: %q", got)
	}
}

func TestWorkerFailureFeedback_NormalizesInvalidUTF8(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_R4"
	writeRetryFeedbackFixture(t, root, id, 1, "worker_stderr.log", []byte{'b', 'a', 'd', ':', 0xff, 0xfe, '\n'})

	got := previousAttemptFeedback(root, id, 2)
	if !utf8.ValidString(got) {
		t.Fatalf("feedback is not valid UTF-8")
	}
	if !strings.Contains(got, workerRetryFeedbackReplacementText) {
		t.Fatalf("invalid UTF-8 was not normalized: %q", got)
	}
}
