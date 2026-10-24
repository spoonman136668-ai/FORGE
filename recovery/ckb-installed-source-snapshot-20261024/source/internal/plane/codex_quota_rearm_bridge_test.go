package plane

import (
	"strings"
	"testing"
	"time"
)

func TestCodexQuotaRestoredBridgeCommandValidation(t *testing.T) {
	now := time.Date(2026, 9, 23, 18, 0, 0, 0, time.UTC)
	cfg := BridgeConfig{
		PlaneID:        "plane-test",
		MailboxID:      "mailbox-test",
		ControlEnabled: true,
	}
	cmd := BridgeCommand{
		Schema:      bridgeCommandSchema,
		ID:          "quota-rearm-bridge-test",
		PlaneID:     cfg.PlaneID,
		MailboxID:   cfg.MailboxID,
		CreatedAt:   now.Add(-time.Minute),
		ExpiresAt:   now.Add(time.Minute),
		Action:      "quota-restored",
		WorkOrderID: "DEMO",
		Generation:  1,
	}
	if err := cmd.validate(cfg, now); err != nil {
		t.Fatalf("quota-restored bridge command rejected: %v", err)
	}
	cmd.WorkOrderID = ""
	if err := cmd.validate(cfg, now); err == nil || !strings.Contains(err.Error(), "CONTROL_ARGUMENTS_INVALID") {
		t.Fatalf("expected invalid empty work-order id, got %v", err)
	}
}
