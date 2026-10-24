package plane

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
)

// Explicit operator continuation authorizes one more attempt of the same
// immutable order, in the same retained workspace, within its original budget.
// It does not authorize a new scope, worker backend, shell, baseline, or ref.
func (p *Engine) objectiveContinueLocked(ctx context.Context, o *Objective, hash string) (Objective, error) {
	if e := p.objectiveAuthority(ctx, o.Generation); e != nil {
		return *o, e
	}
	j, e := p.Store.Get(o.Current)
	if e != nil {
		return *o, e
	}
	if j.State != "BLOCKED" || failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" {
		return *o, errors.New("CONTINUATION_REQUIRES_QUOTA_BLOCKED_ATTEMPT")
	}
	continuationDecision := p.retryDecisionNow(j.ID, j.Attempt, codexQuotaRestoredRearmReason)
	if continuationDecision.HardStop {
		return *o, errors.New("CONTINUATION_ATTEMPT_BUDGET_EXHAUSTED")
	}
	if e = p.noLiveSupervisors(); e != nil {
		return *o, e
	}
	var leases int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases").Scan(&leases); e != nil {
		return *o, e
	}
	if leases != 0 {
		return *o, errors.New("ATTEMPT_STILL_OWNED")
	}
	p.mu.Lock()
	owned := len(p.cancels) > 0
	p.mu.Unlock()
	if owned {
		return *o, errors.New("ATTEMPT_STILL_OWNED")
	}
	h, e := p.objectiveHandoff(j)
	if e != nil {
		return *o, e
	}
	if digest([]byte(jsonText(h))) != hash {
		return *o, errors.New("OBJECTIVE_HANDOFF_CHANGED")
	}
	if _, e = p.verifyRetainedObjectiveWorkspace(j, h); e != nil {
		return *o, e
	}
	// Preserve the existing authorization contract and its exact source scope.
	if e = p.verifyContract(j.Order); e != nil {
		return *o, e
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return *o, e
	}
	defer tx.Rollback()
	var queueState string
	if e = tx.QueryRow("SELECT state FROM queue_items WHERE id=?", j.ID).Scan(&queueState); e != nil {
		return *o, e
	}
	if queueState != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		return *o, errors.New("CONTINUATION_QUEUE_STATE_INVALID")
	}
	if _, e = tx.Exec("INSERT INTO objective_continuations VALUES(?,?,?)", j.ID, j.Attempt+1, jsonText(h)); e != nil {
		return *o, e
	}
	if _, e = tx.Exec("UPDATE work_orders SET state='AUTHORIZED',reason='OPERATOR_QUOTA_CONTINUATION_AUTHORIZED' WHERE id=?", j.ID); e != nil {
		return *o, e
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='QUEUED',reason='OPERATOR_QUOTA_CONTINUATION_AUTHORIZED',next_retry='',updated=? WHERE id=?", now(), j.ID); e != nil {
		return *o, e
	}
	o.Status = "RUNNING"
	o.Paused = false
	o.StopAfterCurrent = false
	o.Blocker = ""
	if e = saveObjective(tx, o, "OPERATOR_continue", false); e != nil {
		return *o, e
	}
	if e = event(tx, j.ID, j.Attempt, "QUOTA_CONTINUATION_AUTHORIZED", "Same work order and retained workspace; next attempt consumes existing budget"); e != nil {
		return *o, e
	}
	return *o, tx.Commit()
}

