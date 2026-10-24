package plane

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func recoverySnapshotEngineFixture(t *testing.T, blocker string) (*Engine, WorkOrder, string, string) {
	t.Helper()
	return recoverySnapshotEngineFixtureAttempt(t, blocker, 1)
}

func recoverySnapshotEngineFixtureAttempt(t *testing.T, blocker string, attempt int) (*Engine, WorkOrder, string, string) {
	t.Helper()
	if attempt < 1 {
		t.Fatal("recovery fixture attempt must be positive")
	}
	p, w := setup(t)
	testAuthority(p)

	native, err := yaml.Marshal(w)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Load(native); err != nil {
		t.Fatal(err)
	}
	if err = p.Authorize(w.ID); err != nil {
		t.Fatal(err)
	}

	q := QueueOrder{
		Schema:        queueSchema,
		ID:            w.ID,
		LogicalStage:  w.ID,
		Kind:          "source",
		WorkOrderYAML: string(native),
	}
	queueRaw := []byte(jsonText(q))
	queueHash := digest(queueRaw)
	if _, err = p.Store.DB.Exec(
		"INSERT INTO queue_items(id,hash,raw,kind,state,mode,authorization,reason,updated) VALUES(?,?,?,'source','FAILED','source','operator',?,?)",
		w.ID, queueHash, queueRaw, blocker, now(),
	); err != nil {
		t.Fatal(err)
	}

	evidence := filepath.Join(p.Root, "evidence", w.ID, fmt.Sprint(attempt))
	if err = os.MkdirAll(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte("pkg/web/app.js\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "acceptance_checks.json"), []Check{
		{Name: "GO_TEST_FAILED", Pass: false, Detail: "fixture failure"},
	}); err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "worker_exit.json"), map[string]any{
		"exit_code": 1,
		"failure_class": "WORKER_EXIT_NONZERO",
	}); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(evidence, "worker_stderr.log"), []byte("bounded fixture stderr\n"), 0600); err != nil {
		t.Fatal(err)
	}
	goDiagnostic := strings.Repeat("x", recoverySnapshotValidationDiagnosticLimit+1024) + "\n{\"Action\":\"fail\",\"Test\":\"TestRecoveryRegression\",\"Output\":\"fixture regression failure\"}\n"
	if err = os.WriteFile(filepath.Join(evidence, "go-all.jsonl"), []byte(goDiagnostic), 0600); err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "attempt_result.json"), map[string]any{
		"state": "BLOCKED",
		"reason": blocker,
		"attempt": attempt,
	}); err != nil {
		t.Fatal(err)
	}
	manifest, err := Manifest(evidence)
	if err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "evidence_manifest.json"), manifest); err != nil {
		t.Fatal(err)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(evidence, "evidence_manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"INSERT INTO evidence_seals(work_order_id,attempt,manifest_sha256) VALUES(?,?,?)",
		w.ID, attempt, digest(manifestRaw),
	); err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"UPDATE work_orders SET state='BLOCKED',attempt=?,reason=?,evidence=? WHERE id=?",
		attempt, blocker, evidence, w.ID,
	); err != nil {
		t.Fatal(err)
	}
	return p, w, queueHash, evidence
}

