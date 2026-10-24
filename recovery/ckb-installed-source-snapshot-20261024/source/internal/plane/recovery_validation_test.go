package plane

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func recoveryValidationCounts(t *testing.T, p *Engine) (work, leases, queue, processes, acceptance int) {
	t.Helper()
	for query, dst := range map[string]*int{
		"SELECT count(*) FROM work_orders":     &work,
		"SELECT count(*) FROM worker_leases":   &leases,
		"SELECT count(*) FROM queue_items":      &queue,
		"SELECT count(*) FROM process_records":  &processes,
		"SELECT count(*) FROM acceptance_runs":  &acceptance,
	} {
		if err := p.Store.DB.QueryRow(query).Scan(dst); err != nil {
			t.Fatal(err)
		}
	}
	return
}

func prepareStage6Fixture(t *testing.T, worker Worker) (*Engine, recoveryCandidatePreflight, RecoveryCandidateResult) {
	t.Helper()
	p, w := setup(t)
	testAuthority(p)
	pre := recoveryCandidateTestPreflight(t, p, w)
	candidate, err := p.prepareRecoveryCandidateWithWorker(
		context.Background(),
		RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 2, TimeoutSeconds: 30},
		pre,
		worker,
	)
	if err != nil {
		t.Fatal(err)
	}
	if candidate.Status != "CANDIDATE_PREPARED" {
		t.Fatal(candidate)
	}
	return p, pre, candidate
}

func TestRecoveryValidationDefaultOffCreatesNoState(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, FakeWorker{})
	if _, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		RecoveryValidationConfig{},
		pre,
		candidate,
	); !errors.Is(err, errRecoveryValidationDisabled) {
		t.Fatal(err)
	}
	var n int
	if err := p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='blocker_recovery_validations'",
	).Scan(&n); err != nil || n != 0 {
		t.Fatal(n, err)
	}
}

func TestRecoveryValidationBaselineGoFailureDoesNotSpendBudget(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	w.Acceptance.All = true
	raw, err := yaml.Marshal(w)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(p.Root, "workorder.yaml"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	pre := recoveryCandidateTestPreflight(t, p, w)
	candidate, err := p.prepareRecoveryCandidateWithWorker(
		context.Background(),
		RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 2, TimeoutSeconds: 30},
		pre,
		FakeWorker{},
	)
	if err != nil {
		t.Fatal(err)
	}
	out, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		RecoveryValidationConfig{Enabled: true, MaxValidationAttempts: 3},
		pre,
		candidate,
	)
	if err == nil || !strings.HasPrefix(err.Error(), "RECOVERY_BASELINE_GO_TEST_FAILED:") {
		t.Fatalf("out=%+v err=%v", out, err)
	}
	if out.ValidationAttempt != 0 || out.Status != "" || out.ProductionAccepted || out.ResumeAuthorized {
		t.Fatalf("baseline failure became candidate validation state: %+v", out)
	}
	var tables int
	if err = p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='blocker_recovery_validations'",
	).Scan(&tables); err != nil || tables != 0 {
		t.Fatalf("baseline failure spent validation state: tables=%d err=%v", tables, err)
	}
	if _, statErr := os.Stat(filepath.Join(p.Root, "evidence", "recovery-validation")); !os.IsNotExist(statErr) {
		t.Fatalf("candidate validation evidence exists after baseline preclaim failure: %v", statErr)
	}
}

func TestRecoveryValidationPassesWithoutProductionStateMutation(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, FakeWorker{})
	bw, bl, bq, bp, ba := recoveryValidationCounts(t, p)

	out, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		RecoveryValidationConfig{Enabled: true},
		pre,
		candidate,
	)
	if err != nil {
		t.Fatal(err)
	}
	if out.Status != "VALIDATED" || out.ProductionAccepted || out.ResumeAuthorized ||
		out.EvidenceManifestSHA256 == "" {
		t.Fatal(out)
	}
	if _, err = p.VerifyRecoveryValidationEvidence(out.RecoveryID, out.RepairAttempt); err != nil {
		t.Fatal(err)
	}

	aw, al, aq, ap, aa := recoveryValidationCounts(t, p)
	if bw != aw || bl != al || bq != aq || bp != ap || ba != aa {
		t.Fatalf("validation mutated production state: before=%d/%d/%d/%d/%d after=%d/%d/%d/%d/%d",
			bw, bl, bq, bp, ba, aw, al, aq, ap, aa)
	}
	var rows int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_validations").Scan(&rows); err != nil || rows != 1 {
		t.Fatal(rows, err)
	}
}

func TestRecoveryValidationRejectsBadCandidateWithoutAuthority(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, &recoveryFixtureWorker{})
	out, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		RecoveryValidationConfig{Enabled: true},
		pre,
		candidate,
	)
	if err == nil {
		t.Fatal("bad recovery candidate validated")
	}
	if out.Status != "REJECTED" || out.FirstFailedCheck == "" ||
		out.ProductionAccepted || out.ResumeAuthorized || out.EvidenceManifestSHA256 == "" {
		t.Fatalf("%+v err=%v", out, err)
	}
	if _, verifyErr := p.VerifyRecoveryValidationEvidence(out.RecoveryID, out.RepairAttempt); verifyErr != nil {
		t.Fatal(verifyErr)
	}
}

