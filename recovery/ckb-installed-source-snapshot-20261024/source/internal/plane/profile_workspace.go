package plane

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type ProfileWorkspaceDryRunEvidence struct {
	ProfileName                string                    `json:"profile_name"`
	Mode                       string                    `json:"mode"`
	WorkOrderID                string                    `json:"work_order_id"`
	RepoPath                   string                    `json:"repo_path"`
	RequestedBaselineRef       string                    `json:"requested_baseline_ref"`
	RequiredBaselineSHA        string                    `json:"required_baseline_sha"`
	Baseline                   ProfileBaselineResolution `json:"baseline"`
	Preflight                  ProfilePreflightEvidence  `json:"preflight"`
	RepoBefore                 ProfileWorkspaceRepoState `json:"repo_before"`
	RepoAfter                  ProfileWorkspaceRepoState `json:"repo_after"`
	WorkspacePlan              ProfileWorkspacePlan      `json:"workspace_plan"`
	AcceptedRefsUnchanged      bool                      `json:"accepted_refs_unchanged"`
	GitStatusUnchanged         bool                      `json:"git_status_unchanged"`
	HeadUnchanged              bool                      `json:"head_unchanged"`
	BranchUnchanged            bool                      `json:"branch_unchanged"`
	BranchRefsUnchanged        bool                      `json:"branch_refs_unchanged"`
	WorkerLaunchAllowed        bool                      `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed bool                      `json:"candidate_acceptance_allowed"`
	RuntimeForbidden           bool                      `json:"runtime_forbidden"`
	WorkerLaunched             bool                      `json:"worker_launched"`
	CandidateAccepted          bool                      `json:"candidate_accepted"`
	RuntimeLaunched            bool                      `json:"runtime_launched"`
	EvidencePath               string                    `json:"evidence_path,omitempty"`
	Status                     string                    `json:"status"`
	Created                    string                    `json:"created"`
}

type ProfileWorkspaceRepoState struct {
	Head         string `json:"head"`
	Branch       string `json:"branch"`
	Status       string `json:"status"`
	AcceptedRefs string `json:"accepted_refs"`
	BranchRefs   string `json:"branch_refs"`
}

type ProfileWorkspacePlan struct {
	WorkOrderID                   string   `json:"work_order_id"`
	WorkspaceRoot                 string   `json:"workspace_root"`
	PrivateRepositoryPath         string   `json:"private_repository_path"`
	PrivateWorktreePath           string   `json:"private_worktree_path"`
	CandidateDiffPath             string   `json:"candidate_diff_path"`
	EvidencePath                  string   `json:"attempt_evidence_path"`
	PlanOnly                      bool     `json:"plan_only"`
	WorkspaceCreatedByR3b         bool     `json:"workspace_created_by_r3b"`
	PrivateCloneCreatedByR3b      bool     `json:"private_clone_created_by_r3b"`
	PrivateWorktreeCreatedByR3b   bool     `json:"private_worktree_created_by_r3b"`
	SourceRepoMutationAllowed     bool     `json:"source_repo_mutation_allowed"`
	AcceptedRefMutationAllowed    bool     `json:"accepted_ref_mutation_allowed"`
	WorkerLaunchAllowed           bool     `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed    bool     `json:"candidate_acceptance_allowed"`
	RuntimeLaunchAllowed          bool     `json:"runtime_launch_allowed"`
	RemotePushAllowed             bool     `json:"remote_push_allowed"`
	AllowedPaths                  []string `json:"allowed_paths"`
	ForbiddenPaths                []string `json:"forbidden_paths"`
	AcceptanceAuthority           string   `json:"acceptance_authority"`
	RequiredPrivateCloneBeforeRun bool     `json:"required_private_clone_before_run"`
}

