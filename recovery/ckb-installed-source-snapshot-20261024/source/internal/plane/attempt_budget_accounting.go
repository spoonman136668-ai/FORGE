package plane

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const durableInfrastructureInterruptionBudget = 2

type AttemptBudgetUsage struct {
	WorkerLaunches              int `json:"worker_launches"`
	EvidenceBackedAttempts      int `json:"evidence_backed_attempts"`
	EngineeringAttempts         int `json:"engineering_attempts"`
	RepairAttempts              int `json:"repair_attempts"`
	InfrastructureInterruptions int `json:"infrastructure_interruptions"`
	QuotaExhaustions            int `json:"quota_exhaustions"`
}

func normalizedAttemptFailureCode(code string) string {
	code = strings.TrimSpace(code)
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	return code
}

func attemptBudgetClassification(code string) (class string, engineering, repair, infrastructure, quota int, terminal bool) {
	code = normalizedAttemptFailureCode(code)
	if code == "" {
		return "", 0, 0, 0, 0, false
	}
	switch code {
	case "OPERATOR_RETRY_AUTHORIZED",
		preWorkerRetryAuthorizedReason,
		workerCancelRetryAuthorizedReason,
		workerAuthRetryAuthorizedReason,
		codexQuotaRestoredRearmReason,
		"Explicit local authorization",
		"Baseline verified; awaiting dispatch",
		"Worker lease acquired",
		"RETRY_LIMIT_REACHED":
		return "", 0, 0, 0, 0, false
	}
	if retryPolicyExternalExhaustion(code) {
		return "quota_exhaustion", 0, 0, 0, 1, true
	}
	if retryPolicyTransientAuthorityReverifyFailure(code) ||
		strings.HasPrefix(code, "CONTROLLER_INTERRUPTED") ||
		code == "WORKER_TIMEOUT" ||
		strings.HasPrefix(code, "WORKER_CANCELLED: NO_PROGRESS_TIMEOUT") ||
		code == "CODEX_PROVIDER_UNAVAILABLE" ||
		code == "PLAYWRIGHT_UNAVAILABLE" ||
		code == "GO_TEST_TIMEOUT" ||
		code == "GO_TEST_INFRASTRUCTURE_FAILED" ||
		code == "GO_CACHE_ACCESS_FAILED" {
		return "infrastructure_interruption", 0, 0, 1, 0, true
	}
	if retryPolicyBoundedRepairFailure(code) || code == "GO_TEST_ASSERTION_FAILED" {
		return "repair_attempt", 1, 1, 0, 0, true
	}
	return "engineering_attempt", 1, 0, 0, 0, true
}

func explicitQuotaEvidence(raw []byte) bool {
	upper := strings.ToUpper(string(raw))
	return strings.Contains(upper, "CODEX_QUOTA_EXHAUSTED") ||
		strings.Contains(upper, "QUOTA_EXHAUSTED") ||
		strings.Contains(upper, "USAGE_LIMIT") ||
		strings.Contains(upper, "INSUFFICIENT_QUOTA")
}

func (p *Engine) historicalAttemptFailureCode(id string, attempt int) (string, bool) {
	if p == nil || strings.TrimSpace(p.Root) == "" || attempt < 1 {
		return "", false
	}
	evidence := filepath.Join(p.Root, "evidence", id, strconv.Itoa(attempt))
	if raw, err := os.ReadFile(filepath.Join(evidence, "acceptance_result.json")); err == nil {
		var v struct {
			State  string `json:"state"`
			Reason string `json:"reason"`
		}
		if json.Unmarshal(raw, &v) == nil && v.Reason != "" && v.State != "ACCEPTED" {
			return v.Reason, true
		}
	}
	if raw, err := os.ReadFile(filepath.Join(evidence, "worker_exit.json")); err == nil {
		var v struct {
			FailureReason string `json:"failure_reason"`
			FailureClass  string `json:"failure_class"`
		}
		if json.Unmarshal(raw, &v) == nil {
			if v.FailureReason != "" {
				return v.FailureReason, true
			}
			if v.FailureClass != "" {
				return v.FailureClass, true
			}
		}
	}
	handoff := filepath.Join(p.Root, "evidence", "external-handoff", id, strconv.Itoa(attempt)+".json")
	if raw, err := os.ReadFile(handoff); err == nil && explicitQuotaEvidence(raw) {
		return "CODEX_QUOTA_EXHAUSTED", true
	}
	return "", false
}

func (p *Engine) attemptBudgetUsage(id string, upto int, currentFailureCode string) (AttemptBudgetUsage, error) {
	var usage AttemptBudgetUsage
	if p == nil || strings.TrimSpace(p.Root) == "" || upto < 1 {
		return usage, nil
	}
	usage.WorkerLaunches = upto

	currentClass, currentEngineering, currentRepair, currentInfrastructure, currentQuota, currentTerminal :=
		attemptBudgetClassification(currentFailureCode)

	for attempt := 1; attempt <= upto; attempt++ {
		class := ""
		engineering, repair, infrastructure, quota := 0, 0, 0, 0
		terminal := false

		if attempt == upto && currentTerminal {
			class = currentClass
			engineering = currentEngineering
			repair = currentRepair
			infrastructure = currentInfrastructure
			quota = currentQuota
			terminal = true
		} else if code, ok := p.historicalAttemptFailureCode(id, attempt); ok {
			usage.EvidenceBackedAttempts++
			class, engineering, repair, infrastructure, quota, terminal = attemptBudgetClassification(code)
		}

		if !terminal || class == "" {
			// Retroactive credit is evidence-based only. Any launch without
			// explicit terminal evidence consumes one engineering slot.
			engineering = 1
			repair = 0
			infrastructure = 0
			quota = 0
		}

		usage.EngineeringAttempts += engineering
		usage.RepairAttempts += repair
		usage.InfrastructureInterruptions += infrastructure
		usage.QuotaExhaustions += quota
	}
	return usage, nil
}
