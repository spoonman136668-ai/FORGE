package plane

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type ObjectiveHandoff struct {
	EvidenceComplete bool   `json:"evidence_complete"`
	InventorySHA     string `json:"workspace_inventory_sha256,omitempty"`
	Schema           string `json:"schema"`
	WorkOrderID      string `json:"work_order_id"`
	Attempt          int    `json:"attempt"`
	Workspace        string `json:"retained_workspace"`
	Evidence         string `json:"failure_evidence"`
	BaselineRef      string `json:"latest_accepted_ref"`
	BaselineSHA      string `json:"latest_accepted_sha"`
	QueueSHA         string `json:"work_order_sha256"`
	DeltaSHA         string `json:"workspace_delta_sha256"`
	ManifestSHA      string `json:"evidence_manifest_sha256"`
	RequiredAction   string `json:"required_action"`
}

// Only an unsuccessful Codex invocation is eligible. We read bounded native
// adapter error events, never infer quota from source files or planner prose.
// Unknown output remains WORKER_EXIT_NONZERO and the existing policy blocks it.
func codexFailure(evidence string) string {
	provider := ""
	for _, name := range []string{"worker_stdout.log", "worker_stderr.log"} {
		f, e := os.Open(filepath.Join(evidence, name))
		if e != nil {
			continue
		}
		s := bufio.NewScanner(io.LimitReader(f, 1<<20))
		s.Buffer(make([]byte, 4096), 64<<10)
		for s.Scan() {
			var v struct {
				Type    string `json:"type"`
				Code    string `json:"code"`
				Message string `json:"message"`
				Error   *struct {
					Code    string `json:"code"`
					Message string `json:"message"`
				} `json:"error"`
			}
			if json.Unmarshal(s.Bytes(), &v) != nil {
				continue
			}
			if v.Type != "error" && v.Type != "turn.failed" {
				continue
			}
			code, msg := v.Code, v.Message
			if v.Error != nil {
				code, msg = v.Error.Code, v.Error.Message
			}
			if code == "CODEX_QUOTA_EXHAUSTED" || code == "usage_limit_reached" || code == "insufficient_quota" || strings.HasPrefix(msg, "You've hit your usage limit.") || strings.HasPrefix(msg, "You have exceeded your current quota.") {
				f.Close()
				return "CODEX_QUOTA_EXHAUSTED"
			}
			if code == "service_unavailable" || code == "provider_unavailable" {
				provider = "CODEX_PROVIDER_UNAVAILABLE"
			}
		}
		f.Close()
	}
	return provider
}

func codexExhaustion(evidence string) bool { return codexFailure(evidence) == "CODEX_QUOTA_EXHAUSTED" }

func (p *Engine) objectiveHandoff(j Job) (ObjectiveHandoff, error) {
	h := ObjectiveHandoff{Schema: "ckb-plane.external-orchestrator-handoff.v1", WorkOrderID: j.ID, Attempt: j.Attempt, Workspace: j.Workspace, Evidence: j.Evidence, BaselineRef: j.Order.Baseline.Ref, BaselineSHA: j.Order.Baseline.SHA, RequiredAction: "External proposal required; retained workspace and failure evidence must be preserved. Continuation execution and acceptance remain plane-owned."}
	if j.Workspace == "" || j.Evidence == "" || failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" {
		return h, errors.New("EXHAUSTION_STATE_INVALID")
	}
	if e := bridgeContained(p.Root, j.Workspace); e != nil {
		return h, e
	}
	if e := bridgeContained(p.Root, j.Evidence); e != nil {
		return h, e
	}
	if e := p.VerifyEvidence(j); e != nil {
		return h, e
	}
	if e := p.Store.DB.QueryRow("SELECT hash FROM queue_items WHERE id=?", j.ID).Scan(&h.QueueSHA); e != nil {
		return h, e
	}
	if e := p.Store.DB.QueryRow("SELECT manifest_sha256 FROM evidence_seals WHERE work_order_id=? AND attempt=?", j.ID, j.Attempt).Scan(&h.ManifestSHA); e != nil {
		return h, e
	}
	if e := regularPath(j.Evidence, "candidate.diff"); e != nil {
		return h, e
	}
	delta, e := os.ReadFile(filepath.Join(j.Evidence, "candidate.diff"))
	if e != nil {
		return h, e
	}
	h.DeltaSHA = digest(delta)
	if e := regularPath(j.Evidence, "candidate_inventory.json"); e != nil {
		return h, e
	}
	inv, e := os.ReadFile(filepath.Join(j.Evidence, "candidate_inventory.json"))
	if e != nil {
		return h, e
	}
	h.InventorySHA = digest(inv)
	h.EvidenceComplete = true
	return h, nil
}

