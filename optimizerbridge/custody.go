package optimizerbridge

// This read-only boundary accepts bytes already exported by the EXISTING
// Cloudflare evidence worker. It creates no Cloudflare client, signer, runner,
// lease or experiment authority. The trust anchor must arrive independently.
import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "strings"
)

const ExportSchema="forge.optimizer.cloud-evidence-export.v1"
const ExportDomain="FORGE-OPTIMIZER-CLOUD-EVIDENCE-V1\x00"
const MaxLaneEvidenceBytes=8<<20

var ErrUnqualifiedExport=errors.New("FORGE_OPTIMIZER_CLOUDFLARE_EVIDENCE_NOT_QUALIFIED")

type EvidenceObject struct {
 Lane string `json:"lane"`
 ObjectKey string `json:"object_key"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 FirstUseLedgerSHA256 string `json:"first_use_ledger_sha256"`
 FirstUseHighWater uint64 `json:"first_use_high_water"`
 SourceBirthLedgerSHA256 string `json:"source_birth_ledger_sha256"`
}
type ExportManifest struct {
 Schema string `json:"schema"`
 Provider string `json:"provider"`
 StoreID string `json:"store_id"`
 Revision uint64 `json:"revision"`
 Objects []EvidenceObject `json:"objects"`
}
type SignedExport struct {
 Manifest ExportManifest `json:"manifest"`
 SignatureHex string `json:"signature_hex"`
}
// ExternalTrust must NOT be generated from the export, Cloudflare object,
// working repository or this CI job. Provisioning and independent source
// custody lie outside this verifier.
type ExternalTrust struct {
 StoreID string `json:"store_id"`
 ManifestSHA256 string `json:"manifest_sha256"`
 CustodianEd25519PublicKeyHex string `json:"custodian_ed25519_public_key_hex"`
 MinimumRevision uint64 `json:"minimum_revision"`
 WinglessFirstUseLedgerSHA256 string `json:"wingless_first_use_ledger_sha256"`
 WinglessFirstUseHighWater uint64 `json:"wingless_first_use_high_water"`
 WinglessSourceBirthLedgerSHA256 string `json:"wingless_source_birth_ledger_sha256"`
 YggdrasilFirstUseLedgerSHA256 string `json:"yggdrasil_first_use_ledger_sha256"`
 YggdrasilFirstUseHighWater uint64 `json:"yggdrasil_first_use_high_water"`
 YggdrasilSourceBirthLedgerSHA256 string `json:"yggdrasil_source_birth_ledger_sha256"`
}
// This record deliberately does NOT claim actual remote read, independent
// operational key custody, complete historical first-use, or scientific gain.
type ExportReview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 ManifestSHA256 string `json:"manifest_sha256"`
 SourceDigestAndCustodySignatureVerified bool `json:"source_digest_and_custody_signature_verified"`
 RemoteReadOperationallyWitnessed bool `json:"remote_read_operationally_witnessed"`
 CompleteFirstUseReconciliationVerified bool `json:"complete_first_use_reconciliation_verified"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
 Shadow Report `json:"shadow"`
 SelectionAudits []SelectionAuditReview `json:"selection_audits,omitempty"`
 HistoricalComparisons []HistoricalComparison `json:"historical_comparisons,omitempty"`
}

