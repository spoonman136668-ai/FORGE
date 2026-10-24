package plane

import (
	"strings"
	"testing"
)

func plannedTransactionFixture(t *testing.T, blocker string) BlockerRecoveryTransaction {
	t.Helper()
	snapshot := recoveryFixture(blocker)
	observation, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, snapshot)
	if err != nil {
		t.Fatal(err)
	}
	return BlockerRecoveryTransaction{
		Schema:                     blockerRecoveryTransactionSchema,
		RecoveryID:                 observation.RecoveryID,
		WorkOrderID:                snapshot.WorkOrderID,
		BlockedAttempt:             snapshot.BlockedAttempt,
		State:                      blockerRecoveryDiagnosing,
		Revision:                   2,
		ControllerRecoveryAttempts: 2,
		DiagnosticAttempts:         1,
		Snapshot:                   snapshot,
		Observation:                &observation,
		Created:                    "2026-09-19T00:00:00Z",
		Updated:                    "2026-09-19T00:00:01Z",
	}
}

func TestRecoveryPlannerDeterministicAndNonMutating(t *testing.T) {
	tx := plannedTransactionFixture(t, "GO_TEST_FAILED")
	a, err := PlanRecovery(tx)
	if err != nil {
		t.Fatal(err)
	}
	b, err := PlanRecovery(tx)
	if err != nil {
		t.Fatal(err)
	}
	if a.PlanID != b.PlanID || a.Disposition != b.Disposition || strings.Join(a.Steps, ",") != strings.Join(b.Steps, ",") {
		t.Fatalf("planner not deterministic: %+v %+v", a, b)
	}
	if a.AutomaticMutation || a.RequiresModel || a.ModelRole != "NONE" {
		t.Fatal(a)
	}
	if a.Disposition != "SOURCE_REPAIR_CANDIDATE" || a.RepairDomain != "APPLICATION_SOURCE" {
		t.Fatal(a)
	}
}

func TestRecoveryPlannerHistoricalFamilies(t *testing.T) {
	cases := []struct {
		name        string
		blocker     string
		diagnostic  string
		disposition string
		domain      string
		authority   bool
		outer       bool
	}{
		{"go-test", "GO_TEST_FAILED", "", "SOURCE_REPAIR_CANDIDATE", "APPLICATION_SOURCE", false, false},
		{"source-hygiene", "SOURCE_HYGIENE_FAILED", "", "SOURCE_REPAIR_CANDIDATE", "APPLICATION_SOURCE", false, false},
		{"workspace", "WORKSPACE_MATERIALIZATION_FAILED", "", "WORKSPACE_REPAIR_CANDIDATE", "CONTROLLER_WORKSPACE", false, false},
		{"repo", "REPO_UNAVAILABLE", "", "DETERMINISTIC_RETRY", "INFRASTRUCTURE", false, false},
		{"uac", "WORKER_TIMEOUT", "windows sandbox failed: CreateProcessAsUserW failed", "ENVIRONMENT_REPAIR_CANDIDATE", "CONTROLLER_TOOLING", false, true},
		{"lease", "PLANE_AUTHORITY_LOST", "AUTHORITY_LEASE_NOT_ACQUIRED", "CONTROLLER_REVERIFY", "AUTHORITY", false, false},
		{"quota", "CODEX_QUOTA_EXHAUSTED", "", "WAIT_EXTERNAL_REMEDIATION", "PROVIDER", false, false},
		{"baseline", "BASELINE_MISMATCH", "", "AUTHORITY_ESCALATION", "POLICY", true, false},
		{"scope", "SCOPE_CHANGE_REQUIRED", "", "AUTHORITY_ESCALATION", "POLICY", true, false},
		{"unknown", "SOMETHING_NEW", "", "AUTHORITY_ESCALATION", "POLICY", true, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			tx := plannedTransactionFixture(t, tc.blocker)
			if tc.diagnostic != "" {
				tx.Snapshot.WorkerDiagnosticExcerpt = tc.diagnostic
				observation, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, tx.Snapshot)
				if err != nil {
					t.Fatal(err)
				}
				tx.RecoveryID = observation.RecoveryID
				tx.Observation = &observation
			}
			plan, err := PlanRecovery(tx)
			if err != nil {
				t.Fatal(err)
			}
			if plan.Disposition != tc.disposition || plan.RepairDomain != tc.domain ||
				plan.RequiresAuthorityChange != tc.authority || plan.OuterQualificationRequired != tc.outer {
				t.Fatalf("got %+v", plan)
			}
			if plan.AutomaticMutation || plan.RequiresModel {
				t.Fatal(plan)
			}
		})
	}
}

func TestRecoveryPlannerWorkerAuthDoesNotProposeSourceRepair(t *testing.T) {
	tx := plannedTransactionFixture(t, "WORKER_EXIT_NONZERO")
	tx.Snapshot.WorkerDiagnosticExcerpt = "refresh token was revoked"
	observation, err := ObserveRecovery(RecoveryObserverConfig{Enabled: true}, tx.Snapshot)
	if err != nil {
		t.Fatal(err)
	}
	tx.RecoveryID = observation.RecoveryID
	tx.Observation = &observation

	plan, err := PlanRecovery(tx)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Disposition != "WAIT_EXTERNAL_REMEDIATION" || plan.RepairDomain != "PROVIDER" {
		t.Fatal(plan)
	}
	for _, step := range plan.Steps {
		if step == "PREPARE_ISOLATED_REPAIR_CANDIDATE" {
			t.Fatal("worker auth outage incorrectly proposed source repair")
		}
	}
}

func TestRecoveryPlannerRejectsStaleObservationBinding(t *testing.T) {
	tx := plannedTransactionFixture(t, "GO_TEST_FAILED")
	tx.Snapshot.EvidenceManifestSHA256 = strings.Repeat("9", 64)
	if _, err := PlanRecovery(tx); err == nil || err.Error() != "RECOVERY_PLAN_STALE_OBSERVATION" {
		t.Fatal(err)
	}
}

func TestRecoveryPlannerRejectsObservationFromDifferentRecovery(t *testing.T) {
	tx := plannedTransactionFixture(t, "GO_TEST_FAILED")
	tx.Observation.RecoveryID = strings.Repeat("8", 64)
	if _, err := PlanRecovery(tx); err == nil || err.Error() != "RECOVERY_PLAN_STALE_OBSERVATION" {
		t.Fatal(err)
	}
}

func TestRecoveryPlanValidatorRejectsMutationAndModelAuthority(t *testing.T) {
	plan, err := PlanRecovery(plannedTransactionFixture(t, "GO_TEST_FAILED"))
	if err != nil {
		t.Fatal(err)
	}
	plan.AutomaticMutation = true
	if err = validateRecoveryPlan(plan); err == nil || err.Error() != "RECOVERY_PLAN_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
	plan.AutomaticMutation = false
	plan.RequiresModel = true
	plan.ModelRole = "NEMOTRON"
	if err = validateRecoveryPlan(plan); err == nil || err.Error() != "RECOVERY_PLAN_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
}

func TestRecoveryPlanValidatorRejectsFreeFormStep(t *testing.T) {
	plan, err := PlanRecovery(plannedTransactionFixture(t, "GO_TEST_FAILED"))
	if err != nil {
		t.Fatal(err)
	}
	plan.Steps = []string{"powershell -Command do-anything"}
	if err = validateRecoveryPlan(plan); err == nil || err.Error() != "RECOVERY_PLAN_STEP_INVALID" {
		t.Fatal(err)
	}
}
