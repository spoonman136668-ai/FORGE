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
)

type recoveryCandidatePreflight struct {
	Transaction BlockerRecoveryTransaction
	Plan        RecoveryPlan
	Snapshot    RecoveryEvidenceSnapshot
	Order       WorkOrder
	OrderYAML   []byte
	SourceRepo  Repo
}

func (p *Engine) PrepareRecoveryCandidate(ctx context.Context, cfg RecoveryRepairConfig, recoveryID string) (RecoveryCandidateResult, error) {
	if err := validateRecoveryRepairConfig(cfg); err != nil {
		return RecoveryCandidateResult{}, err
	}
	preflight, err := p.recoveryCandidatePreflight(ctx, recoveryID)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	referenceContext, err := p.contextFor(preflight.Order)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	planJSON, _ := json.Marshal(preflight.Plan)
	trustedContext := referenceContext +
		"\nRECOVERY CANDIDATE CONTRACT (trusted controller data):\n" +
		string(planJSON) +
		"\nThis is a recovery candidate only. Stay inside the immutable work-order scope. Do not change baseline, authority, policy, accepted refs, credentials, runtime, deployment, or promotion. Do not claim acceptance or resume.\n"
	feedbackParts := []string{}
	if preflight.Snapshot.WorkerDiagnosticExcerpt != "" {
		feedbackParts = append(feedbackParts, "WORKER DIAGNOSTIC:\n"+preflight.Snapshot.WorkerDiagnosticExcerpt)
	}
	if preflight.Snapshot.ControllerDiagnostic != "" {
		feedbackParts = append(feedbackParts, "DETERMINISTIC VALIDATION:\n"+preflight.Snapshot.ControllerDiagnostic)
	}
	feedback := strings.Join(feedbackParts, "\n\n")
	if feedback == "" {
		feedback = preflight.Snapshot.OriginalBlocker
	}
	feedback = truncateRetryFeedbackUTF8(feedback, 64<<10, true)
	runner := p.runner
	if runner == nil {
		runner = SupervisedRunner{}
	}
	worker := CodexAdapter{
		Tool:     p.Config.Tools.Codex,
		Home:     p.Config.Execution.CodexHome,
		Runner:   runner,
		Context:  trustedContext,
		Feedback: feedback,
	}
	return p.prepareRecoveryCandidateWithWorker(ctx, cfg, preflight, worker)
}

