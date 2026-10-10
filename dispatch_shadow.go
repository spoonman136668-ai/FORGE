package progression

// FORGE's dispatch shadow is an inert protocol model. It has no network,
// runner, command execution, queue, clock, state database or dispatch API.
// A future CKB-owned adapter MUST authenticate upstream evidence and atomically
// persist reservations in the existing authority store before any external write.

import (
	"errors"
	"fmt"
)

const (
	ShadowDispatchSchema               = "forge.dispatch-book.v2.shadow"
	ShadowReserved       DispatchPhase = "RESERVED_OUTCOME_UNKNOWN"
	ShadowStarted        DispatchPhase = "PRIMARY_STARTED_OBSERVED"
	ShadowEnded          DispatchPhase = "PRIMARY_TERMINAL_OBSERVED"
)

type DispatchPhase string

// Identity includes the CKB authority epoch and one immutable primary attempt.
// Only the CKB authority may define these fields. Hashes are bare SHA-256.
type DispatchIdentity struct {
	Lane                Lane   `json:"lane"`
	Generation          uint64 `json:"generation"`
	CandidateSHA256     string `json:"candidate_sha256"`
	CohortSHA256        string `json:"cohort_sha256"`
	SourceRef           string `json:"source_ref"`
	PreregSHA256        string `json:"prereg_sha256"`
	QualificationSHA256 string `json:"qualification_sha256"`
	Workflow            string `json:"workflow"`
	Attempt             uint64 `json:"attempt"`
	AuthorityEpoch      uint64 `json:"authority_epoch"`
}

type DispatchReservation struct {
	Identity               DispatchIdentity `json:"identity"`
	IdentitySHA256         string           `json:"identity_sha256"`
	Phase                  DispatchPhase    `json:"phase"`
	RunID                  uint64           `json:"run_id,omitempty"`
	ObservedStartSHA256    string           `json:"observed_start_sha256,omitempty"`
	ObservedTerminalSHA256 string           `json:"observed_terminal_sha256,omitempty"`
	Outcome                string           `json:"outcome,omitempty"`
	DispatchPermitted      bool             `json:"dispatch_permitted"` // ALWAYS FALSE
}

// Cross-lane and same-generation reservations share a single logical book.
// Real concurrency protection requires a CKB atomic transaction, not this map.
type DispatchBook struct {
	Schema           string                         `json:"schema"`
	Reservations     map[string]DispatchReservation `json:"reservations"`
	GenerationOwners map[string]string              `json:"generation_owners"`
	CohortOwners     map[string]string              `json:"cohort_owners"`
}

func NewDispatchBook() DispatchBook {
	return DispatchBook{Schema: ShadowDispatchSchema,
		Reservations:     map[string]DispatchReservation{},
		GenerationOwners: map[string]string{}, CohortOwners: map[string]string{}}
}

// ValidateDispatchBook fails closed on a torn or modified projected ledger.
// It verifies local integrity only, not independent CKB authentication.
func ValidateDispatchBook(b DispatchBook) error {
	if b.Schema != ShadowDispatchSchema || b.Reservations == nil || b.GenerationOwners == nil || b.CohortOwners == nil {
		return errors.New("DISPATCH_BOOK_INVALID")
	}
	if len(b.Reservations) > 50000 || len(b.Reservations) != len(b.GenerationOwners) || len(b.Reservations) != len(b.CohortOwners) {
		return errors.New("DISPATCH_BOOK_INDEX_OR_SIZE_DRIFT")
	}
	for key, row := range b.Reservations {
		h, err := digest(row.Identity)
		if err != nil || h != key || row.IdentitySHA256 != key || row.DispatchPermitted ||
			b.GenerationOwners[generationKey(row.Identity)] != key || b.CohortOwners[row.Identity.CohortSHA256] != key ||
			(row.Identity.Lane != LaneWingless && row.Identity.Lane != LaneYggdrasil) ||
			row.Identity.Generation == 0 || row.Identity.AuthorityEpoch == 0 || row.Identity.Attempt != 1 ||
			row.Identity.Workflow != "research-authority-generic.yml" {
			return errors.New("DISPATCH_BOOK_RESERVATION_OR_INDEX_CORRUPTED")
		}
		switch row.Phase {
		case ShadowReserved:
			if row.RunID != 0 || row.ObservedStartSHA256 != "" || row.ObservedTerminalSHA256 != "" || row.Outcome != "" {
				return errors.New("DISPATCH_BOOK_UNVERIFIED_PRIMARY_FIELDS")
			}
		case ShadowStarted:
			if row.RunID == 0 || !isHash(row.ObservedStartSHA256, 64) || row.ObservedTerminalSHA256 != "" || row.Outcome != "" {
				return errors.New("DISPATCH_BOOK_START_WITNESS_INCOMPLETE")
			}
		case ShadowEnded:
			if row.RunID == 0 || !isHash(row.ObservedStartSHA256, 64) || !isHash(row.ObservedTerminalSHA256, 64) {
				return errors.New("DISPATCH_BOOK_TERMINAL_WITNESS_INCOMPLETE")
			}
			switch row.Outcome {
			case "SUPPORTED", "MIXED", "NEGATIVE", "INVALID", "CONSUMED_INDETERMINATE":
			default:
				return errors.New("DISPATCH_BOOK_UNRECOGNIZED_OUTCOME")
			}
		default:
			return errors.New("DISPATCH_BOOK_PHASE_INVALID")
		}
	}
	return nil
}

