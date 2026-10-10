// Package quarantine implements an in-memory, non-executing scientific
// proposal inbox. It is an offline engineering fixture, not CKB's authority.
package quarantine

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sort"
	"strconv"
	"sync"

	"github.com/spoonman136668-ai/forge/contracts"
)

const SnapshotSchema = "forge.quarantine-shadow.v1"

// Record is a cloned draft and a quarantine-only acknowledgment. Both remain
// untrusted input for any external backend review or scientific admission.
type Record struct {
	Draft   contracts.CandidateDraft           `json:"draft"`
	Receipt contracts.QuarantineAcknowledgment `json:"receipt"`
}

type Snapshot struct {
	Schema  string   `json:"schema"`
	Records []Record `json:"records"`
	SHA256  string   `json:"sha256"`
}

// Inbox is deliberately volatile: it does not persist, send, schedule, or
// submit to CKB, and its idempotency guarantee covers this instance only.
type Inbox struct {
	mu           sync.Mutex
	max          int
	byDigest     map[string]Record
	byGeneration map[string]string
	byCohort     map[string]string
	bySeed       map[string]string
}

func New(maxRecords int) (*Inbox, error) {
	if maxRecords < 1 || maxRecords > 64 {
		return nil, errors.New("FORGE_QUARANTINE_CAP_INVALID")
	}
	return &Inbox{max: maxRecords, byDigest: make(map[string]Record), byGeneration: make(map[string]string), byCohort: make(map[string]string), bySeed: make(map[string]string)}, nil
}
func clone(d contracts.CandidateDraft) contracts.CandidateDraft {
	d.SeedIdentities = append([]string(nil), d.SeedIdentities...)
	d.AllowedPaths = append([]string(nil), d.AllowedPaths...)
	return d
}
func ack(digest string) contracts.QuarantineAcknowledgment {
	return contracts.QuarantineAcknowledgment{Schema: contracts.AcknowledgmentSchema, ProposalSHA256: digest, Status: "QUARANTINE_ONLY"}
}

// SubmitDraft enforces replay, capacity, lane/generation, cohort and seed
// uniqueness. All checks occur under one lock; on conflict nothing is stored.
// A successful acknowledgment carries NO authority outside this shadow inbox.
func (i *Inbox) SubmitDraft(ctx context.Context, d contracts.CandidateDraft) (contracts.QuarantineAcknowledgment, error) {
	var zero contracts.QuarantineAcknowledgment
	if i == nil {
		return zero, errors.New("FORGE_QUARANTINE_NOT_CONFIGURED")
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	if err := contracts.ValidateCandidate(d); err != nil {
		return zero, err
	}
	hash, err := contracts.CanonicalCandidateSHA256(d)
	if err != nil {
		return zero, err
	}
	key := string(d.Lane) + ":" + strconv.FormatUint(d.Generation, 10)
	i.mu.Lock()
	defer i.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	if record, exists := i.byDigest[hash]; exists {
		return record.Receipt, nil
	}
	if len(i.byDigest) >= i.max {
		return zero, errors.New("FORGE_QUARANTINE_CAP_REACHED")
	}
	if _, exists := i.byGeneration[key]; exists {
		return zero, errors.New("FORGE_QUARANTINE_LANE_GENERATION_CONFLICT")
	}
	if _, exists := i.byCohort[d.CohortSHA256]; exists {
		return zero, errors.New("FORGE_QUARANTINE_COHORT_CONFLICT")
	}
	for _, seed := range d.SeedIdentities {
		if _, exists := i.bySeed[seed]; exists {
			return zero, errors.New("FORGE_QUARANTINE_SEED_CONFLICT")
		}
	}
	receipt := ack(hash)
	i.byDigest[hash] = Record{Draft: clone(d), Receipt: receipt}
	i.byGeneration[key] = hash
	i.byCohort[d.CohortSHA256] = hash
	for _, seed := range d.SeedIdentities {
		i.bySeed[seed] = hash
	}
	return receipt, nil
}

// Inspect gives a detached deterministic structural snapshot, not a signed
// audit record, durable receipt or externally authenticated run history.
func (i *Inbox) Inspect(ctx context.Context) (Snapshot, error) {
	var zero Snapshot
	if i == nil {
		return zero, errors.New("FORGE_QUARANTINE_NOT_CONFIGURED")
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	i.mu.Lock()
	defer i.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	out := Snapshot{Schema: SnapshotSchema, Records: make([]Record, 0, len(i.byDigest))}
	for _, r := range i.byDigest {
		out.Records = append(out.Records, Record{Draft: clone(r.Draft), Receipt: r.Receipt})
	}
	sort.Slice(out.Records, func(a, b int) bool {
		x, y := out.Records[a], out.Records[b]
		if x.Draft.Lane != y.Draft.Lane {
			return x.Draft.Lane < y.Draft.Lane
		}
		if x.Draft.Generation != y.Draft.Generation {
			return x.Draft.Generation < y.Draft.Generation
		}
		return x.Receipt.ProposalSHA256 < y.Receipt.ProposalSHA256
	})
	raw, err := json.Marshal(out.Records)
	if err != nil {
		return zero, err
	}
	sum := sha256.Sum256(raw)
	out.SHA256 = hex.EncodeToString(sum[:])
	return out, nil
}

var _ contracts.QuarantineInbox = (*Inbox)(nil)
