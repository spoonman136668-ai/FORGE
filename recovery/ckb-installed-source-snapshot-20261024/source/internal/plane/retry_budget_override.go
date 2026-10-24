package plane

import "time"

const dznRetryOverrideWorkOrderID = "V11110_STAGE_DZN_KTRADE_PAPER_ACCOUNT_EXECUTION_RISK_STATE_R2"
const dznRetryOverrideAbsoluteMax = 6

// RetryBudgetOverride is intentionally singular and DZN-bound. The plane keeps
// its normal global retry ceiling; this record can only extend DZN R2, only to
// the hard cap above, and only until ExpiresAt.
type RetryBudgetOverride struct {
	WorkOrderID string `yaml:"work_order_id"`
	MaxAttempts int    `yaml:"max_attempts"`
	ExpiresAt   string `yaml:"expires_at"`
}

func (p *Engine) effectiveRetryBudget(id string, at time.Time) (int, bool) {
	base := p.Config.Policy.MaxAttempts
	if id != dznRetryOverrideWorkOrderID {
		return base, false
	}
	o := p.Config.Policy.RetryOverride
	if o.WorkOrderID != dznRetryOverrideWorkOrderID || o.MaxAttempts <= base || o.MaxAttempts > dznRetryOverrideAbsoluteMax {
		return base, false
	}
	expires, err := time.Parse(time.RFC3339, o.ExpiresAt)
	if err != nil || !expires.After(at.UTC()) {
		return base, false
	}
	return o.MaxAttempts, true
}

func (p *Engine) retryBudgetState(id string, attempt int, at time.Time) (budget int, overrideActive bool, hardStop bool) {
	budget, overrideActive = p.effectiveRetryBudget(id, at)
	hardStop = overrideActive && attempt >= budget
	return budget, overrideActive, hardStop
}
