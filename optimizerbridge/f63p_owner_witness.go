package optimizerbridge

// F63P binds prospectively prepared exact 1/6 policy-arm assignments to
// externally pinned, independently signed OWNER witness claims, then
// delegates scientific source admission to the existing Trust interface.
//
// This read-only parser cannot establish that an externally signed record
// was genuinely recorded before the original. The separately authorized
// owner must attest independent monotonic first-use custody and timing;
// signatures, hashes and test-only Trusts are NOT that operational evidence.
import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

const F63PWitnessSchema="forge.optimizer.f63p.existing-owner-predecision-witness.v1"
const F63PDomain="FORGE-F63P-EXISTING-OWNER-WITNESS-V1\x00"
var ErrF63P=errors.New("FORGE_F63P_INDEPENDENT_OWNER_FIRSTUSE_WITNESS_NOT_QUALIFIED")

type F63PWitnessRecord struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 AssignmentSHA256 string `json:"assignment_sha256"`
 OwnerSourceSHA string `json:"owner_source_sha"`
 OwnerDecisionSequence uint64 `json:"owner_decision_sequence"`
 FirstUseReceiptSHA256 string `json:"first_use_receipt_sha256"`
 OriginalReceiptSHA256 string `json:"original_receipt_sha256"`
 CandidateSlateSHA256 string `json:"candidate_slate_sha256"`
 SourceFamilySHA256 string `json:"source_family_sha256"`
 BudgetCommitmentSHA256 string `json:"budget_commitment_sha256"`
 FirstUseLedgerHeadSHA256 string `json:"first_use_ledger_head_sha256"`
 FirstUseLedgerHighWater uint64 `json:"first_use_ledger_high_water"`
}
type F63PSignedWitness struct {
 Record F63PWitnessRecord `json:"record"`
 SignatureHex string `json:"signature_hex"`
}
// Pin must come from an independently authenticated existing owner source,
// never the signed record, FORGE branch, or its GitHub CI result itself.
type F63PExternalPin struct {
 Lane string
 SignedRecordSHA256 string
 WitnessPublicKeyHex string
 FirstUseLedgerHeadSHA256 string
 MinimumFirstUseLedgerHighWater uint64
}
type F63PResearchIntake struct {
 Nomination F59PolicyNomination
 OwnerSelection ProspectiveSelection
 Trial F62PTrial
 Witness F63PSignedWitness
 ExternalPin F63PExternalPin
}
type F63PReadOnlyReview struct {
 Schema string `json:"schema"`
 Lanes []string `json:"lanes"`
 ExternallyPinnedWitnessSignaturesVerified bool `json:"externally_pinned_witness_signatures_verified"`
 ExistingOwnerTrustInterfaceAcceptedClaims bool `json:"existing_owner_trust_interface_accepted_claims"`
 ExactPolicyArmPropensityNumerator int `json:"exact_policy_arm_propensity_numerator"`
 ExactPolicyArmPropensityDenominator int `json:"exact_policy_arm_propensity_denominator"`
 IndependentlyProvenPreOutcomeTiming bool `json:"independently_proven_pre_outcome_timing"`
 IndependentlyVerifiedMonotonicFirstUse bool `json:"independently_verified_monotonic_first_use"`
 NewOriginalDispatchAuthorized bool `json:"new_original_dispatch_authorized"`
 CausalComparisonAuthorized bool `json:"causal_comparison_authorized"`
 DreamParetoActivationAuthorized bool `json:"dream_pareto_activation_authorized"`
 ThetaWeightUpdateAuthorized bool `json:"theta_weight_update_authorized"`
 Status string `json:"status"`
}

