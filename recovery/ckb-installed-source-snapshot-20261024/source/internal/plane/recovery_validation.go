package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

func (p *Engine) ValidateRecoveryCandidate(ctx context.Context, cfg RecoveryValidationConfig, recoveryID string, repairAttempt int) (RecoveryValidationResult, error) {
	return p.validateRecoveryCandidateEntry(ctx, cfg, recoveryID, repairAttempt, false)
}

// RevalidateRecoveryCandidate is the explicit policy-owned path for spending a
// second validation attempt on the same sealed repair candidate.
func (p *Engine) RevalidateRecoveryCandidate(ctx context.Context, cfg RecoveryValidationConfig, recoveryID string, repairAttempt int) (RecoveryValidationResult, error) {
	return p.validateRecoveryCandidateEntry(ctx, cfg, recoveryID, repairAttempt, true)
}

func (p *Engine) validateRecoveryCandidateEntry(ctx context.Context, cfg RecoveryValidationConfig, recoveryID string, repairAttempt int, allowNext bool) (RecoveryValidationResult, error) {
	if err := validateRecoveryValidationConfig(cfg); err != nil {
		return RecoveryValidationResult{}, err
	}
	if !hexDigest(recoveryID, 64) || repairAttempt < 1 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_ID_INVALID")
	}
	candidate, err := p.VerifyRecoveryCandidateEvidence(recoveryID, repairAttempt)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if candidate.Status != "CANDIDATE_PREPARED" {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_CANDIDATE_NOT_PREPARED")
	}
	preflight, err := p.recoveryCandidatePreflight(ctx, recoveryID)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if candidate.PlanID != preflight.Plan.PlanID {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_PLAN_CHANGED")
	}
	return p.validateRecoveryCandidatePreparedMode(ctx, cfg, preflight, candidate, allowNext)
}

func (p *Engine) validateRecoveryCandidatePrepared(ctx context.Context, cfg RecoveryValidationConfig, preflight recoveryCandidatePreflight, candidate RecoveryCandidateResult) (RecoveryValidationResult, error) {
	return p.validateRecoveryCandidatePreparedMode(ctx, cfg, preflight, candidate, false)
}