func cloneBook(b DispatchBook) DispatchBook {
	n := NewDispatchBook()
	for k, v := range b.Reservations {
		n.Reservations[k] = v
	}
	for k, v := range b.GenerationOwners {
		n.GenerationOwners[k] = v
	}
	for k, v := range b.CohortOwners {
		n.CohortOwners[k] = v
	}
	return n
}

func generationKey(id DispatchIdentity) string { return fmt.Sprintf("%s:%d", id.Lane, id.Generation) }

func validateDispatchIdentity(s State, id DispatchIdentity) error {
	if s.Schema != NewState().Schema || s.Lanes == nil || s.Consumed == nil {
		return errors.New("DISPATCH_STATE_UNTRUSTED")
	}
	if id.Lane != LaneWingless && id.Lane != LaneYggdrasil {
		return errors.New("DISPATCH_LANE_INVALID")
	}
	if id.Generation < 1 || id.AuthorityEpoch < 1 || id.Attempt != 1 {
		return errors.New("DISPATCH_ATTEMPT_OR_EPOCH_INVALID")
	}
	if id.Workflow != "research-authority-generic.yml" {
		return errors.New("DISPATCH_WORKFLOW_UNAUTHORIZED")
	}
	if !isHash(id.CandidateSHA256, 64) || !isHash(id.CohortSHA256, 64) || !isHash(id.SourceRef, 40) ||
		!isHash(id.PreregSHA256, 64) || !isHash(id.QualificationSHA256, 64) {
		return errors.New("DISPATCH_PIN_INVALID")
	}
	l, ok := s.Lanes[id.Lane]
	if !ok || l.Phase != Admitted || l.Generation != id.Generation ||
		l.CandidateSHA256 != id.CandidateSHA256 || l.CohortSHA256 != id.CohortSHA256 ||
		l.SourceRef != id.SourceRef || l.PreregSHA256 != id.PreregSHA256 || l.QualificationSHA256 != id.QualificationSHA256 {
		return errors.New("DISPATCH_NOT_EXACT_ADMITTED_GENERATION")
	}
	if _, taken := s.Consumed[id.CohortSHA256]; taken {
		return errors.New("DISPATCH_COHORT_ALREADY_CONSUMED")
	}
	for lane, peer := range s.Lanes {
		if lane != id.Lane && peer.Phase != Idle && peer.CohortSHA256 == id.CohortSHA256 {
			return errors.New("DISPATCH_CROSS_LANE_COHORT_COLLISION")
		}
	}
	return nil
}

// ReserveDispatchInShadow does not return a capability to dispatch. A recorded
// reservation is ALWAYS ambiguous until independent GitHub+CKB observation;
// duplicate call returns same record without indicating an outbound retry.
func ReserveDispatchInShadow(s State, current DispatchBook, id DispatchIdentity) (DispatchBook, DispatchReservation, bool, error) {
	if err := ValidateDispatchBook(current); err != nil {
		return DispatchBook{}, DispatchReservation{}, false, err
	}
	if err := validateDispatchIdentity(s, id); err != nil {
		return DispatchBook{}, DispatchReservation{}, false, err
	}
	hash, err := digest(id)
	if err != nil {
		return DispatchBook{}, DispatchReservation{}, false, err
	}
	g := generationKey(id)
	if owner := current.GenerationOwners[g]; owner != "" && owner != hash {
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_GENERATION_ALREADY_RESERVED_DIFFERENT_IDENTITY")
	}
	if owner := current.CohortOwners[id.CohortSHA256]; owner != "" && owner != hash {
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_COHORT_ALREADY_RESERVED")
	}
	if prior, exists := current.Reservations[hash]; exists {
		if prior.Identity != id || prior.DispatchPermitted {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_RESERVATION_CORRUPTED")
		}
		return current, prior, false, nil
	}
	for _, other := range current.Reservations {
		if other.IdentitySHA256 == hash || other.Identity.Lane == id.Lane && other.Identity.Generation == id.Generation ||
			other.Identity.CohortSHA256 == id.CohortSHA256 {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_ORPHAN_RESERVATION_COLLISION")
		}
	}
	next := cloneBook(current)
	row := DispatchReservation{Identity: id, IdentitySHA256: hash, Phase: ShadowReserved, DispatchPermitted: false}
	next.Reservations[hash] = row
	next.GenerationOwners[g] = hash
	next.CohortOwners[id.CohortSHA256] = hash
	return next, row, true, nil
}

