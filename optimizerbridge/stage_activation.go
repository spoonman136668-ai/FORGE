package optimizerbridge

// StageActivation is an evidence-gated handoff to the EXISTING FORGE
// controller. This package has no execution, credential, signing, broker,
// Cloudflare, or accepted-reference mutation capability. Historical/FIT
// diagnostics cannot authorize a prospective selection policy.
import (
 "errors"
 "fmt"
)

var ErrStageEvidence=errors.New("FORGE_ENHANCEMENT_ACTIVATION_PROSPECTIVE_EVIDENCE_REQUIRED")

// Trust is implemented by an already authorized independent acceptance
// provider. Callers cannot replace authentic verification with a boolean
// stored in experiment JSON. No new credential or signing authority is made.
type Trust interface {
 VerifyProspectiveResearchSelection(ProspectiveSelection) error
 VerifyAcceptedScientificOutcome(IndependentlyAcceptedOutcome) error
}
type ProspectiveSelection struct {
 Lane string `json:"lane"`
 FrozenBaselinePolicySHA256 []string `json:"frozen_baseline_policy_sha256"`
 FrozenDreamPolicySHA256 string `json:"frozen_dream_policy_sha256"`
 FrozenParetoPolicySHA256 string `json:"frozen_pareto_policy_sha256"`
 PreregistrationSHA256 string `json:"preregistration_sha256"`
 ProspectiveSourceSHA string `json:"prospective_source_sha"`
 FirstUseReceiptSHA256 string `json:"first_use_receipt_sha256"`
 RandomizationAuditSHA256 string `json:"randomization_audit_sha256"`
 IndependentCausalReviewSHA256 string `json:"independent_causal_review_sha256"`
}
type IndependentlyAcceptedOutcome struct {
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 AcceptedEvidenceSHA256 string `json:"accepted_evidence_sha256"`
 IndependentAdmissionSHA256 string `json:"independent_admission_sha256"`
 FreshSinceFrozenPolicy bool `json:"fresh_since_frozen_policy"`
}
type StructuralMechanismProposal struct {
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 CandidateSHA256 string `json:"candidate_sha256"`
 Generator string `json:"generator"` // Promptbreeder or DGM/GenEnv
 ParentRepresentation string `json:"parent_representation"`
 NewRepresentation string `json:"new_representation"`
 ParentConsumer string `json:"parent_consumer"`
 NewConsumer string `json:"new_consumer"`
 ParentTestEnvironment string `json:"parent_test_environment"`
 NewTestEnvironment string `json:"new_test_environment"`
 FrozenControlSHA256 []string `json:"frozen_control_sha256"`
 Status string `json:"status"`
}
type StageActivation struct {
 Schema string `json:"schema"`
 DreamPareto string `json:"dream_pareto"`
 ThetaEvolve string `json:"theta_evolve"`
 PromptbreederAndGenEnv string `json:"promptbreeder_and_genenv"`
 FrozenSelectionPoliciesPreserved bool `json:"frozen_selection_policies_preserved"`
 AuthenticatedProspectiveResearchSelection bool `json:"authenticated_prospective_research_selection"`
 IndependentOutcomesRequiredForTheta bool `json:"independent_outcomes_required_for_theta"`
 ProposalsOnlyUntested bool `json:"proposals_only_untested"`
 ControllerCutoverAuthorized bool `json:"controller_cutover_authorized"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func exactHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func differentFrozenControls(c []string,dream,pareto string)bool{
 if len(c)<2||len(c)>8||dream==pareto{return false}
 seen:=map[string]bool{dream:true,pareto:true}
 for _,s:=range c{
  if !exactHex(s,64)||seen[s]{return false}
  seen[s]=true
 }
 return true
}
func validTrial(s ProspectiveSelection)bool{
 return checkLane(s.Lane)&&differentFrozenControls(s.FrozenBaselinePolicySHA256,s.FrozenDreamPolicySHA256,s.FrozenParetoPolicySHA256)&&
 exactHex(s.FrozenDreamPolicySHA256,64)&&exactHex(s.FrozenParetoPolicySHA256,64)&&
 exactHex(s.PreregistrationSHA256,64)&&exactHex(s.ProspectiveSourceSHA,40)&&
 exactHex(s.FirstUseReceiptSHA256,64)&&exactHex(s.RandomizationAuditSHA256,64)&&
 exactHex(s.IndependentCausalReviewSHA256,64)
}
func validOutcome(o IndependentlyAcceptedOutcome)bool{
 return checkLane(o.Lane)&&exactHex(o.SourceSHA,40)&&
 exactHex(o.AcceptedEvidenceSHA256,64)&&exactHex(o.IndependentAdmissionSHA256,64)&&
 o.AcceptedEvidenceSHA256!=o.IndependentAdmissionSHA256&&o.FreshSinceFrozenPolicy
}
func validMechanism(m StructuralMechanismProposal)bool{
 if !checkLane(m.Lane)||!exactHex(m.SourceSHA,40)||!exactHex(m.CandidateSHA256,64)||
  (m.Generator!="Promptbreeder"&&m.Generator!="DGM/GenEnv")||
  m.Status!="UNTESTED"||len(m.FrozenControlSHA256)<2||len(m.FrozenControlSHA256)>8{return false}
 distinct:=0
 for _,pair:=range [][2]string{{m.ParentRepresentation,m.NewRepresentation},
  {m.ParentConsumer,m.NewConsumer},{m.ParentTestEnvironment,m.NewTestEnvironment}}{
  if pair[0]==""||pair[1]==""||len(pair[0])>80||len(pair[1])>80{return false}
  if pair[0]!=pair[1]{distinct++}
 }
 if distinct<2{return false} // No hyperparameter-only or trivial prompt mutation.
 seen:=map[string]bool{m.CandidateSHA256:true}
 for _,s:=range m.FrozenControlSHA256{
  if !exactHex(s,64)||seen[s]{return false}
  seen[s]=true
 }
 return true
}
// AssessActivation is deliberately non-executing. Its eligibility result
// requires the existing authority to verify real prospective randomized
// research-SELECTION outcomes, rather than model-training task scores.
// Theta receives ONLY newly independently accepted scientific results; both
// prerequisites must be met before the existing controlled worker may train.
func AssessActivation(trials []ProspectiveSelection,outcomes []IndependentlyAcceptedOutcome,
 proposals []StructuralMechanismProposal,trust Trust)(StageActivation,error){
 out:=StageActivation{Schema:"forge.optimizer.ordered-activation.v1",
  DreamPareto:"WAITING_AUTHENTIC_PROSPECTIVE_COMPARISON",
  ThetaEvolve:"WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS",
  PromptbreederAndGenEnv:"WAITING_NOVEL_SOURCE_PROPOSALS",
  FrozenSelectionPoliciesPreserved:true,
  IndependentOutcomesRequiredForTheta:true,ProposalsOnlyUntested:true}
 if len(trials)!=0&&len(trials)!=2{return out,fmt.Errorf("%w:two_lanes",ErrStageEvidence)}
 seen:=map[string]bool{}
 frozen:=map[string]string{}
 usedReceipt:=map[string]bool{}
 for _,t:=range trials{
  if !validTrial(t)||seen[t.Lane]||usedReceipt[t.FirstUseReceiptSHA256]{
   return out,fmt.Errorf("%w:trial_identity",ErrStageEvidence)
  }
  seen[t.Lane]=true;frozen[t.Lane]=t.ProspectiveSourceSHA
  usedReceipt[t.FirstUseReceiptSHA256]=true
 }
 if len(trials)==2&&trust!=nil{
  for _,t:=range trials{
   if err:=trust.VerifyProspectiveResearchSelection(t);err!=nil{
    return out,fmt.Errorf("%w:prospective_selection:%v",ErrStageEvidence,err)
   }
  }
  out.DreamPareto="ELIGIBLE_FOR_EXISTING_CONTROLLER_POLICY_GATE"
  out.AuthenticatedProspectiveResearchSelection=true
 }
 usedEvidence:=map[string]bool{}
 acceptedLanes:=map[string]bool{}
 if len(outcomes)>0&&len(trials)!=2{
  return out,fmt.Errorf("%w:no_selection_trial",ErrStageEvidence)
 }
 for _,o:=range outcomes{
  if !validOutcome(o)||!seen[o.Lane]||acceptedLanes[o.Lane]||
   usedEvidence[o.AcceptedEvidenceSHA256]||o.SourceSHA==frozen[o.Lane]{
   return out,fmt.Errorf("%w:accepted_outcome_identity",ErrStageEvidence)
  }
  acceptedLanes[o.Lane]=true;usedEvidence[o.AcceptedEvidenceSHA256]=true
  if trust==nil||!out.AuthenticatedProspectiveResearchSelection{
   return out,fmt.Errorf("%w:missing_trust",ErrStageEvidence)
  }
  if err:=trust.VerifyAcceptedScientificOutcome(o);err!=nil{
   return out,fmt.Errorf("%w:independent_outcome:%v",ErrStageEvidence,err)
  }
 }
 if len(acceptedLanes)==2&&out.AuthenticatedProspectiveResearchSelection{
  out.ThetaEvolve="ELIGIBLE_FOR_EXISTING_FROZEN_TRAINING_GATE"
 }
 seenNovelty:=map[string]bool{}
 for _,p:=range proposals{
  if !validMechanism(p)||seenNovelty[p.CandidateSHA256]{
   return out,fmt.Errorf("%w:novelty_not_structurally_distinct",ErrStageEvidence)
  }
  seenNovelty[p.CandidateSHA256]=true
 }
 if len(proposals)>0 {
  out.PromptbreederAndGenEnv="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"
 }
 return out,nil
}
