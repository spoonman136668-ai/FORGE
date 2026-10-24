package plane

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type shadowCodexRunner struct {
	fail  bool
	calls int
}

func (r *shadowCodexRunner) Run(ctx context.Context, spec ProcessSpec, out, stderr io.Writer) error {
	r.calls++
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}
	if r.fail {
		return errors.New("shadow fixture worker failure")
	}
	if err := os.WriteFile(
		filepath.Join(spec.Dir, "demo.txt"),
		[]byte("candidate produced by deterministic fake worker\n"),
		0600,
	); err != nil {
		return err
	}
	_, _ = io.WriteString(out, "shadow fixture candidate written\n")
	return nil
}

func TestBlockerRecoveryShadowDefaultOffIsInert(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if before.State != after.State || before.Attempt != after.Attempt || before.Reason != after.Reason {
		t.Fatalf("default-off shadow mutated work order: before=%+v after=%+v", before, after)
	}
	var tables int
	if err = p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='blocker_recovery_shadow_runs'",
	).Scan(&tables); err != nil {
		t.Fatal(err)
	}
	if tables != 0 {
		t.Fatal("default-off shadow created durable state")
	}
}

func TestBlockerRecoveryShadowValidatesWhilePlanePausedWithoutProductionMutation(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	runner := &shadowCodexRunner{}
	p.runner = runner
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}

	bw, bl, bq, bp, ba := recoveryValidationCounts(t, p)
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowCandidateReady || run.CandidateAttempt != 1 || runner.calls != 1 {
		t.Fatalf("after candidate: %+v calls=%d", run, runner.calls)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err = blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowValidated || run.ValidationAttempt != 1 || runner.calls != 1 {
		t.Fatalf("after validation: %+v calls=%d", run, runner.calls)
	}

	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if before.State != after.State || before.Attempt != after.Attempt || before.Reason != after.Reason {
		t.Fatalf("shadow changed blocked work order: before=%+v after=%+v", before, after)
	}
	if p.setting("paused") != "true" {
		t.Fatal("shadow unpaused plane")
	}
	aw, al, aq, ap, aa := recoveryValidationCounts(t, p)
	if bw != aw || bl != al || bq != aq || bp != ap || ba != aa {
		t.Fatalf("shadow mutated production tables: before=%d/%d/%d/%d/%d after=%d/%d/%d/%d/%d",
			bw, bl, bq, bp, ba, aw, al, aq, ap, aa)
	}
}

