package plane

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
)

func (p *Engine) RecoveryValidation(recoveryID string, repairAttempt int) (RecoveryValidationResult, error) {
	if !hexDigest(recoveryID, 64) || repairAttempt < 1 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_ID_INVALID")
	}
	var attempt int
	if err := p.Store.DB.QueryRow(
		"SELECT max(validation_attempt) FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=?",
		recoveryID, repairAttempt,
	).Scan(&attempt); err != nil {
		return RecoveryValidationResult{}, err
	}
	if attempt < 1 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_NOT_FOUND")
	}
	return p.RecoveryValidationAttempt(recoveryID, repairAttempt, attempt)
}

func (p *Engine) RecoveryValidationAttempt(recoveryID string, repairAttempt, validationAttempt int) (RecoveryValidationResult, error) {
	return loadRecoveryValidation(p.Store.DB, recoveryID, repairAttempt, validationAttempt)
}

func (p *Engine) VerifyRecoveryValidationEvidence(recoveryID string, repairAttempt int) (RecoveryValidationResult, error) {
	out, err := p.RecoveryValidation(recoveryID, repairAttempt)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	return p.verifyRecoveryValidationResult(out)
}

func (p *Engine) VerifyRecoveryValidationAttemptEvidence(recoveryID string, repairAttempt, validationAttempt int) (RecoveryValidationResult, error) {
	out, err := p.RecoveryValidationAttempt(recoveryID, repairAttempt, validationAttempt)
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	return p.verifyRecoveryValidationResult(out)
}

func (p *Engine) verifyRecoveryValidationResult(out RecoveryValidationResult) (RecoveryValidationResult, error) {
	if out.Status == "RUNNING" || out.ValidationAttempt < 1 || !hexDigest(out.EvidenceManifestSHA256, 64) {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_NOT_SEALED")
	}
	if err := bridgeContained(p.Root, out.Evidence); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := bridgeContained(p.Root, out.WorkspaceRoot); err != nil {
		return RecoveryValidationResult{}, err
	}
	if err := VerifyManifest(out.Evidence); err != nil {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_EVIDENCE_INVALID")
	}
	manifestRaw, err := os.ReadFile(filepath.Join(out.Evidence, "evidence_manifest.json"))
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	if digest(manifestRaw) != out.EvidenceManifestSHA256 {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_EVIDENCE_ANCHOR_MISMATCH")
	}

	resultRaw, err := os.ReadFile(filepath.Join(out.Evidence, "validation_result.json"))
	if err != nil {
		return RecoveryValidationResult{}, err
	}
	var disk RecoveryValidationResult
	if err = json.Unmarshal(resultRaw, &disk); err != nil {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_RESULT_INVALID")
	}
	if disk.Schema != recoveryValidationSchema ||
		disk.RecoveryID != out.RecoveryID ||
		disk.PlanID != out.PlanID ||
		disk.RepairAttempt != out.RepairAttempt ||
		disk.ValidationAttempt != out.ValidationAttempt ||
		disk.Status != out.Status ||
		disk.FirstFailedCheck != out.FirstFailedCheck ||
		disk.Evidence != out.Evidence ||
		disk.WorkspaceRoot != out.WorkspaceRoot ||
		disk.BaselineDir != out.BaselineDir ||
		disk.CandidateDir != out.CandidateDir ||
		disk.CandidateManifestSHA256 != out.CandidateManifestSHA256 ||
		disk.EvidenceManifestSHA256 != "" ||
		disk.ProductionAccepted || disk.ResumeAuthorized {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_RESULT_MISMATCH")
	}

	var expectedBaseline map[string]string
	raw, err := os.ReadFile(filepath.Join(out.Evidence, "baseline_inventory.json"))
	if err != nil || json.Unmarshal(raw, &expectedBaseline) != nil {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_BASELINE_INVENTORY_INVALID")
	}
	actualBaseline, err := treeInventory(out.BaselineDir)
	if err != nil || !sameInventory(expectedBaseline, actualBaseline) {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_BASELINE_CHANGED")
	}

	var expectedCandidate map[string]string
	raw, err = os.ReadFile(filepath.Join(out.Evidence, "validation_input.json"))
	if err != nil || json.Unmarshal(raw, &expectedCandidate) != nil {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_INPUT_INVENTORY_INVALID")
	}
	actualCandidate, err := treeInventory(out.CandidateDir)
	if err != nil || !sameInventory(expectedCandidate, actualCandidate) {
		return RecoveryValidationResult{}, errors.New("RECOVERY_VALIDATION_INPUT_CHANGED")
	}
	return out, nil
}