func (p *Engine) recoveryCandidatePreflight(ctx context.Context, recoveryID string) (recoveryCandidatePreflight, error) {
	var out recoveryCandidatePreflight
	if !hexDigest(recoveryID, 64) {
		return out, errors.New("RECOVERY_ID_INVALID")
	}
	txState, err := getBlockerRecoveryTransaction(p.Store.DB, recoveryID)
	if err != nil {
		return out, err
	}
	if txState.State != blockerRecoveryDiagnosing || txState.Observation == nil || txState.Observation.AuthorityRequired {
		return out, errors.New("RECOVERY_REPAIR_STATE_INVALID")
	}
	plan, err := loadPersistedRecoveryPlan(p.Store.DB, recoveryID)
	if err != nil {
		return out, err
	}
	expectedPlan, err := PlanRecovery(txState)
	if err != nil {
		return out, err
	}
	if plan.PlanID != expectedPlan.PlanID || plan.RecoveryID != recoveryID {
		return out, errors.New("RECOVERY_PLAN_IDENTITY_CONFLICT")
	}
	if plan.Disposition != "SOURCE_REPAIR_CANDIDATE" || plan.RepairDomain != "APPLICATION_SOURCE" ||
		plan.RequiresAuthorityChange || plan.OuterQualificationRequired || plan.AutomaticMutation {
		return out, errors.New("RECOVERY_REPAIR_DOMAIN_NOT_SUPPORTED")
	}

	currentSnapshot, err := p.BuildRecoveryEvidenceSnapshot(txState.WorkOrderID)
	if err != nil {
		return out, err
	}
	currentID, err := recoveryIDForEvidence(currentSnapshot)
	if err != nil {
		return out, err
	}
	if currentID != recoveryID {
		return out, errors.New("RECOVERY_SOURCE_EVIDENCE_CHANGED")
	}
	if currentSnapshot.AuthorityGeneration != txState.Snapshot.AuthorityGeneration {
		return out, errors.New("RECOVERY_AUTHORITY_GENERATION_CHANGED")
	}
	if err = p.sourceAuthority(ctx); err != nil {
		return out, err
	}
	if p.Config.Policy.AcceptedRefMutation || p.Config.Policy.RuntimeLaunchAllowed || p.Config.Policy.ArbitraryShell {
		return out, errors.New("RECOVERY_POLICY_REJECTED")
	}

	var leases, liveProcesses int
	if err = p.Store.DB.QueryRow(
		"SELECT count(*) FROM worker_leases WHERE work_order_id=?",
		txState.WorkOrderID,
	).Scan(&leases); err != nil {
		return out, err
	}
	if err = p.Store.DB.QueryRow(
		"SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0",
		txState.WorkOrderID,
	).Scan(&liveProcesses); err != nil {
		return out, err
	}
	if leases != 0 || liveProcesses != 0 {
		return out, errors.New("RECOVERY_ORIGINAL_ATTEMPT_STILL_OWNED")
	}

	var native []byte
	if err = p.Store.DB.QueryRow(
		"SELECT yaml FROM work_orders WHERE id=?",
		txState.WorkOrderID,
	).Scan(&native); err != nil {
		return out, err
	}
	if digest(native) != txState.Snapshot.WorkOrderSHA256 {
		return out, errors.New("RECOVERY_WORK_ORDER_BYTES_CHANGED")
	}
	order, err := ParseOrder(native)
	if err != nil {
		return out, err
	}
	if order.ID != txState.WorkOrderID ||
		order.Baseline.Ref != txState.Snapshot.BaselineRef ||
		order.Baseline.SHA != txState.Snapshot.BaselineSHA {
		return out, errors.New("RECOVERY_WORK_ORDER_IDENTITY_CHANGED")
	}
	if err = p.verifyContract(order); err != nil {
		return out, errors.New("RECOVERY_AUTHORIZATION_CONTRACT_CHANGED")
	}

	sourceRepo, ok := p.Config.Repos[order.Repo]
	if !ok {
		return out, errors.New("RECOVERY_SOURCE_REPO_UNAVAILABLE")
	}
	if err = checkRepo(p.Config.Tools.Git, sourceRepo, order); err != nil {
		return out, err
	}

	out.Transaction = txState
	out.Plan = plan
	out.Snapshot = currentSnapshot
	out.Order = order
	out.OrderYAML = native
	out.SourceRepo = sourceRepo
	return out, nil
}

