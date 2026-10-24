package plane

import (
	"errors"
	"strings"
	"testing"
)

func recoveryFixture(blocker string) RecoveryEvidenceSnapshot {
	return RecoveryEvidenceSnapshot{
		WorkOrderID:              "V11110_RECOVERY_FIXTURE_R1",
		BlockedAttempt:           2,
		QueueInputSHA256:         strings.Repeat("1", 64),
		WorkOrderSHA256:          strings.Repeat("2", 64),
		AuthorizationContractSHA: strings.Repeat("3", 64),
		BaselineRef:              "local-candidate/recovery-fixture-r1",
		BaselineSHA:              strings.Repeat("a", 40),
		ObjectiveID:              "RECOVERY_OBJECTIVE_R1",
		ObjectiveStage:           0,
		ObjectiveRevision:        7,
		AuthorityGeneration:      2,
		OriginalBlocker:          blocker,
		EvidenceManifestSHA256:   strings.Repeat("4", 64),
	}
}

func observeFixture(t *testing.T, in RecoveryEvidenceSnapshot) RecoveryObservation {
	t.Helper()
	out, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, in)
	if err != nil {
		t.Fatal(err)
	}
	if out.AutomaticMutation {
		t.Fatal("stage3 observer gained mutation authority")
	}
	if out.RecoveryID == "" || out.Schema != recoveryObservationSchema || out.PolicyVersion != recoveryObserverPolicyVersion {
		t.Fatal(out)
	}
	return out
}

func TestRecoveryObserverDefaultOff(t *testing.T) {
	_, err := ObserveRecovery(RecoveryObserverConfig{}, recoveryFixture("GO_TEST_FAILED"))
	if !errors.Is(err, errRecoveryObserverDisabled) {
		t.Fatal(err)
	}
}

func TestRecoveryObserverDeterministicForIdenticalEvidence(t *testing.T) {
	in := recoveryFixture("GO_TEST_FAILED")
	in.ChangedFiles = []string{"pkg/web/strategy.html", "pkg/web/app.js"}
	a := observeFixture(t, in)
	in.ChangedFiles = []string{"pkg/web/app.js", "pkg/web/strategy.html"}
	b := observeFixture(t, in)
	if a != b {
		t.Fatalf("classification not deterministic: %#v %#v", a, b)
	}
}

func TestRecoveryObserverRejectsIdentityDrift(t *testing.T) {
	cases := []RecoveryEvidenceSnapshot{
		func() RecoveryEvidenceSnapshot { v := recoveryFixture("GO_TEST_FAILED"); v.QueueInputSHA256 = "bad"; return v }(),
		func() RecoveryEvidenceSnapshot { v := recoveryFixture("GO_TEST_FAILED"); v.BaselineSHA = strings.Repeat("b", 39); return v }(),
		func() RecoveryEvidenceSnapshot { v := recoveryFixture("GO_TEST_FAILED"); v.AuthorityGeneration = 0; return v }(),
		func() RecoveryEvidenceSnapshot { v := recoveryFixture("GO_TEST_FAILED"); v.ObjectiveRevision = 0; return v }(),
	}
	for i, in := range cases {
		if _, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, in); err == nil {
			t.Fatalf("case %d accepted invalid identity", i)
		}
	}
}

func TestRecoveryObserverHistoricalClassificationFixtures(t *testing.T) {
	cases := []struct {
		name      string
		in        RecoveryEvidenceSnapshot
		class     string
		subtype   string
		authority bool
	}{
		{"go-test", recoveryFixture("RETRY_LIMIT_REACHED: GO_TEST_FAILED"), "TEST_FAILURE", "", false},
		{"source-hygiene", recoveryFixture("SOURCE_HYGIENE_FAILED"), "SOURCE_HYGIENE", "", false},
		{"no-diff", recoveryFixture("NO_DIFF_PRODUCED"), "NO_DIFF", "", false},
		{"quota", recoveryFixture("CODEX_QUOTA_EXHAUSTED"), "PROVIDER_TRANSIENT", "QUOTA_EXHAUSTION", false},
		{"baseline", recoveryFixture("BASELINE_MISMATCH"), "BASELINE_DEFECT", "", true},
		{"scope", recoveryFixture("SCOPE_CHANGE_REQUIRED"), "SCOPE_CHANGE_REQUIRED", "", true},
		{"unknown", recoveryFixture("SOMETHING_NEW_AND_UNCLASSIFIED"), "UNKNOWN", "", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			out := observeFixture(t, tc.in)
			if out.NormalizedClass != tc.class || out.Subtype != tc.subtype || out.AuthorityRequired != tc.authority {
				t.Fatalf("got %#v", out)
			}
		})
	}
}

