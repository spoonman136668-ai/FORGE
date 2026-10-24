package plane

import (
	"context"
	"database/sql"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type externalTestMailbox struct {
	published map[string][]byte
}

func (m *externalTestMailbox) Verify(context.Context, BridgeConfig) error  { return nil }
func (m *externalTestMailbox) List(context.Context) ([]bridgeEntry, error) { return nil, nil }
func (m *externalTestMailbox) Read(context.Context, bridgeEntry) ([]byte, error) {
	return nil, os.ErrNotExist
}
func (m *externalTestMailbox) Publish(_ context.Context, path string, raw []byte, _ bool) error {
	if m.published == nil {
		m.published = map[string][]byte{}
	}
	if old, ok := m.published[path]; ok && string(old) != string(raw) {
		return os.ErrExist
	}
	m.published[path] = append([]byte(nil), raw...)
	return nil
}

func externalTestOrder() WorkOrder {
	var w WorkOrder
	w.ID = "EXT_REPAIR_TEST"
	w.Title = "External repair test"
	w.Repo = "ckb"
	w.Baseline.Ref = "accepted/test"
	w.Baseline.SHA = strings.Repeat("a", 40)
	w.Worker.Branch = "codex/ext-repair-test"
	w.Worker.Preferred = "codex"
	w.Scope.Allowed = []string{"pkg/**"}
	w.Acceptance.ProtectRefs = true
	w.Acceptance.Clean = true
	return w
}

func TestExternalOrchestrator_RequestValidation(t *testing.T) {
	r := ExternalOrchestratorRepairRequest{
		Schema:        externalRepairSchema,
		RequestID:     "repair-1",
		WorkOrderID:   "EXT_REPAIR_TEST",
		Attempt:       1,
		HandoffSHA256: strings.Repeat("b", 64),
		Operations:    []ExternalOrchestratorEdit{{Type: "write_text", Path: "pkg/a.go", Content: "package pkg\n"}},
	}
	if err := r.validate(); err != nil {
		t.Fatal(err)
	}
	r.Attempt = 0
	if err := r.validate(); err == nil {
		t.Fatal("zero attempt accepted")
	}
	r.Attempt = 1
	r.HandoffSHA256 = "bad"
	if err := r.validate(); err == nil {
		t.Fatal("bad handoff hash accepted")
	}
}

func TestExternalOrchestrator_PreimageScopeAndRollback(t *testing.T) {
	workspace := t.TempDir()
	if err := os.MkdirAll(filepath.Join(workspace, "pkg"), 0700); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(workspace, "pkg", "a.go")
	before := []byte("package pkg\n\nconst A = 1\n")
	if err := os.WriteFile(path, before, 0600); err != nil {
		t.Fatal(err)
	}
	order := externalTestOrder()
	if err := order.Validate(); err != nil {
		t.Fatalf("fixture invalid: %v", err)
	}
	ops := []ExternalOrchestratorEdit{{
		Type:                 "write_text",
		Path:                 "pkg/a.go",
		ExpectedBeforeSHA256: digest(before),
		Content:              "package pkg\n\nconst A = 2\n",
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
	if !strings.Contains(string(got), "A = 2") {
		t.Fatalf("edit not applied: %q", got)
	}
	if err = rollbackExternalOperations(plans); err != nil {
		t.Fatal(err)
	}
	got, err = os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(before) {
		t.Fatalf("rollback mismatch: got=%q want=%q", got, before)
	}

	bad := ops
	bad[0].ExpectedBeforeSHA256 = strings.Repeat("c", 64)
	if _, err = planExternalOperations(workspace, order, bad); err == nil || !strings.Contains(err.Error(), "PREIMAGE_MISMATCH") {
		t.Fatalf("wrong preimage not rejected: %v", err)
	}
	forbidden := []ExternalOrchestratorEdit{{Type: "write_text", Path: ".github/workflows/x.yml", Content: "x"}}
	if _, err = planExternalOperations(workspace, order, forbidden); err == nil || !strings.Contains(err.Error(), "SCOPE_REFUSED") {
		t.Fatalf("forbidden scope not rejected: %v", err)
	}
}

func TestExternalOrchestrator_CreateDeleteContracts(t *testing.T) {
	workspace := t.TempDir()
	order := externalTestOrder()
	create := []ExternalOrchestratorEdit{{Type: "write_text", Path: "pkg/new.go", Content: "package pkg\n"}}
	plans, err := planExternalOperations(workspace, order, create)
	if err != nil {
		t.Fatal(err)
	}
	if err = applyExternalOperations(plans); err != nil {
		t.Fatal(err)
	}
	created := filepath.Join(workspace, "pkg", "new.go")
	raw, err := os.ReadFile(created)
	if err != nil {
		t.Fatal(err)
	}
	deleteOps := []ExternalOrchestratorEdit{{Type: "delete_file", Path: "pkg/new.go", ExpectedBeforeSHA256: digest(raw)}}
	deletePlans, err := planExternalOperations(workspace, order, deleteOps)
	if err != nil {
		t.Fatal(err)
	}
	if err = applyExternalOperations(deletePlans); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(created); !os.IsNotExist(err) {
		t.Fatalf("delete not applied: %v", err)
	}
	if err = rollbackExternalOperations(deletePlans); err != nil {
		t.Fatal(err)
	}
	if got, err := os.ReadFile(created); err != nil || string(got) != string(raw) {
		t.Fatalf("delete rollback failed: got=%q err=%v", got, err)
	}
}

func TestExternalOrchestrator_OutboxHandoffIsDurableAndSelfBinding(t *testing.T) {
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "bridge.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	mailbox := &externalTestMailbox{}
	b := &WebUIBridge{db: db, mailbox: mailbox}
	h := ObjectiveHandoff{
		Schema:           "ckb-plane.external-orchestrator-handoff.v1",
		WorkOrderID:      "EXT_REPAIR_TEST",
		Attempt:          1,
		Workspace:        `C:\plane\workspaces\s\abc\worktree`,
		Evidence:         `C:\plane\evidence\EXT_REPAIR_TEST\1`,
		BaselineSHA:      strings.Repeat("a", 40),
		QueueSHA:         strings.Repeat("b", 64),
		ManifestSHA:      strings.Repeat("c", 64),
		DeltaSHA:         strings.Repeat("d", 64),
		EvidenceComplete: true,
	}
	if err = b.queueExternalHandoff(h); err != nil {
		t.Fatal(err)
	}
	if err = b.queueExternalHandoff(h); err != nil {
		t.Fatalf("idempotent queue failed: %v", err)
	}
	if err = b.deliverPlaneOutbox(context.Background()); err != nil {
		t.Fatal(err)
	}
	if len(mailbox.published) != 1 {
		t.Fatalf("published=%d want=1", len(mailbox.published))
	}
	for path, raw := range mailbox.published {
		if !strings.HasPrefix(path, "outbox/external-") || !strings.HasSuffix(path, ".json") {
			t.Fatalf("unexpected path %q", path)
		}
		var payload struct {
			Schema        string           `json:"schema"`
			Type          string           `json:"type"`
			HandoffSHA256 string           `json:"handoff_sha256"`
			Handoff       ObjectiveHandoff `json:"handoff"`
		}
		if err = json.Unmarshal(raw, &payload); err != nil {
			t.Fatal(err)
		}
		if payload.Schema != externalHandoffWebUISchema || payload.Type != "external-orchestrator-handoff" || payload.Handoff.WorkOrderID != h.WorkOrderID {
			t.Fatalf("unexpected payload: %+v", payload)
		}
		if payload.HandoffSHA256 != digest([]byte(jsonText(h))) {
			t.Fatalf("handoff hash mismatch: %s", payload.HandoffSHA256)
		}
	}
}
