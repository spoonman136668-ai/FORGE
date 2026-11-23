// Package sourcebirth verifies two separately pinned signatures over a
// prospective source-birth statement, without granting execution authority.
package sourcebirth

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)
const (
 Schema="forge.sourcebirth.signed-birth.v1"
 IssuerDomain="FORGE-SOURCE-BIRTH-ISSUER-V1\n"
 WitnessDomain="FORGE-SOURCE-BIRTH-INDEPENDENT-WITNESS-V1\n"
 ObservationSchema="forge.sourcebirth.readonly-observation.v1"
)
var ErrUntrusted=errors.New("FORGE_SOURCE_BIRTH_INDEPENDENT_CUSTODY_UNPROVEN")
type Statement struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Repository string `json:"repository"`
 OriginalID string `json:"original_id"`
 SourceCommitSHA string `json:"source_commit_sha"`
 SourceTreeSHA string `json:"source_tree_sha"`
 PreregSHA256 string `json:"prereg_sha256"`
 CohortSHA256 string `json:"cohort_sha256"`
 ArchiveSHA256 string `json:"archive_sha256"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BirthSequence uint64 `json:"birth_sequence"`
 WitnessRevision uint64 `json:"witness_revision"`
 FrozenUnix uint64 `json:"frozen_unix"`
 BirthUnix uint64 `json:"birth_unix"`
}
type Signed struct {
 Statement Statement `json:"statement"`
 IssuerSignatureHex string `json:"issuer_signature_hex"`
 WitnessSignatureHex string `json:"witness_signature_hex"`
}
type Pins struct {
 Lane string
 OriginalID string
 SourceCommitSHA string
 SourceTreeSHA string
 PreregSHA256 string
 CohortSHA256 string
 ArchiveSHA256 string
 AuthorityEpoch uint64
 MinBirthSequence uint64
 MinWitnessRevision uint64
 IssuerPublicKey ed25519.PublicKey
 WitnessPublicKey ed25519.PublicKey
}
type Observation struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 BirthSHA256 string `json:"birth_sha256"`
 BirthSequence uint64 `json:"birth_sequence"`
 WitnessRevision uint64 `json:"witness_revision"`
 TwoSignaturesVerified bool `json:"two_signatures_verified"`
 PhysicallyIndependent bool `json:"physically_independent"`
 PersistentFirstUseProven bool `json:"persistent_first_use_proven"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 CutoverAuthorized bool `json:"cutover_authorized"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='-'||c=='_'){return false}}
 return true
}
func repo(lane string)string{
 if lane=="Wingless"||lane=="Yggdrasil"{return "spoonman136668-ai/"+lane}
 return ""
}
func signedPayload(domain string,s Statement)[]byte{
 b,_:=json.Marshal(s)
 return append([]byte(domain),b...)
}
func verifySignature(domain string,s Statement,signatureHex string,key ed25519.PublicKey)bool{
 if !validHex(signatureHex,128)||len(key)!=ed25519.PublicKeySize{return false}
 sig,err:=hex.DecodeString(signatureHex)
 return err==nil&&ed25519.Verify(key,signedPayload(domain,s),sig)
}
// Verify checks two role-separated Ed25519 signatures over exact independently
// supplied expected identities. Hash/signature proof does NOT certify physical
// signer independence, real source creation, durable high-water or first-use.
func Verify(s Signed,p Pins)(Observation,error){
 var zero Observation
 b:=s.Statement
 if repo(p.Lane)==""||b.Schema!=Schema||b.Lane!=p.Lane||
 b.Repository!=repo(p.Lane)||!validID(b.OriginalID)||b.OriginalID!=p.OriginalID||
 !validHex(b.SourceCommitSHA,40)||!validHex(b.SourceTreeSHA,40)||
 !validHex(b.PreregSHA256,64)||!validHex(b.CohortSHA256,64)||!validHex(b.ArchiveSHA256,64)||
 b.SourceCommitSHA!=p.SourceCommitSHA||b.SourceTreeSHA!=p.SourceTreeSHA||
 b.PreregSHA256!=p.PreregSHA256||b.CohortSHA256!=p.CohortSHA256||
 b.ArchiveSHA256!=p.ArchiveSHA256||b.AuthorityEpoch==0||b.AuthorityEpoch!=p.AuthorityEpoch||
 b.BirthSequence==0||p.MinBirthSequence==0||b.BirthSequence<p.MinBirthSequence||
 b.WitnessRevision==0||p.MinWitnessRevision==0||b.WitnessRevision<p.MinWitnessRevision||
 b.FrozenUnix==0||b.BirthUnix<=b.FrozenUnix||
 len(p.IssuerPublicKey)!=ed25519.PublicKeySize||len(p.WitnessPublicKey)!=ed25519.PublicKeySize||
 bytes.Equal(p.IssuerPublicKey,p.WitnessPublicKey)||
 !verifySignature(IssuerDomain,b,s.IssuerSignatureHex,p.IssuerPublicKey)||
 !verifySignature(WitnessDomain,b,s.WitnessSignatureHex,p.WitnessPublicKey){
  return zero,ErrUntrusted
 }
 raw,_:=json.Marshal(s)
 h:=sha256.Sum256(append([]byte("FORGE-SOURCE-BIRTH-READONLY-V1\n"),raw...))
 return Observation{Schema:ObservationSchema,Lane:b.Lane,OriginalID:b.OriginalID,
  BirthSHA256:hex.EncodeToString(h[:]),BirthSequence:b.BirthSequence,
  WitnessRevision:b.WitnessRevision,TwoSignaturesVerified:true},nil
}
