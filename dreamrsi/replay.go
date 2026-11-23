package dreamrsi

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/json"
 "errors"
 "math"
)

const (
 Linear="LINEAR"
 Uniform="DETERMINISTIC_UNIFORM_BASELINE"
)
type Policy struct{
 Lane string `json:"lane"`
 Kind string `json:"kind"`
 Weights [6]int `json:"weights"`
 Seed uint64 `json:"seed"`
 Generation int `json:"generation"`
 ParentSHA256 string `json:"parent_sha256,omitempty"`
}
func (p Policy)ID()string{raw,_:=json.Marshal(p);return hash(raw)}
func VerifyPolicy(p Policy)error{
 if p.Lane!="Wingless"&&p.Lane!="Yggdrasil"||p.Generation<0||p.Generation>12{
  return ErrFrozen
 }
 if p.ParentSHA256!=""&&!validHex(p.ParentSHA256,64){return ErrFrozen}
 if p.Kind==Uniform{
  if p.Seed==0||p.Weights!=[6]int{} {return ErrFrozen}
  return nil
 }
 if p.Kind!=Linear||p.Seed!=0{return ErrFrozen}
 for i,w:=range p.Weights{
  if i<4&&(w<0||w>8)||i>=4&&(w>0||w< -8){return ErrFrozen}
 }
 return nil
}
func BasePolicies(lane string,seed uint64)[]Policy{
 return []Policy{
  {Lane:lane,Kind:Linear,Weights:[6]int{4,2,1,0,-1,0}},
  {Lane:lane,Kind:Linear,Weights:[6]int{1,1,1,1,-1,-1}},
  {Lane:lane,Kind:Linear,Weights:[6]int{1,0,0,0,-1,0}},
  {Lane:lane,Kind:Uniform,Seed:seed},
 }
}
// Select uses ONLY the predecision features in the independently signed
// record. It NEVER reads its ChosenID or postdecision outcome. Counterfactual
// results are not looked up and must not be synthesized.
func Select(p Policy,d Decision)(string,error){
 if err:=VerifyPolicy(p);err!=nil{return "",err}
 if len(d.Options)==0{return "",ErrEvidence}
 best:=""
 var bestScore int64
 if p.Kind==Uniform{
  s:=sha256.Sum256([]byte(p.ID()+":"+d.ContextSHA256))
  n:=binary.BigEndian.Uint64(s[:8])
  return d.Options[n%uint64(len(d.Options))].ID,nil
 }
 for _,o:=range d.Options{
  f:=[6]int{o.Impact,o.Novelty,o.Robustness,o.Diversity,o.EstimatedCost,o.Risk}
  var score int64
  for i,v:=range f{score+=int64(p.Weights[i])*int64(v)}
  if best==""||score>bestScore||score==bestScore&&o.ID<best{
   best=o.ID;bestScore=score
  }
 }
 return best,nil
}
type Replay struct{
 Schema string `json:"schema"`
 PolicySHA256 string `json:"policy_sha256"`
 Lane string `json:"lane"`
 HistorySHA256 string `json:"history_sha256"`
 Records int `json:"records"`
 Matched int `json:"matched"`
 UnsupportedCounterfactuals int `json:"unsupported_counterfactuals"`
 Supported int `json:"supported"`
 Mixed int `json:"mixed"`
 Negative int `json:"negative"`
 Invalid int `json:"invalid"`
 Indeterminate int `json:"indeterminate"`
 ObservationalOnly bool `json:"observational_only"`
 RandomizationAuditRequired bool `json:"randomization_audit_required"`
 EstimatedQuality float64 `json:"estimated_quality"`
 EstimatedCompute float64 `json:"estimated_compute"`
 GainPerCompute float64 `json:"gain_per_compute"`
 CI95Low float64 `json:"ci95_low"`
 CI95High float64 `json:"ci95_high"`
 EffectiveSampleSize float64 `json:"effective_sample_size"`
 CanCompare bool `json:"can_compare"`
}
func reward(outcome string)float64{
 switch outcome{
 case "SUPPORTED":return 3
 case "MIXED":return 1
 default:return 0
 }
}
const ReplaySchema="forge.dreamrsi.contextual-replay.v1"
func Evaluate(p Policy,h Verified,minESS float64,minMatchBP int)(Replay,error){
 out:=Replay{}
 if err:=VerifyPolicy(p);err!=nil||p.Lane!=h.Lane||!validHex(h.HistorySHA256,64)||
  len(h.Decisions)==0||minESS<1||minMatchBP<0||minMatchBP>10000{
  return out,ErrEvidence
 }
 out=Replay{Schema:ReplaySchema,PolicySHA256:p.ID(),Lane:h.Lane,
  HistorySHA256:h.HistorySHA256,Records:len(h.Decisions)}
 vals:=make([]float64,0,len(h.Decisions))
 var weightSum,squareSum,qualitySum,costSum float64
 for _,d:=range h.Decisions{
  id,err:=Select(p,d);if err!=nil{return Replay{},err}
  switch d.Outcome{
  case "SUPPORTED":out.Supported++
  case "MIXED":out.Mixed++
  case "NEGATIVE":out.Negative++
  case "INVALID":out.Invalid++
  case "CONSUMED_INDETERMINATE":out.Indeterminate++
  default:return Replay{},ErrEvidence
  }
  if d.LoggingMode!=Randomized{out.ObservationalOnly=true}
  var v float64
  if id==d.ChosenID{
   out.Matched++
   if d.LoggingMode==Randomized{
    prob:=float64(d.LoggedActionProbabilityBP)/10000
    if prob<.1{return Replay{},ErrEvidence}
    importance:=1/prob
    weightSum+=importance;squareSum+=importance*importance
    v=importance*reward(d.Outcome)
    costSum+=importance*float64(d.ComputeUnits)
   }
  }else {
   // Zero is a contribution to an IPS *expectation* under audited
   // randomized logging, NOT a fabricated individual outcome.
   out.UnsupportedCounterfactuals++
  }
  vals=append(vals,v)
  qualitySum+=v
 }
 n:=float64(len(vals))
 if out.ObservationalOnly{
  // Observational replay cannot establish a counterfactual improvement.
  // We report concordance and actual outcome counts only.
  return out,nil
 }
 out.RandomizationAuditRequired=true // signed mode still needs independent audit
 out.EstimatedQuality=qualitySum/n
 out.EstimatedCompute=costSum/n
 if out.EstimatedCompute>0{out.GainPerCompute=out.EstimatedQuality/out.EstimatedCompute}
 if squareSum>0{out.EffectiveSampleSize=weightSum*weightSum/squareSum}
 if len(vals)>1{
  var total float64
  for _,v:=range vals {delta:=v-out.EstimatedQuality;total+=delta*delta}
  stderr:=math.Sqrt(total/(n-1)/n)
  out.CI95Low=out.EstimatedQuality-1.96*stderr
  out.CI95High=out.EstimatedQuality+1.96*stderr
  if out.CI95Low<0{out.CI95Low=0}
 }
 out.CanCompare=out.Matched*10000>=minMatchBP*out.Records&&
  out.EffectiveSampleSize>=minESS&&out.EstimatedCompute>0
 return out,nil
}
func SafeImprovement(candidate,baseline Replay)bool{
 return candidate.CanCompare&&baseline.CanCompare&&
  !candidate.ObservationalOnly&&!baseline.ObservationalOnly&&
  candidate.Lane==baseline.Lane&&candidate.HistorySHA256==baseline.HistorySHA256&&
  candidate.CI95Low>baseline.CI95High
}
func ValidateBaselines(results []Replay)error{
 if len(results)<4{return errors.New("FORGE_DREAMRSI_BASELINES_REQUIRED")}
 first:=results[0]
 for _,r:=range results{
  if r.Lane!=first.Lane||r.HistorySHA256!=first.HistorySHA256{return ErrEvidence}
 }
 return nil
}