// recoveryBaselineGoPreflight proves that an Acceptance.All baseline is green before
// any candidate validation attempt is claimed. The scratch tree and evidence are
// deliberately non-authoritative and are removed after the preclaim check.
func (p *Engine) recoveryBaselineGoPreflight(ctx context.Context, preflight recoveryCandidatePreflight) error {
	if !preflight.Order.Acceptance.All {
		return nil
	}
	workspaceParent := filepath.Join(p.Root, "workspaces", "baseline-preflight")
	evidenceParent := filepath.Join(p.Root, "evidence", "baseline-preflight")
	if err := os.MkdirAll(workspaceParent, 0700); err != nil {
		return err
	}
	if err := os.MkdirAll(evidenceParent, 0700); err != nil {
		return err
	}
	workspaceRoot, err := os.MkdirTemp(workspaceParent, "preclaim-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(workspaceRoot)
	evidenceRoot, err := os.MkdirTemp(evidenceParent, "preclaim-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(evidenceRoot)
	baselineDir := filepath.Join(workspaceRoot, "baseline")
	if err = p.exportBaseline(ctx, preflight.SourceRepo.LocalPath, preflight.Order.Baseline.SHA, baselineDir); err != nil {
		return fmt.Errorf("RECOVERY_BASELINE_EXPORT_FAILED: %w", err)
	}
	testJob := Job{
		ID:        preflight.Order.ID,
		Attempt:   preflight.Snapshot.BlockedAttempt,
		Workspace: baselineDir,
		Evidence:  evidenceRoot,
		Order:     preflight.Order,
	}
	runnerEngine := *p
	runnerEngine.Store = nil
	pass, detail := runnerEngine.goTest(ctx, testJob, "", true, 0)
	if !pass {
		return errors.New("RECOVERY_BASELINE_GO_TEST_FAILED: " + detail)
	}
	return nil
}

func (p *Engine) validateRecoveryCandidatePreparedMode(ctx context.Context, cfg RecoveryValidationConfig, preflight recoveryCandidatePreflight, candidate RecoveryCandidateResult, allowNext bool) (RecoveryValidationResult, error) {
	if err := validateRecoveryValidationConfig(cfg); err != nil {
		return RecoveryValidationResult{}, err
	}
	if candidate.Status != "CANDIDATE_PREPARED" || candidate.ProductionAccepted || candidate.ResumeAuthorized ||
		candidate.RecoveryID != preflight.Transaction.RecoveryID || candidate.PlanID != preflight.Plan.PlanID {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_CANDIDATE_INVALID")
	}
	if !hexDigest(candidate.EvidenceManifestSHA256, 64) {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_CANDIDATE_UNSEALED")
	}
	if err := p.sourceAuthority(ctx); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := p.verifyContract(preflight.Order); err != nil {
		return RecoveryValidationResult{}, errors.New("RECOVERY_AUTHORIZATION_CONTRACT_CHANGED")
	}
	if err := baseline(p.Config.Tools.Git, preflight.SourceRepo.LocalPath, preflight.Order); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := verifyRecoverySourceState(ctx, p, preflight.SourceRepo.LocalPath, candidate.Evidence); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := p.recoveryBaselineGoPreflight(ctx, preflight); err != nil {
		return RecoveryValidationResult{}, err
	}

	workspaceRoot := filepath.Join(p.Root, "workspaces", "v", candidate.RecoveryID[:24], fmt.Sprint(candidate.RepairAttempt))
	evidence := filepath.Join(p.Root, "evidence", "recovery-validation", candidate.RecoveryID, fmt.Sprint(candidate.RepairAttempt))
	out := RecoveryValidationResult{
		RecoveryID:              candidate.RecoveryID,
		PlanID:                  candidate.PlanID,
		RepairAttempt:           candidate.RepairAttempt,
		WorkspaceRoot:           workspaceRoot,
		BaselineDir:             filepath.Join(workspaceRoot, "baseline"),
		CandidateDir:            filepath.Join(workspaceRoot, "candidate"),
		Evidence:                evidence,
		CandidateManifestSHA256: candidate.EvidenceManifestSHA256,
		ProductionAccepted:      false,
		ResumeAuthorized:        false,
	}
	if err := bridgeContained(p.Root, out.WorkspaceRoot); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := bridgeContained(p.Root, out.Evidence); err != nil {
		return RecoveryValidationResult{}, err
	}
	claimed, err := claimRecoveryValidationMode(
		p.Store.DB,
		out,
		recoveryValidationBudget(cfg),
		allowNext,
	)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if claimed.Status != "RUNNING" {
		if _, verifyErr := p.VerifyRecoveryValidationEvidence(claimed.RecoveryID, claimed.RepairAttempt); verifyErr != nil {
			return RecoveryValidationResult{}, verifyErr
		}
		if claimed.Status != "VALIDATED" {
			return claimed, errors.New(claimed.Status + ": " + claimed.FirstFailedCheck)
		}
		return claimed, nil
	}
	out = claimed

	for _, dir := range []string{out.WorkspaceRoot, out.Evidence} {
		if _, statErr := os.Lstat(dir); !os.IsNotExist(statErr) {
			if statErr == nil {
				statErr = errors.New("RECOVERY_VALIDATION_PATH_COLLISION")
			}
			return p.failRecoveryValidation(out, statErr)
		}
	}
	if err = os.MkdirAll(out.Evidence, 0700); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = os.MkdirAll(out.WorkspaceRoot, 0700); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = writeJSON(filepath.Join(out.Evidence, "candidate_anchor.json"), candidate); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = writeJSON(filepath.Join(out.Evidence, "recovery_transaction.json"), preflight.Transaction); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = writeJSON(filepath.Join(out.Evidence, "recovery_plan.json"), preflight.Plan); err != nil {
		return p.failRecoveryValidation(out, err)
	}

	if err = p.exportBaseline(ctx, preflight.SourceRepo.LocalPath, preflight.Order.Baseline.SHA, out.BaselineDir); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = p.exportBaseline(ctx, preflight.SourceRepo.LocalPath, preflight.Order.Baseline.SHA, out.CandidateDir); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	entries, err := applyRecoveryCandidateOverlay(candidate, out.CandidateDir)
	if err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if !sameRecoveryChangedFiles(entries, candidate.ChangedFiles) {
		return p.failRecoveryValidation(out, errors.New("RECOVERY_VALIDATION_CHANGED_FILES_MISMATCH"))
	}

	baselineInv, err := treeInventory(out.BaselineDir)
	if err != nil {
		return p.failRecoveryValidation(out, err)
	}
	inputInv, err := treeInventory(out.CandidateDir)
	if err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = writeJSON(filepath.Join(out.Evidence, "baseline_inventory.json"), baselineInv); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if err = writeJSON(filepath.Join(out.Evidence, "validation_input.json"), inputInv); err != nil {
		return p.failRecoveryValidation(out, err)
	}

	checks := []Check{}
	failed := ""
	add := func(name string, pass bool, detail string) {
		checks = append(checks, Check{Name: name, Pass: pass, Detail: detail})
		if !pass && failed == "" {
			failed = name
		}
	}

	for _, name := range preflight.Order.RequiredPaths {
		add("REQUIRED_FILE_MISSING", regularPath(out.CandidateDir, name) == nil, name)
	}
	add("NO_DIFF_PRODUCED", len(candidate.ChangedFiles) > 0, "Recovery candidate must contain an authorized source diff")
	for _, name := range candidate.ChangedFiles {
		add("FORBIDDEN_PATH_MODIFIED", preflight.Order.Allows(name), name)
	}
	pass, detail := recoveryDiffHygiene(ctx, p.Config.Tools.Git, out.BaselineDir, out.CandidateDir)
	add("SOURCE_HYGIENE_FAILED", pass, detail)
	for _, entry := range entries {
		if entry.Deleted {
			continue
		}
		full := filepath.Join(out.CandidateDir, filepath.FromSlash(entry.Path))
		info, statErr := os.Lstat(full)
		good := statErr == nil && info.Mode().IsRegular() && info.Mode()&os.ModeSymlink == 0
		if good {
			data, readErr := os.ReadFile(full)
			good = readErr == nil && !bytes.Contains(data, []byte("<<<<<<< ")) && !bytes.ContainsRune(data, 0)
		}
		add("SOURCE_HYGIENE_FAILED", good, entry.Path+": regular text file without merge markers")
	}

	if preflight.SourceRepo.Mode != "demo" {
		add("WINDOWS_AUTHORITY_REQUIRED",
			runtime.GOOS == "windows" && runtime.GOARCH == "amd64" && runtime.Version() == "go1.25.5",
			"Requires Go 1.25.5 windows/amd64")
	}

	testJob := Job{
		ID:        preflight.Order.ID,
		Attempt:   preflight.Snapshot.BlockedAttempt,
		Workspace: out.CandidateDir,
		Evidence:  out.Evidence,
		Order:     preflight.Order,
	}
	runnerEngine := *p
	runnerEngine.Store = nil

	if failed == "" && (len(preflight.Order.Preserve) > 0 || preflight.Order.Acceptance.Browser) {
		for _, c := range runnerEngine.uiChecks(testJob, out.BaselineDir) {
			add(c.Name, c.Pass, c.Detail)
		}
	}
	if failed == "" && p.Config.Autonomy.Enabled {
		pass, detail = runnerEngine.powershellCheck(ctx, testJob, candidate.ChangedFiles)
		add("POWERSHELL_ACCEPTANCE_FAILED", pass, detail)
	}
	if failed == "" {
		for i, pattern := range preflight.Order.RequiredTests.FocusedGo {
			pass, detail = runnerEngine.goTest(ctx, testJob, pattern, false, i)
			add("FOCUSED_TEST_FAILED", pass, detail)
		}
		if preflight.Order.Acceptance.All {
			pass, detail = runnerEngine.goTest(ctx, testJob, "", true, 0)
			add("GO_TEST_FAILED", pass, detail)
		}
	}
	if failed == "" && preflight.Order.Acceptance.Browser {
		cs, browserErr := runnerEngine.browserCheck(ctx, testJob)
		for _, c := range cs {
			add(c.Name, c.Pass, c.Detail)
		}
		code := "PLAYWRIGHT_FAILED"
		if browserErr != nil && strings.HasPrefix(browserErr.Error(), "PLAYWRIGHT_UNAVAILABLE") {
			code = "PLAYWRIGHT_UNAVAILABLE"
		}
		detail = "Static source browser checks at 1024 and 1440"
		if browserErr != nil {
			detail = browserErr.Error()
		}
		add(code, browserErr == nil, detail)
	}

	postInv, invErr := treeInventory(out.CandidateDir)
	add("ACCEPTANCE_INPUT_MUTATED", invErr == nil && sameInventory(inputInv, postInv), "Frozen recovery validation tree unchanged after tests")
	if invErr == nil {
		_ = writeJSON(filepath.Join(out.Evidence, "validation_output.json"), postInv)
	}
	if ctx.Err() != nil {
		add("ACCEPTANCE_CANCELLED", false, ctx.Err().Error())
	}
	if err = verifyRecoverySourceState(ctx, p, preflight.SourceRepo.LocalPath, candidate.Evidence); err != nil {
		add("SOURCE_REPOSITORY_MUTATED", false, err.Error())
	} else {
		add("SOURCE_REPOSITORY_MUTATED", true, "Source repository matches Stage-5 sealed state")
	}
	if p.Config.Autonomy.Enabled {
		err = p.sourceAuthority(ctx)
		if err != nil {
			add("PLANE_AUTHORITY_LOST", false, err.Error())
		} else {
			add("PLANE_AUTHORITY_LOST", true, "Authority reverified before validation seal")
		}
	}

	out.Status = "VALIDATED"
	if failed != "" {
		out.Status = "REJECTED"
		out.FirstFailedCheck = failed
	}
	if err = writeJSON(filepath.Join(out.Evidence, "validation_checks.json"), checks); err != nil {
		return p.failRecoveryValidation(out, err)
	}
	return p.finishAndSealRecoveryValidation(out)
}

func applyRecoveryCandidateOverlay(candidate RecoveryCandidateResult, candidateDir string) ([]RecoveryCandidateEntry, error) {
	raw, err := os.ReadFile(filepath.Join(candidate.Evidence, "candidate_inventory.json"))
	if err != nil {
		return nil, err
	}
	var entries []RecoveryCandidateEntry
	if err = json.Unmarshal(raw, &entries); err != nil {
		return nil, errors.New("RECOVERY_VALIDATION_INVENTORY_INVALID")
	}
	seen := map[string]bool{}
	for _, entry := range entries {
		key := strings.ToLower(entry.Path)
		if !safePath(entry.Path) || seen[key] {
			return nil, errors.New("RECOVERY_VALIDATION_INVENTORY_INVALID")
		}
		seen[key] = true
		dst := filepath.Join(candidateDir, filepath.FromSlash(entry.Path))
		if entry.Deleted {
			if err = os.Remove(dst); err != nil {
				return nil, errors.New("RECOVERY_VALIDATION_DELETE_INVALID")
			}
			continue
		}
		if !hexDigest(entry.SHA256, 64) {
			return nil, errors.New("RECOVERY_VALIDATION_INVENTORY_INVALID")
		}
		src := filepath.Join(candidate.Evidence, "candidate_files", filepath.FromSlash(entry.Path))
		info, statErr := os.Lstat(src)
		if statErr != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
			return nil, errors.New("RECOVERY_VALIDATION_CANDIDATE_FILE_INVALID")
		}
		data, readErr := os.ReadFile(src)
		if readErr != nil || digest(data) != entry.SHA256 {
			return nil, errors.New("RECOVERY_VALIDATION_CANDIDATE_HASH_MISMATCH")
		}
		if err = os.MkdirAll(filepath.Dir(dst), 0700); err != nil {
			return nil, err
		}
		if err = os.WriteFile(dst, data, 0600); err != nil {
			return nil, err
		}
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Path < entries[j].Path })
	return entries, nil
}

