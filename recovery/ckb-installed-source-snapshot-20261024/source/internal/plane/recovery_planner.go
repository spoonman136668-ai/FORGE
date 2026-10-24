package plane

import (
	"encoding/json"
	"errors"
	"strings"
)

const recoveryPlanSchema = "ckb-plane.recovery-plan.v1"
const recoveryPlannerPolicyVersion = "native-blocker-resolver-r1-stage4"

type RecoveryPlan struct {
	Schema                     string   `json:"schema"`
	PlannerPolicyVersion       string   `json:"planner_policy_version"`
	PlanID                     string   `json:"plan_id"`
	RecoveryID                 string   `json:"recovery_id"`
	ObservationPolicyVersion   string   `json:"observation_policy_version"`
	EvidenceManifestSHA256     string   `json:"evidence_manifest_sha256"`
	NormalizedClass            string   `json:"normalized_class"`
	Subtype                    string   `json:"subtype,omitempty"`
	Disposition                string   `json:"disposition"`
	RepairDomain               string   `json:"repair_domain"`
	Steps                      []string `json:"steps"`
	RequiresAuthorityChange    bool     `json:"requires_authority_change"`
	RequiresModel              bool     `json:"requires_model"`
	ModelRole                  string   `json:"model_role"`
	OuterQualificationRequired bool     `json:"outer_qualification_required"`
	AutomaticMutation          bool     `json:"automatic_mutation"`
	Reason                     string   `json:"reason"`
}

type recoveryPlanIdentity struct {
	PlannerPolicyVersion     string `json:"planner_policy_version"`
	RecoveryID               string `json:"recovery_id"`
	ObservationPolicyVersion string `json:"observation_policy_version"`
	EvidenceManifestSHA256   string `json:"evidence_manifest_sha256"`
	NormalizedClass          string `json:"normalized_class"`
	Subtype                  string `json:"subtype,omitempty"`
	Disposition              string `json:"disposition"`
	RepairDomain             string `json:"repair_domain"`
}

func PlanRecovery(v BlockerRecoveryTransaction) (RecoveryPlan, error) {
	var out RecoveryPlan
	if v.Schema != blockerRecoveryTransactionSchema || v.RecoveryID == "" || v.Observation == nil {
		return out, errors.New("RECOVERY_PLAN_REQUIRES_CLASSIFIED_TRANSACTION")
	}
	if v.Observation.RecoveryID != v.RecoveryID ||
		v.Observation.EvidenceManifestSHA256 != v.Snapshot.EvidenceManifestSHA256 ||
		v.Observation.PolicyVersion != recoveryObserverPolicyVersion {
		return out, errors.New("RECOVERY_PLAN_STALE_OBSERVATION")
	}
	if err := validateRecoveryEvidence(v.Snapshot); err != nil {
		return out, err
	}

	disposition, domain, steps, authority, outerQualification, reason := deterministicRecoveryPlan(*v.Observation)
	id := recoveryPlanIdentity{
		PlannerPolicyVersion:     recoveryPlannerPolicyVersion,
		RecoveryID:               v.RecoveryID,
		ObservationPolicyVersion: v.Observation.PolicyVersion,
		EvidenceManifestSHA256:   v.Snapshot.EvidenceManifestSHA256,
		NormalizedClass:          v.Observation.NormalizedClass,
		Subtype:                  v.Observation.Subtype,
		Disposition:              disposition,
		RepairDomain:             domain,
	}
	raw, err := json.Marshal(id)
	if err != nil {
		return out, err
	}
	out = RecoveryPlan{
		Schema:                     recoveryPlanSchema,
		PlannerPolicyVersion:       recoveryPlannerPolicyVersion,
		PlanID:                     digest(raw),
		RecoveryID:                 v.RecoveryID,
		ObservationPolicyVersion:   v.Observation.PolicyVersion,
		EvidenceManifestSHA256:     v.Snapshot.EvidenceManifestSHA256,
		NormalizedClass:            v.Observation.NormalizedClass,
		Subtype:                    v.Observation.Subtype,
		Disposition:                disposition,
		RepairDomain:               domain,
		Steps:                      append([]string(nil), steps...),
		RequiresAuthorityChange:    authority,
		RequiresModel:              false,
		ModelRole:                  "NONE",
		OuterQualificationRequired: outerQualification,
		AutomaticMutation:          false,
		Reason:                     reason,
	}
	return out, validateRecoveryPlan(out)
}

