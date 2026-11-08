// Eureka F7: two successive TRAIN-only feedback generations. Reuses existing
// F5 observations/F6 source grammar/F2 conventional controls. NO dispatch,
// original-owner hooks, runtime compilation, first-use, science or promotion.
package nativediscovery

import (
 "encoding/json"
 "errors"
 "reflect"
)

const F7Schema = "forge.native-discovery.two-generation-feedback-dev.v1"
const F7Generations = 2
const F7FirstProbeCount = 3
var errF7 = errors.New("FORGE_EUREKA_F7_FEEDBACK_GENERATION_INVALID")

type F7Generation struct {
 Generation int `json:"generation"`
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 InitialTrainObservations int `json:"initial_train_observations"`
 ObservedProbes int `json:"observed_probes"`
 AddedProbes int `json:"added_probes"`
 ScoredDevelopmentDecisions int `json:"scored_development_decisions_per_candidate"`
 ParentGenerationReceiptSHA256 string `json:"parent_generation_receipt_sha256"`
 FeedbackPrefixSHA256 string `json:"feedback_prefix_sha256"`
 GenerationReceiptSHA256 string `json:"generation_receipt_sha256"`
 Candidates []F6GeneratedCandidate `json:"candidates"`
 SelectedFamily string `json:"selected_family"`
 SelectedPhase int `json:"selected_phase"`
 SelectedSourceSHA256 string `json:"selected_source_sha256"`
 SelectedTrainingCorrect int `json:"selected_training_correct"`
 SelectedDevAccuracyPct float64 `json:"selected_dev_accuracy_pct"`
 PriorF5SelectedAccuracyPct float64 `json:"prior_f5_selected_accuracy_pct"`
 TabularAccuracyPct float64 `json:"tabular_accuracy_pct"`
 FactorizedAccuracyPct float64 `json:"factorized_accuracy_pct"`
 ExistingNativeAccuracyPct float64 `json:"existing_native_accuracy_pct"`
 StrongestControlAccuracyPct float64 `json:"strongest_control_accuracy_pct"`
 GainOverStrongestControlPP float64 `json:"gain_over_strongest_control_pp"`
 GainOverPreviousGenerationPP float64 `json:"gain_over_previous_generation_pp"`
 OriginalWorldBeforePct float64 `json:"original_world_before_pct"`
 OriginalWorldAfterPct float64 `json:"original_world_after_pct"`
 OriginalWorldColdPct float64 `json:"original_world_cold_pct"`
 ColdStateByteCount int `json:"cold_state_byte_count"`
 ColdReadbackIdentical bool `json:"cold_readback_identical"`
 SourceChangedSincePrevious bool `json:"source_changed_since_previous"`
 DevelopmentClassification string `json:"development_classification"`
}

type F7ArmResult struct {
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 F5FeedbackSHA256 string `json:"f5_feedback_sha256"`
 Generations [F7Generations]F7Generation `json:"generations"`
}

type F7Report struct {
 Schema string `json:"schema"`
 F5SourceSHA256 string `json:"f5_source_sha256"`
 F6Schema string `json:"f6_schema"`
 TrainingSeeds [2]uint32 `json:"training_seeds"`
 Policies [3]string `json:"policies"`
 GenerationsPerArm int `json:"generations_per_arm"`
 GeneratedCandidateCount int `json:"generated_candidate_count"`
 Arms []F7ArmResult `json:"arms"`
 DevelopmentOnly bool `json:"development_only"`
 GeneratedSourceTypecheckedInTestsOnly bool `json:"generated_source_compiled_in_tests_only"`
 NewExperimentObservations int `json:"new_experiment_observations"`
 IndependentHoldoutConsumed bool `json:"independent_holdout_consumed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 GeneralRSIProven bool `json:"general_rsi_proven"`
 OwnerActivation bool `json:"owner_activation"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
}

func f7FeedbackHash(seed uint32,policy string,probes []F5Probe)string{
 b,_:=json.Marshal(struct{
  Seed uint32
  Policy string
  Probes []F5Probe
 }{seed,policy,probes})
 return f3Hash(b)
}

