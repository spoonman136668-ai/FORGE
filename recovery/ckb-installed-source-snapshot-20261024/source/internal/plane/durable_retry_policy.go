package plane

import (
	"math"
	"strings"
	"time"
)

const durableExternalOrchestratorExhaustionClass = "EXTERNAL_ORCHESTRATOR"
const durableNormalRetryExhaustionClass = "NORMAL_RETRY_BUDGET"

type RetryDecision struct {
	BaseBudget       int    `json:"base_budget"`
	EffectiveBudget  int    `json:"effective_budget"`
	MayRetry         bool   `json:"may_retry"`
	HardStop         bool   `json:"hard_stop"`
	ExhaustionClass  string `json:"exhaustion_class"`
	ExternalHandoff  bool   `json:"external_handoff"`
	FailureRetryable bool   `json:"failure_retryable"`
	WindowActive     bool   `json:"window_active"`
	WindowExpiresAt  string `json:"window_expires_at"`
}

// retryBaseBudget is the sole reader for the ordinary configured attempt cap.
// Optional policy layers may raise EffectiveBudget, but never mutate the base.
func (p *Engine) retryBaseBudget() int {
	base := p.Config.Policy.MaxAttempts
	if base < 1 {
		base = 1
	}
	return base
}

func (p *Engine) retryDecisionNow(id string, attempt int, failureCode string) RetryDecision {
	return p.retryDecisionAt(id, attempt, failureCode, time.Now().UTC())
}

// retryDecisionAt composes the durable base budget with the two accepted,
// explicitly configured compatibility layers: the bounded DZN override and the
// global temporary no-idle window. Both fail closed when disabled, malformed,
// expired, or out of scope. Provider/quota exhaustion always wins and routes to
// the external orchestrator.
func (p *Engine) retryDecisionAt(id string, attempt int, failureCode string, at time.Time) RetryDecision {
	base := p.retryBaseBudget()
	engineeringBudget := base
	if overrideBudget, active := p.effectiveRetryBudget(id, at); active {
		engineeringBudget = overrideBudget
	}

	effective := engineeringBudget
	budgetUsed := attempt
	infrastructureUsed := 0
	if usage, accountingErr := p.attemptBudgetUsage(id, attempt, failureCode); accountingErr == nil && usage.EvidenceBackedAttempts > 0 {
		budgetUsed = usage.EngineeringAttempts
		infrastructureUsed = usage.InfrastructureInterruptions
		neutralLaunches := usage.InfrastructureInterruptions + usage.QuotaExhaustions
		if neutralLaunches > 0 {
			if engineeringBudget > math.MaxInt32-neutralLaunches {
				effective = math.MaxInt32
			} else {
				effective = engineeringBudget + neutralLaunches
			}
		}
	}

	decision := RetryDecision{
		BaseBudget:       base,
		EffectiveBudget:  effective,
		MayRetry:         budgetUsed < engineeringBudget,
		HardStop:         budgetUsed >= engineeringBudget,
		ExhaustionClass:  durableNormalRetryExhaustionClass,
		FailureRetryable: retryPolicyFailureRetryable(failureCode),
	}

	if retryPolicyExternalExhaustion(failureCode) {
		decision.MayRetry = false
		decision.HardStop = true
		decision.ExternalHandoff = true
		decision.ExhaustionClass = durableExternalOrchestratorExhaustionClass
		decision.FailureRetryable = false
		return decision
	}

	if infrastructureUsed >= durableInfrastructureInterruptionBudget {
		decision.MayRetry = false
		decision.HardStop = true
		decision.ExhaustionClass = "INFRASTRUCTURE_INTERRUPTION_BUDGET"
		return decision
	}

	window := p.Config.Policy.TemporaryNoIdleRetryWindow
	if !window.Enabled {
		return decision
	}
	expires, err := time.Parse(time.RFC3339, window.ExpiresAt)
	if err != nil || !expires.After(at.UTC()) {
		return decision
	}

	decision.WindowActive = true
	decision.WindowExpiresAt = expires.UTC().Format(time.RFC3339)
	decision.EffectiveBudget = math.MaxInt32
	decision.MayRetry = true
	decision.HardStop = false
	decision.ExhaustionClass = temporaryNoIdleRetryWindowExhaustionClass
	return decision
}

