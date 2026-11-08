// Eureka F11: uncertainty-directed causal intervention DEV comparison.
// A single frozen 32-explanation posterior, three matched planners, existing
// F2/F3 models and F10 NO_GO controls. No owner, first use, code promotion.
package nativediscovery

import (
 "errors"
 "reflect"
)

const (
 F11Schema = "forge.native-discovery.causal-uncertainty-interventions.dev.v1"
 F11Hypotheses = 32
 F11PriorOdds = 3
 F11MinimumAdditionalCorrect = 4
 F11ReviewNO_GO = "F11_DEV_NO_GO"
 F11ReviewSignal = "F11_DEV_SIGNAL_UNVERIFIED"
)
var errF11 = errors.New("FORGE_EUREKA_F11_CAUSAL_INTERVENTION_INVALID")

func f11Policies()[3]string{return [3]string{"uncertainty","fixed","random"}}

type f11Posterior struct{f3Core}

func f11Sign(h,cue,mode int)int{
 if ((h>>cue)&1)^(((h>>4)&1)*mode)==1{return -1}
 return 1
}
func f11Weights(counts f2Counts)([F11Hypotheses]int,error){
 var weights [F11Hypotheses]int
 n:=0
 for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
  for _,count:=range counts[1][cue][mode]{
   if count<0||count>F5ProbeBudget{return weights,errF11}
   n+=count
  }
 }}
 if n>F5ProbeBudget{return weights,errF11}
 for h:=0;h<F11Hypotheses;h++{
  weight:=1
  for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
   matched:=counts[1][cue][mode][1]
   if f11Sign(h,cue,mode)<0{matched=counts[1][cue][mode][0]}
   for k:=0;k<matched;k++{weight*=F11PriorOdds}
  }}
  weights[h]=weight
 }
 return weights,nil
}
func f11Vote(weights [F11Hypotheses]int,cue,mode int)(positive,negative int){
 for h,w:=range weights{
  if f11Sign(h,cue,mode)==1{positive+=w}else{negative+=w}
 }
 return
}
func(m *f11Posterior)Predict(ctx f2Context)int{
 if ctx.Regime<0||ctx.Regime>1||ctx.Cue<0||ctx.Cue>=4||ctx.Mode<0||ctx.Mode>=2{return 1}
 if ctx.Regime==0{return f2prior(m.Counts,ctx.Regime,ctx.Cue,ctx.Mode)}
 w,err:=f11Weights(m.Counts)
 if err!=nil{return 1}
 positive,negative:=f11Vote(w,ctx.Cue,ctx.Mode)
 if positive>negative{return 1}
 if negative>positive{return -1}
 direct,seen:=f2major(m.Counts[1][ctx.Cue][ctx.Mode])
 if seen{return direct}
 return 1
}

// Selects the least identified causal context by maximal uncertainty in the
// fixed posterior BEFORE receiving the consequence of the chosen action.
// Model/data generation are distinct; no seed or oracle effects are read.
func f11Choose(seed uint32,policy string,step int,used [8]bool,
 candidate *f11Posterior,f3 [3]f3Executable)(f2Context,[3]int,int,error){
 if !f5ValidSeed(seed)||step<0||step>=F5ProbeBudget{return f2Context{},[3]int{},0,errF11}
 if policy=="fixed"||policy=="random"{
  ctx,pred,_,calls,err:=f5Select(policy,seed,step,used,f3)
  if err!=nil{return f2Context{},[3]int{},0,errF11}
  return ctx,pred,calls,nil
 }
 if policy!="uncertainty"{return f2Context{},[3]int{},0,errF11}
 weights,err:=f11Weights(candidate.Counts)
 if err!=nil{return f2Context{},[3]int{},0,errF11}
 chosen,best,searches:=-1,-1,0
 for coordinate:=0;coordinate<8;coordinate++{
  if used[coordinate]{continue}
  cue,mode:=coordinate/2,coordinate%2
  positive,negative:=f11Vote(weights,cue,mode)
  searches+=F11Hypotheses
  uncertainty:=positive
  if negative<uncertainty{uncertainty=negative}
  if uncertainty>best{chosen,best=coordinate,uncertainty}
 }
 if chosen<0||searches<1{return f2Context{},[3]int{},0,errF11}
 predicted,err:=f5Read(f3,chosen/2,chosen%2)
 if err!=nil{return f2Context{},[3]int{},0,errF11}
 return f2Context{Regime:1,Cue:chosen/2,Mode:chosen%2},
  predicted,searches+len(f3),nil
}

