package plane

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func writeAttemptBudgetEvidence(t *testing.T, p *Engine, id string, attempt int, code string) {
	t.Helper()
	dir := filepath.Join(p.Root, "evidence", id, fmt.Sprint(attempt))
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := writeJSON(filepath.Join(dir, "worker_exit.json"), map[string]any{
		"failure_reason": code,
		"failure_class":  failureClass(code),
	}); err != nil {
		t.Fatal(err)
	}
}

func TestAttemptBudgetQuotaDoesNotConsumeEngineeringBudget(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 3

	d1 := p.retryDecisionNow(w.ID, 1, "CODEX_QUOTA_EXHAUSTED")
	if !d1.ExternalHandoff || !d1.HardStop {
		t.Fatalf("quota decision=%+v", d1)
	}
	usage, err := p.attemptBudgetUsage(w.ID, 1, "CODEX_QUOTA_EXHAUSTED")
	if err != nil {
		t.Fatal(err)
	}
	if usage.WorkerLaunches != 1 || usage.EngineeringAttempts != 0 || usage.QuotaExhaustions != 1 {
		t.Fatalf("usage=%+v", usage)
	}

	writeAttemptBudgetEvidence(t, p, w.ID, 1, "CODEX_QUOTA_EXHAUSTED")
	d2 := p.retryDecisionNow(w.ID, 1, codexQuotaRestoredRearmReason)
	if d2.HardStop || !d2.MayRetry {
		t.Fatalf("restored decision=%+v usage=%+v", d2, usage)
	}
}

func TestAttemptBudgetMonotonicOrdinalCanExceedConfiguredBudget(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 7
	codes := []string{
		"GO_TEST_FAILED",
		"CODEX_QUOTA_EXHAUSTED",
		"GO_TEST_FAILED",
		"GO_TEST_FAILED",
		"CODEX_QUOTA_EXHAUSTED",
		"GO_TEST_FAILED",
		"GO_TEST_FAILED",
	}
	for i, code := range codes {
		writeAttemptBudgetEvidence(t, p, w.ID, i+1, code)
	}
	usage, err := p.attemptBudgetUsage(w.ID, 7, "")
	if err != nil {
		t.Fatal(err)
	}
	if usage.WorkerLaunches != 7 || usage.EngineeringAttempts != 5 || usage.RepairAttempts != 5 || usage.QuotaExhaustions != 2 {
		t.Fatalf("usage=%+v", usage)
	}
	d := p.retryDecisionNow(w.ID, 7, codexQuotaRestoredRearmReason)
	if d.HardStop || !d.MayRetry {
		t.Fatalf("ordinal 7 should retain engineering budget: decision=%+v usage=%+v", d, usage)
	}
	if d.BaseBudget != 7 || d.EffectiveBudget != 9 {
		t.Fatalf("quota-neutral ordinal ceiling=%+v usage=%+v", d, usage)
	}
}

func TestAttemptBudgetDeterministicFailureConsumesExactlyOne(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 3

	_ = p.retryDecisionNow(w.ID, 1, "GO_TEST_FAILED")
	_ = p.retryDecisionNow(w.ID, 1, "GO_TEST_FAILED")
	usage, err := p.attemptBudgetUsage(w.ID, 1, "GO_TEST_FAILED")
	if err != nil {
		t.Fatal(err)
	}
	if usage.EngineeringAttempts != 1 || usage.RepairAttempts != 1 {
		t.Fatalf("duplicate classification consumed extra budget: %+v", usage)
	}
}

func TestAttemptBudgetInfrastructureSeparatelyBounded(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 3
	for n := 1; n <= durableInfrastructureInterruptionBudget; n++ {
		if n > 1 {
			writeAttemptBudgetEvidence(t, p, w.ID, n-1, "WORKER_TIMEOUT")
		}
		d := p.retryDecisionNow(w.ID, n, "WORKER_TIMEOUT")
		if n < durableInfrastructureInterruptionBudget && (d.HardStop || !d.MayRetry) {
			t.Fatalf("infra n=%d decision=%+v", n, d)
		}
		if n == durableInfrastructureInterruptionBudget {
			if !d.HardStop || d.MayRetry {
				t.Fatalf("infra budget must hard-stop at n=%d: %+v", n, d)
			}
			if d.ExhaustionClass != "INFRASTRUCTURE_INTERRUPTION_BUDGET" {
				t.Fatalf("infra exhaustion class=%q decision=%+v", d.ExhaustionClass, d)
			}
		}
	}
	writeAttemptBudgetEvidence(t, p, w.ID, durableInfrastructureInterruptionBudget, "WORKER_TIMEOUT")
	usage, err := p.attemptBudgetUsage(w.ID, durableInfrastructureInterruptionBudget, "")
	if err != nil {
		t.Fatal(err)
	}
	if usage.EngineeringAttempts != 0 || usage.InfrastructureInterruptions != durableInfrastructureInterruptionBudget {
		t.Fatalf("usage=%+v", usage)
	}
}

