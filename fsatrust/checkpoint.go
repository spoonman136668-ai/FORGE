// Package fsatrust is a fail-closed, non-executing coordination boundary
// between a FORGE-private archive and a SEPARATELY provisioned monotonic
// FORGE Scientific Authority (FSA) checkpoint service. No service, signer,
// credentials, scheduler, controller or durable trust database is provided.
package fsatrust

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

// Identity is an independently operator-pinned FORGE FSA trust root.
// Never learn it from the research journal, a worker, Mind-Palace, CKB,
// KTRADE, or the proposed signed checkpoint itself.
type Identity struct {
 ArchiveID string
 KeyID string
 PublicKey ed25519.PublicKey
 AuthorityEpoch uint64
}

// Authority MUST be implemented by separately authenticated, FORGE-private,
// linearizable, monotonic storage with its own failure domain. A filesystem
// sibling of the archive, public GitHub commit, or untrusted worker is NOT
// an implementation of this contract.
//
// CompareAndSwap must be one atomic, durable operation. A returned error
// may mean the checkpoint was committed; clients MUST NOT blindly retry.
// The implementation must bind archive ID to a specific provisioned store,
// prevent stale anchor rollback, and reject cross-epoch/key substitution.
type Authority interface {
 ReadAnchor(context.Context) (fsahead.Anchor, error)
 ConfirmArchiveBinding(context.Context, string) (bool, error)
 CompareAndSwap(context.Context, fsahead.Anchor, fsahead.Anchor) (bool, error)
}

var (
 ErrUnavailable = errors.New("FORGE_FSA_TRUST_BACKEND_UNAVAILABLE")
 ErrMismatch = errors.New("FORGE_FSA_TRUST_IDENTITY_MISMATCH")
 ErrBinding = errors.New("FORGE_FSA_TRUST_ARCHIVE_BINDING_REJECTED")
 ErrConflict = errors.New("FORGE_FSA_TRUST_CHECKPOINT_CONFLICT")
 // CommitIndeterminate prohibits retrying the same logical operation.
 // Recover using the independently authenticated monotonic anchor first.
 ErrCommitIndeterminate = errors.New("FORGE_FSA_TRUST_COMMIT_INDETERMINATE_RECOVER_BEFORE_ACTION")
)
func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func keyID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'){return false}
 }
 return true
}
func identical(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
  bytes.Equal(a.PublicKey,b.PublicKey)&&a.AuthorityEpoch==b.AuthorityEpoch&&
  a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
func clone(a fsahead.Anchor)fsahead.Anchor{
 a.PublicKey=append(ed25519.PublicKey(nil),a.PublicKey...)
 return a
}
func validateAnchor(a fsahead.Anchor)error{
 if !hexLower(a.ArchiveID,64)||!keyID(a.KeyID)||
  len(a.PublicKey)!=ed25519.PublicKeySize||a.AuthorityEpoch==0||
  a.Sequence>researchlog.MaxEntries||!hexLower(a.HeadSHA256,64)||
  (a.Sequence==0&&a.HeadSHA256!=researchlog.Genesis)||
  (a.Sequence>0&&a.HeadSHA256==researchlog.Genesis){
  return ErrMismatch
 }
 return nil
}
func (p Identity) accepts(a fsahead.Anchor)bool{
 return hexLower(p.ArchiveID,64)&&keyID(p.KeyID)&&
  len(p.PublicKey)==ed25519.PublicKeySize&&p.AuthorityEpoch>0&&
  p.ArchiveID==a.ArchiveID&&p.KeyID==a.KeyID&&
  p.AuthorityEpoch==a.AuthorityEpoch&&bytes.Equal(p.PublicKey,a.PublicKey)
}
func readPinned(ctx context.Context,backend Authority,id Identity)(fsahead.Anchor,error){
 var zero fsahead.Anchor
 if ctx==nil||backend==nil||ctx.Err()!=nil{return zero,ErrUnavailable}
 a,err:=backend.ReadAnchor(ctx)
 if err!=nil{return zero,fmt.Errorf("%w: read",ErrUnavailable)}
 if err=validateAnchor(a);err!=nil||!id.accepts(a){return zero,ErrMismatch}
 bound,err:=backend.ConfirmArchiveBinding(ctx,a.ArchiveID)
 if err!=nil||!bound{return zero,ErrBinding}
 if ctx.Err()!=nil{return zero,ErrUnavailable}
 return clone(a),nil
}
// Advance verifies the exact FSA signature, original evidence, archive
// continuity, external identity and physical binding BEFORE one durable CAS.
// A CAS error or uncertain readback must never cause automatic replay.
func Advance(ctx context.Context,backend Authority,store *privatearchive.Store,id Identity,head fsahead.SignedHead)(fsahead.Anchor,error){
 var zero fsahead.Anchor
 if store==nil{return zero,ErrUnavailable}
 previous,err:=readPinned(ctx,backend,id)
 if err!=nil{return zero,err}
 candidate,err:=fsahead.VerifyArchive(store,previous,head)
 if err!=nil{return zero,err}
 if ctx.Err()!=nil{return zero,ErrUnavailable}
 committed,err:=backend.CompareAndSwap(ctx,clone(previous),clone(candidate))
 if err!=nil{return zero,ErrCommitIndeterminate}
 if !committed{return zero,ErrConflict}
 // Never trust the CAS return alone: authenticate a separate readback
 // before acknowledging success to the research controller.
 observed,err:=readPinned(ctx,backend,id)
 if err!=nil||!identical(observed,candidate){
  return zero,ErrCommitIndeterminate
 }
 return clone(observed),nil
}
// Recover is strictly read-only. After crash or indeterminate commit it
// compares an authenticated high-water mark against the FULL local archive,
// including retained originals. It never repairs, truncates, repeats a
// scientific primary, advances a high-water mark, or changes scheduler state.
func Recover(ctx context.Context,backend Authority,store *privatearchive.Store,id Identity)(fsahead.Anchor,error){
 var zero fsahead.Anchor
 if store==nil{return zero,ErrUnavailable}
 anchor,err:=readPinned(ctx,backend,id);if err!=nil{return zero,err}
 if err=store.VerifyTrustedHead(anchor.Sequence,anchor.HeadSHA256);err!=nil{
  return zero,fmt.Errorf("FORGE_FSA_TRUST_RECOVERY_HEAD_REJECTED: %w",err)
 }
 journal,err:=store.Load();if err!=nil{return zero,err}
 for _,entry:=range journal.Entries{
  switch entry.Event.Kind{
  case researchlog.PrimaryTerminal,researchlog.IndependentReview,researchlog.FinalArchive:
   if _,err:=store.ReadOriginal(entry.Event.OriginalEvidenceSHA256);err!=nil{
    return zero,errors.New("FORGE_FSA_TRUST_RECOVERY_ORIGINAL_MISSING")
   }
  }
 }
 if ctx.Err()!=nil{return zero,ErrUnavailable}
 // A concurrent authority advancement after ReadAnchor would be caught
 // by a second pinned fetch rather than silently returning stale recovery.
 again,err:=readPinned(ctx,backend,id)
 if err!=nil||!identical(anchor,again){return zero,ErrCommitIndeterminate}
 return clone(anchor),nil
}
