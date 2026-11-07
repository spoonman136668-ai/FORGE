// F2: procedural noisy action-consequence worlds with held-out regime changes.
// Development-only. No F139 owner, first-use, research dispatch or code promotion.
package nativediscovery

import (
 "encoding/json"
 "errors"
 "fmt"
 "math/bits"
 "time"
 "github.com/spoonman136668-ai/forge/noveltymechanisms"
)

const (
 F2Schema="forge.native-discovery.unfamiliar-world-development.v1"
 F2AcceptedBase="a8474c1f96b94e780d976aa39ab0fb099c2ce506"
 F2NoiseBP=2000
 F2BenefitPP=5.0
 F2RetentionLossPP=10.0
 F2ProbeCount=6
 F2TrainCount=48
 F2EvaluationCount=64
)
var F2Seeds=[4]uint32{17,31,59,83}
var errF2=errors.New("FORGE_F2_INVALID_PROCEDURAL_EVIDENCE")
type f2Context struct{Regime,Cue,Mode int}
type f2Transition struct{Context f2Context;Action,Effect int}
func f2Good(t f2Transition)bool{return t.Context.Regime>=0&&t.Context.Regime<2&&t.Context.Cue>=0&&t.Context.Cue<4&&t.Context.Mode>=0&&t.Context.Mode<2&&t.Action>=0&&t.Action<2&&(t.Effect==1||t.Effect== -1)}

// World generation is deterministic for reproducibility but its seed, latent
// factors and counterfactual test outcomes are never passed to a model.
func f2mix(v uint32)uint32{v^=v>>16;v*=0x7feb352d;v^=v>>15;v*=0x846ca68b;v^=v>>16;return v}
func f2sign(seed uint32,r,c,m int)int{
 cueBit:=bits.OnesCount32(f2mix(seed+uint32(r*211+c*19+101)))%2
 modeBit:=bits.OnesCount32(f2mix(seed+uint32(r*307+m*29+1009)))%2
 if cueBit^modeBit==0{return 1};return -1
}
func f2shock(seed uint32,r,c,m,index int)int{
 v:=f2mix(seed+uint32(r*601+c*127+m*337+index*10007+31337))%10000
 if v<F2NoiseBP{return -1};return 1
}
func f2make(seed uint32,r,c,m,action,index int)f2Transition{
 sign:=f2sign(seed,r,c,m);if action==1{sign= -sign}
 return f2Transition{f2Context{r,c,m},action,sign*f2shock(seed,r,c,m,index)}
}
func f2training(seed uint32)[]f2Transition{
 rows:=make([]f2Transition,0,F2TrainCount)
 for rep:=0;rep<3;rep++{for c:=0;c<4;c++{for m:=0;m<2;m++{for a:=0;a<2;a++{
  rows=append(rows,f2make(seed,0,c,m,a,rep*2+a))
 }}}}
 return rows
}
func f2probes(seed uint32)[]f2Transition{
 coordinates:=[6][2]int{{0,0},{1,0},{2,0},{3,0},{0,1},{2,1}}
 rows:=make([]f2Transition,0,F2ProbeCount)
 for i,v:=range coordinates{rows=append(rows,f2make(seed,1,v[0],v[1],i%2,50+i))}
 return rows
}
func f2interference(seed uint32)[]f2Transition{
 rows:=make([]f2Transition,0,16)
 for c:=0;c<4;c++{for m:=0;m<2;m++{for a:=0;a<2;a++{
  rows=append(rows,f2make(seed,1,c,m,a,70+c*4+m*2+a))
 }}}
 return rows
}

