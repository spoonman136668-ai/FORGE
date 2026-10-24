package plane

import (
	"context"
	"encoding/json"
	"io"
	"strings"
	"testing"
)

type ktradeRetryFeedbackCaptureRunner struct {
	spec ProcessSpec
}

func (r *ktradeRetryFeedbackCaptureRunner) Run(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
	r.spec = spec
	return nil
}

func TestKTradeGoAssertionRetryFeedbackCarriesAllConcreteFailures(t *testing.T) {
	root := t.TempDir()
	id := "V11110_ROADMAP_KTRADE_KCH_RETRY_FEEDBACK_R1"
	attempt := 5

	writeRetryFeedbackFixture(t, root, id, attempt, "acceptance_result.json", []byte(
		`{"state":"REJECTED_RETRYABLE","reason":"GO_TEST_ASSERTION_FAILED","attempt":5}`,
	))
	writeRetryFeedbackFixture(t, root, id, attempt, "acceptance_checks.json", []byte(
		`[{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"GO_TEST_ASSERTION_FAILED: Go test failed: process exit 1; see go-all.jsonl and sandbox launch/stderr evidence"}]`,
	))

	var log strings.Builder
	emit := func(action, testName, output string) {
		t.Helper()
		raw, err := json.Marshal(map[string]string{
			"Action":  action,
			"Package": "ktrade/pkg",
			"Test":    testName,
			"Output":  output,
		})
		if err != nil {
			t.Fatal(err)
		}
		log.Write(raw)
		log.WriteByte('\n')
	}

	const packageValidation = "TestV11110RoadmapKTradeRepeatablePackageValidationR1"
	const paperReadiness = "TestV11110RoadmapKTradeSustainedOfflinePaperReadinessR1/paper-account-truth"
	const paperRisk = "TestV11110StageDZNPaperAccountExecutionRiskState"

	emit("output", packageValidation, "ktrade_repeatable_package_validation_v11110_roadmap_r1_test.go:29: source identity mismatch: pkg/web/app.js\n")
	emit("fail", packageValidation, "")

	// Force the first failure outside the raw go-all tail. The compact failed-test
	// summary must still carry it into the next repair prompt.
	for i := 0; i < workerRetryDiagnosticMaxBytes/32+256; i++ {
		emit("output", "TestUnrelatedPassingNoise", "unrelated deterministic full-suite output padding\n")
	}

	emit("output", paperReadiness, "paper_account_execution_risk_v11110_stage_dzn_test.go:40: exact accepted DZM baseline changed app.js\n")
	emit("fail", paperReadiness, "")
	emit("output", paperRisk, "paper_account_execution_risk_v11110_stage_dzn_test.go:40: exact accepted DZM baseline changed app.js\n")
	emit("fail", paperRisk, "")

	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl", []byte(log.String()))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl.stderr.log", []byte("exit status 1\n"))
	writeRetryFeedbackFixture(t, root, id, attempt, "worker_exit.json", []byte(
		`{"exit_code":1,"failure_class":"GO_TEST_ASSERTION_FAILED","failure_reason":"GO_TEST_ASSERTION_FAILED"}`,
	))
	writeRetryFeedbackFixture(t, root, id, attempt, "worker_stderr.log", []byte("generic acceptance failure\n"))
	writeRetryFeedbackFixture(t, root, id, attempt, "candidate.diff", []byte("CANDIDATE_DIFF_MUST_NOT_ENTER_RETRY_PROMPT\n"))

	feedback := previousAttemptFeedback(root, id, attempt+1)
	for _, want := range []string{
		"PREVIOUS GO FAILED TEST SUMMARY",
		packageValidation,
		"source identity mismatch: pkg/web/app.js",
		paperReadiness,
		paperRisk,
		"exact accepted DZM baseline changed app.js",
		"GO_TEST_ASSERTION_FAILED",
	} {
		if !strings.Contains(feedback, want) {
			t.Fatalf("retry feedback missing %q: %q", want, feedback)
		}
	}
	if strings.Contains(feedback, "CANDIDATE_DIFF_MUST_NOT_ENTER_RETRY_PROMPT") {
		t.Fatalf("candidate diff escaped retry evidence allowlist: %q", feedback)
	}
	if len([]byte(feedback)) > workerRetryFeedbackMaxBytes {
		t.Fatalf("retry feedback exceeded aggregate cap: got=%d max=%d", len([]byte(feedback)), workerRetryFeedbackMaxBytes)
	}

	runner := &ktradeRetryFeedbackCaptureRunner{}
	adapter := CodexAdapter{
		Tool:     "codex",
		Home:     "test-home",
		Runner:   runner,
		Feedback: feedback,
	}
	if err := adapter.Run(context.Background(), t.TempDir(), WorkOrder{}, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(runner.spec.Input, "PREVIOUS ACCEPTANCE FEEDBACK") &&
		!strings.Contains(runner.spec.Input, "PREVIOUS ATTEMPT DIAGNOSTICS") {
		t.Fatalf("successor prompt missing recognized previous-attempt diagnostic header: %q", runner.spec.Input)
	}
	for _, want := range []string{
		packageValidation,
		"source identity mismatch: pkg/web/app.js",
		paperReadiness,
		paperRisk,
		"exact accepted DZM baseline changed app.js",
	} {
		if !strings.Contains(runner.spec.Input, want) {
			t.Fatalf("successor prompt missing %q: %q", want, runner.spec.Input)
		}
	}
	if strings.Contains(runner.spec.Input, "CANDIDATE_DIFF_MUST_NOT_ENTER_RETRY_PROMPT") {
		t.Fatalf("candidate diff escaped into successor prompt: %q", runner.spec.Input)
	}
}

