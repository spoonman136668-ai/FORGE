package plane

import (
	"context"
	"strings"
	"testing"
)

func TestWebUIBridgeOversizedReadResultIsBoundedAndDoesNotStall(t *testing.T) {
	b, m := bridgeTest(t)

	putCommand(m, bridgeTestCommand("oversized", "status"))

	b.snapshot = func(
		context.Context,
		BridgeCommand,
	) (any, error) {
		return map[string]string{
			"huge": strings.Repeat("x", bridgeMaxBytes),
		}, nil
	}

	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}

	r := getResult(t, m, "oversized")

	if r.Status != "blocked" ||
		r.Code != "BRIDGE_RESULT_TOO_LARGE" ||
		!r.ReadOnly {
		t.Fatalf(
			"unexpected oversized result: %+v",
			r,
		)
	}

	if len(m.output["outbox/oversized.json"]) >= bridgeMaxBytes {
		t.Fatalf(
			"bounded result still too large: %d",
			len(m.output["outbox/oversized.json"]),
		)
	}

	putCommand(m, bridgeTestCommand("after", "ping"))

	b.snapshot = func(
		context.Context,
		BridgeCommand,
	) (any, error) {
		return map[string]bool{
			"connected": true,
		}, nil
	}

	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}

	after := getResult(t, m, "after")

	if after.Status != "succeeded" ||
		after.Code != "READ_ONLY_RESULT" {
		t.Fatalf(
			"later command stalled: %+v",
			after,
		)
	}
}
