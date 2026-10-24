package plane

import (
	"context"
	"errors"
	"strings"
	"time"
)

const authorityTransientAttempts = 3

func transientAuthorityTransportError(err error) bool {
	if err == nil {
		return false
	}
	switch strings.TrimSpace(err.Error()) {
	case "BRIDGE_GITHUB_UNAVAILABLE",
		"BRIDGE_GITHUB_READ_FAILED",
		"BRIDGE_GITHUB_HTTP_500",
		"BRIDGE_GITHUB_HTTP_502",
		"BRIDGE_GITHUB_HTTP_503",
		"BRIDGE_GITHUB_HTTP_504":
		return true
	default:
		return false
	}
}

func retryTransientAuthority(ctx context.Context, fn func() error) error {
	var last error
	for attempt := 0; attempt < authorityTransientAttempts; attempt++ {
		last = fn()
		if last == nil || !transientAuthorityTransportError(last) {
			return last
		}
		if attempt+1 == authorityTransientAttempts {
			return last
		}
		timer := time.NewTimer(time.Duration(attempt+1) * 250 * time.Millisecond)
		select {
		case <-ctx.Done():
			if !timer.Stop() {
				<-timer.C
			}
			return ctx.Err()
		case <-timer.C:
		}
	}
	return errors.New("AUTHORITY_TRANSIENT_RETRY_EXHAUSTED")
}
