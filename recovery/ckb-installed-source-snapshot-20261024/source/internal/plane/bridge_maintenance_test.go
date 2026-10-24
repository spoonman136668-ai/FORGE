package plane

import (
	"strings"
	"testing"
	"time"
)

func maintenanceBridgeConfig() BridgeConfig {
	return BridgeConfig{
		Schema:           "ckb-plane.webui-bridge.v1",
		Repository:       "spoonman136668-ai/ckb",
		RepositoryID:     1,
		Branch:           "ckb-plane/webui-test",
		MailboxID:        "maintenance-test",
		PlaneID:          "plane-test",
		TokenEnv:         "CKB_PLANE_GITHUB_TOKEN",
		PollSeconds:      30,
		HeartbeatSeconds: 300,
		ControlEnabled:   true,
	}
}

func maintenanceCommand(at time.Time, action string) BridgeCommand {
	return BridgeCommand{
		Schema:      bridgeCommandSchema,
		ID:          "maintenance-command",
		PlaneID:     "plane-test",
		MailboxID:   "maintenance-test",
		CreatedAt:   at.Add(-time.Second),
		ExpiresAt:   at.Add(time.Hour),
		Action:      action,
		WorkOrderID: "V11110_STAGE_TEST_R1",
		Generation:  2,
	}
}

func TestBridgeMaintenanceExportIsGenerationBoundControl(t *testing.T) {
	at := time.Now().UTC()
	cfg := maintenanceBridgeConfig()
	cmd := maintenanceCommand(at, "export")
	if err := cmd.validate(cfg, at); err != nil {
		t.Fatalf("valid export rejected: %v", err)
	}
	cmd.Generation = 0
	if err := cmd.validate(cfg, at); err == nil || !strings.Contains(err.Error(), "CONTROL_ARGUMENTS_INVALID") {
		t.Fatalf("export without generation should fail closed, got %v", err)
	}
}

func TestBridgeMaintenanceExportRejectsExecutionArguments(t *testing.T) {
	at := time.Now().UTC()
	cfg := maintenanceBridgeConfig()
	cmd := maintenanceCommand(at, "export")
	cmd.Authorization = "operator"
	if err := cmd.validate(cfg, at); err == nil || !strings.Contains(err.Error(), "CONTROL_ARGUMENTS_INVALID") {
		t.Fatalf("export with execution arguments should fail closed, got %v", err)
	}
}

func TestBridgeMaintenanceRetryRequiresOperatorSource(t *testing.T) {
	at := time.Now().UTC()
	cfg := maintenanceBridgeConfig()
	cmd := maintenanceCommand(at, "retry")
	cmd.Authorization = "operator"
	cmd.Mode = "source"
	if err := cmd.validate(cfg, at); err != nil {
		t.Fatalf("valid bounded retry rejected: %v", err)
	}
	cmd.Authorization = "test"
	if err := cmd.validate(cfg, at); err == nil || !strings.Contains(err.Error(), "CONTROL_ARGUMENTS_INVALID") {
		t.Fatalf("retry without operator authorization should fail closed, got %v", err)
	}
}

func TestBridgeMaintenanceControlsRequireWritableBridge(t *testing.T) {
	at := time.Now().UTC()
	cfg := maintenanceBridgeConfig()
	cfg.ControlEnabled = false
	for _, action := range []string{"export", "retry"} {
		cmd := maintenanceCommand(at, action)
		if action == "retry" {
			cmd.Authorization = "operator"
			cmd.Mode = "source"
		}
		if err := cmd.validate(cfg, at); err == nil || !strings.Contains(err.Error(), "ACTION_NOT_ALLOWED_READ_ONLY_BRIDGE") {
			t.Fatalf("%s should require writable bridge, got %v", action, err)
		}
	}
}

func TestBridgeMaintenanceFailureDetailOnlyForFailedChecks(t *testing.T) {
	if got := bridgeFailureDetail(true, "sensitive passing detail"); got != "" {
		t.Fatalf("passing check detail must not leave the machine, got %q", got)
	}
	got := bridgeFailureDetail(false, "Missing explicit markers\r\nfor   Stage DZB")
	if got != "Missing explicit markers for Stage DZB" {
		t.Fatalf("unexpected bounded detail projection: %q", got)
	}
}

func TestBridgeMaintenanceFailureDetailIsBounded(t *testing.T) {
	got := bridgeFailureDetail(false, strings.Repeat("x", bridgeFailureDetailLimit+100))
	if len(got) != bridgeFailureDetailLimit {
		t.Fatalf("failure detail length=%d want=%d", len(got), bridgeFailureDetailLimit)
	}
}
