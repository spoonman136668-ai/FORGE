package plane

import (
	"errors"
	"testing"
)

func classifiedRecoveryFixture(t *testing.T, blocker string) (*Engine, BlockerRecoveryTransaction) {
	t.Helper()
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	pending, err := createBlockerRecoveryPending(
		RecoveryObserverConfig{Enabled: true},
		p.Store.DB,
		recoveryFixture(blocker),
	)
	if err != nil {
		t.Fatal(err)
	}
	classified, err := classifyBlockerRecoveryPending(
		RecoveryObserverConfig{Enabled: true},
		p.Store.DB,
		pending.RecoveryID,
	)
	if err != nil {
		t.Fatal(err)
	}
	return p, classified
}

func TestRecoveryPlannerStoreDefaultOffCreatesNoTable(t *testing.T) {
	p, classified := classifiedRecoveryFixture(t, "GO_TEST_FAILED")
	if _, err := PrepareRecoveryPlan(RecoveryPlannerConfig{}, p.Store.DB, classified.RecoveryID); !errors.Is(err, errRecoveryPlannerDisabled) {
		t.Fatal(err)
	}
	var n int
	if err := p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='blocker_recovery_plans'",
	).Scan(&n); err != nil {
		t.Fatal(err)
	}
	if n != 0 {
		t.Fatal("default-off planner created durable state")
	}
}

func TestRecoveryPlannerStorePersistsOneIdempotentPlan(t *testing.T) {
	p, classified := classifiedRecoveryFixture(t, "GO_TEST_FAILED")
	beforeQueue, beforeWork, beforeLeases := tableCounts(t, p.Store.DB)

	cfg := RecoveryPlannerConfig{Enabled: true}
	first, err := PrepareRecoveryPlan(cfg, p.Store.DB, classified.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	second, err := PrepareRecoveryPlan(cfg, p.Store.DB, classified.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	if first.PlanID != second.PlanID || first.Disposition != "SOURCE_REPAIR_CANDIDATE" {
		t.Fatalf("%+v %+v", first, second)
	}
	var plans int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_plans").Scan(&plans); err != nil || plans != 1 {
		t.Fatal(plans, err)
	}

	afterQueue, afterWork, afterLeases := tableCounts(t, p.Store.DB)
	if beforeQueue != afterQueue || beforeWork != afterWork || beforeLeases != afterLeases {
		t.Fatal("planner mutated authoritative execution tables")
	}
}

func TestRecoveryPlannerStorePersistsAuthorityEscalationWithoutAuthorityMutation(t *testing.T) {
	p, classified := classifiedRecoveryFixture(t, "SCOPE_CHANGE_REQUIRED")
	before := p.setting("autonomy_generation")

	plan, err := PrepareRecoveryPlan(
		RecoveryPlannerConfig{Enabled: true},
		p.Store.DB,
		classified.RecoveryID,
	)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Disposition != "AUTHORITY_ESCALATION" || !plan.RequiresAuthorityChange || plan.AutomaticMutation {
		t.Fatal(plan)
	}
	if after := p.setting("autonomy_generation"); after != before {
		t.Fatalf("planner changed authority generation: %q -> %q", before, after)
	}
}

func TestRecoveryPlannerStoreRejectsCorruptPersistedPlan(t *testing.T) {
	p, classified := classifiedRecoveryFixture(t, "GO_TEST_FAILED")
	cfg := RecoveryPlannerConfig{Enabled: true}
	plan, err := PrepareRecoveryPlan(cfg, p.Store.DB, classified.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec(
		"UPDATE blocker_recovery_plans SET raw=? WHERE recovery_id=?",
		[]byte("{}"), plan.RecoveryID,
	); err != nil {
		t.Fatal(err)
	}
	if _, err = PrepareRecoveryPlan(cfg, p.Store.DB, classified.RecoveryID); err == nil || err.Error() != "RECOVERY_PLAN_STATE_CORRUPT" {
		t.Fatal(err)
	}
}
