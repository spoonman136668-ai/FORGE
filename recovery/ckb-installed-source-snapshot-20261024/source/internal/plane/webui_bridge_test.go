package plane

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

type memoryMailbox struct {
	input       map[string][]byte
	output      map[string][]byte
	failPublish bool
	failVerify  bool
}

func (m *memoryMailbox) Verify(context.Context, BridgeConfig) error {
	if m.failVerify {
		return errors.New("verify failed")
	}
	return nil
}
func (m *memoryMailbox) List(context.Context) ([]bridgeEntry, error) {
	var out []bridgeEntry
	for id, raw := range m.input {
		out = append(out, bridgeEntry{id + ".json", bridgeBlobSHA(raw)})
	}
	return out, nil
}
func (m *memoryMailbox) Read(_ context.Context, e bridgeEntry) ([]byte, error) {
	return m.input[strings.TrimSuffix(e.Name, ".json")], nil
}
func (m *memoryMailbox) Publish(_ context.Context, p string, raw []byte, replace bool) error {
	if m.failPublish {
		return errors.New("offline")
	}
	if old, ok := m.output[p]; ok && !replace && !bytes.Equal(old, raw) {
		return errors.New("conflict")
	}
	m.output[p] = append([]byte{}, raw...)
	return nil
}

func bridgeTestConfig() BridgeConfig {
	return BridgeConfig{Schema: "ckb-plane.webui-bridge.v1", Repository: "owner/private", RepositoryID: 123, Branch: "ckb-plane/webui-mailbox", MailboxID: "test-mailbox", PlaneID: "test-plane", TokenEnv: "CKB_PLANE_GITHUB_TOKEN", PollSeconds: 60, HeartbeatSeconds: 300}
}
func bridgeTestCommand(id, action string) BridgeCommand {
	at := time.Now().UTC()
	return BridgeCommand{Schema: bridgeCommandSchema, ID: id, PlaneID: "test-plane", MailboxID: "test-mailbox", CreatedAt: at, ExpiresAt: at.Add(time.Hour), Action: action}
}
func bridgeTest(t *testing.T) (*WebUIBridge, *memoryMailbox) {
	t.Helper()
	m := &memoryMailbox{input: map[string][]byte{}, output: map[string][]byte{}}
	b, e := openWebUIBridge(t.TempDir(), "state/plane.db", bridgeTestConfig(), m)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { b.Close() })
	return b, m
}
func putCommand(m *memoryMailbox, c BridgeCommand) { m.input[c.ID], _ = json.Marshal(c) }
func getResult(t *testing.T, m *memoryMailbox, id string) BridgeResult {
	t.Helper()
	var r BridgeResult
	if e := json.Unmarshal(m.output["outbox/"+id+".json"], &r); e != nil {
		t.Fatal(e)
	}
	return r
}

func TestWebUIBridgeRoundTripAndDeduplication(t *testing.T) {
	b, m := bridgeTest(t)
	putCommand(m, bridgeTestCommand("hello", "ping"))
	calls := 0
	original := b.snapshot
	b.snapshot = func(ctx context.Context, c BridgeCommand) (any, error) { calls++; return original(ctx, c) }
	for i := 0; i < 2; i++ {
		if e := b.Once(context.Background()); e != nil {
			t.Fatal(e)
		}
	}
	r := getResult(t, m, "hello")
	if r.Status != "succeeded" || !r.ReadOnly || r.CommandSHA256 != digest(m.input["hello"]) || calls != 1 {
		t.Fatalf("result=%+v calls=%d", r, calls)
	}
	if m.output["status/heartbeat.json"] == nil {
		t.Fatal("heartbeat missing")
	}
}

