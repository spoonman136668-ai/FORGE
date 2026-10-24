package plane

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode/utf8"
)

const (
	externalRepairSchema            = "ckb-plane.external-orchestrator-repair.v1"
	externalHandoffWebUISchema      = "ckb-plane.webui-external-handoff.v1"
	externalRepairMaxOperations     = 32
	externalRepairMaxFileBytes      = 64 << 10
	externalRepairMaxAggregateBytes = 96 << 10
)

type ExternalOrchestratorEdit struct {
	Type                 string `json:"type"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256,omitempty"`
	Content              string `json:"content,omitempty"`
}

type ExternalOrchestratorRepairRequest struct {
	Schema        string                     `json:"schema"`
	RequestID     string                     `json:"request_id"`
	WorkOrderID   string                     `json:"work_order_id"`
	Attempt       int                        `json:"attempt"`
	HandoffSHA256 string                     `json:"handoff_sha256"`
	Operations    []ExternalOrchestratorEdit `json:"operations"`
}

func (r ExternalOrchestratorRepairRequest) validate() error {
	if r.Schema != externalRepairSchema || !bridgeSegment.MatchString(r.RequestID) || !safeID.MatchString(r.WorkOrderID) || r.Attempt < 1 {
		return errors.New("EXTERNAL_REPAIR_IDENTITY_INVALID")
	}
	if len(r.HandoffSHA256) != 64 || strings.Trim(r.HandoffSHA256, "0123456789abcdef") != "" {
		return errors.New("EXTERNAL_REPAIR_HANDOFF_HASH_INVALID")
	}
	if len(r.Operations) == 0 || len(r.Operations) > externalRepairMaxOperations {
		return errors.New("EXTERNAL_REPAIR_LIMIT")
	}
	return nil
}

type externalRepairPlan struct {
	op        ExternalOrchestratorEdit
	workspace string
	target    string
	existed   bool
	mode      os.FileMode
	before    []byte
	applied   bool
}

func validExternalSHA(v string) bool {
	return len(v) == 64 && strings.Trim(v, "0123456789abcdef") == ""
}

func planExternalOperations(workspace string, order WorkOrder, ops []ExternalOrchestratorEdit) ([]externalRepairPlan, error) {
	if workspace == "" || !filepath.IsAbs(workspace) || filepath.Clean(workspace) != workspace {
		return nil, errors.New("EXTERNAL_REPAIR_WORKSPACE_INVALID")
	}
	if len(ops) == 0 || len(ops) > externalRepairMaxOperations {
		return nil, errors.New("EXTERNAL_REPAIR_LIMIT")
	}
	if err := bridgeContained(workspace, workspace); err != nil {
		return nil, err
	}

	seen := map[string]bool{}
	aggregate := 0
	plans := make([]externalRepairPlan, 0, len(ops))
	for _, op := range ops {
		if !safePath(op.Path) || strings.ContainsAny(op.Path, "*?[]{}") || !order.Allows(op.Path) {
			return nil, fmt.Errorf("EXTERNAL_REPAIR_SCOPE_REFUSED: %s", op.Path)
		}
		key := strings.ToLower(filepath.ToSlash(op.Path))
		if seen[key] {
			return nil, fmt.Errorf("EXTERNAL_REPAIR_DUPLICATE_PATH: %s", op.Path)
		}
		seen[key] = true
		target := filepath.Join(workspace, filepath.FromSlash(op.Path))
		if err := bridgeContained(workspace, target); err != nil {
			return nil, err
		}
		plan := externalRepairPlan{op: op, workspace: workspace, target: target}
		info, err := os.Lstat(target)
		if err == nil {
			if !info.Mode().IsRegular() || info.Size() > 4<<20 {
				return nil, fmt.Errorf("EXTERNAL_REPAIR_TARGET_INVALID: %s", op.Path)
			}
			plan.existed = true
			plan.mode = info.Mode().Perm()
			plan.before, err = os.ReadFile(target)
			if err != nil {
				return nil, err
			}
		} else if !os.IsNotExist(err) {
			return nil, err
		}

		switch op.Type {
		case "write_text":
			if !utf8.ValidString(op.Content) || strings.HasPrefix(op.Content, "\ufeff") || strings.ContainsRune(op.Content, '\x00') || len([]byte(op.Content)) > externalRepairMaxFileBytes {
				return nil, fmt.Errorf("EXTERNAL_REPAIR_CONTENT_INVALID: %s", op.Path)
			}
			aggregate += len([]byte(op.Content))
			if plan.existed {
				if !validExternalSHA(op.ExpectedBeforeSHA256) || op.ExpectedBeforeSHA256 != digest(plan.before) {
					return nil, fmt.Errorf("EXTERNAL_REPAIR_PREIMAGE_MISMATCH: %s", op.Path)
				}
			} else if op.ExpectedBeforeSHA256 != "" {
				return nil, fmt.Errorf("EXTERNAL_REPAIR_PREIMAGE_MISMATCH: %s", op.Path)
			}
		case "replace_text":
			if !plan.existed || !validExternalSHA(op.ExpectedBeforeSHA256) || op.ExpectedBeforeSHA256 != digest(plan.before) {
				return nil, fmt.Errorf("EXTERNAL_REPAIR_PREIMAGE_MISMATCH: %s", op.Path)
			}
			if err := validateExternalReplaceText(plan.before, op); err != nil {
				return nil, fmt.Errorf("%w: %s", err, op.Path)
			}
			aggregate += len([]byte(op.Content))
		case "delete_file":
			if op.Content != "" || !plan.existed || !validExternalSHA(op.ExpectedBeforeSHA256) || op.ExpectedBeforeSHA256 != digest(plan.before) {
				return nil, fmt.Errorf("EXTERNAL_REPAIR_PREIMAGE_MISMATCH: %s", op.Path)
			}
		default:
			return nil, fmt.Errorf("EXTERNAL_REPAIR_OPERATION_UNSUPPORTED: %s", op.Type)
		}
		if aggregate > externalRepairMaxAggregateBytes {
			return nil, errors.New("EXTERNAL_REPAIR_LIMIT")
		}
		plans = append(plans, plan)
	}
	return plans, nil
}