func TestRecoveryValidationRefusesTamperedStage5Evidence(t *testing.T) {
	p, _, candidate := prepareStage6Fixture(t, FakeWorker{})
	path := filepath.Join(candidate.Evidence, "candidate_files", "demo.txt")
	if err := os.WriteFile(path, []byte("tampered\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := p.VerifyRecoveryCandidateEvidence(candidate.RecoveryID, candidate.RepairAttempt); err == nil ||
		err.Error() != "RECOVERY_CANDIDATE_EVIDENCE_INVALID" {
		t.Fatal(err)
	}
}

func TestRecoveryValidationReplayDetectsFrozenTreeTampering(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, FakeWorker{})
	out, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		RecoveryValidationConfig{Enabled: true},
		pre,
		candidate,
	)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(out.CandidateDir, "demo.txt"), []byte("tampered after validation\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err = p.VerifyRecoveryValidationEvidence(out.RecoveryID, out.RepairAttempt); err == nil ||
		err.Error() != "RECOVERY_VALIDATION_INPUT_CHANGED" {
		t.Fatal(err)
	}
}

func TestRecoveryValidationTerminalResultCannotGrantAuthority(t *testing.T) {
	p, _, candidate := prepareStage6Fixture(t, FakeWorker{})
	out := RecoveryValidationResult{
		RecoveryID: candidate.RecoveryID,
		PlanID: candidate.PlanID,
		RepairAttempt: candidate.RepairAttempt,
		Status: "RUNNING",
		WorkspaceRoot: filepath.Join(p.Root, "workspaces", "v", candidate.RecoveryID[:24], "1"),
		Evidence: filepath.Join(p.Root, "evidence", "recovery-validation", candidate.RecoveryID, "1"),
		CandidateManifestSHA256: candidate.EvidenceManifestSHA256,
	}
	claim, err := claimRecoveryValidation(p.Store.DB, out)
	if err != nil {
		t.Fatal(err)
	}
	claim.Status = "VALIDATED"
	claim.ProductionAccepted = true
	if _, err = finishRecoveryValidation(p.Store.DB, claim); err == nil ||
		err.Error() != "RECOVERY_VALIDATION_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
	claim.ProductionAccepted = false
	claim.ResumeAuthorized = true
	if _, err = finishRecoveryValidation(p.Store.DB, claim); err == nil ||
		err.Error() != "RECOVERY_VALIDATION_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
}


func TestRecoveryValidationReplayDoesNotSpendRevalidationBudget(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, &recoveryFixtureWorker{})
	cfg := RecoveryValidationConfig{Enabled: true, MaxValidationAttempts: 2}

	first, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		cfg,
		pre,
		candidate,
	)
	if err == nil || first.Status != "REJECTED" || first.ValidationAttempt != 1 {
		t.Fatalf("first=%+v err=%v", first, err)
	}

	replay, err := p.validateRecoveryCandidatePrepared(
		context.Background(),
		cfg,
		pre,
		candidate,
	)
	if err == nil || replay.Status != "REJECTED" || replay.ValidationAttempt != 1 {
		t.Fatalf("replay=%+v err=%v", replay, err)
	}
	var rows int
	if err = p.Store.DB.QueryRow(
		"SELECT count(*) FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=?",
		candidate.RecoveryID, candidate.RepairAttempt,
	).Scan(&rows); err != nil || rows != 1 {
		t.Fatal(rows, err)
	}
}

func TestRecoveryValidationExplicitRevalidationHasSeparateBudget(t *testing.T) {
	p, pre, candidate := prepareStage6Fixture(t, &recoveryFixtureWorker{})
	cfg := RecoveryValidationConfig{Enabled: true, MaxValidationAttempts: 2}
	bw, bl, bq, bp, ba := recoveryValidationCounts(t, p)

	first, err := p.validateRecoveryCandidatePreparedMode(
		context.Background(),
		cfg,
		pre,
		candidate,
		false,
	)
	if err == nil || first.Status != "REJECTED" || first.ValidationAttempt != 1 {
		t.Fatalf("first=%+v err=%v", first, err)
	}
	second, err := p.validateRecoveryCandidatePreparedMode(
		context.Background(),
		cfg,
		pre,
		candidate,
		true,
	)
	if err == nil || second.Status != "REJECTED" || second.ValidationAttempt != 2 {
		t.Fatalf("second=%+v err=%v", second, err)
	}
	if first.Evidence == second.Evidence || first.WorkspaceRoot == second.WorkspaceRoot {
		t.Fatal("revalidation reused prior evidence/workspace")
	}
	if _, err = p.VerifyRecoveryValidationAttemptEvidence(candidate.RecoveryID, candidate.RepairAttempt, 1); err != nil {
		t.Fatal(err)
	}
	if _, err = p.VerifyRecoveryValidationAttemptEvidence(candidate.RecoveryID, candidate.RepairAttempt, 2); err != nil {
		t.Fatal(err)
	}
	if _, err = p.validateRecoveryCandidatePreparedMode(
		context.Background(),
		cfg,
		pre,
		candidate,
		true,
	); err == nil || err.Error() != "RECOVERY_VALIDATION_BUDGET_EXHAUSTED" {
		t.Fatal(err)
	}

	aw, al, aq, ap, aa := recoveryValidationCounts(t, p)
	if bw != aw || bl != al || bq != aq || bp != ap || ba != aa {
		t.Fatalf("revalidation mutated production state: before=%d/%d/%d/%d/%d after=%d/%d/%d/%d/%d",
			bw, bl, bq, bp, ba, aw, al, aq, ap, aa)
	}
}


