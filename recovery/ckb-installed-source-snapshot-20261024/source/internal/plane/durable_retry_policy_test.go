package plane

import "testing"

func TestDurableRetryDecisionUsesConfiguredBudget(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 3
	before := p.retryDecisionNow("W", 2, "WORKER_TIMEOUT")
	if before.BaseBudget != 3 || before.EffectiveBudget != 3 || !before.MayRetry || before.HardStop || !before.FailureRetryable {
		t.Fatalf("before=%+v", before)
	}
	atLimit := p.retryDecisionNow("W", 3, "WORKER_TIMEOUT")
	if atLimit.BaseBudget != 3 || atLimit.EffectiveBudget != 3 || atLimit.MayRetry || !atLimit.HardStop || !atLimit.FailureRetryable {
		t.Fatalf("atLimit=%+v", atLimit)
	}
}

func TestDurableRetryDecisionNeverExpandsInvalidBudget(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 0
	d := p.retryDecisionNow("W", 1, "WORKER_TIMEOUT")
	if d.BaseBudget != 1 || d.EffectiveBudget != 1 || d.MayRetry || !d.HardStop {
		t.Fatalf("decision=%+v", d)
	}
}

func TestDurableRetryDecisionProviderExhaustionHardStops(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 9
	for _, code := range []string{"CODEX_QUOTA_EXHAUSTED", "provider_quota_exhausted", "RATE_LIMIT_EXHAUSTED"} {
		d := p.retryDecisionNow("W", 1, code)
		if d.MayRetry || !d.HardStop || !d.ExternalHandoff || d.FailureRetryable || d.ExhaustionClass != durableExternalOrchestratorExhaustionClass {
			t.Fatalf("%s: %+v", code, d)
		}
	}
}

func TestDurableRetryRecoveryActionPreservesExistingVocabulary(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 3
	cases := []struct {
		attempt int
		failure string
		queue   string
		want    string
	}{
		{1, "WORKER_TIMEOUT", "", "retry"},
		{1, "WORKER_CANCELLED", "NO_PROGRESS_TIMEOUT", "retry"},
		{1, "CONTROLLER_INTERRUPTED: restart", "", "retry"},
		{1, "GO_TEST_FAILED", "", "bounded-repair"},
		{1, "WORKER_EXIT_NONZERO", "", "operator-blocked"},
		{3, "WORKER_TIMEOUT", "", "operator-blocked"},
		{1, "CODEX_QUOTA_EXHAUSTED", "", "operator-blocked"},
	}
	for _, tc := range cases {
		got, decision := p.retryRecoveryAction("W", tc.attempt, tc.failure, tc.queue)
		if got != tc.want {
			t.Fatalf("attempt=%d failure=%q got=%q want=%q decision=%+v", tc.attempt, tc.failure, got, tc.want, decision)
		}
	}
}

func TestDurableRetryWrappedFailureClassification(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 3
	d := p.retryDecisionNow("W", 3, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	if !d.FailureRetryable || !d.HardStop || d.MayRetry {
		t.Fatalf("decision=%+v", d)
	}
}
