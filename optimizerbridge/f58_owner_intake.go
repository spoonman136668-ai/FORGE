package optimizerbridge

// Read-only F58 input boundary for actual two-lane prospective research-
// SELECTION records. It cannot create owner assignments or scientific results.
// Only the existing externally authorized Trust verifier can authenticate
// randomization, first-use custody and independent causal outcome review.
import "fmt"

type F58SelectionIntake struct {
 Schema string `json:"schema"`
 FrozenControlRegistrySHA256 string `json:"frozen_control_registry_sha256"`
 StructurallyRegisteredLanes int `json:"structurally_registered_lanes"`
 TrustVerifiedProspectiveLanes int `json:"trust_verified_prospective_lanes"`
 ExistingControllerPolicyGateEligible bool `json:"existing_controller_policy_gate_eligible"`
 AutomaticControllerCutoverAuthorized bool `json:"automatic_controller_cutover_authorized"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 ThetaWeightUpdatesAuthorized bool `json:"theta_weight_updates_authorized"`
 Mode string `json:"mode"`
}

func AssessF58OwnerSelections(f F58Freeze,trial []ProspectiveSelection,trust Trust)(F58SelectionIntake,error){
 freeze,err:=ReadinessF58(f)
 if err!=nil{return F58SelectionIntake{},err}
 out:=F58SelectionIntake{
  Schema:"forge.optimizer.f58.actual-owner-selection-intake.v1",
  FrozenControlRegistrySHA256:freeze.FrozenControlRegistrySHA256,
  Mode:"BLOCKED_NO_AUTHENTIC_PROSPECTIVE_OWNER_SELECTION",
 }
 if len(trial)>2{return F58SelectionIntake{},ErrF58}
 seenLane:=map[string]bool{}
 unique:=map[string]bool{}
 for _,entry:=range trial{
  laneIdx:= -1
  for i,l:=range f.Lanes {if l.Lane==entry.Lane{laneIdx=i;break}}
  if laneIdx<0||seenLane[entry.Lane]||
   len(entry.FrozenBaselinePolicySHA256)!=4||
   !validTrial(entry)||entry.ProspectiveSourceSHA==F58ParentSource{
   return F58SelectionIntake{},ErrF58
  }
  seenLane[entry.Lane]=true
  refs:=f.Lanes[laneIdx].Controls
  for i,sha:=range entry.FrozenBaselinePolicySHA256{
   if sha!=refs[i].SHA256{return F58SelectionIntake{},fmt.Errorf("%w:baseline_head_drift",ErrF58)}
  }
  for _,digest:=range []string{
   entry.FrozenDreamPolicySHA256,
   entry.FrozenParetoPolicySHA256,
   entry.FirstUseReceiptSHA256,
   entry.RandomizationAuditSHA256,
   entry.IndependentCausalReviewSHA256,
   entry.PreregistrationSHA256,
  }{
   // A trial cannot recycle a control ID or a cross-lane receipt.
   if unique[digest]{return F58SelectionIntake{},fmt.Errorf("%w:duplicate_assessment_receipt",ErrF58)}
   unique[digest]=true
   for _,lane:=range f.Lanes{
    for _,baseline:=range lane.Controls{
     if baseline.SHA256==digest{return F58SelectionIntake{},fmt.Errorf("%w:challenger_equals_control",ErrF58)}
    }
   }
  }
 }
 out.StructurallyRegisteredLanes=len(trial)
 if len(trial)==1{
  out.Mode="PARTIAL_ONE_LANE_REGISTERED_NOT_PROMOTED_OTHER_LANE_INDEPENDENT"
  return out,nil
 }
 if len(trial)!=2{return out,nil}
 if trust==nil{
  out.Mode="TWO_SOURCE_CLAIMS_PRESENT_BUT_INDEPENDENT_TRUST_MISSING"
  return out,nil
 }
 gate,err:=AssessActivation(trial,nil,nil,trust)
 if err!=nil{return F58SelectionIntake{},err}
 if !gate.AuthenticatedProspectiveResearchSelection||
  gate.DreamPareto!="ELIGIBLE_FOR_EXISTING_CONTROLLER_POLICY_GATE"||
  gate.ControllerCutoverAuthorized||gate.ScientificOriginalDispatchAuthorized||
  gate.AcceptedRefMutation||gate.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"{
  return F58SelectionIntake{},ErrF58
 }
 out.TrustVerifiedProspectiveLanes=2
 out.ExistingControllerPolicyGateEligible=true
 out.Mode="ELIGIBLE_FOR_SEPARATE_EXISTING_CONTROLLER_POLICY_GATE_NOT_ACTIVATED"
 return out,nil
}
