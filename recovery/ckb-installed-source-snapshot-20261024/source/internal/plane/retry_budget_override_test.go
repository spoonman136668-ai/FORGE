package plane

import (
	"testing"
	"time"
)

func TestDZNRetryBudgetOverrideExactActive(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 6,
		ExpiresAt:   "2026-09-16T17:00:00Z",
	}
	got, active := p.effectiveRetryBudget(dznRetryOverrideWorkOrderID, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 6 || !active {
		t.Fatalf("active DZN override = (%d,%v), want (6,true)", got, active)
	}
}

func TestDZNRetryBudgetOverrideOtherWorkOrderRemainsCapped(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 6,
		ExpiresAt:   "2026-09-16T17:00:00Z",
	}
	got, active := p.effectiveRetryBudget("V11110_STAGE_OTHER", time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 3 || active {
		t.Fatalf("other work order override = (%d,%v), want (3,false)", got, active)
	}
}

func TestDZNRetryBudgetOverrideExpiredFailsClosed(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 6,
		ExpiresAt:   "2026-09-15T17:00:00Z",
	}
	got, active := p.effectiveRetryBudget(dznRetryOverrideWorkOrderID, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 3 || active {
		t.Fatalf("expired override = (%d,%v), want (3,false)", got, active)
	}
}

func TestDZNRetryBudgetOverrideMalformedExpiryFailsClosed(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 6,
		ExpiresAt:   "not-a-time",
	}
	got, active := p.effectiveRetryBudget(dznRetryOverrideWorkOrderID, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 3 || active {
		t.Fatalf("malformed override = (%d,%v), want (3,false)", got, active)
	}
}

func TestDZNRetryBudgetOverrideOverAbsoluteCapFailsClosed(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 7,
		ExpiresAt:   "2026-09-16T17:00:00Z",
	}
	got, active := p.effectiveRetryBudget(dznRetryOverrideWorkOrderID, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 3 || active {
		t.Fatalf("over-cap override = (%d,%v), want (3,false)", got, active)
	}
}

func TestDZNRetryBudgetOverrideWrongConfiguredIDFailsClosed(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: "V11110_STAGE_OTHER",
		MaxAttempts: 6,
		ExpiresAt:   "2026-09-16T17:00:00Z",
	}
	got, active := p.effectiveRetryBudget(dznRetryOverrideWorkOrderID, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if got != 3 || active {
		t.Fatalf("wrong-ID override = (%d,%v), want (3,false)", got, active)
	}
}

func TestDZNRetryBudgetOverrideHardStopsAtSix(t *testing.T) {
	p := &Engine{}
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.RetryOverride = RetryBudgetOverride{
		WorkOrderID: dznRetryOverrideWorkOrderID,
		MaxAttempts: 6,
		ExpiresAt:   "2026-09-16T17:00:00Z",
	}
	budget, active, hardStop := p.retryBudgetState(dznRetryOverrideWorkOrderID, 6, time.Date(2026, 9, 15, 17, 0, 0, 0, time.UTC))
	if budget != 6 || !active || !hardStop {
		t.Fatalf("attempt-six state = (%d,%v,%v), want (6,true,true)", budget, active, hardStop)
	}
}
