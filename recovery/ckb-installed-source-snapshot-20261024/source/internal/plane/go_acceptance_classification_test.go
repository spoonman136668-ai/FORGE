package plane

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestGoAcceptanceTimeoutConfiguration(t *testing.T) {
	if got := goAcceptanceSupervisorTimeout(false); got != 2*time.Minute {
		t.Fatalf("focused supervisor=%v", got)
	}
	if got := goAcceptanceSupervisorTimeout(true); got != 5*time.Minute {
		t.Fatalf("full supervisor=%v", got)
	}
	if got := goAcceptanceTimeoutArg(false); got != "-timeout=60s" {
		t.Fatalf("focused timeout arg=%q", got)
	}
	if got := goAcceptanceTimeoutArg(true); got != "-timeout=180s" {
		t.Fatalf("full timeout arg=%q", got)
	}
}

func TestGoAcceptanceExecutionFailureClassification(t *testing.T) {
	cases := []struct {
		name   string
		ctxErr error
		runErr error
		stdout string
		stderr string
		want   string
	}{
		{
			name:   "supervisor timeout",
			ctxErr: context.DeadlineExceeded,
			runErr: errors.New("signal killed"),
			want:   "GO_TEST_TIMEOUT",
		},
		{
			name:   "go test timeout",
			runErr: errors.New("exit status 1"),
			stdout: "panic: test timed out after 3m0s",
			want:   "GO_TEST_TIMEOUT",
		},
		{
			name:   "cache access",
			runErr: errors.New("exit status 1"),
			stderr: "go: failed to initialize build cache at C:\\cache: Access is denied. GOCACHE",
			want:   "GO_CACHE_ACCESS_FAILED",
		},
		{
			name:   "assertion",
			runErr: errors.New("exit status 1"),
			stdout: "{\"Action\":\"fail\",\"Package\":\"example/pkg\",\"Test\":\"TestX\"}",
			want:   "GO_TEST_ASSERTION_FAILED",
		},
		{
			name:   "launch infrastructure",
			runErr: errors.New("exec: file not found"),
			want:   "GO_TEST_INFRASTRUCTURE_FAILED",
		},
		{
			name: "no matching pass",
			want: "GO_TEST_ASSERTION_FAILED",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := classifyGoAcceptanceExecutionFailure(
				tc.ctxErr,
				tc.runErr,
				[]byte(tc.stdout),
				[]byte(tc.stderr),
			)
			if got != tc.want {
				t.Fatalf("got=%q want=%q", got, tc.want)
			}
		})
	}
}

func TestGoAcceptanceCheckName(t *testing.T) {
	cases := []struct {
		pass   bool
		detail string
		want   string
	}{
		{true, "10 matching tests passed", "GO_TEST_ASSERTION_FAILED"},
		{false, "GO_TEST_TIMEOUT: deadline", "GO_TEST_TIMEOUT"},
		{false, "GO_CACHE_ACCESS_FAILED: GOCACHE access denied", "GO_CACHE_ACCESS_FAILED"},
		{false, "GO_TEST_INFRASTRUCTURE_FAILED: launch failed", "GO_TEST_INFRASTRUCTURE_FAILED"},
		{false, "GO_TEST_ASSERTION_FAILED: exit status 1", "GO_TEST_ASSERTION_FAILED"},
		{false, "GO_ENVIRONMENT_FAILED: temp unavailable", "GO_TEST_INFRASTRUCTURE_FAILED"},
		{false, "Go test failed: exit status 1", "GO_TEST_ASSERTION_FAILED"},
	}
	for _, tc := range cases {
		if got := goAcceptanceCheckName(tc.pass, tc.detail); got != tc.want {
			t.Fatalf("pass=%v detail=%q got=%q want=%q", tc.pass, tc.detail, got, tc.want)
		}
	}
}

func TestRetryPolicyGoInfrastructureFailure(t *testing.T) {
	for _, code := range []string{
		"GO_TEST_TIMEOUT",
		"GO_TEST_INFRASTRUCTURE_FAILED",
		"GO_CACHE_ACCESS_FAILED",
		"RETRY_LIMIT_REACHED: GO_TEST_TIMEOUT",
	} {
		if !retryPolicyGoInfrastructureFailure(code) {
			t.Fatalf("expected infrastructure code: %q", code)
		}
	}
	for _, code := range []string{"GO_TEST_ASSERTION_FAILED", "GO_TEST_FAILED", "WORKER_TIMEOUT"} {
		if retryPolicyGoInfrastructureFailure(code) {
			t.Fatalf("unexpected infrastructure code: %q", code)
		}
	}
}

func TestGoAcceptanceRetryPolicyIntegration(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3

	if got, _ := p.retryRecoveryAction("W", 1, "GO_TEST_ASSERTION_FAILED", ""); got != "bounded-repair" {
		t.Fatalf("assertion route=%q", got)
	}
	for _, code := range []string{"GO_TEST_TIMEOUT", "GO_TEST_INFRASTRUCTURE_FAILED", "GO_CACHE_ACCESS_FAILED"} {
		got, decision := p.retryRecoveryAction("W", 1, code, "")
		if got != "retry" || !decision.FailureRetryable || decision.HardStop {
			t.Fatalf("code=%q route=%q decision=%+v", code, got, decision)
		}
	}
}

func TestGoAcceptanceGlobalRetryableVocabulary(t *testing.T) {
	for _, code := range []string{
		"GO_TEST_ASSERTION_FAILED",
		"GO_TEST_TIMEOUT",
		"GO_TEST_INFRASTRUCTURE_FAILED",
		"GO_CACHE_ACCESS_FAILED",
	} {
		if !retryable(code) {
			t.Fatalf("split Go failure must be globally retryable for acceptance precedence: %q", code)
		}
	}
	if retryable("ACCEPTANCE_CANCELLED") {
		t.Fatal("acceptance cancellation must remain non-retryable")
	}
}
