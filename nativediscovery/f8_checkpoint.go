// Eureka F8: portable, source-bound cumulative native state. The original
// f3Core Snapshot/Load is the sole learning-state format. No writer, runner,
// owner, scientific first-use, original-research archive or new subprocess.
package nativediscovery

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "reflect"
)

const F8Schema="forge.native-discovery.cumulative-cold-checkpoint.dev.v1"
const F8MaxBytes=1<<20
var errF8=errors.New("FORGE_EUREKA_F8_COLD_RESTORE_SOURCE_OR_AUTHORITY_INVALID")

type F8Step struct{
 Generation int `json:"generation"`
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 F7GenerationReceiptSHA256 string `json:"f7_generation_receipt_sha256"`
 PreviousStepSHA256 string `json:"previous_step_sha256"`
 SelectedFamily string `json:"selected_family"`
 SelectedPhase int `json:"selected_phase"`
 SelectedSourceSHA256 string `json:"selected_source_sha256"`
 SelectedTrainingCorrect int `json:"selected_training_correct"`
 OriginalTrainObservationCount int `json:"original_train_observation_count"`
 PreviouslyLearnedObservations int `json:"previously_learned_observations"`
 NewlyAppliedObservations int `json:"newly_applied_observations"`
 PriorObservationsReapplied int `json:"prior_observations_reapplied"`
 TotalObservedEvidence int `json:"total_observed_evidence"`
 SelectedDevelopmentClassification string `json:"selected_development_classification"`
 GeneratedCandidateSources [F6Families]string `json:"generated_candidate_sources"`
 SnapshotBytes []byte `json:"snapshot_bytes"`
 SnapshotSHA256 string `json:"snapshot_sha256"`
 PredictionSHA256 string `json:"prediction_sha256"`
 ExactFullReplayMatches bool `json:"exact_full_replay_matches"`
 ColdStateReadbackMatches bool `json:"cold_state_readback_matches"`
 RecordSHA256 string `json:"record_sha256"`
}

type F8Arm struct{
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 F5FeedbackSHA256 string `json:"f5_feedback_sha256"`
 Steps [F7Generations]F8Step `json:"steps"`
}

type F8Checkpoint struct{
 Schema string `json:"schema"`
 F7ReportSHA256 string `json:"f7_report_sha256"`
 F5SourceSHA256 string `json:"f5_source_sha256"`
 TrainingSeeds [2]uint32 `json:"training_seeds"`
 Policies [3]string `json:"policies"`
 Arms []F8Arm `json:"arms"`
 TotalSteps int `json:"total_steps"`
 NewGeneratedObservations int `json:"new_generated_observations"`
 DevelopmentOnly bool `json:"development_only"`
 GeneratedSourceExecuted bool `json:"generated_source_executed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 IndependentFirstUseConsumed bool `json:"independent_first_use_consumed"`
 RSIProven bool `json:"rsi_proven"`
 OwnerActivation bool `json:"owner_activation"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 CheckpointSHA256 string `json:"checkpoint_sha256"`
}