// Called under queueMu after the worker released ownership. The existing
// attempt retains its workspace and sealed evidence; nothing is cleaned or
// re-materialized. No recovery decision/attempt budget is consumed.
func (p *Engine) holdCodexExhaustion(j Job) error {
	if !p.Config.Autonomy.ObjectiveController {
		return nil
	}
	var n int
	if e := p.Store.DB.QueryRow("SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)", j.ID, j.ID).Scan(&n); e != nil {
		return e
	}
	p.mu.Lock()
	_, owned := p.cancels[j.ID]
	p.mu.Unlock()
	if n != 0 || owned {
		return errors.New("EXHAUSTION_WAITING_FOR_WORKER_RELEASE")
	}
	h, e := p.objectiveHandoff(j)
	if e != nil {
		return e
	}
	path := filepath.Join(p.Root, "evidence", "external-handoff", j.ID, strconv.Itoa(j.Attempt)+".json")
	if e = bridgeContained(p.Root, path); e != nil {
		return e
	}
	raw := []byte(jsonText(h))
	if old, er := os.ReadFile(path); er == nil {
		if regularPath(filepath.Dir(path), filepath.Base(path)) != nil || string(old) != string(raw) {
			return errors.New("EXHAUSTION_HANDOFF_CHANGED")
		}
	} else if os.IsNotExist(er) {
		if e = durableNew(path, raw); e != nil {
			return e
		}
	} else {
		return er
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	var state string
	if e = tx.QueryRow("SELECT state FROM queue_items WHERE id=?", j.ID).Scan(&state); e != nil {
		return e
	}
	if state == "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		return nil
	}
	if state != "RUNNING" && state != "RETRY_WAIT" && state != "BLOCKED" {
		return errors.New("EXHAUSTION_QUEUE_STATE_INVALID")
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='WAITING_FOR_EXTERNAL_ORCHESTRATOR',reason='CODEX_QUOTA_EXHAUSTED',next_retry='',updated=? WHERE id=?", now(), j.ID); e != nil {
		return e
	}
	if e = event(tx, j.ID, j.Attempt, "WAITING_FOR_EXTERNAL_ORCHESTRATOR", "CODEX_QUOTA_EXHAUSTED; handoff="+path); e != nil {
		return e
	}
	if e = tx.Commit(); e != nil {
		return e
	}
	if p.bridge != nil {
		if e = p.bridge.queueExternalHandoff(h); e != nil {
			_ = p.setSetting("bridge_status", "EXTERNAL_HANDOFF_QUEUE_FAILED: "+e.Error())
		}
	}
	return nil
}

func (p *Engine) objectiveRetryGuard(id string) error {
	if !p.Config.Autonomy.ObjectiveController {
		return nil
	}
	var reason string
	e := p.Store.DB.QueryRow("SELECT reason FROM work_orders WHERE id=?", id).Scan(&reason)
	if errors.Is(e, sql.ErrNoRows) {
		return nil
	}
	if e != nil {
		return e
	}
	if failureClass(reason) == "CODEX_QUOTA_EXHAUSTED" {
		return errors.New("WAITING_FOR_EXTERNAL_ORCHESTRATOR: quota exhaustion cannot use generic retry")
	}
	return nil
}
