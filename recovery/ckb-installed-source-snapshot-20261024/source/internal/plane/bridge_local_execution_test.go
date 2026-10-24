package plane

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestLocalExecutionBridgeCommandIsGenerationBoundAndTyped(t *testing.T) {
	now := time.Now().UTC()
	cfg := BridgeConfig{
		Schema:           "ckb-plane.webui-bridge.v1",
		Repository:       "spoonman136668-ai/ckb",
		RepositoryID:     1349639063,
		Branch:           "ckb-plane/webui-test",
		MailboxID:        "test-mailbox",
		PlaneID:          "test-plane",
		TokenEnv:         "CKB_PLANE_GITHUB_TOKEN",
		PollSeconds:      30,
		HeartbeatSeconds: 300,
		ControlEnabled:   true,
	}
	command := BridgeCommand{
		Schema:      bridgeCommandSchema,
		ID:          "local-exec-test",
		PlaneID:     cfg.PlaneID,
		MailboxID:   cfg.MailboxID,
		CreatedAt:   now.Add(-time.Second),
		ExpiresAt:   now.Add(time.Minute),
		Action:      "local-exec",
		Generation:  2,
		InputSHA256: strings.Repeat("a", 64),
		OperationID: "plane-health",
		Parameters:  map[string]json.RawMessage{},
	}
	if err := command.validate(cfg, now); err != nil {
		t.Fatalf("local-exec command rejected: %v", err)
	}

	command.Generation = 0
	if err := command.validate(cfg, now); err == nil || err.Error() != "CONTROL_ARGUMENTS_INVALID" {
		t.Fatalf("expected generation-bound refusal, got %v", err)
	}
}

func TestLocalExecutionBridgeRejectsCommandShapedShellInput(t *testing.T) {
	now := time.Now().UTC()
	cfg := BridgeConfig{
		Schema:           "ckb-plane.webui-bridge.v1",
		Repository:       "spoonman136668-ai/ckb",
		RepositoryID:     1349639063,
		Branch:           "ckb-plane/webui-test",
		MailboxID:        "test-mailbox",
		PlaneID:          "test-plane",
		TokenEnv:         "CKB_PLANE_GITHUB_TOKEN",
		PollSeconds:      30,
		HeartbeatSeconds: 300,
		ControlEnabled:   true,
	}
	command := BridgeCommand{
		Schema:      bridgeCommandSchema,
		ID:          "local-exec-shell-refusal",
		PlaneID:     cfg.PlaneID,
		MailboxID:   cfg.MailboxID,
		CreatedAt:   now.Add(-time.Second),
		ExpiresAt:   now.Add(time.Minute),
		Action:      "local-exec",
		Generation:  2,
		InputSHA256: strings.Repeat("a", 64),
		OperationID: "plane-health",
		Parameters: map[string]json.RawMessage{
			"Command": json.RawMessage(`"Get-ChildItem;Remove-Item C:\\*"`),
		},
	}
	// Bridge shape can only carry named typed parameters. The operation registry is
	// the second gate and will reject undeclared names/unsafe values before launch.
	if err := command.validate(cfg, now); err != nil {
		t.Fatalf("bridge should preserve typed payload for registry validation: %v", err)
	}
}

func TestLocalExecutionFieldsAreRefusedOnOtherBridgeActions(t *testing.T) {
	now := time.Now().UTC()
	cfg := BridgeConfig{
		Schema:           "ckb-plane.webui-bridge.v1",
		Repository:       "spoonman136668-ai/ckb",
		RepositoryID:     1349639063,
		Branch:           "ckb-plane/webui-test",
		MailboxID:        "test-mailbox",
		PlaneID:          "test-plane",
		TokenEnv:         "CKB_PLANE_GITHUB_TOKEN",
		PollSeconds:      30,
		HeartbeatSeconds: 300,
		ControlEnabled:   true,
	}
	command := BridgeCommand{
		Schema:      bridgeCommandSchema,
		ID:          "status-smuggle",
		PlaneID:     cfg.PlaneID,
		MailboxID:   cfg.MailboxID,
		CreatedAt:   now.Add(-time.Second),
		ExpiresAt:   now.Add(time.Minute),
		Action:      "status",
		OperationID: "plane-health",
	}
	if err := command.validate(cfg, now); err == nil || err.Error() != "COMMAND_ARGUMENTS_INVALID" {
		t.Fatalf("expected smuggled local-exec fields to be rejected, got %v", err)
	}
}
