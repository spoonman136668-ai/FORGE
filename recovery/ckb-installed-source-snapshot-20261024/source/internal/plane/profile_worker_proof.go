package plane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

const r4aProfileName = "ckb-r4a-source-proof"
const r4aProfileMode = "ckb-source-only-worker-proof"
const r4aWorkOrderID = "CKB_R4A_SOURCE_ONLY_WORKER_PROOF_R1"
const r4aBaselineRef = "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1"
const r4aBaselineSHA = "01260dda4bdebc454921cdf0c5d3d0eeafef7629"
const r4aDocPath = "docs/CKB_PLANE_R4A_SOURCE_ONLY_PROOF.md"
const r4aTestPath = "pkg/r4a_source_only_worker_proof_test.go"
const r4aFocusedTest = "TestR4aSourceOnlyWorkerProofMarker"

// r4aRequireExactBQBaseline keeps production R4a bound to the exact accepted BQ baseline. Tests may temporarily disable this package-local seam because they use synthetic fixture commits.
var r4aRequireExactBQBaseline = true

type ProfileWorkerProofEvidence struct {
	ProfileName                string                    `json:"profile_name"`
	Mode                       string                    `json:"mode"`
	WorkOrderID                string                    `json:"work_order_id"`
	WorkOrderTitle             string                    `json:"work_order_title"`
	RepoPath                   string                    `json:"repo_path"`
	BaselineRef                string                    `json:"baseline_ref"`
	BaselineSHA                string                    `json:"baseline_sha"`
	Preflight                  ProfilePreflightEvidence  `json:"preflight"`
	RepoBefore                 ProfileWorkspaceRepoState `json:"repo_before"`
	RepoAfter                  ProfileWorkspaceRepoState `json:"repo_after"`
	PostWorkerScrub            ProfileScrubEvidence      `json:"post_worker_scrub"`
	ProfileWorkOrderPath       string                    `json:"profile_work_order_path"`
	WorkerProofEvidencePath    string                    `json:"worker_proof_evidence_path"`
	FinalState                 string                    `json:"final_state"`
	Reason                     string                    `json:"reason"`
	Attempt                    int                       `json:"attempt"`
	ReservedAttempt            int                       `json:"reserved_attempt"`
	Workspace                  string                    `json:"workspace"`
	AcceptanceEvidence         string                    `json:"acceptance_evidence"`
	CandidateDiffPath          string                    `json:"candidate_diff_path"`
	ChangedFiles               []string                  `json:"changed_files"`
	Checks                     []Check                   `json:"checks"`
	WorkerExit                 map[string]any            `json:"worker_exit,omitempty"`
	AllowedPaths               []string                  `json:"allowed_paths"`
	ForbiddenPaths             []string                  `json:"forbidden_paths"`
	GoPackages                 []string                  `json:"go_packages"`
	FocusedTests               []string                  `json:"focused_tests"`
	RunGoTestAll               bool                      `json:"run_go_test_all"`
	WorkerLaunchAllowed        bool                      `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed bool                      `json:"candidate_acceptance_allowed"`
	RuntimeForbidden           bool                      `json:"runtime_forbidden"`
	WorkerLaunched             bool                      `json:"worker_launched"`
	CandidateAccepted          bool                      `json:"candidate_accepted"`
	RuntimeLaunched            bool                      `json:"runtime_launched"`
	DeploymentRan              bool                      `json:"deployment_ran"`
	AcceptedRefPromotionRan    bool                      `json:"accepted_ref_promotion_ran"`
	SourceStatusUnchanged      bool                      `json:"source_status_unchanged"`
	SourceHeadUnchanged        bool                      `json:"source_head_unchanged"`
	SourceBranchUnchanged      bool                      `json:"source_branch_unchanged"`
	AcceptedRefsUnchanged      bool                      `json:"accepted_refs_unchanged"`
	BranchRefsUnchanged        bool                      `json:"branch_refs_unchanged"`
	WorkspaceInsidePlane       bool                      `json:"workspace_inside_plane"`
	WorkspaceInsideSourceRepo  bool                      `json:"workspace_inside_source_repo"`
	SourceRepoInsideWorkspace  bool                      `json:"source_repo_inside_workspace"`
	DiffTouchesOnlyAllowlist   bool                      `json:"diff_touches_only_allowlist"`
	RequiredFilesPresent       bool                      `json:"required_files_present"`
	MarkerContentPresent       bool                      `json:"marker_content_present"`
	FocusedTestPassed          bool                      `json:"focused_test_passed"`
	GoAllPassed                bool                      `json:"go_all_passed"`
	GoAllConfigured            bool                      `json:"go_all_configured"`
	AcceptanceInputUnchanged   bool                      `json:"acceptance_input_unchanged"`
	AcceptedRefCheckPassed     bool                      `json:"accepted_ref_check_passed"`
	Status                     string                    `json:"status"`
	Created                    string                    `json:"created"`
}

func (p *Engine) WorkerProofSelectedProfile(ctx context.Context, evidenceRoot string) (ev ProfileWorkerProofEvidence, err error) {
	if e := p.guardLegacyExecution(); e != nil {
		return ev, e
	}
	ev.Created = time.Now().UTC().Format(time.RFC3339Nano)
	ev.Status = "BLOCKED"
	if evidenceRoot == "" {
		evidenceRoot = filepath.Join(p.Root, "artifacts", "r4a")
	}
	if mkdirErr := os.MkdirAll(evidenceRoot, 0o700); mkdirErr != nil {
		return ev, mkdirErr
	}
	defer func() {
		if ev.ProfileName == "" {
			ev.ProfileName = "unknown"
		}
		if ev.WorkerProofEvidencePath == "" {
			ev.WorkerProofEvidencePath = filepath.Join(evidenceRoot, ev.ProfileName+"-worker-proof.json")
		}
		if err != nil && ev.Reason == "" {
			ev.Reason = err.Error()
		}
		_ = writeJSON(ev.WorkerProofEvidencePath, ev)
	}()

	if p.Profile == nil {
		return ev, errors.New("PROFILE_REQUIRED: no dispatch profile selected")
	}
	profile := *p.Profile
	ev.ProfileName = profile.ProfileName
	ev.Mode = profile.Mode
	ev.WorkOrderID = profile.WorkOrderID
	ev.RepoPath = profile.RepoPath
	ev.BaselineRef = profile.RequiredBaselineRef
	ev.BaselineSHA = profile.RequiredBaselineSHA
	ev.AllowedPaths = append([]string{}, profile.AllowedPaths...)
	ev.ForbiddenPaths = append([]string{}, profile.ForbiddenPaths...)
	ev.GoPackages = append([]string{}, profile.GoPackages...)
	ev.FocusedTests = append([]string{}, profile.FocusedTests...)
	ev.RunGoTestAll = profile.RunGoTestAll == nil || *profile.RunGoTestAll
	ev.WorkerLaunchAllowed = profile.WorkerLaunchAllowed
	ev.CandidateAcceptanceAllowed = profile.CandidateAcceptanceAllowed
	ev.RuntimeForbidden = profile.RuntimeForbidden
	ev.WorkerProofEvidencePath = filepath.Join(evidenceRoot, profile.ProfileName+"-worker-proof.json")

	if profile.ProfileName != r4aProfileName || profile.Mode != r4aProfileMode || profile.WorkOrderID != r4aWorkOrderID {
		return ev, errors.New("PROFILE_WORKER_PROOF_FORBIDDEN: R4a only permits ckb-r4a-source-proof")
	}
	if profile.RequiredBaselineRef != r4aBaselineRef {
		return ev, errors.New("BASELINE_MISMATCH: R4a requires exact BQ accepted baseline ref")
	}
	if r4aRequireExactBQBaseline && profile.RequiredBaselineSHA != r4aBaselineSHA {
		return ev, errors.New("BASELINE_MISMATCH: R4a requires exact BQ accepted baseline")
	}
	if !profile.WorkerLaunchAllowed || !profile.CandidateAcceptanceAllowed || !profile.RuntimeForbidden {
		return ev, errors.New("PROFILE_POLICY_INVALID: R4a requires worker launch/candidate acceptance and runtime forbidden")
	}
	if !sameStringSet(profile.AllowedPaths, []string{r4aDocPath, r4aTestPath}) {
		return ev, fmt.Errorf("PROFILE_SCOPE_INVALID: R4a allowed paths must be exactly %s and %s", r4aDocPath, r4aTestPath)
	}
	if len(profile.FocusedTests) != 1 || normalizeFocusedTest(profile.FocusedTests[0]) != "^"+r4aFocusedTest+"$" {
		return ev, errors.New("PROFILE_TEST_INVALID: R4a focused test must be TestR4aSourceOnlyWorkerProofMarker")
	}
	if len(profile.GoPackages) != 1 || profile.GoPackages[0] != "./pkg" {
		return ev, errors.New("PROFILE_TEST_INVALID: R4a must test ./pkg only")
	}

	before, stateErr := p.profileWorkspaceRepoState(ctx, profile.RepoPath)
	if stateErr != nil {
		return ev, stateErr
	}
	ev.RepoBefore = before
	if strings.TrimSpace(before.Status) != "" {
		return ev, errors.New("SOURCE_HYGIENE_FAILED: source CKB repo must be clean before R4a worker proof")
	}

	preflight, preflightErr := p.PreflightDispatchProfile(ctx, profile, filepath.Join(evidenceRoot, "preflight"))
	ev.Preflight = preflight
	if preflightErr != nil {
		return ev, preflightErr
	}

	order, orderErr := profile.WorkOrder()
	if orderErr != nil {
		return ev, orderErr
	}
	ev.WorkOrderTitle = order.Title
	workOrderYAML, marshalErr := yaml.Marshal(order)
	if marshalErr != nil {
		return ev, marshalErr
	}
	ev.ProfileWorkOrderPath = filepath.Join(evidenceRoot, profile.ProfileName+"-workorder.yaml")
	if writeErr := os.WriteFile(ev.ProfileWorkOrderPath, workOrderYAML, 0o600); writeErr != nil {
		return ev, writeErr
	}
	if loadErr := p.Store.Load(workOrderYAML); loadErr != nil {
		return ev, fmt.Errorf("PROFILE_WORKER_PROOF_LOAD_FAILED: %w", loadErr)
	}
	reserved, reserveErr := p.reserveProfileReplayAttempt(order.ID)
	if reserveErr != nil {
		return ev, reserveErr
	}
	ev.ReservedAttempt = reserved
	if authErr := p.Authorize(order.ID); authErr != nil {
		return ev, authErr
	}
	if readyErr := p.Ready(order.ID); readyErr != nil {
		return ev, readyErr
	}

	var job Job
	for attempt := 0; attempt < p.retryBaseBudget(); attempt++ {
		if attempt == 0 {
			if dispatchErr := p.Dispatch(order.ID); dispatchErr != nil {
				return ev, dispatchErr
			}
		} else {
			if retryErr := p.Retry(order.ID); retryErr != nil {
				return ev, retryErr
			}
		}
		waitCtx, cancel := context.WithTimeout(ctx, p.attemptTimeout()+2*time.Minute)
		j, waitErr := p.Wait(waitCtx, order.ID)
		cancel()
		if waitErr != nil {
			return ev, waitErr
		}
		job = j
		if job.State != "REJECTED_RETRYABLE" {
			break
		}
	}

	ev.FinalState = job.State
	ev.Reason = job.Reason
	ev.Attempt = job.Attempt
	ev.Workspace = job.Workspace
	ev.AcceptanceEvidence = job.Evidence
	ev.CandidateDiffPath = filepath.Join(job.Evidence, "candidate.diff")
	ev.WorkerLaunched = job.Attempt > 0 && job.Workspace != ""
	ev.CandidateAccepted = job.State == "ACCEPTED"

	if checks, checksErr := p.Checks(order.ID); checksErr == nil {
		ev.Checks = checks
		ev.FocusedTestPassed = profileReplayCheckPassed(checks, "FOCUSED_TEST_FAILED")
		ev.GoAllPassed = profileReplayCheckPassed(checks, "GO_TEST_FAILED")
		ev.AcceptanceInputUnchanged = profileReplayCheckPassed(checks, "ACCEPTANCE_INPUT_MUTATED")
		ev.AcceptedRefCheckPassed = profileReplayCheckPassed(checks, "ACCEPTED_REF_MUTATION_DETECTED")
	}
	if files, filesErr := readProfileReplayChangedFiles(filepath.Join(job.Evidence, "changed_files.txt")); filesErr == nil {
		ev.ChangedFiles = files
	}
	if workerExit, workerExitErr := readProfileReplayJSONMap(filepath.Join(job.Evidence, "worker_exit.json")); workerExitErr == nil {
		ev.WorkerExit = workerExit
	}
	if postScrub, scrubErr := scrubCodexProfile(profile.CodexProfilePath, profileScrubDenylist(profile.ScrubDenylist)); scrubErr == nil {
		ev.PostWorkerScrub = postScrub
	} else {
		return ev, scrubErr
	}
	if after, afterErr := p.profileWorkspaceRepoState(ctx, profile.RepoPath); afterErr == nil {
		ev.RepoAfter = after
	} else {
		return ev, afterErr
	}

	ev.SourceStatusUnchanged = ev.RepoBefore.Status == ev.RepoAfter.Status
	ev.SourceHeadUnchanged = ev.RepoBefore.Head == ev.RepoAfter.Head
	ev.SourceBranchUnchanged = ev.RepoBefore.Branch == ev.RepoAfter.Branch
	ev.AcceptedRefsUnchanged = ev.RepoBefore.AcceptedRefs == ev.RepoAfter.AcceptedRefs
	ev.BranchRefsUnchanged = ev.RepoBefore.BranchRefs == ev.RepoAfter.BranchRefs
	ev.WorkspaceInsidePlane = pathIsWithinOrEqual(p.Root, job.Workspace)
	ev.WorkspaceInsideSourceRepo = pathIsWithinOrEqual(profile.RepoPath, job.Workspace)
	ev.SourceRepoInsideWorkspace = pathIsWithinOrEqual(job.Workspace, profile.RepoPath)
	ev.DiffTouchesOnlyAllowlist = sameStringSet(ev.ChangedFiles, []string{r4aDocPath, r4aTestPath})
	ev.RequiredFilesPresent = fileExists(filepath.Join(job.Evidence, "candidate_files", filepath.FromSlash(r4aDocPath))) && fileExists(filepath.Join(job.Evidence, "candidate_files", filepath.FromSlash(r4aTestPath)))
	ev.MarkerContentPresent = fileContains(filepath.Join(job.Evidence, "candidate_files", filepath.FromSlash(r4aDocPath)), r4aWorkOrderID) && fileContains(filepath.Join(job.Evidence, "candidate_files", filepath.FromSlash(r4aTestPath)), r4aFocusedTest)
	if !ev.FocusedTestPassed {
		ev.FocusedTestPassed = profileReplayTestPassed(filepath.Join(job.Evidence, "go-focused-0.jsonl"), r4aFocusedTest)
	}
	ev.GoAllConfigured = order.Acceptance.All
	if !order.Acceptance.All {
		ev.GoAllPassed = false
	}

	if job.State != "ACCEPTED" {
		return ev, fmt.Errorf("R4A_WORKER_PROOF_NOT_ACCEPTED: %s: %s", job.State, job.Reason)
	}
	if !ev.DiffTouchesOnlyAllowlist {
		return ev, fmt.Errorf("R4A_DIFF_SCOPE_FAILED: changed_files=%v", ev.ChangedFiles)
	}
	if !ev.RequiredFilesPresent || !ev.MarkerContentPresent {
		return ev, errors.New("R4A_MARKER_CONTENT_FAILED")
	}
	if !ev.FocusedTestPassed {
		return ev, errors.New("R4A_FOCUSED_TEST_EVIDENCE_FAILED")
	}
	if order.Acceptance.All && !ev.GoAllPassed {
		return ev, errors.New("R4A_GO_ALL_EVIDENCE_FAILED")
	}
	if !ev.AcceptanceInputUnchanged || !ev.AcceptedRefCheckPassed {
		return ev, errors.New("R4A_ACCEPTANCE_INVARIANT_FAILED")
	}
	if !ev.SourceStatusUnchanged || !ev.SourceHeadUnchanged || !ev.SourceBranchUnchanged || !ev.AcceptedRefsUnchanged || !ev.BranchRefsUnchanged {
		return ev, errors.New("R4A_SOURCE_REPO_MUTATION_DETECTED")
	}
	if !ev.WorkspaceInsidePlane || ev.WorkspaceInsideSourceRepo || ev.SourceRepoInsideWorkspace {
		return ev, errors.New("R4A_WORKSPACE_ISOLATION_FAILED")
	}
	if ev.RuntimeLaunched || ev.DeploymentRan || ev.AcceptedRefPromotionRan {
		return ev, errors.New("R4A_FORBIDDEN_RUNTIME_DEPLOY_OR_PROMOTION")
	}
	ev.Status = "ACCEPTED"
	return ev, nil
}

func sameStringSet(a, b []string) bool {
	aa := append([]string{}, a...)
	bb := append([]string{}, b...)
	for i := range aa {
		aa[i] = filepath.ToSlash(strings.TrimSpace(aa[i]))
	}
	for i := range bb {
		bb[i] = filepath.ToSlash(strings.TrimSpace(bb[i]))
	}
	sort.Strings(aa)
	sort.Strings(bb)
	if len(aa) != len(bb) {
		return false
	}
	for i := range aa {
		if aa[i] != bb[i] {
			return false
		}
	}
	return true
}

func fileExists(path string) bool {
	info, err := os.Lstat(path)
	return err == nil && info.Mode().IsRegular()
}

func fileContains(path, needle string) bool {
	b, err := os.ReadFile(path)
	return err == nil && strings.Contains(string(b), needle)
}

func readR4aJSONMap(path string) (map[string]any, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(b, &out); err != nil {
		return nil, err
	}
	return out, nil
}
