// Package progression is a deterministic, non-executing projection of CKB
// scientific successor progression. It does not own a scheduler, queue, runner,
// admission gate, accepted ref, or any external capability.
package progression

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
)

const (
	EventSchema        = "ckb.research.proposed-event.v2.shadow"
	JournalSchema      = "ckb.research.journal-record.v2.shadow"
	Genesis            = "0000000000000000000000000000000000000000000000000000000000000000"
	LaneWingless  Lane = "Wingless"
	LaneYggdrasil Lane = "Yggdrasil"
)

type Lane string
type Phase string
type Kind string

const (
	Idle      Phase = "IDLE"
	Selected  Phase = "SELECTED"
	Frozen    Phase = "FROZEN"
	Built     Phase = "BUILT"
	Qualified Phase = "QUALIFIED"
	Admitted  Phase = "ADMITTED"
	Running   Phase = "RUNNING"
	Terminal  Phase = "TERMINAL_UNARCHIVED"
	Archived  Phase = "ARCHIVED"
	Blocked   Phase = "BLOCKED"

	Select  Kind = "SELECT"
	Freeze  Kind = "FREEZE"
	Build   Kind = "BUILD"
	Qualify Kind = "QUALIFY"
	Admit   Kind = "ADMISSION_OBSERVED"
	Start   Kind = "PRIMARY_START_OBSERVED"
	Finish  Kind = "PRIMARY_TERMINAL_OBSERVED"
	Archive Kind = "ARCHIVE_OBSERVED"
	Close   Kind = "CLOSE"
	Block   Kind = "BLOCK"
)

// An Event must be assembled from independently verified CKB-side witnesses.
// The reducer validates structure and consistency, never external authenticity.
// Every digest is a lowercase SHA256 except source_ref, which is a Git SHA1.
// The optional run fields are legal only in primary start/finish/archive events.
// No boolean in this schema confers READY_RESEARCH or dispatch authority.
type Event struct {
	Schema              string `json:"schema"`
	Kind                Kind   `json:"kind"`
	Lane                Lane   `json:"lane"`
	Generation          uint64 `json:"generation"`
	CandidateSHA256     string `json:"candidate_sha256"`
	CohortSHA256        string `json:"cohort_sha256"`
	SourceRef           string `json:"source_ref"`
	WitnessSHA256       string `json:"witness_sha256"`
	PreregSHA256        string `json:"prereg_sha256,omitempty"`
	QualificationSHA256 string `json:"qualification_sha256,omitempty"`
	RunID               uint64 `json:"run_id,omitempty"`
	Attempt             uint64 `json:"attempt,omitempty"`
	Outcome             string `json:"outcome,omitempty"`
	EvidenceSHA256      string `json:"evidence_sha256,omitempty"`
	ArchiveSHA256       string `json:"archive_sha256,omitempty"`
	Reason              string `json:"reason,omitempty"`
}

type LaneState struct {
	Phase               Phase  `json:"phase"`
	Generation          uint64 `json:"generation"`
	CandidateSHA256     string `json:"candidate_sha256,omitempty"`
	CohortSHA256        string `json:"cohort_sha256,omitempty"`
	SourceRef           string `json:"source_ref,omitempty"`
	PreregSHA256        string `json:"prereg_sha256,omitempty"`
	QualificationSHA256 string `json:"qualification_sha256,omitempty"`
	RunID               uint64 `json:"run_id,omitempty"`
	Attempt             uint64 `json:"attempt,omitempty"`
	Outcome             string `json:"outcome,omitempty"`
	EvidenceSHA256      string `json:"evidence_sha256,omitempty"`
	ArchiveSHA256       string `json:"archive_sha256,omitempty"`
	BlockReason         string `json:"block_reason,omitempty"`
}

type State struct {
	Schema           string             `json:"schema"`
	Sequence         uint64             `json:"sequence"`
	LastRecordSHA256 string             `json:"last_record_sha256"`
	Lanes            map[Lane]LaneState `json:"lanes"`
	Consumed         map[string]string  `json:"consumed_cohort_sha256"`
	Seen             map[string]bool    `json:"seen_event_sha256"`
}

