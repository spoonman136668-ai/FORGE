// Eureka F5: a pure TRAIN-only hypothesis tournament over the existing three
// compiled F3 candidates. No source writing, holdout, FSA, controller or worker.
package nativediscovery

import (
 "errors"
 "reflect"
)

const F5Schema = "forge.native-discovery.training-intervention-tournament.v1"
const F5ProbeBudget = 6
var errF5 = errors.New("FORGE_EUREKA_F5_TRAINING_TOURNAMENT_INVALID")

func f5Policies() [3]string { return [3]string{"disagreement","fixed","random"} }
func f5ValidSeed(seed uint32) bool { return seed==17||seed==31 }

type F5Probe struct {
 Step int `json:"step"`
 Cue int `json:"cue"`
 Mode int `json:"mode"`
 Action int `json:"action"`
 ObservedEffect int `json:"observed_effect"`
 PreObservationPredictions [3]int `json:"pre_observation_predictions"`
 DivergentPairs int `json:"divergent_pairs"`
}

type F5CandidateResult struct {
 CandidateID string `json:"candidate_id"`
 StructuralSourceSHA256 string `json:"structural_source_sha256"`
 F4BehaviorSHA256 string `json:"f4_behavior_sha256"`
 F4DuplicateBehaviorOf string `json:"f4_duplicate_behavior_of"`
 EvidenceScore int `json:"evidence_score"`
 ChangedWorldAccuracyPct float64 `json:"changed_world_accuracy_pct"`
}

type F5ArmResult struct {
 Policy string `json:"policy"`
 Seed uint32 `json:"seed"`
 TrainObservations int `json:"train_observations"`
 ProbeObservations int `json:"probe_observations"`
 ScoredDecisionsPerModel int `json:"scored_decisions_per_model"`
 PlannerPredictionCalls int `json:"planner_prediction_calls"`
 DisagreementProbeCount int `json:"disagreement_probe_count"`
 SelectedCandidateID string `json:"selected_candidate_id"`
 SelectedAccuracyPct float64 `json:"selected_accuracy_pct"`
 TabularAccuracyPct float64 `json:"tabular_accuracy_pct"`
 FactorizedAccuracyPct float64 `json:"factorized_accuracy_pct"`
 ExistingF2NativeAccuracyPct float64 `json:"existing_f2_native_accuracy_pct"`
 StrongestControlAccuracyPct float64 `json:"strongest_control_accuracy_pct"`
 Probes []F5Probe `json:"probes"`
 Candidates []F5CandidateResult `json:"candidates"`
}