func deterministicRecoveryPlan(o RecoveryObservation) (disposition, domain string, steps []string, authority, outerQualification bool, reason string) {
	class := strings.TrimSpace(o.NormalizedClass)
	subtype := strings.TrimSpace(o.Subtype)

	if o.AuthorityRequired {
		return "AUTHORITY_ESCALATION", "POLICY", []string{"PREPARE_OPERATOR_DECISION_PACKET"}, true, false,
			"Observation requires authority beyond the existing immutable recovery envelope."
	}

	switch class {
	case "TEST_FAILURE", "COMPILE_FAILURE", "ACCEPTANCE_FAILURE", "SOURCE_HYGIENE", "FORBIDDEN_PATH", "NO_DIFF":
		return "SOURCE_REPAIR_CANDIDATE", "APPLICATION_SOURCE",
			[]string{"PREPARE_ISOLATED_REPAIR_CANDIDATE", "RUN_DETERMINISTIC_RECOVERY_VALIDATION"},
			false, false, "Prepare a bounded candidate under the original work-order authority; deterministic validation remains the judge."

	case "ENVIRONMENT_DEFECT":
		return "ENVIRONMENT_REPAIR_CANDIDATE", "CONTROLLER_TOOLING",
			[]string{"PREPARE_ISOLATED_ENVIRONMENT_REPAIR", "RUN_DETERMINISTIC_RECOVERY_VALIDATION"},
			false, true, "Environment/controller-tooling repair is proposed only in isolation and requires outer qualification before any live controller change."

	case "WORKSPACE_DEFECT":
		return "WORKSPACE_REPAIR_CANDIDATE", "CONTROLLER_WORKSPACE",
			[]string{"PREPARE_ISOLATED_WORKSPACE_REPAIR", "RUN_DETERMINISTIC_RECOVERY_VALIDATION"},
			false, false, "Repair workspace/materialization state without changing the immutable work order."

	case "WORKER_NO_PROGRESS":
		return "WORKER_RETRY_STRATEGY", "WORKER_EXECUTION",
			[]string{"DIAGNOSE_NO_PROGRESS", "PREPARE_BOUNDED_WORKER_RETRY_STRATEGY"},
			false, false, "Investigate bounded worker progress evidence before proposing a retry."

	case "TRANSIENT_INFRA":
		return "DETERMINISTIC_RETRY", "INFRASTRUCTURE",
			[]string{"REVERIFY_INFRASTRUCTURE", "RETRY_WITH_EXISTING_AUTHORITY"},
			false, false, "Transient infrastructure recovery may reuse existing authority only after deterministic revalidation."

	case "PROVIDER_TRANSIENT":
		if subtype == "WORKER_AUTH" {
			return "WAIT_EXTERNAL_REMEDIATION", "PROVIDER",
				[]string{"WAIT_FOR_WORKER_AUTH_REMEDIATION", "REVERIFY_WORKER_AUTH"},
				false, false, "Worker authentication is an external remediation boundary; source repair is not appropriate."
		}
		return "WAIT_EXTERNAL_REMEDIATION", "PROVIDER",
			[]string{"WAIT_FOR_PROVIDER_RECOVERY", "REVERIFY_PROVIDER_AVAILABILITY"},
			false, false, "Provider availability/quota must recover before the original work can continue."

	case "AUTHORITY_MISMATCH":
		if subtype == "AUTHORITY_LEASE" {
			return "CONTROLLER_REVERIFY", "AUTHORITY",
				[]string{"REVERIFY_EXISTING_PLANE_AUTHORITY", "RECONCILE_ORIGINAL_BLOCKER"},
				false, false, "Reverify existing authority; do not change authority generation or ownership."
		}
		return "AUTHORITY_ESCALATION", "AUTHORITY",
			[]string{"PREPARE_OPERATOR_DECISION_PACKET"},
			true, false, "Authority ownership/fencing cannot be changed by recovery."

	case "DEPENDENCY_BLOCK":
		return "WAIT_DEPENDENCY", "DEPENDENCY",
			[]string{"RECHECK_DECLARED_DEPENDENCY"},
			false, false, "Wait for the declared dependency to become satisfied; do not bypass dependency semantics."

	case "BASELINE_DEFECT", "SCOPE_CHANGE_REQUIRED", "POLICY_BOUNDARY", "UNKNOWN":
		return "AUTHORITY_ESCALATION", "POLICY",
			[]string{"PREPARE_OPERATOR_DECISION_PACKET"},
			true, false, "Recovery cannot alter baseline, scope, policy, or unknown authority semantics autonomously."
	}

	return "AUTHORITY_ESCALATION", "POLICY",
		[]string{"PREPARE_OPERATOR_DECISION_PACKET"},
		true, false, "Unrecognized recovery class fails toward escalation."
}

func validateRecoveryPlan(p RecoveryPlan) error {
	if p.Schema != recoveryPlanSchema || p.PlannerPolicyVersion != recoveryPlannerPolicyVersion ||
		!hexDigest(p.PlanID, 64) || !hexDigest(p.RecoveryID, 64) || !hexDigest(p.EvidenceManifestSHA256, 64) {
		return errors.New("RECOVERY_PLAN_INVALID")
	}
	if p.ObservationPolicyVersion != recoveryObserverPolicyVersion || p.NormalizedClass == "" ||
		p.Disposition == "" || p.RepairDomain == "" || len(p.Steps) == 0 || p.Reason == "" {
		return errors.New("RECOVERY_PLAN_INVALID")
	}
	if p.AutomaticMutation || p.RequiresModel || p.ModelRole != "NONE" {
		return errors.New("RECOVERY_PLAN_AUTHORITY_INVALID")
	}
	for _, step := range p.Steps {
		switch step {
		case "PREPARE_OPERATOR_DECISION_PACKET",
			"PREPARE_ISOLATED_REPAIR_CANDIDATE",
			"PREPARE_ISOLATED_ENVIRONMENT_REPAIR",
			"PREPARE_ISOLATED_WORKSPACE_REPAIR",
			"RUN_DETERMINISTIC_RECOVERY_VALIDATION",
			"DIAGNOSE_NO_PROGRESS",
			"PREPARE_BOUNDED_WORKER_RETRY_STRATEGY",
			"REVERIFY_INFRASTRUCTURE",
			"RETRY_WITH_EXISTING_AUTHORITY",
			"WAIT_FOR_WORKER_AUTH_REMEDIATION",
			"REVERIFY_WORKER_AUTH",
			"WAIT_FOR_PROVIDER_RECOVERY",
			"REVERIFY_PROVIDER_AVAILABILITY",
			"REVERIFY_EXISTING_PLANE_AUTHORITY",
			"RECONCILE_ORIGINAL_BLOCKER",
			"RECHECK_DECLARED_DEPENDENCY":
		default:
			return errors.New("RECOVERY_PLAN_STEP_INVALID")
		}
	}
	return nil
}