func TestWebUIBridgeRejectsMutationAndMalformedCommands(t *testing.T) {
	for _, action := range []string{"dispatch", "authorize", "retry", "accept", "resume", "pause", "load", "shell", "run-pending", "deploy"} {
		t.Run(action, func(t *testing.T) {
			b, m := bridgeTest(t)
			putCommand(m, bridgeTestCommand("refuse", action))
			b.snapshot = func(context.Context, BridgeCommand) (any, error) {
				t.Fatal("forbidden action reached observation")
				return nil, nil
			}
			if e := b.Once(context.Background()); e != nil {
				t.Fatal(e)
			}
			if r := getResult(t, m, "refuse"); r.Code != "ACTION_NOT_ALLOWED_READ_ONLY_BRIDGE" || r.Status != "refused" {
				t.Fatalf("%+v", r)
			}
		})
	}
	for _, kind := range []string{"expired", "wrong-plane", "wrong-mailbox", "wrong-file", "extra-field", "duplicate", "null", "future", "long-ttl"} {
		t.Run(kind, func(t *testing.T) {
			b, m := bridgeTest(t)
			c := bridgeTestCommand("invalid", "ping")
			switch kind {
			case "expired":
				c.ExpiresAt = time.Now().Add(-time.Hour)
			case "wrong-plane":
				c.PlaneID = "other"
			case "wrong-mailbox":
				c.MailboxID = "other"
			case "future":
				c.CreatedAt = time.Now().Add(time.Hour)
				c.ExpiresAt = c.CreatedAt.Add(time.Hour)
			case "long-ttl":
				c.ExpiresAt = c.CreatedAt.Add(48 * time.Hour)
			}
			putCommand(m, c)
			switch kind {
			case "wrong-file":
				m.input["other"] = m.input[c.ID]
				delete(m.input, c.ID)
			case "extra-field":
				m.input[c.ID] = append(m.input[c.ID][:len(m.input[c.ID])-1], []byte(`,"shell":"go run ."}`)...)
			case "duplicate":
				m.input[c.ID] = append(m.input[c.ID][:len(m.input[c.ID])-1], []byte(`,"action":"dispatch"}`)...)
			case "null":
				m.input[c.ID] = []byte("null")
			}
			b.snapshot = func(context.Context, BridgeCommand) (any, error) {
				t.Fatal("invalid request reached observer")
				return nil, nil
			}
			if e := b.Once(context.Background()); e != nil {
				t.Fatal(e)
			}
			id := c.ID
			if kind == "wrong-file" {
				id = "other"
			}
			if r := getResult(t, m, id); r.Status != "refused" {
				t.Fatalf("%+v", r)
			}
		})
	}
}

func TestWebUIBridgePublishRetryUsesDurableResult(t *testing.T) {
	b, m := bridgeTest(t)
	putCommand(m, bridgeTestCommand("retry", "ping"))
	calls := 0
	b.snapshot = func(context.Context, BridgeCommand) (any, error) {
		calls++
		return map[string]int{"observation": calls}, nil
	}
	m.failPublish = true
	if e := b.Once(context.Background()); e == nil {
		t.Fatal("expected delivery failure")
	}
	var original []byte
	if e := b.db.QueryRow("SELECT result FROM commands WHERE id='retry'").Scan(&original); e != nil {
		t.Fatal(e)
	}
	m.failPublish = false
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if calls != 1 || !bytes.Equal(original, m.output["outbox/retry.json"]) {
		t.Fatal("re-observed or changed result")
	}
	c := bridgeTestCommand("retry", "status")
	putCommand(m, c)
	if e := b.Once(context.Background()); e == nil || e.Error() != "BRIDGE_COMMAND_ID_REUSED" {
		t.Fatalf("expected ID conflict: %v", e)
	}
}

func TestWebUIBridgeLockAndIdentity(t *testing.T) {
	b, m := bridgeTest(t)
	if other, e := openWebUIBridge(b.Root, "state/plane.db", b.Config, m); e == nil {
		other.Close()
		t.Fatal("second bridge acquired lock")
	}
	if e := b.Close(); e != nil {
		t.Fatal(e)
	}
	c := b.Config
	c.MailboxID = "different"
	if other, e := openWebUIBridge(b.Root, "state/plane.db", c, m); e == nil {
		other.Close()
		t.Fatal("ledger identity silently changed")
	}
}