func sameRecoveryChangedFiles(entries []RecoveryCandidateEntry, changed []string) bool {
	a := make([]string, 0, len(entries))
	for _, entry := range entries {
		a = append(a, entry.Path)
	}
	b := append([]string(nil), changed...)
	sort.Strings(a)
	sort.Strings(b)
	return jsonText(a) == jsonText(b)
}

func verifyRecoverySourceState(ctx context.Context, p *Engine, sourceRepo, candidateEvidence string) error {
	raw, err := os.ReadFile(filepath.Join(candidateEvidence, "source_repo_after.json"))
	if err != nil {
		return err
	}
	var sealed ProfileWorkspaceRepoState
	if err = json.Unmarshal(raw, &sealed); err != nil {
		return errors.New("RECOVERY_SOURCE_STATE_INVALID")
	}
	current, err := p.profileWorkspaceRepoState(ctx, sourceRepo)
	if err != nil {
		return err
	}
	if sealed != current {
		return errors.New("RECOVERY_SOURCE_REPO_CHANGED")
	}
	return nil
}

func recoveryDiffHygiene(ctx context.Context, gitTool, baselineDir, candidateDir string) (bool, string) {
	root, err := os.MkdirTemp("", "ckb-recovery-hygiene-")
	if err != nil {
		return false, err.Error()
	}
	defer os.RemoveAll(root)
	baselineNormalized := filepath.Join(root, "baseline")
	candidateNormalized := filepath.Join(root, "candidate")
	if err = copyRecoveryHygieneTree(baselineDir, baselineNormalized); err != nil {
		return false, err.Error()
	}
	if err = copyRecoveryHygieneTree(candidateDir, candidateNormalized); err != nil {
		return false, err.Error()
	}

	bounded, cancel := context.WithTimeout(ctx, time.Minute)
	defer cancel()
	cmd := exec.CommandContext(bounded, gitTool,
		"-c", "core.hooksPath=",
		"-c", "core.fsmonitor=false",
		"-c", "core.autocrlf=false",
		"-c", "core.safecrlf=false",
		"-c", "core.eol=lf",
		"diff", "--no-index", "--no-ext-diff", "--no-textconv", "--check", "--", baselineNormalized, candidateNormalized,
	)
	cmd.WaitDelay = 2 * time.Second
	out, err := cmd.CombinedOutput()
	text := strings.TrimSpace(string(out))
	if len(text) > 4096 {
		text = text[len(text)-4096:]
	}
	if err == nil {
		return true, "No whitespace/conflict errors after CRLF normalization"
	}
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) && exitErr.ExitCode() == 1 && text == "" {
		return true, "Candidate differs from baseline with no whitespace/conflict errors after CRLF normalization"
	}
	if text == "" {
		text = err.Error()
	}
	return false, text
}

