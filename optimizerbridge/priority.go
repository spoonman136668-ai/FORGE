package optimizerbridge

// PriorityPlan is the safe, fixed research progression. It is advisory;
// a green historical test cannot unlock prospective science automatically.
type PriorityPlan struct {
 Schema string `json:"schema"`
 Phase string `json:"phase"`
 Lane string `json:"lane"`
 DreamPolicySHA256 string `json:"dream_policy_sha256"`
 BaselineFinalists []string `json:"baseline_finalists"`
 ParetoFinalists []string `json:"pareto_finalists"`
 FrozenControlsRequired bool `json:"frozen_controls_required"`
 ProspectiveRandomizationRequired bool `json:"prospective_randomization_required"`
 IndependentOutcomeReviewRequired bool `json:"independent_outcome_review_required"`
 ThetaCanLearnFromAcceptedOutcomes bool `json:"theta_can_learn_from_accepted_outcomes"`
 PromptAndGenenvCanProposeNovelty bool `json:"prompt_and_genenv_can_propose_novelty"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 ExperimentDispatchAuthorized bool `json:"experiment_dispatch_authorized"`
}
// PlanFirstPhase keeps research candidate identities lane-specific and retains
// frozen baseline candidates alongside Pareto diversity and the Dream choice.
// The subsequent phases require real independently accepted prospective data.
func PlanFirstPhase(r LaneResult)(PriorityPlan,error){
 if !checkLane(r.Lane)||!digestOK(r.DreamPolicySHA256,64)||
  len(r.BaselineFinalists)==0||len(r.ParetoFinalists)==0||
  r.DreamPoliciesEvaluated==0||r.CapabilityModes["dream_rsi"]!="SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN"||
  r.CapabilityModes["shinka_pareto"]!="HISTORICAL_DIVERSITY_ADVISORY"{
  return PriorityPlan{},ErrBlocked
 }
 uniq:=func(ids []string)bool{
  used:=map[string]bool{}
  for _,id:=range ids{if id==""||used[id]{return false};used[id]=true}
  return true
 }
 if !uniq(r.BaselineFinalists)||!uniq(r.ParetoFinalists){return PriorityPlan{},ErrBlocked}
 return PriorityPlan{Schema:"forge.optimizer.priority-plan.v1",Phase:"DREAM_PARETO_FROZEN_CONTROL_PROSPECTIVE_PREREGISTRATION",
  Lane:r.Lane,DreamPolicySHA256:r.DreamPolicySHA256,
  BaselineFinalists:append([]string(nil),r.BaselineFinalists...),
  ParetoFinalists:append([]string(nil),r.ParetoFinalists...),
  FrozenControlsRequired:true,ProspectiveRandomizationRequired:true,IndependentOutcomeReviewRequired:true},nil
}
