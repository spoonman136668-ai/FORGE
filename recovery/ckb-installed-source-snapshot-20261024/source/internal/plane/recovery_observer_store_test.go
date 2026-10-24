package plane

import (
	"database/sql"
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

func TestBlockerRecoveryObserverStoreIsExplicitAndNamespaced(t *testing.T) {
	p, _ := setup(t)
	for _, table := range []string{"blocker_recovery_transactions", "blocker_recovery_decisions"} {
		var n int
		if err := p.Store.DB.QueryRow("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", table).Scan(&n); err != nil {
			t.Fatal(err)
		}
		if n != 0 {
			t.Fatalf("stage3 table %s existed before explicit initialization", table)
		}
	}
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	var existingRetryTable int
	if err := p.Store.DB.QueryRow("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='recovery_decisions'").Scan(&existingRetryTable); err != nil {
		t.Fatal(err)
	}
	if existingRetryTable != 1 {
		t.Fatal("existing retry recovery_decisions table was lost or renamed")
	}
}

func TestBlockerRecoveryPendingIsIdempotentAndIdentityBound(t *testing.T) {
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	cfg := RecoveryObserverConfig{Enabled: true}
	in := recoveryFixture("GO_TEST_FAILED")
	first, err := createBlockerRecoveryPending(cfg, p.Store.DB, in)
	if err != nil {
		t.Fatal(err)
	}
	second, err := createBlockerRecoveryPending(cfg, p.Store.DB, in)
	if err != nil {
		t.Fatal(err)
	}
	if first.RecoveryID != second.RecoveryID || second.Revision != 1 || second.State != blockerRecoveryPending {
		t.Fatalf("%+v %+v", first, second)
	}
	var rows int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_transactions").Scan(&rows); err != nil || rows != 1 {
		t.Fatal(rows, err)
	}
	in.QueueInputSHA256 = strings.Repeat("9", 64)
	if _, err = createBlockerRecoveryPending(cfg, p.Store.DB, in); err == nil || err.Error() != "RECOVERY_IDENTITY_CONFLICT" {
		t.Fatal(err)
	}
}

func TestBlockerRecoveryClassificationPersistsWithoutMutatingQueueOrWorkOrder(t *testing.T) {
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	beforeQueue, beforeWork, beforeLeases := tableCounts(t, p.Store.DB)
	cfg := RecoveryObserverConfig{Enabled: true}
	pending, err := createBlockerRecoveryPending(cfg, p.Store.DB, recoveryFixture("RETRY_LIMIT_REACHED: GO_TEST_FAILED"))
	if err != nil {
		t.Fatal(err)
	}
	classified, err := classifyBlockerRecoveryPending(cfg, p.Store.DB, pending.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	if classified.State != blockerRecoveryDiagnosing || classified.Revision != 2 || classified.DiagnosticAttempts != 1 || classified.ControllerRecoveryAttempts != 2 {
		t.Fatal(classified)
	}
	if classified.Observation == nil || classified.Observation.NormalizedClass != "TEST_FAILURE" || classified.Observation.AutomaticMutation {
		t.Fatal(classified.Observation)
	}
	again, err := classifyBlockerRecoveryPending(cfg, p.Store.DB, pending.RecoveryID)
	if err != nil || again.Revision != classified.Revision {
		t.Fatal(again, err)
	}
	afterQueue, afterWork, afterLeases := tableCounts(t, p.Store.DB)
	if beforeQueue != afterQueue || beforeWork != afterWork || beforeLeases != afterLeases {
		t.Fatalf("observer mutated authoritative execution tables: before=%v/%v/%v after=%v/%v/%v", beforeQueue, beforeWork, beforeLeases, afterQueue, afterWork, afterLeases)
	}
	var decisions int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_decisions WHERE recovery_id=?", pending.RecoveryID).Scan(&decisions); err != nil || decisions != 2 {
		t.Fatal(decisions, err)
	}
}

func TestBlockerRecoveryAuthorityBoundaryEscalatesOnlyRecoveryState(t *testing.T) {
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	cfg := RecoveryObserverConfig{Enabled: true}
	pending, err := createBlockerRecoveryPending(cfg, p.Store.DB, recoveryFixture("SCOPE_CHANGE_REQUIRED"))
	if err != nil {
		t.Fatal(err)
	}
	out, err := classifyBlockerRecoveryPending(cfg, p.Store.DB, pending.RecoveryID)
	if err != nil {
		t.Fatal(err)
	}
	if out.State != blockerRecoveryEscalated || out.Observation == nil || !out.Observation.AuthorityRequired {
		t.Fatal(out)
	}
}

func TestBlockerRecoveryStoreFailsClosedOnCorruptRawState(t *testing.T) {
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	cfg := RecoveryObserverConfig{Enabled: true}
	pending, err := createBlockerRecoveryPending(cfg, p.Store.DB, recoveryFixture("GO_TEST_FAILED"))
	if err != nil {
		t.Fatal(err)
	}
	var raw []byte
	if err = p.Store.DB.QueryRow("SELECT raw FROM blocker_recovery_transactions WHERE recovery_id=?", pending.RecoveryID).Scan(&raw); err != nil {
		t.Fatal(err)
	}
	var state map[string]any
	if err = json.Unmarshal(raw, &state); err != nil {
		t.Fatal(err)
	}
	state["revision"] = float64(999)
	raw, _ = json.Marshal(state)
	if _, err = p.Store.DB.Exec("UPDATE blocker_recovery_transactions SET raw=? WHERE recovery_id=?", raw, pending.RecoveryID); err != nil {
		t.Fatal(err)
	}
	if _, err = getBlockerRecoveryTransaction(p.Store.DB, pending.RecoveryID); err == nil || err.Error() != "RECOVERY_STATE_CORRUPT" {
		t.Fatal(err)
	}
}

func TestBlockerRecoveryObserverStoreDefaultOff(t *testing.T) {
	p, _ := setup(t)
	if err := initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	if _, err := createBlockerRecoveryPending(RecoveryObserverConfig{}, p.Store.DB, recoveryFixture("GO_TEST_FAILED")); !errors.Is(err, errRecoveryObserverDisabled) {
		t.Fatal(err)
	}
	var n int
	if err := p.Store.DB.QueryRow("SELECT count(*) FROM blocker_recovery_transactions").Scan(&n); err != nil || n != 0 {
		t.Fatal(n, err)
	}
}

func tableCounts(t *testing.T, db *sql.DB) (queue, work, leases int) {
	t.Helper()
	for query, dst := range map[string]*int{
		"SELECT count(*) FROM queue_items":    &queue,
		"SELECT count(*) FROM work_orders":    &work,
		"SELECT count(*) FROM worker_leases":  &leases,
	} {
		if err := db.QueryRow(query).Scan(dst); err != nil {
			t.Fatal(err)
		}
	}
	return queue, work, leases
}