func f7Receipt(row F7Generation)string{
 row.GenerationReceiptSHA256=""
 raw,_:=json.Marshal(row)
 return f3Hash(append([]byte("FORGE_EUREKA_F7_CHAIN_V1\n"),raw...))
}

func f7ObservedTransitions(probes []F5Probe) ([]f2Transition,error){
 if len(probes)!=F7FirstProbeCount&&len(probes)!=F5ProbeBudget{return nil,errF7}
 out:=make([]f2Transition,0,len(probes))
 used:=[8]bool{}
 for i,p:=range probes{
  key:=p.Cue*2+p.Mode
  if p.Step!=i||p.Cue<0||p.Cue>=4||p.Mode<0||p.Mode>=2||
   key<0||key>=8||used[key]||p.Action!=i%2||
   p.ObservedEffect!=1&&p.ObservedEffect!= -1||
   p.DivergentPairs!=f5Pairs(p.PreObservationPredictions){return nil,errF7}
  for _,x:=range p.PreObservationPredictions{if x!=1&&x!= -1{return nil,errF7}}
  used[key]=true
  out=append(out,f2Transition{Context:f2Context{Regime:1,Cue:p.Cue,Mode:p.Mode},
   Action:p.Action,Effect:p.ObservedEffect})
 }
 return out,nil
}