func (p *Engine) WorkspaceDryRunSelectedProfile(ctx context.Context, evidenceRoot string) (ev ProfileWorkspaceDryRunEvidence, err error) {
	ev.Created = time.Now().UTC().Format(time.RFC3339Nano)
	ev.Status = "BLOCKED"
	if evidenceRoot == "" {
		evidenceRoot = filepath.Join(p.Root, "artifacts", "r3b")
	}
	if mkdirErr := os.MkdirAll(evidenceRoot, 0o700); mkdirErr != nil {
		return ev, mkdirErr
	}
	defer func() {
		if ev.ProfileName == "" {
			ev.ProfileName = "unknown"
		}
		if ev.EvidencePath == "" {
			ev.EvidencePath = filepath.Join(evidenceRoot, ev.ProfileName+"-workspace-dry-run.json")
		}
		if err != nil && ev.Status == "BLOCKED" {
			// Keep the failure serializable even when the caller returns the error.
			ev.WorkerLaunched = false
			ev.CandidateAccepted = false
			ev.RuntimeLaunched = false
		}
		_ = writeJSON(ev.EvidencePath, ev)
	}()

	if p.Profile == nil {
		return ev, errors.New("PROFILE_REQUIRED: no dispatch profile selected")
	}
	profile := *p.Profile
	ev.ProfileName = profile.ProfileName
	ev.Mode = profile.Mode
	ev.WorkOrderID = profile.WorkOrderID
	ev.RepoPath = profile.RepoPath
	ev.RequestedBaselineRef = profile.RequiredBaselineRef
	ev.RequiredBaselineSHA = profile.RequiredBaselineSHA
	ev.WorkerLaunchAllowed = profile.WorkerLaunchAllowed
	ev.CandidateAcceptanceAllowed = profile.CandidateAcceptanceAllowed
	ev.RuntimeForbidden = profile.RuntimeForbidden
	ev.WorkerLaunched = false
	ev.CandidateAccepted = false
	ev.RuntimeLaunched = false
	ev.EvidencePath = filepath.Join(evidenceRoot, profile.ProfileName+"-workspace-dry-run.json")

	if profile.ProfileName != "ckb-readonly" || profile.Mode != "readonly-baseline-verification" {
		return ev, errors.New("WORKSPACE_DRY_RUN_FORBIDDEN: R3b is ckb-readonly only")
	}
	if profile.WorkerLaunchAllowed || profile.CandidateAcceptanceAllowed || !profile.RuntimeForbidden {
		return ev, errors.New("WORKSPACE_DRY_RUN_FORBIDDEN: ckb-readonly must remain non-executable")
	}
	if strings.TrimSpace(profile.AcceptedRefsPolicy) == "" || !strings.Contains(strings.ToLower(profile.AcceptedRefsPolicy), "never") {
		return ev, errors.New("WORKSPACE_DRY_RUN_FORBIDDEN: accepted refs policy must forbid mutation")
	}

	preflight, preflightErr := p.PreflightDispatchProfile(ctx, profile, filepath.Join(evidenceRoot, "preflight"))
	ev.Preflight = preflight
	if preflightErr != nil {
		return ev, preflightErr
	}
	ev.Baseline = preflight.Baseline

	before, stateErr := p.profileWorkspaceRepoState(ctx, profile.RepoPath)
	if stateErr != nil {
		return ev, stateErr
	}
	ev.RepoBefore = before

	planRoot := filepath.Join(p.Root, "workspaces", profile.WorkOrderID, "r3b-dry-run-"+profileWorkspaceShortSHA(profile.RequiredBaselineSHA))
	ev.WorkspacePlan = ProfileWorkspacePlan{
		WorkOrderID:                   profile.WorkOrderID,
		WorkspaceRoot:                 planRoot,
		PrivateRepositoryPath:         filepath.Join(planRoot, "repository"),
		PrivateWorktreePath:           filepath.Join(planRoot, "worktree"),
		CandidateDiffPath:             filepath.Join(p.Root, "evidence", profile.WorkOrderID, "r3b-dry-run", "candidate.diff"),
		EvidencePath:                  filepath.Join(p.Root, "evidence", profile.WorkOrderID, "r3b-dry-run"),
		PlanOnly:                      true,
		WorkspaceCreatedByR3b:         false,
		PrivateCloneCreatedByR3b:      false,
		PrivateWorktreeCreatedByR3b:   false,
		SourceRepoMutationAllowed:     false,
		AcceptedRefMutationAllowed:    false,
		WorkerLaunchAllowed:           false,
		CandidateAcceptanceAllowed:    false,
		RuntimeLaunchAllowed:          false,
		RemotePushAllowed:             false,
		AllowedPaths:                  append([]string{}, profile.AllowedPaths...),
		ForbiddenPaths:                append([]string{}, profile.ForbiddenPaths...),
		AcceptanceAuthority:           profile.AcceptanceAuthority,
		RequiredPrivateCloneBeforeRun: true,
	}
	if profileWorkspacePathExists(planRoot) {
		return ev, fmt.Errorf("WORKSPACE_DRY_RUN_PATH_OCCUPIED: %s", planRoot)
	}

	after, afterErr := p.profileWorkspaceRepoState(ctx, profile.RepoPath)
	if afterErr != nil {
		return ev, afterErr
	}
	ev.RepoAfter = after
	ev.AcceptedRefsUnchanged = before.AcceptedRefs == after.AcceptedRefs
	ev.GitStatusUnchanged = before.Status == after.Status
	ev.HeadUnchanged = before.Head == after.Head
	ev.BranchUnchanged = before.Branch == after.Branch
	ev.BranchRefsUnchanged = before.BranchRefs == after.BranchRefs

	if preflight.Status != "DRY_DISPATCH_READY" || preflight.Baseline.ResolvedSHA != profile.RequiredBaselineSHA {
		return ev, errors.New("WORKSPACE_DRY_RUN_BASELINE_NOT_VERIFIED")
	}
	if !ev.AcceptedRefsUnchanged {
		return ev, errors.New("WORKSPACE_DRY_RUN_ACCEPTED_REFS_MUTATED")
	}
	if !ev.GitStatusUnchanged || !ev.HeadUnchanged || !ev.BranchUnchanged || !ev.BranchRefsUnchanged {
		return ev, errors.New("WORKSPACE_DRY_RUN_SOURCE_REPO_MUTATED")
	}
	if ev.WorkspacePlan.WorkspaceCreatedByR3b || ev.WorkspacePlan.PrivateCloneCreatedByR3b || ev.WorkspacePlan.PrivateWorktreeCreatedByR3b {
		return ev, errors.New("WORKSPACE_DRY_RUN_CREATED_WORKSPACE")
	}
	ev.Status = "WORKSPACE_DRY_RUN_READY"
	return ev, nil
}

