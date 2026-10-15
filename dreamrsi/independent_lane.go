package dreamrsi

// R27 removes an accidental coupling between otherwise independent Wingless
// and Yggdrasil prospective SHADOW assessments. A negative or unavailable
// history in one lane never licenses or blocks the other's source-only review.
// Existing scientific owner/custody and full cross-lane admission remain
// external; per-lane reports cannot promote or dispatch originals.
import (
 "crypto/sha256"
 "encoding/hex"
)

const SingleLaneOwnerSchema = "forge.dreamrsi.r27-single-lane-owner-evidence.v1"
const SingleLanePinsSchema = "forge.dreamrsi.r27-single-lane-independent-pins.v1"
const SingleLaneReviewSchema = "forge.dreamrsi.r27-single-lane-shadow.v1"

type SingleLaneOwnerBundle struct {
 Schema string `json:"schema"`
 Lane OwnerLaneEvidence `json:"lane"`
}
type SingleLaneIndependentPins struct {
 Schema string `json:"schema"`
 OwnerBundleSHA256 string `json:"owner_bundle_sha256"`
 Lane IndependentLanePins `json:"lane"`
}
type SingleLaneReview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lane ProspectiveLaneReview `json:"lane"`
 IndependentRandomizationOperationallyProven bool `json:"independent_randomization_operationally_proven"`
 IndependentFirstUseAndSourceBirthProven bool `json:"independent_first_use_and_source_birth_proven"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OptimizerDispatchAuthorized bool `json:"optimizer_dispatch_authorized"`
 NewOriginalsExecuted int `json:"new_originals_executed"`
}

// AssessProspectiveLane is an isolated READ-ONLY evaluation: all three
// independently pinned periods and the predecision auditor must qualify.
// It cannot prove absence of cohort reuse in *other* external scientific
// lanes. Scientific authority must perform global exclusion before admission.
func AssessProspectiveLane(input ProspectiveLaneInput)(ProspectiveLaneReview,error){
 var zero ProspectiveLaneReview
 if !checkProspectiveLane(input.Lane)||
  input.Optimizer.Lane!=input.Lane||input.FrozenHoldout.Lane!=input.Lane||
  !input.Optimizer.QualifiedForProspectiveTest||
  input.Optimizer.ScientificAccepted||input.Optimizer.DispatchAuthorized||
  input.Optimizer.ImprovementEstablished{
  return zero,ErrProspective
 }
 train,err:=VerifyEnvelope(input.Train,input.TrainPin)
 if err!=nil||train.Lane!=input.Lane{return zero,ErrProspective}
 validation,err:=VerifyEnvelope(input.Validation,input.ValidationPin)
 if err!=nil||validation.Lane!=input.Lane{return zero,ErrProspective}
 held,err:=VerifyEnvelope(input.Heldout,input.HeldoutPin)
 if err!=nil||held.Lane!=input.Lane{return zero,ErrProspective}
 count,err:=verifyProspectiveAssignmentAudit(input,held)
 if err!=nil||count==0{return zero,ErrProspective}
 // The existing frozen four-baseline temporal holdout evaluator performs
 // split and cohort separation, preserving every negative and invalid row.
 report,err:=AssessHoldout(input.Optimizer,train,validation,held,
  input.FrozenHoldout,input.IndependentlyPinnedHoldoutSpecSHA256)
 if err!=nil||report.ScientificAccepted||report.DispatchAuthorized||
  report.ImprovementEstablished||len(report.Baselines)!=4{
  return zero,ErrProspective
 }
 return ProspectiveLaneReview{
  Lane:input.Lane,AuditedAssignments:count,
  FrozenOptimizerHeadSHA256:input.Optimizer.LineageHeadSHA256,
  SignedHoldoutHistorySHA256:held.HistorySHA256,
  Comparison:report,
 },nil
}
func checkProspectiveLane(lane string)bool{
 return lane=="Wingless"||lane=="Yggdrasil"
}

// ReviewOwnerSingleLaneEvidence reads an existing authorized owner's
// canonical byte output plus externally obtained, independently pinned
// identities; it does not create keys, claims, assignments or experiments.
func ReviewOwnerSingleLaneEvidence(ownerRaw,pinRaw []byte)(SingleLaneReview,error){
 var zero SingleLaneReview
 owner,err:=decodeIntake[SingleLaneOwnerBundle](ownerRaw,MaxOwnerEvidenceBytes)
 if err!=nil{return zero,ErrProspectiveIntake}
 pins,err:=decodeIntake[SingleLaneIndependentPins](pinRaw,MaxIndependentPinsBytes)
 if err!=nil{return zero,ErrProspectiveIntake}
 sum:=sha256.Sum256(ownerRaw)
 if owner.Schema!=SingleLaneOwnerSchema||pins.Schema!=SingleLanePinsSchema||
  !validHex(pins.OwnerBundleSHA256,64)||
  pins.OwnerBundleSHA256!=hex.EncodeToString(sum[:]){
  return zero,ErrProspectiveIntake
 }
 e,p:=owner.Lane,pins.Lane
 if !checkProspectiveLane(e.Lane)||e.Lane!=p.Lane||
  !validHex(p.FrozenOptimizerHeadSHA256,64)||
  e.Optimizer.LineageHeadSHA256!=p.FrozenOptimizerHeadSHA256||
  p.Train.ExpectedHistorySHA256==p.Validation.ExpectedHistorySHA256||
  p.Train.ExpectedHistorySHA256==p.Heldout.ExpectedHistorySHA256||
  p.Validation.ExpectedHistorySHA256==p.Heldout.ExpectedHistorySHA256{
  return zero,ErrProspectiveIntake
 }
 input:=ProspectiveLaneInput{
  Lane:e.Lane,Optimizer:e.Optimizer,Train:e.Train,
  Validation:e.Validation,Heldout:e.Heldout,
  TrainPin:p.Train,ValidationPin:p.Validation,HeldoutPin:p.Heldout,
  FrozenHoldout:e.FrozenHoldout,
  IndependentlyPinnedHoldoutSpecSHA256:p.HoldoutSpecSHA256,
  SignedAudit:e.SignedAudit,AuditPins:p.Audit,
 }
 review,err:=AssessProspectiveLane(input)
 if err!=nil||review.Lane!=e.Lane||review.FirstUseCustodyVerified||
  review.ActualRandomizationIndependentlyDemonstrated||
  review.Comparison.ScientificAccepted||review.Comparison.ImprovementEstablished||
  review.Comparison.DispatchAuthorized{
  return zero,ErrProspectiveIntake
 }
 return SingleLaneReview{
  Schema:SingleLaneReviewSchema,
  Mode:"INDEPENDENT_RESEARCH_LANE_SIGNED_SHADOW_ONLY_NO_DISPATCH",
  Lane:review,
 },nil
}
