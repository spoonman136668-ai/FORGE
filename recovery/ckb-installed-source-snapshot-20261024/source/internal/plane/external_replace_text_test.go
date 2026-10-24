package plane

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestExternalOrchestrator_ReplaceTextLargeFilePreimageAndRollback(t *testing.T) {
	workspace := t.TempDir()
	if err := os.MkdirAll(filepath.Join(workspace, "pkg"), 0700); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(workspace, "pkg", "large.js")
	before := []byte(strings.Repeat("x", 96<<10) + "\nconst uniqueAnchor = 1;\n" + strings.Repeat("y", 96<<10))
	if err := os.WriteFile(path, before, 0600); err != nil {
		t.Fatal(err)
	}
	order := externalTestOrder()
	payload, _ := json.Marshal(externalReplaceTextPayload{Old: "const uniqueAnchor = 1;", New: "const uniqueAnchor = 2;"})
	ops := []ExternalOrchestratorEdit{{
		Type:                 "replace_text",
		Path:                 "pkg/large.js",
		ExpectedBeforeSHA256: digest(before),
		Content:              string(payload),
	}}
	plans, err := planExternalOperations(workspace, order, ops)
	if err != nil {
		t.Fatal(err)
	}
	if err = applyExternalOperations(plans); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(got), "const uniqueAnchor = 2;") || strings.Contains(string(got), "const uniqueAnchor = 1;") {
		t.Fatal("replace_text did not replace unique anchor")
	}
	if err = rollbackExternalOperations(plans); err != nil {
		t.Fatal(err)
	}
	got, err = os.ReadFile(path)
	if err != nil || string(got) != string(before) {
		t.Fatalf("rollback mismatch err=%v", err)
	}
}

func TestExternalOrchestrator_ReplaceTextFailsClosed(t *testing.T) {
	workspace := t.TempDir()
	if err := os.MkdirAll(filepath.Join(workspace, "pkg"), 0700); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(workspace, "pkg", "a.js")
	before := []byte("anchor\nanchor\n")
	if err := os.WriteFile(path, before, 0600); err != nil {
		t.Fatal(err)
	}
	order := externalTestOrder()
	payload, _ := json.Marshal(externalReplaceTextPayload{Old: "anchor", New: "changed"})
	base := ExternalOrchestratorEdit{Type: "replace_text", Path: "pkg/a.js", ExpectedBeforeSHA256: digest(before), Content: string(payload)}
	if _, err := planExternalOperations(workspace, order, []ExternalOrchestratorEdit{base}); err == nil || !strings.Contains(err.Error(), "MATCH_COUNT") {
		t.Fatalf("duplicate anchor did not fail closed: %v", err)
	}
	base.ExpectedBeforeSHA256 = strings.Repeat("a", 64)
	if _, err := planExternalOperations(workspace, order, []ExternalOrchestratorEdit{base}); err == nil || !strings.Contains(err.Error(), "PREIMAGE_MISMATCH") {
		t.Fatalf("wrong preimage did not fail closed: %v", err)
	}
	bad, _ := json.Marshal(externalReplaceTextPayload{Old: "", New: "changed"})
	base.ExpectedBeforeSHA256 = digest(before)
	base.Content = string(bad)
	if _, err := planExternalOperations(workspace, order, []ExternalOrchestratorEdit{base}); err == nil || !strings.Contains(err.Error(), "PAYLOAD_INVALID") {
		t.Fatalf("empty old anchor did not fail closed: %v", err)
	}
}