func f8Digest(domain string,v any)string{
 raw,_:=json.Marshal(v)
 return f3Hash(append([]byte(domain),raw...))
}
func f8StepDigest(v F8Step)string{
 v.RecordSHA256=""
 return f8Digest("FORGE-EUREKA-F8-STEP-V1\n",v)
}
func f8CheckpointDigest(v F8Checkpoint)string{
 v.CheckpointSHA256=""
 return f8Digest("FORGE-EUREKA-F8-BUNDLE-V1\n",v)
}
func f8Predictions(m *f6Repair)string{
 var predictions [2][4][2]int
 for r:=0;r<2;r++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
  predictions[r][c][mode]=m.Predict(f2Context{Regime:r,Cue:c,Mode:mode})
 }}}
 return f8Digest("FORGE-EUREKA-F8-16-PREDICTIONS-V1\n",predictions)
}
func f8Matches(a,b *f6Repair)bool{
 if a==nil||b==nil||a.Family!=b.Family||a.Phase!=b.Phase{return false}
 for r:=0;r<2;r++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
  ctx:=f2Context{Regime:r,Cue:c,Mode:mode}
  if a.Predict(ctx)!=b.Predict(ctx){return false}
 }}}
 return reflect.DeepEqual(a.Counts,b.Counts)
}
func f8ExactModel(seed uint32,probes []F5Probe,family string,phase int)(*f6Repair,error){
 if !f5ValidSeed(seed)||len(probes)!=F7FirstProbeCount&&len(probes)!=F5ProbeBudget{
  return nil,errF8
 }
 observed,err:=f7ObservedTransitions(probes)
 if err!=nil{return nil,errF8}
 m:=&f6Repair{Family:family,Phase:phase}
 if _,err:=f6Source(family,phase);err!=nil{return nil,errF8}
 if err:=f2teach([]f2Observer{m},f2training(seed));err!=nil{return nil,errF8}
 if err:=f2teach([]f2Observer{m},observed);err!=nil{return nil,errF8}
 return m,nil
}
func f8OneStep(arm F5ArmResult,from F7Generation,prior *F8Step)(F8Step,error){
 if !f5ValidSeed(arm.Seed)||len(arm.Probes)!=F5ProbeBudget||
  (from.Generation!=1&&from.Generation!=2)||from.Seed!=arm.Seed||
  from.Policy!=arm.Policy||from.GenerationReceiptSHA256!=f7Receipt(from)||
  (from.Generation==1&&prior!=nil)||(from.Generation==2&&prior==nil)||
  len(from.Candidates)!=F6Families||from.ObservedProbes!=from.Generation*F7FirstProbeCount{
  return F8Step{},errF8
 }
 source,err:=f6Source(from.SelectedFamily,from.SelectedPhase)
 if err!=nil||f3Hash([]byte(source))!=from.SelectedSourceSHA256{return F8Step{},errF8}
 count:=from.Generation*F7FirstProbeCount
 step:=F8Step{Generation:from.Generation,Seed:arm.Seed,Policy:arm.Policy,
  F7GenerationReceiptSHA256:from.GenerationReceiptSHA256,
  SelectedFamily:from.SelectedFamily,SelectedPhase:from.SelectedPhase,
  SelectedSourceSHA256:from.SelectedSourceSHA256,
  SelectedTrainingCorrect:from.SelectedTrainingCorrect,
  OriginalTrainObservationCount:F2TrainCount,
  NewlyAppliedObservations:F7FirstProbeCount,
  TotalObservedEvidence:F2TrainCount+count,
  SelectedDevelopmentClassification:from.DevelopmentClassification}
 for i,c:=range from.Candidates{
  if c.SourceSHA256!=f3Hash([]byte(c.GeneratedGoSource))||c.TrainingTotal!=count{
   return F8Step{},errF8
  }
  step.GeneratedCandidateSources[i]=c.SourceSHA256
 }
 var model *f6Repair
 if prior==nil{
  step.PreviousStepSHA256=from.ParentGenerationReceiptSHA256
  model,err=f8ExactModel(arm.Seed,arm.Probes[:F7FirstProbeCount],from.SelectedFamily,from.SelectedPhase)
  if err!=nil{return F8Step{},errF8}
 }else{
  if prior.Generation!=1||prior.Seed!=arm.Seed||prior.Policy!=arm.Policy||
   prior.RecordSHA256!=f8StepDigest(*prior)||
   prior.SnapshotSHA256!=f3Hash(prior.SnapshotBytes)||
   prior.TotalObservedEvidence!=F2TrainCount+F7FirstProbeCount||
   from.ParentGenerationReceiptSHA256!=prior.F7GenerationReceiptSHA256{
   return F8Step{},errF8
  }
  step.PreviousStepSHA256=prior.RecordSHA256
  step.PreviouslyLearnedObservations=prior.TotalObservedEvidence
  model=&f6Repair{Family:from.SelectedFamily,Phase:from.SelectedPhase}
  if err:=model.Load(prior.SnapshotBytes);err!=nil{return F8Step{},errF8}
  // Never reapply G1 or initial training; counts are in the restored snapshot.
  fresh,err:=f7ObservedTransitions(arm.Probes)
  if err!=nil{return F8Step{},errF8}
  if err:=f2teach([]f2Observer{model},fresh[F7FirstProbeCount:]);err!=nil{
   return F8Step{},errF8
  }
 }
 full,err:=f8ExactModel(arm.Seed,arm.Probes[:count],from.SelectedFamily,from.SelectedPhase)
 if err!=nil||!f8Matches(model,full){return F8Step{},errF8}
 step.ExactFullReplayMatches=true
 snapshot,err:=model.Snapshot()
 if err!=nil||len(snapshot)<10||len(snapshot)>4096{return F8Step{},errF8}
 step.SnapshotBytes=append([]byte(nil),snapshot...)
 step.SnapshotSHA256=f3Hash(snapshot)
 step.PredictionSHA256=f8Predictions(model)
 cold:=&f6Repair{Family:step.SelectedFamily,Phase:step.SelectedPhase}
 if err:=cold.Load(step.SnapshotBytes);err!=nil||!f8Matches(cold,model){return F8Step{},errF8}
 step.ColdStateReadbackMatches=true
 if from.ColdStateByteCount!=len(snapshot)||from.SelectedSourceSHA256!=step.SelectedSourceSHA256||
  from.Generation==2&&step.PreviouslyLearnedObservations!=F2TrainCount+F7FirstProbeCount{
  return F8Step{},errF8
 }
 step.RecordSHA256=f8StepDigest(step)
 return step,nil
}
// F8Development does not store or dispatch. The frozen F7 source supplies
// every input and all negative results; only exact old TRAIN data is replayed.
func F8Development()(F8Checkpoint,error){
 f7,err:=F7Development()
 if err!=nil||F7ValidatePreview(f7)!=nil||len(f7.Arms)!=6||
  !f7.DevelopmentOnly||f7.ScientificAccepted||f7.OwnerActivation||
  f7.DispatchAuthorized||f7.NewExperimentObservations!=0{
  return F8Checkpoint{},errF8
 }
 f5,err:=F5Development()
 if err!=nil||F5ValidatePreview(f5)!=nil||len(f5.Arms)!=len(f7.Arms){
  return F8Checkpoint{},errF8
 }
 out:=F8Checkpoint{Schema:F8Schema,
  F7ReportSHA256:f8Digest("FORGE-EUREKA-F7-REPORT-V1\n",f7),
  F5SourceSHA256:f7.F5SourceSHA256,TrainingSeeds:f7.TrainingSeeds,Policies:f7.Policies,
  Arms:make([]F8Arm,0,6),DevelopmentOnly:true}
 for i,arm:=range f7.Arms{
  old:=f5.Arms[i]
  if arm.Seed!=old.Seed||arm.Policy!=old.Policy||
   arm.Seed!=f7.TrainingSeeds[i/3]||arm.Policy!=f7.Policies[i%3]||
   arm.F5FeedbackSHA256!=f6FeedbackSHA(old,f5){return F8Checkpoint{},errF8}
  g1,err:=f8OneStep(old,arm.Generations[0],nil)
  if err!=nil{return F8Checkpoint{},errF8}
  g2,err:=f8OneStep(old,arm.Generations[1],&g1)
  if err!=nil{return F8Checkpoint{},errF8}
  out.Arms=append(out.Arms,F8Arm{Seed:arm.Seed,Policy:arm.Policy,
   F5FeedbackSHA256:arm.F5FeedbackSHA256,
   Steps:[F7Generations]F8Step{g1,g2}})
  out.TotalSteps+=2
 }
 if out.TotalSteps!=12{return F8Checkpoint{},errF8}
 out.CheckpointSHA256=f8CheckpointDigest(out)
 return out,nil
}
func F8Validate(x F8Checkpoint)error{
 if x.Schema!=F8Schema||x.CheckpointSHA256!=f8CheckpointDigest(x)||
  !x.DevelopmentOnly||x.GeneratedSourceExecuted||x.ScientificAccepted||
  x.IndependentFirstUseConsumed||x.RSIProven||x.OwnerActivation||
  x.DispatchAuthorized||x.NewGeneratedObservations!=0||
  x.AgentCalls!=0||x.PaidAPICalls!=0{return errF8}
 exact,err:=F8Development()
 if err!=nil||!reflect.DeepEqual(x,exact){return errF8}
 return nil
}
// F8Export yields portable bytes, *not* a custody-certified artifact or
// production write. Approved storage/integrity owner remains independent.
func F8Export(x F8Checkpoint)([]byte,string,error){
 if F8Validate(x)!=nil{return nil,"",errF8}
 b,err:=json.Marshal(x)
 if err!=nil||len(b)==0||len(b)>F8MaxBytes{return nil,"",errF8}
 b=append(b,'\n')
 return b,f3Hash(b),nil
}
// Caller supplies separately anchored expected *artifact* digest: comparing a
// locally recomputed hash alone cannot catch deletion of a valid checkpoint.
func F8Import(raw []byte,expectedArtifactSHA256 string)(F8Checkpoint,error){
 if len(raw)<16||len(raw)>F8MaxBytes||len(expectedArtifactSHA256)!=64||
  f3Hash(raw)!=expectedArtifactSHA256{return F8Checkpoint{},errF8}
 var x F8Checkpoint
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&x);err!=nil||d.Decode(new(any))!=io.EOF{return F8Checkpoint{},errF8}
 canonical,err:=json.Marshal(x)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n'))||F8Validate(x)!=nil{
  return F8Checkpoint{},errF8
 }
 return x,nil
}
// F8Restore is read-only, cold and exact-source; it never runs new experiments.
func F8Restore(x F8Checkpoint,seed uint32,policy string,generation int,expectedStepSHA256 string)(*f6Repair,error){
 if F8Validate(x)!=nil||!f5ValidSeed(seed)||generation<1||generation>2||
  len(expectedStepSHA256)!=64{return nil,errF8}
 for _,arm:=range x.Arms{
  if arm.Seed!=seed||arm.Policy!=policy{continue}
  row:=arm.Steps[generation-1]
  if row.RecordSHA256!=expectedStepSHA256||row.RecordSHA256!=f8StepDigest(row)||
   row.SnapshotSHA256!=f3Hash(row.SnapshotBytes)||
   row.SelectedSourceSHA256==""{return nil,errF8}
  source,err:=f6Source(row.SelectedFamily,row.SelectedPhase)
  if err!=nil||f3Hash([]byte(source))!=row.SelectedSourceSHA256{return nil,errF8}
  restored:=&f6Repair{Family:row.SelectedFamily,Phase:row.SelectedPhase}
  if err:=restored.Load(row.SnapshotBytes);err!=nil||
   f8Predictions(restored)!=row.PredictionSHA256{return nil,errF8}
  return restored,nil
 }
 return nil,errF8
}