func TestRecoverySnapshotBindsBlockedAttemptIdentity(t *testing.T) {
	p, w, queueHash, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	out, err := p.BuildRecoveryEvidenceSnapshot(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if out.WorkOrderID != w.ID || out.BlockedAttempt != 1 || out.QueueInputSHA256 != queueHash {
		t.Fatal(out)
	}
	if out.BaselineRef != w.Baseline.Ref || out.BaselineSHA != w.Baseline.SHA || out.AuthorityGeneration != 1 {
		t.Fatal(out)
	}
	if out.OriginalBlocker != "GO_TEST_FAILED" || len(out.ChangedFiles) != 1 || out.ChangedFiles[0] != "pkg/web/app.js" {
		t.Fatal(out)
	}
	if len(out.FailedChecks) != 1 || out.FailedChecks[0] != "GO_TEST_FAILED" || out.WorkerFailureClass != "WORKER_EXIT_NONZERO" {
		t.Fatal(out)
	}
	if !strings.Contains(out.ControllerDiagnostic, "bounded tail") ||
		!strings.Contains(out.ControllerDiagnostic, "TestRecoveryRegression") ||
		len(out.ControllerDiagnostic) > recoverySnapshotValidationDiagnosticLimit+128 {
		t.Fatal(out.ControllerDiagnostic)
	}
}

func TestRecoverySnapshotRejectsEvidenceTamper(t *testing.T) {
	p, w, _, evidence := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	if err := os.WriteFile(filepath.Join(evidence, "worker_stderr.log"), []byte("tampered\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_EVIDENCE_INVALID" {
		t.Fatal(err)
	}
}

func TestRecoverySnapshotRejectsQueueByteDrift(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	if _, err := p.Store.DB.Exec("UPDATE queue_items SET raw=? WHERE id=?", []byte("{}"), w.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_QUEUE_HASH_MISMATCH" {
		t.Fatal(err)
	}
}

func TestRecoverySnapshotRejectsAuthorizationContractDrift(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	p.Config.Policy.MaxAttempts++
	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_AUTHORIZATION_CONTRACT_CHANGED" {
		t.Fatal(err)
	}
}

func TestRecoverySnapshotRejectsChangedEvidencePath(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	other := filepath.Join(p.Root, "evidence", w.ID, "other")
	if _, err := p.Store.DB.Exec("UPDATE work_orders SET evidence=? WHERE id=?", other, w.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_EVIDENCE_PATH_CHANGED" {
		t.Fatal(err)
	}
}

func TestRecoverySnapshotRequiresTerminalBlockedAttempt(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	if _, err := p.Store.DB.Exec("UPDATE work_orders SET state='REJECTED_RETRYABLE' WHERE id=?", w.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_REQUIRES_BLOCKED_ATTEMPT" {
		t.Fatal(err)
	}
}

func TestRecoverySnapshotRejectsAttemptResultMismatch(t *testing.T) {
	p, w, _, evidence := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	if err := writeJSON(filepath.Join(evidence, "attempt_result.json"), map[string]any{
		"state": "BLOCKED",
		"reason": "SOMETHING_ELSE",
		"attempt": 1,
	}); err != nil {
		t.Fatal(err)
	}
	manifest, err := Manifest(evidence)
	if err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "evidence_manifest.json"), manifest); err != nil {
		t.Fatal(err)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(evidence, "evidence_manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"UPDATE evidence_seals SET manifest_sha256=? WHERE work_order_id=? AND attempt=1",
		digest(manifestRaw), w.ID,
	); err != nil {
		t.Fatal(err)
	}
	if _, err = p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || !strings.Contains(err.Error(), "RECOVERY_ATTEMPT_RESULT_MISMATCH") {
		t.Fatal(err)
	}
}


func TestRecoverySnapshotBindsObjectiveIdentityWithoutObjectiveControllerOverlay(t *testing.T) {
	p, w, queueHash, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")

	var contract string
	if err := p.Store.DB.QueryRow(
		"SELECT digest FROM authorization_contracts WHERE work_order_id=?",
		w.ID,
	).Scan(&contract); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec(`
CREATE TABLE objectives(id TEXT PRIMARY KEY,raw BLOB NOT NULL,priority INTEGER NOT NULL,revision INTEGER NOT NULL);
CREATE TABLE objective_stages(objective_id TEXT NOT NULL,stage INTEGER NOT NULL,work_id TEXT NOT NULL UNIQUE,hash TEXT NOT NULL,contract TEXT NOT NULL);
`); err != nil {
		t.Fatal(err)
	}

	objectiveID := "RECOVERY_OBJECTIVE_FIXTURE"
	objectiveRaw := jsonText(map[string]any{
		"schema":                "ckb-plane.objective.v1",
		"objective_id":          objectiveID,
		"authority_generation":  int64(1),
		"status":                "BLOCKED",
		"priority":              7,
		"revision":              int64(4),
		"next_stage":            0,
		"stage_count":           1,
		"current_work_order_id": w.ID,
	})
	if _, err := p.Store.DB.Exec(
		"INSERT INTO objectives(id,raw,priority,revision) VALUES(?,?,?,?)",
		objectiveID, objectiveRaw, 7, 4,
	); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec(
		"INSERT INTO objective_stages(objective_id,stage,work_id,hash,contract) VALUES(?,?,?,?,?)",
		objectiveID, 0, w.ID, queueHash, contract,
	); err != nil {
		t.Fatal(err)
	}

	out, err := p.BuildRecoveryEvidenceSnapshot(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if out.ObjectiveID != objectiveID || out.ObjectiveStage != 0 || out.ObjectiveRevision != 4 {
		t.Fatalf("objective identity not bound: %+v", out)
	}
}

func TestRecoverySnapshotRejectsCorruptObjectiveIdentityWithoutObjectiveControllerOverlay(t *testing.T) {
	p, w, queueHash, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")

	var contract string
	if err := p.Store.DB.QueryRow(
		"SELECT digest FROM authorization_contracts WHERE work_order_id=?",
		w.ID,
	).Scan(&contract); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec(`
CREATE TABLE objectives(id TEXT PRIMARY KEY,raw BLOB NOT NULL,priority INTEGER NOT NULL,revision INTEGER NOT NULL);
CREATE TABLE objective_stages(objective_id TEXT NOT NULL,stage INTEGER NOT NULL,work_id TEXT NOT NULL UNIQUE,hash TEXT NOT NULL,contract TEXT NOT NULL);
`); err != nil {
		t.Fatal(err)
	}

	objectiveID := "RECOVERY_OBJECTIVE_CORRUPT"
	objectiveRaw := jsonText(map[string]any{
		"schema":                "ckb-plane.objective.v1",
		"objective_id":          objectiveID,
		"authority_generation":  int64(1),
		"status":                "BLOCKED",
		"priority":              7,
		"revision":              int64(3),
		"next_stage":            0,
		"stage_count":           1,
		"current_work_order_id": w.ID,
	})
	if _, err := p.Store.DB.Exec(
		"INSERT INTO objectives(id,raw,priority,revision) VALUES(?,?,?,?)",
		objectiveID, objectiveRaw, 7, 4,
	); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec(
		"INSERT INTO objective_stages(objective_id,stage,work_id,hash,contract) VALUES(?,?,?,?,?)",
		objectiveID, 0, w.ID, queueHash, contract,
	); err != nil {
		t.Fatal(err)
	}

	if _, err := p.BuildRecoveryEvidenceSnapshot(w.ID); err == nil || err.Error() != "RECOVERY_OBJECTIVE_STATE_CORRUPT" {
		t.Fatal(err)
	}
}
