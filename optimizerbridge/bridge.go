// Package optimizerbridge composes FORGE's existing five research-enhancement
// implementations using exact independently supplied source/trust pins.
// It is a READ-ONLY, NON-AUTHORIZING selector advisory; FSA/once-only science
// is never inferred from these historical results or synthetic qualification.
package optimizerbridge

import (
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/promptlineage"
 "github.com/spoonman136668-ai/forge/thetaadapt"
 "github.com/spoonman136668-ai/forge/genenv"
)

var ErrBlocked=errors.New("FORGE_OPTIMIZER_BRIDGE_UNQUALIFIED_SOURCE_OR_AUTHORITY")

// Evidence must be supplied by the existing research owner. Inputs and trust
// pins are separate. This package cannot create a trust root or accept one
// computed from untrusted evidence.
type LaneEvidence struct{
 Lane string `json:"lane"`
 Portfolio evoportfolio.Frozen `json:"portfolio"`
 ParetoFreeze evoportfolio.ParetoFreeze `json:"pareto_freeze"`
 ParetoLineage []evoportfolio.IslandLineage `json:"pareto_lineage"`
 DreamTrain dreamrsi.Envelope `json:"dream_train"`
 DreamValidation dreamrsi.Envelope `json:"dream_validation"`
 DreamSpec dreamrsi.FrozenSpec `json:"dream_spec"`
 PromptFreeze promptlineage.Frozen `json:"prompt_freeze"`
 ThetaFreeze thetaadapt.Frozen `json:"theta_freeze"`
 ThetaTraining thetaadapt.Training `json:"theta_training"`
 EnvironmentFreeze genenv.Frozen `json:"environment_freeze"`
 EnvironmentHistory genenv.History `json:"environment_history"`
}
type LanePins struct{
 Lane string `json:"lane"`
 PortfolioSHA256 string `json:"portfolio_sha256"`
 ParetoPolicySHA256 string `json:"pareto_policy_sha256"`
 IndependentEd25519PublicKeyHex string `json:"independent_ed25519_public_key_hex"`
 DreamTrainSHA256 string `json:"dream_train_sha256"`
 DreamValidationSHA256 string `json:"dream_validation_sha256"`
 DreamSpecSHA256 string `json:"dream_spec_sha256"`
 PromptSHA256 string `json:"prompt_sha256"`
 ThetaFreezeSHA256 string `json:"theta_freeze_sha256"`
 ThetaTrainingSHA256 string `json:"theta_training_sha256"`
 EnvironmentFreezeSHA256 string `json:"environment_freeze_sha256"`
 EnvironmentHistorySHA256 string `json:"environment_history_sha256"`
}
type LaneResult struct{
 Lane string `json:"lane"`
 PortfolioSHA256 string `json:"portfolio_sha256"`
 BaselineFinalists []string `json:"baseline_finalists"`
 ParetoFinalists []string `json:"pareto_finalists"`
 HistoricalArchiveCount int `json:"historical_archive_count"`
 NegativeCount int `json:"negative_count"`
 MixedCount int `json:"mixed_count"`
 InvalidCount int `json:"invalid_count"`
 IndeterminateCount int `json:"indeterminate_count"`
 ScreenComputeSpent int64 `json:"screen_compute_spent"`
 BaselineSealedComputeReserved int64 `json:"baseline_sealed_compute_reserved"`
 ParetoSealedComputeReserved int64 `json:"pareto_sealed_compute_reserved"`
 DreamPolicySHA256 string `json:"dream_policy_sha256"`
 DreamTrainingSHA256 string `json:"dream_training_sha256"`
 DreamValidationSHA256 string `json:"dream_validation_sha256"`
 DreamPoliciesEvaluated int `json:"dream_policies_evaluated"`
 DreamProspectiveComparisonEligible bool `json:"dream_prospective_comparison_eligible"`
 PromptCandidateCount int `json:"prompt_candidate_count"`
 ThetaTrainingRecordsPreserved int `json:"theta_training_records_preserved"`
 ThetaUpdates int `json:"theta_updates"`
 EnvironmentUntestedCount int `json:"environment_untested_count"`
 EnvironmentNoveltyIsOnlyHistoricalDistance bool `json:"environment_novelty_is_only_historical_distance"`
 CapabilityModes map[string]string `json:"capability_modes"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lanes []LaneResult `json:"lanes"`
 AuthenticRandomizationAuditRequired bool `json:"authentic_randomization_audit_required"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 ScienceOriginalsExecuted int `json:"science_originals_executed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

func checkLane(lane string)bool{return lane=="Wingless"||lane=="Yggdrasil"}

// EvaluateLane must successfully run ALL five existing packages; missing one
// input blocks the complete advisory rather than silently downgrading safety.
// "Dream" selection remains train/validation research, never improvement
// proof: true prospective sealed assessment lives with the independent FSA.
func EvaluateLane(e LaneEvidence,p LanePins)(LaneResult,error){
 var zero LaneResult
 if !checkLane(e.Lane)||p.Lane!=e.Lane{return zero,fmt.Errorf("%w:lane",ErrBlocked)}
 portfolio,err:=evoportfolio.Select(e.Portfolio,p.PortfolioSHA256)
 if err!=nil||portfolio.Lane!=e.Lane||len(portfolio.Finalists)==0||
   portfolio.ScientificAccepted||portfolio.DispatchAuthorized||
   portfolio.AcceptedRefMutation{return zero,fmt.Errorf("%w:portfolio",ErrBlocked)}
 pareto,err:=evoportfolio.ParetoAdvisory(
  e.Portfolio,p.PortfolioSHA256,e.ParetoFreeze,p.ParetoPolicySHA256,e.ParetoLineage)
 if err!=nil||pareto.Lane!=e.Lane||pareto.ImprovementScientificallyEstablished||
   pareto.MutationRuntimeActivated||pareto.DispatchAuthorized||
   pareto.AcceptedRefMutation||pareto.ScientificAccepted||
   pareto.ReservedSealedCompute>e.Portfolio.MaxSealedCompute||
   len(pareto.Archive)!=len(portfolio.Archive){return zero,fmt.Errorf("%w:pareto",ErrBlocked)}
 trust:=p.IndependentEd25519PublicKeyHex
 tr,err:=dreamrsi.VerifyEnvelope(e.DreamTrain,dreamrsi.TrustPin{
   ExpectedHistorySHA256:p.DreamTrainSHA256,IndependentEd25519PublicKeyHex:trust})
 if err!=nil||tr.Lane!=e.Lane{return zero,fmt.Errorf("%w:train_auth",ErrBlocked)}
 va,err:=dreamrsi.VerifyEnvelope(e.DreamValidation,dreamrsi.TrustPin{
   ExpectedHistorySHA256:p.DreamValidationSHA256,IndependentEd25519PublicKeyHex:trust})
 if err!=nil||va.Lane!=e.Lane||va.HistorySHA256==tr.HistorySHA256{return zero,fmt.Errorf("%w:validation_auth",ErrBlocked)}
 opt,err:=dreamrsi.Optimize(tr,va,e.DreamSpec,p.DreamSpecSHA256)
 if err!=nil||dreamrsi.ValidateOptimization(opt)!=nil||
   opt.Lane!=e.Lane||opt.ScientificAccepted||opt.DispatchAuthorized||
   opt.ImprovementEstablished||opt.EvaluationsUsed>e.DreamSpec.MaxEvaluations||
   opt.DecisionReplaysUsed>e.DreamSpec.MaxReplayDecisions{return zero,fmt.Errorf("%w:dream_optimization",ErrBlocked)}

 // Keep all proposal generators under exactly one already-frozen lane/source
 // identity. The source must already occur in the frozen portfolio; a newly
 // generated child cannot masquerade as a historical screened incumbent.
 source:=e.PromptFreeze.SourceSHA
 sourceKnown:=false
 for _,c:=range e.Portfolio.Candidates{if c.SourceSHA==source{sourceKnown=true}}
 if !sourceKnown||e.ThetaFreeze.SourceSHA!=source||
   e.EnvironmentFreeze.SourceSHA!=source{return zero,fmt.Errorf("%w:source_link",ErrBlocked)}
 prompts,err:=promptlineage.Generate(e.PromptFreeze,p.PromptSHA256)
 if err!=nil||prompts.DispatchAuthorized||prompts.ScientificAccepted||
   prompts.SealedEvaluationConsumed||len(prompts.Candidates)==0{return zero,fmt.Errorf("%w:prompt",ErrBlocked)}
 theta,err:=thetaadapt.Adapt(e.ThetaFreeze,p.ThetaFreezeSHA256,
   e.ThetaTraining,p.ThetaTrainingSHA256)
 if err!=nil||theta.DispatchAuthorized||theta.ScientificAccepted||
   theta.SealedHoldoutConsumed||theta.UpdatesApplied>e.ThetaFreeze.MaxUpdates||
   theta.ComputeSpent>e.ThetaFreeze.MaxTrainingCompute{return zero,fmt.Errorf("%w:theta",ErrBlocked)}
 env,err:=genenv.Generate(e.EnvironmentFreeze,p.EnvironmentFreezeSHA256,
   e.EnvironmentHistory,p.EnvironmentHistorySHA256)
 if err!=nil||env.DispatchAuthorized||env.ScientificAccepted||
   env.SealedHoldoutConsumed||len(env.Candidates)==0||
   env.OperationsUsed>e.EnvironmentFreeze.MaxOperations{return zero,fmt.Errorf("%w:genenv",ErrBlocked)}
 for _,child:=range prompts.Candidates{
   if child.Classification!="UNTESTED"{return zero,fmt.Errorf("%w:prompt_children",ErrBlocked)}
 }
 for _,child:=range env.Candidates{
   if child.Classification!="UNTESTED_PROPOSAL"{return zero,fmt.Errorf("%w:genenv_children",ErrBlocked)}
 }
 // Do not leak a successor candidate based on newly seen validation outcomes:
 // this is a shadow comparison only, not an authorizing experiment selection.
 out:=LaneResult{Lane:e.Lane,PortfolioSHA256:p.PortfolioSHA256,
   HistoricalArchiveCount:len(portfolio.Archive),
   NegativeCount:portfolio.NegativeCount,MixedCount:portfolio.MixedCount,
   ScreenComputeSpent:portfolio.ScreenComputeSpent,
   BaselineSealedComputeReserved:portfolio.SealedComputeReserved,
   ParetoSealedComputeReserved:pareto.ReservedSealedCompute,
   DreamPolicySHA256:opt.SelectedPolicySHA256,
   DreamTrainingSHA256:opt.TrainingSHA256,DreamValidationSHA256:opt.ValidationSHA256,
   DreamPoliciesEvaluated:len(opt.Records),
   DreamProspectiveComparisonEligible:opt.QualifiedForProspectiveTest,
   PromptCandidateCount:len(prompts.Candidates),
   ThetaTrainingRecordsPreserved:theta.RecordsPreserved,ThetaUpdates:theta.UpdatesApplied,
   EnvironmentUntestedCount:len(env.Candidates),
   EnvironmentNoveltyIsOnlyHistoricalDistance:true,
   CapabilityModes:map[string]string{
      "dream_rsi":"SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN",
      "shinka_pareto":"HISTORICAL_DIVERSITY_ADVISORY",
      "promptbreeder":"UNTESTED_LINEAGE_PROPOSALS",
      "theta_evolve":"TRAIN_ONLY_BOUNDED_PROPOSAL",
      "dgm_genenv":"UNTESTED_ENVIRONMENT_NOVELTY_PROPOSALS",
   }}
 for _,c:=range portfolio.Finalists{out.BaselineFinalists=append(out.BaselineFinalists,c.ID)}
 out.ParetoFinalists=append(out.ParetoFinalists,pareto.ParetoFinalists...)
 for _,c:=range portfolio.Archive{
   switch c.HistoricalClass{
    case "INVALID":out.InvalidCount++
    case "CONSUMED_INDETERMINATE":out.IndeterminateCount++
   }
 }
 if out.HistoricalArchiveCount!=out.NegativeCount+out.MixedCount+
    out.InvalidCount+out.IndeterminateCount+countSupported(portfolio.Archive){
    return zero,fmt.Errorf("%w:archive",ErrBlocked)
 }
 if theta.RecordsPreserved!=len(e.ThetaTraining.Records)||
    env.HistoricalCount!=len(e.EnvironmentHistory.Records){
    return zero,fmt.Errorf("%w:negative-preservation",ErrBlocked)
 }
 return out,nil
}
func countSupported(xs []evoportfolio.Candidate)int{
 n:=0;for _,c:=range xs{if c.HistoricalClass=="SUPPORTED"{n++}}
 return n
}
// EvaluatePair checks both lane identities and exactly-once historic source
// names before emitting a report. Failure is atomic (no partial plan output).
func EvaluatePair(inputs []LaneEvidence,pins []LanePins)(Report,error){
 var zero Report
 if len(inputs)!=2||len(pins)!=2||
  inputs[0].Lane!="Wingless"||inputs[1].Lane!="Yggdrasil"||
  pins[0].Lane!="Wingless"||pins[1].Lane!="Yggdrasil"{
  return zero,ErrBlocked
 }
 // Cross-lane content/address reuse is forbidden, even in advisory selection.
 sources:=map[string]bool{}
 receipts:=map[string]bool{}
 cohorts:=map[string]bool{}
 for _,lane:=range inputs{
  for _,c:=range lane.Portfolio.Candidates{
   if sources[c.SourceSHA]{return zero,ErrBlocked}
   sources[c.SourceSHA]=true
  }
  for _,env:=range []dreamrsi.Envelope{lane.DreamTrain,lane.DreamValidation}{
   for _,d:=range env.History.Decisions{
    if receipts[d.ReceiptSHA256]||cohorts[d.ChosenCohortSHA256]{
     return zero,ErrBlocked
    }
    receipts[d.ReceiptSHA256]=true
    cohorts[d.ChosenCohortSHA256]=true
   }
  }
 }
 a,err:=EvaluateLane(inputs[0],pins[0]);if err!=nil{return zero,err}
 b,err:=EvaluateLane(inputs[1],pins[1]);if err!=nil{return zero,err}
 if a.DreamTrainingSHA256==b.DreamTrainingSHA256||
    a.DreamValidationSHA256==b.DreamValidationSHA256||
    a.PortfolioSHA256==b.PortfolioSHA256{return zero,ErrBlocked}
 return Report{Schema:"forge.research-enhancements.dual-lane-shadow.v1",
  Mode:"AUTHENTICATED_HISTORICAL_COMPOSITION_ADVISORY_ONLY",
  Lanes:[]LaneResult{a,b},
  AuthenticRandomizationAuditRequired:true},nil
}