func TestRecoveryObserverR9R10WindowsCacheRefinesForbiddenPathToEnvironmentDefect(t *testing.T) {
	in := recoveryFixture("FORBIDDEN_PATH_MODIFIED")
	in.ChangedFiles = []string{
		"%SystemDrive%/ProgramData/Microsoft/Windows/Caches/cversions.2.db",
		"%SystemDrive%/ProgramData/Microsoft/Windows/Caches/cversions.2.db-wal",
	}
	out := observeFixture(t, in)
	if out.NormalizedClass != "ENVIRONMENT_DEFECT" || out.Subtype != "WINDOWS_SANDBOX_ARTIFACT" || out.AuthorityRequired {
		t.Fatal(out)
	}
}

func TestRecoveryObserverRealSourceForbiddenPathStaysScopeViolation(t *testing.T) {
	in := recoveryFixture("FORBIDDEN_PATH_MODIFIED")
	in.ChangedFiles = []string{"pkg/risk.go"}
	out := observeFixture(t, in)
	if out.NormalizedClass != "FORBIDDEN_PATH" || out.Subtype != "SOURCE_SCOPE_VIOLATION" || out.AuthorityRequired {
		t.Fatal(out)
	}
}

func TestRecoveryObserverUACTimeoutRefinesToEnvironmentDefect(t *testing.T) {
	in := recoveryFixture("RETRY_LIMIT_REACHED: WORKER_TIMEOUT")
	in.WorkerDiagnosticExcerpt = "windows sandbox failed: CreateProcessAsUserW failed"
	out := observeFixture(t, in)
	if out.NormalizedClass != "ENVIRONMENT_DEFECT" || out.Subtype != "WINDOWS_SANDBOX_INTERACTIVE_BLOCK" {
		t.Fatal(out)
	}
}

func TestRecoveryObserverAuthorityLeaseFailureIsNotScopeAuthorityExpansion(t *testing.T) {
	in := recoveryFixture("PLANE_AUTHORITY_LOST")
	in.ControllerDiagnostic = "AUTHORITY_LEASE_NOT_ACQUIRED"
	out := observeFixture(t, in)
	if out.NormalizedClass != "AUTHORITY_MISMATCH" || out.Subtype != "AUTHORITY_LEASE" || out.AuthorityRequired {
		t.Fatal(out)
	}
}

func TestRecoveryObserverWorkerAuthUsesBoundedDiagnosticMarker(t *testing.T) {
	in := recoveryFixture("WORKER_EXIT_NONZERO")
	in.WorkerFailureClass = "WORKER_EXIT_NONZERO"
	in.WorkerDiagnosticExcerpt = "access token could not be refreshed because your refresh token was revoked"
	out := observeFixture(t, in)
	if out.NormalizedClass != "PROVIDER_TRANSIENT" || out.Subtype != "WORKER_AUTH" {
		t.Fatal(out)
	}
}

func TestRecoveryObserverDiagnosticLimitFailsClosed(t *testing.T) {
	in := recoveryFixture("WORKER_TIMEOUT")
	in.WorkerDiagnosticExcerpt = strings.Repeat("x", (64<<10)+1)
	if _, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, in); err == nil || err.Error() != "RECOVERY_DIAGNOSTIC_TOO_LARGE" {
		t.Fatal(err)
	}
}
