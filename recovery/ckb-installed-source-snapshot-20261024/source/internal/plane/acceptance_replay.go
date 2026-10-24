package plane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const acceptanceReplayReason = "ACCEPTANCE_REPLAY_AFTER_BROWSER_HARNESS_REPAIR"

func acceptanceReplayReasonAllowed(reason string) bool {
	return reason == "BROWSER_CRITICAL_CONTROL" || reason == "PLAYWRIGHT_FAILED" || reason == "PLANE_AUTHORITY_LOST"
}

func transientAuthorityReplayEvidence(j Job) error {
	raw, err := os.ReadFile(filepath.Join(j.Evidence, "acceptance_checks.json"))
	if err != nil {
		return errors.New("ACCEPTANCE_REPLAY_AUTHORITY_EVIDENCE_MISSING")
	}
	var checks []Check
	if err = json.Unmarshal(raw, &checks); err != nil {
		return errors.New("ACCEPTANCE_REPLAY_AUTHORITY_EVIDENCE_INVALID")
	}
	authorityMatches := 0
	cancelMatches := 0
	otherFailures := 0
	authorityDetail := ""
	for _, check := range checks {
		if check.Pass {
			continue
		}
		switch check.Name {
		case "PLANE_AUTHORITY_LOST":
			authorityMatches++
			authorityDetail = strings.TrimSpace(check.Detail)
		case "ACCEPTANCE_CANCELLED":
			if strings.TrimSpace(check.Detail) == "context canceled" {
				cancelMatches++
			} else {
				otherFailures++
			}
		default:
			otherFailures++
		}
	}
	if authorityMatches != 1 {
		return errors.New("ACCEPTANCE_REPLAY_AUTHORITY_EVIDENCE_AMBIGUOUS")
	}
	if transientAuthorityTransportError(errors.New(authorityDetail)) {
		return nil
	}
	if authorityDetail == "context canceled" && cancelMatches == 1 && otherFailures == 0 {
		return nil
	}
	return errors.New("ACCEPTANCE_REPLAY_AUTHORITY_FAILURE_NOT_TRANSIENT")
}

func copyAcceptanceReplayEvidence(src, dst string) error {
	if err := os.MkdirAll(dst, 0700); err != nil {
		return err
	}
	return filepath.WalkDir(src, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		if rel == "." {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return errors.New("ACCEPTANCE_REPLAY_EVIDENCE_SYMLINK_REFUSED")
		}
		target := filepath.Join(dst, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0700)
		}
		if !info.Mode().IsRegular() {
			return errors.New("ACCEPTANCE_REPLAY_EVIDENCE_NONREGULAR_REFUSED")
		}
		if err = os.MkdirAll(filepath.Dir(target), 0700); err != nil {
			return err
		}
		in, err := os.Open(path)
		if err != nil {
			return err
		}
		defer in.Close()
		out, err := os.OpenFile(target, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			return err
		}
		_, copyErr := io.Copy(out, in)
		closeErr := out.Close()
		if copyErr != nil {
			return copyErr
		}
		return closeErr
	})
}

func (p *Engine) archiveAcceptanceReplay(j Job, queueReceipt string) (string, error) {
	root := filepath.Join(
		p.Root,
		"evidence",
		"maintenance",
		"acceptance-replay",
		j.ID,
		strconv.Itoa(j.Attempt),
		randomID(),
	)
	if err := bridgeContained(p.Root, root); err != nil {
		return "", err
	}
	if err := copyAcceptanceReplayEvidence(j.Evidence, filepath.Join(root, "attempt-evidence")); err != nil {
		return "", err
	}
	if queueReceipt != "" {
		if err := bridgeContained(p.Root, queueReceipt); err != nil {
			return "", err
		}
		if info, err := os.Lstat(queueReceipt); err == nil {
			if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
				return "", errors.New("ACCEPTANCE_REPLAY_QUEUE_RECEIPT_INVALID")
			}
			data, err := os.ReadFile(queueReceipt)
			if err != nil {
				return "", err
			}
			if err = os.WriteFile(filepath.Join(root, "prior-queue-result.json"), data, 0600); err != nil {
				return "", err
			}
		} else if !os.IsNotExist(err) {
			return "", err
		}
	}
	if err := writeJSON(filepath.Join(root, "archive.json"), map[string]any{
		"schema":        "ckb-plane.acceptance-replay-archive.v1",
		"work_order_id": j.ID,
		"attempt":       j.Attempt,
		"state":         j.State,
		"reason":        j.Reason,
		"evidence":      j.Evidence,
		"observed_at":   now(),
	}); err != nil {
		return "", err
	}
	return root, nil
}