// Intents are informational recommendations, not dispatch commands.
type Intent struct {
	Lane            Lane   `json:"lane"`
	Generation      uint64 `json:"generation"`
	Status          string `json:"status"`
	SuggestedNext   string `json:"suggested_next"`
	CandidateSHA256 string `json:"candidate_sha256,omitempty"`
}

func NewState() State {
	return State{Schema: "ckb.research.projection.v2.shadow", LastRecordSHA256: Genesis,
		Lanes:    map[Lane]LaneState{LaneWingless: {Phase: Idle}, LaneYggdrasil: {Phase: Idle}},
		Consumed: map[string]string{}, Seen: map[string]bool{}}
}

func digest(v any) (string, error) {
	data, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	sha := sha256.Sum256(data)
	return hex.EncodeToString(sha[:]), nil
}

func isHash(value string, n int) bool {
	if len(value) != n {
		return false
	}
	for _, ch := range value {
		if (ch < '0' || ch > '9') && (ch < 'a' || ch > 'f') {
			return false
		}
	}
	return true
}

func require(b bool, reason string) error {
	if !b {
		return errors.New(reason)
	}
	return nil
}

func validateEvent(e Event) error {
	if e.Schema != EventSchema {
		return errors.New("EVENT_SCHEMA_REJECTED")
	}
	if e.Lane != LaneWingless && e.Lane != LaneYggdrasil {
		return errors.New("INVALID_LANE")
	}
	if e.Generation < 1 {
		return errors.New("INVALID_GENERATION")
	}
	if !isHash(e.CandidateSHA256, 64) || !isHash(e.CohortSHA256, 64) || !isHash(e.WitnessSHA256, 64) || !isHash(e.SourceRef, 40) {
		return errors.New("IDENTITY_INCOMPLETE")
	}
	if e.PreregSHA256 != "" && !isHash(e.PreregSHA256, 64) {
		return errors.New("PREREG_HASH_INVALID")
	}
	if e.QualificationSHA256 != "" && !isHash(e.QualificationSHA256, 64) {
		return errors.New("QUALIFICATION_HASH_INVALID")
	}
	if e.EvidenceSHA256 != "" && !isHash(e.EvidenceSHA256, 64) {
		return errors.New("EVIDENCE_HASH_INVALID")
	}
	if e.ArchiveSHA256 != "" && !isHash(e.ArchiveSHA256, 64) {
		return errors.New("ARCHIVE_HASH_INVALID")
	}
	switch e.Kind {
	case Select, Freeze, Build, Qualify, Admit, Start, Finish, Archive, Close, Block:
	default:
		return errors.New("UNKNOWN_EVENT_KIND")
	}
	if e.Kind == Block {
		if e.Reason == "" || ValidateReason(e.Reason) != nil {
			return errors.New("BLOCK_REASON_REQUIRED")
		}
	} else if e.Reason != "" {
		return errors.New("REASON_UNEXPECTED")
	}
	if e.Kind == Freeze && e.PreregSHA256 == "" {
		return errors.New("PREREG_WITNESS_MISSING")
	}
	if e.Kind == Qualify && e.QualificationSHA256 == "" {
		return errors.New("QUALIFICATION_WITNESS_MISSING")
	}
	if e.Kind == Start || e.Kind == Finish || e.Kind == Archive {
		if e.RunID == 0 || e.Attempt == 0 {
			return errors.New("RUN_WITNESS_INCOMPLETE")
		}
	} else if e.RunID != 0 || e.Attempt != 0 {
		return errors.New("UNEXPECTED_RUN_ID")
	}
	if e.Kind == Finish {
		switch e.Outcome {
		case "SUPPORTED", "MIXED", "NEGATIVE", "INVALID", "CONSUMED_INDETERMINATE":
		default:
			return errors.New("OUTCOME_UNRECOGNIZED")
		}
		if e.EvidenceSHA256 == "" && e.Outcome != "CONSUMED_INDETERMINATE" {
			return errors.New("PRIMARY_RAW_EVIDENCE_MISSING")
		}
	} else if e.Outcome != "" {
		return errors.New("UNEXPECTED_OUTCOME")
	}
	if e.Kind == Archive && e.ArchiveSHA256 == "" {
		return errors.New("ARCHIVE_WITNESS_MISSING")
	}
	if e.Kind != Archive && e.ArchiveSHA256 != "" {
		return errors.New("ARCHIVE_HASH_UNEXPECTED")
	}
	if e.Kind != Finish && e.Kind != Archive && e.EvidenceSHA256 != "" {
		return errors.New("UNEXPECTED_EVIDENCE_HASH")
	}
	if e.Kind != Freeze && e.Kind != Qualify && e.Kind != Admit && e.PreregSHA256 != "" {
		return errors.New("UNEXPECTED_PREREG_HASH")
	}
	if e.Kind != Qualify && e.Kind != Admit && e.QualificationSHA256 != "" {
		return errors.New("UNEXPECTED_QUALIFICATION_HASH")
	}
	return nil
}

