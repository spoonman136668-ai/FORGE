// Package fsahead verifies independently issued FORGE Scientific Authority
// (FSA) archive-head witnesses. It is read-only. Neither source nor tests
// provision a signing key, issue science permissions, or modify live systems.
package fsahead

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strings"

 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 Schema = "forge.fsa.signed-head.v1"
 Domain = "FORGE_SCIENTIFIC_AUTHORITY_ARCHIVE_HEAD_V1"
 domainSeparator = "FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"
)

// Payload is the exact field-ordered JSON message authenticated by Ed25519.
// In particular, key identity and *independent* predecessor state are signed.
// It grants no authorization to create or launch scientific experiments.
type Payload struct {
 Schema string `json:"schema"`
 Domain string `json:"domain"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 ParentSequence uint64 `json:"parent_sequence"`
 ParentHeadSHA256 string `json:"parent_head_sha256"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
}
type SignedHead struct {
 Payload Payload `json:"payload"`
 SignatureHex string `json:"signature_hex"`
}

// Anchor MUST come from separately authenticated, monotonic, FORGE-private
// storage. It must never be initialized from the untrusted archive or receipt.
// A caller is responsible for retaining the returned anchor durably only
// after independent FSA authorization and explicit controlled checkpointing.
type Anchor struct {
 ArchiveID string
 KeyID string
 PublicKey ed25519.PublicKey
 AuthorityEpoch uint64
 Sequence uint64
 HeadSHA256 string
}
func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func identifier(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'){return false}
 }
 return true
}
func validateAnchor(a Anchor)error{
 if !hexLower(a.ArchiveID,64)||!identifier(a.KeyID)||len(a.PublicKey)!=ed25519.PublicKeySize||a.AuthorityEpoch==0||a.Sequence>researchlog.MaxEntries||!hexLower(a.HeadSHA256,64){
  return errors.New("FORGE_FSA_EXTERNAL_TRUST_ANCHOR_INVALID")
 }
 if a.Sequence==0&&a.HeadSHA256!=researchlog.Genesis{
  return errors.New("FORGE_FSA_EXTERNAL_GENESIS_MISMATCH")
 }
 if a.Sequence>0&&a.HeadSHA256==researchlog.Genesis{
  return errors.New("FORGE_FSA_EXTERNAL_NONEMPTY_GENESIS")
 }
 return nil
}
func signedBytes(p Payload)([]byte,error){
 raw,err:=json.Marshal(p);if err!=nil{return nil,err}
 return append([]byte(domainSeparator),raw...),nil
}
// VerifySignature only validates source identity, domain separation, exact
// predecessor, monotonic progress, and Ed25519 authenticity. The signed
// head must ALSO be checked against the complete private scientific archive.
func VerifySignature(a Anchor,checkpoint SignedHead)(Payload,error){
 var empty Payload
 if err:=validateAnchor(a);err!=nil{return empty,err}
 p:=checkpoint.Payload
 if p.Schema!=Schema||p.Domain!=Domain||p.ArchiveID!=a.ArchiveID||p.KeyID!=a.KeyID||
   p.AuthorityEpoch!=a.AuthorityEpoch||p.ParentSequence!=a.Sequence||
   p.ParentHeadSHA256!=a.HeadSHA256||p.Sequence<=a.Sequence||
   p.Sequence>researchlog.MaxEntries||!hexLower(p.HeadSHA256,64)||p.HeadSHA256==researchlog.Genesis{
  return empty,errors.New("FORGE_FSA_CHECKPOINT_SCOPE_OR_PREDECESSOR_INVALID")
 }
 if !hexLower(checkpoint.SignatureHex,ed25519.SignatureSize*2){
  return empty,errors.New("FORGE_FSA_CHECKPOINT_SIGNATURE_FORMAT")
 }
 signature,err:=hex.DecodeString(checkpoint.SignatureHex)
 if err!=nil{return empty,errors.New("FORGE_FSA_CHECKPOINT_SIGNATURE_DECODE")}
 bytes,err:=signedBytes(p);if err!=nil{return empty,err}
 if !ed25519.Verify(a.PublicKey,bytes,signature){
  return empty,errors.New("FORGE_FSA_CHECKPOINT_SIGNATURE_UNTRUSTED")
 }
 return p,nil
}
// VerifyArchive checks the FSA signature AND exact full archive sequence,
// chained record identities, independently pinned predecessor, and presence
// of all retained original terminal/review/archive evidence. It never writes.
// A positive result is NOT itself a durable monotonic checkpoint commit.
func VerifyArchive(store *privatearchive.Store,a Anchor,checkpoint SignedHead)(Anchor,error){
 var zero Anchor
 p,err:=VerifySignature(a,checkpoint);if err!=nil{return zero,err}
 if store==nil{return zero,errors.New("FORGE_FSA_PRIVATE_ARCHIVE_MISSING")}
 journal,err:=store.Load();if err!=nil{return zero,fmt.Errorf("FORGE_FSA_ARCHIVE_STRUCTURAL_REJECT: %w",err)}
 if len(journal.Entries)!=int(p.Sequence){
  return zero,errors.New("FORGE_FSA_ARCHIVE_HEAD_SEQUENCE_MISMATCH")
 }
 if journal.Entries[len(journal.Entries)-1].RecordSHA256!=p.HeadSHA256{
  return zero,errors.New("FORGE_FSA_ARCHIVE_SIGNED_HEAD_MISMATCH")
 }
 if a.Sequence>0&&journal.Entries[int(a.Sequence)-1].RecordSHA256!=a.HeadSHA256{
  return zero,errors.New("FORGE_FSA_ARCHIVE_ROLLBACK_OR_FORK")
 }
 for _,record:=range journal.Entries{
  switch record.Event.Kind {
  case researchlog.PrimaryTerminal,researchlog.IndependentReview,researchlog.FinalArchive:
   original,err:=store.ReadOriginal(record.Event.OriginalEvidenceSHA256)
   if err!=nil||len(original)==0{return zero,errors.New("FORGE_FSA_ORIGINAL_EVIDENCE_UNAVAILABLE")}
   // ReadOriginal verifies original content SHA-256. Do not echo private bytes.
   h:=sha256.Sum256(original)
   if hex.EncodeToString(h[:])!=record.Event.OriginalEvidenceSHA256{
    return zero,errors.New("FORGE_FSA_ORIGINAL_EVIDENCE_MISMATCH")
   }
  }
 }
 updated:=a
 updated.PublicKey=append(ed25519.PublicKey(nil),a.PublicKey...)
 updated.Sequence=p.Sequence
 updated.HeadSHA256=p.HeadSHA256
 return updated,nil
}

// CheckpointSignBytesForTest is intentionally NOT exported. Production
// issuance must be supplied by a separately qualified FSA signer in a
// different private authority component; the public reader only verifies.
var _ = strings.TrimSpace
