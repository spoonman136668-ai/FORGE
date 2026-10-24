package plane

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
)

func (p *Engine) QualifyAutonomy(ctx context.Context) (map[string]any, error) {
	lock, e := p.controllerLock()
	if e != nil {
		return nil, e
	}
	defer lock.Close()
	if p.Config.Execution.SandboxSyntax != "native" && p.Config.Execution.SandboxSyntax != "windows-subcommand" {
		return nil, errors.New("CONFIGURE_SANDBOX_SYNTAX_FIRST")
	}
	if runtime.GOOS != "windows" || runtime.GOARCH != "amd64" {
		return nil, errors.New("NATIVE_WINDOWS_QUALIFICATION_REQUIRED")
	}
	root := filepath.Join(p.Root, "artifacts", "autonomy-qualification", randomID())
	source := filepath.Join(root, "source")
	if e = bridgeContained(p.Root, source); e != nil {
		return nil, e
	}
	if e = durableNew(filepath.Join(source, "go.mod"), []byte("module plane-qualification\n\ngo 1.25.5\n")); e != nil {
		return nil, e
	}
	if e = durableNew(filepath.Join(source, "qualification_test.go"), []byte("package qualification\nimport \"testing\"\nfunc TestPlaneQualification(t *testing.T) {}\n")); e != nil {
		return nil, e
	}
	j := Job{ID: "PLANE_QUALIFICATION", Workspace: source, Evidence: root}
	j.Order.Repo = "ckb"
	j.Order.RequiredTests.Packages = []string{"./..."}
	if e = p.realEnvironmentPreflight(j.Order); e != nil {
		return nil, e
	}
	pass, detail := p.goTest(ctx, j, "^TestPlaneQualification$", false, 0)
	result := map[string]any{"schema": "ckb-plane.windows-qualification.v1", "version": AutonomyVersion, "passed": pass, "detail": detail, "config_and_tool_digest": p.contract(WorkOrder{}), "observed_at": now(), "model_worker_launched": false, "ckb_source_mutated": false, "evidence": root}
	b, _ := json.MarshalIndent(result, "", "  ")
	if e = durableNew(filepath.Join(root, "qualification.json"), b); e != nil {
		return result, e
	}
	if !pass {
		return result, errors.New("WINDOWS_SANDBOX_QUALIFICATION_FAILED: " + detail)
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return result, e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("INSERT OR REPLACE INTO settings VALUES('qualification_digest',?)", p.contract(WorkOrder{})); e != nil {
		return result, e
	}
	if _, e = tx.Exec("INSERT OR REPLACE INTO settings VALUES('qualification_receipt',?)", filepath.Join(root, "qualification.json")); e != nil {
		return result, e
	}
	if e = event(tx, "", 0, "WINDOWS_QUALIFIED", root); e != nil {
		return result, e
	}
	return result, tx.Commit()
}

func (p *Engine) verifyQualification() error {
	if p.setting("qualification_digest") != p.contract(WorkOrder{}) {
		return errors.New("WINDOWS_QUALIFICATION_REQUIRED_OR_CONFIGURATION_CHANGED")
	}
	path := p.setting("qualification_receipt")
	if e := bridgeContained(p.Root, path); e != nil {
		return e
	}
	b, e := os.ReadFile(path)
	if e != nil {
		return errors.New("QUALIFICATION_RECEIPT_MISSING")
	}
	var receipt struct {
		Passed bool   `json:"passed"`
		Digest string `json:"config_and_tool_digest"`
	}
	if e = json.Unmarshal(b, &receipt); e != nil || !receipt.Passed || receipt.Digest != p.contract(WorkOrder{}) {
		return errors.New("QUALIFICATION_RECEIPT_INVALID")
	}
	return nil
}

func (p *Engine) CheckAutonomyHandoff(ctx context.Context) error {
	if e := p.verifyQualification(); e != nil {
		return e
	}
	if e := p.CheckR4c1Proof(); e != nil {
		return e
	}
	return p.verifyOriginalInactive(ctx)
}

func (p *Engine) CheckR4c1Proof() error {
	const id = "V11110_STAGE_CT_POST_ACCEPTANCE_QUEUE_CONSUMPTION_R1"
	var state, kind, hash string
	if e := p.Store.DB.QueryRow("SELECT state,kind,hash FROM queue_items WHERE id=?", id).Scan(&state, &kind, &hash); e != nil || state != "COMPLETED" || kind != "proof" {
		return errors.New("R4C1_NATIVE_PROOF_REQUIRED_BEFORE_CUTOVER")
	}
	var raw []byte
	var receiptHash string
	if e := p.Store.DB.QueryRow("SELECT hash,raw FROM queue_receipts WHERE work_order_id=?", id).Scan(&receiptHash, &raw); e != nil || digest(raw) != receiptHash {
		return errors.New("R4C1_RECEIPT_REQUIRED")
	}
	var receipt QueueResult
	if e := json.Unmarshal(raw, &receipt); e != nil || receipt.InputSHA256 != hash || receipt.Mode != "controlled-proof" || receipt.Authorization != "test" || receipt.Disposition != "completed" || receipt.ProductionAccepted || receipt.WorkOrderID != id || receipt.BaselineRef != "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1" || !shaRE.MatchString(receipt.BaselineSHA) {
		return errors.New("R4C1_CONTROLLED_PROOF_REQUIRED")
	}
	if e := bridgeContained(p.Root, receipt.Evidence); e != nil {
		return e
	}
	disk, e := os.ReadFile(filepath.Join(receipt.Evidence, "queue-result.json"))
	if e != nil || digest(disk) != receiptHash {
		return errors.New("R4C1_RECEIPT_FILE_CHANGED_OR_MISSING")
	}
	return nil
}