func shaHex(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func digestOK(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if c<'0'||c>'9'{if c<'a'||c>'f'{return false}}}
 return true
}
func objectKeyOK(s string)bool{
 if len(s)<3||len(s)>512||strings.HasPrefix(s,"/")||strings.Contains(s,"\\")||strings.Contains(s,"//"){return false}
 for _,part:=range strings.Split(s,"/"){
  if part==""||part=="."||part==".."{return false}
 }
 for _,c:=range s{
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'||c=='/'){return false}
 }
 return true
}
func decodeCanonical(raw []byte,out any)error{
 if len(raw)==0||len(raw)>MaxLaneEvidenceBytes{return ErrUnqualifiedExport}
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 if err:=d.Decode(out);err!=nil{return ErrUnqualifiedExport}
 var extra any
 if err:=d.Decode(&extra);err!=io.EOF{return ErrUnqualifiedExport}
 canonical,err:=json.Marshal(out)
 if err!=nil||!bytes.Equal(canonical,raw){return ErrUnqualifiedExport}
 return nil
}
// verifyPinnedExportInputs authenticates both immutable lane objects and
// externally held source/first-use pins BEFORE any optimizer evaluation.
// It is side-effect-free, does not assert independent physical custody and
// never infers permission to start or select a scientific original.
func verifyPinnedExportInputs(signed SignedExport,trust ExternalTrust,raw [2][]byte,pins []LanePins)([2]LaneEvidence,error){
 var zero [2]LaneEvidence
 m:=signed.Manifest
 if m.Schema!=ExportSchema||m.Provider!="CLOUDFLARE_EXISTING"||
  len(m.StoreID)<4||len(m.StoreID)>128||m.StoreID!=trust.StoreID||
  m.Revision==0||trust.MinimumRevision==0||m.Revision<trust.MinimumRevision||
  len(m.Objects)!=2||!digestOK(trust.ManifestSHA256,64)||
  !digestOK(trust.CustodianEd25519PublicKeyHex,64)||
  !digestOK(signed.SignatureHex,128)||len(pins)!=2{
  return zero,ErrUnqualifiedExport
 }
 payload,err:=json.Marshal(m)
 if err!=nil||shaHex(payload)!=trust.ManifestSHA256{return zero,ErrUnqualifiedExport}
 pk,_:=hex.DecodeString(trust.CustodianEd25519PublicKeyHex)
 sig,_:=hex.DecodeString(signed.SignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(pk),append([]byte(ExportDomain),payload...),sig){return zero,ErrUnqualifiedExport}
 if pins[0].IndependentEd25519PublicKeyHex==trust.CustodianEd25519PublicKeyHex||
  pins[1].IndependentEd25519PublicKeyHex==trust.CustodianEd25519PublicKeyHex {
  return zero,ErrUnqualifiedExport
 }
 wantLane:=[]string{"Wingless","Yggdrasil"}
 wantLedger:=[]string{trust.WinglessFirstUseLedgerSHA256,trust.YggdrasilFirstUseLedgerSHA256}
 wantHigh:=[]uint64{trust.WinglessFirstUseHighWater,trust.YggdrasilFirstUseHighWater}
 wantBirth:=[]string{trust.WinglessSourceBirthLedgerSHA256,trust.YggdrasilSourceBirthLedgerSHA256}
 var evidence [2]LaneEvidence
 for i,obj:=range m.Objects{
  if obj.Lane!=wantLane[i]||pins[i].Lane!=obj.Lane||
   !objectKeyOK(obj.ObjectKey)||!digestOK(obj.EvidenceSHA256,64)||
   shaHex(raw[i])!=obj.EvidenceSHA256||
   !digestOK(obj.FirstUseLedgerSHA256,64)||
   !digestOK(obj.SourceBirthLedgerSHA256,64)||obj.SourceBirthLedgerSHA256!=wantBirth[i]||
   obj.FirstUseLedgerSHA256!=wantLedger[i]||
   obj.FirstUseHighWater==0||obj.FirstUseHighWater!=wantHigh[i]{
    return zero,fmt.Errorf("%w:lane_%s",ErrUnqualifiedExport,wantLane[i])
  }
  var e LaneEvidence
  if err:=decodeCanonical(raw[i],&e);err!=nil||e.Lane!=obj.Lane{return zero,ErrUnqualifiedExport}
  evidence[i]=e
 }
 if m.Objects[0].ObjectKey==m.Objects[1].ObjectKey||
  m.Objects[0].EvidenceSHA256==m.Objects[1].EvidenceSHA256||
  m.Objects[0].FirstUseLedgerSHA256==m.Objects[1].FirstUseLedgerSHA256||
  m.Objects[0].SourceBirthLedgerSHA256==m.Objects[1].SourceBirthLedgerSHA256{
  return zero,ErrUnqualifiedExport
 }
 return evidence,nil
}

// EvaluatePinnedExport retains the source-compatible read-only shadow API.
// All immutable inputs are validated before the five historical optimizers.
func EvaluatePinnedExport(signed SignedExport,trust ExternalTrust,raw [2][]byte,pins []LanePins)(ExportReview,error){
 var zero ExportReview
 evidence,err:=verifyPinnedExportInputs(signed,trust,raw,pins)
 if err!=nil{return zero,err}
 report,err:=EvaluatePair(evidence[:],pins)
 if err!=nil{return zero,fmt.Errorf("%w: %v",ErrUnqualifiedExport,err)}
 if report.DispatchAuthorized||report.ScientificAccepted||report.ScientificImprovementEstablished||
  report.FirstUseConsumed||report.ScienceOriginalsExecuted!=0{return zero,ErrUnqualifiedExport}
 return ExportReview{
  Schema:"forge.optimizer.cloud-export-review.v1",
  Mode:"SIGNED_PINNED_HISTORICAL_SHADOW_NOT_REMOTE_OR_SCIENTIFIC_ACCEPTANCE",
  ManifestSHA256:trust.ManifestSHA256,
  SourceDigestAndCustodySignatureVerified:true,
  Shadow:report,
 },nil
}