func TestKTradeRetryFeedbackKeepsFocusedAndFullSuiteEvidence(t *testing.T) {
	root := t.TempDir()
	id := "V11110_ROADMAP_KTRADE_RETRY_FEEDBACK_MIXED_R1"
	attempt := 3

	writeRetryFeedbackFixture(t, root, id, attempt, "acceptance_checks.json", []byte(
		`[
			{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-0.jsonl"},
			{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"see go-all.jsonl"}
		]`,
	))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-focused-0.jsonl", []byte("FOCUSED_KTRADE_FAILURE\n"))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-focused-0.jsonl.stderr.log", []byte("FOCUSED_KTRADE_STDERR\n"))

	fullEvent, err := json.Marshal(map[string]string{
		"Action":  "fail",
		"Package": "ktrade/pkg",
		"Test":    "TestV11110RoadmapKTradeRepeatablePackageValidationR1",
	})
	if err != nil {
		t.Fatal(err)
	}
	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl", append(fullEvent, '\n'))
	writeRetryFeedbackFixture(t, root, id, attempt, "go-all.jsonl.stderr.log", []byte("FULL_KTRADE_STDERR\n"))

	got := previousAttemptFeedback(root, id, attempt+1)
	for _, want := range []string{
		"FOCUSED_KTRADE_FAILURE",
		"FOCUSED_KTRADE_STDERR",
		"TestV11110RoadmapKTradeRepeatablePackageValidationR1",
		"FULL_KTRADE_STDERR",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("mixed retry feedback missing %q: %q", want, got)
		}
	}
}

