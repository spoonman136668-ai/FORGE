package plane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const localCandidateBaselinePrefix = "local-candidate/"

func localCandidateBaselineID(ref string) (string, bool) {
	if !strings.HasPrefix(ref, localCandidateBaselinePrefix) {
		return "", false
	}
	id := strings.TrimPrefix(ref, localCandidateBaselinePrefix)
	if !safeID.MatchString(id) {
		return "", false
	}
	return id, true
}

func baselineRefAllowed(ref string) bool {
	if strings.HasPrefix(ref, "accepted/") {
		return true
	}
	_, ok := localCandidateBaselineID(ref)
	return ok
}

type localCandidateExport struct {
	Schema             string `json:"schema"`
	WorkOrderID        string `json:"work_order_id"`
	Attempt            int    `json:"attempt"`
	BaselineSHA        string `json:"baseline_sha"`
	CandidateSHA       string `json:"candidate_sha"`
	WorkerBranch       string `json:"worker_branch"`
	DevelopmentBranch  string `json:"development_branch"`
	Bundle             string `json:"bundle"`
	BundleSHA256       string `json:"bundle_sha256"`
	Published          bool   `json:"published"`
	AcceptedRefMutated bool   `json:"accepted_ref_mutated"`
}

// ensureLocalCandidateBaseline imports only a previously ACCEPTED, evidence-verified,
// hash-verified local export into the engineering clone under a private CKB-plane
// namespace. It never creates or moves refs/heads/accepted, refs/tags/accepted, or
// refs/remotes/origin/accepted and it never changes the source working tree.
func (p *Engine) ensureLocalCandidateBaseline(ctx context.Context, w WorkOrder) error {
	parentID, local := localCandidateBaselineID(w.Baseline.Ref)
	if !local {
		return nil
	}
	if p.Config.Policy.AcceptedRefMutation {
		return errors.New("LOCAL_CANDIDATE_BASELINE_POLICY_INVALID")
	}

	parent, e := p.Store.Get(parentID)
	if e != nil || parent.State != "ACCEPTED" {
		return errors.New("LOCAL_CANDIDATE_ACCEPTANCE_REQUIRED")
	}
	if parent.Order.Repo != w.Repo {
		return errors.New("LOCAL_CANDIDATE_REPO_MISMATCH")
	}
	if e = p.VerifyEvidence(parent); e != nil {
		return errors.New("LOCAL_CANDIDATE_EVIDENCE_INVALID")
	}

	exportRoot := filepath.Join(p.Root, "exports", parentID, fmt.Sprint(parent.Attempt))
	if e = bridgeContained(p.Root, exportRoot); e != nil {
		return e
	}
	manifestPath := filepath.Join(exportRoot, "candidate.json")
	manifestRaw, e := os.ReadFile(manifestPath)
	if e != nil {
		return errors.New("LOCAL_CANDIDATE_EXPORT_REQUIRED")
	}
	var manifest localCandidateExport
	if e = json.Unmarshal(manifestRaw, &manifest); e != nil {
		return errors.New("LOCAL_CANDIDATE_EXPORT_INVALID")
	}
	expectedBundle := filepath.Join(exportRoot, "candidate.bundle")
	if manifest.Schema != "ckb-plane.candidate-export.v1" ||
		manifest.WorkOrderID != parentID ||
		manifest.Attempt != parent.Attempt ||
		manifest.CandidateSHA != w.Baseline.SHA ||
		manifest.Bundle != expectedBundle ||
		manifest.Published || manifest.AcceptedRefMutated ||
		!strings.HasPrefix(manifest.WorkerBranch, "codex/") {
		return errors.New("LOCAL_CANDIDATE_EXPORT_INVALID")
	}
	bundleRaw, e := os.ReadFile(expectedBundle)
	if e != nil || digest(bundleRaw) != manifest.BundleSHA256 {
		return errors.New("LOCAL_CANDIDATE_EXPORT_INTEGRITY_FAILED")
	}

	repo, ok := p.Config.Repos[w.Repo]
	if !ok || repo.Mode != "engineering" || strings.TrimSpace(repo.LocalPath) == "" {
		return errors.New("REPO_UNAVAILABLE")
	}
	beforeStatus, e := git(p.Config.Tools.Git, repo.LocalPath, "status", "--porcelain")
	if e != nil || beforeStatus != "" {
		return errors.New("SOURCE_HYGIENE_FAILED: starting repository is dirty")
	}
	acceptedBefore, e := refs(p.Config.Tools.Git, repo.LocalPath)
	if e != nil {
		return e
	}

	localRef := "refs/ckb-plane/candidates/" + parentID
	if existing, er := git(p.Config.Tools.Git, repo.LocalPath, "rev-parse", "--verify", localRef+"^{commit}"); er == nil {
		if existing != w.Baseline.SHA {
			return errors.New("LOCAL_CANDIDATE_REF_CONFLICT")
		}
	} else {
		if _, e = gitContext(ctx, p.Config.Tools.Git, repo.LocalPath, "bundle", "verify", expectedBundle); e != nil {
			return errors.New("LOCAL_CANDIDATE_BUNDLE_VERIFY_FAILED")
		}
		sourceRef := "refs/heads/" + manifest.WorkerBranch
		refspec := sourceRef + ":" + localRef
		if _, e = gitContext(ctx, p.Config.Tools.Git, repo.LocalPath, "fetch", "--no-tags", "--no-write-fetch-head", "--", expectedBundle, refspec); e != nil {
			return errors.New("LOCAL_CANDIDATE_IMPORT_FAILED")
		}
		imported, er := git(p.Config.Tools.Git, repo.LocalPath, "rev-parse", "--verify", localRef+"^{commit}")
		if er != nil || imported != w.Baseline.SHA {
			return errors.New("LOCAL_CANDIDATE_IMPORT_SHA_MISMATCH")
		}
	}

	acceptedAfter, e := refs(p.Config.Tools.Git, repo.LocalPath)
	if e != nil || acceptedAfter != acceptedBefore {
		return errors.New("ACCEPTED_REF_MUTATION_DETECTED")
	}
	afterStatus, e := git(p.Config.Tools.Git, repo.LocalPath, "status", "--porcelain")
	if e != nil || afterStatus != beforeStatus {
		return errors.New("SOURCE_HYGIENE_FAILED: local candidate import changed working tree")
	}
	return nil
}