func f63PHash(raw []byte)string{
 digest:=sha256.Sum256(raw)
 return hex.EncodeToString(digest[:])
}
func f63PVerifyWitness(l F63PResearchIntake)error{
 w:=l.Witness.Record
 p:=l.ExternalPin
 t:=l.Trial
 a:=t.Assignment
 s:=l.OwnerSelection
 n:=l.Nomination
 if w.Schema!=F63PWitnessSchema||
  w.Lane!=n.Lane||p.Lane!=n.Lane||
  w.AssignmentSHA256!=a.AssignmentSHA256||
  w.OwnerSourceSHA!=n.PredecisionOwnerSourceSHA||
  w.OwnerDecisionSequence!=t.OwnerDecisionSequence||
  w.FirstUseReceiptSHA256!=s.FirstUseReceiptSHA256||
  w.OriginalReceiptSHA256!=t.OriginalReceiptSHA256||
  w.CandidateSlateSHA256!=a.PublicCandidateSlateSHA256||
  w.SourceFamilySHA256!=a.PublicSourceFamilySHA256||
  w.BudgetCommitmentSHA256!=a.BudgetCommitmentSHA256||
  !f59Hex(w.FirstUseLedgerHeadSHA256,64)||
  w.FirstUseLedgerHeadSHA256!=p.FirstUseLedgerHeadSHA256||
  p.MinimumFirstUseLedgerHighWater==0||
  w.FirstUseLedgerHighWater<p.MinimumFirstUseLedgerHighWater||
  w.FirstUseLedgerHighWater<t.OwnerDecisionSequence||
  !f59Hex(p.SignedRecordSHA256,64)||
  !f59Hex(p.WitnessPublicKeyHex,64)||
  !f59Hex(l.Witness.SignatureHex,128)||
  s.Lane!=n.Lane||
  s.FrozenDreamPolicySHA256!=n.DreamPolicySHA256||
  s.FrozenParetoPolicySHA256!=n.ParetoPolicySHA256||
  s.PreregistrationSHA256!=n.OwnerPreregistrationSHA256||
  s.ProspectiveSourceSHA!=n.PredecisionOwnerSourceSHA||
  s.RandomizationAuditSHA256!=p.SignedRecordSHA256 {
  return ErrF63P
 }
 canonical,err:=json.Marshal(w)
 if err!=nil||f63PHash(canonical)!=p.SignedRecordSHA256{return ErrF63P}
 pub,_:=hex.DecodeString(p.WitnessPublicKeyHex)
 sig,_:=hex.DecodeString(l.Witness.SignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(pub),append([]byte(F63PDomain),canonical...),sig){
  return ErrF63P
 }
 return nil
}

// ObserveF63PExistingOwner is read-only: two independently authenticated
// source claims and two separately pinned witness records are necessary.
// Neither the signed witness nor the caller-provided trust verifier proves
// *when* the predecision was admitted or whether the real existing owner
// atomically consumed first-use. Those require live external verification.
// Consequently even fully signature-matching input NEVER activates a policy.
func ObserveF63PExistingOwner(f F58Freeze,lanes []F63PResearchIntake,trust Trust)(F63PReadOnlyReview,error){
 var zero F63PReadOnlyReview
 if trust==nil||len(lanes)!=2||lanes[0].Nomination.Lane!="Wingless"||
  lanes[1].Nomination.Lane!="Yggdrasil" {
  return zero,ErrF63P
 }
 n0,n1:=lanes[0].Nomination,lanes[1].Nomination
 enrolled,err:=PreviewEnrollment(f,[]F59PolicyNomination{n0,n1})
 if err!=nil||enrolled.SourceNominatedLanes!=2{return zero,ErrF63P}
 seen:=map[string]bool{}
 claims:=make([]ProspectiveSelection,0,2)
 for _,lane:=range lanes{
  t:=lane.Trial
  a:=t.Assignment
  if err:=ValidateF61Prepared(f,lane.Nomination,a);err!=nil{return zero,ErrF63P}
  if _,err:=PreviewF62PExactPolicyArms(f,lane.Nomination,[]F62PTrial{t});err!=nil{
   return zero,ErrF63P
  }
  if err:=f63PVerifyWitness(lane);err!=nil{return zero,ErrF63P}
  for _,v:=range []string{
   a.AssignmentSHA256,t.OriginalReceiptSHA256,
   lane.OwnerSelection.FirstUseReceiptSHA256,
   lane.ExternalPin.SignedRecordSHA256,
   lane.ExternalPin.WitnessPublicKeyHex,
   lane.ExternalPin.FirstUseLedgerHeadSHA256,
  }{
   if seen[v]{return zero,ErrF63P}
   seen[v]=true
  }
  claims=append(claims,lane.OwnerSelection)
 }
 existing,err:=AssessF58OwnerSelections(f,claims,trust)
 if err!=nil||existing.TrustVerifiedProspectiveLanes!=2||
  !existing.ExistingControllerPolicyGateEligible||
  existing.ScientificOriginalDispatchAuthorized||existing.AutomaticControllerCutoverAuthorized{
  return zero,ErrF63P
 }
 return F63PReadOnlyReview{
  Schema:"forge.optimizer.f63p.readonly-external-owner-source-binding.v1",
  Lanes:[]string{"Wingless","Yggdrasil"},
  ExternallyPinnedWitnessSignaturesVerified:true,
  ExistingOwnerTrustInterfaceAcceptedClaims:true,
  ExactPolicyArmPropensityNumerator:1,
  ExactPolicyArmPropensityDenominator:6,
  Status:"SIGNED_WITNESS_AND_TRUST_SOURCE_CHECKED_REAL_PREOUTCOME_FIRSTUSE_STILL_UNPROVEN",
 },nil
}