// Apply produces a new state from one proposed event. It is pure and never
// touches disk, GitHub, runners, accepted refs, or any scientific primary.
// Duplicates return an unchanged state; same event identity is exact-content.
func Apply(current State, e Event) (State, bool, error) {
	if current.Schema != "ckb.research.projection.v2.shadow" || current.Lanes == nil || current.Seen == nil || current.Consumed == nil {
		return State{}, false, errors.New("STATE_SCHEMA_REJECTED")
	}
	if err := validateEvent(e); err != nil {
		return State{}, false, err
	}
	id, err := digest(e)
	if err != nil {
		return State{}, false, err
	}
	if current.Seen[id] {
		return current, false, nil
	}
	ls, ok := current.Lanes[e.Lane]
	if !ok {
		return State{}, false, errors.New("LANE_NOT_PRESENT")
	}
	// Prevent accidental reuse across W/Y and across generations even if the
	// corresponding prior primary is a negative or indeterminate.
	if e.Kind == Select {
		if ls.Phase != Idle || e.Generation != ls.Generation+1 {
			return State{}, false, errors.New("INVALID_NEXT_GENERATION")
		}
		if _, used := current.Consumed[e.CohortSHA256]; used {
			return State{}, false, errors.New("CONSUMED_COHORT_REUSE")
		}
		for lane, peer := range current.Lanes {
			if lane != e.Lane && peer.Phase != Idle && peer.CohortSHA256 == e.CohortSHA256 {
				return State{}, false, errors.New("CROSS_LANE_COHORT_COLLISION")
			}
		}
		ls = LaneState{Phase: Selected, Generation: e.Generation, CandidateSHA256: e.CandidateSHA256,
			CohortSHA256: e.CohortSHA256, SourceRef: e.SourceRef}
	} else {
		if e.Generation != ls.Generation || e.CandidateSHA256 != ls.CandidateSHA256 || e.CohortSHA256 != ls.CohortSHA256 || e.SourceRef != ls.SourceRef {
			return State{}, false, errors.New("PINNED_GENERATION_IDENTITY_DRIFT")
		}
		switch e.Kind {
		case Freeze:
			if ls.Phase != Selected {
				return State{}, false, errors.New("FREEZE_STAGE_INVALID")
			}
			ls.PreregSHA256 = e.PreregSHA256
			ls.Phase = Frozen
		case Build:
			if ls.Phase != Frozen {
				return State{}, false, errors.New("BUILD_STAGE_INVALID")
			}
			ls.Phase = Built
		case Qualify:
			if ls.Phase != Built {
				return State{}, false, errors.New("QUALIFY_STAGE_INVALID")
			}
			ls.QualificationSHA256 = e.QualificationSHA256
			ls.Phase = Qualified
		case Admit:
			if ls.Phase != Qualified || e.QualificationSHA256 != ls.QualificationSHA256 || e.PreregSHA256 != ls.PreregSHA256 {
				return State{}, false, errors.New("ADMISSION_PROVENANCE_DRIFT")
			}
			ls.Phase = Admitted
		case Start:
			if ls.Phase != Admitted {
				return State{}, false, errors.New("PRIMARY_START_NOT_ADMITTED")
			}
			if prior, used := current.Consumed[e.CohortSHA256]; used {
				return State{}, false, fmt.Errorf("PRIMARY_COHORT_ALREADY_CONSUMED:%s", prior)
			}
			ls.RunID = e.RunID
			ls.Attempt = e.Attempt
			ls.Phase = Running
		case Finish:
			if ls.Phase != Running || e.RunID != ls.RunID || e.Attempt != ls.Attempt {
				return State{}, false, errors.New("PRIMARY_TERMINAL_RUN_IDENTITY_DRIFT")
			}
			ls.Phase = Terminal
			ls.Outcome = e.Outcome
			ls.EvidenceSHA256 = e.EvidenceSHA256
		case Archive:
			if ls.Phase != Terminal || e.RunID != ls.RunID || e.Attempt != ls.Attempt || e.EvidenceSHA256 != ls.EvidenceSHA256 {
				return State{}, false, errors.New("ARCHIVE_RAW_EVIDENCE_MISMATCH")
			}
			ls.Phase = Archived
			ls.ArchiveSHA256 = e.ArchiveSHA256
		case Close:
			if ls.Phase != Archived {
				return State{}, false, errors.New("CLOSE_WITHOUT_ARCHIVE")
			}
			// Preserve last scientific outcome and immutable cohort across
			// close until a distinct successor generation is selected.
			ls.Phase = Idle
		case Block:
			if ls.Phase == Idle || ls.Phase == Archived || ls.Phase == Blocked {
				return State{}, false, errors.New("BLOCK_STAGE_INVALID")
			}
			ls.Phase = Blocked
			ls.BlockReason = e.Reason
		default:
			return State{}, false, errors.New("ILLEGAL_EVENT")
		}
	}
	// Do not modify maps in the input state: all state transitions are copy-on-write.
	next := State{Schema: current.Schema, Sequence: current.Sequence, LastRecordSHA256: current.LastRecordSHA256,
		Lanes: make(map[Lane]LaneState, len(current.Lanes)), Consumed: make(map[string]string, len(current.Consumed)), Seen: make(map[string]bool, len(current.Seen)+1)}
	for k, v := range current.Lanes {
		next.Lanes[k] = v
	}
	for k, v := range current.Consumed {
		next.Consumed[k] = v
	}
	for k, v := range current.Seen {
		next.Seen[k] = v
	}
	if e.Kind == Start {
		next.Consumed[e.CohortSHA256] = fmt.Sprintf("%s:%d:%d", e.Lane, e.Generation, e.RunID)
	}
	next.Lanes[e.Lane] = ls
	next.Seen[id] = true
	return next, true, nil
}

