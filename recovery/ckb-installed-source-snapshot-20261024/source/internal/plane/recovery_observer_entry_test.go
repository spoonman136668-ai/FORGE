package plane

import "testing"

func TestObserveBlockedWorkDefaultOffCreatesNoRecoveryState(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	if _, err := p.ObserveBlockedWork(RecoveryObserverConfig{}, w.ID); err == nil || err.Error() != "RECOVERY_OBSERVER_DISABLED" {
		t.Fatal(err)
	}
	for _, table := range []string{"blocker_recovery_transactions", "blocker_recovery_decisions"} {
		var n int
		if err := p.Store.DB.QueryRow("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", table).Scan(&n); err != nil {
			t.Fatal(err)
		}
		if n != 0 {
			t.Fatalf("default-off observer created %s", table)
		}
	}
}

func TestObserveBlockedWorkClassifiesWithoutExecutionMutation(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "GO_TEST_FAILED")
	beforeQueue, beforeWork, beforeLeases := tableCounts(t, p.Store.DB)

	out, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if out.State != blockerRecoveryDiagnosing || out.Observation == nil || out.Observation.NormalizedClass != "TEST_FAILURE" {
		t.Fatal(out)
	}
	if out.Observation.AutomaticMutation || out.Observation.AuthorityRequired {
		t.Fatal(out.Observation)
	}

	afterQueue, afterWork, afterLeases := tableCounts(t, p.Store.DB)
	if beforeQueue != afterQueue || beforeWork != afterWork || beforeLeases != afterLeases {
		t.Fatalf("observer mutated execution state: before=%d/%d/%d after=%d/%d/%d", beforeQueue, beforeWork, beforeLeases, afterQueue, afterWork, afterLeases)
	}

	again, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if again.RecoveryID != out.RecoveryID || again.Revision != out.Revision {
		t.Fatalf("duplicate observation was not idempotent: first=%+v second=%+v", out, again)
	}
	var decisions int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_decisions WHERE recovery_id=?", out.RecoveryID).Scan(&decisions); err != nil {
		t.Fatal(err)
	}
	if decisions != 2 {
		t.Fatalf("duplicate observation appended decisions: %d", decisions)
	}
}

func TestObserveBlockedWorkUnknownFailsTowardEscalationOnly(t *testing.T) {
	p, w, _, _ := recoverySnapshotEngineFixture(t, "UNCLASSIFIED_NEW_BLOCKER")
	beforeQueue, beforeWork, beforeLeases := tableCounts(t, p.Store.DB)

	out, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if out.State != blockerRecoveryEscalated || out.Observation == nil || out.Observation.NormalizedClass != "UNKNOWN" || !out.Observation.AuthorityRequired {
		t.Fatal(out)
	}
	afterQueue, afterWork, afterLeases := tableCounts(t, p.Store.DB)
	if beforeQueue != afterQueue || beforeWork != afterWork || beforeLeases != afterLeases {
		t.Fatal("unknown classification mutated authoritative execution state")
	}
}