// Observation fields MUST have been authenticated independently by CKB against
// GitHub run/attempt/source/workflow and immutable raw receipts. This inert
// function only enforces structural consistency and is not that authentication.
type DispatchObservation struct {
	IdentitySHA256 string `json:"identity_sha256"`
	Kind           string `json:"kind"` // STARTED or TERMINAL
	RunID          uint64 `json:"run_id"`
	Attempt        uint64 `json:"attempt"`
	Workflow       string `json:"workflow"`
	SourceRef      string `json:"source_ref"`
	WitnessSHA256  string `json:"witness_sha256"`
	Outcome        string `json:"outcome,omitempty"`
}

func ObserveDispatchInShadow(current DispatchBook, observed DispatchObservation) (DispatchBook, DispatchReservation, bool, error) {
	if err := ValidateDispatchBook(current); err != nil {
		return DispatchBook{}, DispatchReservation{}, false, err
	}
	if !isHash(observed.IdentitySHA256, 64) || !isHash(observed.WitnessSHA256, 64) {
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_OBSERVATION_IDENTITY_INVALID")
	}
	prior, ok := current.Reservations[observed.IdentitySHA256]
	if !ok || prior.IdentitySHA256 != observed.IdentitySHA256 || prior.DispatchPermitted {
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_OBSERVATION_NO_RESERVATION")
	}
	if observed.RunID == 0 || observed.Attempt != prior.Identity.Attempt || observed.Workflow != prior.Identity.Workflow || observed.SourceRef != prior.Identity.SourceRef {
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_OBSERVATION_WRONG_PRIMARY")
	}
	nextRow := prior
	switch observed.Kind {
	case "STARTED":
		if observed.Outcome != "" {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_STARTED_HAS_OUTCOME")
		}
		if prior.Phase == ShadowStarted || prior.Phase == ShadowEnded {
			if prior.RunID != observed.RunID || prior.ObservedStartSHA256 != observed.WitnessSHA256 {
				return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_CONFLICTING_START_WITNESS")
			}
			return current, prior, false, nil
		}
		if prior.Phase != ShadowReserved {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_START_PHASE_INVALID")
		}
		nextRow.Phase = ShadowStarted
		nextRow.RunID = observed.RunID
		nextRow.ObservedStartSHA256 = observed.WitnessSHA256
	case "TERMINAL":
		if prior.Phase != ShadowStarted && prior.Phase != ShadowEnded {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_TERMINAL_WITHOUT_START")
		}
		if observed.RunID != prior.RunID {
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_TERMINAL_RUN_DRIFT")
		}
		switch observed.Outcome {
		case "SUPPORTED", "MIXED", "NEGATIVE", "INVALID", "CONSUMED_INDETERMINATE":
		default:
			return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_TERMINAL_OUTCOME_INVALID")
		}
		if prior.Phase == ShadowEnded {
			if prior.ObservedTerminalSHA256 != observed.WitnessSHA256 || prior.Outcome != observed.Outcome {
				return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_TERMINAL_WITNESS_CONFLICT")
			}
			return current, prior, false, nil
		}
		nextRow.Phase = ShadowEnded
		nextRow.ObservedTerminalSHA256 = observed.WitnessSHA256
		nextRow.Outcome = observed.Outcome
	default:
		return DispatchBook{}, DispatchReservation{}, false, errors.New("DISPATCH_OBSERVATION_KIND_INVALID")
	}
	next := cloneBook(current)
	next.Reservations[observed.IdentitySHA256] = nextRow
	return next, nextRow, true, nil
}
