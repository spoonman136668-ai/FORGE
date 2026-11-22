// Eureka F13: causal-law drift with a genuinely unannounced rule change.
// A synthetic DEV experiment only, isolated from original FORGE owner,
// first-use, scientific archive and production workers.
package nativediscovery

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "reflect"
 "sync"
)

const (
 F13Schema="forge.native-discovery.unannounced-drift.dev.v1"
 F13MemorySchema="forge.native-discovery.unannounced-drift-memory.dev.v1"
 F13Actions=60
 F13SwitchStep=48
 F13Delay=2
 F13MinGain=4
 F13MinAblationGain=8
 F13NO_GO="F13_DEV_NO_GO"
 F13Signal="F13_DEV_SIGNAL_UNVERIFIED"
)
var errF13=errors.New("FORGE_EUREKA_F13_DRIFT_OR_AUTHORITY_INVALID")
func f13Seeds()[2]uint32{return [2]uint32{17,31}}
func f13Policies()[2]string{return [2]string{"fixed","random"}}
func f13Rules(seed uint32)(int,int,error){
 switch seed{
 case 17:return 7,8,nil
 case 31:return 13,3,nil
 default:return 0,0,errF13
 }
}
func f13Action(seed uint32,policy string,step int)(int,error){
 if !f5ValidSeed(seed)||step<0||step>=F13Actions||
  policy!="fixed"&&policy!="random"{return 0,errF13}
 if step<F13SwitchStep{return int(f12Mix(seed^uint32(step+9)*0x94d049bb)&1),nil}
 if policy=="fixed"{return (step-F13SwitchStep)%2,nil}
 return int(f12Mix(seed^uint32(step+97)*0x165667b1)&1),nil
}
// Only this world-generation function accesses the hidden law. The learner
// receives neither law nor change-point; all input event Phase fields stay 0.
func f13Generate(seed uint32,policy string)([]f12Event,error){
 before,after,err:=f13Rules(seed)
 if err!=nil||policy!="fixed"&&policy!="random"{return nil,errF13}
 state:=int(f12Mix(seed^0x125ecafe)&3)
 initial:=state
 previous:=make([]int,0,F13Actions)
 events:=make([]f12Event,0,F13Actions)
 for step:=0;step<F13Actions;step++{
  action,err:=f13Action(seed,policy,step)
  if err!=nil{return nil,errF13}
  cue:=f12Cue(seed,step,0)
  revealed:= -1
  if step==1{revealed=initial}
  if step>=F13Delay{revealed=previous[step-F13Delay]}
  events=append(events,f12Event{
   Step:step,Phase:0,Cue:cue,Action:action,
   Sensor:state&1,DelayedState:revealed,
  })
  rule:=before
  if step>=F13SwitchStep{rule=after}
  state=f12Next(rule,state,0,cue,action)
  previous=append(previous,state)
 }
 return events,nil
}