type F11Round struct{
 Generation int `json:"generation"`
 ObservedProbes int `json:"observed_probes"`
 SelectedF3ID string `json:"selected_f3_id"`
 PosteriorCorrect int `json:"posterior_correct_of_64"`
 F3Correct int `json:"f3_correct_of_64"`
 TabularCorrect int `json:"tabular_correct_of_64"`
 FactorizedCorrect int `json:"factorized_correct_of_64"`
 NativeCorrect int `json:"native_correct_of_64"`
 StrongestMatchedCorrect int `json:"strongest_matched_correct_of_64"`
 StrongestMatchedName string `json:"strongest_matched_name"`
 AdvantageOverStrongest int `json:"advantage_over_strongest"`
 OriginalWorldBefore int `json:"original_world_before_of_64"`
 OriginalWorldAfter int `json:"original_world_after_of_64"`
 OriginalWorldRetained bool `json:"original_world_retained"`
 ColdPredictionMatches bool `json:"cold_prediction_matches"`
 SnapshotSHA256 string `json:"snapshot_sha256"`
 SnapshotBytes int `json:"snapshot_bytes"`
}

type F11Arm struct{
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 TrainObservations int `json:"train_observations"`
 ProbeObservations int `json:"probe_observations"`
 PlannerPredictionCalls int `json:"planner_prediction_calls"`
 Probes []F5Probe `json:"probes"`
 Rounds [2]F11Round `json:"rounds"`
 FeedbackSHA256 string `json:"feedback_sha256"`
}

type F11Report struct{
 Schema string `json:"schema"`
 ParentF10DigestSHA256 string `json:"parent_f10_digest_sha256"`
 TrainingSeeds [2]uint32 `json:"training_seeds"`
 Policies [3]string `json:"policies"`
 HypothesisCount int `json:"hypothesis_count"`
 PosteriorOdds int `json:"posterior_odds"`
 DecisionsPerModelPerGeneration int `json:"decisions_per_model_per_generation"`
 MinimumAdditionalCorrect int `json:"minimum_additional_correct"`
 TotalArms int `json:"total_arms"`
 TotalInterventions int `json:"total_interventions"`
 TotalPlannerPredictionCalls int `json:"total_planner_prediction_calls"`
 UncertaintyVersusStrongest [2]int `json:"uncertainty_versus_strongest"`
 UncertaintyVersusBestAblation [2]int `json:"uncertainty_versus_best_ablation"`
 UncertaintyWinningSeeds int `json:"uncertainty_winning_seeds"`
 OriginalWorldRetainedArms int `json:"original_world_retained_arms"`
 Arms []F11Arm `json:"arms"`
 Classification string `json:"classification"`
 DevelopmentOnly bool `json:"development_only"`
 F10NegativePreserved bool `json:"f10_negative_preserved"`
 SameSyntheticTrainingOnly bool `json:"same_synthetic_training_only"`
 DifferentPlannerCoordinatesAllowed bool `json:"different_planner_coordinates_allowed"`
 IndependentFirstUseConsumed bool `json:"independent_first_use_consumed"`
 WholeProcessCostMeasured bool `json:"whole_process_cost_measured"`
 StrongestRealWorldBaselineQualified bool `json:"strongest_real_world_baseline_qualified"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OwnerEligible bool `json:"owner_eligible"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ExistingF139LaneAltered bool `json:"existing_f139_lane_altered"`
 ExperimentIssued bool `json:"experiment_issued"`
 PaidAPICalls int `json:"paid_api_calls"`
 AgentCalls int `json:"agent_calls"`
 DigestSHA256 string `json:"digest_sha256"`
}

func f11Digest(report F11Report)string{
 report.DigestSHA256=""
 return f8Digest("FORGE-EUREKA-F11-FROZEN-CAUSAL-DEV-V1\n",report)
}
func f11Score(model f2Observer,seed uint32,regime int)(int,error){
 good,total:=f2score(model,seed,regime)
 if total!=F2EvaluationCount||good<0||good>total{return 0,errF11}
 return good,nil
}