func (p *Engine) prepareRecoveryCandidateWithWorker(ctx context.Context, cfg RecoveryRepairConfig, preflight recoveryCandidatePreflight, worker Worker) (RecoveryCandidateResult, error) {
	if err := validateRecoveryRepairConfig(cfg); err != nil {
		return RecoveryCandidateResult{}, err
	}
	if worker == nil || worker.Name() != "codex" && worker.Name() != "fake" {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_WORKER_INVALID")
	}
	if err := initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		return RecoveryCandidateResult{}, err
	}

	workspaceID := preflight.Transaction.RecoveryID[:24]
	workspaceBase := filepath.Join(p.Root, "workspaces", "r", workspaceID)
	evidenceBase := filepath.Join(p.Root, "evidence", "recovery", preflight.Transaction.RecoveryID)
	if err := bridgeContained(p.Root, workspaceBase); err != nil {
		return RecoveryCandidateResult{}, err
	}
	if err := bridgeContained(p.Root, evidenceBase); err != nil {
		return RecoveryCandidateResult{}, err
	}
	claim, err := claimRecoveryCandidate(
		p.Store.DB,
		preflight.Transaction.RecoveryID,
		preflight.Plan.PlanID,
		workspaceBase,
		evidenceBase,
		cfg.MaxRepairAttempts,
	)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if err = bridgeContained(p.Root, claim.WorkspaceRoot); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = bridgeContained(p.Root, claim.Evidence); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if _, err = os.Lstat(claim.WorkspaceRoot); !os.IsNotExist(err) {
		if err == nil {
			err = errors.New("RECOVERY_WORKSPACE_COLLISION")
		}
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if _, err = os.Lstat(claim.Evidence); !os.IsNotExist(err) {
		if err == nil {
			err = errors.New("RECOVERY_EVIDENCE_COLLISION")
		}
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = os.MkdirAll(claim.Evidence, 0700); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	if err = writeJSON(filepath.Join(claim.Evidence, "recovery_transaction.json"), preflight.Transaction); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "recovery_plan.json"), preflight.Plan); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "recovery_snapshot.json"), preflight.Snapshot); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = os.WriteFile(filepath.Join(claim.Evidence, "work_order.yaml"), preflight.OrderYAML, 0600); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	sourceBefore, err := p.profileWorkspaceRepoState(ctx, preflight.SourceRepo.LocalPath)
	if err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "source_repo_before.json"), sourceBefore); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	materializeCtx, materializeCancel := context.WithTimeout(ctx, 2*time.Minute)
	worktree, before, materializeErr := prepareWorkspace(
		materializeCtx,
		p.Config.Tools.Git,
		preflight.SourceRepo.LocalPath,
		claim.WorkspaceRoot,
		preflight.Order,
	)
	materializeCancel()
	if materializeErr != nil {
		_ = writeJSON(filepath.Join(claim.Evidence, "materialization_error.json"), map[string]any{
			"error": materializeErr.Error(),
			"production_accepted": false,
			"resume_authorized": false,
		})
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", materializeErr)
	}
	claim.Worktree = worktree
	if err = writeJSON(filepath.Join(claim.Evidence, "repo_state_before.json"), before); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	stdout, err := os.OpenFile(filepath.Join(claim.Evidence, "worker_stdout.log"), os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0600)
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	stderr, err := os.OpenFile(filepath.Join(claim.Evidence, "worker_stderr.log"), os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0600)
	if err != nil {
		stdout.Close()
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	runCtx, cancel := context.WithTimeout(ctx, time.Duration(cfg.TimeoutSeconds)*time.Second)
	workerErr := worker.Run(runCtx, worktree, preflight.Order, stdout, stderr)
	cancel()
	stdout.Close()
	stderr.Close()
	claim.WorkerExitCode = exitCode(workerErr)
	if err = writeJSON(filepath.Join(claim.Evidence, "worker_exit.json"), map[string]any{
		"exit_code": claim.WorkerExitCode,
		"error": errorText(workerErr),
		"finished": now(),
		"production_accepted": false,
		"resume_authorized": false,
	}); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	changedFiles, err := changed(p.Config.Tools.Git, worktree, preflight.Order.Baseline.SHA)
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	sort.Strings(changedFiles)
	claim.ChangedFiles = append([]string(nil), changedFiles...)
	if err = os.WriteFile(
		filepath.Join(claim.Evidence, "changed_files.txt"),
		[]byte(strings.Join(changedFiles, "\n")+"\n"),
		0600,
	); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	after, err := p.recoveryRepoState(preflight.SourceRepo.LocalPath, worktree, preflight.Order.Baseline.SHA)
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "repo_state_after.json"), after); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if after.SourceRefs != before.SourceRefs || after.AttemptRefs != before.AttemptRefs {
		return p.finishAndSealRecoveryCandidate(claim, "REF_MUTATION", errors.New("RECOVERY_ACCEPTED_REF_MUTATION_DETECTED"))
	}
	sourceAfter, err := p.profileWorkspaceRepoState(ctx, preflight.SourceRepo.LocalPath)
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "source_repo_after.json"), sourceAfter); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if jsonText(sourceBefore) != jsonText(sourceAfter) {
		return p.finishAndSealRecoveryCandidate(claim, "REF_MUTATION", errors.New("RECOVERY_SOURCE_REPO_MUTATED"))
	}

	for _, name := range changedFiles {
		if !preflight.Order.Allows(name) {
			return p.finishAndSealRecoveryCandidate(claim, "FORBIDDEN_PATH", fmt.Errorf("RECOVERY_FORBIDDEN_PATH: %s", name))
		}
	}
	diff, err := git(p.Config.Tools.Git, worktree, "diff", "--binary", "--no-ext-diff", "--no-textconv", preflight.Order.Baseline.SHA, "--")
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = os.WriteFile(filepath.Join(claim.Evidence, "candidate.diff"), []byte(diff), 0600); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	claim.CandidateDiffSHA256 = digest([]byte(diff))
	inventory, err := recoveryCandidateInventory(worktree, changedFiles)
	if err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "candidate_inventory.json"), inventory); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeRecoveryCandidateFiles(worktree, claim.Evidence, inventory); err != nil {
		return p.finishAndSealRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}

	status := "CANDIDATE_PREPARED"
	if workerErr != nil {
		status = "WORKER_FAILED"
	} else if len(changedFiles) == 0 {
		status = "NO_DIFF"
	}
	return p.finishAndSealRecoveryCandidate(claim, status, workerErr)
}

func (p *Engine) recoveryRepoState(source, worktree, baselineSHA string) (RepoState, error) {
	out := RepoState{Baseline: baselineSHA}
	var err error
	out.SourceRefs, err = refs(p.Config.Tools.Git, source)
	if err != nil {
		return out, err
	}
	out.AttemptRefs, err = refs(p.Config.Tools.Git, worktree)
	if err != nil {
		return out, err
	}
	out.Head, err = git(p.Config.Tools.Git, worktree, "rev-parse", "HEAD")
	if err != nil {
		return out, err
	}
	out.Status, err = git(p.Config.Tools.Git, worktree, "status", "--porcelain")
	return out, err
}

