package fsaprovision

// Read-only verification of independently signed records of externally run
// failure drills. Neither the signature nor this code proves physical
// independence, truthful observations, or hardware-backed durability.

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
)

const (
 DrillSchema = "forge.fsa.physical-drill-report.v1"
 drillDomain = "FORGE-FSA-PHYSICAL-DRILL-REPORT-V1\n"
 MaxDrillBytes = 16384
 CaseAuthorityLoss = "authority-host-loss"
 CaseWitnessLoss = "witness-host-loss"
 CaseFloorLoss = "floor-host-loss"
 CasePartition = "authority-witness-partition"
 CaseHostReplacement = "authority-host-replacement"
)
var ErrDrillUnverified = errors.New("FORGE_FSA_DRILL_REPORT_UNTRUSTED_OR_INCOMPLETE")

// All pins must be acquired outside the report under independent operator
// control. The expected report digest is bound to the complete signed bytes.
type DrillPin struct {
 ChallengeSHA256 string
 SourceCommitSHA string
 ReportSHA256 string
 AuditorPublicKey ed25519.PublicKey
}
type FaultRecord struct {
 Case string `json:"case"`
 ChallengeSHA256 string `json:"challenge_sha256"`
 BeforeHeadSHA256 string `json:"before_head_sha256"`
 AfterHeadSHA256 string `json:"after_head_sha256"`
 BeforeFloorRevision uint64 `json:"before_floor_revision"`
 AfterFloorRevision uint64 `json:"after_floor_revision"`
 IsolationTraceSHA256 string `json:"isolation_trace_sha256"`
 RecoveryTraceSHA256 string `json:"recovery_trace_sha256"`
 ExternalRetentionSHA256 string `json:"external_retention_sha256"`
 FailClosedObserved bool `json:"fail_closed_observed"`
 NoReplayObserved bool `json:"no_replay_observed"`
 NoUnauthorizedAdvanceObserved bool `json:"no_unauthorized_advance_observed"`
 ReplacementProvisionSHA256 string `json:"replacement_provision_sha256,omitempty"`
}
type DrillReport struct {
 Schema string `json:"schema"`
 SourceCommitSHA string `json:"source_commit_sha"`
 BundleSHA256 string `json:"bundle_sha256"`
 ArchiveID string `json:"archive_id"`
 ProvisioningEpoch uint64 `json:"provisioning_epoch"`
 ChallengeSHA256 string `json:"challenge_sha256"`
 Cases []FaultRecord `json:"cases"`
}
type SignedDrillReport struct {
 Report DrillReport `json:"report"`
 AuditorSignatureHex string `json:"auditor_signature_hex"`
}
// VerifiedDrillDocument means only that signed, pre-pinned, internally
// consistent documentary evidence passed checks. It is NOT an acceptance,
// deployment, physical-independence or scientific-execution credential.
type VerifiedDrillDocument struct {
 ReportSHA256 string
 BundleSHA256 string
 ChallengeSHA256 string
 CheckedCases int
}
func caseOrder() []string {
 return []string{CaseAuthorityLoss, CaseWitnessLoss, CaseFloorLoss, CasePartition, CaseHostReplacement}
}
func hex40(v string) bool {
 if len(v)!=40{return false}
 for _,c:=range v {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func sha256Text(data []byte) string {
 sum:=sha256.Sum256(data)
 return hex.EncodeToString(sum[:])
}
// VerifyDrillReport performs no I/O, mutating writes, retries, network
// requests, host inspection or scheduling. It depends on a provisioning
// bundle already verified against an external immutable pin.
func (v *Verifier) VerifyDrillReport(bundle Bundle, pin DrillPin, signed SignedDrillReport) (VerifiedDrillDocument,error) {
 fail:=func()(VerifiedDrillDocument,error){return VerifiedDrillDocument{},ErrDrillUnverified}
 if v==nil||len(pin.AuditorPublicKey)!=ed25519.PublicKeySize||
  !hex64(pin.ChallengeSHA256)||!hex64(pin.ReportSHA256)||!hex40(pin.SourceCommitSHA){return fail()}
 if bytes.Equal(pin.AuditorPublicKey,v.pin.AuthorityAttestor)||
  bytes.Equal(pin.AuditorPublicKey,v.pin.WitnessAttestor)||
  bytes.Equal(pin.AuditorPublicKey,v.pin.FloorAttestor){return fail()}
 desc,err:=v.Verify(bundle)
 if err!=nil{return fail()}
 r:=signed.Report
 if r.Schema!=DrillSchema||r.SourceCommitSHA!=pin.SourceCommitSHA||
  r.BundleSHA256!=desc.BundleSHA256||r.ArchiveID!=desc.ArchiveID||
  r.ProvisioningEpoch!=desc.ProvisioningEpoch||r.ChallengeSHA256!=pin.ChallengeSHA256||
  len(r.Cases)!=len(caseOrder()){return fail()}
 for i,c:=range r.Cases {
  if c.Case!=caseOrder()[i]||c.ChallengeSHA256!=pin.ChallengeSHA256||
   !hex64(c.BeforeHeadSHA256)||!hex64(c.AfterHeadSHA256)||
   !hex64(c.IsolationTraceSHA256)||!hex64(c.RecoveryTraceSHA256)||
   !hex64(c.ExternalRetentionSHA256)||c.BeforeFloorRevision==0||
   c.AfterFloorRevision<c.BeforeFloorRevision||!c.FailClosedObserved||
   !c.NoReplayObserved||!c.NoUnauthorizedAdvanceObserved {return fail()}
  // These drills prohibit an accepted science transition during a
  // fault. A changed head must remain withheld, not reported as
  // a successful recovery; independently reconcile it elsewhere.
  if c.BeforeHeadSHA256!=c.AfterHeadSHA256||
   c.BeforeFloorRevision!=c.AfterFloorRevision{return fail()}
  if c.Case==CaseHostReplacement {
   if !hex64(c.ReplacementProvisionSHA256)||
    c.ReplacementProvisionSHA256==desc.BundleSHA256 {return fail()}
  } else if c.ReplacementProvisionSHA256!="" {return fail()}
 }
 rawReport,err:=json.Marshal(r)
 if err!=nil{return fail()}
 sig,err:=hex.DecodeString(signed.AuditorSignatureHex)
 if err!=nil||len(sig)!=ed25519.SignatureSize||
  !ed25519.Verify(pin.AuditorPublicKey,append([]byte(drillDomain),rawReport...),sig){return fail()}
 rawSigned,err:=json.Marshal(signed)
 if err!=nil||sha256Text(rawSigned)!=pin.ReportSHA256{return fail()}
 return VerifiedDrillDocument{ReportSHA256:pin.ReportSHA256,
  BundleSHA256:desc.BundleSHA256,ChallengeSHA256:pin.ChallengeSHA256,
  CheckedCases:len(r.Cases)},nil
}
// VerifyDrillJSON prohibits alternate encodings and unknown/duplicate keys by
// requiring byte-for-byte canonical encoding after strict schema decode.
func (v *Verifier) VerifyDrillJSON(bundle Bundle,pin DrillPin,raw []byte)(VerifiedDrillDocument,error){
 if len(raw)==0||len(raw)>MaxDrillBytes {return VerifiedDrillDocument{},ErrDrillUnverified}
 var signed SignedDrillReport
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(&signed);err!=nil{return VerifiedDrillDocument{},ErrDrillUnverified}
 var extra any
 if dec.Decode(&extra)!=io.EOF{return VerifiedDrillDocument{},ErrDrillUnverified}
 canonical,err:=json.Marshal(signed)
 if err!=nil||!bytes.Equal(canonical,raw){return VerifiedDrillDocument{},ErrDrillUnverified}
 return v.VerifyDrillReport(bundle,pin,signed)
}
