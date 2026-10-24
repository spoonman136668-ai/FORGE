package plane

import (
	"context"
	"errors"
	"testing"
)

func TestTransientAuthorityTransportClassification(t *testing.T) {
	for _, code := range []string{
		"BRIDGE_GITHUB_UNAVAILABLE",
		"BRIDGE_GITHUB_READ_FAILED",
		"BRIDGE_GITHUB_HTTP_500",
		"BRIDGE_GITHUB_HTTP_502",
		"BRIDGE_GITHUB_HTTP_503",
		"BRIDGE_GITHUB_HTTP_504",
	} {
		if !transientAuthorityTransportError(errors.New(code)) {
			t.Fatalf("expected transient: %s", code)
		}
	}
	for _, code := range []string{
		"",
		"BRIDGE_GITHUB_HTTP_401",
		"BRIDGE_GITHUB_HTTP_409",
		"ANOTHER_PLANE_OWNS_REPOSITORY",
		"AUTHORITY_REPOSITORY_MISMATCH",
		"ORIGINAL_WORKFLOW_NOT_DISABLED: x",
	} {
		if transientAuthorityTransportError(errors.New(code)) {
			t.Fatalf("unsafe authority failure classified transient: %s", code)
		}
	}
}

func TestRetryTransientAuthority(t *testing.T) {
	calls := 0
	err := retryTransientAuthority(context.Background(), func() error {
		calls++
		if calls < 3 {
			return errors.New("BRIDGE_GITHUB_UNAVAILABLE")
		}
		return nil
	})
	if err != nil || calls != 3 {
		t.Fatalf("expected bounded recovery on third call: calls=%d err=%v", calls, err)
	}

	calls = 0
	err = retryTransientAuthority(context.Background(), func() error {
		calls++
		return errors.New("AUTHORITY_REPOSITORY_MISMATCH")
	})
	if err == nil || calls != 1 {
		t.Fatalf("identity failure must fail immediately: calls=%d err=%v", calls, err)
	}

	calls = 0
	err = retryTransientAuthority(context.Background(), func() error {
		calls++
		return errors.New("BRIDGE_GITHUB_HTTP_503")
	})
	if err == nil || calls != authorityTransientAttempts {
		t.Fatalf("transient exhaustion must remain failed: calls=%d err=%v", calls, err)
	}
}