func TestBlockerRecoveryShadowRejectsWithoutOriginalRetry(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	runner := &shadowCodexRunner{fail: true}
	p.runner = runner
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowRejected || runner.calls != 1 {
		t.Fatalf("%+v calls=%d", run, runner.calls)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if runner.calls != 1 {
		t.Fatalf("terminal shadow relaunched worker: calls=%d", runner.calls)
	}

	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if after.Attempt != before.Attempt || after.State != before.State {
		t.Fatalf("shadow spent original attempt: before=%+v after=%+v", before, after)
	}
}

func TestBlockerRecoveryShadowInterruptedCandidateFailsClosed(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	txState, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PrepareRecoveryPlan(RecoveryPlannerConfig{Enabled: true}, p.Store.DB, txState.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	run, err := ensureBlockerRecoveryShadowRun(p.Store.DB, txState, plan)
	if err != nil {
		t.Fatal(err)
	}
	run, err = moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowPlanned, recoveryShadowCandidateRunning, 0, 0, "",
	)
	if err != nil {
		t.Fatal(err)
	}
	if err = initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	claim, err := claimRecoveryCandidate(
		p.Store.DB,
		txState.RecoveryID,
		plan.PlanID,
		filepath.Join(p.Root, "workspaces", "r", txState.RecoveryID[:24]),
		filepath.Join(p.Root, "evidence", "recovery", txState.RecoveryID),
		1,
	)
	if err != nil {
		t.Fatal(err)
	}
	if claim.Status != "RUNNING" {
		t.Fatal(claim)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err = getBlockerRecoveryShadowRun(p.Store.DB, txState.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowRejected || run.CandidateAttempt != 1 {
		t.Fatal(run)
	}
	candidate, err := p.RecoveryCandidate(txState.RecoveryID, 1)
	if err != nil {
		t.Fatal(err)
	}
	if candidate.Status != "EVIDENCE_FAILED" || candidate.ProductionAccepted || candidate.ResumeAuthorized {
		t.Fatal(candidate)
	}
}

func TestBlockerRecoveryShadowRejectsPhaseSkip(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	txState, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PrepareRecoveryPlan(RecoveryPlannerConfig{Enabled: true}, p.Store.DB, txState.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	run, err := ensureBlockerRecoveryShadowRun(p.Store.DB, txState, plan)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowPlanned, recoveryShadowValidated, 1, 1, "",
	); err == nil || err.Error() != "RECOVERY_SHADOW_TRANSITION_INVALID" {
		t.Fatal(err)
	}
}

func TestBlockerRecoveryShadowR11TerminalGoAllGateShape(t *testing.T) {
	p, w, _, evidence := recoverySnapshotEngineFixtureAttempt(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED", 3)

	checks := []Check{
		{Name: "PLANE_AUTHORITY_LOST", Pass: true},
		{Name: "BASELINE_MISMATCH", Pass: true},
		{Name: "BRANCH_ANCESTRY_INVALID", Pass: true},
		{Name: "WORKER_BRANCH_CHANGED", Pass: true},
		{Name: "ACCEPTED_REF_MUTATION_DETECTED", Pass: true},
		{Name: "REQUIRED_FILE_MISSING", Pass: true},
		{Name: "CANDIDATE_READ_FAILED", Pass: true},
		{Name: "NO_DIFF_PRODUCED", Pass: true},
		{Name: "FORBIDDEN_PATH_MODIFIED", Pass: true},
		{Name: "SOURCE_HYGIENE_FAILED", Pass: true},
		{Name: "WINDOWS_AUTHORITY_REQUIRED", Pass: true},
		{Name: "CANDIDATE_FREEZE_FAILED", Pass: true},
		{Name: "UI_BASELINE_EXPORT", Pass: true},
		{Name: "UI_BEHAVIOR_PARITY", Pass: true},
		{Name: "UI_ID_DATA_PARITY", Pass: true},
		{Name: "UI_CRITICAL_ID", Pass: true},
		{Name: "UI_CHART_ID", Pass: true},
		{Name: "UI_REQUIRED_MARKER", Pass: true},
		{Name: "POWERSHELL_ACCEPTANCE_FAILED", Pass: true},
		{Name: "FOCUSED_TEST_FAILED", Pass: true},
		{Name: "GO_TEST_FAILED", Pass: false, Detail: "Go test failed: process exit 1; see go-all.jsonl"},
		{Name: "ACCEPTANCE_INPUT_MUTATED", Pass: true},
		{Name: "ACCEPTED_REF_MUTATION_DETECTED", Pass: true},
	}
	if err := writeJSON(filepath.Join(evidence, "acceptance_checks.json"), checks); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(evidence, "evidence_manifest.json")); err != nil {
		t.Fatal(err)
	}
	manifest, err := Manifest(evidence)
	if err != nil {
		t.Fatal(err)
	}
	if err = writeJSON(filepath.Join(evidence, "evidence_manifest.json"), manifest); err != nil {
		t.Fatal(err)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(evidence, "evidence_manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"UPDATE evidence_seals SET manifest_sha256=? WHERE work_order_id=? AND attempt=?",
		digest(manifestRaw), w.ID, 3,
	); err != nil {
		t.Fatal(err)
	}

	snapshot, err := p.BuildRecoveryEvidenceSnapshot(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if snapshot.BlockedAttempt != 3 || len(snapshot.FailedChecks) != 1 || snapshot.FailedChecks[0] != "GO_TEST_FAILED" {
		t.Fatalf("unexpected R11-shaped snapshot: %+v", snapshot)
	}
	if !strings.Contains(snapshot.ControllerDiagnostic, "GO_TEST_FAILED deterministic output") ||
		!strings.Contains(snapshot.ControllerDiagnostic, "TestRecoveryRegression") {
		t.Fatalf("missing bounded go-all diagnostic: %q", snapshot.ControllerDiagnostic)
	}

	runner := &shadowCodexRunner{}
	p.runner = runner
	if err = p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowValidated || run.CandidateAttempt != 1 || run.ValidationAttempt != 1 || runner.calls != 1 {
		t.Fatalf("unexpected R11-shaped shadow outcome: run=%+v calls=%d", run, runner.calls)
	}

	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if before.State != after.State || before.Attempt != 3 || after.Attempt != 3 || before.Reason != after.Reason {
		t.Fatalf("R11-shaped shadow mutated original attempt: before=%+v after=%+v", before, after)
	}
	if p.setting("paused") != "true" {
		t.Fatal("R11-shaped shadow unpaused plane")
	}
}

func TestBlockerRecoveryShadowRevalidatesPriorHygieneOnlyRejectionWithoutSecondWorker(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	runner := &shadowCodexRunner{}
	p.runner = runner
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowCandidateReady || run.CandidateAttempt != 1 || runner.calls != 1 {
		t.Fatalf("expected one sealed candidate before synthetic prior rejection: run=%+v calls=%d", run, runner.calls)
	}
	candidate, err := p.RecoveryCandidate(run.RecoveryID, 1)
	if err != nil {
		t.Fatal(err)
	}
	seed := RecoveryValidationResult{
		RecoveryID:              run.RecoveryID,
		PlanID:                  run.PlanID,
		RepairAttempt:           1,
		WorkspaceRoot:           filepath.Join(p.Root, "workspaces", "v", run.RecoveryID[:24], "1"),
		Evidence:                filepath.Join(p.Root, "evidence", "recovery-validation", run.RecoveryID, "1"),
		CandidateManifestSHA256: candidate.EvidenceManifestSHA256,
		ProductionAccepted:      false,
		ResumeAuthorized:        false,
	}
	first, err := claimRecoveryValidationMode(p.Store.DB, seed, 2, false)
	if err != nil {
		t.Fatal(err)
	}
	first.Status = "REJECTED"
	first.FirstFailedCheck = "SOURCE_HYGIENE_FAILED"
	first, err = finishRecoveryValidation(p.Store.DB, first)
	if err != nil {
		t.Fatal(err)
	}
	running, err := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowCandidateReady, recoveryShadowValidationRunning,
		1, 0, "",
	)
	if err != nil {
		t.Fatal(err)
	}
	_, err = moveBlockerRecoveryShadowRun(
		p.Store.DB, running, recoveryShadowValidationRunning, recoveryShadowRejected,
		1, first.ValidationAttempt, "REJECTED: SOURCE_HYGIENE_FAILED",
	)
	if err != nil {
		t.Fatal(err)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err = blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowValidated || run.CandidateAttempt != 1 || run.ValidationAttempt != 2 || runner.calls != 1 {
		t.Fatalf("hygiene-only revalidation did not validate same sealed candidate: run=%+v calls=%d", run, runner.calls)
	}
	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if before.State != after.State || before.Attempt != after.Attempt || before.Reason != after.Reason {
		t.Fatalf("hygiene revalidation mutated original attempt: before=%+v after=%+v", before, after)
	}
	if p.setting("paused") != "true" {
		t.Fatal("hygiene revalidation unpaused plane")
	}
}

func TestBlockerRecoveryShadowThirdValidationAfterTwoHygieneOnlyRejectionsWithoutSecondWorker(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "RETRY_LIMIT_REACHED: GO_TEST_FAILED")
	runner := &shadowCodexRunner{}
	p.runner = runner
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeShadow); err != nil {
		t.Fatal(err)
	}
	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowCandidateReady || run.CandidateAttempt != 1 || runner.calls != 1 {
		t.Fatalf("expected one sealed candidate: run=%+v calls=%d", run, runner.calls)
	}
	candidate, err := p.RecoveryCandidate(run.RecoveryID, 1)
	if err != nil {
		t.Fatal(err)
	}
	seed := RecoveryValidationResult{
		RecoveryID:              run.RecoveryID,
		PlanID:                  run.PlanID,
		RepairAttempt:           1,
		WorkspaceRoot:           filepath.Join(p.Root, "workspaces", "v", run.RecoveryID[:24], "1"),
		Evidence:                filepath.Join(p.Root, "evidence", "recovery-validation", run.RecoveryID, "1"),
		CandidateManifestSHA256: candidate.EvidenceManifestSHA256,
		ProductionAccepted:      false,
		ResumeAuthorized:        false,
	}
	first, err := claimRecoveryValidationMode(p.Store.DB, seed, 3, false)
	if err != nil {
		t.Fatal(err)
	}
	first.Status = "REJECTED"
	first.FirstFailedCheck = "SOURCE_HYGIENE_FAILED"
	first, err = finishRecoveryValidation(p.Store.DB, first)
	if err != nil {
		t.Fatal(err)
	}
	second, err := claimRecoveryValidationMode(p.Store.DB, seed, 3, true)
	if err != nil {
		t.Fatal(err)
	}
	second.Status = "REJECTED"
	second.FirstFailedCheck = "SOURCE_HYGIENE_FAILED"
	second, err = finishRecoveryValidation(p.Store.DB, second)
	if err != nil {
		t.Fatal(err)
	}
	running, err := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowCandidateReady, recoveryShadowValidationRunning,
		1, 0, "",
	)
	if err != nil {
		t.Fatal(err)
	}
	_, err = moveBlockerRecoveryShadowRun(
		p.Store.DB, running, recoveryShadowValidationRunning, recoveryShadowRejected,
		1, second.ValidationAttempt, "REJECTED: SOURCE_HYGIENE_FAILED",
	)
	if err != nil {
		t.Fatal(err)
	}

	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	run, err = blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryShadowValidated || run.CandidateAttempt != 1 || run.ValidationAttempt != 3 || runner.calls != 1 {
		t.Fatalf("third validation did not validate same sealed candidate: run=%+v calls=%d", run, runner.calls)
	}
	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if before.State != after.State || before.Attempt != after.Attempt || before.Reason != after.Reason {
		t.Fatalf("third validation mutated original attempt: before=%+v after=%+v", before, after)
	}
	if p.setting("paused") != "true" {
		t.Fatal("third validation unpaused plane")
	}
}

func TestBlockerRecoveryActiveDeterministicInfrastructureQueuesBoundedRetry(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "REPO_UNAVAILABLE")
	testAuthority(p)
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeActive); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if after.State != "DRAFT" || after.Attempt != before.Attempt || after.Reason != "OPERATOR_RETRY_AUTHORIZED" {
		t.Fatalf("active retry did not stage bounded retry: before=%+v after=%+v", before, after)
	}
	var qState, auth, mode string
	if err = p.Store.DB.QueryRow("SELECT state,authorization,mode FROM queue_items WHERE id=?", w.ID).Scan(&qState, &auth, &mode); err != nil {
		t.Fatal(err)
	}
	if qState != "QUEUED" || auth != "operator" || mode != "source" {
		t.Fatalf("queue=%s auth=%s mode=%s", qState, auth, mode)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryActiveRetryQueued || run.LastError != "" {
		t.Fatalf("active recovery phase=%+v", run)
	}
	var leases int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases WHERE work_order_id=?", w.ID).Scan(&leases); err != nil {
		t.Fatal(err)
	}
	if leases != 0 {
		t.Fatalf("active retry dispatched in promotion tick: leases=%d", leases)
	}
	if p.Config.Policy.AcceptedRefMutation {
		t.Fatal("active recovery enabled accepted-ref mutation")
	}
}

func TestBlockerRecoveryActiveDoesNotOverrideRetryBudget(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixtureAttempt(t, "REPO_UNAVAILABLE", 3)
	testAuthority(p)
	p.Config.Policy.MaxAttempts = 3
	if err := p.setSetting(blockerResolverModeSetting, blockerResolverModeActive); err != nil {
		t.Fatal(err)
	}
	before, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	after, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if after.State != before.State || after.Attempt != before.Attempt {
		t.Fatalf("budget refusal mutated blocked attempt: before=%+v after=%+v", before, after)
	}
	run, err := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != recoveryActiveRetryRefused || !strings.HasPrefix(run.LastError, "RETRY_LIMIT_REACHED") {
		t.Fatalf("budget refusal not recorded: %+v", run)
	}
}