func f11Arm(seed uint32,policy string,preview F4Preview)(F11Arm,error){
 if !f5ValidSeed(seed)||len(preview.Candidates)!=3||
  preview.TrainingSeeds!=f4TrainingSeeds()||
  preview.EvaluatedHeldout||preview.ScientificAccepted||preview.OwnerActivation{
  return F11Arm{},errF11
 }
 if policy!="uncertainty"&&policy!="fixed"&&policy!="random"{return F11Arm{},errF11}
 candidate:=&f11Posterior{}
 baseline:=&f2Tab{}
 factor:=&f2Factor{}
 native:=&f2Native{}
 var f3models [3]f3Executable
 ids:=[3]string{}
 for i,row:=range preview.Candidates{
  ids[i]=row.CandidateID
  if ids[i]==""||(i>0&&ids[i]<=ids[i-1]){return F11Arm{},errF11}
  model,err:=f3New(ids[i])
  if err!=nil{return F11Arm{},errF11}
  f3models[i]=model
 }
 controls:=[]f2Observer{candidate,baseline,factor,native,f3models[0],f3models[1],f3models[2]}
 train:=f2training(seed)
 if len(train)!=F2TrainCount||f2teach(controls,train)!=nil{return F11Arm{},errF11}
 originalBefore,err:=f11Score(candidate,seed,0)
 if err!=nil{return F11Arm{},errF11}
 out:=F11Arm{Seed:seed,Policy:policy,TrainObservations:len(train),
  Probes:make([]F5Probe,0,F5ProbeBudget)}
 used:=[8]bool{}
 scores:=[3]int{}
 for step:=0;step<F5ProbeBudget;step++{
  ctx,readouts,calls,err:=f11Choose(seed,policy,step,used,candidate,f3models)
  if err!=nil{return F11Arm{},errF11}
  key:=ctx.Cue*2+ctx.Mode
  if ctx.Regime!=1||key<0||key>=8||used[key]||calls<3{return F11Arm{},errF11}
  used[key]=true
  action:=step%2
  // Commit to coordinate/action BEFORE the world yields the intervention
  // outcome; the world seed never enters candidate's causal posterior.
  event:=f2make(seed,1,ctx.Cue,ctx.Mode,action,50+step)
  if !f2Good(event)||f5ScoreFeedback(&scores,readouts,action,event.Effect)!=nil{
   return F11Arm{},errF11
  }
  for _,model:=range controls{if model.Observe(event)!=nil{return F11Arm{},errF11}}
  out.Probes=append(out.Probes,F5Probe{Step:step,Cue:ctx.Cue,Mode:ctx.Mode,
   Action:action,ObservedEffect:event.Effect,PreObservationPredictions:readouts,
   DivergentPairs:f5Pairs(readouts)})
  out.PlannerPredictionCalls+=calls
  if step!=2&&step!=5{continue}
  if err:=native.Freeze();err!=nil{return F11Arm{},errF11}
  winner:=0
  for i:=1;i<3;i++{if scores[i]>scores[winner]{winner=i}}
  g:=0
  if step==5{g=1}
  round:=F11Round{Generation:g+1,ObservedProbes:step+1,SelectedF3ID:ids[winner],
   OriginalWorldBefore:originalBefore}
  if round.PosteriorCorrect,err=f11Score(candidate,seed,1);err!=nil{return F11Arm{},errF11}
  if round.F3Correct,err=f11Score(f3models[winner],seed,1);err!=nil{return F11Arm{},errF11}
  if round.TabularCorrect,err=f11Score(baseline,seed,1);err!=nil{return F11Arm{},errF11}
  if round.FactorizedCorrect,err=f11Score(factor,seed,1);err!=nil{return F11Arm{},errF11}
  if round.NativeCorrect,err=f11Score(native,seed,1);err!=nil{return F11Arm{},errF11}
  round.StrongestMatchedName,round.StrongestMatchedCorrect,err=
   f10StrongestCounts(round.F3Correct,round.TabularCorrect,round.FactorizedCorrect,round.NativeCorrect)
  if err!=nil{return F11Arm{},errF11}
  round.AdvantageOverStrongest=round.PosteriorCorrect-round.StrongestMatchedCorrect
  if round.OriginalWorldAfter,err=f11Score(candidate,seed,0);err!=nil{return F11Arm{},errF11}
  round.OriginalWorldRetained=round.OriginalWorldAfter==round.OriginalWorldBefore
  snapshot,err:=candidate.Snapshot()
  if err!=nil||len(snapshot)<10||len(snapshot)>4096{return F11Arm{},errF11}
  round.SnapshotSHA256=f3Hash(snapshot)
  round.SnapshotBytes=len(snapshot)
  cold:=&f11Posterior{}
  if cold.Load(snapshot)!=nil{return F11Arm{},errF11}
  round.ColdPredictionMatches=true
  for regime:=0;regime<2;regime++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
   ctx:=f2Context{Regime:regime,Cue:cue,Mode:mode}
   if candidate.Predict(ctx)!=cold.Predict(ctx){return F11Arm{},errF11}
  }}}
  if !round.OriginalWorldRetained||!round.ColdPredictionMatches{return F11Arm{},errF11}
  out.Rounds[g]=round
 }
 out.ProbeObservations=len(out.Probes)
 if len(out.Probes)!=F5ProbeBudget{return F11Arm{},errF11}
 out.FeedbackSHA256=f7FeedbackHash(seed,policy,out.Probes)
 return out,nil
}