func recoveryCandidateInventory(worktree string, changedFiles []string) ([]RecoveryCandidateEntry, error) {
	out := make([]RecoveryCandidateEntry, 0, len(changedFiles))
	for _, name := range changedFiles {
		if !safePath(name) {
			return nil, errors.New("RECOVERY_CHANGED_PATH_INVALID")
		}
		path := filepath.Join(worktree, filepath.FromSlash(name))
		info, err := os.Lstat(path)
		if os.IsNotExist(err) {
			out = append(out, RecoveryCandidateEntry{Path: name, Deleted: true})
			continue
		}
		if err != nil {
			return nil, err
		}
		if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
			return nil, errors.New("RECOVERY_CANDIDATE_FILE_INVALID")
		}
		if info.Size() > 4<<20 {
			return nil, errors.New("RECOVERY_CANDIDATE_FILE_TOO_LARGE")
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		out = append(out, RecoveryCandidateEntry{Path: name, SHA256: digest(raw)})
	}
	return out, nil
}

func writeRecoveryCandidateFiles(worktree, evidence string, entries []RecoveryCandidateEntry) error {
	root := filepath.Join(evidence, "candidate_files")
	for _, entry := range entries {
		if entry.Deleted {
			continue
		}
		if !safePath(entry.Path) || !hexDigest(entry.SHA256, 64) {
			return errors.New("RECOVERY_CANDIDATE_ENTRY_INVALID")
		}
		src := filepath.Join(worktree, filepath.FromSlash(entry.Path))
		info, err := os.Lstat(src)
		if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
			return errors.New("RECOVERY_CANDIDATE_FILE_INVALID")
		}
		raw, err := os.ReadFile(src)
		if err != nil {
			return err
		}
		if digest(raw) != entry.SHA256 {
			return errors.New("RECOVERY_CANDIDATE_HASH_MISMATCH")
		}
		dst := filepath.Join(root, filepath.FromSlash(entry.Path))
		if err = os.MkdirAll(filepath.Dir(dst), 0700); err != nil {
			return err
		}
		f, err := os.OpenFile(dst, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			return err
		}
		if _, err = f.Write(raw); err != nil {
			f.Close()
			return err
		}
		if err = f.Close(); err != nil {
			return err
		}
	}
	return nil
}

func (p *Engine) failRecoveryCandidate(claim RecoveryCandidateResult, status string, cause error) (RecoveryCandidateResult, error) {
	out, err := finishRecoveryCandidate(p.Store.DB, func() RecoveryCandidateResult {
		claim.Status = status
		claim.ProductionAccepted = false
		claim.ResumeAuthorized = false
		return claim
	}())
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if cause != nil {
		return out, cause
	}
	return out, errors.New(status)
}

func (p *Engine) finishAndSealRecoveryCandidate(claim RecoveryCandidateResult, status string, cause error) (RecoveryCandidateResult, error) {
	claim.Status = status
	claim.ProductionAccepted = false
	claim.ResumeAuthorized = false
	// The on-disk result is part of the evidence manifest, so it deliberately
	// does not contain the manifest's own digest. The SQLite row is the external
	// anchor and gains EvidenceManifestSHA256 only after the packet is sealed.
	claim.EvidenceManifestSHA256 = ""
	if err := writeJSON(filepath.Join(claim.Evidence, "candidate_result.json"), claim); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	manifest, err := Manifest(claim.Evidence)
	if err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	if err = writeJSON(filepath.Join(claim.Evidence, "evidence_manifest.json"), manifest); err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(claim.Evidence, "evidence_manifest.json"))
	if err != nil {
		return p.failRecoveryCandidate(claim, "EVIDENCE_FAILED", err)
	}
	claim.EvidenceManifestSHA256 = digest(manifestRaw)
	final, finishErr := finishRecoveryCandidate(p.Store.DB, claim)
	if finishErr != nil {
		return RecoveryCandidateResult{}, finishErr
	}
	if cause != nil {
		return final, cause
	}
	if status != "CANDIDATE_PREPARED" {
		return final, errors.New(status)
	}
	return final, nil
}

func errorText(err error) string {
	if err == nil {
		return ""
	}
	text := err.Error()
	if len(text) > 4096 {
		text = text[len(text)-4096:]
	}
	return text
}
