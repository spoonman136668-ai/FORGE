// Package contracts defines FORGE's standalone, versioned, unprivileged
// interface to an independently qualified execution backend.
//
// This package deliberately imports no CKB-plane code. Implementing a backend
// interface does not grant scientific admission, runner or dispatch authority.
package contracts

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"path"
	"strings"
)

const (
	CandidateSchema      = "forge.candidate-draft.v1"
	ObservationSchema    = "forge.backend-observation.v1"
	AcknowledgmentSchema = "forge.quarantine-acknowledgment.v1"
	MaxPaths             = 24
	MaxSeedIdentities    = 128
)

type Lane string

const (
	Wingless  Lane = "Wingless"
	Yggdrasil Lane = "Yggdrasil"
)

type EvidenceClass string

const (
	Synthetic EvidenceClass = "SYNTHETIC_ONLY"
	External  EvidenceClass = "EXTERNAL_SOURCE_UNVERIFIED"
)

// Budget binds resources before submission. Reconciliation and scheduling
// remain responsibilities of CKB's authorized backend.
type Budget struct {
	TimeoutSeconds uint32 `json:"timeout_seconds"`
	MemoryMiB      uint32 `json:"memory_mib"`
	ComputeUnits   uint32 `json:"compute_units"`
}

// CandidateDraft is an immutable proposal for quarantine review only.
// Any non-false authority field fails validation, even if the candidate has
// independently pinned preregistration and source fingerprints.
type CandidateDraft struct {
	Schema                 string        `json:"schema"`
	Lane                   Lane          `json:"lane"`
	Generation             uint64        `json:"generation"`
	CandidateID            string        `json:"candidate_id"`
	SourceCommitSHA        string        `json:"source_commit_sha"`
	CandidateSHA256        string        `json:"candidate_sha256"`
	PreregistrationSHA256  string        `json:"preregistration_sha256"`
	CohortSHA256           string        `json:"cohort_sha256"`
	EvidenceClass          EvidenceClass `json:"evidence_class"`
	SeedIdentities         []string      `json:"seed_identities"`
	AllowedPaths           []string      `json:"allowed_paths"`
	Budget                 Budget        `json:"budget"`
	ScientificPrimary      bool          `json:"scientific_primary"`
	DispatchAuthorized     bool          `json:"dispatch_authorized"`
	AcceptedRefMutation    bool          `json:"accepted_ref_mutation"`
	ProductionAuthority    bool          `json:"production_authority"`
	ExternalSourceAdmitted bool          `json:"external_source_admitted"`
}

func isLowerHex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	for _, c := range s {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {
			return false
		}
	}
	return true
}

func validRelativeResearchPath(s string) bool {
	if s == "" || len(s) > 240 || strings.ContainsAny(s, "\\:\x00") || strings.HasPrefix(s, "/") || strings.HasSuffix(s, "/") || strings.Contains(s, "//") {
		return false
	}
	if path.Clean(s) != s || strings.HasPrefix(s, "../") || s == ".." || strings.HasPrefix(s, "./") {
		return false
	}
	for _, piece := range strings.Split(s, "/") {
		if piece == "." || piece == ".." || piece == "" || strings.HasPrefix(piece, ".") {
			return false
		}
	}
	// FORGE proposals cannot alter execution or authority infrastructure.
	for _, prefix := range []string{".github/", "snapshot/", "internal/plane/", "config/", "KTRADE/", "scripts/", "research/progression-v2-shadow/"} {
		if strings.HasPrefix(s, prefix) {
			return false
		}
	}
	return true
}

