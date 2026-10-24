package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func prepareCodexQuotaRearmFixture(t *testing.T) (*Engine, WorkOrder, string) {
	t.Helper()
	p, w := setup(t)
	testAuthority(p)
	p.Config.Autonomy.ObjectiveController = true

	workRaw, err := yaml.Marshal(w)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Load(workRaw); err != nil {
		t.Fatal(err)
	}
	q := QueueOrder{
		Schema:        queueSchema,
		ID:            w.ID,
		LogicalStage:  w.ID,
		Kind:          "source",
		WorkOrderYAML: string(workRaw),
	}
	queueRaw, err := json.Marshal(q)
	if err != nil {
		t.Fatal(err)
	}
	pending, err := p.queuePath("pending", w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = durableNew(pending, queueRaw); err != nil {
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
		QueueSHA:         digest(queueRaw),
		EvidenceComplete: true,
	}
	handoffDir := filepath.Join(p.Root, "evidence", "external-handoff", w.ID)
	if err = os.MkdirAll(handoffDir, 0700); err != nil {
		t.Fatal(err)
	}
	handoffPath := filepath.Join(handoffDir, "2.json")
	if err = writeJSON(handoffPath, h); err != nil {
		t.Fatal(err)
	}
	return p, w, handoffPath
}

func TestCodexQuotaRestoredRearmQueuesNormalLoop(t *testing.T) {
	p, w, handoff := prepareCodexQuotaRearmFixture(t)
	result, err := p.LocalControl(context.Background(), "quota-restored", w.ID)
	if err != nil {
		t.Fatal(err)
	}
	got := result.(map[string]any)
	if got["queue_state_after"] != "QUEUED" || got["work_order_state_after"] != "DRAFT" {
		t.Fatalf("unexpected result: %#v", got)
	}
	var qState, qReason, jState, jReason string
	var attempt int
	if err = p.Store.DB.QueryRow("SELECT state,reason FROM queue_items WHERE id=?", w.ID).Scan(&qState, &qReason); err != nil {
		t.Fatal(err)
	}
	if err = p.Store.DB.QueryRow("SELECT state,reason,attempt FROM work_orders WHERE id=?", w.ID).Scan(&jState, &jReason, &attempt); err != nil {
		t.Fatal(err)
	}
	if qState != "QUEUED" || jState != "DRAFT" || qReason != codexQuotaRestoredRearmReason || jReason != codexQuotaRestoredRearmReason || attempt != 2 {
		t.Fatalf("queue=%s/%s job=%s/%s attempt=%d", qState, qReason, jState, jReason, attempt)
	}
	if _, err = os.Stat(handoff); err != nil {
		t.Fatalf("held handoff was not preserved: %v", err)
	}
	events, err := p.Store.Events(0)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, e := range events {
		if e.WorkOrderID == w.ID && e.Attempt == 2 && e.Type == codexQuotaRestoredRearmReason {
			found = true
		}
	}
	if !found {
		t.Fatal("quota-restored audit event missing")
	}
}

func TestCodexQuotaRestoredRearmRefusesOwnedWorker(t *testing.T) {
	p, w, _ := prepareCodexQuotaRearmFixture(t)
	if _, err := p.Store.DB.Exec(
		"INSERT INTO worker_leases(work_order_id,attempt,owner,created) VALUES(?,?,?,?)",
		w.ID, 2, "fixture", now(),
	); err != nil {
		t.Fatal(err)
	}
	_, err := p.LocalControl(context.Background(), "quota-restored", w.ID)
	if err == nil || !strings.Contains(err.Error(), "REQUIRES_RELEASED_WORKER") {
		t.Fatalf("expected worker ownership refusal, got %v", err)
	}
	var qState string
	if err = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", w.ID).Scan(&qState); err != nil {
		t.Fatal(err)
	}
	if qState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		t.Fatalf("queue mutated on refusal: %s", qState)
	}
}

func TestCodexQuotaRestoredRearmRefusesChangedHandoff(t *testing.T) {
	p, w, handoff := prepareCodexQuotaRearmFixture(t)
	if err := os.WriteFile(handoff, []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
	_, err := p.LocalControl(context.Background(), "quota-restored", w.ID)
	if err == nil {
		t.Fatal("expected handoff verification refusal")
	}
	var qState string
	if e := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", w.ID).Scan(&qState); e != nil {
		t.Fatal(e)
	}
	if qState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		t.Fatalf("queue mutated on invalid handoff: %s", qState)
	}
}