func rollbackExternalOperations(plans []externalRepairPlan) error {
	var first error
	for i := len(plans) - 1; i >= 0; i-- {
		p := plans[i]
		if !p.applied {
			continue
		}
		if p.existed {
			if err := os.MkdirAll(filepath.Dir(p.target), 0700); err == nil {
				err = os.WriteFile(p.target, p.before, p.mode)
				if err != nil && first == nil {
					first = err
				}
			} else if first == nil {
				first = err
			}
		} else if err := os.Remove(p.target); err != nil && !os.IsNotExist(err) && first == nil {
			first = err
		}
	}
	return first
}

func applyExternalOperations(plans []externalRepairPlan) error {
	for i := range plans {
		p := &plans[i]
		if err := bridgeContained(p.workspace, p.target); err != nil {
			_ = rollbackExternalOperations(plans)
			return err
		}
		p.applied = true
		var err error
		switch p.op.Type {
		case "write_text":
			if err = os.MkdirAll(filepath.Dir(p.target), 0700); err == nil {
				mode := p.mode
				if !p.existed || mode == 0 {
					mode = 0600
				}
				err = os.WriteFile(p.target, []byte(p.op.Content), mode)
			}
		case "replace_text":
			err = applyExternalReplaceText(p.target, p.before, p.mode, p.op)
		case "delete_file":
			err = os.Remove(p.target)
		}
		if err != nil {
			_ = rollbackExternalOperations(plans)
			return err
		}
	}
	return nil
}

func (b *WebUIBridge) ensurePlaneOutbox() error {
	if b == nil || b.db == nil {
		return errors.New("BRIDGE_UNAVAILABLE")
	}
	_, err := b.db.Exec(`CREATE TABLE IF NOT EXISTS plane_outbox(path TEXT PRIMARY KEY, body BLOB NOT NULL, delivered INTEGER NOT NULL DEFAULT 0);`)
	return err
}

