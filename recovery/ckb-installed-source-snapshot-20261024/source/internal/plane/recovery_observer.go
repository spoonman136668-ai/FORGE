package plane

import (
	"encoding/json"
	"errors"
	"sort"
	"strings"
)

const recoveryObservationSchema = "ckb-plane.recovery-observation.v1"
const recoveryObserverPolicyVersion = "native-blocker-resolver-r1-stage3"

var errRecoveryObserverDisabled = errors.New("RECOVERY_OBSERVER_DISABLED")

type RecoveryObserverConfig struct {
	Enabled bool
}

type RecoveryEvidenceSnapshot struct {
	WorkOrderID               string   `json:"work_order_id"`
	BlockedAttempt            int      `json:"blocked_attempt"`
	QueueInputSHA256          string   `json:"queue_input_sha256"`
	WorkOrderSHA256           string   `json:"work_order_sha256"`
	AuthorizationContractSHA  string   `json:"authorization_contract_sha256"`
	BaselineRef               string   `json:"baseline_ref"`
	BaselineSHA               string   `json:"baseline_sha"`
	ObjectiveID               string   `json:"objective_id,omitempty"`
	ObjectiveStage            int      `json:"objective_stage,omitempty"`
	ObjectiveRevision         int64    `json:"objective_revision,omitempty"`
	AuthorityGeneration       int64    `json:"authority_generation"`
	OriginalBlocker           string   `json:"original_blocker"`
	EvidenceManifestSHA256    string   `json:"evidence_manifest_sha256"`
	ChangedFiles              []string `json:"changed_files,omitempty"`
	FailedChecks              []string `json:"failed_checks,omitempty"`
	WorkerFailureClass        string   `json:"worker_failure_class,omitempty"`
	WorkerDiagnosticExcerpt   string   `json:"worker_diagnostic_excerpt,omitempty"`
	ControllerDiagnostic      string   `json:"controller_diagnostic,omitempty"`
}

type RecoveryObservation struct {
	Schema                 string `json:"schema"`
	PolicyVersion          string `json:"policy_version"`
	RecoveryID             string `json:"recovery_id"`
	WorkOrderID            string `json:"work_order_id"`
	BlockedAttempt         int    `json:"blocked_attempt"`
	AuthorityGeneration    int64  `json:"authority_generation"`
	OriginalBlocker        string `json:"original_blocker"`
	NormalizedClass        string `json:"normalized_class"`
	Subtype                string `json:"subtype,omitempty"`
	AuthorityRequired      bool   `json:"authority_required"`
	AutomaticMutation      bool   `json:"automatic_mutation"`
	Reason                 string `json:"reason"`
	EvidenceManifestSHA256 string `json:"evidence_manifest_sha256"`
}

type recoveryIdentity struct {
	PolicyVersion            string `json:"policy_version"`
	WorkOrderID              string `json:"work_order_id"`
	BlockedAttempt           int    `json:"blocked_attempt"`
	QueueInputSHA256         string `json:"queue_input_sha256"`
	WorkOrderSHA256          string `json:"work_order_sha256"`
	AuthorizationContractSHA string `json:"authorization_contract_sha256"`
	BaselineRef              string `json:"baseline_ref"`
	BaselineSHA              string `json:"baseline_sha"`
	ObjectiveID              string `json:"objective_id,omitempty"`
	ObjectiveStage           int    `json:"objective_stage,omitempty"`
	ObjectiveRevision        int64  `json:"objective_revision,omitempty"`
	AuthorityGeneration      int64  `json:"authority_generation"`
	OriginalBlocker          string `json:"original_blocker"`
	EvidenceManifestSHA256   string `json:"evidence_manifest_sha256"`
}

func recoveryIDForEvidence(in RecoveryEvidenceSnapshot) (string, error) {
	if err := validateRecoveryEvidence(in); err != nil {
		return "", err
	}
	id := recoveryIdentity{
		PolicyVersion:            recoveryObserverPolicyVersion,
		WorkOrderID:              in.WorkOrderID,
		BlockedAttempt:           in.BlockedAttempt,
		QueueInputSHA256:         in.QueueInputSHA256,
		WorkOrderSHA256:          in.WorkOrderSHA256,
		AuthorizationContractSHA: in.AuthorizationContractSHA,
		BaselineRef:              in.BaselineRef,
		BaselineSHA:              in.BaselineSHA,
		ObjectiveID:              in.ObjectiveID,
		ObjectiveStage:           in.ObjectiveStage,
		ObjectiveRevision:        in.ObjectiveRevision,
		AuthorityGeneration:      in.AuthorityGeneration,
		OriginalBlocker:          in.OriginalBlocker,
		EvidenceManifestSHA256:   in.EvidenceManifestSHA256,
	}
	raw, err := json.Marshal(id)
	if err != nil {
		return "", err
	}
	return digest(raw), nil
}

