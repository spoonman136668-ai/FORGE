// Package retentiongate verifies externally provided backup bytes and two
// independent signatures. It cannot establish independent operational control
// of either signer and never grants scientific first-use/acceptance authority.
package retentiongate

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "strings"
 "time"
)
const ReceiptSchema="forge.external-original-retention-receipt.v1"
const AnchorSchema="forge.external-retention-trust-anchor.v1"
var ErrBlocked=errors.New("FORGE_LONG_TERM_RETENTION_OR_INDEPENDENT_CUSTODY_UNVERIFIED")
type Trust struct {
 Schema string `json:"schema"`
 ResearchAuthorityPub string `json:"research_authority_public_key"`
 StorageCustodianPub string `json:"storage_custodian_public_key"`
 MinimumRevision uint64 `json:"minimum_revision"`
}
type Claim struct{
 Repository string `json:"repository"`
 Experiment string `json:"experiment"`
 RunID uint64 `json:"run_id"`
 ArtifactID uint64 `json:"artifact_id"`
 OriginalZIP_SHA256 string `json:"original_zip_sha256"`
 BackupZIP_SHA256 string `json:"backup_zip_sha256"`
 StorageObjectID string `json:"storage_object_id"`
 RetainUntil string `json:"retain_until"`
 Revision uint64 `json:"revision"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Claim Claim `json:"claim"`
 AuthoritySignature string `json:"authority_signature"`
 CustodianSignature string `json:"custodian_signature"`
}
type Report struct{
 Schema string `json:"schema"`
 SourceRunID uint64 `json:"source_run_id"`
 SourceArtifactID uint64 `json:"source_artifact_id"`
 BackupObjectID string `json:"backup_object_id"`
 SourceAndReplicaSHA256 string `json:"source_and_replica_sha256"`
 SignedReceiptCryptographicallyValid bool `json:"signed_receipt_cryptographically_valid"`
 ReplicaBytesRestoredAndMatched bool `json:"replica_bytes_restored_and_matched"`
 ExternalTrustRootsOperationallyIndependent bool `json:"external_trust_roots_operationally_independent"`
 RetentionDurabilityAcrossFailuresProven bool `json:"retention_durability_across_failures_proven"`
 FirstUseAuthenticated bool `json:"first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
// Reject recursive duplicate/case-aliased JSON keys before Go's decoder
// can apply last-key-wins to a purported external trust root or receipt.
func uniqueJSON(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw))
 var visit func(int)bool
 visit=func(depth int)bool{
  if depth>32{return false}
  t,err:=d.Token();if err!=nil{return false}
  delim,ok:=t.(json.Delim);if !ok{return true}
  if delim!='{'&&delim!='['{return false}
  keys:=map[string]bool{}
  for d.More(){
   if delim=='{'{
    k,err:=d.Token();if err!=nil{return false}
    name,ok:=k.(string);if !ok||len(name)==0||len(name)>128{return false}
    canonical:=strings.ToLower(name)
    if keys[canonical]{return false};keys[canonical]=true
   }
   if !visit(depth+1){return false}
  }
  end,err:=d.Token();return err==nil&&end==json.Delim(map[json.Delim]rune{'{':'}','[':']'}[delim])
 }
 if !visit(0){return false}
 _,err:=d.Token();return err==io.EOF
}
func parse(raw []byte,dest any)bool{
 if len(raw)==0||len(raw)>4096||!uniqueJSON(raw){return false}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 return d.Decode(dest)==nil&&d.Decode(new(any))==io.EOF
}
func decodeHex(s string,n int)([]byte,bool){
 if len(s)!=2*n{return nil,false}
 b,err:=hex.DecodeString(s);return b,err==nil&&len(b)==n
}
func signBytes(role string,claim Claim)[]byte{
 b,_:=json.Marshal(claim)
 sum:=sha256.Sum256(append([]byte("FORGE_EXTERNAL_RETENTION_V1:"+role+":"),b...))
 return sum[:]
}
// Verify requires actual recovered backup bytes, not a backup object ID alone.
// The anchor must itself come from an independently protected control plane,
// not a repository file, workflow environment variable, or self-signed source.
// Passing this function verifies cryptographic consistency only.
func Verify(anchorRaw,receiptRaw,originalZIP,recoveredZIP []byte,asOf time.Time)(Report,error){
 var zero Report
 var t Trust;var r Receipt
 if !parse(anchorRaw,&t)||!parse(receiptRaw,&r)||t.Schema!=AnchorSchema||r.Schema!=ReceiptSchema{return zero,ErrBlocked}
 owner,ok:=decodeHex(t.ResearchAuthorityPub,ed25519.PublicKeySize);if !ok{return zero,ErrBlocked}
 custodian,ok:=decodeHex(t.StorageCustodianPub,ed25519.PublicKeySize);if !ok||bytes.Equal(owner,custodian){return zero,ErrBlocked}
 a,ok:=decodeHex(r.AuthoritySignature,ed25519.SignatureSize);if !ok{return zero,ErrBlocked}
 c,ok:=decodeHex(r.CustodianSignature,ed25519.SignatureSize);if !ok{return zero,ErrBlocked}
 p:=r.Claim
 if p.Repository!="spoonman136668-ai/Wingless"&&p.Repository!="spoonman136668-ai/Yggdrasil"{return zero,ErrBlocked}
 if p.RunID==0||p.ArtifactID==0||p.Revision==0||p.Revision<t.MinimumRevision||len(p.Experiment)<1||len(p.Experiment)>96||
  !strings.HasPrefix(p.StorageObjectID,"external://")||len(p.StorageObjectID)>256||strings.ContainsAny(p.StorageObjectID,"\n\r\x00"){return zero,ErrBlocked}
 for _,ch:=range p.Experiment{if !(ch>='A'&&ch<='Z'||ch>='a'&&ch<='z'||ch>='0'&&ch<='9'||ch=='-'||ch=='_'){return zero,ErrBlocked}}
 want,ok:=decodeHex(p.OriginalZIP_SHA256,sha256.Size);if !ok{return zero,ErrBlocked}
 backup,ok:=decodeHex(p.BackupZIP_SHA256,sha256.Size);if !ok||!bytes.Equal(want,backup){return zero,ErrBlocked}
 if len(originalZIP)==0||len(recoveredZIP)==0||len(originalZIP)>8<<20||len(recoveredZIP)>8<<20{return zero,ErrBlocked}
 gotOriginal:=sha256.Sum256(originalZIP);gotBackup:=sha256.Sum256(recoveredZIP)
 if !bytes.Equal(gotOriginal[:],want)||!bytes.Equal(gotBackup[:],backup){return zero,ErrBlocked}
 until,err:=time.Parse("2006-01-02",p.RetainUntil)
 if err!=nil||until.Before(asOf.AddDate(1,0,0))||until.Year()>2100{return zero,ErrBlocked}
 if !ed25519.Verify(owner,signBytes("research-authority",p),a)||
  !ed25519.Verify(custodian,signBytes("storage-custodian",p),c){return zero,ErrBlocked}
 return Report{Schema:"forge.external-retention-offline-verification.v1",SourceRunID:p.RunID,SourceArtifactID:p.ArtifactID,
  BackupObjectID:p.StorageObjectID,SourceAndReplicaSHA256:p.OriginalZIP_SHA256,
  SignedReceiptCryptographicallyValid:true,ReplicaBytesRestoredAndMatched:true},nil
}