func (b *WebUIBridge) queueExternalHandoff(h ObjectiveHandoff) error {
	if err := b.ensurePlaneOutbox(); err != nil {
		return err
	}
	handoffRaw := []byte(jsonText(h))
	payload := map[string]any{
		"schema":           externalHandoffWebUISchema,
		"type":             "external-orchestrator-handoff",
		"handoff_sha256":   digest(handoffRaw),
		"allowed_action":   "external-repair",
		"acceptance_owner": "ckb-plane",
		"handoff":          h,
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	if len(raw) > bridgeMaxBytes {
		return errors.New("EXTERNAL_HANDOFF_TOO_LARGE")
	}
	name := "external-" + digest(raw)[:32]
	path := "outbox/" + name + ".json"
	var old []byte
	err = b.db.QueryRow("SELECT body FROM plane_outbox WHERE path=?", path).Scan(&old)
	if err == nil {
		if string(old) != string(raw) {
			return errors.New("EXTERNAL_HANDOFF_CONFLICT")
		}
		return nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return err
	}
	_, err = b.db.Exec("INSERT INTO plane_outbox(path,body,delivered) VALUES(?,?,0)", path, raw)
	return err
}

func (b *WebUIBridge) deliverPlaneOutbox(ctx context.Context) error {
	if err := b.ensurePlaneOutbox(); err != nil {
		return err
	}
	rows, err := b.db.QueryContext(ctx, "SELECT path,body FROM plane_outbox WHERE delivered=0 ORDER BY path LIMIT 20")
	if err != nil {
		return err
	}
	defer rows.Close()
	type item struct {
		path string
		raw  []byte
	}
	var items []item
	for rows.Next() {
		var i item
		if err = rows.Scan(&i.path, &i.raw); err != nil {
			return err
		}
		items = append(items, i)
	}
	if err = rows.Err(); err != nil {
		return err
	}
	for _, i := range items {
		if err = b.mailbox.Publish(ctx, i.path, i.raw, false); err != nil {
			return err
		}
		if _, err = b.db.ExecContext(ctx, "UPDATE plane_outbox SET delivered=1 WHERE path=?", i.path); err != nil {
			return err
		}
	}
	return nil
}

func readObjectiveHandoff(root string, j Job, expectedSHA string) (ObjectiveHandoff, []byte, error) {
	var h ObjectiveHandoff
	path := filepath.Join(root, "evidence", "external-handoff", j.ID, fmt.Sprintf("%d.json", j.Attempt))
	if err := bridgeContained(root, path); err != nil {
		return h, nil, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return h, nil, err
	}
	if digest(raw) != expectedSHA {
		return h, nil, errors.New("EXTERNAL_REPAIR_HANDOFF_CHANGED")
	}
	if err = json.Unmarshal(raw, &h); err != nil {
		return h, nil, err
	}
	if h.Schema != "ckb-plane.external-orchestrator-handoff.v1" || h.WorkOrderID != j.ID || h.Attempt != j.Attempt || h.Workspace != j.Workspace || h.Evidence != j.Evidence || !h.EvidenceComplete {
		return h, nil, errors.New("EXTERNAL_REPAIR_HANDOFF_IDENTITY_MISMATCH")
	}
	return h, raw, nil
}

func (p *Engine) ExternalOrchestratorRepair(ctx context.Context, r ExternalOrchestratorRepairRequest) (map[string]any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if !p.Config.Autonomy.ObjectiveController {
		return nil, errors.New("OBJECTIVE_CONTROLLER_DISABLED")
	}
	if err := r.validate(); err != nil {
		return nil, err
	}
	if err := p.sourceAuthority(ctx); err != nil {
		return nil, err
	}
	j, err := p.Store.Get(r.WorkOrderID)
	if err != nil {
		return nil, err
	}
	if j.Attempt != r.Attempt || j.Workspace == "" || j.Evidence == "" {
		return nil, errors.New("EXTERNAL_REPAIR_ATTEMPT_CHANGED")
	}
	var qState, qReason string
	if err = p.Store.DB.QueryRow("SELECT state,reason FROM queue_items WHERE id=?", j.ID).Scan(&qState, &qReason); err != nil {
		return nil, err
	}
	if qState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		return nil, errors.New("EXTERNAL_REPAIR_REQUIRES_WAITING_STATE")
	}
	if failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" && !strings.HasPrefix(qReason, "EXTERNAL_REPAIR_ACCEPTANCE_FAILED") {
		return nil, errors.New("EXTERNAL_REPAIR_REASON_INVALID")
	}
	var active int
	if err = p.Store.DB.QueryRow("SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)", j.ID, j.ID).Scan(&active); err != nil {
		return nil, err
	}
	p.mu.Lock()
	_, owned := p.cancels[j.ID]
	p.mu.Unlock()
	if active != 0 || owned {
		return nil, errors.New("EXTERNAL_REPAIR_WORKER_STILL_OWNED")
	}
	handoff, handoffRaw, err := readObjectiveHandoff(p.Root, j, r.HandoffSHA256)
	if err != nil {
		return nil, err
	}
	if handoff.BaselineSHA != j.Order.Baseline.SHA {
		return nil, errors.New("EXTERNAL_REPAIR_BASELINE_CHANGED")
	}

	plans, err := planExternalOperations(j.Workspace, j.Order, r.Operations)
	if err != nil {
		return nil, err
	}
	if err = applyExternalOperations(plans); err != nil {
		return nil, err
	}
	keepWorkspace := false
	defer func() {
		if !keepWorkspace {
			_ = rollbackExternalOperations(plans)
		}
	}()

	beforeRaw, err := os.ReadFile(filepath.Join(j.Evidence, "repo_state_before.json"))
	if err != nil {
		return nil, err
	}
	var before RepoState
	if err = json.Unmarshal(beforeRaw, &before); err != nil {
		return nil, err
	}
	paths, err := changed(p.Config.Tools.Git, j.Workspace, j.Order.Baseline.SHA)
	if err != nil {
		return nil, err
	}
	if len(paths) == 0 {
		return nil, errors.New("EXTERNAL_REPAIR_NO_DIFF_PRODUCED")
	}
	for _, path := range paths {
		if !j.Order.Allows(path) {
			return nil, fmt.Errorf("EXTERNAL_REPAIR_SCOPE_REFUSED: %s", path)
		}
	}
	if _, err = p.capture(j, before); err != nil {
		return nil, err
	}
	applied := make([]string, 0, len(plans))
	for _, plan := range plans {
		applied = append(applied, plan.op.Path)
	}
	sort.Strings(applied)
	repairEvidence := map[string]any{
		"schema":           externalRepairSchema,
		"request_id":       r.RequestID,
		"work_order_id":    j.ID,
		"attempt":          j.Attempt,
		"handoff_sha256":   digest(handoffRaw),
		"applied_paths":    applied,
		"acceptance_owner": "ckb-plane",
	}
	if err = writeJSON(filepath.Join(j.Evidence, "external_repair_"+r.RequestID+".json"), repairEvidence); err != nil {
		return nil, err
	}

	tx, err := p.Store.DB.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	if _, err = tx.Exec("UPDATE work_orders SET state='CANDIDATE',reason='External orchestrator candidate captured' WHERE id=? AND attempt=?", j.ID, j.Attempt); err != nil {
		return nil, err
	}
	if _, err = tx.Exec("UPDATE queue_items SET state='RUNNING',reason='EXTERNAL_ORCHESTRATOR_ACCEPTANCE',next_retry='',updated=? WHERE id=? AND state='WAITING_FOR_EXTERNAL_ORCHESTRATOR'", now(), j.ID); err != nil {
		return nil, err
	}
	if err = event(tx, j.ID, j.Attempt, "EXTERNAL_ORCHESTRATOR_CANDIDATE", "Bounded WebUI repair applied; deterministic acceptance begins"); err != nil {
		return nil, err
	}
	if err = tx.Commit(); err != nil {
		return nil, err
	}
	keepWorkspace = true

	if err = p.acceptContext(ctx, j.ID); err != nil {
		current, getErr := p.Store.Get(j.ID)
		if getErr == nil && current.State == "ACCEPTING" {
			_ = p.Store.Move(j.ID, "BLOCKED", "ACCEPTANCE_INTERNAL_ERROR")
		}
	}
	current, getErr := p.Store.Get(j.ID)
	if getErr != nil {
		return nil, getErr
	}
	if current.State == "ACCEPTED" {
		return map[string]any{
			"accepted":      true,
			"work_order_id": current.ID,
			"attempt":       current.Attempt,
			"state":         current.State,
			"reason":        current.Reason,
			"applied_paths": applied,
		}, nil
	}

	tx, err = p.Store.DB.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	reason := "EXTERNAL_REPAIR_ACCEPTANCE_FAILED: " + current.Reason
	if _, err = tx.Exec("UPDATE queue_items SET state='WAITING_FOR_EXTERNAL_ORCHESTRATOR',reason=?,next_retry='',updated=? WHERE id=?", reason, now(), j.ID); err != nil {
		return nil, err
	}
	if err = event(tx, j.ID, j.Attempt, "WAITING_FOR_EXTERNAL_ORCHESTRATOR", reason); err != nil {
		return nil, err
	}
	if err = tx.Commit(); err != nil {
		return nil, err
	}
	_ = p.Seal(current)
	return map[string]any{
		"accepted":      false,
		"work_order_id": current.ID,
		"attempt":       current.Attempt,
		"state":         current.State,
		"reason":        current.Reason,
		"applied_paths": applied,
		"next_action":   "External orchestrator may inspect current evidence and submit another bounded repair; Codex is not relaunched automatically.",
	}, nil
}