func TestKTradeRetryFeedbackCarriesPriorAcceptanceAcrossCleanControllerCancellation(t *testing.T) {
	root := t.TempDir()
	id := "V11110_ROADMAP_KTRADE_UI_COMPRESSION_R1"
	failedAttempt := 5
	cancelledAttempt := 6

	writeRetryFeedbackFixture(t, root, id, failedAttempt, "acceptance_result.json", []byte(
		`{"state":"REJECTED_RETRYABLE","reason":"GO_TEST_ASSERTION_FAILED","attempt":5}`,
	))
	writeRetryFeedbackFixture(t, root, id, failedAttempt, "acceptance_checks.json", []byte(
		`[{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"see go-all.jsonl"}]`,
	))

	var log strings.Builder
	emit := func(action, testName, output string) {
		t.Helper()
		raw, err := json.Marshal(map[string]string{
			"Action":  action,
			"Package": "ckb/pkg",
			"Test":    testName,
			"Output":  output,
		})
		if err != nil {
			t.Fatal(err)
		}
		log.Write(raw)
		log.WriteByte('\n')
	}
	emit("output", "TestV11110RoadmapKTradeRepeatablePackageValidationR1", "ktrade_repeatable_package_validation_v11110_roadmap_r1_test.go:29: source identity mismatch: pkg/web/app.css\n")
	emit("fail", "TestV11110RoadmapKTradeRepeatablePackageValidationR1", "")
	emit("output", "TestV11110StageDZNPaperAccountExecutionRiskState", "paper_account_execution_risk_v11110_stage_dzn_test.go:40: exact accepted DZM baseline changed strategy.html\n")
	emit("fail", "TestV11110StageDZNPaperAccountExecutionRiskState", "")
	writeRetryFeedbackFixture(t, root, id, failedAttempt, "go-all.jsonl", []byte(log.String()))
	writeRetryFeedbackFixture(t, root, id, failedAttempt, "go-all.jsonl.stderr.log", []byte("exit status 1\n"))
	writeRetryFeedbackFixture(t, root, id, failedAttempt, "candidate.diff", []byte("OLDER_CANDIDATE_DIFF_MUST_NOT_ENTER_PROMPT\n"))

	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "acceptance_result.json", []byte(
		`{"state":"REJECTED_RETRYABLE","reason":"WORKER_CANCELLED: CONTROLLER_SHUTDOWN","acceptance_ran":false}`,
	))
	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "acceptance_checks.json", []byte(`[]`))
	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "worker_exit.json", []byte(
		`{"exit_code":-1,"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: CONTROLLER_SHUTDOWN","cancel_reason":"CONTROLLER_SHUTDOWN"}`,
	))
	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "worker_stderr.log", []byte("controller shutdown\n"))
	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "worker_stdout.log", []byte("QUALIFIED_TEST_ONLY_CANDIDATE_MUST_NOT_ENTER_PROMPT\n"))
	writeRetryFeedbackFixture(t, root, id, cancelledAttempt, "candidate.diff", []byte("CANCELLED_CANDIDATE_DIFF_MUST_NOT_ENTER_PROMPT\n"))

	feedback := previousAttemptFeedback(root, id, cancelledAttempt+1)
	for _, want := range []string{
		"WORKER_CANCELLED",
		"PRE-CANCELLATION ACCEPTANCE RESULT",
		"PRE-CANCELLATION PREVIOUS GO FAILED TEST SUMMARY",
		"TestV11110RoadmapKTradeRepeatablePackageValidationR1",
		"source identity mismatch: pkg/web/app.css",
		"TestV11110StageDZNPaperAccountExecutionRiskState",
		"exact accepted DZM baseline changed strategy.html",
	} {
		if !strings.Contains(feedback, want) {
			t.Fatalf("cancel-hop retry feedback missing %q: %q", want, feedback)
		}
	}
	for _, forbidden := range []string{
		"QUALIFIED_TEST_ONLY_CANDIDATE_MUST_NOT_ENTER_PROMPT",
		"CANCELLED_CANDIDATE_DIFF_MUST_NOT_ENTER_PROMPT",
		"OLDER_CANDIDATE_DIFF_MUST_NOT_ENTER_PROMPT",
	} {
		if strings.Contains(feedback, forbidden) {
			t.Fatalf("excluded evidence escaped cancel-hop allowlist %q: %q", forbidden, feedback)
		}
	}
	if len([]byte(feedback)) > workerRetryFeedbackMaxBytes {
		t.Fatalf("cancel-hop retry feedback exceeded aggregate cap: got=%d max=%d", len([]byte(feedback)), workerRetryFeedbackMaxBytes)
	}
}

func TestKTradeRetryFeedbackDoesNotHopAcrossCancellationWithAcceptanceFailure(t *testing.T) {
	root := t.TempDir()
	id := "V11110_ROADMAP_KTRADE_UI_COMPRESSION_R1"
	writeRetryFeedbackFixture(t, root, id, 5, "acceptance_checks.json", []byte(
		`[{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"older failure"}]`,
	))
	writeRetryFeedbackFixture(t, root, id, 5, "go-all.jsonl", []byte(
		`{"Action":"fail","Package":"ckb/pkg","Test":"TestOlderFailure","Output":"OLDER_FAILURE_MUST_NOT_CARRY"}`+"\n",
	))
	writeRetryFeedbackFixture(t, root, id, 6, "acceptance_result.json", []byte(
		`{"state":"REJECTED_RETRYABLE","reason":"WORKER_CANCELLED","acceptance_ran":false}`,
	))
	writeRetryFeedbackFixture(t, root, id, 6, "acceptance_checks.json", []byte(
		`[{"name":"FOCUSED_TEST_FAILED","pass":false,"detail":"see go-focused-0.jsonl"}]`,
	))
	writeRetryFeedbackFixture(t, root, id, 6, "worker_exit.json", []byte(
		`{"failure_class":"WORKER_CANCELLED","failure_reason":"WORKER_CANCELLED: CONTROLLER_SHUTDOWN"}`,
	))
	writeRetryFeedbackFixture(t, root, id, 6, "go-focused-0.jsonl", []byte("CURRENT_FAILURE\n"))

	feedback := previousAttemptFeedback(root, id, 7)
	if strings.Contains(feedback, "OLDER_FAILURE_MUST_NOT_CARRY") {
		t.Fatalf("older acceptance failure carried across non-clean cancelled attempt: %q", feedback)
	}
	if !strings.Contains(feedback, "CURRENT_FAILURE") {
		t.Fatalf("immediate failed acceptance evidence missing: %q", feedback)
	}
}
