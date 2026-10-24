package plane

import (
	"math"
	"testing"
	"time"
)

func retryPolicyTestEngine(enabled bool, expires string) *Engine {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.TemporaryNoIdleRetryWindow = TemporaryNoIdleRetryWindow{
		Enabled:   enabled,
		ExpiresAt: expires,
	}
	return p
}

func TestRetryPolicyBaseBudgetHelper(t *testing.T) {
	p := &Engine{}
	if got := p.retryBaseBudget(); got != 1 {
		t.Fatalf("zero configured budget should clamp to 1: got=%d", got)
	}
	p.Config.Policy.MaxAttempts = 3
	if got := p.retryBaseBudget(); got != 3 {
		t.Fatalf("configured base budget mismatch: got=%d want=3", got)
	}
}

func TestRetryPolicyEffectiveBudgetStatusProjection(t *testing.T) {
	p := retryPolicyTestEngine(false, "")
	if got := p.retryEffectiveBudgetNow(); got != 3 {
		t.Fatalf("default effective budget mismatch: got=%d want=3", got)
	}
	p.Config.Policy.TemporaryNoIdleRetryWindow = TemporaryNoIdleRetryWindow{
		Enabled:   true,
		ExpiresAt: time.Now().UTC().Add(time.Hour).Format(time.RFC3339),
	}
	if got := p.retryEffectiveBudgetNow(); got != math.MaxInt32 {
		t.Fatalf("active-window effective budget mismatch: got=%d want=%d", got, math.MaxInt32)
	}
}

func TestRetryPolicyDefaultCapOutsideWindow(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(false, "")
	d := p.retryDecision("ANY_SOURCE_WORK", 3, "WORKER_EXIT_NONZERO", now)
	if d.EffectiveBudget != 3 || d.MayRetry || !d.HardStop || d.WindowActive || d.ExternalHandoff {
		t.Fatalf("unexpected decision: %+v", d)
	}
	if !d.FailureRetryable || d.ExhaustionClass != normalRetryExhaustionClass {
		t.Fatalf("unexpected normal classification: %+v", d)
	}
}

func TestRetryPolicyActiveWindowRemovesCountTerminal(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(12*time.Hour).Format(time.RFC3339))
	d := p.retryDecision("ANY_SOURCE_WORK", 100, "WORKER_EXIT_NONZERO", now)
	if !d.WindowActive || !d.MayRetry || d.HardStop || d.ExternalHandoff {
		t.Fatalf("active window did not remove count terminal: %+v", d)
	}
	if d.EffectiveBudget != math.MaxInt32 || d.BaseBudget != 3 {
		t.Fatalf("budget mismatch: %+v", d)
	}
	if !d.FailureRetryable || d.ExhaustionClass != temporaryNoIdleRetryWindowExhaustionClass {
		t.Fatalf("classification mismatch: %+v", d)
	}
}

func TestRetryPolicyExactExpiryRestoresDefaultCap(t *testing.T) {
	expires := time.Date(2026, 9, 16, 16, 57, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, expires.Format(time.RFC3339))
	d := p.retryDecision("ANY_SOURCE_WORK", 3, "WORKER_EXIT_NONZERO", expires)
	if d.WindowActive || d.MayRetry || !d.HardStop || d.EffectiveBudget != 3 {
		t.Fatalf("exact expiry did not restore default budget: %+v", d)
	}
}

func TestRetryPolicyMalformedExpiryFailsClosed(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, "not-a-time")
	d := p.retryDecision("ANY_SOURCE_WORK", 3, "WORKER_EXIT_NONZERO", now)
	if d.WindowActive || d.MayRetry || !d.HardStop || d.EffectiveBudget != 3 {
		t.Fatalf("malformed expiry did not fail closed: %+v", d)
	}
}

func TestRetryPolicyQuotaExhaustionAlwaysRoutesExternal(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(12*time.Hour).Format(time.RFC3339))
	for _, code := range []string{
		"CODEX_QUOTA_EXHAUSTED",
		"WORKER_EXIT_NONZERO: PROVIDER_QUOTA_EXHAUSTED",
		"rate_limit_exhausted",
	} {
		d := p.retryDecision("ANY_SOURCE_WORK", 3, code, now)
		if d.WindowActive || d.MayRetry || !d.HardStop || !d.ExternalHandoff {
			t.Fatalf("quota exhaustion escaped external handoff for %q: %+v", code, d)
		}
		if d.ExhaustionClass != externalOrchestratorExhaustionClass || d.FailureRetryable {
			t.Fatalf("quota classification mismatch for %q: %+v", code, d)
		}
	}
}

func TestRetryPolicyFailureEligibility(t *testing.T) {
	cases := []struct {
		code string
		want bool
	}{
		{"WORKER_EXIT_NONZERO", true},
		{"RETRY_LIMIT_REACHED: WORKER_EXIT_NONZERO", true},
		{"RETRY_LIMIT_REACHED", true},
		{"GO_TEST_FAILED", true},
		{"PLAYWRIGHT_FAILED", true},
		{"SOURCE_HYGIENE_FAILED", false},
		{"PLANE_AUTHORITY_LOST", false},
		{"ACCEPTED_REF_MUTATION_FORBIDDEN", false},
		{"CODEX_QUOTA_EXHAUSTED", false},
	}
	for _, tc := range cases {
		if got := retryPolicyFailureRetryable(tc.code); got != tc.want {
			t.Fatalf("retryPolicyFailureRetryable(%q)=%v want=%v", tc.code, got, tc.want)
		}
	}
}