type f2Observer interface{Observe(f2Transition)error;Predict(f2Context)int}
type f2Counts [2][4][2][2]int
func(v *f2Counts)add(t f2Transition)error{
 if !f2Good(t){return errF2}
 effect:=t.Effect;if t.Action==1{effect= -effect}
 ix:=0;if effect==1{ix=1}
 if v[t.Context.Regime][t.Context.Cue][t.Context.Mode][ix]>=256{return errF2}
 v[t.Context.Regime][t.Context.Cue][t.Context.Mode][ix]++
 return nil
}
func f2major(v [2]int)(int,bool){
 if v[0]+v[1]==0{return 1,false};if v[0]>v[1]{return -1,true};return 1,true
}
func f2prior(c f2Counts,r,cue,mode int)int{
 if r<0||r>=2||cue<0||cue>=4||mode<0||mode>=2{return 1}
 v,ok:=f2major(c[r][cue][mode]);if !ok{return 1};return v
}
// Conventional empirical context-table baseline.
type f2Tab struct{Counts f2Counts}
func(m *f2Tab)Observe(t f2Transition)error{return m.Counts.add(t)}
func(m *f2Tab)Predict(c f2Context)int{return f2prior(m.Counts,c.Regime,c.Cue,c.Mode)}
// Strong conventional baseline: exact maximum-likelihood search over all 32
// factorized sign assignments, on all the same action/outcome observations.
type f2Factor struct{Counts f2Counts}
func(m *f2Factor)Observe(t f2Transition)error{return m.Counts.add(t)}
func(m *f2Factor)Predict(c f2Context)int{
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 best,bestScore:=0,-1<<30
 for hypothesis:=0;hypothesis<32;hypothesis++{
  match:=0
  for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
   sign:=1
   if ((hypothesis>>cue)&1)^(((hypothesis>>4)&1)*mode)==1{sign= -1}
   v:=m.Counts[c.Regime][cue][mode]
   if sign==1{match+=v[1]-v[0]}else{match+=v[0]-v[1]}
  }}
  if match>bestScore{bestScore=match;best=hypothesis}
 }
 if ((best>>c.Cue)&1)^(((best>>4)&1)*c.Mode)==1{return -1}
 return 1
}
// Native F95-backed relation memory. Isolated regime banks preserve original
// state during new-dynamics training. All inferred edges derive from examples.
type f2Native struct{
 Counts f2Counts `json:"counts"`
 graph [2]noveltymechanisms.Memory
}
func(m *f2Native)Observe(t f2Transition)error{return m.Counts.add(t)}
func(m *f2Native)Freeze()error{
 for r:=0;r<2;r++{
  seen:=0
  for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
   for _,v:=range m.Counts[r][cue][mode]{if v<0||v>256{return errF2};seen+=v}
  }}
  if seen==0{continue}
  cueSigns:=[4]int{1,1,1,1}
  for c:=0;c<4;c++{cueSigns[c],_=f2major(m.Counts[r][c][0])}
  flipVote:=0
  for c:=0;c<4;c++{
   a,okA:=f2major(m.Counts[r][c][0]);b,okB:=f2major(m.Counts[r][c][1])
   if okA&&okB{flipVote+=a*b}
  }
  flip:=1;if flipVote<0{flip= -1}
  edges:=make([]noveltymechanisms.Relation,0,8)
  for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
   s:=cueSigns[c];if mode==1{s*=flip}
   direct,ok:=f2major(m.Counts[r][c][mode]);if ok{s=direct}
   result:="positive";if s<0{result="negative"}
   edges=append(edges,noveltymechanisms.Relation{
    From:fmt.Sprintf("cue-%d-mode-%d",c,mode),Role:"effect",To:result})
  }}
  memory,err:=noveltymechanisms.Compile(edges);if err!=nil{return err}
  m.graph[r]=memory
 }
 return nil
}
func(m *f2Native)Predict(c f2Context)int{
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 result,err:=noveltymechanisms.Resolve(m.graph[c.Regime],
  fmt.Sprintf("cue-%d-mode-%d",c.Cue,c.Mode),[]string{"effect"})
 if err!=nil||!result.UniqueAnswer||len(result.Targets)!=1{return 1}
 if result.Targets[0]=="negative"{return -1};return 1
}
func(m *f2Native)Snapshot()([]byte,error){
 return json.Marshal(struct{
  Schema string `json:"schema"`
  Counts f2Counts `json:"counts"`
 }{F2Schema,m.Counts})
}
func f2restore(data []byte)(*f2Native,error){
 if len(data)==0||len(data)>4096{return nil,errF2}
 var blob struct{
  Schema string `json:"schema"`
  Counts f2Counts `json:"counts"`
 }
 if err:=json.Unmarshal(data,&blob);err!=nil{return nil,err}
 if blob.Schema!=F2Schema{return nil,errF2}
 count:=0
 for r:=0;r<2;r++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
  for _,v:=range blob.Counts[r][c][mode]{
   if v<0||v>256{return nil,errF2};count+=v
  }
 }}} 
 if count<1||count>256{return nil,errF2}
 m:=&f2Native{Counts:blob.Counts};if err:=m.Freeze();err!=nil{return nil,err}
 return m,nil
}
func f2teach(models []f2Observer,rows []f2Transition)error{
 for _,t:=range rows{for _,m:=range models{if err:=m.Observe(t);err!=nil{return err}}}
 return nil
}
func f2score(m f2Observer,seed uint32,r int)(int,int){
 success,total:=0,0
 for rep:=0;rep<8;rep++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
  context:=f2Context{r,c,mode}
  action:=0;if m.Predict(context)<0{action=1}
  result:=f2make(seed,r,c,mode,action,100+rep)
  if result.Effect==1{success++};total++
 }}}
 return success,total
}
func f2accuracy(a,b int)float64{if b==0{return 0};return 100*float64(a)/float64(b)}
type F2SeedResult struct{
 Seed uint32 `json:"seed"`
 TrainObservations int `json:"train_observations"`
 ChangedRegimeProbes int `json:"changed_regime_probes"`
 InterferenceObservations int `json:"interference_observations"`
 EvaluationDecisions int `json:"evaluation_decisions_per_arm"`
 NativeBeforeProbePct float64 `json:"native_before_probe_pct"`
 NativeChangedPct float64 `json:"native_changed_pct"`
 TabularChangedPct float64 `json:"tabular_changed_pct"`
 StrongFactorChangedPct float64 `json:"strong_factor_changed_pct"`
 NativeBaseBeforePct float64 `json:"native_base_before_pct"`
 NativeBaseAfterPct float64 `json:"native_base_after_pct"`
 NativeColdBasePct float64 `json:"native_cold_base_pct"`
 StrongBaseAfterPct float64 `json:"strong_base_after_pct"`
 SnapshotBytes int `json:"snapshot_bytes"`
 LearnerTrainWallNs [3]int64 `json:"learner_train_wall_ns"`
 MatchedInformationAndActions bool `json:"matched_information_and_actions"`
}
type F2Report struct{
 Schema string `json:"schema"`
 AcceptedBaseline string `json:"accepted_baseline"`
 Seeds [4]uint32 `json:"seeds"`
 NoiseBP int `json:"noise_bp"`
 FrozenRequiredGainPP float64 `json:"frozen_required_gain_pp"`
 FrozenMaxRetentionLossPP float64 `json:"frozen_max_retention_loss_pp"`
 Results []F2SeedResult `json:"results"`
 DevelopmentCriterionMet bool `json:"development_criterion_met"`
 DevelopmentStatus string `json:"development_status"`
 NonCeilingHoldout bool `json:"non_ceiling_holdout"`
 NativeSourceGenerated bool `json:"native_source_generated"`
 SyntheticData bool `json:"synthetic_data"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 OwnerWrites int `json:"owner_writes"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 ScientificAccepted bool `json:"scientific_accepted"`
 GeneralRSIProven bool `json:"general_rsi_proven"`
}
func F2Development()(F2Report,error){
 report:=F2Report{Schema:F2Schema,AcceptedBaseline:F2AcceptedBase,
  Seeds:F2Seeds,NoiseBP:F2NoiseBP,FrozenRequiredGainPP:F2BenefitPP,
  FrozenMaxRetentionLossPP:F2RetentionLossPP,SyntheticData:true,
  NonCeilingHoldout:true,Results:make([]F2SeedResult,0,len(F2Seeds)),
  DevelopmentStatus:"DEV_NO_GO"}
 successes:=0
 for _,seed:=range F2Seeds{
  native,table,strong:=&f2Native{},&f2Tab{},&f2Factor{}
  models:=[]f2Observer{native,table,strong}
  training:=f2training(seed)
  started:=time.Now()
  for _,x:=range training{if err:=native.Observe(x);err!=nil{return F2Report{},err}}
  nativeNS:=time.Since(started).Nanoseconds()
  started=time.Now()
  for _,x:=range training{if err:=table.Observe(x);err!=nil{return F2Report{},err}}
  tableNS:=time.Since(started).Nanoseconds()
  started=time.Now()
  for _,x:=range training{if err:=strong.Observe(x);err!=nil{return F2Report{},err}}
  strongNS:=time.Since(started).Nanoseconds()
  if err:=native.Freeze();err!=nil{return F2Report{},err}
  before,t:=f2score(native,seed,0)
  noProbe,_:=f2score(native,seed,1)
  probes:=f2probes(seed)
  if err:=f2teach(models,probes);err!=nil{return F2Report{},err}
  if err:=native.Freeze();err!=nil{return F2Report{},err}
  n,_:=f2score(native,seed,1)
  b,_:=f2score(table,seed,1)
  strongScore,_:=f2score(strong,seed,1)
  more:=f2interference(seed)
  if err:=f2teach(models,more);err!=nil{return F2Report{},err}
  if err:=native.Freeze();err!=nil{return F2Report{},err}
  after,_:=f2score(native,seed,0)
  strongAfter,_:=f2score(strong,seed,0)
  snapshot,err:=native.Snapshot();if err!=nil{return F2Report{},err}
  cold,err:=f2restore(snapshot);if err!=nil{return F2Report{},err}
  coldRetain,_:=f2score(cold,seed,0)
  if len(training)!=F2TrainCount||len(probes)!=F2ProbeCount||len(more)!=16||
   t!=F2EvaluationCount||after!=coldRetain{return F2Report{},errF2}
  row:=F2SeedResult{Seed:seed,TrainObservations:len(training),
   ChangedRegimeProbes:len(probes),InterferenceObservations:len(more),
   EvaluationDecisions:t,NativeBeforeProbePct:f2accuracy(noProbe,t),
   NativeChangedPct:f2accuracy(n,t),TabularChangedPct:f2accuracy(b,t),
   StrongFactorChangedPct:f2accuracy(strongScore,t),
   NativeBaseBeforePct:f2accuracy(before,t),NativeBaseAfterPct:f2accuracy(after,t),
   NativeColdBasePct:f2accuracy(coldRetain,t),StrongBaseAfterPct:f2accuracy(strongAfter,t),
   SnapshotBytes:len(snapshot),LearnerTrainWallNs:[3]int64{nativeNS,tableNS,strongNS},
   MatchedInformationAndActions:true}
  report.Results=append(report.Results,row)
  strongest:=row.StrongFactorChangedPct
  if row.TabularChangedPct>strongest{strongest=row.TabularChangedPct}
  if row.NativeChangedPct-strongest>=F2BenefitPP &&
   row.NativeChangedPct-row.NativeBeforeProbePct>=10 &&
   row.NativeBaseBeforePct-row.NativeBaseAfterPct<=F2RetentionLossPP &&
   row.NativeColdBasePct==row.NativeBaseAfterPct{successes++}
  maximum:=0
  for rep:=0;rep<8;rep++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
   if f2shock(seed,1,c,mode,100+rep)>0{maximum++}
  }}}
  if maximum==F2EvaluationCount{report.NonCeilingHoldout=false}
 }
 report.DevelopmentCriterionMet=successes>=3&&report.NonCeilingHoldout
 if report.DevelopmentCriterionMet{report.DevelopmentStatus="SYNTHETIC_PROVISIONAL_ONLY"}
 return report,nil
}
