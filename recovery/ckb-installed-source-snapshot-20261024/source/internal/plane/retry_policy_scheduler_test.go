package plane

import (
	"testing"
	"time"
)

func TestRetryPolicySchedulerWindowConvertsOrdinaryFailureToRetry(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(time.Hour).Format(time.RFC3339))
	action, decision := p.retryRecoveryAction("ANY_SOURCE_WORK", 4, "WORKER_EXIT_NONZERO", "", now)
	if action != "retry" {
		t.Fatalf("action=%q want=retry decision=%+v", action, decision)
	}
	if !decision.WindowActive || !decision.MayRetry || decision.ExternalHandoff {
		t.Fatalf("unexpected decision: %+v", decision)
	}
}

func TestRetryPolicySchedulerKeepsBoundedRepair(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(time.Hour).Format(time.RFC3339))
	for _, reason := range []string{"FOCUSED_TEST_FAILED", "GO_TEST_FAILED", "NO_DIFF_PRODUCED", "PLAYWRIGHT_FAILED", "POWERSHELL_ACCEPTANCE_FAILED"} {
		action, decision := p.retryRecoveryAction("ANY_SOURCE_WORK", 8, reason, "", now)
		if action != "bounded-repair" {
			t.Fatalf("reason=%q action=%q want=bounded-repair decision=%+v", reason, action, decision)
		}
	}
}

func TestRetryPolicySchedulerQuotaNeverGenericRetries(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(time.Hour).Format(time.RFC3339))
	action, decision := p.retryRecoveryAction("ANY_SOURCE_WORK", 4, "CODEX_QUOTA_EXHAUSTED", "", now)
	if action != "external-orchestrator" || !decision.ExternalHandoff || decision.MayRetry {
		t.Fatalf("quota entered generic retry: action=%q decision=%+v", action, decision)
	}
}

func TestRetryPolicySchedulerUnsafeFailureStaysOperatorBlocked(t *testing.T) {
	now := time.Date(2026, 9, 15, 20, 0, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, now.Add(time.Hour).Format(time.RFC3339))
	for _, reason := range []string{"SOURCE_HYGIENE_FAILED", "PLANE_AUTHORITY_LOST", "ACCEPTED_REF_MUTATION_FORBIDDEN"} {
		action, decision := p.retryRecoveryAction("ANY_SOURCE_WORK", 4, reason, "", now)
		if action != "operator-blocked" || decision.FailureRetryable {
			t.Fatalf("unsafe reason changed recovery policy: reason=%q action=%q decision=%+v", reason, action, decision)
		}
	}
}

func TestRetryPolicySchedulerExpiryRestoresOldOperatorBlock(t *testing.T) {
	expires := time.Date(2026, 9, 16, 16, 57, 0, 0, time.UTC)
	p := retryPolicyTestEngine(true, expires.Format(time.RFC3339))
	action, decision := p.retryRecoveryAction("ANY_SOURCE_WORK", 4, "WORKER_EXIT_NONZERO", "", expires)
	if action != "operator-blocked" || decision.WindowActive {
		t.Fatalf("expiry did not restore normal recovery policy: action=%q decision=%+v", action, decision)
	}
}
