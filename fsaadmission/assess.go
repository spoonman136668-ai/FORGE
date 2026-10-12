// Package fsaadmission composes the existing frozen-proposal, all-lane ledger,
// and independently anchored journal checks into a negative-only preflight.
// It has no authority to reserve a cohort, emit a primary-start receipt,
// dispatch work, or admit/accept scientific evidence.
package fsaadmission

import (
    "errors"
    "fmt"

    "github.com/spoonman136668-ai/forge/eligibility"
    "github.com/spoonman136668-ai/forge/researchlog"
    "github.com/spoonman136668-ai/forge/startrecovery"
)

var ErrBlocked = errors.New("FORGE_FSA_COMPOSED_PREFLIGHT_BLOCKED")

// Disposition explicitly denies scientific execution authority even on success.
type Disposition string
const PreflightOnly Disposition = "SOURCE_PREFLIGHT_ONLY_NOT_ADMITTED"

// Evidence carries *externally authenticated* identities. Computing hashes
// locally is not authentication: callers must independently attest the frozen
// digest, complete all-lane ledger pin/generation, and exact journal head.
// The source-only preflight cannot provide those attestations itself.
type Evidence struct {
    Frozen eligibility.Frozen
    FrozenPinSHA256 string
    Ledger eligibility.LedgerSnapshot
    LedgerPinSHA256 string
    LedgerGeneration uint64
    CompleteAllLanes bool
    Journal researchlog.Journal
    JournalHead startrecovery.TrustedHead
    ExperimentGeneration uint64
}

// Assess verifies that one fully frozen candidate has no observed conflict.
// A nil error means only static consistency; no caller may infer permission
// to reserve, dispatch, write an authority checkpoint, or start science.
func Assess(e Evidence) (Disposition, error) {
    p := e.Frozen
    if e.ExperimentGeneration == 0 ||
        e.ExperimentGeneration != e.LedgerGeneration ||
        e.Ledger.Generation != e.ExperimentGeneration ||
        !e.CompleteAllLanes ||
        !e.JournalHead.IndependentlyAuthenticated {
        return "", fmt.Errorf("%w: independent generation or attestation unavailable", ErrBlocked)
    }

    // Verify a complete, independently pinned all-lane snapshot first,
    // including active/consumed cohorts and all prior/uncertain starts.
    if err := eligibility.VerifyLedger(p, e.Ledger, e.LedgerPinSHA256,
        e.ExperimentGeneration, e.CompleteAllLanes); err != nil {
        return "", fmt.Errorf("%w: ledger: %v", ErrBlocked, err)
    }

    decision, err := startrecovery.Inspect(e.Journal, e.JournalHead,
        p.Lane, p.CandidateID)
    if err != nil || decision != startrecovery.NoPriorStart {
        return "", fmt.Errorf("%w: start not independently reconciled: %v", ErrBlocked, err)
    }

    // The latest record for this experiment must be the exact qualified
    // frozen proposal at the pinned generation, rather than merely an
    // unrelated qualified experiment in the same verified journal.
    var last researchlog.Event
    for _, record := range e.Journal.Entries {
        if record.Event.Lane == p.Lane && record.Event.ExperimentID == p.CandidateID {
            last = record.Event
        }
    }
    if last.Kind != researchlog.SourceQualified ||
        last.Generation != e.ExperimentGeneration ||
        last.SourceCommitSHA != p.SourceSHA ||
        last.PreregSHA256 != p.PreregSHA256 ||
        last.CohortSHA256 != p.CohortSHA256 {
        return "", fmt.Errorf("%w: candidate journal identity mismatch", ErrBlocked)
    }

    // Build the eligibility witness only from the already-verified ledger
    // and independently reconciled journal; never trust caller-supplied
    // LedgerAuthenticated or StartReconciled booleans.
    consumed := make(map[string]bool, len(e.Ledger.ConsumedCohorts)+len(e.Ledger.ActiveCohorts))
    for _, hash := range e.Ledger.ConsumedCohorts { consumed[hash] = true }
    for _, hash := range e.Ledger.ActiveCohorts { consumed[hash] = true }
    witness := eligibility.Witness{
        Lane: p.Lane, SourceSHA: p.SourceSHA,
        PreregSHA256: p.PreregSHA256, CohortSHA256: p.CohortSHA256,
        ProtocolSHA256: p.ProtocolSHA256, FrozenSHA256: e.FrozenPinSHA256,
        ConsumedCohorts: consumed, LedgerAuthenticated: true,
        StartReconciled: true,
    }
    if err := eligibility.Check(p, witness); err != nil {
        return "", fmt.Errorf("%w: frozen proposal: %v", ErrBlocked, err)
    }
    return PreflightOnly, nil
}