// retryRecoveryAction centralizes controller recovery vocabulary. An optional
// timestamp preserves deterministic accepted tests without making wall-clock
// injection part of ordinary production callers.
func (p *Engine) retryRecoveryAction(id string, attempt int, failureCode, queueReason string, atOpt ...time.Time) (string, RetryDecision) {
	at := time.Now().UTC()
	if len(atOpt) > 0 {
		at = atOpt[0].UTC()
	}
	decision := p.retryDecisionAt(id, attempt, failureCode, at)
	if decision.ExternalHandoff {
		if len(atOpt) > 0 {
			return "external-orchestrator", decision
		}
		return "operator-blocked", decision
	}
	if decision.HardStop {
		return "operator-blocked", decision
	}

	action := "operator-blocked"
	if (failureCode == "WORKER_CANCELLED" && queueReason == "NO_PROGRESS_TIMEOUT") ||
		retryPolicyTransientAuthorityReverifyFailure(failureCode) ||
		retryPolicyGoInfrastructureFailure(failureCode) ||
		failureCode == "WORKER_TIMEOUT" || strings.HasPrefix(failureCode, "CONTROLLER_INTERRUPTED") {
		action = "retry"
	} else if retryPolicyBoundedRepairFailure(failureCode) {
		action = "bounded-repair"
	}
	if decision.WindowActive && decision.FailureRetryable && action == "operator-blocked" {
		action = "retry"
	}
	if !decision.FailureRetryable {
		action = "operator-blocked"
	}
	return action, decision
}

func retryPolicyTransientAuthorityReverifyFailure(code string) bool {
	const prefix = "WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: "
	if !strings.HasPrefix(code, prefix) {
		return false
	}
	cause := strings.TrimSpace(strings.TrimPrefix(code, prefix))
	switch cause {
	case "BRIDGE_GITHUB_UNAVAILABLE",
		"BRIDGE_GITHUB_READ_FAILED",
		"BRIDGE_GITHUB_HTTP_500",
		"BRIDGE_GITHUB_HTTP_502",
		"BRIDGE_GITHUB_HTTP_503",
		"BRIDGE_GITHUB_HTTP_504":
		return true
	default:
		return false
	}
}
func retryPolicyBoundedRepairFailure(code string) bool {
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	switch code {
	case "FOCUSED_TEST_FAILED", "GO_TEST_FAILED", "GO_TEST_ASSERTION_FAILED", "NO_DIFF_PRODUCED", "PLAYWRIGHT_FAILED", "POWERSHELL_ACCEPTANCE_FAILED":
		return true
	}
	return false
}

func retryPolicyExternalExhaustion(code string) bool {
	upper := strings.ToUpper(strings.TrimSpace(code))
	if upper == "" {
		return false
	}
	for _, marker := range []string{
		"CODEX_QUOTA_EXHAUSTED",
		"PROVIDER_QUOTA_EXHAUSTED",
		"QUOTA_EXHAUSTED",
		"RATE_LIMIT_EXHAUSTED",
	} {
		if strings.Contains(upper, marker) {
			return true
		}
	}
	return false
}

func retryPolicyFailureRetryable(code string) bool {
	code = strings.TrimSpace(code)
	if code == "" {
		return true
	}
	if retryPolicyExternalExhaustion(code) {
		return false
	}
	if retryPolicyGoInfrastructureFailure(code) {
		return true
	}
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	if strings.HasPrefix(code, "CONTROLLER_INTERRUPTED") {
		return true
	}
	if strings.HasPrefix(code, "WORKER_CANCELLED: AUTHORITY_REVERIFY_FAILED: ") {
		return retryPolicyTransientAuthorityReverifyFailure(code)
	}
	if code == "RETRY_LIMIT_REACHED" {
		return true
	}
	switch code {
	case "OPERATOR_RETRY_AUTHORIZED",
		preWorkerRetryAuthorizedReason,
		workerCancelRetryAuthorizedReason,
		workerAuthRetryAuthorizedReason,
		"Explicit local authorization",
		"Baseline verified; awaiting dispatch",
		"Worker lease acquired":
		return true
	}
	return retryable(code)
}