// ValidateCandidate checks structural consistency, not source authenticity,
// prospective cohort disjointness, sealed-split safety, or CKB acceptance.
func ValidateCandidate(d CandidateDraft) error {
	if d.Schema != CandidateSchema || (d.Lane != Wingless && d.Lane != Yggdrasil) || d.Generation == 0 || d.Generation > 1_000_000_000 || len(d.CandidateID) == 0 || len(d.CandidateID) > 160 || strings.TrimSpace(d.CandidateID) != d.CandidateID {
		return errors.New("FORGE_CANDIDATE_IDENTITY_INVALID")
	}
	if !isLowerHex(d.SourceCommitSHA, 40) || !isLowerHex(d.CandidateSHA256, 64) || !isLowerHex(d.PreregistrationSHA256, 64) || !isLowerHex(d.CohortSHA256, 64) {
		return errors.New("FORGE_CANDIDATE_PIN_INVALID")
	}
	if d.EvidenceClass != Synthetic && d.EvidenceClass != External {
		return errors.New("FORGE_EVIDENCE_CLASS_UNSUPPORTED")
	}
	if d.ScientificPrimary || d.DispatchAuthorized || d.AcceptedRefMutation || d.ProductionAuthority || d.ExternalSourceAdmitted {
		return errors.New("FORGE_PROPOSAL_PRIVILEGE_FORBIDDEN")
	}
	if d.Budget.TimeoutSeconds == 0 || d.Budget.MemoryMiB == 0 || d.Budget.ComputeUnits == 0 || d.Budget.TimeoutSeconds > 86400 || d.Budget.MemoryMiB > 32768 || d.Budget.ComputeUnits > 1000000 {
		return errors.New("FORGE_BUDGET_INVALID")
	}
	if len(d.SeedIdentities) == 0 || len(d.SeedIdentities) > MaxSeedIdentities || len(d.AllowedPaths) == 0 || len(d.AllowedPaths) > MaxPaths {
		return errors.New("FORGE_PROPOSAL_BOUNDS_INVALID")
	}
	seeds := make(map[string]struct{}, len(d.SeedIdentities))
	for _, s := range d.SeedIdentities {
		if len(s) <= len(d.Lane)+1 || len(s) > 128 || !strings.HasPrefix(s, string(d.Lane)+":") || strings.TrimSpace(s) != s {
			return errors.New("FORGE_SEED_IDENTITY_INVALID")
		}
		if _, exists := seeds[s]; exists {
			return errors.New("FORGE_DUPLICATE_SEED")
		}
		seeds[s] = struct{}{}
	}
	paths := make(map[string]struct{}, len(d.AllowedPaths))
	for _, s := range d.AllowedPaths {
		if !validRelativeResearchPath(s) {
			return fmt.Errorf("FORGE_PATH_NOT_ALLOWED:%q", s)
		}
		if _, exists := paths[s]; exists {
			return errors.New("FORGE_DUPLICATE_PATH")
		}
		paths[s] = struct{}{}
	}
	return nil
}

// CanonicalCandidateSHA256 hashes a validated structural proposal. The digest
// is not a CKB admission signature nor proof of the actual source bytes.
func CanonicalCandidateSHA256(d CandidateDraft) (string, error) {
	if err := ValidateCandidate(d); err != nil {
		return "", err
	}
	b, err := json.Marshal(d)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}

// Observation is read-only data whose authenticity must be independently
// established by the execution backend and checked by the trusted caller.
// FORGE never converts an observation into permission to dispatch.
type Observation struct {
	Schema              string `json:"schema"`
	Lane                Lane   `json:"lane"`
	AuthorityEpoch      uint64 `json:"authority_epoch"`
	SourceWitnessSHA256 string `json:"source_witness_sha256"`
	LedgerWitnessSHA256 string `json:"ledger_witness_sha256"`
	LatestOutcome       string `json:"latest_outcome"`
	ScientificAuthority bool   `json:"scientific_authority"`
	AcceptedRefMutation bool   `json:"accepted_ref_mutation"`
}

func ValidateObservation(o Observation) error {
	if o.Schema != ObservationSchema || (o.Lane != Wingless && o.Lane != Yggdrasil) || o.AuthorityEpoch == 0 || !isLowerHex(o.SourceWitnessSHA256, 64) || !isLowerHex(o.LedgerWitnessSHA256, 64) || o.ScientificAuthority || o.AcceptedRefMutation {
		return errors.New("FORGE_OBSERVATION_CONTRACT_INVALID")
	}
	switch o.LatestOutcome {
	case "NONE", "SUPPORTED", "MIXED", "NEGATIVE", "INVALID", "CONSUMED_INDETERMINATE", "UNKNOWN":
	default:
		return errors.New("FORGE_OUTCOME_UNRECOGNIZED")
	}
	return nil
}

// QuarantineAcknowledgment is not admission. Any unexpected positive
// privilege claim is rejected even when the proposal digest matches.
type QuarantineAcknowledgment struct {
	Schema              string `json:"schema"`
	ProposalSHA256      string `json:"proposal_sha256"`
	Status              string `json:"status"`
	ScientificAdmitted  bool   `json:"scientific_admitted"`
	DispatchAuthorized  bool   `json:"dispatch_authorized"`
	AcceptedRefMutation bool   `json:"accepted_ref_mutation"`
}

func ValidateAcknowledgment(a QuarantineAcknowledgment, proposalSHA256 string) error {
	if a.Schema != AcknowledgmentSchema || !isLowerHex(proposalSHA256, 64) || a.ProposalSHA256 != proposalSHA256 || a.Status != "QUARANTINE_ONLY" || a.ScientificAdmitted || a.DispatchAuthorized || a.AcceptedRefMutation {
		return errors.New("FORGE_ACK_AUTHORITY_OR_IDENTITY_DRIFT")
	}
	return nil
}

// EvidenceReader is deliberately query-only. Receipt authentication and
// source provenance remain the caller/backend's responsibility.
type EvidenceReader interface {
	ReadLatest(ctx context.Context, lane Lane) (Observation, error)
}

// QuarantineInbox accepts draft submissions only. Implementations must run
// behind the existing, independently qualified CKB review path; no API here
// can authorize primary science, spawn a runner, enqueue work, or update refs.
type QuarantineInbox interface {
	SubmitDraft(ctx context.Context, draft CandidateDraft) (QuarantineAcknowledgment, error)
}