func copyRecoveryHygieneTree(src, dst string) error {
	return filepath.WalkDir(src, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := dst
		if rel != "." {
			target = filepath.Join(dst, rel)
		}
		if entry.IsDir() {
			return os.MkdirAll(target, 0700)
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
			return errors.New("RECOVERY_HYGIENE_NON_REGULAR_FILE")
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if !bytes.ContainsRune(data, 0) {
			data = bytes.ReplaceAll(data, []byte("\r\n"), []byte("\n"))
		}
		if err = os.MkdirAll(filepath.Dir(target), 0700); err != nil {
			return err
		}
		return os.WriteFile(target, data, 0600)
	})
}

func (p *Engine) failRecoveryValidation(out RecoveryValidationResult, cause error) (RecoveryValidationResult, error) {
	out.Status = "EVIDENCE_FAILED"
	out.FirstFailedCheck = "EVIDENCE_FAILED"
	out.ProductionAccepted = false
	out.ResumeAuthorized = false
	if out.Evidence != "" {
		if err := os.MkdirAll(out.Evidence, 0700); err == nil {
			_ = writeJSON(filepath.Join(out.Evidence, "validation_error.json"), map[string]any{
				"error": errorText(cause),
				"production_accepted": false,
				"resume_authorized": false,
			})
			if final, sealErr := p.sealRecoveryValidationRecord(out); sealErr == nil {
				if cause != nil {
					return final, cause
				}
				return final, errors.New("EVIDENCE_FAILED")
			}
		}
	}
	final, finishErr := finishRecoveryValidation(p.Store.DB, out)
	if finishErr != nil {
		return RecoveryValidationResult{}, finishErr
	}
	if cause != nil {
		return final, cause
	}
	return final, errors.New("EVIDENCE_FAILED")
}

func (p *Engine) sealRecoveryValidationRecord(out RecoveryValidationResult) (RecoveryValidationResult, error) {
	out.ProductionAccepted = false
	out.ResumeAuthorized = false
	out.EvidenceManifestSHA256 = ""
	if err := writeJSON(filepath.Join(out.Evidence, "validation_result.json"), out); err != nil {
		return RecoveryValidationResult{}, err
	}
	manifest, err := Manifest(out.Evidence)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if err = writeJSON(filepath.Join(out.Evidence, "evidence_manifest.json"), manifest); err != nil {
		return RecoveryValidationResult{}, err
	}
	manifestRaw, err := os.ReadFile(filepath.Join(out.Evidence, "evidence_manifest.json"))
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	out.EvidenceManifestSHA256 = digest(manifestRaw)
	return finishRecoveryValidation(p.Store.DB, out)
}

func (p *Engine) finishAndSealRecoveryValidation(out RecoveryValidationResult) (RecoveryValidationResult, error) {
	final, err := p.sealRecoveryValidationRecord(out)
	if err != nil {
		return p.failRecoveryValidation(out, err)
	}
	if final.Status != "VALIDATED" {
		return final, errors.New(final.Status + ": " + final.FirstFailedCheck)
	}
	return final, nil
}