func TestAttemptBudgetEngineeringLimitAfterNeutralLaunches(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 3

	codes := []string{
		"CODEX_QUOTA_EXHAUSTED",
		"GO_TEST_FAILED",
		"GO_TEST_FAILED",
		"GO_TEST_FAILED",
	}
	for i, code := range codes {
		writeAttemptBudgetEvidence(t, p, w.ID, i+1, code)
	}

	d := p.retryDecisionNow(w.ID, 4, "GO_TEST_FAILED")
	if !d.HardStop || d.MayRetry {
		t.Fatalf("engineering budget must stop after three engineering failures: %+v", d)
	}
	if d.BaseBudget != 3 || d.EffectiveBudget != 4 {
		t.Fatalf("neutral launch must extend ordinal ceiling only: %+v", d)
	}
}

func TestAttemptBudgetLegacyNoHistoryFallsBackToEngineering(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 3

	d := p.retryDecisionNow("NO_HISTORY", 3, "")
	if !d.HardStop || d.MayRetry || d.BaseBudget != 3 || d.EffectiveBudget != 3 {
		t.Fatalf("unknown historical launches must fail closed as engineering: %+v", d)
	}
}

func TestAttemptBudgetNoRuntimeRootFallsBackWithoutAccounting(t *testing.T) {
	p := &Engine{}
	usage, err := p.attemptBudgetUsage("NO_ROOT", 4, "GO_TEST_FAILED")
	if err != nil {
		t.Fatal(err)
	}
	if usage != (AttemptBudgetUsage{}) {
		t.Fatalf("policy-only context must not fabricate accounting: %+v", usage)
	}

	d := p.retryDecisionNow("NO_ROOT", 1, "WORKER_TIMEOUT")
	if d.BaseBudget != 1 || d.EffectiveBudget != 1 || d.MayRetry || !d.HardStop {
		t.Fatalf("policy-only raw-attempt fallback changed: %+v", d)
	}
}

func TestAttemptBudgetExternalHandoffRequiresExplicitQuotaEvidence(t *testing.T) {
	p, w := setup(t)
	path := filepath.Join(p.Root, "evidence", "external-handoff", w.ID, "1.json")
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(`{"kind":"external-handoff","reason":"generic"}`), 0600); err != nil {
		t.Fatal(err)
	}
	usage, err := p.attemptBudgetUsage(w.ID, 1, "")
	if err != nil {
		t.Fatal(err)
	}
	if usage.EngineeringAttempts != 1 || usage.QuotaExhaustions != 0 {
		t.Fatalf("generic handoff must not receive quota credit: %+v", usage)
	}

	if err := os.WriteFile(path, []byte(`{"kind":"external-handoff","reason":"CODEX_QUOTA_EXHAUSTED"}`), 0600); err != nil {
		t.Fatal(err)
	}
	usage, err = p.attemptBudgetUsage(w.ID, 1, "")
	if err != nil {
		t.Fatal(err)
	}
	if usage.EngineeringAttempts != 0 || usage.QuotaExhaustions != 1 {
		t.Fatalf("explicit quota evidence must receive quota credit: %+v", usage)
	}
}

func TestAttemptBudgetCurrentNeutralFailureCannotSelfExpandWithoutPriorEvidence(t *testing.T) {
	p, _ := setup(t)
	p.Config.Policy.MaxAttempts = 3

	before := p.retryDecisionNow("NO_EVIDENCE", 2, "WORKER_TIMEOUT")
	if before.BaseBudget != 3 || before.EffectiveBudget != 3 || !before.MayRetry || before.HardStop {
		t.Fatalf("current neutral failure self-expanded before limit: %+v", before)
	}

	atLimit := p.retryDecisionNow("NO_EVIDENCE", 3, "WORKER_TIMEOUT")
	if atLimit.BaseBudget != 3 || atLimit.EffectiveBudget != 3 || atLimit.MayRetry || !atLimit.HardStop {
		t.Fatalf("current neutral failure self-expanded at limit: %+v", atLimit)
	}
}
