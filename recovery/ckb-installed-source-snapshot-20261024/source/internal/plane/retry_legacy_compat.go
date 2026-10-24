package plane

import "time"

// Compatibility surface for accepted live callers/tests. Runtime authority is
// retryDecisionAt/retryDecisionNow in durable_retry_policy.go.
func (p *Engine) retryDecision(id string, attempt int, failureCode string, at time.Time) RetryDecision {
	return p.retryDecisionAt(id, attempt, failureCode, at)
}
