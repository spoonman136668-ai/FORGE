package plane

import (
	"testing"
	"time"
)

func TestWebUIMailboxResilienceRetryDelayIsBounded(t *testing.T) {
	base := 60 * time.Second
	delay := base
	for i := 0; i < 20; i++ {
		delay = bridgeRetryDelay(delay, base)
	}
	if delay != 2*time.Minute {
		t.Fatalf("unexpected retry cap: %s", delay)
	}
	if got := bridgeRetryDelay(15*time.Minute, 15*time.Minute); got != 15*time.Minute {
		t.Fatalf("configured poll floor changed: %s", got)
	}
}