type F5Report struct {
 Schema string `json:"schema"`
 F4Schema string `json:"f4_schema"`
 F4GeneratedSourceSHA256 string `json:"f4_generated_source_sha256"`
 NativeGeneratorFrozenSHA256 string `json:"native_generator_frozen_sha256"`
 SyntheticTrainingHistorySHA256 string `json:"synthetic_training_history_sha256"`
 TrainingSeeds [2]uint32 `json:"training_seeds"`
 Policies [3]string `json:"policies"`
 Arms []F5ArmResult `json:"arms"`
 DevelopmentStatus string `json:"development_status"`
 ReusedSyntheticTraining bool `json:"reused_synthetic_training"`
 IndependentHoldoutConsumed bool `json:"independent_holdout_consumed"`
 NewMechanismGenerated bool `json:"new_mechanism_generated"`
 ScientificAccepted bool `json:"scientific_accepted"`
 GeneralRSIProven bool `json:"general_rsi_proven"`
 OwnerActivation bool `json:"owner_activation"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
}

// f5Read returns the three pre-outcome sign predictions. The caller may not
// inspect the environment's actual effect until AFTER selecting a coordinate.
func f5Read(models [3]f3Executable,cue,mode int)([3]int,error){
 var out [3]int
 if cue<0||cue>=4||mode<0||mode>=2{return out,errF5}
 for i,model:=range models {
  out[i]=model.Predict(f2Context{Regime:1,Cue:cue,Mode:mode})
  if out[i]!=1&&out[i]!= -1{return [3]int{},errF5}
 }
 return out,nil
}
func f5Pairs(p [3]int)int{
 n:=0
 for i:=0;i<len(p);i++{for j:=i+1;j<len(p);j++{
  if p[i]!=p[j]{n++}
 }}
 return n
}
func f5Select(policy string,seed uint32,step int,used [8]bool,models [3]f3Executable)(f2Context,[3]int,int,int,error){
 var none f2Context
 if !f5ValidSeed(seed)||step<0||step>=F5ProbeBudget{return none,[3]int{},0,0,errF5}
 remaining:=make([]int,0,8)
 for i:=0;i<8;i++{if !used[i]{remaining=append(remaining,i)}}
 if len(remaining)<1{return none,[3]int{},0,0,errF5}
 index,calls:=-1,0
 switch policy {
 case "fixed":
  order:=[F5ProbeBudget]int{0,2,4,6,1,5}
  index=order[step]
  if used[index]{return none,[3]int{},0,0,errF5}
 case "random":
  slot:=int(f2mix(seed^0x9e3779b9^uint32(step*7919+37))%uint32(len(remaining)))
  index=remaining[slot]
 case "disagreement":
  best:=-1
  for _,candidate:=range remaining{
   predictions,err:=f5Read(models,candidate/2,candidate%2)
   if err!=nil{return none,[3]int{},0,0,err}
   calls+=len(models)
   pairs:=f5Pairs(predictions)
   if pairs>best{best=pairs;index=candidate}
  }
 default:
  return none,[3]int{},0,0,errF5
 }
 if index<0||used[index]{return none,[3]int{},0,0,errF5}
 readout,err:=f5Read(models,index/2,index%2)
 if err!=nil{return none,[3]int{},0,0,err}
 calls+=len(models)
 return f2Context{Regime:1,Cue:index/2,Mode:index%2},readout,f5Pairs(readout),calls,nil
}

// Evidence is scored BEFORE each model sees the new observation. Only actual
// action/consequence feedback changes the scores, not oracle counterfactuals.
func f5ScoreFeedback(scores *[3]int,predictions [3]int,action,effect int)error{
 if action!=0&&action!=1||effect!=1&&effect!= -1{return errF5}
 normalized:=effect
 if action==1{normalized= -normalized}
 for i,pred:=range predictions {
  if pred!=1&&pred!= -1{return errF5}
  if pred==normalized{scores[i]++}else{scores[i]--}
 }
 return nil
}

func f5Run(policy string,seed uint32,parent F4Preview)(F5ArmResult,error){
 if !f5ValidSeed(seed)||len(parent.Candidates)!=3||parent.TrainingSeeds!=f4TrainingSeeds()||
  parent.EvaluatedHeldout||parent.ScientificAccepted||parent.OwnerActivation{return F5ArmResult{},errF5}
 ids:=[3]string{}
 models:=[3]f3Executable{}
 for i,row:=range parent.Candidates{
  if row.CandidateID==""||(i>0&&row.CandidateID<=ids[i-1]){return F5ArmResult{},errF5}
  ids[i]=row.CandidateID
  model,err:=f3New(row.CandidateID)
  if err!=nil{return F5ArmResult{},err}
  models[i]=model
 }
 tabular,factorized,native:=&f2Tab{},&f2Factor{},&f2Native{}
 arms:=[]f2Observer{models[0],models[1],models[2],tabular,factorized,native}
 training:=f2training(seed)
 if len(training)!=F2TrainCount{return F5ArmResult{},errF5}
 if err:=f2teach(arms,training);err!=nil{return F5ArmResult{},err}
 out:=F5ArmResult{Policy:policy,Seed:seed,TrainObservations:len(training),
  Probes:make([]F5Probe,0,F5ProbeBudget),
  Candidates:make([]F5CandidateResult,0,len(models))}
 used:=[8]bool{}
 scores:=[3]int{}
 for step:=0;step<F5ProbeBudget;step++{
  context,predictions,pairs,calls,err:=f5Select(policy,seed,step,used,models)
  if err!=nil{return F5ArmResult{},err}
  out.PlannerPredictionCalls+=calls
  key:=context.Cue*2+context.Mode
  if context.Regime!=1||key<0||key>=8||used[key]{return F5ArmResult{},errF5}
  used[key]=true
  action:=step%2
  // Environment outcome is first computed AFTER the planner has committed to
  // the coordinate and action. The action is the same across all policies.
  event:=f2make(seed,1,context.Cue,context.Mode,action,50+step)
  if !f2Good(event){return F5ArmResult{},errF5}
  if err:=f5ScoreFeedback(&scores,predictions,action,event.Effect);err!=nil{
   return F5ArmResult{},err
  }
  for _,observer:=range arms{
   if err:=observer.Observe(event);err!=nil{return F5ArmResult{},err}
  }
  if pairs>0{out.DisagreementProbeCount++}
  out.Probes=append(out.Probes,F5Probe{Step:step,Cue:context.Cue,
   Mode:context.Mode,Action:action,ObservedEffect:event.Effect,
   PreObservationPredictions:predictions,DivergentPairs:pairs})
 }
 if err:=native.Freeze();err!=nil{return F5ArmResult{},err}
 out.ProbeObservations=len(out.Probes)
 winner:=0
 for i:=1;i<len(scores);i++{
  if scores[i]>scores[winner]{winner=i}
 }
 for i,model:=range models{
  successes,total:=f2score(model,seed,1)
  if total!=F2EvaluationCount{return F5ArmResult{},errF5}
  out.Candidates=append(out.Candidates,F5CandidateResult{
   CandidateID:ids[i],StructuralSourceSHA256:parent.Candidates[i].StructuralSourceSHA256,
   F4BehaviorSHA256:parent.Candidates[i].TrainingBehaviorSHA256,
   F4DuplicateBehaviorOf:parent.Candidates[i].DuplicateBehaviorOf,
   EvidenceScore:scores[i],ChangedWorldAccuracyPct:f2accuracy(successes,total),
  })
 }
 out.SelectedCandidateID=ids[winner]
 out.SelectedAccuracyPct=out.Candidates[winner].ChangedWorldAccuracyPct
 tabScore,tabTotal:=f2score(tabular,seed,1)
 factScore,factTotal:=f2score(factorized,seed,1)
 nativeScore,nativeTotal:=f2score(native,seed,1)
 if tabTotal!=F2EvaluationCount||factTotal!=F2EvaluationCount||
  nativeTotal!=F2EvaluationCount{return F5ArmResult{},errF5}
 out.TabularAccuracyPct=f2accuracy(tabScore,tabTotal)
 out.FactorizedAccuracyPct=f2accuracy(factScore,factTotal)
 out.ExistingF2NativeAccuracyPct=f2accuracy(nativeScore,nativeTotal)
 out.StrongestControlAccuracyPct=out.TabularAccuracyPct
 if out.FactorizedAccuracyPct>out.StrongestControlAccuracyPct{
  out.StrongestControlAccuracyPct=out.FactorizedAccuracyPct
 }
 if out.ExistingF2NativeAccuracyPct>out.StrongestControlAccuracyPct{
  out.StrongestControlAccuracyPct=out.ExistingF2NativeAccuracyPct
 }
 out.ScoredDecisionsPerModel=F2EvaluationCount
 return out,nil
}
func F5Development()(F5Report,error){
 parent,err:=F4Development()
 if err!=nil||len(parent.Candidates)!=3||parent.Schema!=F4Schema||
  parent.TrainingSeeds!=f4TrainingSeeds()||
  parent.EvaluatedHeldout||parent.ScientificAccepted||
  parent.OwnerActivation||parent.AgentCalls!=0||parent.PaidAPICalls!=0{
  return F5Report{},errF5
 }
 result:=F5Report{Schema:F5Schema,F4Schema:parent.Schema,
  F4GeneratedSourceSHA256:parent.ParentGeneratedSourceSHA256,
  NativeGeneratorFrozenSHA256:parent.NativeGeneratorFrozenSHA256,
  SyntheticTrainingHistorySHA256:parent.SyntheticTrainingHistorySHA256,
  TrainingSeeds:f4TrainingSeeds(),Policies:f5Policies(),
  DevelopmentStatus:"TRAIN_ONLY_SCIENCE_UNVERIFIED",
  ReusedSyntheticTraining:true,Arms:make([]F5ArmResult,0,6)}
 for _,seed:=range result.TrainingSeeds{
  for _,policy:=range result.Policies{
   trial,err:=f5Run(policy,seed,parent)
   if err!=nil{return F5Report{},err}
   result.Arms=append(result.Arms,trial)
  }
 }
 return result,nil
}
func F5ValidatePreview(report F5Report)error{
 expected,err:=F5Development()
 if err!=nil||!reflect.DeepEqual(expected,report){return errF5}
 return nil
}
