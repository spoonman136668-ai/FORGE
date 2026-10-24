package plane

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Export a verified local candidate as one commit and aligned worker/development
// refs in a private bundle. This does not push or create any accepted ref.
func (p *Engine) ExportCandidateOffline(ctx context.Context, id string) (map[string]any, error) {
	lock, e := p.controllerLock()
	if e != nil {
		// A live local controller is the state-root owner. Route the export through
		// its native loopback command instead of forcing the operator to kill a
		// completed controller just to seal an already accepted candidate bundle.
		v, er := p.callLocalController(ctx, NativeRequest{Action: "export", ID: id})
		if er != nil {
			if strings.Contains(er.Error(), "CONTROLLER_LOCKED_OR_UNAVAILABLE") {
				return nil, e
			}
			return nil, er
		}
		var result map[string]any
		b, er := json.Marshal(v)
		if er != nil {
			return nil, er
		}
		if er = json.Unmarshal(b, &result); er != nil {
			return nil, er
		}
		return result, nil
	}
	defer lock.Close()
	return p.ExportCandidate(ctx, id)
}

// ExportCandidate runs inside the current state-root owner. It is used by the
// offline command after taking the controller lock, and by the live controller's
// native loopback endpoint while that controller owns the lock.
func (p *Engine) ExportCandidate(ctx context.Context, id string) (map[string]any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	return p.exportCandidateLocked(ctx, id)
}

// exportCandidateLocked performs the existing accepted-candidate export while
// the caller already owns queueMu. AutonomyTick uses this for deterministic
// successor materialization without recursive locking.
func (p *Engine) exportCandidateLocked(ctx context.Context, id string) (map[string]any, error) {
	j, e := p.Store.Get(id)
	if e != nil {
		if errors.Is(e, sql.ErrNoRows) {
			return nil, errors.New("LOCAL_ACCEPTANCE_REQUIRED")
		}
		return nil, e
	}
	if j.State != "ACCEPTED" {
		return nil, errors.New("LOCAL_ACCEPTANCE_REQUIRED")
	}
	if e = p.VerifyEvidence(j); e != nil {
		return nil, e
	}
	root := filepath.Join(p.Root, "exports", id, fmt.Sprint(j.Attempt))
	if e = bridgeContained(p.Root, root); e != nil {
		return nil, e
	}
	resultPath := filepath.Join(root, "candidate.json")
	if b, er := os.ReadFile(resultPath); er == nil {
		var result map[string]any
		if er = json.Unmarshal(b, &result); er != nil {
			return nil, er
		}
		bundle, er := os.ReadFile(filepath.Join(root, "candidate.bundle"))
		if er != nil || digest(bundle) != result["bundle_sha256"] {
			return nil, errors.New("EXPORT_INTEGRITY_FAILED")
		}
		return result, nil
	}
	if _, er := os.Stat(root); !os.IsNotExist(er) {
		return nil, errors.New("EXPORT_INTERRUPTED_REVIEW_REQUIRED")
	}
	work, _, e := prepare(ctx, p.Config.Tools.Git, p.Config.Repos[j.Order.Repo].LocalPath, root, j.Order)
	if e != nil {
		return nil, e
	}
	b, e := os.ReadFile(filepath.Join(j.Evidence, "candidate_inventory.json"))
	if e != nil {
		return nil, e
	}
	var entries []CandidateEntry
	if e = json.Unmarshal(b, &entries); e != nil {
		return nil, e
	}
	for _, entry := range entries {
		if !j.Order.Allows(entry.Path) {
			return nil, errors.New("EXPORT_SCOPE_INVALID")
		}
		dst := filepath.Join(work, filepath.FromSlash(entry.Path))
		if e = bridgeContained(work, dst); e != nil {
			return nil, e
		}
		if entry.Deleted {
			if e = os.Remove(dst); e != nil {
				return nil, e
			}
			continue
		}
		src := filepath.Join(j.Evidence, "candidate_files", filepath.FromSlash(entry.Path))
		if e = regularPath(filepath.Join(j.Evidence, "candidate_files"), entry.Path); e != nil {
			return nil, e
		}
		data, e := os.ReadFile(src)
		if e != nil || digest(data) != entry.SHA256 {
			return nil, errors.New("EXPORT_CANDIDATE_HASH_MISMATCH")
		}
		if e = os.MkdirAll(filepath.Dir(dst), 0700); e != nil {
			return nil, e
		}
		if e = os.WriteFile(dst, data, 0600); e != nil {
			return nil, e
		}
	}
	tool := p.Config.Tools.Git
	if _, e = gitContext(ctx, tool, work, "add", "--all", "--"); e != nil {
		return nil, e
	}
	if _, e = gitContext(ctx, tool, work, "-c", "user.name=CKB Plane", "-c", "user.email=plane@localhost", "-c", "commit.gpgsign=false", "commit", "-m", "Candidate "+j.ID); e != nil {
		return nil, e
	}
	sha, e := git(tool, work, "rev-parse", "HEAD")
	if e != nil {
		return nil, e
	}
	count, e := git(tool, work, "rev-list", "--count", j.Order.Baseline.SHA+"..HEAD")
	if e != nil || count != "1" {
		return nil, errors.New("EXPORT_ONE_COMMIT_REQUIRED")
	}
	development := "development/" + strings.TrimPrefix(j.Order.Worker.Branch, "codex/")
	if _, e = gitContext(ctx, tool, work, "branch", development, sha); e != nil {
		return nil, e
	}
	bundle := filepath.Join(root, "candidate.bundle")
	if _, e = gitContext(ctx, tool, work, "bundle", "create", bundle, j.Order.Worker.Branch, development, "^"+j.Order.Baseline.SHA); e != nil {
		return nil, e
	}
	raw, e := os.ReadFile(bundle)
	if e != nil {
		return nil, e
	}
	result := map[string]any{"schema": "ckb-plane.candidate-export.v1", "work_order_id": id, "attempt": j.Attempt, "baseline_sha": j.Order.Baseline.SHA, "candidate_sha": sha, "worker_branch": j.Order.Worker.Branch, "development_branch": development, "bundle": bundle, "bundle_sha256": digest(raw), "published": false, "accepted_ref_mutated": false}
	data, _ := json.MarshalIndent(result, "", "  ")
	if e = durableNew(resultPath, data); e != nil {
		return nil, e
	}
	return result, nil
}
