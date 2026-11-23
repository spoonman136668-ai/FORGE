// RSH-03 wires the advisory six-lane archive-head observation to the
// EXISTING signed-witness/mTLS FORGE FSA client. It cannot issue CAS,
// original-first-use permits, dispatches, or scientific acceptance.
package researchfeed

import (
 "bytes"
 "context"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
)

// verifiedFSAReader intentionally has only the two ReadonlyFSA methods.
// In particular it does NOT implement fsatrust.Authority/CompareAndSwap.
// Both peers and the operator pin must be supplied out-of-band by an
// independent, authenticated operator; this function provisions nothing.
type verifiedFSAReader struct {
 remote *fsaremote.Client
 archiveID string
 bindingSHA256 string
}

// NewVerifiedRemoteFSA constructs a read-only interface to the pre-existing
// dual-peer client. Each ReadAnchor verifies the separately signed witness,
// mutually authenticated TLS peers, and independently pinned SPKI identities.
// ConfirmArchiveBinding verifies the physical binding against the remote pin.
// It is still NOT an attestation of deployed peer failure-domain separation.
func NewVerifiedRemoteFSA(authority, witness fsaremote.Peer, remotePin fsaremote.Pin, ownerPin TrustedPin)(ReadonlyFSA,error){
 if !validPin(ownerPin) ||
  ownerPin.ArchiveID!=remotePin.ArchiveID ||
  ownerPin.KeyID!=remotePin.KeyID ||
  !bytes.Equal(ownerPin.PublicKey,remotePin.PublicKey) ||
  ownerPin.Epoch!=remotePin.AuthorityEpoch ||
  ownerPin.BindingSHA256!=remotePin.BindingSHA256 ||
  remotePin.MinimumRevision==0 ||
  len(remotePin.WitnessPublicKey)!=32 ||
  bytes.Equal(remotePin.WitnessPublicKey,remotePin.PublicKey){
  return nil,ErrFSAPreview
 }
 remote,err:=fsaremote.NewClient(authority,witness,remotePin)
 if err!=nil{return nil,ErrFSAPreview}
 return &verifiedFSAReader{remote:remote,archiveID:ownerPin.ArchiveID,bindingSHA256:ownerPin.BindingSHA256},nil
}

func(v *verifiedFSAReader)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 if v==nil||v.remote==nil||ctx==nil||ctx.Err()!=nil{return fsahead.Anchor{},ErrFSAPreview}
 a,err:=v.remote.ReadAnchor(ctx)
 if err!=nil||ctx.Err()!=nil{return fsahead.Anchor{},ErrFSAPreview}
 return a,nil
}
func(v *verifiedFSAReader)ReadBinding(ctx context.Context,archiveID string)(string,bool,error){
 if v==nil||v.remote==nil||ctx==nil||ctx.Err()!=nil||
  archiveID!=v.archiveID{return "",false,ErrFSAPreview}
 ok,err:=v.remote.ConfirmArchiveBinding(ctx,archiveID)
 if err!=nil||!ok||ctx.Err()!=nil{return "",false,ErrFSAPreview}
 // Only return the *already authenticated and independently pinned* digest.
 // No untrusted response body or worker-supplied value confers authority.
 return v.bindingSHA256,true,nil
}
var _ ReadonlyFSA=(*verifiedFSAReader)(nil)
