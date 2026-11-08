// Eureka F12: bounded hidden-state, delayed-consequence DEV only.
// The synthetic world's true rule is confined to f12Generate/f12Score; no
// learner, controller, F139 lane, archive writer or first-use uses it.
package nativediscovery

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "reflect"
)

const (
 F12Schema = "forge.native-discovery.hidden-delayed-causal-dev.v1"
 F12MemorySchema = "forge.native-discovery.hidden-delayed-memory-dev.v1"
 F12LearnActions = 48
 F12ProbeActions = 6
 F12Actions = F12LearnActions + F12ProbeActions
 F12Delay = 2
 F12RuleCount = 16
 F12MinimumStrongGain = 4
 F12MinimumAblationGain = 8
 F12DecisionCount = 64
 F12NO_GO = "F12_DEV_NO_GO"
 F12Signal = "F12_DEV_SIGNAL_UNVERIFIED"
)
var errF12 = errors.New("FORGE_EUREKA_F12_HIDDEN_CAUSAL_SCOPE_INVALID")

func f12Seeds() [2]uint32 {return [2]uint32{17,31}}
func f12Policies() [2]string {return [2]string{"fixed","random"}}
func f12SeedValid(seed uint32)bool{return seed==17||seed==31}

func f12Mix(v uint32)uint32{
 v+=0x9e3779b9
 v=(v^(v>>16))*0x85ebca6b
 v=(v^(v>>13))*0xc2b2ae35
 return v^(v>>16)
}
func f12TrueRule(seed uint32)(int,error){
 switch seed {
 case 17: return 7,nil  // action, cue, and world-phase effects
 case 31: return 13,nil // action, world-phase and bias effects
 default: return 0,errF12
 }
}
func f12Next(rule,h,phase,cue,action int)int{
 low:=(h>>1)&1
 if rule&1!=0 {low^=action}
 if rule&2!=0 {low^=cue&1}
 if rule&4!=0 {low^=phase}
 if rule&8!=0 {low^=1}
 return ((h&1)<<1)|low
}
type f12Event struct{
 Step int `json:"step"`
 Phase int `json:"phase"`
 Cue int `json:"cue"`
 Action int `json:"action"`
 Sensor int `json:"sensor"`
 DelayedState int `json:"delayed_state"`
}
func f12Action(seed uint32,policy string,step int)(int,error){
 if !f12SeedValid(seed)||step<0||step>=F12Actions{return 0,errF12}
 if step<F12LearnActions{
  return int(f12Mix(seed^uint32(step+9)*0x94d049bb)&1),nil
 }
 switch policy{
 case "fixed":return (step-F12LearnActions)%2,nil
 case "random":return int(f12Mix(seed^uint32(step+97)*0x165667b1)&1),nil
 default:return 0,errF12
 }
}
func f12Cue(seed uint32,step,episode int)int{
 return int(f12Mix(seed^uint32(step+1)*0xd8163841^uint32(episode+1)*0xa36d3a2b)&3)
}
func f12Generate(seed uint32,policy string)([]f12Event,error){
 rule,err:=f12TrueRule(seed)
 if err!=nil||policy!="fixed"&&policy!="random"{return nil,errF12}
 state:=int(f12Mix(seed^0x125ecafe)&3)
 initial:=state
 after:=make([]int,0,F12Actions)
 events:=make([]f12Event,0,F12Actions)
 for step:=0;step<F12Actions;step++{
  phase:=0
  if step>=F12LearnActions{phase=1}
  action,err:=f12Action(seed,policy,step)
  if err!=nil{return nil,errF12}
  cue:=f12Cue(seed,step,0)
  delayed:= -1
  if step==1{delayed=initial}
  if step>=2{delayed=after[step-F12Delay]}
  // Nothing about the future state is supplied before the action is fixed.
  events=append(events,f12Event{Step:step,Phase:phase,Cue:cue,
   Action:action,Sensor:state&1,DelayedState:delayed})
  state=f12Next(rule,state,phase,cue,action)
  after=append(after,state)
 }
 return events,nil
}
type f12Cause struct{
 Step int `json:"step"`
 Phase int `json:"phase"`
 Cue int `json:"cue"`
 Action int `json:"action"`
}
type f12Memory struct{
 Schema string `json:"schema"`
 Kind string `json:"kind"`
 Seen int `json:"seen"`
 Credited int `json:"credited"`
 Match [F12RuleCount]int `json:"match"`
 Table [2][4][2][2][4]int `json:"table"`
 Pending [F12Delay]f12Cause `json:"pending"`
 LastDelayed int `json:"last_delayed"`
}
func f12KindValid(k string)bool{
 return k=="causal"||k=="mle"||k=="table"||k=="no-action"||k=="wrong-lag"
}
func f12New(kind string)(*f12Memory,error){
 if !f12KindValid(kind){return nil,errF12}
 return &f12Memory{Schema:F12MemorySchema,Kind:kind,LastDelayed:-1},nil
}
func(m *f12Memory)Validate()error{
 if m==nil||m.Schema!=F12MemorySchema||!f12KindValid(m.Kind)||
  m.Seen<0||m.Seen>F12Actions||m.Credited!=max(0,m.Seen-F12Delay)||
  m.LastDelayed< -1||m.LastDelayed>3||
  m.Seen==0&&m.LastDelayed!= -1||
  m.Seen>=2&&m.LastDelayed<0{return errF12}
 counted:=0
 for phase:=0;phase<2;phase++{for h:=0;h<4;h++{for cue:=0;cue<2;cue++{
  for action:=0;action<2;action++{for next:=0;next<4;next++{
   n:=m.Table[phase][h][cue][action][next]
   if n<0||n>F12Actions{return errF12}
   counted+=n
  }}
 }}}
 if counted!=m.Credited{return errF12}
 for _,n:=range m.Match{if n<0||n>m.Credited{return errF12}}
 if m.Seen>=2{
  for i,cause:=range m.Pending{
   if cause.Step!=m.Seen-2+i||cause.Action<0||cause.Action>1||
    cause.Cue<0||cause.Cue>=4||cause.Phase<0||cause.Phase>1||
    cause.Phase!=(cause.Step/F12LearnActions){return errF12}
  }
 }
 return nil
}
func(m *f12Memory)Observe(e f12Event)error{
 if m.Validate()!=nil||e.Step!=m.Seen||e.Step<0||e.Step>=F12Actions||
  e.Phase!=e.Step/F12LearnActions||e.Cue<0||e.Cue>=4||
  e.Action<0||e.Action>1||e.Sensor<0||e.Sensor>1||
  e.Step==0&&e.DelayedState!= -1||
  e.Step>=1&&(e.DelayedState<0||e.DelayedState>3){return errF12}
 if e.Step>=F12Delay{
  before,after:=m.LastDelayed,e.DelayedState
  cause:=m.Pending[0]
  if m.Kind=="wrong-lag"{cause=m.Pending[1]}
  if before<0||before>3||after<0||after>3{return errF12}
  m.Table[cause.Phase][before][cause.Cue&1][cause.Action][after]++
  for rule:=0;rule<F12RuleCount;rule++{
   if f12Next(rule,before,cause.Phase,cause.Cue,cause.Action)==after{
    m.Match[rule]++
   }
  }
  m.Credited++
 }
 m.Pending[0]=m.Pending[1]
 m.Pending[1]=f12Cause{Step:e.Step,Phase:e.Phase,Cue:e.Cue,Action:e.Action}
 if e.Step>=1{m.LastDelayed=e.DelayedState}
 m.Seen++
 return m.Validate()
}
func(m *f12Memory)Snapshot()([]byte,error){
 if m.Validate()!=nil{return nil,errF12}
 b,err:=json.Marshal(m)
 if err!=nil||len(b)>16384{return nil,errF12}
 return b,nil
}
func f12Load(raw []byte,expectedSHA string)(*f12Memory,error){
 if len(raw)<20||len(raw)>16384||len(expectedSHA)!=64||
  f3Hash(raw)!=expectedSHA{return nil,errF12}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 var v f12Memory
 if d.Decode(&v)!=nil||d.Decode(new(any))!=io.EOF||v.Validate()!=nil{return nil,errF12}
 canonical,err:=json.Marshal(v)
 if err!=nil||!bytes.Equal(canonical,raw){return nil,errF12}
 return &v,nil
}
// Each rule proposes a *single coherent two-action trajectory*. A weighted
// vote between the four terminal hidden states never reads a future label.
func(m *f12Memory)Predict(last f12Event,current f12Event)(int,int,error){
 if m.Validate()!=nil||current.Step!=last.Step+1||current.Step<2||
  current.DelayedState<0||current.DelayedState>3||
  last.Cue<0||last.Cue>=4||last.Action<0||last.Action>1||
  current.Cue<0||current.Cue>=4||current.Action<0||current.Action>1||
  last.Phase<0||last.Phase>1||current.Phase<0||current.Phase>1{
  return 0,0,errF12
 }
 start:=current.DelayedState
 if m.Kind=="table"{
  first:=m.tablePredict(start,last.Phase,last.Cue,last.Action)
  second:=m.tablePredict(first,current.Phase,current.Cue,current.Action)
  return second,2, nil
 }
 maxMatches:= -1
 bestRule:=0
 for rule:=0;rule<F12RuleCount;rule++{
  if m.Kind=="no-action"&&rule&1!=0{continue}
  n:=m.Match[rule]
  if n>maxMatches{maxMatches=n;bestRule=rule}
 }
 if m.Kind=="mle"{
  return f12Next(bestRule,
   f12Next(bestRule,start,last.Phase,last.Cue,last.Action),
   current.Phase,current.Cue,current.Action),2*F12RuleCount,nil
 }
 var votes [4]int
 for rule:=0;rule<F12RuleCount;rule++{
  if m.Kind=="no-action"&&rule&1!=0{continue}
  delta:=maxMatches-m.Match[rule]
  if delta>8{continue}
  weight:=1
  for pow:=0;pow<8-delta;pow++{weight*=3}
  state:=f12Next(rule,start,last.Phase,last.Cue,last.Action)
  state=f12Next(rule,state,current.Phase,current.Cue,current.Action)
  votes[state]+=weight
 }
 predicted,bestVote:=0,-1
 for state,weight:=range votes{if weight>bestVote{predicted,bestVote=state,weight}}
 if bestVote<=0{return 0,0,errF12}
 return predicted,2*F12RuleCount,nil
}
func(m *f12Memory)tablePredict(state,phase,cue,action int)int{
 counts:=m.Table[phase][state][cue&1][action]
 best,peak:=0,-1
 for next,n:=range counts{if n>peak{best,peak=next,n}}
 if peak==0 {
  // Explicit frozen ignorant prior: state remains unchanged if no directly
  // trained transition; never consult the world law as a fallback.
  return state
 }
 return best
}
func f12Evaluation(seed uint32,episode,phase int)([]f12Event,[]int,error){
 rule,err:=f12TrueRule(seed)
 if err!=nil||episode<0||episode>=8||phase<0||phase>1{return nil,nil,errF12}
 state:=int(f12Mix(seed^uint32(episode+1)*0x91a615ef^uint32(phase+1)*0x34b35a4d)&3)
 initial:=state
 after:=make([]int,0,10)
 events:=make([]f12Event,0,10)
 for t:=0;t<10;t++{
  cue:=f12Cue(seed,t+100,episode+1)
  action:=int(f12Mix(seed^uint32(t+121)*0xd119e3bb^uint32(episode+3)*0xf1357aea)&1)
  delayed:= -1
  if t==1{delayed=initial}
  if t>=2{delayed=after[t-2]}
  events=append(events,f12Event{Step:t,Phase:phase,Cue:cue,Action:action,
   Sensor:state&1,DelayedState:delayed})
  state=f12Next(rule,state,phase,cue,action)
  after=append(after,state)
 }
 return events,after,nil
}
func f12Score(m *f12Memory,seed uint32,phase int)(int,int,error){
 good,calls:=0,0
 for episode:=0;episode<8;episode++{
  events,after,err:=f12Evaluation(seed,episode,phase)
  if err!=nil{return 0,0,errF12}
  for t:=2;t<10;t++{
   result,cost,err:=m.Predict(events[t-1],events[t])
   if err!=nil{return 0,0,errF12}
   if result==after[t]{good++}
   calls+=cost
  }
 }
 if good<0||good>F12DecisionCount{return 0,0,errF12}
 return good,calls,nil
}
type F12Round struct{
 Generation int `json:"generation"`
 ActionCount int `json:"action_count"`
 CreditedDelayedConsequences int `json:"credited_delayed_consequences"`
 UnresolvedPendingActions int `json:"unresolved_pending_actions"`
 CausalCorrect int `json:"causal_correct_of_64"`
 MLECorrect int `json:"mle_correct_of_64"`
 TableCorrect int `json:"table_correct_of_64"`
 NoActionCorrect int `json:"no_action_correct_of_64"`
 WrongLagCorrect int `json:"wrong_lag_correct_of_64"`
 StrongestCorrect int `json:"strongest_correct_of_64"`
 AdvantageOverStrongest int `json:"advantage_over_strongest"`
 AdvantageOverNoAction int `json:"advantage_over_no_action"`
 AdvantageOverWrongLag int `json:"advantage_over_wrong_lag"`
 OriginalCorrect [5]int `json:"original_correct_of_64"`
 ChangedCorrect [5]int `json:"changed_correct_of_64"`
 ColdStateMatches bool `json:"cold_state_matches"`
 SnapshotSHA256 [5]string `json:"snapshot_sha256"`
 PredictionRuleChecks int `json:"prediction_rule_checks"`
}
type F12Arm struct{
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 Actions []f12Event `json:"actions"`
 HistorySHA256 string `json:"history_sha256"`
 Rounds [2]F12Round `json:"rounds"`
 MeetsFrozenThreshold bool `json:"meets_frozen_threshold"`
 OriginalWorldRetained bool `json:"original_world_retained"`
}
type F12Report struct{
 Schema string `json:"schema"`
 ParentF11DigestSHA256 string `json:"parent_f11_digest_sha256"`
 F10AndF11NegativePreserved bool `json:"f10_and_f11_negative_preserved"`
 Seeds [2]uint32 `json:"seeds"`
 Policies [2]string `json:"policies"`
 PriorOdds int `json:"prior_odds"`
 HiddenStateCount int `json:"hidden_state_count"`
 CandidateRuleCount int `json:"candidate_rule_count"`
 DelaySteps int `json:"delay_steps"`
 TrainingActions int `json:"training_actions"`
 ProbeActions int `json:"probe_actions"`
 ScoredDecisionsPerModel int `json:"scored_decisions_per_model"`
 MinimumStrongGain int `json:"minimum_strong_gain"`
 MinimumAblationGain int `json:"minimum_ablation_gain"`
 ArmCount int `json:"arm_count"`
 PassingArms int `json:"passing_arms"`
 TotalRuleChecks int `json:"total_rule_checks"`
 Arms []F12Arm `json:"arms"`
 Classification string `json:"classification"`
 DevelopmentOnly bool `json:"development_only"`
 IndependentScienceSeedsConsumed bool `json:"independent_science_seeds_consumed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 FullProcessEfficiencyProven bool `json:"full_process_efficiency_proven"`
 OwnerEligible bool `json:"owner_eligible"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 LiveFORGEResearchChanged bool `json:"live_forge_research_changed"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 DigestSHA256 string `json:"digest_sha256"`
}
func f12Digest(v F12Report)string{
 v.DigestSHA256=""
 return f8Digest("FORGE-EUREKA-F12-HIDDEN-STATE-V1\n",v)
}
func f12Kinds()[5]string{return [5]string{"causal","mle","table","no-action","wrong-lag"}}
func f12Arm(seed uint32,policy string)(F12Arm,error){
 events,err:=f12Generate(seed,policy)
 if err!=nil||len(events)!=F12Actions{return F12Arm{},errF12}
 a:=F12Arm{Seed:seed,Policy:policy,Actions:events,
  HistorySHA256:f8Digest("FORGE-EUREKA-F12-EVENTS-V1\n",events)}
 var models [5]*f12Memory
 for i,kind:=range f12Kinds(){
  models[i],err=f12New(kind)
  if err!=nil{return F12Arm{},errF12}
 }
 var originalG1 [5]int
 for generation:=0;generation<2;generation++{
  cut:=F12LearnActions+3*(generation+1)
  begin:=0
  if generation==1{begin=F12LearnActions+3}
  for _,e:=range events[begin:cut]{
   for _,m:=range models{if m.Observe(e)!=nil{return F12Arm{},errF12}}
  }
  round:=F12Round{Generation:generation+1,ActionCount:cut,
   CreditedDelayedConsequences:cut-F12Delay,
   UnresolvedPendingActions:F12Delay,ColdStateMatches:true}
  for i,m:=range models{
   if m.Seen!=cut||m.Credited!=cut-F12Delay{return F12Arm{},errF12}
   snap,err:=m.Snapshot()
   if err!=nil{return F12Arm{},errF12}
   round.SnapshotSHA256[i]=f3Hash(snap)
   cold,err:=f12Load(snap,round.SnapshotSHA256[i])
   if err!=nil||!reflect.DeepEqual(m,cold){return F12Arm{},errF12}
   after,err:=cold.Snapshot()
   if err!=nil||!bytes.Equal(snap,after){return F12Arm{},errF12}
   fresh,_:=f12New(m.Kind)
   for _,e:=range events[:cut]{
    if fresh.Observe(e)!=nil{return F12Arm{},errF12}
   }
   replay,err:=fresh.Snapshot()
   if err!=nil||!bytes.Equal(snap,replay){return F12Arm{},errF12}
   // Only newly delivered three actions advance G2: the old 51 actions
   // are retained as counted learned state and two outstanding causal IDs.
   models[i]=cold
   round.OriginalCorrect[i],_,err=f12Score(cold,seed,0)
   if err!=nil{return F12Arm{},errF12}
   var roundCost int
   round.ChangedCorrect[i],roundCost,err=f12Score(cold,seed,1)
   if err!=nil{return F12Arm{},errF12}
   round.PredictionRuleChecks+=roundCost
   if generation==0{originalG1[i]=round.OriginalCorrect[i]}
  }
  round.CausalCorrect=round.ChangedCorrect[0]
  round.MLECorrect=round.ChangedCorrect[1]
  round.TableCorrect=round.ChangedCorrect[2]
  round.NoActionCorrect=round.ChangedCorrect[3]
  round.WrongLagCorrect=round.ChangedCorrect[4]
  round.StrongestCorrect=max(round.MLECorrect,round.TableCorrect)
  round.AdvantageOverStrongest=round.CausalCorrect-round.StrongestCorrect
  round.AdvantageOverNoAction=round.CausalCorrect-round.NoActionCorrect
  round.AdvantageOverWrongLag=round.CausalCorrect-round.WrongLagCorrect
  a.Rounds[generation]=round
 }
 // The retention gate applies to the proposed causal mechanism, not to
 // deliberately impaired controls: a wrong-lag ablation is allowed to regress.
 a.OriginalWorldRetained=a.Rounds[1].OriginalCorrect[0]>=originalG1[0]
 g2:=a.Rounds[1]
 a.MeetsFrozenThreshold=a.OriginalWorldRetained&&g2.ColdStateMatches&&
  g2.AdvantageOverStrongest>=F12MinimumStrongGain&&
  g2.AdvantageOverNoAction>=F12MinimumAblationGain&&
  g2.AdvantageOverWrongLag>=F12MinimumAblationGain
 return a,nil
}
func F12Development()(F12Report,error){
 old,err:=F11Development()
 if err!=nil||F11Validate(old)!=nil||old.Classification!=F11ReviewNO_GO||
  old.OwnerEligible||old.ScientificAccepted||old.DispatchAuthorized{
  return F12Report{},errF12
 }
 out:=F12Report{Schema:F12Schema,ParentF11DigestSHA256:old.DigestSHA256,
  F10AndF11NegativePreserved:true,Seeds:f12Seeds(),Policies:f12Policies(),
  PriorOdds:3,HiddenStateCount:4,CandidateRuleCount:F12RuleCount,DelaySteps:F12Delay,
  TrainingActions:F12LearnActions,ProbeActions:F12ProbeActions,
  ScoredDecisionsPerModel:F12DecisionCount,
  MinimumStrongGain:F12MinimumStrongGain,MinimumAblationGain:F12MinimumAblationGain,
  Arms:make([]F12Arm,0,4),DevelopmentOnly:true}
 for _,seed:=range out.Seeds{
  for _,policy:=range out.Policies{
   arm,err:=f12Arm(seed,policy)
   if err!=nil{return F12Report{},errF12}
   out.Arms=append(out.Arms,arm)
   out.ArmCount++
   if arm.MeetsFrozenThreshold{out.PassingArms++}
   for _,round:=range arm.Rounds{out.TotalRuleChecks+=round.PredictionRuleChecks}
  }
 }
 if out.ArmCount!=4{return F12Report{},errF12}
 out.Classification=F12NO_GO
 if out.PassingArms==4{out.Classification=F12Signal}
 out.DigestSHA256=f12Digest(out)
 return out,nil
}
func F12Validate(v F12Report)error{
 if v.Schema!=F12Schema||v.DigestSHA256!=f12Digest(v)||
  !v.DevelopmentOnly||!v.F10AndF11NegativePreserved||
  v.IndependentScienceSeedsConsumed||v.ScientificAccepted||
  v.FullProcessEfficiencyProven||v.OwnerEligible||v.DispatchAuthorized||
  v.LiveFORGEResearchChanged||v.AgentCalls!=0||v.PaidAPICalls!=0{return errF12}
 expected,err:=F12Development()
 if err!=nil||!reflect.DeepEqual(v,expected){return errF12}
 return nil
}
