// Package fsawitnessguard checks a signed FSA witness against an independently
// retained high-water commitment. It is inert source code: it does not create
// a listener, store, signer, scheduler, or external authority.
package fsawitnessguard

import (
 "bytes"
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
)

var ErrUntrusted = errors.New("FORGE_FSA_WITNESS_HIGHWATER_UNTRUSTED_OR_INDETERMINATE")
const commitmentDomain = "FORGE-FSA-INDEPENDENT-WITNESS-COMMITMENT-V1\n"

// Commitment must be retained and monotonically advanced in a failure domain
// independent of the witness ledger. Same-process or same-disk deployments
// do not satisfy physical independence.
type Commitment struct {
 Revision uint64
 WitnessSHA256 string
}

// Ledger is a separately provisioned durable atomic conditional-write store.
// CAS MUST never overwrite a mismatched exact digest. False means definitive
// conflict; a possibly committed write MUST return an error.
type Ledger interface {
 Read(context.Context) (fsaremote.SignedWitness, error)
 CompareAndSwap(context.Context, string, fsaremote.SignedWitness) (bool, error)
}

// Floor is an independently provisioned rollback-resistant conditional-write
// register. The real provider MUST enforce monotonicity even after host loss.
type Floor interface {
 Read(context.Context) (Commitment, error)
 CompareAndSwap(context.Context, Commitment, Commitment) (bool, error)
}

type Guard struct {
 pin fsaremote.Pin
 ledger Ledger
 floor Floor
}

// New is read/write inert. The pin, genesis and floor must be obtained from
// separately authenticated provisioning, never inferred from the local ledger.
func New(pin fsaremote.Pin, ledger Ledger, floor Floor) (*Guard, error) {
 if ledger == nil || floor == nil || pin.MinimumRevision == 0 ||
  len(pin.WitnessPublicKey) != 32 || len(pin.PublicKey) != 32 ||
  bytes.Equal(pin.WitnessPublicKey, pin.PublicKey) {
  return nil, ErrUntrusted
 }
 pin.PublicKey=bytes.Clone(pin.PublicKey)
 pin.WitnessPublicKey=bytes.Clone(pin.WitnessPublicKey)
 return &Guard{pin:pin, ledger:ledger, floor:floor}, nil
}

func digest(w fsaremote.SignedWitness) (string, error) {
 raw, err := json.Marshal(w)
 if err != nil { return "", err }
 sum := sha256.Sum256(append([]byte(commitmentDomain), raw...))
 return hex.EncodeToString(sum[:]), nil
}

func anchor(p fsaremote.Pin, h fsaremote.WitnessHead) fsahead.Anchor {
 return fsahead.Anchor{ArchiveID:h.ArchiveID, KeyID:h.KeyID, PublicKey:bytes.Clone(p.PublicKey),
  AuthorityEpoch:h.AuthorityEpoch, Sequence:h.Sequence, HeadSHA256:h.HeadSHA256}
}

func (g *Guard) read(ctx context.Context) (fsaremote.SignedWitness, Commitment, error) {
 if g == nil || ctx == nil || ctx.Err() != nil { return fsaremote.SignedWitness{}, Commitment{}, ErrUntrusted }
 witnessed, err := g.ledger.Read(ctx)
 if err != nil { return fsaremote.SignedWitness{}, Commitment{}, ErrUntrusted }
 if fsaremote.VerifyWitness(g.pin, witnessed, anchor(g.pin,witnessed.Head)) != nil {
  return fsaremote.SignedWitness{}, Commitment{}, ErrUntrusted
 }
 expected, err := digest(witnessed)
 if err != nil { return fsaremote.SignedWitness{}, Commitment{}, ErrUntrusted }
 independent, err := g.floor.Read(ctx)
 if err != nil || ctx.Err() != nil || independent.Revision != witnessed.Head.Revision ||
  independent.WitnessSHA256 != expected {
  return fsaremote.SignedWitness{}, Commitment{}, ErrUntrusted
 }
 return witnessed, independent, nil
}

// ReadHighWater implements fsaservice.WitnessReader without granting write
// access. The archive ID and immutable pinned identity must match exactly.
func (g *Guard) ReadHighWater(ctx context.Context, archiveID string) (fsaremote.SignedWitness,error) {
 if g == nil || archiveID != g.pin.ArchiveID { return fsaremote.SignedWitness{}, ErrUntrusted }
 w, _, err := g.read(ctx)
 return w, err
}

// Advance conditionally installs ONE independently signed successor. It is
// not an authority checkpoint admission or scientific-transition signer.
// Indeterminate outcomes halt with no retry, repair, or inferred success.
func (g *Guard) Advance(ctx context.Context, previous, next fsaremote.SignedWitness) (bool,error) {
 current, floor, err := g.read(ctx)
 if err != nil { return false, err }
 oldHash, err := digest(current)
 if err != nil { return false, ErrUntrusted }
 suppliedHash, err := digest(previous)
 if err != nil || suppliedHash != oldHash { return false, nil }
 if next.Head.Revision <= current.Head.Revision ||
  next.Head.Revision != current.Head.Revision+1 ||
  next.Head.Sequence <= current.Head.Sequence ||
  next.Head.Sequence != current.Head.Sequence+1 ||
  next.Head.HeadSHA256 == current.Head.HeadSHA256 ||
  fsaremote.VerifyWitness(g.pin,next,anchor(g.pin,next.Head)) != nil || ctx.Err() != nil {
  return false, ErrUntrusted
 }
 newHash,err:=digest(next)
 if err != nil { return false, ErrUntrusted }
 future:=Commitment{Revision:next.Head.Revision,WitnessSHA256:newHash}
 committed,err:=g.ledger.CompareAndSwap(ctx,oldHash,next)
 if err != nil { return false, ErrUntrusted } // May already be committed.
 if !committed { return false,nil }
 // If the floor update fails, the ledger is ahead and reads fail closed.
 // Require independently verified recovery: NEVER replay the CAS.
 raised,err:=g.floor.CompareAndSwap(ctx,floor,future)
 if err != nil || !raised { return false,ErrUntrusted }
 observed,_,err:=g.read(ctx)
 if err != nil { return false,ErrUntrusted }
 observedHash,err:=digest(observed)
 if err != nil || observedHash != newHash { return false,ErrUntrusted }
 return true,nil
}
