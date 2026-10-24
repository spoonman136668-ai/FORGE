package plane

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDXAControlEvidencePreservesVerifiedSanitizedProjection(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	if err := p.Dispatch(w.ID); err != nil {
		t.Fatal(err)
	}
	j := wait(t, p, w.ID)
	if j.State != "ACCEPTED" {
		t.Fatal(j)
	}

	previousCalls := 0
	b := &WebUIBridge{}
	b.snapshot = func(ctx context.Context, c BridgeCommand) (any, error) {
		previousCalls++
		return map[string]any{
			"work_order_id": c.WorkOrderID,
			"state":         j.State,
			"attempt":       j.Attempt,
			"checks": []map[string]any{
				{"name": "BROWSER_CRITICAL_CONTROL", "pass": false},
			},
			"verification": "recorded_metadata_only_not_a_fresh_file_integrity_audit",
		}, nil
	}
	p.AttachBridge(b)

	v, err := b.snapshot(context.Background(), BridgeCommand{Action: "evidence", WorkOrderID: w.ID})
	if err != nil {
		t.Fatal(err)
	}
	m, ok := v.(map[string]any)
	if !ok {
		t.Fatalf("unexpected evidence projection type: %T", v)
	}
	if m["verified_now"] != true {
		t.Fatalf("fresh evidence verification missing: %#v", m)
	}
	if previousCalls != 1 {
		t.Fatalf("sanitized projection calls=%d want=1", previousCalls)
	}
	if !strings.Contains(strings.ToLower(strings.TrimSpace(toJSONForDXATest(m))), "browser_critical_control") {
		t.Fatalf("sanitized acceptance check projection missing: %#v", m)
	}

	// Fresh evidence verification must remain authoritative: corrupting a sealed
	// artifact must fail before the metadata-only projection can be returned.
	if err := os.WriteFile(filepath.Join(j.Evidence, "worker_stdout.log"), []byte("changed"), 0600); err != nil {
		t.Fatal(err)
	}
	manifest, err := Manifest(j.Evidence)
	if err != nil {
		t.Fatal(err)
	}
	if err := writeJSON(filepath.Join(j.Evidence, "evidence_manifest.json"), manifest); err != nil {
		t.Fatal(err)
	}
	previousCalls = 0
	if _, err := b.snapshot(context.Background(), BridgeCommand{Action: "evidence", WorkOrderID: w.ID}); err == nil {
		t.Fatal("corrupt sealed evidence was exported")
	}
	if previousCalls != 0 {
		t.Fatalf("projection ran before fresh verification: calls=%d", previousCalls)
	}
}

func toJSONForDXATest(v any) string {
	return jsonText(v)
}
