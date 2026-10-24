package plane

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
)

func (p *Engine) RecoveryCandidate(recoveryID string, attempt int) (RecoveryCandidateResult, error) {
	var out RecoveryCandidateResult
	var raw []byte
	var status string
	if !hexDigest(recoveryID, 64) || attempt < 1 {
		return out, errors.New("RECOVERY_CANDIDATE_ID_INVALID")
	}
	if err := p.Store.DB.QueryRow(
		"SELECT raw,status FROM blocker_recovery_candidates WHERE recovery_id=? AND repair_attempt=?",
		recoveryID, attempt,
	).Scan(&raw, &status); err != nil {
		return out, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return RecoveryCandidateResult{}, err
	}
	if out.Schema != recoveryCandidateSchema || out.RecoveryID != recoveryID ||
		out.RepairAttempt != attempt || out.Status != status ||
		out.ProductionAccepted || out.ResumeAuthorized {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_STATE_CORRUPT")
	}
	return out, nil
}

func (p *Engine) VerifyRecoveryCandidateEvidence(recoveryID string, attempt int) (RecoveryCandidateResult, error) {
	out, err := p.RecoveryCandidate(recoveryID, attempt)
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if out.Status == "RUNNING" || !hexDigest(out.EvidenceManifestSHA256, 64) {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_NOT_SEALED")
	}
	if err = bridgeContained(p.Root, out.Evidence); err != nil {
		return RecoveryCandidateResult{}, err
	}
	if err = VerifyManifest(out.Evidence); err != nil {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_EVIDENCE_INVALID")
	}
	manifestRaw, err := os.ReadFile(filepath.Join(out.Evidence, "evidence_manifest.json"))
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	if digest(manifestRaw) != out.EvidenceManifestSHA256 {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_EVIDENCE_ANCHOR_MISMATCH")
	}
	resultRaw, err := os.ReadFile(filepath.Join(out.Evidence, "candidate_result.json"))
	if err != nil {
		return RecoveryCandidateResult{}, err
	}
	var disk RecoveryCandidateResult
	if err = json.Unmarshal(resultRaw, &disk); err != nil {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_RESULT_INVALID")
	}
	if disk.Schema != recoveryCandidateSchema ||
		disk.RecoveryID != out.RecoveryID ||
		disk.PlanID != out.PlanID ||
		disk.RepairAttempt != out.RepairAttempt ||
		disk.Status != out.Status ||
		disk.WorkspaceRoot != out.WorkspaceRoot ||
		disk.Worktree != out.Worktree ||
		disk.Evidence != out.Evidence ||
		jsonText(disk.ChangedFiles) != jsonText(out.ChangedFiles) ||
		disk.CandidateDiffSHA256 != out.CandidateDiffSHA256 ||
		disk.WorkerExitCode != out.WorkerExitCode ||
		disk.ProductionAccepted || disk.ResumeAuthorized ||
		disk.EvidenceManifestSHA256 != "" {
		return RecoveryCandidateResult{}, errors.New("RECOVERY_CANDIDATE_RESULT_MISMATCH")
	}
	return out, nil
}
