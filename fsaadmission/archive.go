package fsaadmission

import (
    "context"
    "fmt"

    "github.com/spoonman136668-ai/forge/fsatrust"
    "github.com/spoonman136668-ai/forge/privatearchive"
    "github.com/spoonman136668-ai/forge/startrecovery"
)

// AssessArchived derives its journal and trusted head from an independently
// authenticated, read-only FSA recovery, never from caller-supplied flags.
// The supplied ledger and frozen pins STILL require separate authentication;
// neither this method nor a successful preflight grants scientific admission,
// cohort reservation, signing rights or an experiment dispatch capability.
//
// A production Authority MUST be separately provisioned with independent
// storage, identity and witness protections. Local test doubles are not
// acceptable deployment authorities.
func AssessArchived(
    ctx context.Context,
    backend fsatrust.Authority,
    archive *privatearchive.Store,
    identity fsatrust.Identity,
    evidence Evidence,
) (Disposition, error) {
    // Never allow an unprovisioned backend or archive to fall back to an
    // in-memory proposal journal or attacker-provided trusted-head flag.
    anchor, err := fsatrust.Recover(ctx, backend, archive, identity)
    if err != nil {
        return "", fmt.Errorf("%w: authenticated archive recovery: %v", ErrBlocked, err)
    }
    journal, err := archive.Load()
    if err != nil {
        return "", fmt.Errorf("%w: archive load: %v", ErrBlocked, err)
    }
    // Recover verified the entire original archive, then authenticated the
    // remote head again. Reject a concurrent archive change rather than
    // accepting a later or stale local observation.
    if err := archive.VerifyTrustedHead(anchor.Sequence, anchor.HeadSHA256); err != nil {
        return "", fmt.Errorf("%w: post-recovery archive drift: %v", ErrBlocked, err)
    }
    // A verified record-chain head alone does not attest that immutable
    // terminal originals remained present during later archive reads.
    // Repeat the COMPLETE trusted recovery after loading the journal, so
    // original loss during the earlier recovery/read interval fails closed.
    // A deployed authority must additionally protect immutable originals
    // against concurrent deletion or corruption; read-only source checks
    // cannot turn a writable archive into an atomic filesystem snapshot.
    second, err := fsatrust.Recover(ctx, backend, archive, identity)
    if err != nil {
        return "", fmt.Errorf("%w: final originals and head recovery: %v", ErrBlocked, err)
    }
    if second.Sequence != anchor.Sequence || second.HeadSHA256 != anchor.HeadSHA256 {
        return "", fmt.Errorf("%w: archive highwater advanced during assessment", ErrBlocked)
    }
    evidence.Journal = journal
    evidence.JournalHead = startrecovery.TrustedHead{
        Sequence: anchor.Sequence,
        SHA256: anchor.HeadSHA256,
        IndependentlyAuthenticated: true,
    }
    return Assess(evidence)
}
