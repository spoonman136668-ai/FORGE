package plane

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
)

// Explicit local setup operation. Only the already-bound mailbox manifest is
// updated; no workflows, source branches or accepted refs are touched.
func EnableBridgeControl(ctx context.Context, file string, enable bool) error {
	c, e := LoadBridgeConfig(file)
	if e != nil {
		return e
	}
	token := os.Getenv(c.TokenEnv)
	if token == "" {
		return errors.New("BRIDGE_TOKEN_MISSING")
	}
	m := newGitHubMailbox(c, token)
	old := c
	old.ControlEnabled = false
	if e = m.Verify(ctx, old); e != nil {
		old.ControlEnabled = true
		if e = m.Verify(ctx, old); e != nil {
			return e
		}
	}
	_, sha, _, e := m.get(ctx, "mailbox.json")
	if e != nil {
		return e
	}
	schema := "ckb-plane.webui-mailbox.v1"
	if enable {
		schema = "ckb-plane.webui-mailbox.v2"
	}
	raw, _ := json.MarshalIndent(map[string]any{"schema": schema, "plane_id": c.PlaneID, "mailbox_id": c.MailboxID, "read_only": !enable}, "", "  ")
	payload := map[string]any{"message": "Configure CKB-plane mailbox capabilities [skip ci]", "branch": c.Branch, "sha": sha, "content": base64.StdEncoding.EncodeToString(raw)}
	if _, e = m.api(ctx, "PUT", "/contents/bridge/mailbox.json", payload, nil); e != nil {
		return e
	}
	c.ControlEnabled = enable
	raw, _ = json.MarshalIndent(c, "", "  ")
	temp := filepath.Join(filepath.Dir(file), "bridge-config-"+randomID()+".tmp")
	if e = durableNew(temp, raw); e != nil {
		return e
	}
	// Existing config is backed up by the installer; replacement does not alter
	// mailbox identity or clear the durable request ledger.
	if e = os.Rename(temp, file); e != nil {
		return e
	}
	return nil
}
