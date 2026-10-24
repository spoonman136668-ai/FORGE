package plane

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func prepareExternalWaitingAckFixture(t *testing.T) (*Engine, WorkOrder) {
	t.Helper()
	p, w := setup(t)
	raw, err := os.ReadFile(filepath.Join(p.Root, "workorder.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Load(raw); err != nil {
		t.Fatal(err)
	}
	workspace := filepath.Join(p.Root, "workspaces", "held", "worktree")
	evidence := filepath.Join(p.Root, "evidence", w.ID, "2")
	if err = os.MkdirAll(workspace, 0700); err != nil {
		t.Fatal(err)
	}
	if err = os.MkdirAll(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"UPDATE work_orders SET state='BLOCKED',attempt=2,reason='CODEX_QUOTA_EXHAUSTED',workspace=?,evidence=? WHERE id=?",
		workspace, evidence, w.ID,
	); err != nil {
		t.Fatal(err)
	}
	queueRaw := []byte("{\"fixture\":\"external-wait\"}")
	if _, err = p.Store.DB.Exec(
		"INSERT INTO queue_items(id,hash,raw,kind,state,mode,authorization,reason,updated) VALUES(?,?,?,?,?,?,?,?,?)",
		w.ID, digest(queueRaw), queueRaw, "source", "WAITING_FOR_EXTERNAL_ORCHESTRATOR", "source", "operator", "CODEX_QUOTA_EXHAUSTED", now(),
	); err != nil {
		t.Fatal(err)
	}
	j, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Seal(j); err != nil {
		t.Fatal(err)
	}
	h := ObjectiveHandoff{
		Schema:           "ckb-plane.external-orchestrator-handoff.v1",
		WorkOrderID:      w.ID,
		Attempt:          j.Attempt,
		Workspace:        workspace,
		Evidence:         evidence,
		BaselineRef:      w.Baseline.Ref,
		BaselineSHA:      w.Baseline.SHA,
		EvidenceComplete: true,
	}
	handoffDir := filepath.Join(p.Root, "evidence", "external-handoff", w.ID)
	if err = os.MkdirAll(handoffDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(handoffDir, "2.json"), h); err != nil {
		t.Fatal(err)
	}
	return p, w
}

func TestExternalWaitingAcknowledgeReviewsWithoutAcceptance(t *testing.T) {
	p, w := prepareExternalWaitingAckFixture(t)
	result, err := p.LocalControl(context.Background(), "acknowledge", w.ID)
	if err != nil {
		t.Fatal(err)
	}
	got, ok := result.(map[string]string)
	if !ok || got["state"] != "REVIEWED" {
		t.Fatalf("unexpected result: %#v", result)
	}
	var queueState, workState string
	if err = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", w.ID).Scan(&queueState); err != nil {
		t.Fatal(err)
	}
	if err = p.Store.DB.QueryRow("SELECT state FROM work_orders WHERE id=?", w.ID).Scan(&workState); err != nil {
		t.Fatal(err)
	}
	if queueState != "REVIEWED" || workState == "ACCEPTED" {
		t.Fatalf("queue=%s work=%s", queueState, workState)
	}
	handoff := filepath.Join(p.Root, "evidence", "external-handoff", w.ID, "2.json")
	if _, err = os.Stat(handoff); err != nil {
		t.Fatalf("handoff not preserved: %v", err)
	}
	events, err := p.Store.Events(0)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, e := range events {
		if e.WorkOrderID == w.ID && e.Attempt == 2 && e.Type == "EXTERNAL_ORCHESTRATOR_REVIEWED" {
			found = true
		}
	}
	if !found {
		t.Fatal("review audit event missing")
	}
}

func TestExternalWaitingAcknowledgeRefusesOwnedWorker(t *testing.T) {
	p, w := prepareExternalWaitingAckFixture(t)
	if _, err := p.Store.DB.Exec(
		"INSERT INTO worker_leases(work_order_id,attempt,owner,created) VALUES(?,?,?,?)",
		w.ID, 2, "fixture", now(),
	); err != nil {
		t.Fatal(err)
	}
	_, err := p.LocalControl(context.Background(), "acknowledge", w.ID)
	if err == nil || !strings.Contains(err.Error(), "REQUIRES_RELEASED_WORKER") {
		t.Fatalf("expected owned-worker refusal, got %v", err)
	}
	var state string
	if e := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", w.ID).Scan(&state); e != nil {
		t.Fatal(e)
	}
	if state != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		t.Fatalf("state mutated on refusal: %s", state)
	}
}

func TestExternalWaitingAcknowledgePreservesLegacyBlockedContract(t *testing.T) {
	p, w := setup(t)
	raw, err := os.ReadFile(filepath.Join(p.Root, "workorder.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Load(raw); err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"INSERT INTO queue_items(id,hash,raw,kind,state,mode,authorization,reason,updated) VALUES(?,?,?,?,?,?,?,?,?)",
		w.ID, strings.Repeat("a", 64), []byte("{}"), "source", "BLOCKED", "source", "operator", "fixture", now(),
	); err != nil {
		t.Fatal(err)
	}
	result, err := p.LocalControl(context.Background(), "acknowledge", w.ID)
	if err != nil {
		t.Fatal(err)
	}
	got := result.(map[string]string)
	if got["state"] != "REVIEWED" {
		t.Fatalf("legacy acknowledge changed: %#v", got)
	}
}