func f7BuildGeneration(arm F5ArmResult, parent F5Report,previous *F7Generation, count int)(F7Generation,error){
 if !f5ValidSeed(arm.Seed)||len(arm.Probes)!=F5ProbeBudget||
  (arm.Policy!="disagreement"&&arm.Policy!="fixed"&&arm.Policy!="random")||
  parent.F4GeneratedSourceSHA256==""||
  (count!=F7FirstProbeCount&&count!=F5ProbeBudget){return F7Generation{},errF7}
 partial:=arm.Probes[:count]
 observations,err:=f7ObservedTransitions(partial)
 if err!=nil{return F7Generation{},errF7}
 proposed,err:=f6ProposeN(partial,count)
 if err!=nil||len(proposed)!=F6Families{return F7Generation{},errF7}
 row:=F7Generation{
  Seed:arm.Seed,Policy:arm.Policy,InitialTrainObservations:F2TrainCount,
  ObservedProbes:count,AddedProbes:F7FirstProbeCount,
  ScoredDevelopmentDecisions:F2EvaluationCount,FeedbackPrefixSHA256:f7FeedbackHash(arm.Seed,arm.Policy,partial),
  Candidates:make([]F6GeneratedCandidate,0,F6Families),
 }
 if count==F7FirstProbeCount{
  if previous!=nil{return F7Generation{},errF7}
  row.Generation=1
  row.ParentGenerationReceiptSHA256=parent.F4GeneratedSourceSHA256
 }else{
  if previous==nil||previous.Generation!=1||
   previous.ObservedProbes!=F7FirstProbeCount||
   previous.Seed!=arm.Seed||previous.Policy!=arm.Policy||
   previous.GenerationReceiptSHA256!=f7Receipt(*previous){return F7Generation{},errF7}
  row.Generation=2
  row.ParentGenerationReceiptSHA256=previous.GenerationReceiptSHA256
 }
 // Each arm sees the same real F5 actions and effects, at each G1/G2 cut.
 old,err:=f3New(arm.SelectedCandidateID)
 if err!=nil{return F7Generation{},errF7}
 table,factor,native:=&f2Tab{},&f2Factor{},&f2Native{}
 controls:=[]f2Observer{old,table,factor,native}
 train:=f2training(arm.Seed)
 if len(train)!=F2TrainCount{return F7Generation{},errF7}
 if err:=f2teach(controls,train);err!=nil{return F7Generation{},errF7}
 if err:=f2teach(controls,observations);err!=nil{return F7Generation{},errF7}
 if err:=native.Freeze();err!=nil{return F7Generation{},errF7}
 success,total:=f2score(old,arm.Seed,1)
 if total!=F2EvaluationCount{return F7Generation{},errF7}
 row.PriorF5SelectedAccuracyPct=f2accuracy(success,total)
 success,total=f2score(table,arm.Seed,1)
 if total!=F2EvaluationCount{return F7Generation{},errF7}
 row.TabularAccuracyPct=f2accuracy(success,total)
 success,total=f2score(factor,arm.Seed,1)
 if total!=F2EvaluationCount{return F7Generation{},errF7}
 row.FactorizedAccuracyPct=f2accuracy(success,total)
 success,total=f2score(native,arm.Seed,1)
 if total!=F2EvaluationCount{return F7Generation{},errF7}
 row.ExistingNativeAccuracyPct=f2accuracy(success,total)
 row.StrongestControlAccuracyPct=row.TabularAccuracyPct
 if row.FactorizedAccuracyPct>row.StrongestControlAccuracyPct{
  row.StrongestControlAccuracyPct=row.FactorizedAccuracyPct
 }
 if row.ExistingNativeAccuracyPct>row.StrongestControlAccuracyPct{
  row.StrongestControlAccuracyPct=row.ExistingNativeAccuracyPct
 }
 // Before diagnostic scoring, generation selection depends ONLY on observed
 // training fit. In particular none of the scored development labels enter it.
 selected:=0
 for i:=1;i<len(proposed);i++{
  if proposed[i].TrainingCorrect>proposed[selected].TrainingCorrect{selected=i}
 }
 selectedModel:=&f6Repair{Family:proposed[selected].Family,Phase:proposed[selected].Phase}
 for i,proposal:=range proposed{
  model:=&f6Repair{Family:proposal.Family,Phase:proposal.Phase}
  if err:=f2teach([]f2Observer{model},train);err!=nil{return F7Generation{},errF7}
  if err:=f2teach([]f2Observer{model},observations);err!=nil{return F7Generation{},errF7}
  success,total=f2score(model,arm.Seed,1)
  if total!=F2EvaluationCount{return F7Generation{},errF7}
  proposal.DevChangedWorldAccuracyPct=f2accuracy(success,total)
  row.Candidates=append(row.Candidates,proposal)
  if i==selected{selectedModel=model}
 }
 chosen:=row.Candidates[selected]
 row.SelectedFamily=chosen.Family
 row.SelectedPhase=chosen.Phase
 row.SelectedSourceSHA256=chosen.SourceSHA256
 row.SelectedTrainingCorrect=chosen.TrainingCorrect
 row.SelectedDevAccuracyPct=chosen.DevChangedWorldAccuracyPct
 row.GainOverStrongestControlPP=row.SelectedDevAccuracyPct-row.StrongestControlAccuracyPct
 if previous!=nil{
  row.GainOverPreviousGenerationPP=row.SelectedDevAccuracyPct-previous.SelectedDevAccuracyPct
  row.SourceChangedSincePrevious=row.SelectedSourceSHA256!=previous.SelectedSourceSHA256
 }
 // Original-world retained capability is a separate diagnostic: training has
 // zero new regime-0 observations after the initial 48; test cold readback.
 a,n:=f2score(selectedModel,arm.Seed,0)
 if n!=F2EvaluationCount{return F7Generation{},errF7}
 row.OriginalWorldAfterPct=f2accuracy(a,n)
 // Original-world before the probe stream is reconstructed from the same
 // frozen training cohort, without accessing downstream outcome labels.
 before:=&f6Repair{Family:chosen.Family,Phase:chosen.Phase}
 if err:=f2teach([]f2Observer{before},train);err!=nil{return F7Generation{},errF7}
 a,n=f2score(before,arm.Seed,0)
 if n!=F2EvaluationCount{return F7Generation{},errF7}
 row.OriginalWorldBeforePct=f2accuracy(a,n)
 snapshot,err:=selectedModel.Snapshot()
 if err!=nil||len(snapshot)==0||len(snapshot)>4096{return F7Generation{},errF7}
 cold:=&f6Repair{Family:chosen.Family,Phase:chosen.Phase}
 if err:=cold.Load(snapshot);err!=nil{return F7Generation{},errF7}
 for regime:=0;regime<2;regime++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
  ctx:=f2Context{Regime:regime,Cue:cue,Mode:mode}
  if cold.Predict(ctx)!=selectedModel.Predict(ctx){return F7Generation{},errF7}
 }}}
 a,n=f2score(cold,arm.Seed,0)
 if n!=F2EvaluationCount{return F7Generation{},errF7}
 row.OriginalWorldColdPct=f2accuracy(a,n)
 row.ColdReadbackIdentical=row.OriginalWorldColdPct==row.OriginalWorldAfterPct
 if !row.ColdReadbackIdentical||row.OriginalWorldAfterPct!=row.OriginalWorldBeforePct{return F7Generation{},errF7}
 row.ColdStateByteCount=len(snapshot)
 if row.GainOverStrongestControlPP<=0{
  row.DevelopmentClassification="F7_DEV_NO_GO"
 }else{
  row.DevelopmentClassification="F7_DEV_AHEAD_UNVERIFIED"
 }
 row.GenerationReceiptSHA256=f7Receipt(row)
 return row,nil
}

