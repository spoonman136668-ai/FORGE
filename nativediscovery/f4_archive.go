// F4 constructs a TRAIN-only, nonexecuting research archive for the existing
// F3 compiled mechanisms. It neither invents source nor accesses heldout data.
package nativediscovery

import (
 "errors"
 "reflect"
 "sort"
)

const F4Schema = "forge.native-discovery.training-stepping-stones.v1"
func f4TrainingSeeds() [2]uint32{return [2]uint32{17,31}}
var errF4 = errors.New("FORGE_EUREKA_F4_TRAINING_ARCHIVE_INVALID")

type F4ArchivedCandidate struct {
 CandidateID string
 GeneratedType string
 StructuralSourceSHA256 string
 TrainingBehaviorSHA256 string
 DisagreementBits int
 DuplicateBehaviorOf string
 TrainingTrials [2]F3Trial
 MeanGainOverStrongestPP float64
 TrainingClassification string
}

type F4Preview struct {
 Schema string
 ParentGeneratedSourceSHA256 string
 NativeGeneratorFrozenSHA256 string
 SyntheticTrainingHistorySHA256 string
 TrainingSeeds [2]uint32
 Candidates []F4ArchivedCandidate
 NextProbeCandidateID string
 DuplicateBehaviorCount int
 DevelopmentOnly bool
 EvaluatedHeldout bool
 SealedFirstUse bool
 ScientificAccepted bool
 GeneralRSIProven bool
 OwnerActivation bool
 DispatchAuthorized bool
 AgentCalls int
 PaidAPICalls int
}

// f4Behavior uses only training and training-probe observations, including for
// the matched conventional comparator. Unobserved contexts are predictions,
// not holdout outcomes, and are never used to claim generalization accuracy.
func f4Behavior(id string)(string,int,error){
 trace:=make([]byte,0,32)
 novelty:=0
 for _,seed:=range f4TrainingSeeds() {
  model,err:=f3New(id)
  if err!=nil{return "",0,errF4}
  baseline:=&f2Tab{}
  arms:=[]f2Observer{model,baseline}
  training,probes:=f2training(seed),f2probes(seed)
  if len(training)!=F2TrainCount||len(probes)!=F2ProbeCount{return "",0,errF4}
  if err:=f2teach(arms,training);err!=nil{return "",0,err}
  if err:=f2teach(arms,probes);err!=nil{return "",0,err}
  for regime:=0;regime<2;regime++ {
   for cue:=0;cue<4;cue++ {
    for mode:=0;mode<2;mode++ {
     context:=f2Context{Regime:regime,Cue:cue,Mode:mode}
     prediction,control:=model.Predict(context),baseline.Predict(context)
     if (prediction!=1&&prediction!= -1)||(control!=1&&control!= -1){
      return "",0,errF4
     }
     if prediction==1{trace=append(trace,'1')}else{trace=append(trace,'0')}
     if prediction!=control{novelty++}
    }
   }
  }
 }
 if len(trace)!=32{return "",0,errF4}
 return f3Hash(trace),novelty,nil
}

func f4Build()(F4Preview,error){
 source,err:=F3Generate()
 if err!=nil{return F4Preview{},err}
 if len(source.Candidates)!=3||source.SourceSHA256!=f3Hash(source.Source)||
  len(source.SourceSHA256)!=64||len(source.GeneratorFrozenSHA256)!=64||
  len(source.TrainingHistorySHA256)!=64{return F4Preview{},errF4}
 candidates:=append([]F3SourceCandidate(nil),source.Candidates...)
 sort.Slice(candidates,func(i,j int)bool{return candidates[i].ID<candidates[j].ID})
 result:=F4Preview{
  Schema:F4Schema,ParentGeneratedSourceSHA256:source.SourceSHA256,
  NativeGeneratorFrozenSHA256:source.GeneratorFrozenSHA256,
  SyntheticTrainingHistorySHA256:source.TrainingHistorySHA256,
  TrainingSeeds:f4TrainingSeeds(),DevelopmentOnly:true,
 }
 signatures:=map[string]string{}
 sourceDigests:=map[string]bool{}
 for _,candidate:=range candidates {
  if candidate.ID==""||candidate.GeneratedType==""||
   len(candidate.StructuralSourceSHA256)!=64||
   sourceDigests[candidate.StructuralSourceSHA256]{
   return F4Preview{},errF4
  }
  sourceDigests[candidate.StructuralSourceSHA256]=true
  signature,novelty,err:=f4Behavior(candidate.ID)
  if err!=nil{return F4Preview{},err}
  row:=F4ArchivedCandidate{
   CandidateID:candidate.ID,GeneratedType:candidate.GeneratedType,
   StructuralSourceSHA256:candidate.StructuralSourceSHA256,
   TrainingBehaviorSHA256:signature,DisagreementBits:novelty,
  }
  if parent,exists:=signatures[signature];exists{
   row.DuplicateBehaviorOf=parent
   result.DuplicateBehaviorCount++
  }else{
   signatures[signature]=candidate.ID
  }
  for i,seed:=range f4TrainingSeeds() {
   trial,err:=f3Trial(candidate.ID,seed)
   if err!=nil{return F4Preview{},err}
   if trial.CandidateID!=candidate.ID||trial.Seed!=seed||
    trial.TrainExperiences!=F2TrainCount||trial.NewWorldProbes!=F2ProbeCount||
    trial.InterferenceExperiences!=16||trial.ScoredDecisions!=F2EvaluationCount||
    trial.NativeBaseAfterPct!=trial.NativeColdBasePct{return F4Preview{},errF4}
   row.TrainingTrials[i]=trial
   strongest:=trial.TabularChangedPct
   if trial.FactorizedChangedPct>strongest{strongest=trial.FactorizedChangedPct}
   if trial.ExistingF2NativeChangedPct>strongest{strongest=trial.ExistingF2NativeChangedPct}
   row.MeanGainOverStrongestPP+=(trial.NativeChangedPct-strongest)/float64(len(f4TrainingSeeds()))
  }
  switch {
  case row.MeanGainOverStrongestPP>0: row.TrainingClassification="TRAIN_AHEAD_UNVERIFIED"
  case row.MeanGainOverStrongestPP<0: row.TrainingClassification="TRAIN_BELOW_STRONGEST"
  default: row.TrainingClassification="TRAIN_TIED_STRONGEST"
  }
  result.Candidates=append(result.Candidates,row)
 }
 // A stepping stone is a proposal to investigate, NOT an accepted algorithm.
 // Only distinct training-view behaviors can compete for this suggestion.
 var winner *F4ArchivedCandidate
 for i:=range result.Candidates {
  candidate:=&result.Candidates[i]
  if candidate.DuplicateBehaviorOf!=""||candidate.DisagreementBits==0{continue}
  if winner==nil||candidate.DisagreementBits>winner.DisagreementBits||
   (candidate.DisagreementBits==winner.DisagreementBits&&
    candidate.MeanGainOverStrongestPP>winner.MeanGainOverStrongestPP){
   winner=candidate
  }
 }
 if winner!=nil{result.NextProbeCandidateID=winner.CandidateID}
 return result,nil
}

func F4Development()(F4Preview,error){return f4Build()}

// Recompute from frozen source and train-only observations. The preview has no
// authority and is not an externally authenticated evidence receipt.
func F4ValidatePreview(preview F4Preview)error{
 expected,err:=f4Build()
 if err!=nil||!reflect.DeepEqual(preview,expected){return errF4}
 return nil
}
