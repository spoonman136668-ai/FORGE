// Package fsaremote defines a client-only, non-executing, dual-service
// protocol for FORGE Scientific Authority (FSA) checkpoints. No server,
// signer, trust database, task queue or production credential is created.
package fsaremote

import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 WitnessSchema = "forge.fsa.remote-witness.v1"
 WitnessDomain = "FORGE_FSA_REMOTE_HIGHWATER_V1"
 WireSchema = "forge.fsa.remote-api.v1"
 domainPrefix = "FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"
 MaxResponseBytes = 16384
)
var (
 ErrWitness = errors.New("FORGE_FSA_INDEPENDENT_WITNESS_UNTRUSTED")
 ErrMismatch = errors.New("FORGE_FSA_REMOTE_HEAD_OR_BINDING_MISMATCH")
 ErrRemote = errors.New("FORGE_FSA_REMOTE_UNAVAILABLE_OR_INDETERMINATE")
)
type Pin struct {
 ArchiveID string
 KeyID string
 PublicKey ed25519.PublicKey
 AuthorityEpoch uint64
 BindingSHA256 string
 WitnessPublicKey ed25519.PublicKey
 MinimumRevision uint64
}
type WitnessHead struct {
 Schema string `json:"schema"`
 Domain string `json:"domain"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
 Revision uint64 `json:"revision"`
}
type SignedWitness struct {
 Head WitnessHead `json:"head"`
 SignatureHex string `json:"signature_hex"`
}
type AnchorWire struct {
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 PublicKeyHex string `json:"public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func validKeyID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'||c=='-'){return false}}
 return true
}
func (p Pin)valid()bool{
 return validHex(p.ArchiveID,64)&&validKeyID(p.KeyID)&&
 len(p.PublicKey)==ed25519.PublicKeySize&&p.AuthorityEpoch>0&&
 validHex(p.BindingSHA256,64)&&len(p.WitnessPublicKey)==ed25519.PublicKeySize&&
 p.MinimumRevision>0
}
func makeWire(a fsahead.Anchor)AnchorWire{
 return AnchorWire{ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKeyHex:hex.EncodeToString(a.PublicKey),AuthorityEpoch:a.AuthorityEpoch,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256}
}
func parseAnchor(w AnchorWire)(fsahead.Anchor,error){
 b,err:=hex.DecodeString(w.PublicKeyHex)
 if err!=nil||len(b)!=ed25519.PublicKeySize||!validHex(w.ArchiveID,64)||!validKeyID(w.KeyID)||w.AuthorityEpoch==0||
 w.Sequence>researchlog.MaxEntries||!validHex(w.HeadSHA256,64)||
 (w.Sequence==0&&w.HeadSHA256!=researchlog.Genesis)||(w.Sequence>0&&w.HeadSHA256==researchlog.Genesis){
  return fsahead.Anchor{},ErrMismatch
 }
 return fsahead.Anchor{ArchiveID:w.ArchiveID,KeyID:w.KeyID,PublicKey:ed25519.PublicKey(b),AuthorityEpoch:w.AuthorityEpoch,Sequence:w.Sequence,HeadSHA256:w.HeadSHA256},nil
}
func sameAnchor(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&bytes.Equal(a.PublicKey,b.PublicKey)&&
 a.AuthorityEpoch==b.AuthorityEpoch&&a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
func (p Pin)accepts(a fsahead.Anchor)bool{
 return a.ArchiveID==p.ArchiveID&&a.KeyID==p.KeyID&&bytes.Equal(a.PublicKey,p.PublicKey)&&a.AuthorityEpoch==p.AuthorityEpoch
}
// VerifyWitness checks an independent Ed25519 signature, provisioned identity,
// physical binding commitment, and a caller-provisioned minimum revision.
// It CANNOT establish that the witness service actually retained the latest
// revision: that requires independently durable, monotonic service behavior.
func VerifyWitness(p Pin,w SignedWitness,a fsahead.Anchor)error{
 if !p.valid()||!p.accepts(a){return ErrMismatch}
 h:=w.Head
 if h.Schema!=WitnessSchema||h.Domain!=WitnessDomain||
 h.ArchiveID!=p.ArchiveID||h.KeyID!=p.KeyID||h.AuthorityEpoch!=p.AuthorityEpoch||
 h.BindingSHA256!=p.BindingSHA256||h.Sequence!=a.Sequence||h.HeadSHA256!=a.HeadSHA256||
 h.Revision<p.MinimumRevision||h.Revision==0||h.Sequence>researchlog.MaxEntries||
 !validHex(w.SignatureHex,ed25519.SignatureSize*2){
  return ErrWitness
 }
 sig,err:=hex.DecodeString(w.SignatureHex);if err!=nil{return ErrWitness}
 body,err:=json.Marshal(h);if err!=nil{return ErrWitness}
 message:=append([]byte(domainPrefix),body...)
 if !ed25519.Verify(p.WitnessPublicKey,message,sig){return ErrWitness}
 return nil
}
