package optimizerbridge

// F59 is a read-only enrollment boundary for future *owner-produced* Dream-RSI
// and Pareto challenger policies. It never invents a policy identity, uses
// task-level FIT scores as research-selection outcomes, verifies its own
// independence, or initiates first-use.
import "errors"

const F59EnrollmentSchema = "forge.optimizer.f59.owner-policy-enrollment.v1"
var ErrF59Enrollment = errors.New("FORGE_F59_AUTHENTIC_OWNER_CHALLENGERS_NOT_ENROLLED")

type F59PolicyNomination struct {
 Lane string `json:"lane"`
 FrozenControlRegistrySHA256 string `json:"frozen_control_registry_sha256"`
 DreamPolicySHA256 string `json:"dream_policy_sha256"`
 DreamOptimizerLineageSHA256 string `json:"dream_optimizer_lineage_sha256"`
 DreamTrainingHistorySHA256 string `json:"dream_training_history_sha256"`
 DreamValidationHistorySHA256 string `json:"dream_validation_history_sha256"`
 ParetoPolicySHA256 string `json:"pareto_policy_sha256"`
 ParetoFrozenPortfolioSHA256 string `json:"pareto_frozen_portfolio_sha256"`
 ParetoLineageSHA256 string `json:"pareto_lineage_sha256"`
 OwnerPreregistrationSHA256 string `json:"owner_preregistration_sha256"`
 PredecisionOwnerSourceSHA string `json:"predecision_owner_source_sha"`
 IndependentExternalTrustReceiptSHA256 string `json:"independent_external_trust_receipt_sha256"`
}
type F59EnrollmentReadiness struct {
 Schema string `json:"schema"`
 CurrentRegistrationSHA256 string `json:"current_registration_sha256"`
 FrozenControlPolicies int `json:"frozen_control_policies"`
 SourceNominatedLanes int `json:"source_nominated_lanes"`
 OwnerAuthenticatedLanes int `json:"owner_authenticated_lanes"`
 DistinctNewScientificFirstUseAssignments int `json:"distinct_new_scientific_firstuse_assignments"`
 FirstProspectiveSelectionExecuted bool `json:"first_prospective_selection_executed"`
 DreamParetoPolicySelectionActivated bool `json:"dream_pareto_policy_selection_activated"`
 ThetaEvolvePromotionAuthorized bool `json:"theta_evolve_promotion_authorized"`
 TrialDispatchAuthorized bool `json:"trial_dispatch_authorized"`
 Status string `json:"status"`
}

// PreviewEnrollment binds untrusted nominations to the *existing* F58 freeze,
// but DOES NOT authenticate them. Only the existing separately authorized
// owner/Trust may subsequently advance through AssessF58OwnerSelections.
func PreviewEnrollment(f F58Freeze, nominations []F59PolicyNomination)(F59EnrollmentReadiness,error){
 frozen,err:=ReadinessF58(f)
 if err!=nil{return F59EnrollmentReadiness{},err}
 out:=F59EnrollmentReadiness{
  Schema:F59EnrollmentSchema,
  CurrentRegistrationSHA256:frozen.FrozenControlRegistrySHA256,
  FrozenControlPolicies:frozen.FrozenControlPolicies,
  Status:"FROZEN_CONTROLS_READY_OWNER_CUSTODY_AND_FIRST_USE_NOT_RECEIVED",
 }
 if len(nominations)>len(f.Lanes){return F59EnrollmentReadiness{},ErrF59Enrollment}
 usedLane:=map[string]bool{}
 seen:=map[string]bool{}
 for _,n:=range nominations {
  if usedLane[n.Lane]||n.FrozenControlRegistrySHA256!=frozen.FrozenControlRegistrySHA256{
   return F59EnrollmentReadiness{},ErrF59Enrollment
  }
  var controls []F58Baseline
  for _,lane:=range f.Lanes{
   if lane.Lane==n.Lane{controls=lane.Controls;break}
  }
  if len(controls)!=4||!f59Hex(n.DreamPolicySHA256,64)||
   !f59Hex(n.DreamOptimizerLineageSHA256,64)||
   !f59Hex(n.DreamTrainingHistorySHA256,64)||
   !f59Hex(n.DreamValidationHistorySHA256,64)||
   !f59Hex(n.ParetoPolicySHA256,64)||
   !f59Hex(n.ParetoFrozenPortfolioSHA256,64)||
   !f59Hex(n.ParetoLineageSHA256,64)||
   !f59Hex(n.OwnerPreregistrationSHA256,64)||
   !f59Hex(n.PredecisionOwnerSourceSHA,40)||
   !f59Hex(n.IndependentExternalTrustReceiptSHA256,64)||
   n.PredecisionOwnerSourceSHA==F58ParentSource||
   n.DreamPolicySHA256==n.ParetoPolicySHA256||
   n.DreamTrainingHistorySHA256==n.DreamValidationHistorySHA256{
   return F59EnrollmentReadiness{},ErrF59Enrollment
  }
  // The independent custodian, training, registration and cohort identities
  // must be separate and not reused across the two experiment owners.
  for _,sha:=range []string{
   n.DreamPolicySHA256,n.DreamOptimizerLineageSHA256,
   n.DreamTrainingHistorySHA256,n.DreamValidationHistorySHA256,
   n.ParetoPolicySHA256,n.ParetoFrozenPortfolioSHA256,
   n.ParetoLineageSHA256,n.OwnerPreregistrationSHA256,
   n.IndependentExternalTrustReceiptSHA256,
   n.PredecisionOwnerSourceSHA,
  }{
   if seen[sha]{return F59EnrollmentReadiness{},ErrF59Enrollment}
   seen[sha]=true
   for _,lane:=range f.Lanes{
    for _,base:=range lane.Controls{
     if sha==base.SHA256{return F59EnrollmentReadiness{},ErrF59Enrollment}
    }
   }
  }
  usedLane[n.Lane]=true
 }
 out.SourceNominatedLanes=len(nominations)
 if len(nominations)>0{
  out.Status="NOMINATIONS_SOURCE_STRUCTURALLY_VALID_NOT_EXTERNALLY_AUTHENTICATED"
 }
 return out,nil
}
func f59Hex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