func ObserveRecovery(cfg RecoveryObserverConfig, in RecoveryEvidenceSnapshot) (RecoveryObservation, error) {
	if !cfg.Enabled {
		return RecoveryObservation{}, errRecoveryObserverDisabled
	}
	in = canonicalRecoveryEvidence(in)
	recoveryID, err := recoveryIDForEvidence(in)
	if err != nil {
		return RecoveryObservation{}, err
	}
	class, subtype, authority, reason := classifyRecoveryEvidence(in)
	return RecoveryObservation{
		Schema:                 recoveryObservationSchema,
		PolicyVersion:          recoveryObserverPolicyVersion,
		RecoveryID:             recoveryID,
		WorkOrderID:            in.WorkOrderID,
		BlockedAttempt:         in.BlockedAttempt,
		AuthorityGeneration:    in.AuthorityGeneration,
		OriginalBlocker:        in.OriginalBlocker,
		NormalizedClass:        class,
		Subtype:                subtype,
		AuthorityRequired:      authority,
		AutomaticMutation:      false,
		Reason:                 reason,
		EvidenceManifestSHA256: in.EvidenceManifestSHA256,
	}, nil
}

func canonicalRecoveryEvidence(in RecoveryEvidenceSnapshot) RecoveryEvidenceSnapshot {
	in.OriginalBlocker = strings.TrimSpace(in.OriginalBlocker)
	in.WorkerFailureClass = strings.TrimSpace(in.WorkerFailureClass)
	in.WorkerDiagnosticExcerpt = strings.TrimSpace(in.WorkerDiagnosticExcerpt)
	in.ControllerDiagnostic = strings.TrimSpace(in.ControllerDiagnostic)
	in.ChangedFiles = append([]string(nil), in.ChangedFiles...)
	in.FailedChecks = append([]string(nil), in.FailedChecks...)
	sort.Strings(in.ChangedFiles)
	sort.Strings(in.FailedChecks)
	return in
}

func validateRecoveryEvidence(in RecoveryEvidenceSnapshot) error {
	if !safeID.MatchString(in.WorkOrderID) {
		return errors.New("RECOVERY_WORK_ORDER_ID_INVALID")
	}
	if in.BlockedAttempt < 0 {
		return errors.New("RECOVERY_ATTEMPT_INVALID")
	}
	for _, v := range []string{in.QueueInputSHA256, in.WorkOrderSHA256, in.AuthorizationContractSHA, in.EvidenceManifestSHA256} {
		if !hexDigest(v, 64) {
			return errors.New("RECOVERY_IDENTITY_HASH_INVALID")
		}
	}
	if !safePath(in.BaselineRef) || !shaRE.MatchString(in.BaselineSHA) {
		return errors.New("RECOVERY_BASELINE_INVALID")
	}
	if in.ObjectiveID != "" {
		if !safeID.MatchString(in.ObjectiveID) || in.ObjectiveStage < 0 || in.ObjectiveRevision < 1 {
			return errors.New("RECOVERY_OBJECTIVE_IDENTITY_INVALID")
		}
	}
	if in.AuthorityGeneration < 1 {
		return errors.New("RECOVERY_AUTHORITY_GENERATION_INVALID")
	}
	if in.OriginalBlocker == "" || len(in.OriginalBlocker) > 4096 {
		return errors.New("RECOVERY_BLOCKER_INVALID")
	}
	for _, p := range in.ChangedFiles {
		if !safePath(p) {
			return errors.New("RECOVERY_CHANGED_PATH_INVALID")
		}
	}
	if len(in.WorkerDiagnosticExcerpt) > 64<<10 || len(in.ControllerDiagnostic) > 64<<10 {
		return errors.New("RECOVERY_DIAGNOSTIC_TOO_LARGE")
	}
	return nil
}

func hexDigest(v string, n int) bool {
	return len(v) == n && strings.Trim(v, "0123456789abcdef") == ""
}

