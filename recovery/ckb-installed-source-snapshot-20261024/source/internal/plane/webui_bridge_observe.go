package plane

import (
	"context"
	"database/sql"
	"errors"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

type bridgeJob struct {
	ID          string `json:"id"`
	State       string `json:"state"`
	Attempt     int    `json:"attempt"`
	HasEvidence bool   `json:"has_evidence"`
}

// Read only a curated projection. No prompts, credentials, source, logs, repo URLs,
// arbitrary files or raw event messages leave the machine through this release.
func (b *WebUIBridge) observe(ctx context.Context, cmd BridgeCommand) (any, error) {
	if cmd.Action == "ping" {
		return map[string]any{"connected": true, "capabilities": []string{"ping", "status", "workorder", "events", "evidence"}, "worker_launch_allowed": false, "queue_consumption_allowed": false}, nil
	}
	if e := bridgeContained(b.Root, b.PlaneState); e != nil {
		return nil, e
	}
	info, e := os.Stat(b.PlaneState)
	if e != nil || !info.Mode().IsRegular() {
		return nil, errors.New("PLANE_STATE_UNAVAILABLE")
	}
	p := filepath.ToSlash(b.PlaneState)
	if !strings.HasPrefix(p, "/") {
		p = "/" + p
	}
	u := url.URL{Scheme: "file", Path: p}
	q := url.Values{"mode": {"ro"}, "_pragma": {"query_only(1)", "busy_timeout(3000)"}}
	u.RawQuery = q.Encode()
	db, e := sql.Open("sqlite", u.String())
	if e != nil {
		return nil, e
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	// Every result observes one database snapshot. Never migrate the plane store.
	tx, e := db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	switch cmd.Action {
	case "status":
		var paused string
		if e = tx.QueryRowContext(ctx, "SELECT value FROM settings WHERE key='paused'").Scan(&paused); e != nil {
			return nil, e
		}
		rows, e := tx.QueryContext(ctx, "SELECT id,state,attempt,evidence<>'' FROM work_orders ORDER BY rowid DESC LIMIT 101")
		if e != nil {
			return nil, e
		}
		defer rows.Close()
		jobs := []bridgeJob{}
		for rows.Next() {
			var j bridgeJob
			if e = rows.Scan(&j.ID, &j.State, &j.Attempt, &j.HasEvidence); e != nil {
				return nil, e
			}
			jobs = append(jobs, j)
		}
		if e = rows.Err(); e != nil {
			return nil, e
		}
		truncated := len(jobs) > 100
		if truncated {
			jobs = jobs[:100]
		}
		return map[string]any{"plane_dispatch_paused": paused == "true", "jobs": jobs, "jobs_truncated": truncated, "bridge_read_only": true, "authority_changed": false, "note": "Plane SQLite state only; this does not report the original GitHub orchestration loop or R4c1 filesystem queue."}, nil
	case "workorder":
		var j bridgeJob
		if e = tx.QueryRowContext(ctx, "SELECT id,state,attempt,evidence<>'' FROM work_orders WHERE id=?", cmd.WorkOrderID).Scan(&j.ID, &j.State, &j.Attempt, &j.HasEvidence); e != nil {
			return nil, e
		}
		return j, nil
	case "events":
		rows, e := tx.QueryContext(ctx, "SELECT id,timestamp,work_order_id,attempt_id,type,severity FROM events WHERE id>? ORDER BY id LIMIT 51", cmd.AfterEvent)
		if e != nil {
			return nil, e
		}
		defer rows.Close()
		type eventView struct {
			ID          int64  `json:"id"`
			Timestamp   string `json:"timestamp"`
			WorkOrderID string `json:"work_order_id"`
			Attempt     int    `json:"attempt"`
			Type        string `json:"type"`
			Severity    string `json:"severity"`
		}
		out := []eventView{}
		for rows.Next() {
			var ev eventView
			if e = rows.Scan(&ev.ID, &ev.Timestamp, &ev.WorkOrderID, &ev.Attempt, &ev.Type, &ev.Severity); e != nil {
				return nil, e
			}
			out = append(out, ev)
		}
		if e = rows.Err(); e != nil {
			return nil, e
		}
		more := len(out) > 50
		if more {
			out = out[:50]
		}
		next := cmd.AfterEvent
		if len(out) > 0 {
			next = out[len(out)-1].ID
		}
		return map[string]any{"events": out, "next_after_event": next, "has_more": more}, nil
	case "evidence":
		var state, hash string
		var attempt int
		if e = tx.QueryRowContext(ctx, "SELECT state,attempt FROM work_orders WHERE id=?", cmd.WorkOrderID).Scan(&state, &attempt); e != nil {
			return nil, e
		}
		e = tx.QueryRowContext(ctx, "SELECT manifest_sha256 FROM evidence_seals WHERE work_order_id=? AND attempt=?", cmd.WorkOrderID, attempt).Scan(&hash)
		if e != nil && !errors.Is(e, sql.ErrNoRows) {
			return nil, e
		}
		if hash != "" && (len(hash) != 64 || strings.Trim(hash, "0123456789abcdef") != "") {
			return nil, errors.New("EVIDENCE_HASH_INVALID")
		}
		rows, e := tx.QueryContext(ctx, "SELECT name,pass,detail FROM acceptance_checks WHERE run_id=(SELECT MAX(id) FROM acceptance_runs WHERE work_order_id=? AND attempt=?) ORDER BY id LIMIT 101", cmd.WorkOrderID, attempt)
		if e != nil {
			return nil, e
		}
		defer rows.Close()
		type checkView struct {
			Name   string `json:"name"`
			Pass   bool   `json:"pass"`
			Detail string `json:"detail,omitempty"`
		}
		checks := []checkView{}
		for rows.Next() {
			var c checkView
			var detail string
			if e = rows.Scan(&c.Name, &c.Pass, &detail); e != nil {
				return nil, e
			}
			c.Detail = bridgeFailureDetail(c.Pass, detail)
			checks = append(checks, c)
		}
		if e = rows.Err(); e != nil {
			return nil, e
		}
		truncated := len(checks) > 100
		if truncated {
			checks = checks[:100]
		}
		return map[string]any{"work_order_id": cmd.WorkOrderID, "state": state, "attempt": attempt, "recorded_manifest_sha256": hash, "checks": checks, "checks_truncated": truncated, "verification": "recorded_metadata_only_not_a_fresh_file_integrity_audit"}, nil
	}
	return nil, errors.New("ACTION_NOT_ALLOWED_READ_ONLY_BRIDGE")
}
