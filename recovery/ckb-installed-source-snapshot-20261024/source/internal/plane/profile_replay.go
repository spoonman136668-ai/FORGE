package plane

import (
	"bufio"
	"bytes"
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

type ProfileReplayEvidence struct {
	ProfileName                   string                   `json:"profile_name"`
	Mode                          string                   `json:"mode"`
	ProfileWorkOrderID            string                   `json:"profile_work_order_id"`
	WorkOrderID                   string                   `json:"work_order_id"`
	WorkOrderTitle                string                   `json:"work_order_title"`
	Preflight                     ProfilePreflightEvidence `json:"preflight"`
	PostReplayScrub               ProfileScrubEvidence     `json:"post_replay_scrub"`
	ReplayEvidencePath            string                   `json:"replay_evidence_path"`
	ProfileWorkOrderPath          string                   `json:"profile_work_order_path"`
	FinalState                    string                   `json:"final_state"`
	Reason                        string                   `json:"reason"`
	Attempt                       int                      `json:"attempt"`
	ReservedAttempt               int                      `json:"reserved_attempt"`
	Workspace                     string                   `json:"workspace"`
	Evidence                      string                   `json:"evidence"`
	CandidateDiffPath             string                   `json:"candidate_diff_path"`
	ChangedFiles                  []string                 `json:"changed_files"`
	Checks                        []Check                  `json:"checks"`
	WorkerExit                    map[string]any           `json:"worker_exit,omitempty"`
	SourceAcceptedRefsBefore      string                   `json:"source_accepted_refs_before"`
	SourceAcceptedRefsAfter       string                   `json:"source_accepted_refs_after"`
	AcceptedRefsUnchanged         bool                     `json:"accepted_refs_unchanged"`
	CandidateDiffOnlyToyGo        bool                     `json:"candidate_diff_only_toy_go"`
	CandidateDiffBeforeAfter      bool                     `json:"candidate_diff_before_after"`
	FocusedTestMessagePass        bool                     `json:"focused_test_message_pass"`
	AllTestMessagePass            bool                     `json:"all_test_message_pass"`
	AcceptanceInputUnchanged      bool                     `json:"acceptance_input_unchanged"`
	AcceptedRefCheckPassed        bool                     `json:"accepted_ref_check_passed"`
	CodexDenylistCleanAfterReplay bool                     `json:"codex_denylist_clean_after_replay"`
	Status                        string                   `json:"status"`
	Created                       string                   `json:"created"`
}

func (p *Engine) ReplaySelectedProfile(ctx context.Context, evidenceRoot string) (ev ProfileReplayEvidence, err error) {
	if e := p.guardLegacyExecution(); e != nil {
		return ev, e
	}
	ev.Created = time.Now().UTC().Format(time.RFC3339Nano)
	ev.Status = "BLOCKED"
	if evidenceRoot == "" {
		evidenceRoot = filepath.Join(p.Root, "artifacts", "r2f")
	}
	if mkdirErr := os.MkdirAll(evidenceRoot, 0o700); mkdirErr != nil {
		return ev, mkdirErr
	}
	defer func() {
		if ev.ProfileName == "" {
			ev.ProfileName = "unknown"
		}
		if ev.ReplayEvidencePath == "" {
			ev.ReplayEvidencePath = filepath.Join(evidenceRoot, ev.ProfileName+"-profile-replay.json")
		}
		if err != nil && ev.Reason == "" {
			ev.Reason = err.Error()
		}
		_ = writeJSON(ev.ReplayEvidencePath, ev)
	}()

	if p.Profile == nil {
		return ev, errors.New("PROFILE_REQUIRED: no dispatch profile selected")
	}
	profile := *p.Profile
	ev.ProfileName = profile.ProfileName
	ev.Mode = profile.Mode
	ev.ProfileWorkOrderID = profile.WorkOrderID
	ev.ReplayEvidencePath = filepath.Join(evidenceRoot, profile.ProfileName+"-profile-replay.json")

	// R2f intentionally proves only the disposable toy path. CKB profiles remain
	// preflight-only until a later explicitly authorized read-only dry dispatch.
	if profile.ProfileName != "toy" || profile.Mode != "toy-proof-profile" {
		return ev, errors.New("PROFILE_REPLAY_FORBIDDEN: R2f replay is toy-only")
	}
	if !profile.WorkerLaunchAllowed || !profile.CandidateAcceptanceAllowed {
		return ev, errors.New("PROFILE_REPLAY_FORBIDDEN: selected profile cannot launch worker and accept candidate")
	}

	preflight, preflightErr := p.PreflightDispatchProfile(ctx, profile, evidenceRoot)
	ev.Preflight = preflight
	if preflightErr != nil {
		return ev, preflightErr
	}

	order, orderErr := profile.WorkOrder()
	if orderErr != nil {
		return ev, orderErr
	}
	ev.WorkOrderID = order.ID
	ev.WorkOrderTitle = order.Title
	beforeRefs, refsErr := refs(p.Config.Tools.Git, profile.RepoPath)
	if refsErr != nil {
		return ev, refsErr
	}
	ev.SourceAcceptedRefsBefore = beforeRefs

	workOrderYAML, marshalErr := yaml.Marshal(order)
	if marshalErr != nil {
		return ev, marshalErr
	}
	ev.ProfileWorkOrderPath = filepath.Join(evidenceRoot, profile.ProfileName+"-profile-workorder.yaml")
	if writeErr := os.WriteFile(ev.ProfileWorkOrderPath, workOrderYAML, 0o600); writeErr != nil {
		return ev, writeErr
	}
	if loadErr := p.Store.Load(workOrderYAML); loadErr != nil {
		return ev, fmt.Errorf("PROFILE_REPLAY_LOAD_FAILED: %w", loadErr)
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
	if dispatchErr := p.Dispatch(order.ID); dispatchErr != nil {
		return ev, dispatchErr
	}

	waitCtx, cancel := context.WithTimeout(ctx, p.attemptTimeout()+2*time.Minute)
	defer cancel()
	job, waitErr := p.Wait(waitCtx, order.ID)
	if waitErr != nil {
		return ev, waitErr
	}
	ev.FinalState = job.State
	ev.Reason = job.Reason
	ev.Attempt = job.Attempt
	ev.Workspace = job.Workspace
	ev.Evidence = job.Evidence
	ev.CandidateDiffPath = filepath.Join(job.Evidence, "candidate.diff")

	postScrub, postScrubErr := scrubCodexProfile(profile.CodexProfilePath, profileScrubDenylist(profile.ScrubDenylist))
	ev.PostReplayScrub = postScrub
	ev.CodexDenylistCleanAfterReplay = postScrubErr == nil && len(postScrub.PresentAfter) == 0
	if postScrubErr != nil {
		return ev, postScrubErr
	}

	if checks, checksErr := p.Checks(order.ID); checksErr == nil {
		ev.Checks = checks
		ev.AcceptanceInputUnchanged = profileReplayCheckPassed(checks, "ACCEPTANCE_INPUT_MUTATED")
		ev.AcceptedRefCheckPassed = profileReplayCheckPassed(checks, "ACCEPTED_REF_MUTATION_DETECTED")
	}
	if files, filesErr := readProfileReplayChangedFiles(filepath.Join(job.Evidence, "changed_files.txt")); filesErr == nil {
		ev.ChangedFiles = files
	}
	if workerExit, workerExitErr := readProfileReplayJSONMap(filepath.Join(job.Evidence, "worker_exit.json")); workerExitErr == nil {
		ev.WorkerExit = workerExit
	}
	afterRefs, afterRefsErr := refs(p.Config.Tools.Git, profile.RepoPath)
	if afterRefsErr != nil {
		return ev, afterRefsErr
	}
	ev.SourceAcceptedRefsAfter = afterRefs
	ev.AcceptedRefsUnchanged = ev.SourceAcceptedRefsBefore == ev.SourceAcceptedRefsAfter
	ev.CandidateDiffOnlyToyGo = len(ev.ChangedFiles) == 1 && ev.ChangedFiles[0] == "toy.go"
	ev.CandidateDiffBeforeAfter = profileReplayDiffShowsBeforeAfter(ev.CandidateDiffPath)
	ev.FocusedTestMessagePass = profileReplayTestPassed(filepath.Join(job.Evidence, "go-focused-0.jsonl"), "TestMessage")
	ev.AllTestMessagePass = profileReplayTestPassed(filepath.Join(job.Evidence, "go-all.jsonl"), "TestMessage")

	if job.State != "ACCEPTED" {
		return ev, fmt.Errorf("PROFILE_REPLAY_NOT_ACCEPTED: %s: %s", job.State, job.Reason)
	}
	if !ev.CandidateDiffOnlyToyGo {
		return ev, fmt.Errorf("R2F_TOY_DIFF_SCOPE_FAILED: changed_files=%v", ev.ChangedFiles)
	}
	if !ev.CandidateDiffBeforeAfter {
		return ev, errors.New("R2F_TOY_DIFF_CONTENT_FAILED: candidate.diff does not show before->after toy change")
	}
	if !ev.FocusedTestMessagePass || !ev.AllTestMessagePass {
		return ev, errors.New("R2F_TOY_TEST_EVIDENCE_FAILED: TestMessage pass missing from focused or all go test JSONL")
	}
	if !ev.AcceptanceInputUnchanged {
		return ev, errors.New("R2F_ACCEPTANCE_INPUT_MUTATED")
	}
	if !ev.AcceptedRefsUnchanged || !ev.AcceptedRefCheckPassed {
		return ev, errors.New("R2F_ACCEPTED_REF_MUTATION_DETECTED")
	}
	if !ev.CodexDenylistCleanAfterReplay {
		return ev, errors.New("R2F_CODEX_PROFILE_DENYLIST_RECREATED")
	}
	ev.Status = "ACCEPTED"
	return ev, nil
}

func (p *Engine) reserveProfileReplayAttempt(id string) (int, error) {
	maxAttempts := p.retryBaseBudget()
	if maxAttempts <= 0 {
		maxAttempts = 1
	}
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		workspace := filepath.Join(p.Root, "workspaces", id, fmt.Sprint(attempt))
		evidence := filepath.Join(p.Root, "evidence", id, fmt.Sprint(attempt))
		if pathExists(workspace) || pathExists(evidence) {
			continue
		}
		res, err := p.Store.DB.Exec("UPDATE work_orders SET attempt=? WHERE id=? AND state='DRAFT'", attempt-1, id)
		if err != nil {
			return 0, err
		}
		if rows, _ := res.RowsAffected(); rows != 1 {
			return 0, errors.New("PROFILE_REPLAY_ATTEMPT_RESERVATION_FAILED")
		}
		return attempt, nil
	}
	return 0, fmt.Errorf("PROFILE_REPLAY_ATTEMPT_PATHS_EXHAUSTED: no clean attempt path for %s within max_attempts=%d", id, maxAttempts)
}

func pathExists(path string) bool {
	_, err := os.Lstat(path)
	return err == nil || !os.IsNotExist(err)
}

func readProfileReplayChangedFiles(path string) ([]string, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	out := []string{}
	for _, line := range strings.Split(strings.ReplaceAll(string(b), "\r\n", "\n"), "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			out = append(out, filepath.ToSlash(line))
		}
	}
	sort.Strings(out)
	return out, nil
}

func readProfileReplayJSONMap(path string) (map[string]any, error) {
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

func profileReplayDiffShowsBeforeAfter(path string) bool {
	b, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	text := strings.ReplaceAll(string(b), "\t", "")
	return strings.Contains(text, "diff --git a/toy.go b/toy.go") && strings.Contains(text, "-return \"before\"") && strings.Contains(text, "+return \"after\"")
}

func profileReplayTestPassed(path, testName string) bool {
	b, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	scanner := bufio.NewScanner(bytes.NewReader(b))
	scanner.Buffer(make([]byte, 4096), 1<<20)
	for scanner.Scan() {
		var row struct {
			Action string `json:"Action"`
			Test   string `json:"Test"`
		}
		if json.Unmarshal(scanner.Bytes(), &row) == nil && row.Action == "pass" && row.Test == testName {
			return true
		}
	}
	return false
}

func profileReplayCheckPassed(checks []Check, name string) bool {
	for _, check := range checks {
		if check.Name == name {
			return check.Pass
		}
	}
	return false
}
