package fsawitnessguard

import (
	"context"

	"github.com/spoonman136668-ai/forge/fsaremote"
)

// RecoveryState is a read-only observation, never permission to retry,
// finalize, repair, or accept a scientific transition.
type RecoveryState string

const (
	RecoveryPreviousObserved RecoveryState = "PREVIOUS_OBSERVED_NO_REPLAY_AUTHORITY"
	RecoveryNextObserved     RecoveryState = "NEXT_OBSERVED_NO_ACCEPTANCE_AUTHORITY"
	RecoveryLedgerAhead      RecoveryState = "LEDGER_AHEAD_QUARANTINE"
	RecoveryFloorAhead       RecoveryState = "FLOOR_AHEAD_QUARANTINE"
)

// RecoveryObservation describes two stable sets of independently obtained
// reads. It is diagnostic evidence, not a signed receipt or linearizable
// cross-domain transaction. The caller must separately verify off-host
// retention, source admission, and physical failure-domain independence.
type RecoveryObservation struct {
	State         RecoveryState
	LedgerRevision uint64
	FloorRevision  uint64
	LedgerSHA256   string
	FloorSHA256    string
}

type recoveryPair struct {
	ledger fsaremote.SignedWitness
	floor  Commitment
	hash   string
}

func (g *Guard) recoveryRead(ctx context.Context) (recoveryPair, error) {
	if g == nil || g.ledger == nil || g.floor == nil || ctx == nil || ctx.Err() != nil {
		return recoveryPair{}, ErrUntrusted
	}
	w, err := g.ledger.Read(ctx)
	if err != nil || fsaremote.VerifyWitness(g.pin, w, anchor(g.pin, w.Head)) != nil {
		return recoveryPair{}, ErrUntrusted
	}
	hash, err := digest(w)
	if err != nil {
		return recoveryPair{}, ErrUntrusted
	}
	f, err := g.floor.Read(ctx)
	if err != nil || ctx.Err() != nil {
		return recoveryPair{}, ErrUntrusted
	}
	return recoveryPair{ledger: w, floor: f, hash: hash}, nil
}

// InspectRecovery compares a caller-supplied exact signed predecessor and
// intended successor against separately read ledger and floor records.
// It never calls CAS, signs records, or authorizes automatic recovery.
//
// Even PREVIOUS_OBSERVED is NOT evidence that retrying a possibly committed
// operation is safe. NEXT_OBSERVED is NOT scientific acceptance. A rollback
// of both stores can only be excluded by actual independently protected
// monotonic retention, not by this source-only read path.
func (g *Guard) InspectRecovery(
	ctx context.Context, archiveID string,
	previous, proposed fsaremote.SignedWitness,
) (RecoveryObservation, error) {
	if g == nil || ctx == nil || ctx.Err() != nil || archiveID != g.pin.ArchiveID ||
		previous.Head.Revision == ^uint64(0) || previous.Head.Sequence == ^uint64(0) ||
		proposed.Head.Revision != previous.Head.Revision+1 ||
		proposed.Head.Sequence != previous.Head.Sequence+1 ||
		proposed.Head.HeadSHA256 == previous.Head.HeadSHA256 ||
		fsaremote.VerifyWitness(g.pin, previous, anchor(g.pin, previous.Head)) != nil ||
		fsaremote.VerifyWitness(g.pin, proposed, anchor(g.pin, proposed.Head)) != nil {
		return RecoveryObservation{}, ErrUntrusted
	}
	beforeHash, err := digest(previous)
	if err != nil {
		return RecoveryObservation{}, ErrUntrusted
	}
	afterHash, err := digest(proposed)
	if err != nil || beforeHash == afterHash {
		return RecoveryObservation{}, ErrUntrusted
	}
	beforeFloor := Commitment{Revision: previous.Head.Revision, WitnessSHA256: beforeHash}
	afterFloor := Commitment{Revision: proposed.Head.Revision, WitnessSHA256: afterHash}

	// Repeated independent reads reject a moving or torn observation.
	// This does not claim a distributed atomic snapshot or physical custody.
	first, err := g.recoveryRead(ctx)
	if err != nil {
		return RecoveryObservation{}, err
	}
	second, err := g.recoveryRead(ctx)
	if err != nil || first.hash != second.hash || first.floor != second.floor {
		return RecoveryObservation{}, ErrUntrusted
	}
	out := RecoveryObservation{
		LedgerRevision: second.ledger.Head.Revision,
		FloorRevision: second.floor.Revision,
		LedgerSHA256: second.hash,
		FloorSHA256: second.floor.WitnessSHA256,
	}
	switch {
	case second.hash == beforeHash && second.floor == beforeFloor:
		out.State = RecoveryPreviousObserved
	case second.hash == afterHash && second.floor == afterFloor:
		out.State = RecoveryNextObserved
	case second.hash == afterHash && second.floor == beforeFloor:
		out.State = RecoveryLedgerAhead
	case second.hash == beforeHash && second.floor == afterFloor:
		out.State = RecoveryFloorAhead
	default:
		return RecoveryObservation{}, ErrUntrusted
	}
	return out, nil
}
