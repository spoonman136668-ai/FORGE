package hybridrunnerpreview

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
)

// CustodyReferences are untrusted identifiers. Full evidence custody, source
// and first-use verification MUST occur in separately qualified native
// authority. A reference hash or claimed signer identity proves none of them.
type CustodyReferences struct {
 Repository string `json:"repository"`
 SourceSHA string `json:"source_sha"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 SignedAttestationSHA256 string `json:"signed_attestation_sha256"`
 ArtifactSHA256 string `json:"artifact_sha256"`
 ClaimedSignerKeySHA256 string `json:"claimed_signer_key_sha256"`
 ClaimedOriginalLedgerHeadSHA256 string `json:"claimed_original_ledger_head_sha256"`
}
const HandoffSchema="forge.hybrid.disabled-evidence-handoff.v1"
const HandoffMode="OFFLINE_REFS_ONLY_NO_DISPATCH_OR_FIRST_USE_PROOF"

type Handoff struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Repository string `json:"repository"`
 RequestSHA256 string `json:"request_sha256"`
 ReviewStatus string `json:"review_status"`
 ReviewReason string `json:"review_reason"`
 CustodyReferencesSHA256 string `json:"custody_references_sha256"`
 TargetRunner string `json:"target_runner"`
 RequiresIndependentSourceAndFirstUseWitness bool `json:"requires_independent_source_and_first_use_witness"`
 SourceAuthenticated bool `json:"source_authenticated"`
 FirstUseAuthenticated bool `json:"first_use_authenticated"`
 GPUReserved bool `json:"gpu_reserved"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 HandoffSHA256 string `json:"handoff_sha256"`
}
func handoffHash(h Handoff)string{
 h.HandoffSHA256=""
 b,_:=json.Marshal(h)
 s:=sha256.Sum256(append([]byte("FORGE-HYBRID-DISABLED-HANDOFF-V1\n"),b...))
 return hex.EncodeToString(s[:])
}
func custodyHash(c CustodyReferences)string{
 b,_:=json.Marshal(c)
 s:=sha256.Sum256(append([]byte("FORGE-HYBRID-CUSTODY-REFS-V1\n"),b...))
 return hex.EncodeToString(s[:])
}
func validRefs(c CustodyReferences,req Request)bool{
 return c.Repository==Project&&c.SourceSHA==req.SourceSHA&&
  c.ProtocolSHA256==req.ProtocolSHA256&&
  isLowerHex(c.SignedAttestationSHA256,64)&&
  isLowerHex(c.ArtifactSHA256,64)&&
  isLowerHex(c.ClaimedSignerKeySHA256,64)&&
  isLowerHex(c.ClaimedOriginalLedgerHeadSHA256,64)
}
// BuildDisabledHandoff joins exact-request planning output and syntactic
// evidence references. It does not verify signatures, GitHub, complete
// ledgers, worker identity, or available compute; no runner API is invoked.
func BuildDisabledHandoff(req Request,review Result,refs CustodyReferences)(Handoff,error){
 var zero Handoff
 if !validRequest(req)||AssertNonAuthorizing(review)!=nil||
  review.RequestSHA256!=newResult(req,nil).RequestSHA256||
  !validRefs(refs,req){return zero,ErrBlocked}
 h:=Handoff{
  Schema:HandoffSchema,Mode:HandoffMode,Repository:Project,
  RequestSHA256:review.RequestSHA256,
  ReviewStatus:review.Status,ReviewReason:review.Reason,
  CustodyReferencesSHA256:custodyHash(refs),TargetRunner:RunnerName,
  RequiresIndependentSourceAndFirstUseWitness:true,
 }
 h.HandoffSHA256=handoffHash(h)
 return h,nil
}
func VerifyDisabledHandoff(h Handoff)error{
 if h.Schema!=HandoffSchema||h.Mode!=HandoffMode||h.Repository!=Project||
  h.TargetRunner!=RunnerName||!isLowerHex(h.RequestSHA256,64)||
  !isLowerHex(h.CustodyReferencesSHA256,64)||
  !isLowerHex(h.HandoffSHA256,64)||h.HandoffSHA256!=handoffHash(h)||
  !validReason(h.ReviewStatus,h.ReviewReason)||
  !h.RequiresIndependentSourceAndFirstUseWitness||
  h.SourceAuthenticated||h.FirstUseAuthenticated||h.GPUReserved||
  h.ExecutionAuthorized{return ErrBlocked}
 return nil
}
