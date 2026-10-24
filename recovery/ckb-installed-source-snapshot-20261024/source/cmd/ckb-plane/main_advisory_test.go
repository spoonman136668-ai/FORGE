package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"ckb-plane/internal/plane"
)

func TestAdvisoryCLIBypassesEngineAndQueueState(t *testing.T) {
	root := t.TempDir()
	configDir := filepath.Join(root, "config")
	if err := os.Mkdir(configDir, 0700); err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(configDir, "autonomy.yaml")
	config := `advisory:
    opencode:
        enabled: false
        manual_only: true
        model: openrouter/nvidia/nemotron-3-super-120b-a12b:free
        api_key_env: OPENROUTER_API_KEY
        executable_sha256: 0242a0dc705af67c90882b456a36b619883c1c786aad8fe071a1bc64e5d1d440
        timeout_seconds: 180
tools:
    opencode: C:\unused\opencode.exe
state:
    sqlite_path: state/autonomy.db
`
	if err := os.WriteFile(configPath, []byte(config), 0600); err != nil {
		t.Fatal(err)
	}

	packet := plane.OpenCodeAdvisoryPacket{
		Schema:             "ckb-plane.opencode-advisory-packet.v1",
		RequestID:          "cli_activation_guard_001",
		Purpose:            "Prove the manual advisory CLI does not instantiate queue state.",
		DataClassification: "synthetic",
		Context:            "Synthetic CLI guard packet.",
	}
	raw, err := json.Marshal(packet)
	if err != nil {
		t.Fatal(err)
	}
	packetPath := filepath.Join(root, "packet.json")
	if err := os.WriteFile(packetPath, raw, 0600); err != nil {
		t.Fatal(err)
	}

	err = run([]string{"advisory", "run", "--config", configPath, "--file", packetPath})
	if err == nil || err.Error() != "OPENCODE_ADVISORY_NOT_ENABLED" {
		t.Fatalf("unexpected advisory CLI result: %v", err)
	}
	if _, statErr := os.Lstat(filepath.Join(root, "state", "autonomy.db")); !os.IsNotExist(statErr) {
		t.Fatalf("advisory CLI created autonomy DB: %v", statErr)
	}
	if _, statErr := os.Lstat(filepath.Join(root, "workorders")); !os.IsNotExist(statErr) {
		t.Fatalf("advisory CLI touched workorder state: %v", statErr)
	}
}
