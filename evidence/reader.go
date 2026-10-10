// Package evidence adapts independently authenticated, immutable scientific
// evidence into read-only FORGE observations. It never grants scientific
// admission, workflow dispatch, or mutation authority.
package evidence

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"github.com/spoonman136668-ai/forge/contracts"
)

const ReceiptSchema = "forge.original-evidence.v1"
const MaxReceiptBytes = 64 * 1024

type Receipt struct {
	Schema                    string                  `json:"schema"`
	Observation               contracts.Observation   `json:"observation"`
	SourceClass               contracts.EvidenceClass `json:"source_class"`
	OriginalStartedSHA256     string                  `json:"original_started_sha256"`
	OriginalTerminalSHA256    string                  `json:"original_terminal_sha256"`
	OriginalArchiveSHA256     string                  `json:"original_archive_sha256"`
	OriginalRawEvidenceSHA256 string                  `json:"original_raw_evidence_sha256"`
	OriginalRunConsumed       bool                    `json:"original_run_consumed"`
	ScientificAccepted        bool                    `json:"scientific_accepted"`
	DispatchAuthorized        bool                    `json:"dispatch_authorized"`
	AcceptedRefMutation       bool                    `json:"accepted_ref_mutation"`
	ReplayAuthorized          bool                    `json:"replay_authorized"`
}

type Witness struct {
	AuthorityEpoch      uint64
	SourceWitnessSHA256 string
	LedgerWitnessSHA256 string
	ReceiptSHA256       string
}

// Source returns the exact original, canonical receipt bytes. Its transport is
// implemented outside FORGE. Reading bytes never confers execution rights.
type Source interface {
	ReadReceipt(ctx context.Context, lane contracts.Lane) ([]byte, error)
}

// Authenticator is supplied by an independently trusted authority. Requiring
// this dependency prevents a receipt's self-claimed SHA from becoming proof.
// An implementation must verify provenance, signer trust and replay status.
type Authenticator interface {
	Authenticate(ctx context.Context, lane contracts.Lane, original []byte, expected Witness) error
}

type Reader struct {
	source Source
	auth   Authenticator
	pins   map[contracts.Lane]Witness
}

func lowerHex(s string) bool {
	if len(s) != 64 {
		return false
	}
	for _, ch := range s {
		if (ch < '0' || ch > '9') && (ch < 'a' || ch > 'f') {
			return false
		}
	}
	return true
}

// NewReader freezes exactly one independently provided pin per research lane.
// It fails closed when authentication is absent or identities are incomplete.
func NewReader(src Source, auth Authenticator, witnesses map[contracts.Lane]Witness) (*Reader, error) {
	if src == nil || auth == nil || len(witnesses) != 2 {
		return nil, errors.New("FORGE_EVIDENCE_TRUST_CONFIGURATION_MISSING")
	}
	out := make(map[contracts.Lane]Witness, 2)
	for _, lane := range []contracts.Lane{contracts.Wingless, contracts.Yggdrasil} {
		w, ok := witnesses[lane]
		if !ok || w.AuthorityEpoch == 0 || !lowerHex(w.SourceWitnessSHA256) ||
			!lowerHex(w.LedgerWitnessSHA256) || !lowerHex(w.ReceiptSHA256) {
			return nil, errors.New("FORGE_EVIDENCE_INDEPENDENT_PIN_INVALID")
		}
		out[lane] = w
	}
	return &Reader{source: src, auth: auth, pins: out}, nil
}

// DecodeCanonical rejects unknown fields, noncanonical JSON, duplicate keys,
// and ambiguous trailing content. These are consistency controls, not proof.
func DecodeCanonical(b []byte) (Receipt, error) {
	var zero Receipt
	if len(b) == 0 || len(b) > MaxReceiptBytes {
		return zero, errors.New("FORGE_EVIDENCE_BOUNDS")
	}
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if err := d.Decode(&zero); err != nil {
		return Receipt{}, fmt.Errorf("FORGE_EVIDENCE_JSON: %w", err)
	}
	var trailing any
	if err := d.Decode(&trailing); err != io.EOF {
		return Receipt{}, errors.New("FORGE_EVIDENCE_TRAILING")
	}
	canonical, err := json.Marshal(zero)
	if err != nil || !bytes.Equal(bytes.TrimSpace(b), canonical) {
		return Receipt{}, errors.New("FORGE_EVIDENCE_NONCANONICAL_OR_DUPLICATE")
	}
	if zero.Schema != ReceiptSchema || contracts.ValidateObservation(zero.Observation) != nil ||
		(zero.SourceClass != contracts.Synthetic && zero.SourceClass != contracts.External) ||
		!lowerHex(zero.OriginalStartedSHA256) || !lowerHex(zero.OriginalTerminalSHA256) ||
		!lowerHex(zero.OriginalArchiveSHA256) || !lowerHex(zero.OriginalRawEvidenceSHA256) ||
		!zero.OriginalRunConsumed || zero.ScientificAccepted || zero.DispatchAuthorized ||
		zero.AcceptedRefMutation || zero.ReplayAuthorized {
		return Receipt{}, errors.New("FORGE_EVIDENCE_CONTRACT_OR_AUTHORITY_INVALID")
	}
	if zero.Observation.LatestOutcome == "NONE" {
		return Receipt{}, errors.New("FORGE_EVIDENCE_ORIGINAL_RESULT_ABSENT")
	}
	return zero, nil
}

// ReadLatest only exposes the observation after exact frozen identity, strict
// structural checks and independent authentication of the original bytes.
// This interface never submits, schedules, mutates or reconciles science.
func (r *Reader) ReadLatest(ctx context.Context, lane contracts.Lane) (contracts.Observation, error) {
	var zero contracts.Observation
	if r == nil || r.source == nil || r.auth == nil {
		return zero, errors.New("FORGE_EVIDENCE_READER_UNCONFIGURED")
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	pin, ok := r.pins[lane]
	if !ok {
		return zero, errors.New("FORGE_EVIDENCE_LANE_UNAUTHORIZED")
	}
	original, err := r.source.ReadReceipt(ctx, lane)
	if err != nil {
		return zero, fmt.Errorf("FORGE_EVIDENCE_READ: %w", err)
	}
	if len(original) == 0 || len(original) > MaxReceiptBytes {
		return zero, errors.New("FORGE_EVIDENCE_BYTES_LIMIT")
	}
	sha := sha256.Sum256(original)
	if hex.EncodeToString(sha[:]) != pin.ReceiptSHA256 {
		return zero, errors.New("FORGE_EVIDENCE_RECEIPT_IDENTITY_DRIFT")
	}
	receipt, err := DecodeCanonical(original)
	if err != nil {
		return zero, err
	}
	o := receipt.Observation
	if o.Lane != lane || o.AuthorityEpoch != pin.AuthorityEpoch ||
		o.SourceWitnessSHA256 != pin.SourceWitnessSHA256 || o.LedgerWitnessSHA256 != pin.LedgerWitnessSHA256 {
		return zero, errors.New("FORGE_EVIDENCE_OBSERVATION_DRIFT")
	}
	if err := r.auth.Authenticate(ctx, lane, original, pin); err != nil {
		return zero, fmt.Errorf("FORGE_EVIDENCE_UNAUTHENTICATED: %w", err)
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	return o, nil
}

var _ contracts.EvidenceReader = (*Reader)(nil)
