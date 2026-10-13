// Package fsaservice exposes independently authenticated, read-only FSA checkpoint observations.
package fsaservice

import (
 "bytes"
 "context"
 "errors"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
)

var ErrAuthorityObservation = errors.New("FORGE_FSA_AUTHORITY_READONLY_OBSERVATION_BLOCKED")

// IndependentBinding supplies an independently protected physical archive-binding
// commitment. It must NOT be implemented from a checkpoint-store ID, a worker
// assertion or a path to the local research archive.
type IndependentBinding interface {
 ReadBinding(context.Context, string) (bindingSHA256 string, bound bool, err error)
}

// ObservedAuthority joins independent read-only stores; it grants no CAS,
// signer, worker launch or scientific authority.
type ObservedAuthority struct {
 checkpoint fsatrust.Authority
 binding IndependentBinding
}

func NewObservedAuthority(checkpoint fsatrust.Authority, binding IndependentBinding) (*ObservedAuthority, error) {
 if checkpoint == nil || binding == nil { return nil, ErrAuthorityObservation }
 return &ObservedAuthority{checkpoint:checkpoint,binding:binding},nil
}
func sameObservedAnchor(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
 bytes.Equal(a.PublicKey,b.PublicKey)&&a.AuthorityEpoch==b.AuthorityEpoch&&
 a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}

// ReadAnchor is authenticated and cross-checked against a separate, signed
// high-water witness by the existing mTLS fsaremote client.
func (a *ObservedAuthority)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 if a==nil||a.checkpoint==nil||ctx==nil||ctx.Err()!=nil{return fsahead.Anchor{},ErrAuthorityObservation}
 head,err:=a.checkpoint.ReadAnchor(ctx)
 if err!=nil||ctx.Err()!=nil{return fsahead.Anchor{},ErrAuthorityObservation}
 head.PublicKey=append([]byte(nil),head.PublicKey...)
 return head,nil
}

// ReadBinding refuses an unbound archive, inaccessible independent proof or
// changed trusted head during attestation. No trust digest comes from a worker.
func (a *ObservedAuthority)ReadBinding(ctx context.Context,archiveID string)(string,bool,error){
 if a==nil||a.binding==nil||ctx==nil||ctx.Err()!=nil||archiveID==""{return "",false,ErrAuthorityObservation}
 before,err:=a.ReadAnchor(ctx)
 if err!=nil||before.ArchiveID!=archiveID{return "",false,ErrAuthorityObservation}
 bound,err:=a.checkpoint.ConfirmArchiveBinding(ctx,archiveID)
 if err!=nil||!bound{return "",false,ErrAuthorityObservation}
 digest,independentlyBound,err:=a.binding.ReadBinding(ctx,archiveID)
 if err!=nil||!independentlyBound||digest==""||ctx.Err()!=nil{return "",false,ErrAuthorityObservation}
 after,err:=a.ReadAnchor(ctx)
 if err!=nil||!sameObservedAnchor(before,after){return "",false,ErrAuthorityObservation}
 return digest,true,nil
}
var _ AuthorityStore = (*ObservedAuthority)(nil)