func TestRecoveryDiffHygieneIgnoresGlobalAutoCRLFWarningsButStillCatchesWhitespace(t *testing.T) {
	root := t.TempDir()
	config := filepath.Join(root, "gitconfig")
	if err := os.WriteFile(config, []byte("[core]\n\tautocrlf = true\n\tsafecrlf = true\n"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("GIT_CONFIG_GLOBAL", config)
	t.Setenv("GIT_CONFIG_NOSYSTEM", "1")

	baselineDir := filepath.Join(root, "baseline")
	candidateDir := filepath.Join(root, "candidate")
	if err := os.MkdirAll(baselineDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(candidateDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(baselineDir, "demo.txt"), []byte("baseline\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(candidateDir, "demo.txt"), []byte("candidate produced by deterministic fake worker\n"), 0600); err != nil {
		t.Fatal(err)
	}

	pass, detail := recoveryDiffHygiene(context.Background(), "git", baselineDir, candidateDir)
	if !pass {
		t.Fatalf("autocrlf warning contaminated hygiene result: %s", detail)
	}

	if err := os.WriteFile(filepath.Join(candidateDir, "demo.txt"), []byte("bad trailing whitespace \n"), 0600); err != nil {
		t.Fatal(err)
	}
	pass, detail = recoveryDiffHygiene(context.Background(), "git", baselineDir, candidateDir)
	if pass {
		t.Fatalf("real whitespace defect escaped hygiene check: %s", detail)
	}
}


func TestRecoveryDiffHygieneAllowsCRLFButRejectsRealTrailingWhitespace(t *testing.T) {
	root := t.TempDir()
	baseline := filepath.Join(root, "baseline")
	candidate := filepath.Join(root, "candidate")
	if err := os.MkdirAll(baseline, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(candidate, 0700); err != nil {
		t.Fatal(err)
	}
	baseFile := filepath.Join(baseline, "sample.go")
	candidateFile := filepath.Join(candidate, "sample.go")
	if err := os.WriteFile(baseFile, []byte("package sample\n\nvar Value = 1\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(candidateFile, []byte("package sample\r\n\r\nvar Value = 2\r\n"), 0600); err != nil {
		t.Fatal(err)
	}
	pass, detail := recoveryDiffHygiene(context.Background(), "git", baseline, candidate)
	if !pass {
		t.Fatalf("CRLF line terminators must not fail source hygiene: %s", detail)
	}
	if err := os.WriteFile(candidateFile, []byte("package sample\r\n\r\nvar Value = 2  \r\n"), 0600); err != nil {
		t.Fatal(err)
	}
	pass, detail = recoveryDiffHygiene(context.Background(), "git", baseline, candidate)
	if pass {
		t.Fatalf("real trailing whitespace must remain rejected: %s", detail)
	}
}


func TestRecoveryDiffHygieneIgnoresPreexistingWhitespaceExposedOnlyByLineEndingRewrite(t *testing.T) {
	root := t.TempDir()
	baseline := filepath.Join(root, "baseline")
	candidate := filepath.Join(root, "candidate")
	if err := os.MkdirAll(baseline, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(candidate, 0700); err != nil {
		t.Fatal(err)
	}
	base := "/* legacy trailing whitespace */  \nbody { color: black; }\n"
	cand := "/* legacy trailing whitespace */  \r\nbody { color: black; }\r\n.alert { display: block; }\r\n"
	if err := os.WriteFile(filepath.Join(baseline, "app.css"), []byte(base), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(candidate, "app.css"), []byte(cand), 0600); err != nil {
		t.Fatal(err)
	}
	pass, detail := recoveryDiffHygiene(context.Background(), "git", baseline, candidate)
	if !pass {
		t.Fatalf("preexisting trailing whitespace became a false positive after line-ending rewrite: %s", detail)
	}

	cand = "/* legacy trailing whitespace */  \r\nbody { color: black; }\r\n.alert { display: block; }  \r\n"
	if err := os.WriteFile(filepath.Join(candidate, "app.css"), []byte(cand), 0600); err != nil {
		t.Fatal(err)
	}
	pass, detail = recoveryDiffHygiene(context.Background(), "git", baseline, candidate)
	if pass {
		t.Fatalf("candidate-introduced trailing whitespace escaped normalized hygiene check: %s", detail)
	}
}