func TestWebUIBridgeOnlyObservesPlaneDatabase(t *testing.T) {
	b, m := bridgeTest(t)
	s, e := OpenStore(b.PlaneState)
	if e != nil {
		t.Fatal(e)
	}
	_, e = s.DB.Exec(`INSERT INTO work_orders(id,yaml,state,attempt,evidence) VALUES('ORDER_1','private prompt secret','ACCEPTED',1,'private/path');
INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES('now','ORDER_1',1,'ACCEPTED','INFO','SECRET RAW EVENT','{}');
INSERT INTO evidence_seals VALUES('ORDER_1',1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
INSERT INTO acceptance_runs(id,work_order_id,attempt,result) VALUES(1,'ORDER_1',1,'PASS');
INSERT INTO acceptance_checks(run_id,name,pass,detail) VALUES(1,'FOCUSED_TEST',1,'SECRET DETAIL');`)
	if e != nil {
		t.Fatal(e)
	}
	s.DB.Close()
	before, e := os.ReadFile(b.PlaneState)
	if e != nil {
		t.Fatal(e)
	}
	for _, action := range []string{"status", "workorder", "events", "evidence"} {
		c := bridgeTestCommand(action, action)
		if action == "workorder" || action == "evidence" {
			c.WorkOrderID = "ORDER_1"
		}
		putCommand(m, c)
	}
	if e = b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	for _, action := range []string{"status", "workorder", "events", "evidence"} {
		r := getResult(t, m, action)
		if r.Status != "succeeded" {
			t.Fatalf("%s: %+v", action, r)
		}
		raw := string(m.output["outbox/"+action+".json"])
		for _, secret := range []string{"SECRET", "private prompt", "private/path"} {
			if strings.Contains(raw, secret) {
				t.Fatal("unapproved content exported")
			}
		}
	}
	after, e := os.ReadFile(b.PlaneState)
	if e != nil {
		t.Fatal(e)
	}
	if !bytes.Equal(before, after) {
		t.Fatal("plane DB changed")
	}
}

func TestWebUIBridgeMissingPlaneStateDoesNotCreateIt(t *testing.T) {
	b, m := bridgeTest(t)
	putCommand(m, bridgeTestCommand("status", "status"))
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if r := getResult(t, m, "status"); r.Status != "blocked" {
		t.Fatal(r)
	}
	if _, e := os.Stat(b.PlaneState); !os.IsNotExist(e) {
		t.Fatal("plane state was created")
	}
}
func TestWebUIBridgeConfigAndContainment(t *testing.T) {
	for _, branch := range []string{"main", "accepted/x", "orchestration/ckb-codex", "ckb-plane/webui-../x"} {
		c := bridgeTestConfig()
		c.Branch = branch
		if c.Validate() == nil {
			t.Fatal("bad branch accepted")
		}
	}
	root := t.TempDir()
	if e := bridgeContained(root, filepath.Join(root, "..", "outside")); e == nil {
		t.Fatal("outside accepted")
	}
	if e := os.Symlink(t.TempDir(), filepath.Join(root, "alias")); e == nil {
		if bridgeContained(root, filepath.Join(root, "alias", "state.db")) == nil {
			t.Fatal("external symlink accepted")
		}
	}
}

type bridgeRoundTrip func(*http.Request) (*http.Response, error)

func (f bridgeRoundTrip) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }
func bridgeHTTPResponse(status int, v any) *http.Response {
	raw, _ := json.Marshal(v)
	return &http.Response{StatusCode: status, Header: http.Header{}, Body: io.NopCloser(bytes.NewReader(raw))}
}
func gitContent(raw []byte) map[string]any {
	return map[string]any{"type": "file", "encoding": "base64", "size": len(raw), "sha": bridgeBlobSHA(raw), "content": base64.StdEncoding.EncodeToString(raw)}
}