type f13Credit struct{
 Step int `json:"step"`
 Before int `json:"before"`
 After int `json:"after"`
 Cue int `json:"cue"`
 Action int `json:"action"`
 WrongCue int `json:"wrong_cue"`
 WrongAction int `json:"wrong_action"`
}
type f13Notebook struct{
 Schema string `json:"schema"`
 Seen int `json:"seen"`
 LastDelayed int `json:"last_delayed"`
 Pending [2]f12Cause `json:"pending"`
 Credits []f13Credit `json:"credits"`
}
func f13New()*f13Notebook{
 return &f13Notebook{Schema:F13MemorySchema,LastDelayed:-1,Credits:make([]f13Credit,0,F13Actions)}
}
func(m *f13Notebook)Validate()error{
 if m==nil||m.Schema!=F13MemorySchema||m.Seen<0||m.Seen>F13Actions||
  m.LastDelayed< -1||m.LastDelayed>3||len(m.Credits)!=max(0,m.Seen-F13Delay)||
  m.Seen==0&&m.LastDelayed!= -1||m.Seen>=2&&m.LastDelayed<0{return errF13}
 for i,row:=range m.Credits{
  if row.Step!=i||row.Before<0||row.Before>3||
   row.After<0||row.After>3||row.Cue<0||row.Cue>=4||
   row.Action<0||row.Action>1||row.WrongCue<0||row.WrongCue>=4||
   row.WrongAction<0||row.WrongAction>1{return errF13}
 }
 if m.Seen>=2{
  for j,p:=range m.Pending{
   if p.Step!=m.Seen-2+j||p.Phase!=0||
    p.Cue<0||p.Cue>=4||p.Action<0||p.Action>1{return errF13}
  }
 }
 return nil
}
func(m *f13Notebook)Observe(e f12Event)error{
 if m.Validate()!=nil||e.Step!=m.Seen||e.Step>=F13Actions||
  e.Phase!=0||e.Action<0||e.Action>1||e.Cue<0||e.Cue>=4||
  e.Sensor<0||e.Sensor>1||
  e.Step==0&&e.DelayedState!= -1||
  e.Step>=1&&(e.DelayedState<0||e.DelayedState>3){return errF13}
 if e.Step>=F13Delay{
  old:=m.Pending[0]
  wrong:=m.Pending[1]
  m.Credits=append(m.Credits,f13Credit{
   Step:old.Step,Before:m.LastDelayed,After:e.DelayedState,
   Cue:old.Cue,Action:old.Action,
   WrongCue:wrong.Cue,WrongAction:wrong.Action,
  })
 }
 m.Pending[0]=m.Pending[1]
 m.Pending[1]=f12Cause{Step:e.Step,Cue:e.Cue,Action:e.Action,Phase:0}
 if e.Step>=1{m.LastDelayed=e.DelayedState}
 m.Seen++
 return m.Validate()
}
func(m *f13Notebook)Snapshot()([]byte,error){
 if m.Validate()!=nil{return nil,errF13}
 b,err:=json.Marshal(m)
 if err!=nil||len(b)>32768{return nil,errF13}
 return b,nil
}
func f13Load(raw []byte,expected string)(*f13Notebook,error){
 if len(raw)<30||len(raw)>32768||len(expected)!=64||
  f3Hash(raw)!=expected{return nil,errF13}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 var v f13Notebook
 if dec.Decode(&v)!=nil||dec.Decode(new(any))!=io.EOF||
  v.Validate()!=nil{return nil,errF13}
 canonical,err:=json.Marshal(&v)
 if err!=nil||!bytes.Equal(canonical,raw){return nil,errF13}
 return &v,nil
}
func f13Match(rule int,rec f13Credit,wrongLag bool)bool{
 cue,action:=rec.Cue,rec.Action
 if wrongLag{cue,action=rec.WrongCue,rec.WrongAction}
 return f12Next(rule,rec.Before,0,cue,action)==rec.After
}
func f13Best(records []f13Credit,wrongLag,noAction bool)(int,int){
 best,peak:=0,-1
 for rule:=0;rule<F12RuleCount;rule++{
  if noAction&&rule&1!=0{continue}
  hits:=0
  for _,rec:=range records{if f13Match(rule,rec,wrongLag){hits++}}
  if hits>peak{best,peak=rule,hits}
 }
 return best,peak
}
func f13Recent(records []f13Credit,n int)[]f13Credit{
 if len(records)>n{return records[len(records)-n:]}
 return records
}
func f13Surprise(records []f13Credit)bool{
 if len(records)<6{return false}
 historical:=records[:len(records)-3]
 rule,_:=f13Best(historical,false,false)
 misses:=0
 for _,rec:=range records[len(records)-3:]{
  if !f13Match(rule,rec,false){misses++}
 }
 return misses>=2
}
func f13Posterior(records []f13Credit,last,current f12Event)(int,int,error){
 var hits [F12RuleCount]int
 maxHits:=0
 for rule:=0;rule<F12RuleCount;rule++{
  for _,rec:=range records{if f13Match(rule,rec,false){hits[rule]++}}
  if hits[rule]>maxHits{maxHits=hits[rule]}
 }
 var votes [4]int
 for rule:=0;rule<F12RuleCount;rule++{
  gap:=maxHits-hits[rule]
  if gap>8{continue}
  weight:=1
  for k:=0;k<8-gap;k++{weight*=3}
  state:=f12Next(rule,current.DelayedState,0,last.Cue,last.Action)
  state=f12Next(rule,state,0,current.Cue,current.Action)
  votes[state]+=weight
 }
 predicted,peak:=0,-1
 for i,v:=range votes{
  if v>peak{predicted,peak=i,v}
 }
 if peak<=0{return 0,0,errF13}
 // 16 hypotheses × number of credited transitions plus 32 rule
 // applications for two-step coherent predictions.
 return predicted,F12RuleCount*len(records)+2*F12RuleCount,nil
}
func f13Table(records []f13Credit,state,cue,action int)int{
 var n [4]int
 for _,rec:=range records{
  if rec.Before==state&&rec.Cue&1==cue&1&&rec.Action==action{n[rec.After]++}
 }
 best,count:=state,0
 for i,v:=range n{if v>count{best,count=i,v}}
 return best
}
func f13Predict(kind string,m *f13Notebook,last,current f12Event)(int,int,bool,error){
 if m.Validate()!=nil||current.Step!=last.Step+1||current.Step<2||
  current.DelayedState<0||current.DelayedState>3||
  current.Cue<0||current.Cue>=4||last.Cue<0||last.Cue>=4||
  current.Action<0||current.Action>1||last.Action<0||last.Action>1||
  current.Phase!=0||last.Phase!=0{return 0,0,false,errF13}
 records:=m.Credits
 alarm:=false
 if kind=="causal-drift"{
  alarm=f13Surprise(records)
  if alarm{records=f13Recent(records,8)}
  p,c,e:=f13Posterior(records,last,current)
  return p,c,alarm,e
 }
 if kind=="table"{
  mid:=f13Table(records,current.DelayedState,last.Cue,last.Action)
  return f13Table(records,mid,current.Cue,current.Action),2*len(records),false,nil
 }
 wrongLag,noAction:=false,false
 switch kind{
 case "full-mle":
 case "rolling8-mle":records=f13Recent(records,8)
 case "rolling16-mle":records=f13Recent(records,16)
 case "no-action":records=f13Recent(records,8);noAction=true
 case "wrong-lag":records=f13Recent(records,8);wrongLag=true
 default:return 0,0,false,errF13
 }
 rule,_:=f13Best(records,wrongLag,noAction)
 mid:=f12Next(rule,current.DelayedState,0,last.Cue,last.Action)
 return f12Next(rule,mid,0,current.Cue,current.Action),
  F12RuleCount*len(records)+2*F12RuleCount,false,nil
}
func f13Kinds()[7]string{
 return [7]string{"causal-drift","full-mle","rolling8-mle","rolling16-mle","table","no-action","wrong-lag"}
}
func f13Evaluation(seed uint32,episode int,changed bool)([]f12Event,[]int,error){
 before,after,err:=f13Rules(seed)
 if err!=nil||episode<0||episode>=8{return nil,nil,errF13}
 rule:=before
 if changed{rule=after}
 state:=int(f12Mix(seed^uint32(episode+1)*0x91a615ef^uint32(31+episode)*0x34b35a4d)&3)
 initial:=state
 history:=make([]int,0,10)
 events:=make([]f12Event,0,10)
 for step:=0;step<10;step++{
  cue:=f12Cue(seed,step+100,episode+1)
  action:=int(f12Mix(seed^uint32(step+121)*0xd119e3bb^uint32(episode+3)*0xf1357aea)&1)
  revealed:= -1
  if step==1{revealed=initial}
  if step>=2{revealed=history[step-2]}
  events=append(events,f12Event{
   Step:step,Phase:0,Cue:cue,Action:action,Sensor:state&1,DelayedState:revealed,
  })
  state=f12Next(rule,state,0,cue,action)
  history=append(history,state)
 }
 return events,history,nil
}
func f13Score(kind string,m *f13Notebook,seed uint32,changed bool)(int,int,error){
 correct,checks:=0,0
 for episode:=0;episode<8;episode++{
  events,after,err:=f13Evaluation(seed,episode,changed)
  if err!=nil{return 0,0,errF13}
  for step:=2;step<10;step++{
   guess,cost,_,err:=f13Predict(kind,m,events[step-1],events[step])
   if err!=nil{return 0,0,errF13}
   if guess==after[step]{correct++}
   checks+=cost
  }
 }
 if correct<0||correct>64{return 0,0,errF13}
 return correct,checks,nil
}
type F13Round struct{
 Generation int `json:"generation"`
 ActionsSeen int `json:"actions_seen"`
 CreditedConsequences int `json:"credited_consequences"`
 PendingConsequences int `json:"pending_consequences"`
 ColdStateMatches bool `json:"cold_state_matches"`
 SnapshotSHA256 string `json:"snapshot_sha256"`
 SurpriseAlarm bool `json:"surprise_alarm"`
 OriginalCorrect [7]int `json:"original_correct"`
 ChangedCorrect [7]int `json:"changed_correct"`
 StrongestMatchedCorrect int `json:"strongest_matched_correct"`
 AdvantageOverStrongest int `json:"advantage_over_strongest"`
 AdvantageOverNoAction int `json:"advantage_over_no_action"`
 AdvantageOverWrongLag int `json:"advantage_over_wrong_lag"`
 RuleWorkChecks int `json:"rule_work_checks"`
}
type F13Arm struct{
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 TraceSHA256 string `json:"trace_sha256"`
 Rounds [2]F13Round `json:"rounds"`
 RetainedOriginal bool `json:"retained_original"`
 PassesThreshold bool `json:"passes_threshold"`
}
type F13Report struct{
 Schema string `json:"schema"`
 F12SourceDigestSHA256 string `json:"f12_source_digest_sha256"`
 EarlierNegativePreserved bool `json:"earlier_negative_preserved"`
 Seeds [2]uint32 `json:"seeds"`
 Policies [2]string `json:"policies"`
 ChangeStep int `json:"change_step"`
 TotalActions int `json:"total_actions"`
 Delay int `json:"delay"`
 CandidateRules int `json:"candidate_rules"`
 ScoredDecisions int `json:"scored_decisions"`
 MinStrongGain int `json:"min_strong_gain"`
 MinAblationGain int `json:"min_ablation_gain"`
 Arms []F13Arm `json:"arms"`
 PassingArms int `json:"passing_arms"`
 TotalRuleWorkChecks int `json:"total_rule_work_checks"`
 Classification string `json:"classification"`
 DevelopmentOnly bool `json:"development_only"`
 ScientificAccepted bool `json:"scientific_accepted"`
 IndependentHoldoutConsumed bool `json:"independent_holdout_consumed"`
 FullProcessEfficiencyProven bool `json:"full_process_efficiency_proven"`
 OwnerEligible bool `json:"owner_eligible"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 LiveFORGEResearchChanged bool `json:"live_forge_research_changed"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 DigestSHA256 string `json:"digest_sha256"`
}
func f13Digest(x F13Report)string{
 x.DigestSHA256=""
 return f8Digest("FORGE-EUREKA-F13-CAUSAL-DRIFT-V1\n",x)
}
func f13Arm(seed uint32,policy string)(F13Arm,error){
 trace,err:=f13Generate(seed,policy)
 if err!=nil||len(trace)!=F13Actions{return F13Arm{},errF13}
 arm:=F13Arm{Seed:seed,Policy:policy,
  TraceSHA256:f8Digest("FORGE-EUREKA-F13-OBSERVATIONS-V1\n",trace)}
 m:=f13New()
 for g,cut:=range [2]int{54,60}{
  start:=0
  if g==1{start=54}
  for _,e:=range trace[start:cut]{
   if err:=m.Observe(e);err!=nil{return F13Arm{},errF13}
  }
  snapshot,err:=m.Snapshot()
  if err!=nil{return F13Arm{},errF13}
  sha:=f3Hash(snapshot)
  cold,err:=f13Load(snapshot,sha)
  if err!=nil||!reflect.DeepEqual(m,cold){return F13Arm{},errF13}
  fresh:=f13New()
  for _,e:=range trace[:cut]{
   if fresh.Observe(e)!=nil{return F13Arm{},errF13}
  }
  replay,err:=fresh.Snapshot()
  if err!=nil||!bytes.Equal(snapshot,replay){return F13Arm{},errF13}
  r:=F13Round{Generation:g+1,ActionsSeen:cut,CreditedConsequences:cut-2,
   PendingConsequences:2,ColdStateMatches:true,SnapshotSHA256:sha,
   SurpriseAlarm:f13Surprise(cold.Credits)}
  for i,kind:=range f13Kinds(){
   var cost int
   r.OriginalCorrect[i],cost,err=f13Score(kind,cold,seed,false)
   if err!=nil{return F13Arm{},errF13}
   r.RuleWorkChecks+=cost
   r.ChangedCorrect[i],cost,err=f13Score(kind,cold,seed,true)
   if err!=nil{return F13Arm{},errF13}
   r.RuleWorkChecks+=cost
  }
  r.StrongestMatchedCorrect=max(max(r.ChangedCorrect[1],r.ChangedCorrect[2]),
   max(r.ChangedCorrect[3],r.ChangedCorrect[4]))
  r.AdvantageOverStrongest=r.ChangedCorrect[0]-r.StrongestMatchedCorrect
  r.AdvantageOverNoAction=r.ChangedCorrect[0]-r.ChangedCorrect[5]
  r.AdvantageOverWrongLag=r.ChangedCorrect[0]-r.ChangedCorrect[6]
  arm.Rounds[g]=r
  m=cold
 }
 arm.RetainedOriginal=arm.Rounds[1].OriginalCorrect[0]>=arm.Rounds[0].OriginalCorrect[0]
 g2:=arm.Rounds[1]
 arm.PassesThreshold=arm.RetainedOriginal&&g2.ColdStateMatches&&
  g2.AdvantageOverStrongest>=F13MinGain&&
  g2.AdvantageOverNoAction>=F13MinAblationGain&&
  g2.AdvantageOverWrongLag>=F13MinAblationGain
 return arm,nil
}
func F13Development()(F13Report,error){
 previous,err:=F12Development()
 if err!=nil||F12Validate(previous)!=nil||previous.Classification!=F12NO_GO||
  previous.ScientificAccepted||previous.OwnerEligible||previous.DispatchAuthorized{
  return F13Report{},errF13
 }
 out:=F13Report{
  Schema:F13Schema,F12SourceDigestSHA256:previous.DigestSHA256,
  EarlierNegativePreserved:true,Seeds:f13Seeds(),Policies:f13Policies(),
  ChangeStep:F13SwitchStep,TotalActions:F13Actions,Delay:F13Delay,
  CandidateRules:F12RuleCount,ScoredDecisions:64,
  MinStrongGain:F13MinGain,MinAblationGain:F13MinAblationGain,
  Arms:make([]F13Arm,0,4),DevelopmentOnly:true,
 }
 for _,seed:=range out.Seeds{
  for _,policy:=range out.Policies{
   arm,err:=f13Arm(seed,policy)
   if err!=nil{return F13Report{},errF13}
   out.Arms=append(out.Arms,arm)
   for _,round:=range arm.Rounds{out.TotalRuleWorkChecks+=round.RuleWorkChecks}
   if arm.PassesThreshold{out.PassingArms++}
  }
 }
 if len(out.Arms)!=4{return F13Report{},errF13}
 out.Classification=F13NO_GO
 if out.PassingArms==4{out.Classification=F13Signal}
 out.DigestSHA256=f13Digest(out)
 return out,nil
}
// The expected source report is immutable for one exact compiled Go program.
// Cache only the expensive reference *inside* validation: no result is ever
// returned, edited or accepted from this cache; all negative cases still
// compare every field against the full frozen developmental computation.
// Cache identity is the compiled package's exact source, not an external
// unverified disk artifact or model/runner state.
var f13ValidatedReference struct {
 once sync.Once
 report F13Report
 err error
}
func F13Validate(out F13Report)error{
 if out.Schema!=F13Schema||out.DigestSHA256!=f13Digest(out)||
  !out.DevelopmentOnly||!out.EarlierNegativePreserved||
  out.ScientificAccepted||out.IndependentHoldoutConsumed||
  out.FullProcessEfficiencyProven||out.OwnerEligible||
  out.DispatchAuthorized||out.LiveFORGEResearchChanged||
  out.AgentCalls!=0||out.PaidAPICalls!=0{return errF13}
 f13ValidatedReference.once.Do(func(){
  f13ValidatedReference.report,f13ValidatedReference.err=F13Development()
 })
 if f13ValidatedReference.err!=nil||
  !reflect.DeepEqual(out,f13ValidatedReference.report){return errF13}
 return nil
}
