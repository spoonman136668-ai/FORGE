package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWebUIBridgeCLIConfigurationOnly(t *testing.T) {
	dir := t.TempDir()
	config := filepath.Join(dir, "local.yaml")
	bridge := filepath.Join(dir, "bridge.json")
	if e := os.WriteFile(config, []byte("state:\n  sqlite_path: state/plane.db\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(bridge, []byte(`{"schema":"ckb-plane.webui-bridge.v1","repository":"owner/private","repository_id":123,"branch":"ckb-plane/webui-mailbox","mailbox_id":"m","plane_id":"p","token_env":"CKB_PLANE_GITHUB_TOKEN","poll_seconds":60,"heartbeat_seconds":300}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e := run([]string{"bridge", "check-config", "--config", config, "--bridge-config", bridge}); e != nil {
		t.Fatal(e)
	}
	if _, e := os.Stat(filepath.Join(dir, "state")); !os.IsNotExist(e) {
		t.Fatal("configuration check wrote state")
	}
	if e := run([]string{"bridge", "dispatch"}); e == nil {
		t.Fatal("dispatch exposed")
	}
}
