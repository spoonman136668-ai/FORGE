package dreamrsi

// R24 is a source-only verifier for FUTURE, separately signed two-lane
// prospective policy comparisons. It neither chooses a real scientific
// original nor establishes randomization, custody, or causal improvement.
import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
)

const (
 ProspectiveAuditSchema = "forge.dreamrsi.prospective-assignment-audit.v1"
 ProspectiveAuditDomain = "FORGE-DREAMRSI-PROSPECTIVE-AUDIT-V1\x00"
 ProspectivePairSchema = "forge.dreamrsi.prospective-two-lane-shadow.v1"
)
var ErrProspective=errors.New("FORGE_PROSPECTIVE_POLICY_AUTHORITY_OR_EVIDENCE_UNQUALIFIED")

// This is a PREDECISION-only cross-check. Post-decision outcomes cannot
// appear here, and an independently signed claim still is not evidence
// that randomization actually occurred on a distinct protected host.
type ProspectiveAssignment struct {
 Tick uint64 `json:"tick"`
 ReceiptSHA256 string `json:"receipt_sha256"`
 ChosenID string `json:"chosen_id"`
 ChosenCohortSHA256 string `json:"chosen_cohort_sha256"`
 LoggedProbabilityBP int `json:"logged_probability_bp"`
 RandomizationProofSHA256 string `json:"randomization_proof_sha256"`
 AssignmentEventSHA256 string `json:"assignment_event_sha256"`
}
type ProspectiveAudit struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 HoldoutHistorySHA256 string `json:"holdout_history_sha256"`
 SelectedPolicySHA256 string `json:"selected_policy_sha256"`
 Entries []ProspectiveAssignment `json:"entries"`
}
type SignedProspectiveAudit struct {
 Audit ProspectiveAudit `json:"audit"`
 SignatureHex string `json:"signature_hex"`
}
type ProspectiveAuditPins struct {
 ExpectedAuditSHA256 string `json:"expected_audit_sha256"`
 IndependentAuditorKeyHex string `json:"independent_auditor_key_hex"`
}
type ProspectiveLaneInput struct {
 Lane string
 Optimizer Optimization
 Train Envelope
 Validation Envelope
 Heldout Envelope
 TrainPin TrustPin
 ValidationPin TrustPin
 HeldoutPin TrustPin
 FrozenHoldout HoldoutSpec
 IndependentlyPinnedHoldoutSpecSHA256 string
 SignedAudit SignedProspectiveAudit
 AuditPins ProspectiveAuditPins
}
type ProspectiveLaneReview struct {
 Lane string `json:"lane"`
 AuditedAssignments int `json:"audited_assignments"`
 FrozenOptimizerHeadSHA256 string `json:"frozen_optimizer_head_sha256"`
 SignedHoldoutHistorySHA256 string `json:"signed_holdout_history_sha256"`
 Comparison HoldoutReport `json:"comparison"`
 ActualRandomizationIndependentlyDemonstrated bool `json:"actual_randomization_independently_demonstrated"`
 FirstUseCustodyVerified bool `json:"first_use_custody_verified"`
}
type ProspectivePairReview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lanes []ProspectiveLaneReview `json:"lanes"`
 IndependentRandomizationOperationallyProven bool `json:"independent_randomization_operationally_proven"`
 IndependentFirstUseAndSourceBirthProven bool `json:"independent_first_use_and_source_birth_proven"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OptimizerDispatchAuthorized bool `json:"optimizer_dispatch_authorized"`
 NewOriginalsExecuted int `json:"new_originals_executed"`
}

func verifyProspectiveAssignmentAudit(input ProspectiveLaneInput,h Verified)(int,error){
 a:=input.SignedAudit.Audit
 p:=input.AuditPins
 if a.Schema!=ProspectiveAuditSchema||a.Lane!=h.Lane||
  a.Epoch==0||a.Epoch!=h.Epoch||
  a.HoldoutHistorySHA256!=h.HistorySHA256||
  a.SelectedPolicySHA256!=input.Optimizer.SelectedPolicySHA256||
  len(a.Entries)!=len(h.Decisions)||len(a.Entries)==0||
  !validHex(p.ExpectedAuditSHA256,64)||!validHex(p.IndependentAuditorKeyHex,64)||
  !validHex(input.SignedAudit.SignatureHex,128){
  return 0,ErrProspective
 }
 // The auditor must be independently pinned, not copied from a source-
 // history signer in the same lane.
 for _,source:=range []TrustPin{input.TrainPin,input.ValidationPin,input.HeldoutPin}{
  if source.IndependentEd25519PublicKeyHex==p.IndependentAuditorKeyHex{
   return 0,ErrProspective
  }
 }
 raw,err:=json.Marshal(a)
 if err!=nil||hash(raw)!=p.ExpectedAuditSHA256{return 0,ErrProspective}
 key,_:=hex.DecodeString(p.IndependentAuditorKeyHex)
 signature,_:=hex.DecodeString(input.SignedAudit.SignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(key),append([]byte(ProspectiveAuditDomain),raw...),signature){
  return 0,ErrProspective
 }
 seen:=map[string]bool{}
 var prev uint64
 for i,entry:=range a.Entries{
  d:=h.Decisions[i]
  if (i>0&&entry.Tick<=prev)||
   d.LoggingMode!=Randomized||
   entry.Tick!=d.Tick||
   entry.ReceiptSHA256!=d.ReceiptSHA256||
   entry.ChosenID!=d.ChosenID||
   entry.ChosenCohortSHA256!=d.ChosenCohortSHA256||
   entry.LoggedProbabilityBP!=d.LoggedActionProbabilityBP||
   entry.RandomizationProofSHA256!=d.RandomizationProofSHA256||
   !validHex(entry.AssignmentEventSHA256,64)||
   seen[entry.AssignmentEventSHA256] {
   return 0,ErrProspective
  }
  prev=entry.Tick
  seen[entry.AssignmentEventSHA256]=true
 }
 return len(a.Entries),nil
}

// AssessProspectivePair only assesses source-signed, independently pinned
// data from a separately authorized future owner. All-or-nothing failure:
// never emit even one lane if its counterpart lacks authenticated evidence.
// Holdout algorithms and four baselines are reused from the qualified
// dreamrsi.AssessHoldout routine, not reimplemented or retrospectively tuned.
func AssessProspectivePair(pair [2]ProspectiveLaneInput)(ProspectivePairReview,error){
 var zero ProspectivePairReview
 if pair[0].Lane!="Wingless"||pair[1].Lane!="Yggdrasil"||
  pair[0].Optimizer.Lane!="Wingless"||pair[1].Optimizer.Lane!="Yggdrasil"{
  return zero,ErrProspective
 }
 keys:=map[string]bool{}
 receipts:=map[string]bool{}
 cohorts:=map[string]bool{}
 events:=map[string]bool{}
 reviewed:=make([]ProspectiveLaneReview,0,2)
 for _,input:=range pair {
  if !input.Optimizer.QualifiedForProspectiveTest||
    input.Optimizer.ScientificAccepted||input.Optimizer.DispatchAuthorized||
    input.Optimizer.ImprovementEstablished ||
    input.Lane!=input.FrozenHoldout.Lane||
    input.Optimizer.Lane!=input.Lane {
    return zero,ErrProspective
  }
  for _,key:=range []string{
   input.TrainPin.IndependentEd25519PublicKeyHex,
   input.ValidationPin.IndependentEd25519PublicKeyHex,
   input.HeldoutPin.IndependentEd25519PublicKeyHex,
   input.AuditPins.IndependentAuditorKeyHex,
  } {
   if !validHex(key,64){return zero,ErrProspective}
  }
  // A lane may sign its train/validation/holdout histories with one
  // protected key; all roles in the OTHER lane must be disjoint.
  for _,other:=range []ProspectiveLaneInput{pair[0],pair[1]}{
   if other.Lane==input.Lane{continue}
   for _,key:=range []string{
    other.TrainPin.IndependentEd25519PublicKeyHex,
    other.ValidationPin.IndependentEd25519PublicKeyHex,
    other.HeldoutPin.IndependentEd25519PublicKeyHex,
    other.AuditPins.IndependentAuditorKeyHex,
   }{
    for _,mine:=range []string{
     input.TrainPin.IndependentEd25519PublicKeyHex,
     input.ValidationPin.IndependentEd25519PublicKeyHex,
     input.HeldoutPin.IndependentEd25519PublicKeyHex,
     input.AuditPins.IndependentAuditorKeyHex,
    }{if key==mine{return zero,ErrProspective}}
   }
  }
  tr,err:=VerifyEnvelope(input.Train,input.TrainPin)
  if err!=nil{return zero,ErrProspective}
  va,err:=VerifyEnvelope(input.Validation,input.ValidationPin)
  if err!=nil{return zero,ErrProspective}
  ho,err:=VerifyEnvelope(input.Heldout,input.HeldoutPin)
  if err!=nil{return zero,ErrProspective}
  if tr.Lane!=input.Lane||va.Lane!=input.Lane||ho.Lane!=input.Lane{
   return zero,ErrProspective
  }
  for _,history:=range []Verified{tr,va,ho}{
   for _,d:=range history.Decisions{
    if receipts[d.ReceiptSHA256]||cohorts[d.ChosenCohortSHA256]{
     return zero,ErrProspective
    }
    receipts[d.ReceiptSHA256]=true
    cohorts[d.ChosenCohortSHA256]=true
   }
  }
  count,err:=verifyProspectiveAssignmentAudit(input,ho)
  if err!=nil{return zero,ErrProspective}
  for _,event:=range input.SignedAudit.Audit.Entries {
   if events[event.AssignmentEventSHA256]{return zero,ErrProspective}
   events[event.AssignmentEventSHA256]=true
  }
  report,err:=AssessHoldout(input.Optimizer,tr,va,ho,
    input.FrozenHoldout,input.IndependentlyPinnedHoldoutSpecSHA256)
  if err!=nil||report.ScientificAccepted||report.DispatchAuthorized||
   report.ImprovementEstablished {
   return zero,ErrProspective
  }
  reviewed=append(reviewed,ProspectiveLaneReview{
   Lane:input.Lane, AuditedAssignments:count,
   FrozenOptimizerHeadSHA256:input.Optimizer.LineageHeadSHA256,
   SignedHoldoutHistorySHA256:ho.HistorySHA256,
   Comparison:report,
  })
 }
 // "Signed assignment claims match" != independent randomization/first-use.
 // Even statistically interesting heldout results cannot become authority.
 return ProspectivePairReview{
  Schema:ProspectivePairSchema,
  Mode:"SIGNED_PROSPECTIVE_SHADOW_REVIEW_NO_DISPATCH_OR_CAUSAL_AUTHORITY",
  Lanes:reviewed,
 },nil
}
