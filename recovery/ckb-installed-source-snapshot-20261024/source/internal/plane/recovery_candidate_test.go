package plane

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestRecoveryCandidatePreparedUsesSeparateWorkspaceAndNoWorkerLease(t *testing.T) {
	p, w := setup(t)
	pre := recoveryCandidateTestPreflight(t, p, w)
	beforeSource, err := p.profileWorkspaceRepoState(context.Background(), pre.SourceRepo.LocalPath)
	if err != nil {
		t.Fatal(err)
	}
	beforeWork, beforeLeases, beforeQueue := recoveryAuthoritativeCounts(t, p.Store.DB)

	worker := &recoveryFixtureWorker{}
	out, err := p.prepareRecoveryCandidateWithWorker(
		context.Background(),
		RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 2, TimeoutSeconds: 30},
		pre,
		worker,
	)
	if err != nil {
		t.Fatal(err)
	}
	if out.Status != "CANDIDATE_PREPARED" || out.RepairAttempt != 1 ||
		out.ProductionAccepted || out.ResumeAuthorized || worker.Calls() != 1 {
		t.Fatalf("%+v calls=%d", out, worker.Calls())
	}
	if out.Worktree == "" || out.Evidence == "" || out.EvidenceManifestSHA256 == "" {
		t.Fatal(out)
	}
	if err = bridgeContained(p.Root, out.Worktree); err != nil {
		t.Fatal(err)
	}
	if err = bridgeContained(p.Root, out.Evidence); err != nil {
		t.Fatal(err)
	}
	if filepath.Clean(out.Worktree) == filepath.Clean(pre.SourceRepo.LocalPath) {
		t.Fatal("recovery worker used source repo directly")
	}
	if _, err = os.Stat(filepath.Join(out.Evidence, "candidate.diff")); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(filepath.Join(out.Evidence, "candidate_files", "demo.txt")); err != nil {
		t.Fatal(err)
	}
	if _, err = p.VerifyRecoveryCandidateEvidence(out.RecoveryID, out.RepairAttempt); err != nil {
		t.Fatal(err)
	}

	afterSource, err := p.profileWorkspaceRepoState(context.Background(), pre.SourceRepo.LocalPath)
	if err != nil {
		t.Fatal(err)
	}
	if jsonText(beforeSource) != jsonText(afterSource) {
		t.Fatal("source repository changed")
	}
	afterWork, afterLeases, afterQueue := recoveryAuthoritativeCounts(t, p.Store.DB)
	if beforeWork != afterWork || beforeLeases != afterLeases || beforeQueue != afterQueue {
		t.Fatalf("candidate mutated execution tables: before=%d/%d/%d after=%d/%d/%d",
			beforeWork, beforeLeases, beforeQueue, afterWork, afterLeases, afterQueue)
	}
}

func TestRecoveryCandidateFailureModesRemainNonAuthoritative(t *testing.T) {
	for _, tc := range []struct {
		kind string
		want string
	}{
		{"fail", "WORKER_FAILED"},
		{"nodiff", "NO_DIFF"},
		{"forbidden", "FORBIDDEN_PATH"},
		{"ref", "REF_MUTATION"},
	} {
		t.Run(tc.kind, func(t *testing.T) {
			p, w := setup(t)
			pre := recoveryCandidateTestPreflight(t, p, w)
			worker := &recoveryFixtureWorker{kind: tc.kind}
			out, err := p.prepareRecoveryCandidateWithWorker(
				context.Background(),
				RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 1, TimeoutSeconds: 30},
				pre,
				worker,
			)
			if err == nil {
				t.Fatalf("expected terminal error for %s", tc.want)
			}
			if out.Status != tc.want || out.ProductionAccepted || out.ResumeAuthorized {
				t.Fatalf("%+v err=%v", out, err)
			}
			if out.EvidenceManifestSHA256 == "" {
				t.Fatal("terminal recovery result was not sealed")
			}
			if _, verifyErr := p.VerifyRecoveryCandidateEvidence(out.RecoveryID, out.RepairAttempt); verifyErr != nil {
				t.Fatal(verifyErr)
			}
		})
	}
}

func TestRecoveryCandidateEvidenceTamperingFailsClosed(t *testing.T) {
	p, w := setup(t)
	pre := recoveryCandidateTestPreflight(t, p, w)
	out, err := p.prepareRecoveryCandidateWithWorker(
		context.Background(),
		RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 1, TimeoutSeconds: 30},
		pre,
		&recoveryFixtureWorker{},
	)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(out.Evidence, "candidate.diff"), []byte("tampered\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err = p.VerifyRecoveryCandidateEvidence(out.RecoveryID, out.RepairAttempt); err == nil ||
		err.Error() != "RECOVERY_CANDIDATE_EVIDENCE_INVALID" {
		t.Fatal(err)
	}
}