func (p *Engine) profileWorkspaceRepoState(ctx context.Context, repo string) (ProfileWorkspaceRepoState, error) {
	var st ProfileWorkspaceRepoState
	var err error
	st.Head, err = gitContext(ctx, p.Config.Tools.Git, repo, "rev-parse", "HEAD")
	if err != nil {
		return st, err
	}
	st.Branch, err = gitContext(ctx, p.Config.Tools.Git, repo, "branch", "--show-current")
	if err != nil {
		return st, err
	}
	st.Status, err = gitContext(ctx, p.Config.Tools.Git, repo, "status", "--porcelain=v1", "-uall")
	if err != nil {
		return st, err
	}
	st.AcceptedRefs, err = gitContext(ctx, p.Config.Tools.Git, repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/accepted/", "refs/tags/accepted/", "refs/remotes/origin/accepted/")
	if err != nil {
		return st, err
	}
	st.BranchRefs, err = gitContext(ctx, p.Config.Tools.Git, repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/", "refs/tags/", "refs/remotes/origin/")
	if err != nil {
		return st, err
	}
	return st, nil
}

func profileWorkspaceShortSHA(sha string) string {
	if len(sha) >= 12 {
		return sha[:12]
	}
	return sha
}

func profileWorkspacePathExists(path string) bool {
	_, err := os.Lstat(path)
	return err == nil || !os.IsNotExist(err)
}
