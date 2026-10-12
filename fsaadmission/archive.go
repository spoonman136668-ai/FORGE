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
    evidence.Journal = journal
    evidence.JournalHead = startrecovery.TrustedHead{
        Sequence: anchor.Sequence,
        SHA256: anchor.HeadSHA256,
        IndependentlyAuthenticated: true,
    }
    return Assess(evidence)
}