func classifyRecoveryEvidence(in RecoveryEvidenceSnapshot) (class, subtype string, authority bool, reason string) {
	blocker := strings.ToUpper(in.OriginalBlocker)
	failure := strings.ToUpper(in.WorkerFailureClass)
	diagnostic := strings.ToLower(in.WorkerDiagnosticExcerpt + "\n" + in.ControllerDiagnostic)
	checks := strings.ToUpper(strings.Join(in.FailedChecks, "\n"))

	switch {
	case strings.Contains(blocker, "ACCEPTED_REF_MUTATION") ||
		strings.Contains(blocker, "AUTHORITY_GENERATION_CHANGED") ||
		strings.Contains(blocker, "ANOTHER_PLANE_OWNS_REPOSITORY"):
		return "AUTHORITY_MISMATCH", "AUTHORITY_FENCE", true, "Recovery cannot change authority ownership or accepted-ref policy."

	case strings.Contains(blocker, "PLANE_AUTHORITY_LOST") ||
		strings.Contains(diagnostic, "authority_lease_not_acquired"):
		return "AUTHORITY_MISMATCH", "AUTHORITY_LEASE", false, "Repository authority must be reverified by deterministic controller policy."

	case strings.Contains(blocker, "FORBIDDEN_PATH_MODIFIED"):
		if windowsSandboxArtifact(in.ChangedFiles) {
			return "ENVIRONMENT_DEFECT", "WINDOWS_SANDBOX_ARTIFACT", false, "Forbidden changes are confined to Windows sandbox/cache artifacts rather than authorized source."
		}
		return "FORBIDDEN_PATH", "SOURCE_SCOPE_VIOLATION", false, "Candidate changed a path outside the immutable work-order allowlist."

	case strings.Contains(blocker, "SOURCE_HYGIENE_FAILED"):
		return "SOURCE_HYGIENE", "", false, "Candidate failed deterministic source-hygiene checks."

	case strings.Contains(blocker, "NO_DIFF_PRODUCED"):
		return "NO_DIFF", "", false, "Worker produced no candidate diff for the authorized engineering task."

	case strings.Contains(blocker, "WORKSPACE_MATERIALIZATION_FAILED"):
		return "WORKSPACE_DEFECT", "", false, "Workspace materialization failed before a valid candidate could be evaluated."

	case strings.Contains(blocker, "REPO_UNAVAILABLE"):
		return "TRANSIENT_INFRA", "REPOSITORY_UNAVAILABLE", false, "Registered source repository was unavailable to the controller."

	case strings.Contains(blocker, "WORKER_TIMEOUT") || strings.Contains(blocker, "NO_PROGRESS_TIMEOUT"):
		if strings.Contains(diagnostic, "createprocessasuserw") ||
			strings.Contains(diagnostic, "windows sandbox") ||
			strings.Contains(diagnostic, "uac") {
			return "ENVIRONMENT_DEFECT", "WINDOWS_SANDBOX_INTERACTIVE_BLOCK", false, "Worker timeout is accompanied by Windows sandbox/elevation evidence."
		}
		return "WORKER_NO_PROGRESS", "", false, "Worker exceeded the bounded progress or execution window."

	case strings.Contains(blocker, "WORKER_AUTH_UNAVAILABLE") ||
		strings.Contains(failure, "WORKER_AUTH_UNAVAILABLE") ||
		revokedAuthDiagnostic(diagnostic):
		return "PROVIDER_TRANSIENT", "WORKER_AUTH", false, "Worker authentication is unavailable and requires credential/session remediation outside source repair."

	case strings.Contains(blocker, "CODEX_QUOTA_EXHAUSTED") ||
		strings.Contains(blocker, "PROVIDER_QUOTA_EXHAUSTED") ||
		strings.Contains(blocker, "QUOTA_EXHAUSTED"):
		return "PROVIDER_TRANSIENT", "QUOTA_EXHAUSTION", false, "Provider quota is exhausted; source mutation is not an appropriate recovery action."

	case strings.Contains(blocker, "GO_TEST_FAILED") || strings.Contains(blocker, "FOCUSED_TEST_FAILED"):
		return "TEST_FAILURE", "", false, "Deterministic Go test validation failed."

	case strings.Contains(blocker, "PLAYWRIGHT_FAILED") || strings.Contains(blocker, "POWERSHELL_ACCEPTANCE_FAILED"):
		return "ACCEPTANCE_FAILURE", "", false, "Deterministic acceptance validation failed."

	case strings.Contains(blocker, "COMPILE") || strings.Contains(checks, "COMPILE"):
		return "COMPILE_FAILURE", "", false, "Compilation failed under the bounded candidate."

	case strings.Contains(blocker, "BASELINE_MISMATCH") || strings.Contains(blocker, "BASELINE_"):
		return "BASELINE_DEFECT", "", true, "The pinned baseline contract cannot be silently changed by recovery."

	case strings.Contains(blocker, "DEPENDENCY"):
		return "DEPENDENCY_BLOCK", "", false, "A declared dependency prevents progress."

	case strings.Contains(blocker, "SCOPE") || strings.Contains(blocker, "ALLOWED_PATH"):
		return "SCOPE_CHANGE_REQUIRED", "", true, "Recovery would require authority beyond the immutable work-order scope."

	case strings.Contains(blocker, "POLICY") || strings.Contains(blocker, "CREDENTIAL") ||
		strings.Contains(blocker, "RUNTIME_LAUNCH") || strings.Contains(blocker, "TRADEGUARD"):
		return "POLICY_BOUNDARY", "", true, "Recovery intersects an explicit policy or safety boundary."
	}

	return "UNKNOWN", "", true, "No deterministic recovery classification matched the bounded evidence."
}

func windowsSandboxArtifact(paths []string) bool {
	if len(paths) == 0 {
		return false
	}
	for _, p := range paths {
		s := strings.ToLower(strings.ReplaceAll(p, "\\", "/"))
		if !(strings.Contains(s, "%systemdrive%/programdata/microsoft/windows/caches/") ||
			strings.Contains(s, "programdata/microsoft/windows/caches/")) {
			return false
		}
	}
	return true
}

func revokedAuthDiagnostic(s string) bool {
	for _, marker := range []string{
		"token_revoked",
		"refresh_token_invalidated",
		"refresh token was revoked",
		"access token could not be refreshed because your refresh token was revoked",
	} {
		if strings.Contains(s, marker) {
			return true
		}
	}
	return false
}