func F11Development()(F11Report,error){
 f10,err:=F10Development()
 if err!=nil||F10Validate(f10)!=nil||f10.Classification!=F10ReviewNO_GO||
  f10.ScientificAccepted||f10.OwnerEligible||f10.DispatchAuthorized{
  return F11Report{},errF11
 }
 preview,err:=F4Development()
 if err!=nil||F4ValidatePreview(preview)!=nil{return F11Report{},errF11}
 out:=F11Report{
  Schema:F11Schema,ParentF10DigestSHA256:f10.DigestSHA256,
  TrainingSeeds:f4TrainingSeeds(),Policies:f11Policies(),
  HypothesisCount:F11Hypotheses,PosteriorOdds:F11PriorOdds,
  DecisionsPerModelPerGeneration:F2EvaluationCount,
  MinimumAdditionalCorrect:F11MinimumAdditionalCorrect,
  Arms:make([]F11Arm,0,6),DevelopmentOnly:true,
  F10NegativePreserved:true,SameSyntheticTrainingOnly:true,
  DifferentPlannerCoordinatesAllowed:true,
 }
 for _,seed:=range out.TrainingSeeds{
  for _,policy:=range out.Policies{
   arm,err:=f11Arm(seed,policy,preview)
   if err!=nil{return F11Report{},errF11}
   out.Arms=append(out.Arms,arm)
   out.TotalArms++
   out.TotalInterventions+=arm.ProbeObservations
   out.TotalPlannerPredictionCalls+=arm.PlannerPredictionCalls
   if arm.Rounds[0].OriginalWorldRetained&&arm.Rounds[1].OriginalWorldRetained{
    out.OriginalWorldRetainedArms++
   }
  }
 }
 if out.TotalArms!=6||out.TotalInterventions!=6*F5ProbeBudget||
  out.OriginalWorldRetainedArms!=6{return F11Report{},errF11}
 for i:=0;i<2;i++{
  block:=out.Arms[i*3:i*3+3]
  main:=block[0].Rounds[1].PosteriorCorrect
  strongest:=block[0].Rounds[1].StrongestMatchedCorrect
  betterAblation:=max(block[1].Rounds[1].PosteriorCorrect,block[2].Rounds[1].PosteriorCorrect)
  out.UncertaintyVersusStrongest[i]=main-strongest
  out.UncertaintyVersusBestAblation[i]=main-betterAblation
  if main-strongest>=F11MinimumAdditionalCorrect&&
   main-betterAblation>=F11MinimumAdditionalCorrect{
   out.UncertaintyWinningSeeds++
  }
 }
 if out.UncertaintyWinningSeeds==2{out.Classification=F11ReviewSignal
 }else{out.Classification=F11ReviewNO_GO}
 out.DigestSHA256=f11Digest(out)
 return out,nil
}

func F11Validate(x F11Report)error{
 if x.Schema!=F11Schema||x.DigestSHA256!=f11Digest(x)||
  !x.DevelopmentOnly||!x.F10NegativePreserved||!x.SameSyntheticTrainingOnly||
  !x.DifferentPlannerCoordinatesAllowed||x.IndependentFirstUseConsumed||
  x.WholeProcessCostMeasured||x.StrongestRealWorldBaselineQualified||
  x.ScientificAccepted||x.OwnerEligible||x.DispatchAuthorized||
  x.ExistingF139LaneAltered||x.ExperimentIssued||
  x.AgentCalls!=0||x.PaidAPICalls!=0{return errF11}
 exact,err:=F11Development()
 if err!=nil||!reflect.DeepEqual(x,exact){return errF11}
 return nil
}
