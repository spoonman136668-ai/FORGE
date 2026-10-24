package plane

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"testing"
)

type durableArchiveTestMailbox struct {
	*memoryMailbox
	archived map[string][]byte
	fail     bool
}

func (m *durableArchiveTestMailbox) Archive(_ context.Context, entry bridgeEntry) error {
	if m.fail {
		return errors.New("archive offline")
	}
	id := strings.TrimSuffix(entry.Name, ".json")
	raw, ok := m.input[id]
	if !ok {
		return errors.New("archive input missing")
	}
	if bridgeBlobSHA(raw) != entry.SHA {
		return errors.New("archive sha mismatch")
	}
	path, e := bridgeArchivePath(entry)
	if e != nil {
		return e
	}
	if old, ok := m.archived[path]; ok && !bytes.Equal(old, raw) {
		return errors.New("archive conflict")
	}
	m.archived[path] = append([]byte{}, raw...)
	delete(m.input, id)
	return nil
}

func TestWebUIBridgeDurableArchiveCompactsOnlyDeliveredCommands(t *testing.T) {
	base := &memoryMailbox{input: map[string][]byte{}, output: map[string][]byte{}}
	m := &durableArchiveTestMailbox{memoryMailbox: base, archived: map[string][]byte{}}
	b, e := openWebUIBridge(t.TempDir(), "state/plane.db", bridgeTestConfig(), m)
	if e != nil {
		t.Fatal(e)
	}
	defer b.Close()

	putCommand(base, bridgeTestCommand("archive-me", "ping"))
	original := append([]byte{}, base.input["archive-me"]...)

	if e = b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}

	if _, ok := base.input["archive-me"]; ok {
		t.Fatal("delivered command remained in active inbox")
	}
	entry := bridgeEntry{Name: "archive-me.json", SHA: bridgeBlobSHA(original)}
	archivePath, e := bridgeArchivePath(entry)
	if e != nil {
		t.Fatal(e)
	}
	if !bytes.Equal(m.archived[archivePath], original) {
		t.Fatal("archive did not preserve exact command bytes")
	}

	putCommand(base, bridgeTestCommand("not-delivered", "ping"))
	raw := base.input["not-delivered"]
	if _, e = b.db.Exec(
		"INSERT INTO commands(id,blob_sha,input_hash,result,delivered) VALUES(?,?,?,?,0)",
		"not-delivered", bridgeBlobSHA(raw), digest(raw), []byte(`{"pending":true}`),
	); e != nil {
		t.Fatal(e)
	}

	entries, e := m.List(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	if e = b.compactDeliveredMailboxEntries(context.Background(), entries); e != nil {
		t.Fatal(e)
	}
	if _, ok := base.input["not-delivered"]; !ok {
		t.Fatal("undelivered command was compacted")
	}
}

func TestWebUIBridgeTreeFallbackEscapesContentsLimit(t *testing.T) {
	c := bridgeTestConfig()
	m := newGitHubMailbox(c, "test-token-never-log")
	full := make([]map[string]any, 1000)
	for i := range full {
		full[i] = map[string]any{
			"name": fmt.Sprintf("old-%04d.json", i),
			"type": "file",
			"sha":  strings.Repeat("a", 40),
			"size": 1,
		}
	}
	refSHA := strings.Repeat("b", 40)
	treeSHA := strings.Repeat("c", 40)
	itemSHA := strings.Repeat("d", 40)

	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		switch {
		case strings.Contains(r.URL.Path, "/contents/bridge/inbox"):
			return bridgeHTTPResponse(200, full), nil
		case strings.Contains(r.URL.Path, "/git/ref/heads/"):
			return bridgeHTTPResponse(200, map[string]any{"object": map[string]any{"sha": refSHA}}), nil
		case strings.Contains(r.URL.Path, "/git/commits/"):
			return bridgeHTTPResponse(200, map[string]any{"tree": map[string]any{"sha": treeSHA}}), nil
		case strings.Contains(r.URL.Path, "/git/trees/"):
			return bridgeHTTPResponse(200, map[string]any{
				"truncated": false,
				"tree": []map[string]any{
					{"path": "bridge/inbox/from-tree.json", "type": "blob", "sha": itemSHA, "size": 1},
				},
			}), nil
		default:
			return bridgeHTTPResponse(404, map[string]string{"message": "not found"}), nil
		}
	})

	entries, e := m.List(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	if len(entries) != 1 || entries[0].Name != "from-tree.json" || entries[0].SHA != itemSHA {
		t.Fatalf("unexpected tree fallback entries: %+v", entries)
	}
}

func TestWebUIBridgeDurableArchiveFailureDoesNotReobserve(t *testing.T) {
	base := &memoryMailbox{input: map[string][]byte{}, output: map[string][]byte{}}
	m := &durableArchiveTestMailbox{memoryMailbox: base, archived: map[string][]byte{}, fail: true}
	b, e := openWebUIBridge(t.TempDir(), "state/plane.db", bridgeTestConfig(), m)
	if e != nil {
		t.Fatal(e)
	}
	defer b.Close()

	putCommand(base, bridgeTestCommand("archive-retry", "ping"))
	calls := 0
	b.snapshot = func(context.Context, BridgeCommand) (any, error) {
		calls++
		return map[string]int{"observation": calls}, nil
	}

	if e = b.Once(context.Background()); e == nil {
		t.Fatal("expected archive failure")
	}
	if calls != 1 {
		t.Fatalf("unexpected observations: %d", calls)
	}

	m.fail = false
	if e = b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if calls != 1 {
		t.Fatal("archive retry re-observed delivered command")
	}
}
