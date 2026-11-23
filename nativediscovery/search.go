// F1 links the EXISTING FORGE GenEnv bounded native generator to the F0
// action-consequence assay and F95 relational readout. This is a source-only
// synthetic development adapter, not a source-code invention or science claim.
package nativediscovery

import (
 "encoding/json"
 "fmt"
 "sort"

 "github.com/spoonman136668-ai/forge/genenv"
)

const F1Schema="forge.native-discovery.generator-linked-development.v1"
const F1SourceSHA="5553250d2ebd013bc6ca017b6f0d6ea1ced82c37"
const F1MinGainPP=5.0
const F1MaxInterferenceLossPP=10.0

type F1Metric struct {
 CandidateID string `json:"candidate_id"`
 Seed int `json:"seed"`
 Prior [3]int64 `json:"prior"`
 NativeAccuracy float64 `json:"native_accuracy_pct"`
 ColdAccuracy float64 `json:"cold_accuracy_pct"`
 ReversedDynamicsAccuracy float64 `json:"reversed_dynamics_accuracy_pct"`
 PostInterferenceAccuracy float64 `json:"post_interference_accuracy_pct"`
 StrongestConventionalAccuracy float64 `json:"strongest_conventional_accuracy_pct"`
 LearnedObservations int `json:"learned_observations"`
 OriginalF95Relations int `json:"f95_relations"`
}
type F1Lane struct {
 SyntheticLaneLabel string `json:"synthetic_lane_label"`
 FrozenGeneratorSHA256 string `json:"frozen_generator_sha256"`
 SyntheticTrainingHistorySHA256 string `json:"synthetic_training_history_sha256"`
 GeneratorCandidates []genenv.Candidate `json:"generator_candidates"`
 TrainingMetrics []F1Metric `json:"training_metrics"`
 SelectedCandidateID string `json:"selected_candidate_id"`
 HoldoutMetrics []F1Metric `json:"holdout_metrics"`
 HeldoutCriterionMet bool `json:"heldout_criterion_met"`
}
type F1Report struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha"`
 Lanes []F1Lane `json:"lanes"`
 TrainingSeeds [2]int `json:"training_seeds"`
 HoldoutSeed int `json:"holdout_seed"`
 RequiredGainPP float64 `json:"required_gain_pp"`
 MaxInterferenceLossPP float64 `json:"max_interference_loss_pp"`
 DevelopmentStatus string `json:"development_status"`
 GenuineSourceGeneration bool `json:"genuine_source_generation"`
 AuthenticScience bool `json:"authentic_science"`
 F94IndependentSourceAudit bool `json:"f94_independent_source_audit"`
 ControllerWrites int `json:"controller_writes"`
 PaidAPICalls int `json:"paid_api_calls"`
 AgentCalls int `json:"agent_calls"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 ScientificAccepted bool `json:"scientific_accepted"`
 AcceptedRefMutations int `json:"accepted_ref_mutations"`
}

func f1Generator(lane string)(genenv.Frozen,genenv.History,string,string){
 history:=genenv.History{Schema:genenv.HistorySchema,Lane:lane,
  SourceSHA:F1SourceSHA,
  Records:[]genenv.Record{
   {Sequence:1,EvidenceSHA256:repeatHex("1"),TrainingOnly:true,Classification:"NEGATIVE",Vector:[]int64{1,1,2}},
   {Sequence:2,EvidenceSHA256:repeatHex("2"),TrainingOnly:true,Classification:"MIXED",Vector:[]int64{1,2,1}},
   {Sequence:3,EvidenceSHA256:repeatHex("3"),TrainingOnly:true,Classification:"INVALID",Vector:[]int64{2,1,1}},
  }}
 histSHA:=genenv.HistoryDigest(history)
 freeze:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:lane,
  SourceSHA:F1SourceSHA,Epoch:1,HistorySHA256:histSHA,
  Base:[]int64{2,2,2},MaxLevel:4,MaxCandidates:3,MaxOperations:3,
  Requests:[]genenv.Request{
   {ID:"prior-down",Changes:[]genenv.Change{{Index:0,Delta:1}}},
   {ID:"prior-hold",Changes:[]genenv.Change{{Index:1,Delta:1}}},
   {ID:"prior-up",Changes:[]genenv.Change{{Index:2,Delta:1}}},
  }}
 return freeze,history,genenv.FrozenDigest(freeze),histSHA
}
func repeatHex(c string)string{
 b:=make([]byte,64)
 for i:=range b{b[i]=c[0]}
 return string(b)
}

// A strictly typed, code-reviewed interpretation of GenEnv's [3] vector:
// only small priors on downward/neutral/upward observed effects. Every
// prediction traverses the original F95 representation through Assoc.Predict.
// The params cannot issue code, change source, select a task, or dispatch.
type f1Predictor struct{
 native *Assoc
 prior [3]int64
}
func(p f1Predictor)Predict(o Observation,a int)int{
 initial:=p.native.Predict(o,a)
 if a<0||a>2{return 0}
 counts,found:=p.native.Counts[key(o,a)]
 if !found{return initial}
 maxScore:=int64(-1)
 answer:=initial
 for i:=0;i<3;i++{
  score:=int64(counts[i])+p.prior[i]
  if score>maxScore{maxScore=score;answer=i-1}
 }
 return answer
}
func f1Score(candidate genenv.Candidate,seed int)(F1Metric,error){
 var empty F1Metric
 if len(candidate.Vector)!=3||candidate.Classification!="UNTESTED_PROPOSAL"{return empty,errInvalid}
 var prior [3]int64
 for i,x:=range candidate.Vector{
  if x<1||x>4{return empty,errInvalid}
  prior[i]=x
 }
 native:=newAssoc();object:=newTable(true);strong:=newTable(false)
 tape:=suite(seed,0,true,TrainRounds)
 for _,x:=range tape{
  if err:=native.Observe(x);err!=nil{return empty,err}
  if err:=object.Observe(x);err!=nil{return empty,err}
  if err:=strong.Observe(x);err!=nil{return empty,err}
 }
 if err:=native.Freeze();err!=nil{return empty,err}
 originalRelations:=len(native.Counts)
 model:=f1Predictor{native:native,prior:prior}
 got,total:=scored(model,seed,0)
 obj,_:=scored(object,seed,0)
 factor,_:=scored(strong,seed,0)
 snapshot,err:=native.Snapshot();if err!=nil{return empty,err}
 cold,err:=restoreAssoc(snapshot);if err!=nil{return empty,err}
 restored:=f1Predictor{native:cold,prior:prior}
 retained,_:=scored(restored,seed,0)
 reversed,_:=scored(restored,seed,1)
 for _,x:=range suite(seed,1,true,InterferenceRounds){
  if err:=cold.Observe(x);err!=nil{return empty,err}
 }
 if err:=cold.Freeze();err!=nil{return empty,err}
 after,_:=scored(restored,seed,0)
 if total!=36||retained!=got||len(tape)!=90{return empty,errInvalid}
 strongest:=obj
 if factor>strongest{strongest=factor}
 return F1Metric{
  CandidateID:candidate.ID,Seed:seed,Prior:prior,
  NativeAccuracy:pct(got,total),ColdAccuracy:pct(retained,total),
  ReversedDynamicsAccuracy:pct(reversed,total),
  PostInterferenceAccuracy:pct(after,total),
  StrongestConventionalAccuracy:pct(strongest,total),
  LearnedObservations:len(tape),OriginalF95Relations:originalRelations,
 },nil
}
func F1Development()(F1Report,error){
 report:=F1Report{Schema:F1Schema,SourceSHA:F1SourceSHA,TrainingSeeds:[2]int{11,23},
  HoldoutSeed:47,RequiredGainPP:F1MinGainPP,
  MaxInterferenceLossPP:F1MaxInterferenceLossPP,
  DevelopmentStatus:"DEV_NO_GO",
  Lanes:make([]F1Lane,0,2)}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  frozen,history,pin,histSHA:=f1Generator(lane)
  population,err:=genenv.Generate(frozen,pin,history,histSHA)
  if err!=nil{return F1Report{},fmt.Errorf("native generator %s: %w",lane,err)}
  if len(population.Candidates)!=3||population.OperationsUsed!=3||
   population.NegativeCount!=1||population.InvalidCount!=1||
   population.MixedCount!=1||population.ScientificAccepted||
   population.DispatchAuthorized||population.SealedHoldoutConsumed{
    return F1Report{},errInvalid
  }
  row:=F1Lane{SyntheticLaneLabel:lane,FrozenGeneratorSHA256:pin,
    SyntheticTrainingHistorySHA256:histSHA,
    GeneratorCandidates:population.Candidates,
    TrainingMetrics:make([]F1Metric,0,6),
    HoldoutMetrics:make([]F1Metric,0,3)}
  score:=map[string]float64{}
  seen:=map[string]bool{}
  for _,c:=range population.Candidates{
   if seen[c.ID]{return F1Report{},errInvalid}
   seen[c.ID]=true
   for _,seed:=range report.TrainingSeeds{
    m,err:=f1Score(c,seed);if err!=nil{return F1Report{},err}
    row.TrainingMetrics=append(row.TrainingMetrics,m)
    score[c.ID]+=m.NativeAccuracy-m.StrongestConventionalAccuracy
   }
  }
  // Candidate selection uses ONLY the two open training-development seeds.
  ids:=make([]string,0,len(population.Candidates))
  for _,c:=range population.Candidates{ids=append(ids,c.ID)}
  sort.Strings(ids)
  best:=ids[0]
  for _,candidateID:=range ids[1:]{
   if score[candidateID]>score[best]{best=candidateID}
  }
  row.SelectedCandidateID=best
  for _,c:=range population.Candidates{
   m,err:=f1Score(c,report.HoldoutSeed)
   if err!=nil{return F1Report{},err}
   // Preserve ALL results, even losing candidates, after selection was frozen.
   row.HoldoutMetrics=append(row.HoldoutMetrics,m)
   if c.ID==best{
    row.HeldoutCriterionMet=m.NativeAccuracy-m.StrongestConventionalAccuracy>=F1MinGainPP &&
     m.ColdAccuracy==m.NativeAccuracy &&
     m.NativeAccuracy-m.PostInterferenceAccuracy<=F1MaxInterferenceLossPP
   }
  }
  report.Lanes=append(report.Lanes,row)
 }
 // Scientific acceptance requires independent source, randomized actions,
 // sealed original outcomes and FSA; this fixed synthetic study has none.
 return report,nil
}
func(m F1Report)Canonical()([]byte,error){return json.Marshal(m)}
