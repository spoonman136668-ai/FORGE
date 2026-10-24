package plane

import (
	"testing"
	"time"
)

func TestAuthorityReverifyTransientRetryClassification(t *testing.T) {
	at := time.Date(2026, 9, 19, 9, 0, 0, 0, time.UTC)
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.TemporaryNoIdleRetryWindow.Enabled = true
	p.Config.Policy.TemporaryNoIdleRetryWindow.ExpiresAt = at.Add(time.Hour).Format(time.RFC3339)

	for _, code := range []string{
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_UNAVAILABLE",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_READ_FAILED",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_HTTP_500",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_HTTP_502",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_HTTP_503",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_HTTP_504",
	} {
		if !retryPolicyTransientAuthorityReverifyFailure(code) {
			t.Fatalf("transient authority-reverify failure not recognized: %q", code)
		}
		action, decision := p.retryRecoveryAction("W", 2, code, "", at)
		if action != "retry" || !decision.FailureRetryable {
			t.Fatalf("transient authority-reverify failure did not enter existing retry path: code=%q action=%q decision=%+v", code, action, decision)
		}
	}

	for _, code := range []string{
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: ANOTHER_PLANE_OWNS_REPOSITORY",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: AUTHORITY_REPOSITORY_MISMATCH",
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_HTTP_401",
	} {
		if retryPolicyTransientAuthorityReverifyFailure(code) {
			t.Fatalf("unsafe authority-reverify failure entered transient class: %q", code)
		}
		action, decision := p.retryRecoveryAction("W", 2, code, "", at)
		if action != "operator-blocked" || decision.FailureRetryable {
			t.Fatalf("unsafe authority-reverify failure escaped operator block under active retry window: code=%q action=%q decision=%+v", code, action, decision)
		}
	}

	outside := &Engine{}
	outside.Config.Policy.MaxAttempts = 3
	_, exhausted := outside.retryRecoveryAction(
		"W",
		3,
		"WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: BRIDGE_GITHUB_UNAVAILABLE",
		"",
		at,
	)
	if exhausted.MayRetry || !exhausted.HardStop {
		t.Fatalf("transient classification expanded ordinary retry budget: decision=%+v", exhausted)
	}
}