func F7Development()(F7Report,error){
 f5,err:=F5Development()
 if err!=nil||F5ValidatePreview(f5)!=nil||f5.Schema!=F5Schema||
  f5.TrainingSeeds!=f4TrainingSeeds()||f5.Policies!=f5Policies()||
  len(f5.Arms)!=6||f5.ScientificAccepted||f5.OwnerActivation||
  f5.DispatchAuthorized||f5.IndependentHoldoutConsumed||
  f5.AgentCalls!=0||f5.PaidAPICalls!=0{return F7Report{},errF7}
 f6,err:=F6Development()
 if err!=nil||F6ValidatePreview(f6)!=nil||f6.Schema!=F6Schema||
  len(f6.Arms)!=len(f5.Arms)||f6.IndependentHoldoutConsumed||
  f6.ScientificAccepted||f6.OwnerActivation{return F7Report{},errF7}
 out:=F7Report{
  Schema:F7Schema,F5SourceSHA256:f5.F4GeneratedSourceSHA256,
  F6Schema:f6.Schema,TrainingSeeds:f5.TrainingSeeds,Policies:f5.Policies,
  GenerationsPerArm:F7Generations,
  Arms:make([]F7ArmResult,0,len(f5.Arms)),DevelopmentOnly:true,
  GeneratedSourceTypecheckedInTestsOnly:true,
 }
 for i,arm:=range f5.Arms{
  if arm.Seed!=out.TrainingSeeds[i/3]||arm.Policy!=out.Policies[i%3]||
   arm.TrainObservations!=F2TrainCount||arm.ProbeObservations!=F5ProbeBudget||
   len(arm.Probes)!=F5ProbeBudget||arm.ScoredDecisionsPerModel!=F2EvaluationCount||
   f6.Arms[i].Seed!=arm.Seed||f6.Arms[i].ParentF5Policy!=arm.Policy{
   return F7Report{},errF7
  }
  trial:=F7ArmResult{Seed:arm.Seed,Policy:arm.Policy,
   F5FeedbackSHA256:f6FeedbackSHA(arm,f5)}
  first,err:=f7BuildGeneration(arm,f5,nil,F7FirstProbeCount)
  if err!=nil{return F7Report{},err}
  second,err:=f7BuildGeneration(arm,f5,&first,F5ProbeBudget)
  if err!=nil{return F7Report{},err}
  // Generation 2 must reproduce original F6 six-probe ranking and source.
  if second.SelectedSourceSHA256!=f6.Arms[i].SelectedSourceSHA256||
   second.SelectedFamily!=f6.Arms[i].SelectedFamily||
   second.SelectedDevAccuracyPct!=f6.Arms[i].SelectedDevChangedWorldAccuracyPct{
   return F7Report{},errF7
  }
  trial.Generations=[F7Generations]F7Generation{first,second}
  out.Arms=append(out.Arms,trial)
  out.GeneratedCandidateCount+=len(first.Candidates)+len(second.Candidates)
 }
 if out.GeneratedCandidateCount!=6*F7Generations*F6Families{return F7Report{},errF7}
 return out,nil
}

func F7ValidatePreview(report F7Report)error{
 exact,err:=F7Development()
 if err!=nil||!reflect.DeepEqual(report,exact){return errF7}
 return nil
}
