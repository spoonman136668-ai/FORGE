package plane

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func writeAuthorityReplayChecks(t *testing.T, dir string, checks []Check) Job {
	t.Helper()
	raw, err := json.Marshal(checks)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(dir, "acceptance_checks.json"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	return Job{Evidence: dir}
}

func TestTransientAuthorityReplayEvidence(t *testing.T) {
	dir := t.TempDir()
	j := writeAuthorityReplayChecks(t, dir, []Check{
		{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "BRIDGE_GITHUB_UNAVAILABLE"},
	})
	if err := transientAuthorityReplayEvidence(j); err != nil {
		t.Fatalf("expected transient authority evidence to be replayable: %v", err)
	}
}

func TestAcceptanceSchedulerCancellationEvidence(t *testing.T) {
	dir := t.TempDir()
	j := writeAuthorityReplayChecks(t, dir, []Check{
		{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "context canceled"},
		{Name: "BASELINE_MISMATCH", Pass: true, Detail: "Exact authoritative baseline SHA"},
		{Name: "ACCEPTANCE_CANCELLED", Pass: false, Detail: "context canceled"},
	})
	if err := transientAuthorityReplayEvidence(j); err != nil {
		t.Fatalf("expected isolated scheduler cancellation to be replayable after scheduler repair: %v", err)
	}
}

func TestTransientAuthorityReplayEvidenceRejectsUnsafeOrAmbiguous(t *testing.T) {
	for name, checks := range map[string][]Check{
		"identity": {
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "AUTHORITY_REPOSITORY_MISMATCH"},
		},
		"auth": {
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "BRIDGE_GITHUB_HTTP_401"},
		},
		"ambiguous": {
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "BRIDGE_GITHUB_UNAVAILABLE"},
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "BRIDGE_GITHUB_HTTP_503"},
		},
		"cancel_without_pair": {
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "context canceled"},
		},
		"cancel_with_other_failure": {
			{Name: "PLANE_AUTHORITY_LOST", Pass: false, Detail: "context canceled"},
			{Name: "ACCEPTANCE_CANCELLED", Pass: false, Detail: "context canceled"},
			{Name: "GO_TEST_FAILED", Pass: false, Detail: "unrelated failure"},
		},
		"missing": {},
	} {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			j := writeAuthorityReplayChecks(t, dir, checks)
			if err := transientAuthorityReplayEvidence(j); err == nil {
				t.Fatal("expected replay evidence rejection")
			}
		})
	}
}

func TestAcceptanceReplayReasonAllowsAuthorityLoss(t *testing.T) {
	if !acceptanceReplayReasonAllowed("PLANE_AUTHORITY_LOST") {
		t.Fatal("authority loss reason must reach sealed-evidence validation")
	}
}
