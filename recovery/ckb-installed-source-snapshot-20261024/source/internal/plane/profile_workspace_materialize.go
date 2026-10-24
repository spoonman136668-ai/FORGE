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

type ProfileWorkspaceMaterializedEvidence struct {
	ProfileName                string                       `json:"profile_name"`
	Mode                       string                       `json:"mode"`
	WorkOrderID                string                       `json:"work_order_id"`
	RepoPath                   string                       `json:"repo_path"`
	RequestedBaselineRef       string                       `json:"requested_baseline_ref"`
	RequiredBaselineSHA        string                       `json:"required_baseline_sha"`
	Baseline                   ProfileBaselineResolution    `json:"baseline"`
	Preflight                  ProfilePreflightEvidence     `json:"preflight"`
	RepoBefore                 ProfileWorkspaceRepoState    `json:"repo_before"`
	RepoAfter                  ProfileWorkspaceRepoState    `json:"repo_after"`
	Workspace                  ProfileMaterializedWorkspace `json:"workspace"`
	AcceptedRefsUnchanged      bool                         `json:"accepted_refs_unchanged"`
	GitStatusUnchanged         bool                         `json:"git_status_unchanged"`
	HeadUnchanged              bool                         `json:"head_unchanged"`
	BranchUnchanged            bool                         `json:"branch_unchanged"`
	BranchRefsUnchanged        bool                         `json:"branch_refs_unchanged"`
	WorkerLaunchAllowed        bool                         `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed bool                         `json:"candidate_acceptance_allowed"`
	RuntimeForbidden           bool                         `json:"runtime_forbidden"`
	WorkerLaunched             bool                         `json:"worker_launched"`
	CandidateAccepted          bool                         `json:"candidate_accepted"`
	RuntimeLaunched            bool                         `json:"runtime_launched"`
	EvidencePath               string                       `json:"evidence_path,omitempty"`
	Status                     string                       `json:"status"`
	Created                    string                       `json:"created"`
}

type ProfileMaterializedWorkspace struct {
	WorkspaceRoot                   string   `json:"workspace_root"`
	PrivateRepositoryPath           string   `json:"private_repository_path"`
	PrivateWorktreePath             string   `json:"private_worktree_path"`
	CandidateDiffPath               string   `json:"candidate_diff_path"`
	AttemptEvidencePath             string   `json:"attempt_evidence_path"`
	PlanOnly                        bool     `json:"plan_only"`
	PolicyReadonly                  bool     `json:"policy_readonly"`
	WorkspaceCreatedByR3c           bool     `json:"workspace_created_by_r3c"`
	PrivateRepositoryCreatedByR3c   bool     `json:"private_repository_created_by_r3c"`
	PrivateWorktreeCreatedByR3c     bool     `json:"private_worktree_created_by_r3c"`
	PrivateRepositoryLocalFetchUsed bool     `json:"private_repository_local_fetch_used"`
	PrivateRepositoryRemoteRemoved  bool     `json:"private_repository_remote_removed"`
	PrivateRepositoryRemotes        string   `json:"private_repository_remotes"`
	WorkspaceHead                   string   `json:"workspace_head"`
	WorkspaceBranch                 string   `json:"workspace_branch"`
	WorkspaceStatus                 string   `json:"workspace_status"`
	WorkspaceExists                 bool     `json:"workspace_exists"`
	WorkspaceInsidePlane            bool     `json:"workspace_inside_plane"`
	WorkspaceInsideSourceRepo       bool     `json:"workspace_inside_source_repo"`
	SourceRepoInsideWorkspace       bool     `json:"source_repo_inside_workspace"`
	SourceRepoMutationAllowed       bool     `json:"source_repo_mutation_allowed"`
	AcceptedRefMutationAllowed      bool     `json:"accepted_ref_mutation_allowed"`
	WorkerLaunchAllowed             bool     `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed      bool     `json:"candidate_acceptance_allowed"`
	RuntimeLaunchAllowed            bool     `json:"runtime_launch_allowed"`
	RemotePushAllowed               bool     `json:"remote_push_allowed"`
	AllowedPaths                    []string `json:"allowed_paths"`
	ForbiddenPaths                  []string `json:"forbidden_paths"`
	AcceptanceAuthority             string   `json:"acceptance_authority"`
}

