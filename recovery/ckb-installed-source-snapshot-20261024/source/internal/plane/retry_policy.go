package plane

import (
	"math"
	"strings"
	"time"
)

const temporaryNoIdleRetryWindowExhaustionClass = "TEMPORARY_NO_IDLE_WINDOW"
const externalOrchestratorExhaustionClass = "EXTERNAL_ORCHESTRATOR"
const normalRetryExhaustionClass = "NORMAL_RETRY_BUDGET"

type TemporaryNoIdleRetryWindow struct {
	Enabled   bool   `yaml:"enabled" json:"enabled"`
	ExpiresAt string `yaml:"expires_at" json:"expires_at"`
}

type LegacyRetryDecision struct {
	BaseBudget       int    `json:"base_budget"`
	EffectiveBudget  int    `json:"effective_budget"`
	MayRetry         bool   `json:"may_retry"`
	HardStop         bool   `json:"hard_stop"`
	WindowActive     bool   `json:"window_active"`
	WindowExpiresAt  string `json:"window_expires_at,omitempty"`
	ExhaustionClass  string `json:"exhaustion_class"`
	ExternalHandoff  bool   `json:"external_handoff"`
	FailureRetryable bool   `json:"failure_retryable"`
}

// legacyRetryBaseBudget is the sole reader of the configured ordinary attempt budget.
// Qualification/profile loops and explicit quota continuation intentionally use
// this base budget rather than the temporary no-idle effective ceiling.
func (p *Engine) legacyRetryBaseBudget() int {
	base := p.retryBaseBudget()
	if base < 1 {
		base = 1
	}
	return base
}

func (p *Engine) legacyRetryDecisionNow(id string, attempt int, failureCode string) LegacyRetryDecision {
	return p.legacyRetryDecision(id, attempt, failureCode, time.Now().UTC())
}

// retryEffectiveBudgetNow projects only the current count policy for status
// reporting. It deliberately has no work-order dependency: the temporary
// no-idle window is global count policy, while per-failure quota/external
// handoff classification remains owned by legacyRetryDecision at behavioral seams.
func (p *Engine) retryEffectiveBudgetNow() int {
	return p.legacyRetryDecision("", 0, "", time.Now().UTC()).EffectiveBudget
}

// legacyRetryDecision is the single count/exhaustion policy used by retry
// authorization, readiness, leasing, post-worker classification and recovery
// scheduling. It does not bypass source authority, operator authorization,
// queue hash integrity, dependency checks, lease ownership, accepted-ref
// protection, or runtime/live-trading boundaries.
//
// During an active temporary no-idle window, count exhaustion is disabled by
// using a very high lease ceiling. Wall-clock expiry remains authoritative: as
// soon as ExpiresAt is reached, the normal configured budget applies again
// without a config rewrite or controller restart.
func (p *Engine) legacyRetryDecision(id string, attempt int, failureCode string, at time.Time) LegacyRetryDecision {
	base := p.legacyRetryBaseBudget()
	decision := LegacyRetryDecision{
		BaseBudget:       base,
		EffectiveBudget:  base,
		MayRetry:         attempt < base,
		HardStop:         attempt >= base,
		ExhaustionClass:  normalRetryExhaustionClass,
		FailureRetryable: legacyRetryPolicyFailureRetryable(failureCode),
	}

	if legacyRetryPolicyExternalExhaustion(failureCode) {
		decision.MayRetry = false
		decision.HardStop = true
		decision.ExternalHandoff = true
		decision.ExhaustionClass = externalOrchestratorExhaustionClass
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

// legacyRetryRecoveryAction keeps the existing controller recovery vocabulary. The
// temporary window changes only ordinary retryable failures that would
// otherwise be operator-blocked into the controller's existing RETRY_WAIT
// path. Deterministic-test failures continue through bounded-repair, and
// provider/quota exhaustion never enters generic retry.
func (p *Engine) legacyRetryRecoveryAction(id string, attempt int, failureCode, queueReason string, at time.Time) (string, LegacyRetryDecision) {
	decision := p.legacyRetryDecision(id, attempt, failureCode, at)
	if decision.ExternalHandoff {
		return "external-orchestrator", decision
	}

	action := "operator-blocked"
	if (failureCode == "WORKER_CANCELLED" && queueReason == "NO_PROGRESS_TIMEOUT") ||
		failureCode == "WORKER_TIMEOUT" || strings.HasPrefix(failureCode, "CONTROLLER_INTERRUPTED") {
		action = "retry"
	} else if legacyRetryPolicyBoundedRepairFailure(failureCode) {
		action = "bounded-repair"
	}

	if decision.WindowActive && decision.FailureRetryable && action == "operator-blocked" {
		action = "retry"
	}
	return action, decision
}

func legacyRetryPolicyBoundedRepairFailure(code string) bool {
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	switch code {
	case "FOCUSED_TEST_FAILED", "GO_TEST_FAILED", "NO_DIFF_PRODUCED", "PLAYWRIGHT_FAILED", "POWERSHELL_ACCEPTANCE_FAILED":
		return true
	}
	return false
}

func legacyRetryPolicyExternalExhaustion(code string) bool {
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

func legacyRetryPolicyFailureRetryable(code string) bool {
	code = strings.TrimSpace(code)
	if code == "" {
		// Ready/Dispatch may ask only for the count policy.
		return true
	}
	if legacyRetryPolicyExternalExhaustion(code) {
		return false
	}
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	if code == "RETRY_LIMIT_REACHED" {
		// A count-only false start has no underlying failure class left in the
		// work-order reason. Explicit source/operator authorization is still
		// required before this can be retried.
		return true
	}
	switch code {
	case "OPERATOR_RETRY_AUTHORIZED",
		preWorkerRetryAuthorizedReason,
		workerCancelRetryAuthorizedReason,
		"Explicit local authorization",
		"Baseline verified; awaiting dispatch",
		"Worker lease acquired":
		return true
	}
	return retryable(code)
}