func (p *Engine) verifyRetainedObjectiveWorkspace(j Job, h ObjectiveHandoff) (RepoState, error) {
	var before, after RepoState
	if h.WorkOrderID != j.ID || h.Attempt < 1 || h.BaselineRef != j.Order.Baseline.Ref || h.BaselineSHA != j.Order.Baseline.SHA {
		return before, errors.New("CONTINUATION_IDENTITY_CHANGED")
	}
	if e := bridgeContained(p.Root, h.Workspace); e != nil {
		return before, e
	}
	if e := bridgeContained(p.Root, h.Evidence); e != nil {
		return before, e
	}
	old := j
	old.Attempt = h.Attempt
	old.Evidence = h.Evidence
	if e := p.VerifyEvidence(old); e != nil {
		return before, e
	}
	manifest, e := os.ReadFile(filepath.Join(h.Evidence, "evidence_manifest.json"))
	if e != nil || digest(manifest) != h.ManifestSHA {
		return before, errors.New("CONTINUATION_EVIDENCE_CHANGED")
	}
	for name, dst := range map[string]*RepoState{"repo_state_before.json": &before, "repo_state_after.json": &after} {
		b, e := os.ReadFile(filepath.Join(h.Evidence, name))
		if e != nil {
			return before, e
		}
		if e = json.Unmarshal(b, dst); e != nil {
			return before, e
		}
	}
	head, e := git(p.Config.Tools.Git, h.Workspace, "rev-parse", "HEAD")
	if e != nil || head != after.Head {
		return before, errors.New("CONTINUATION_HEAD_CHANGED")
	}
	branch, e := git(p.Config.Tools.Git, h.Workspace, "symbolic-ref", "--short", "HEAD")
	if e != nil || branch != j.Order.Worker.Branch {
		return before, errors.New("CONTINUATION_BRANCH_CHANGED")
	}
	sourceRefs, e := refs(p.Config.Tools.Git, p.Config.Repos[j.Order.Repo].LocalPath)
	if e != nil || sourceRefs != before.SourceRefs {
		return before, errors.New("CONTINUATION_SOURCE_REFS_CHANGED")
	}
	attemptRefs, e := refs(p.Config.Tools.Git, h.Workspace)
	if e != nil || attemptRefs != before.AttemptRefs {
		return before, errors.New("CONTINUATION_ATTEMPT_REFS_CHANGED")
	}
	status, e := git(p.Config.Tools.Git, h.Workspace, "status", "--porcelain")
	if e != nil || status != after.Status {
		return before, errors.New("CONTINUATION_WORKSPACE_STATUS_CHANGED")
	}
	files, e := changed(p.Config.Tools.Git, h.Workspace, j.Order.Baseline.SHA)
	if e != nil {
		return before, e
	}
	sort.Strings(files)
	var inventory []CandidateEntry
	b, e := os.ReadFile(filepath.Join(h.Evidence, "candidate_inventory.json"))
	if e != nil {
		return before, e
	}
	if e = json.Unmarshal(b, &inventory); e != nil {
		return before, e
	}
	sort.Slice(inventory, func(i, k int) bool { return inventory[i].Path < inventory[k].Path })
	if len(files) != len(inventory) {
		return before, errors.New("CONTINUATION_INVENTORY_CHANGED")
	}
	for i, v := range inventory {
		if files[i] != v.Path || !j.Order.Allows(v.Path) {
			return before, errors.New("CONTINUATION_SCOPE_CHANGED")
		}
		path := filepath.Join(h.Workspace, filepath.FromSlash(v.Path))
		if v.Deleted {
			if _, e = os.Lstat(path); !os.IsNotExist(e) {
				return before, errors.New("CONTINUATION_DELETION_CHANGED")
			}
			continue
		}
		if e = regularPath(h.Workspace, v.Path); e != nil {
			return before, e
		}
		b, e = os.ReadFile(path)
		if e != nil || digest(b) != v.SHA256 {
			return before, errors.New("CONTINUATION_CONTENT_CHANGED")
		}
	}
	return before, nil
}

// The ordinary worker execution path calls this at the existing materialization
// seam. An explicitly bound continuation reuses the retained worktree; all other
// attempts keep their existing isolated materialization behavior.
func (p *Engine) prepareObjectiveWorkspace(ctx context.Context, source, root string, j Job, attempt int) (string, RepoState, error) {
	if p.Config.Autonomy.ObjectiveController {
		var raw []byte
		e := p.Store.DB.QueryRow("SELECT handoff FROM objective_continuations WHERE work_id=? AND next_attempt=?", j.ID, attempt).Scan(&raw)
		if e == nil {
			var h ObjectiveHandoff
			if e = json.Unmarshal(raw, &h); e != nil {
				return "", RepoState{}, e
			}
			if h.Attempt+1 != attempt {
				return "", RepoState{}, errors.New("CONTINUATION_ATTEMPT_CHANGED")
			}
			before, e := p.verifyRetainedObjectiveWorkspace(j, h)
			return h.Workspace, before, e
		}
		if !errors.Is(e, sql.ErrNoRows) {
			return "", RepoState{}, e
		}
	}
	return prepareWorkspace(ctx, p.Config.Tools.Git, source, root, j.Order)
}