func (p *Engine) MaterializeReadonlyWorkspaceSelectedProfile(ctx context.Context, evidenceRoot string) (ev ProfileWorkspaceMaterializedEvidence, err error) {
	created := time.Now().UTC()
	ev.Created = created.Format(time.RFC3339Nano)
	ev.Status = "BLOCKED"
	if evidenceRoot == "" {
		evidenceRoot = filepath.Join(p.Root, "artifacts", "r3c")
	}
	if mkdirErr := os.MkdirAll(evidenceRoot, 0o700); mkdirErr != nil {
		return ev, mkdirErr
	}
	defer func() {
		if ev.ProfileName == "" {
			ev.ProfileName = "unknown"
		}
		if ev.EvidencePath == "" {
			ev.EvidencePath = filepath.Join(evidenceRoot, ev.ProfileName+"-workspace-materialized-readonly.json")
		}
		if err != nil && ev.Status == "BLOCKED" {
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
	ev.EvidencePath = filepath.Join(evidenceRoot, profile.ProfileName+"-workspace-materialized-readonly.json")

	if profile.ProfileName != "ckb-readonly" || profile.Mode != "readonly-baseline-verification" {
		return ev, errors.New("WORKSPACE_MATERIALIZE_FORBIDDEN: R3c is ckb-readonly only")
	}
	if profile.WorkerLaunchAllowed || profile.CandidateAcceptanceAllowed || !profile.RuntimeForbidden {
		return ev, errors.New("WORKSPACE_MATERIALIZE_FORBIDDEN: ckb-readonly must remain non-executable")
	}
	if strings.TrimSpace(profile.AcceptedRefsPolicy) == "" || !strings.Contains(strings.ToLower(profile.AcceptedRefsPolicy), "never") {
		return ev, errors.New("WORKSPACE_MATERIALIZE_FORBIDDEN: accepted refs policy must forbid mutation")
	}

	preflight, preflightErr := p.PreflightDispatchProfile(ctx, profile, filepath.Join(evidenceRoot, "preflight"))
	ev.Preflight = preflight
	if preflightErr != nil {
		return ev, preflightErr
	}
	ev.Baseline = preflight.Baseline
	if preflight.Status != "DRY_DISPATCH_READY" || preflight.Baseline.ResolvedSHA != profile.RequiredBaselineSHA {
		return ev, errors.New("WORKSPACE_MATERIALIZE_BASELINE_NOT_VERIFIED")
	}

	before, stateErr := p.profileWorkspaceRepoState(ctx, profile.RepoPath)
	if stateErr != nil {
		return ev, stateErr
	}
	ev.RepoBefore = before

	safeProfileName := profileWorkspaceSafeSegment(profile.ProfileName)
	if safeProfileName == "" {
		safeProfileName = "profile"
	}
	planRoot := filepath.Join(p.Root, "workspaces", "r3c", safeProfileName, profileWorkspaceShortSHA(profile.RequiredBaselineSHA)+"-"+fmt.Sprintf("%x", created.UnixNano()))
	privateRepo := filepath.Join(planRoot, "repo")
	privateWorktree := filepath.Join(planRoot, "tree")
	ev.Workspace = ProfileMaterializedWorkspace{
		WorkspaceRoot:                   planRoot,
		PrivateRepositoryPath:           privateRepo,
		PrivateWorktreePath:             privateWorktree,
		CandidateDiffPath:               filepath.Join(p.Root, "evidence", profile.WorkOrderID, "r3c-materialized", "candidate.diff"),
		AttemptEvidencePath:             filepath.Join(p.Root, "evidence", profile.WorkOrderID, "r3c-materialized"),
		PlanOnly:                        false,
		PolicyReadonly:                  true,
		WorkspaceCreatedByR3c:           false,
		PrivateRepositoryCreatedByR3c:   false,
		PrivateWorktreeCreatedByR3c:     false,
		PrivateRepositoryLocalFetchUsed: false,
		PrivateRepositoryRemoteRemoved:  false,
		SourceRepoMutationAllowed:       false,
		AcceptedRefMutationAllowed:      false,
		WorkerLaunchAllowed:             false,
		CandidateAcceptanceAllowed:      false,
		RuntimeLaunchAllowed:            false,
		RemotePushAllowed:               false,
		AllowedPaths:                    append([]string{}, profile.AllowedPaths...),
		ForbiddenPaths:                  append([]string{}, profile.ForbiddenPaths...),
		AcceptanceAuthority:             profile.AcceptanceAuthority,
	}
	if profileWorkspacePathExists(planRoot) {
		return ev, fmt.Errorf("WORKSPACE_MATERIALIZE_PATH_OCCUPIED: %s", planRoot)
	}
	if err = os.MkdirAll(planRoot, 0o700); err != nil {
		return ev, err
	}
	ev.Workspace.WorkspaceCreatedByR3c = true

	if _, err = gitContext(ctx, p.Config.Tools.Git, planRoot, "init", privateRepo); err != nil {
		return ev, err
	}
	ev.Workspace.PrivateRepositoryCreatedByR3c = true

	if _, err = gitContext(ctx, p.Config.Tools.Git, privateRepo, "fetch", "--no-tags", "--", profile.RepoPath, profile.RequiredBaselineSHA); err != nil {
		return ev, fmt.Errorf("BASELINE_LOCAL_FETCH_FAILED: %w", err)
	}
	ev.Workspace.PrivateRepositoryLocalFetchUsed = true
	if _, err = gitContext(ctx, p.Config.Tools.Git, privateRepo, "rev-parse", "--verify", profile.RequiredBaselineSHA+"^{commit}"); err != nil {
		return ev, errors.New("BASELINE_MISMATCH")
	}
	if _, err = gitContext(ctx, p.Config.Tools.Git, privateRepo, "worktree", "add", "--detach", privateWorktree, profile.RequiredBaselineSHA); err != nil {
		return ev, err
	}
	ev.Workspace.PrivateWorktreeCreatedByR3c = true
	ev.Workspace.PrivateRepositoryRemoteRemoved = true
	remotes, remoteErr := gitContext(ctx, p.Config.Tools.Git, privateRepo, "remote")
	if remoteErr != nil {
		return ev, remoteErr
	}
	ev.Workspace.PrivateRepositoryRemotes = strings.TrimSpace(remotes)

	ev.Workspace.WorkspaceHead, err = gitContext(ctx, p.Config.Tools.Git, privateWorktree, "rev-parse", "HEAD")
	if err != nil {
		return ev, err
	}
	ev.Workspace.WorkspaceBranch, err = gitContext(ctx, p.Config.Tools.Git, privateWorktree, "branch", "--show-current")
	if err != nil {
		return ev, err
	}
	ev.Workspace.WorkspaceStatus, err = gitContext(ctx, p.Config.Tools.Git, privateWorktree, "status", "--porcelain=v1", "-uall")
	if err != nil {
		return ev, err
	}
	_, statErr := os.Stat(privateWorktree)
	ev.Workspace.WorkspaceExists = statErr == nil
	ev.Workspace.WorkspaceInsidePlane = pathIsWithinOrEqual(p.Root, planRoot)
	ev.Workspace.WorkspaceInsideSourceRepo = pathIsWithinOrEqual(profile.RepoPath, planRoot)
	ev.Workspace.SourceRepoInsideWorkspace = pathIsWithinOrEqual(planRoot, profile.RepoPath)

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

	if !ev.AcceptedRefsUnchanged {
		return ev, errors.New("WORKSPACE_MATERIALIZE_ACCEPTED_REFS_MUTATED")
	}
	if !ev.GitStatusUnchanged || !ev.HeadUnchanged || !ev.BranchUnchanged || !ev.BranchRefsUnchanged {
		return ev, errors.New("WORKSPACE_MATERIALIZE_SOURCE_REPO_MUTATED")
	}
	if !ev.Workspace.WorkspaceExists || ev.Workspace.WorkspaceHead != profile.RequiredBaselineSHA || ev.Workspace.WorkspaceStatus != "" {
		return ev, errors.New("WORKSPACE_MATERIALIZE_WORKTREE_INVALID")
	}
	if ev.Workspace.PrivateRepositoryRemotes != "" || !ev.Workspace.PrivateRepositoryRemoteRemoved {
		return ev, errors.New("WORKSPACE_MATERIALIZE_PRIVATE_REMOTE_NOT_REMOVED")
	}
	if !ev.Workspace.WorkspaceInsidePlane || ev.Workspace.WorkspaceInsideSourceRepo || ev.Workspace.SourceRepoInsideWorkspace {
		return ev, errors.New("WORKSPACE_MATERIALIZE_SOURCE_SEPARATION_INVALID")
	}
	ev.Status = "WORKSPACE_MATERIALIZED_READONLY"
	return ev, nil
}

func profileWorkspaceSafeSegment(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return ""
	}
	var b strings.Builder
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z':
			b.WriteRune(r)
		case r >= 'A' && r <= 'Z':
			b.WriteRune(r)
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == '-' || r == '_' || r == '.':
			b.WriteRune(r)
		default:
			b.WriteRune('-')
		}
	}
	out := strings.Trim(b.String(), "-_.")
	if len(out) > 40 {
		out = out[:40]
		out = strings.Trim(out, "-_.")
	}
	return out
}
func pathIsWithinOrEqual(base, target string) bool {
	baseAbs, err := filepath.Abs(base)
	if err != nil {
		return false
	}
	targetAbs, err := filepath.Abs(target)
	if err != nil {
		return false
	}
	baseAbs = filepath.Clean(baseAbs)
	targetAbs = filepath.Clean(targetAbs)
	if strings.EqualFold(baseAbs, targetAbs) {
		return true
	}
	rel, err := filepath.Rel(baseAbs, targetAbs)
	if err != nil {
		return false
	}
	return rel != "." && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)) && !filepath.IsAbs(rel)
}
