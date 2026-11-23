// Package fsaservice contains source-only trust boundaries, not deployed FSA authority.
package fsaservice

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "errors"
 "sync"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
)

// ErrCheckpointGateBlocked indicates that an independently authenticated
// prerequisite failed before the local source-only checkpoint protocol.
var ErrCheckpointGateBlocked=errors.New("FORGE_FSA_SIGNED_CHECKPOINT_GATE_BLOCKED")
// ErrCheckpointGateIndeterminate means a checkpoint may have been committed,
// but no independently authenticated, matching witness acknowledgement exists.
// It MUST NOT trigger a replay, blind CAS retry or worker dispatch.
var ErrCheckpointGateIndeterminate=errors.New("FORGE_FSA_SIGNED_CHECKPOINT_INDETERMINATE_NO_RETRY")

// CheckpointGate is a SYNTHETIC, operator-provisioned source-only integration
// boundary. It neither serves HTTP nor provisions a signer, authority, worker,
// scheduler, queue or production credential. It is NOT a write-side API
// substitute for a linearizable independently deployed FSA service.
type CheckpointGate struct {
 mu sync.Mutex
 checkpoint fsatrust.Authority
 independentBinding IndependentBinding
 archive *privatearchive.Store
 remote *fsaremote.Client
 identity fsatrust.Identity
 bindingSHA256 string
 indeterminate bool
}

func NewCheckpointGate(backend fsatrust.Authority,binding IndependentBinding,
 archive *privatearchive.Store,remote *fsaremote.Client,
 id fsatrust.Identity,bindingSHA256 string)(*CheckpointGate,error){
 if backend==nil||binding==nil||archive==nil||remote==nil||
  !validHex(id.ArchiveID,64)||!validID(id.KeyID)||
  len(id.PublicKey)!=ed25519.PublicKeySize||id.AuthorityEpoch==0||
  !validHex(bindingSHA256,64){
  return nil,ErrCheckpointGateBlocked
 }
 id.PublicKey=append(ed25519.PublicKey(nil),id.PublicKey...)
 return &CheckpointGate{checkpoint:backend,independentBinding:binding,
  archive:archive,remote:remote,identity:id,bindingSHA256:bindingSHA256},nil
}

func(g *CheckpointGate)identityMatches(a fsahead.Anchor)bool{
 return a.ArchiveID==g.identity.ArchiveID&&a.KeyID==g.identity.KeyID&&
 bytes.Equal(a.PublicKey,g.identity.PublicKey)&&
 a.AuthorityEpoch==g.identity.AuthorityEpoch
}

// bindingConfirmed never promotes a checkpoint store's self-reported ID to
// proof of independently bound physical archive identity.
func(g *CheckpointGate)bindingConfirmed(ctx context.Context)bool{
 if ctx==nil||ctx.Err()!=nil{return false}
 bound,err:=g.checkpoint.ConfirmArchiveBinding(ctx,g.identity.ArchiveID)
 if err!=nil||!bound||ctx.Err()!=nil{return false}
 digest,attested,err:=g.independentBinding.ReadBinding(ctx,g.identity.ArchiveID)
 if err!=nil||!attested||digest!=g.bindingSHA256||ctx.Err()!=nil{return false}
 bound,err=g.remote.ConfirmArchiveBinding(ctx,g.identity.ArchiveID)
 return err==nil&&bound&&ctx.Err()==nil
}

// AdvanceSignedCheckpoint requires a signed, full-archive-verifiable FSA
// checkpoint, a distinct read-only mTLS authority+witness client, operator-
// pinned identity and an independently protected archive-binding attestor.
// No successful return grants permission to execute/accept science.
//
// The source-only backend's CAS must be independently linearizable/durable in
// any future deployment. This method does NOT create that external guarantee.
// After any possible CAS, an unconfirmed witness is terminally indeterminate
// for this gate instance, even if the authority store already advanced.
func(g *CheckpointGate)AdvanceSignedCheckpoint(ctx context.Context, signed fsahead.SignedHead)(fsahead.Anchor,error){
 var empty fsahead.Anchor
 if g==nil||ctx==nil||ctx.Err()!=nil{return empty,ErrCheckpointGateBlocked}
 g.mu.Lock()
 defer g.mu.Unlock()
 if g.indeterminate{return empty,ErrCheckpointGateIndeterminate}
 before,err:=g.remote.ReadAnchor(ctx)
 if err!=nil||!g.identityMatches(before){return empty,ErrCheckpointGateBlocked}
 local,err:=g.checkpoint.ReadAnchor(ctx)
 if err!=nil||!sameObservedAnchor(before,local){return empty,ErrCheckpointGateBlocked}
 if !g.bindingConfirmed(ctx){return empty,ErrCheckpointGateBlocked}
 // A separate, independently authenticated read detects movement during the
 // multi-source preflight before we consider a local compare-and-swap.
 preflight,err:=g.remote.ReadAnchor(ctx)
 if err!=nil||!sameObservedAnchor(before,preflight){return empty,ErrCheckpointGateBlocked}
 if _,err:=fsahead.VerifyArchive(g.archive,before,signed);err!=nil{
  return empty,ErrCheckpointGateBlocked
 }
 // fsatrust.Advance RE-verifies signature, complete archive/evidence and
 // monotonic predecessor just before invoking exactly one backend CAS.
 advanced,err:=fsatrust.Advance(ctx,g.checkpoint,g.archive,g.identity,signed)
 if err!=nil{
  if errors.Is(err,fsatrust.ErrCommitIndeterminate){
   g.indeterminate=true
   return empty,ErrCheckpointGateIndeterminate
  }
  return empty,err
 }
 // The checkpoint must not be acknowledged until the separately signed
 // witness is *already* durably retained by an independent remote peer.
 observed,err:=g.remote.ReadAnchor(ctx)
 if err!=nil||!sameObservedAnchor(advanced,observed){
  g.indeterminate=true
  return empty,ErrCheckpointGateIndeterminate
 }
 if !g.bindingConfirmed(ctx){
  g.indeterminate=true
  return empty,ErrCheckpointGateIndeterminate
 }
 again,err:=g.remote.ReadAnchor(ctx)
 if err!=nil||!sameObservedAnchor(advanced,again){
  g.indeterminate=true
  return empty,ErrCheckpointGateIndeterminate
 }
 return advanced,nil
}

// Indeterminate remains sticky for the lifetime of a gate instance. It is
// only an observation, never a permission to clear first-use hazard.
func(g *CheckpointGate)Indeterminate()bool{
 if g==nil{return true}
 g.mu.Lock()
 defer g.mu.Unlock()
 return g.indeterminate
}