func TestWebUIBridgeGitHubTransport(t *testing.T) {
	c := bridgeTestConfig()
	m := newGitHubMailbox(c, "test-token-never-log")
	stored := map[string][]byte{}
	manifest, _ := json.Marshal(map[string]any{"schema": "ckb-plane.webui-mailbox.v1", "plane_id": c.PlaneID, "mailbox_id": c.MailboxID, "read_only": true})
	stored["/repos/owner/private/contents/bridge/mailbox.json"] = manifest
	command, _ := json.Marshal(bridgeTestCommand("ping", "ping"))
	cmdSHA := bridgeBlobSHA(command)
	writes := 0
	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		if r.URL.Scheme != "https" || r.URL.Host != "api.github.com" || r.Header.Get("Authorization") != "Bearer test-token-never-log" {
			t.Fatal("wrong destination/auth")
		}
		switch r.URL.Path {
		case "/repos/owner/private":
			return bridgeHTTPResponse(200, map[string]any{"id": 123, "private": true, "full_name": "owner/private"}), nil
		case "/repos/owner/private/contents/bridge/inbox":
			return bridgeHTTPResponse(200, []any{map[string]any{"name": "ping.json", "type": "file", "sha": cmdSHA, "size": len(command)}}), nil
		case "/repos/owner/private/git/blobs/" + cmdSHA:
			return bridgeHTTPResponse(200, gitContent(command)), nil
		}
		if r.Method == "GET" {
			if r.URL.Query().Get("ref") != c.Branch {
				t.Fatal("missing branch")
			}
			raw, ok := stored[r.URL.Path]
			if !ok {
				return bridgeHTTPResponse(404, map[string]string{"message": "not found"}), nil
			}
			return bridgeHTTPResponse(200, gitContent(raw)), nil
		}
		if r.Method != "PUT" {
			t.Fatal("unexpected mutation")
		}
		var payload map[string]string
		if e := json.NewDecoder(r.Body).Decode(&payload); e != nil {
			t.Fatal(e)
		}
		if payload["branch"] != c.Branch || !strings.Contains(payload["message"], "[skip ci]") {
			t.Fatal("wrong write branch")
		}
		raw, e := base64.StdEncoding.DecodeString(payload["content"])
		if e != nil {
			t.Fatal(e)
		}
		stored[r.URL.Path] = raw
		writes++
		return bridgeHTTPResponse(201, map[string]any{}), nil
	})
	ctx := context.Background()
	if e := m.Verify(ctx, c); e != nil {
		t.Fatal(e)
	}
	entries, e := m.List(ctx)
	if e != nil || len(entries) != 1 {
		t.Fatal(entries, e)
	}
	raw, e := m.Read(ctx, entries[0])
	if e != nil || !bytes.Equal(raw, command) {
		t.Fatal(e)
	}
	for i := 0; i < 2; i++ {
		if e = m.Publish(ctx, "outbox/ping.json", []byte(`{"ok":true}`), false); e != nil {
			t.Fatal(e)
		}
	}
	if writes != 1 {
		t.Fatal("duplicate commit")
	}
	if e = m.Publish(ctx, "outbox/ping.json", []byte(`{"different":true}`), false); e == nil {
		t.Fatal("overwrote result")
	}
	if e = m.Publish(ctx, "../../main", nil, true); e == nil {
		t.Fatal("unsafe publish")
	}
}

func TestWebUIBridgeTransportFailsClosed(t *testing.T) {
	for _, status := range []int{401, 403, 429, 500} {
		t.Run(fmt.Sprint(status), func(t *testing.T) {
			m := newGitHubMailbox(bridgeTestConfig(), "never-print-me")
			m.client.Transport = bridgeRoundTrip(func(*http.Request) (*http.Response, error) {
				return bridgeHTTPResponse(status, map[string]string{"message": "never-print-me"}), nil
			})
			e := m.Verify(context.Background(), m.cfg)
			if e == nil || strings.Contains(e.Error(), "never-print-me") {
				t.Fatal(e)
			}
		})
	}
	m := newGitHubMailbox(bridgeTestConfig(), "token")
	m.client.Transport = bridgeRoundTrip(func(*http.Request) (*http.Response, error) {
		return bridgeHTTPResponse(200, map[string]any{"id": 123, "private": false, "full_name": "owner/private"}), nil
	})
	if e := m.Verify(context.Background(), m.cfg); e == nil {
		t.Fatal("public repo accepted")
	}
	if m.client.CheckRedirect(&http.Request{}, nil) == nil {
		t.Fatal("redirect allowed")
	}
}