func (p *Engine) AcceptanceReplay(ctx context.Context, id string) (map[string]any, error) {
	if !safeID.MatchString(id) {
		return nil, errors.New("WORK_ORDER_ID_INVALID")
	}
	if p.Config.Policy.AcceptedRefMutation {
		return nil, errors.New("ACCEPTED_REF_MUTATION_FORBIDDEN")
	}
	if err := p.sourceAuthority(ctx); err != nil {
		return nil, err
	}

	p.queueMu.Lock()

	var paused string
	if err := p.Store.DB.QueryRow("SELECT value FROM settings WHERE key='paused'").Scan(&paused); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	if paused != "true" {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_REQUIRES_PAUSED_CONTROLLER")
	}

	j, err := p.Store.Get(id)
	if err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	if j.Attempt < 1 || j.State != "BLOCKED" || !acceptanceReplayReasonAllowed(j.Reason) || j.Workspace == "" || j.Evidence == "" {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_STATE_INVALID")
	}

	if j.Reason == "PLANE_AUTHORITY_LOST" {
		if err = transientAuthorityReplayEvidence(j); err != nil {
			p.queueMu.Unlock()
			return nil, err
		}
	}

	var qState, qReason, qReceipt string
	if err = p.Store.DB.QueryRow("SELECT state,reason,receipt FROM queue_items WHERE id=?", id).Scan(&qState, &qReason, &qReceipt); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	if qState != "FAILED" || qReason != j.Reason {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_QUEUE_INVALID")
	}

	var active int
	if err = p.Store.DB.QueryRow(
		"SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)",
		id, id,
	).Scan(&active); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	p.mu.Lock()
	_, owned := p.cancels[id]
	p.mu.Unlock()
	if active != 0 || owned {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_WORKER_STILL_OWNED")
	}
	if err = p.VerifyEvidence(j); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}

	archive, err := p.archiveAcceptanceReplay(j, qReceipt)
	if err != nil {
		p.queueMu.Unlock()
		return nil, err
	}

	for _, scratch := range []string{
		filepath.Join(p.Root, "acceptance", j.ID, fmt.Sprint(j.Attempt)),
		filepath.Join(p.Root, "acceptance", j.ID, fmt.Sprintf("%d-baseline", j.Attempt)),
	} {
		if err = bridgeContained(p.Root, scratch); err != nil {
			p.queueMu.Unlock()
			return nil, err
		}
		if err = os.RemoveAll(scratch); err != nil {
			p.queueMu.Unlock()
			return nil, err
		}
	}

	tx, err := p.Store.DB.Begin()
	if err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	defer tx.Rollback()

	res, err := tx.Exec(
		"UPDATE work_orders SET state='CANDIDATE',reason=? WHERE id=? AND attempt=? AND state='BLOCKED' AND reason=?",
		acceptanceReplayReason, id, j.Attempt, j.Reason,
	)
	if err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	n, err := res.RowsAffected()
	if err != nil || n != 1 {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_STATE_CHANGED")
	}
	res, err = tx.Exec(
		"UPDATE queue_items SET state='RUNNING',reason=?,receipt='',next_retry='',updated=? WHERE id=? AND state='FAILED' AND reason=?",
		acceptanceReplayReason, now(), id, qReason,
	)
	if err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	n, err = res.RowsAffected()
	if err != nil || n != 1 {
		p.queueMu.Unlock()
		return nil, errors.New("ACCEPTANCE_REPLAY_QUEUE_CHANGED")
	}
	if err = event(tx, id, j.Attempt, "ACCEPTANCE_REPLAY", "Archived sealed failed acceptance and replaying deterministic gates without worker relaunch"); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	if err = tx.Commit(); err != nil {
		p.queueMu.Unlock()
		return nil, err
	}
	p.queueMu.Unlock()

	acceptErr := p.Accept(id)
	current, getErr := p.Store.Get(id)
	if getErr != nil {
		return nil, getErr
	}
	if acceptErr != nil && current.State == "ACCEPTING" {
		_ = p.Store.Move(id, "BLOCKED", "ACCEPTANCE_INTERNAL_ERROR")
		current, _ = p.Store.Get(id)
	}

	if current.Attempt != j.Attempt {
		return nil, errors.New("ACCEPTANCE_REPLAY_ATTEMPT_CHANGED")
	}
	queueAfter := "RUNNING"
	if current.State != "ACCEPTED" {
		if _, err := p.Store.DB.Exec(
			"UPDATE queue_items SET state='FAILED',reason=?,updated=? WHERE id=? AND state='RUNNING' AND reason=?",
			current.Reason, now(), id, acceptanceReplayReason,
		); err != nil {
			return nil, err
		}
		queueAfter = "FAILED"
	}
	result := map[string]any{
		"id":                       current.ID,
		"attempt":                  current.Attempt,
		"state":                    current.State,
		"reason":                   current.Reason,
		"worker_relaunched":        false,
		"attempt_incremented":      false,
		"accepted_ref_mutated":     false,
		"prior_evidence_archive":   archive,
		"queue_state_after_replay": queueAfter,
	}
	if acceptErr != nil {
		return result, acceptErr
	}
	return result, nil
}

func (p *Engine) AcceptanceReplayOffline(ctx context.Context, id string) (any, error) {
	f, err := p.controllerLock()
	if err != nil {
		return p.callLocalController(ctx, NativeRequest{Action: "acceptance-replay", ID: id})
	}
	defer f.Close()
	return p.AcceptanceReplay(ctx, id)
}
