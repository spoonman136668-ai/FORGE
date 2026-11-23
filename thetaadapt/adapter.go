// Package thetaadapt implements a deterministic, non-executing, training-only
// bounded parameter proposal. Neither results nor input pins grant FSA authority.
package thetaadapt

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

const (
 FrozenSchema="forge.thetaadapt.frozen.v1"
 TrainingSchema="forge.thetaadapt.training.v1"
 ProposalSchema="forge.thetaadapt.proposal.v1"
 Genesis="0000000000000000000000000000000000000000000000000000000000000000"
)
var ErrUnqualified=errors.New("FORGE_THETAADAPT_FROZEN_TRAINING_UNQUALIFIED")

type Frozen struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 SourceSHA string `json:"source_sha"`
 TrainingSHA256 string `json:"training_sha256"`
 FeatureCount int `json:"feature_count"`
 InitialWeights []int64 `json:"initial_weights"`
 MaxAbsWeight int64 `json:"max_abs_weight"`
 LearningStep int64 `json:"learning_step"`
 MaxUpdates int `json:"max_updates"`
 MaxTrainingCompute int64 `json:"max_training_compute"`
}
type TrainingRecord struct {
 Sequence int `json:"sequence"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 Classification string `json:"classification"`
 TrainingOnly bool `json:"training_only"`
 Compute int64 `json:"compute"`
 Direction []int64 `json:"direction"`
}
type Training struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 Records []TrainingRecord `json:"records"`
}
type Proposal struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenSHA256 string `json:"frozen_sha256"`
 TrainingSHA256 string `json:"training_sha256"`
 InitialSHA256 string `json:"initial_sha256"`
 Weights []int64 `json:"weights"`
 UpdatesApplied int `json:"updates_applied"`
 RecordsPreserved int `json:"records_preserved"`
 NegativeCount int `json:"negative_count"`
 MixedCount int `json:"mixed_count"`
 InvalidCount int `json:"invalid_count"`
 IndeterminateCount int `json:"indeterminate_count"`
 ComputeSpent int64 `json:"compute_spent"`
 LineageHeadSHA256 string `json:"lineage_head_sha256"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 SealedHoldoutConsumed bool `json:"sealed_holdout_consumed"`
}
func hash(domain string,v any)string{
 data,_:=json.Marshal(v)
 sum:=sha256.Sum256(append([]byte(domain+"\n"),data...))
 return hex.EncodeToString(sum[:])
}
func FrozenDigest(f Frozen)string{return hash("FORGE-THETA-FROZEN-V1",f)}
func TrainingDigest(t Training)string{return hash("FORGE-THETA-TRAINING-V1",t)}
func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func absBound(x,cap int64)bool{return x>=-cap&&x<=cap}
func validClass(c string)bool{
 switch c{
 case "SUPPORTED","NEGATIVE","MIXED","INVALID","CONSUMED_INDETERMINATE":return true
 }
 return false
}
func validFrozen(f Frozen,pin string)bool{
 if f.Schema!=FrozenSchema||(f.Lane!="Wingless"&&f.Lane!="Yggdrasil")||f.Epoch==0||
 !hexLower(f.SourceSHA,40)||!hexLower(f.TrainingSHA256,64)||!hexLower(pin,64)||
 FrozenDigest(f)!=pin||f.FeatureCount<1||f.FeatureCount>16||
 len(f.InitialWeights)!=f.FeatureCount||f.MaxAbsWeight<1||f.MaxAbsWeight>10000||
 f.LearningStep<1||f.LearningStep>100||f.MaxUpdates<1||f.MaxUpdates>64||
 f.MaxTrainingCompute<1||f.MaxTrainingCompute>1000000{return false}
 for _,w:=range f.InitialWeights{if !absBound(w,f.MaxAbsWeight){return false}}
 return true
}
// Adapt only constructs a bounded advisory delta from independently pinned
// training material. Hash equality is NOT proof of external authentication.
// Invalid and indeterminate records are retained but cannot modify weights.
func Adapt(f Frozen,frozenPin string,h Training,trainingPin string)(Proposal,error){
 var zero Proposal
 if !validFrozen(f,frozenPin)||h.Schema!=TrainingSchema||h.Lane!=f.Lane||
 h.SourceSHA!=f.SourceSHA||!hexLower(trainingPin,64)||
 trainingPin!=f.TrainingSHA256||TrainingDigest(h)!=trainingPin||
 len(h.Records)==0||len(h.Records)>f.MaxUpdates{return zero,ErrUnqualified}
 weights:=append([]int64(nil),f.InitialWeights...)
 out:=Proposal{Schema:ProposalSchema,Lane:f.Lane,FrozenSHA256:frozenPin,
 TrainingSHA256:trainingPin,InitialSHA256:hash("FORGE-THETA-INITIAL-V1",weights),
 Weights:weights,LineageHeadSHA256:Genesis}
 seen:=make(map[string]bool,len(h.Records))
 for i,rec:=range h.Records{
  if rec.Sequence!=i+1||!rec.TrainingOnly||!hexLower(rec.EvidenceSHA256,64)||
  seen[rec.EvidenceSHA256]||!validClass(rec.Classification)||
  rec.Compute<1||rec.Compute>f.MaxTrainingCompute-out.ComputeSpent||
  len(rec.Direction)!=f.FeatureCount{return zero,ErrUnqualified}
  seen[rec.EvidenceSHA256]=true
  blocked:=rec.Classification=="INVALID"||rec.Classification=="CONSUMED_INDETERMINATE"
  for j,v:=range rec.Direction{
   if v< -1||v>1||(blocked&&v!=0){return zero,ErrUnqualified}
   weights[j]+=f.LearningStep*v
   if weights[j]>f.MaxAbsWeight{weights[j]=f.MaxAbsWeight}
   if weights[j]< -f.MaxAbsWeight{weights[j]= -f.MaxAbsWeight}
  }
  out.ComputeSpent+=rec.Compute
  switch rec.Classification{
  case "NEGATIVE":out.NegativeCount++
  case "MIXED":out.MixedCount++
  case "INVALID":out.InvalidCount++
  case "CONSUMED_INDETERMINATE":out.IndeterminateCount++
  }
  out.LineageHeadSHA256=hash("FORGE-THETA-STEP-V1",struct{
   Previous string `json:"previous"`
   Frozen string `json:"frozen"`
   Training string `json:"training"`
   Record TrainingRecord `json:"record"`
   Weights []int64 `json:"weights"`
  }{out.LineageHeadSHA256,frozenPin,trainingPin,rec,weights})
 }
 out.UpdatesApplied=len(h.Records)
 out.RecordsPreserved=len(h.Records)
 return out,nil
}
