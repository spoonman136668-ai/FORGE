package dreamrsi

import (
 "encoding/json"
 "errors"
 "fmt"
 "sort"
)

type PolicyRecord struct {
 Schema string `json:"schema"`
 Sequence int `json:"sequence"`
 PreviousSHA256 string `json:"previous_sha256"`
 Policy Policy `json:"policy"`
 PolicySHA256 string `json:"policy_sha256"`
 Train Replay `json:"train"`
 Validation Replay `json:"validation"`
 RecordSHA256 string `json:"record_sha256"`
}
const LineageGenesis="0000000000000000000000000000000000000000000000000000000000000000"
func RecordDigest(r PolicyRecord)string{
 r.RecordSHA256=""
 b,_:=json.Marshal(r)
 return hash(b)
}
func ValidateRecords(records []PolicyRecord, lane string)error{
 prev:=LineageGenesis
 seen:=map[string]bool{}
 for i,r:=range records{
  if r.Schema!=RecordSchema||r.Sequence!=i+1||r.PreviousSHA256!=prev||
   r.RecordSHA256!=RecordDigest(r)||r.PolicySHA256!=r.Policy.ID()||
   r.Policy.Lane!=lane||seen[r.PolicySHA256]||
   r.Train.PolicySHA256!=r.PolicySHA256||
   r.Validation.PolicySHA256!=r.PolicySHA256||
   r.Train.Lane!=lane||r.Validation.Lane!=lane||
   VerifyPolicy(r.Policy)!=nil{return ErrEvidence}
  seen[r.PolicySHA256]=true
  prev=r.RecordSHA256
 }
 return nil
}
func appendRecord(records []PolicyRecord,p Policy,train,validation Replay)[]PolicyRecord{
 prev:=LineageGenesis
 if len(records)>0{prev=records[len(records)-1].RecordSHA256}
 record:=PolicyRecord{Schema:RecordSchema,Sequence:len(records)+1,
  PreviousSHA256:prev,Policy:p,PolicySHA256:p.ID(),
  Train:train,Validation:validation}
 record.RecordSHA256=RecordDigest(record)
 return append(records,record)
}
type Optimization struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenSpecSHA256 string `json:"frozen_spec_sha256"`
 TrainingSHA256 string `json:"training_sha256"`
 ValidationSHA256 string `json:"validation_sha256"`
 Baselines []Replay `json:"baselines"`
 Records []PolicyRecord `json:"records"`
 LineageHeadSHA256 string `json:"lineage_head_sha256"`
 Selected Policy `json:"selected"`
 SelectedPolicySHA256 string `json:"selected_policy_sha256"`
 SelectedTraining Replay `json:"selected_training"`
 SelectedValidation Replay `json:"selected_validation"`
 EvaluationsUsed int `json:"evaluations_used"`
 DecisionReplaysUsed int `json:"decision_replays_used"`
 QualifiedForProspectiveTest bool `json:"qualified_for_prospective_test"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ImprovementEstablished bool `json:"improvement_established"`
}
const OptimizationSchema="forge.dreamrsi.optimization.v1"
type ranked struct{
 policy Policy
 train Replay
 validation Replay
}
func better(a,b ranked)bool{
 if a.validation.CanCompare!=b.validation.CanCompare{return a.validation.CanCompare}
 if a.validation.GainPerCompute!=b.validation.GainPerCompute{
  return a.validation.GainPerCompute>b.validation.GainPerCompute
 }
 if a.validation.CI95Low!=b.validation.CI95Low{return a.validation.CI95Low>b.validation.CI95Low}
 return a.policy.ID()<b.policy.ID()
}
func distance(a,b Policy)int{
 if a.Kind!=b.Kind{return 100}
 total:=0
 for i:=range a.Weights{
  d:=a.Weights[i]-b.Weights[i];if d<0{d= -d};total+=d
 }
 return total
}
func survivors(ranks []ranked,max int)[]ranked{
 sort.Slice(ranks,func(i,j int)bool{return better(ranks[i],ranks[j])})
 out:=make([]ranked,0,max)
 for _,r:=range ranks{
  if !r.validation.CanCompare{continue}
  distinct:=true
  for _,p:=range out{if distance(r.policy,p.policy)<2{distinct=false;break}}
  if distinct{out=append(out,r)}
  if len(out)==max{break}
 }
 return out
}
func mutate(parent Policy,seed uint64,generation,step int)Policy{
 // Content-addressed mutation: no wall clock or nondeterministic RNG.
 b,_:=json.Marshal(struct{ID string;Seed uint64;Generation,Step int}{
  parent.ID(),seed,generation,step,
 })
 sum:=hash(b)
 var n uint64
 for i:=0;i<12;i++{
  c:=sum[i];n*=16
  if c>='0'&&c<='9'{n+=uint64(c-'0')}else{n+=uint64(c-'a'+10)}
 }
 next:=parent
 next.Kind=Linear
 next.Seed=0
 next.Generation=generation
 next.ParentSHA256=parent.ID()
 i:=int(n%6)
 direction:=1
 if (n/6)%2==0{direction= -1}
 next.Weights[i]+=direction
 if i<4 {
  if next.Weights[i]<0{next.Weights[i]=0}
  if next.Weights[i]>8{next.Weights[i]=8}
 }else{
  if next.Weights[i]>0{next.Weights[i]=0}
  if next.Weights[i]< -8{next.Weights[i]= -8}
 }
 return next
}
func Optimize(train,validation Verified,spec FrozenSpec,specSHA string)(Optimization,error){
 var empty Optimization
 if err:=VerifySpec(spec,specSHA,train,validation);err!=nil{return empty,err}
 // Selection from deterministic/nonrandom historical traces would
 // optimize for coincidental agreement with the logged decisions.
 for _,h:=range []Verified{train,validation}{
  for _,d:=range h.Decisions{
   if d.LoggingMode!=Randomized{return empty,ErrUnsupported}
  }
 }
 result:=Optimization{Schema:OptimizationSchema,Lane:spec.Lane,
  FrozenSpecSHA256:specSHA,TrainingSHA256:train.HistorySHA256,
  ValidationSHA256:validation.HistorySHA256,LineageHeadSHA256:LineageGenesis}
 seen:=map[string]bool{}
 ranks:=[]ranked{}
 evaluate:=func(p Policy)(bool,error){
  if _,ok:=seen[p.ID()];ok{return false,nil}
  if result.EvaluationsUsed+2>spec.MaxEvaluations||
   result.DecisionReplaysUsed+len(train.Decisions)+len(validation.Decisions)>spec.MaxReplayDecisions{
   return false,nil
  }
  if err:=VerifyPolicy(p);err!=nil{return false,err}
  tr,err:=Evaluate(p,train,spec.MinEffectiveSampleSize,spec.MinMatchBP)
  if err!=nil{return false,err}
  va,err:=Evaluate(p,validation,spec.MinEffectiveSampleSize,spec.MinMatchBP)
  if err!=nil{return false,err}
  seen[p.ID()]=true
  result.Records=appendRecord(result.Records,p,tr,va)
  result.EvaluationsUsed+=2
  result.DecisionReplaysUsed+=len(train.Decisions)+len(validation.Decisions)
  ranks=append(ranks,ranked{p,tr,va})
  return true,nil
 }
 baselines:=BasePolicies(spec.Lane,spec.Seed)
 for _,p:=range baselines{
  ok,err:=evaluate(p)
  if err!=nil||!ok{return empty,fmt.Errorf("%w:baseline-budget",ErrFrozen)}
  result.Baselines=append(result.Baselines,result.Records[len(result.Records)-1].Validation)
 }
 if err:=ValidateBaselines(result.Baselines);err!=nil{return empty,err}
 champions:=survivors(append([]ranked(nil),ranks...),spec.Population)
 for gen:=1;gen<=spec.MaxGenerations;gen++{
  if len(champions)==0{break}
  for i:=0;i<spec.MutationsPerGeneration;i++{
   parent:=champions[i%len(champions)]
   if parent.policy.Kind!=Linear{continue}
   candidate:=mutate(parent.policy,spec.Seed,gen,i)
   used,err:=evaluate(candidate)
   if err!=nil{return empty,err}
   if !used&&result.EvaluationsUsed+2>spec.MaxEvaluations{break}
  }
  champions=survivors(append([]ranked(nil),ranks...),spec.Population)
 }
 if len(result.Records)==0{return empty,ErrFrozen}
 if err:=ValidateRecords(result.Records,spec.Lane);err!=nil{return empty,err}
 result.LineageHeadSHA256=result.Records[len(result.Records)-1].RecordSHA256
 if len(champions)>0{
  choice:=champions[0]
  result.Selected=choice.policy;result.SelectedPolicySHA256=choice.policy.ID()
  result.SelectedTraining=choice.train;result.SelectedValidation=choice.validation
  result.QualifiedForProspectiveTest=choice.validation.CanCompare
 }else{
  result.Selected=baselines[0];result.SelectedPolicySHA256=baselines[0].ID()
  result.SelectedTraining=result.Records[0].Train
  result.SelectedValidation=result.Records[0].Validation
 }
 // Never declare scientific gain on a model-selected validation set.
 // The independent *sealed* prospective holdout is a separate gate.
 return result,nil
}
func ValidateOptimization(o Optimization)error{
 if o.Schema!=OptimizationSchema||o.Lane!="Wingless"&&o.Lane!="Yggdrasil"||
  !validHex(o.FrozenSpecSHA256,64)||!validHex(o.TrainingSHA256,64)||
  !validHex(o.ValidationSHA256,64)||o.EvaluationsUsed!=2*len(o.Records)||
  len(o.Records)==0||len(o.Baselines)!=4||
  o.LineageHeadSHA256!=o.Records[len(o.Records)-1].RecordSHA256||
  o.SelectedPolicySHA256!=o.Selected.ID()||
  o.ScientificAccepted||o.DispatchAuthorized||o.ImprovementEstablished{
  return ErrFrozen
 }
 if err:=ValidateRecords(o.Records,o.Lane);err!=nil{return err}
 for _,r:=range o.Records{
  if r.Train.HistorySHA256!=o.TrainingSHA256||
   r.Validation.HistorySHA256!=o.ValidationSHA256{return ErrFrozen}
 }
 return nil
}
var _=errors.Is