func Advisory(s State) []Intent {
	result := make([]Intent, 0, 2)
	for _, lane := range []Lane{LaneWingless, LaneYggdrasil} {
		ls := s.Lanes[lane]
		next := "REQUIRES_INDEPENDENT_CKB_RECONCILIATION"
		switch ls.Phase {
		case Idle:
			next = "SELECT_DISTINCT_FROZEN_PORTFOLIO_CANDIDATE"
		case Selected:
			next = "VERIFY_FROZEN_PREREG_BEFORE_BUILD"
		case Frozen:
			next = "BUILD_ONLY_IN_QUARANTINE"
		case Built:
			next = "RUN_FOCUSED_AND_FINAL_REGRESSION"
		case Qualified:
			next = "REQUIRE_INDEPENDENT_CKB_ADMISSION"
		case Admitted:
			next = "REQUIRE_CKB_ONLY_ONCE_DISPATCH_AND_START_RECEIPT"
		case Running:
			next = "AWAIT_CKB_PRIMARY_TERMINAL_EVIDENCE"
		case Terminal:
			next = "PRESERVE_RAW_EVIDENCE_AND_VERIFY_ARCHIVE"
		case Archived:
			next = "CLOSE_AND_SELECT_NEXT_DISTINCT_GENERATION"
		case Blocked:
			next = "HUMAN_OR_CKB_BOUNDED_CAUSAL_REPAIR_REQUIRED"
		}
		result = append(result, Intent{Lane: lane, Generation: ls.Generation, Status: string(ls.Phase), SuggestedNext: next, CandidateSHA256: ls.CandidateSHA256})
	}
	return result
}

// EventDigest is a content address, NOT authentication or scientific authority.
func EventDigest(e Event) (string, error) {
	if err := validateEvent(e); err != nil {
		return "", err
	}
	return digest(e)
}

// Enforce simple labels on exported fields to prevent normalization ambiguity.
func ValidateReason(reason string) error {
	if len(reason) > 256 || strings.ContainsAny(reason, "\r\n\x00") {
		return errors.New("UNSAFE_REASON")
	}
	return nil
}
