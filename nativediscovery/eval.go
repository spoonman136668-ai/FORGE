// Package nativediscovery is a bounded, source-only FORGE development evaluator.
// It never dispatches research, activates an owner, or asserts science.
package nativediscovery

import (
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "sort"
 "time"
 "github.com/spoonman136668-ai/forge/noveltymechanisms"
)
const(
 ReportSchema="forge.native-discovery.action-consequence-development.v1"
 TrainRounds=5
 InterferenceRounds=8
 FrozenMinGainPP=5.0
 FrozenMaxForgettingPP=10.0
)
var Seeds=[3]int{11,23,47}
var cues=[3]string{"amber","cedar","slate"}
var modes=[2]string{"north","south"}
var errInvalid=errors.New("NATIVE_DISCOVERY_FROZEN_PROTOCOL_INVALID")
type Observation struct{ Object,Cue,Mode string; Level int }
type Transition struct{ Observation Observation; Action,NextLevel int }
func(t Transition)valid()bool{
 if t.Action<0||t.Action>2||t.Observation.Object==""||len(t.Observation.Object)>48||
 t.Observation.Level<0||t.Observation.Level>10||t.NextLevel< -1||t.NextLevel>11||
 t.NextLevel-t.Observation.Level< -1||t.NextLevel-t.Observation.Level>1{return false}
 c,m:=false,false
 for _,v:=range cues{if t.Observation.Cue==v{c=true}}
 for _,v:=range modes{if t.Observation.Mode==v{m=true}}
 return c&&m
}
// The hidden causal rule is for the environment, not exposed to models.
func effect(o Observation,action,world int)int{
 sign:=1
 if o.Cue=="cedar"{sign=-1}
 if o.Mode=="south"{sign= -sign}
 if world==1{sign= -sign}
 if action==0{return sign}
 if action==1{return -sign}
 return 0
}
func outcome(o Observation,a,world int)Transition{return Transition{o,a,o.Level+effect(o,a,world)}}
func key(o Observation,a int)string{return o.Cue+"-"+o.Mode+fmt.Sprintf("-a%d",a)}
func objectKey(o Observation,a int)string{return o.Object+fmt.Sprintf("-a%d",a)}
func relationKey(o Observation)string{return o.Cue+"-"+o.Mode}
func role(a int)string{return fmt.Sprintf("action-%d",a)}
var deltaLabels=[3]string{"down","hold","up"}

// Assoc learns from actual logged transitions, then uses existing F95 typed
// relations to retrieve action consequences. It is not an accepted learner.
type Assoc struct{Counts map[string][3]int `json:"counts"`;memory noveltymechanisms.Memory}
func newAssoc()*Assoc{return &Assoc{Counts:make(map[string][3]int)}}
func(m *Assoc)Observe(t Transition)error{
 if !t.valid(){return errInvalid}
 k:=key(t.Observation,t.Action);v:=m.Counts[k]
 v[t.NextLevel-t.Observation.Level+1]++;m.Counts[k]=v;return nil
}
func(m *Assoc)Freeze()error{
 if len(m.Counts)==0||len(m.Counts)>54{return errInvalid}
 keys:=make([]string,0,len(m.Counts))
 for k:=range m.Counts{keys=append(keys,k)}
 sort.Strings(keys)
 links:=make([]noveltymechanisms.Relation,0,len(keys))
 for _,k:=range keys{
  valid:=false
  for _,cue:=range cues{for _,mode:=range modes{for a:=0;a<3;a++{
   if k==key(Observation{Cue:cue,Mode:mode},a){valid=true}
  }}}
  counts:=m.Counts[k]
  if !valid||counts[0]<0||counts[1]<0||counts[2]<0||
     counts[0]+counts[1]+counts[2]==0||counts[0]+counts[1]+counts[2]>256{return errInvalid}
  picked:=1
  for i:=0;i<3;i++{if counts[i]>counts[picked]{picked=i}}
  a:=int(k[len(k)-1]-'0')
  if a<0||a>2||len(k)<4{return errInvalid}
  links=append(links,noveltymechanisms.Relation{
   From:k[:len(k)-3],Role:role(a),To:deltaLabels[picked]})
 }
 mem,err:=noveltymechanisms.Compile(links)
 if err!=nil{return err}
 m.memory=mem
 return nil
}
func(m *Assoc)Predict(o Observation,a int)int{
 if a<0||a>2{return 0}
 result,err:=noveltymechanisms.Resolve(m.memory,relationKey(o),[]string{role(a)})
 if err!=nil||!result.UniqueAnswer||len(result.Targets)!=1{return 0}
 for i,v:=range deltaLabels{if v==result.Targets[0]{return i-1}}
 return 0
}
func(m *Assoc)Snapshot()([]byte,error){return json.Marshal(m)}
func restoreAssoc(data []byte)(*Assoc,error){
 if len(data)==0||len(data)>8192{return nil,errInvalid}
 var m Assoc
 if err:=json.Unmarshal(data,&m);err!=nil{return nil,err}
 if err:=m.Freeze();err!=nil{return nil,err}
 return &m,nil
}

// Conventional controls receive identical logged training information:
// one per-object empirical table, one stronger feature-compositional table.
type Table struct{Counts map[string][3]int;perObject bool}
func newTable(perObject bool)*Table{return &Table{Counts:make(map[string][3]int),perObject:perObject}}
func(t *Table)Observe(x Transition)error{
 if !x.valid(){return errInvalid}
 k:=key(x.Observation,x.Action)
 if t.perObject{k=objectKey(x.Observation,x.Action)}
 v:=t.Counts[k];v[x.NextLevel-x.Observation.Level+1]++;t.Counts[k]=v
 return nil
}
func(t *Table)Predict(o Observation,a int)int{
 k:=key(o,a)
 if t.perObject{k=objectKey(o,a)}
 v:=t.Counts[k];best:=1
 for i:=0;i<3;i++{if v[i]>v[best]{best=i}}
 return best-1
}
type Model interface{Predict(Observation,int)int}
func choose(m Model,o Observation,target int)int{
 best,loss:=0,math.MaxInt
 for a:=0;a<3;a++{
  delta:=m.Predict(o,a)
  distance:=o.Level+delta-target
  if distance<0{distance= -distance}
  if distance<loss{best=a;loss=distance}
 }
 return best
}
func correctAction(o Observation,target,world,action int)bool{
 loss:=o.Level+effect(o,action,world)-target
 if loss<0{loss= -loss}
 for a:=0;a<3;a++{
  other:=o.Level+effect(o,a,world)-target
  if other<0{other= -other}
  if other<loss{return false}
 }
 return true
}
func suite(seed,world int,training bool,rounds int)[]Transition{
 data:=make([]Transition,0,rounds*len(cues)*len(modes)*3)
 purpose:="hold"
 if training{purpose="train"}
 for pass:=0;pass<rounds;pass++{
  for ci,c:=range cues{for mi,mode:=range modes{for a:=0;a<3;a++{
   o:=Observation{Object:fmt.Sprintf("%s-%d-%d-%d",purpose,seed,ci,mi),
     Cue:c,Mode:mode,Level:3+(seed+pass+ci+mi)%3}
   data=append(data,outcome(o,a,world))
  }}}
 }
 // Deterministic order rotation (copy; never mutate the original tape).
 if len(data)>0{
  shift:=seed%len(data)
  rotated:=append([]Transition(nil),data[shift:]...)
  data=append(rotated,data[:shift]...)
 }
 return data
}
func scored(m Model,seed,world int)(int,int){
 right,total:=0,0
 for ci,c:=range cues{for mi,mode:=range modes{for rep:=0;rep<3;rep++{
  for _,wanted:=range []int{-1,1}{
   o:=Observation{Object:fmt.Sprintf("hold-%d-%d-%d-%d",seed,ci,mi,rep),
    Cue:c,Mode:mode,Level:4}
   a:=choose(m,o,o.Level+wanted)
   if correctAction(o,o.Level+wanted,world,a){right++}
   total++
  }
 }}}
 return right,total
}
func pct(a,b int)float64{if b==0{return 0};return 100*float64(a)/float64(b)}
type SeedReport struct{
 Seed int `json:"seed"`
 TrainingTransitions int `json:"training_transitions"`
 TransferDecisions int `json:"transfer_decisions"`
 FreshAccuracy float64 `json:"fresh_accuracy_pct"`
 RelationalAccuracy float64 `json:"relational_accuracy_pct"`
 ObjectTabularAccuracy float64 `json:"object_tabular_accuracy_pct"`
 FactorTableAccuracy float64 `json:"factor_table_accuracy_pct"`
 ColdRestoreAccuracy float64 `json:"cold_restore_accuracy_pct"`
 UnfamiliarDynamicsAccuracy float64 `json:"unfamiliar_dynamics_accuracy_pct"`
 PostInterferenceAccuracy float64 `json:"post_interference_accuracy_pct"`
 ShuffledFeedbackAccuracy float64 `json:"shuffled_feedback_accuracy_pct"`
 TrainingWallNs [3]int64 `json:"training_wall_ns_by_model"`
 ColdSnapshotBytes int `json:"cold_snapshot_bytes"`
}
type Report struct{
 Schema string `json:"schema"`
 Seeds [3]int `json:"seeds"`
 TrainingRounds int `json:"training_rounds"`
 InterferenceRounds int `json:"interference_rounds"`
 FrozenRequiredGainPP float64 `json:"frozen_required_gain_pp"`
 FrozenMaxForgettingPP float64 `json:"frozen_max_forgetting_pp"`
 PerSeed []SeedReport `json:"per_seed"`
 CriterionMet bool `json:"criterion_met"`
 DevelopmentStatus string `json:"development_status"`
 SyntheticWorld bool `json:"synthetic_world"`
 ModelCalls int `json:"model_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 ActiveControllerWrites int `json:"active_controller_writes"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 ScientificAccepted bool `json:"scientific_accepted"`
 GeneralRSIProven bool `json:"general_rsi_proven"`
}
// RunDevelopment is a complete, bounded synthetic assay. No held-out results
// train the models. Positive development results still need independent science.
func RunDevelopment()(Report,error){
 out:=Report{Schema:ReportSchema,Seeds:Seeds,TrainingRounds:TrainRounds,
  InterferenceRounds:InterferenceRounds,FrozenRequiredGainPP:FrozenMinGainPP,
  FrozenMaxForgettingPP:FrozenMaxForgettingPP,PerSeed:make([]SeedReport,0,len(Seeds)),SyntheticWorld:true}
 successes:=0
 for _,seed:=range Seeds{
  tape:=suite(seed,0,true,TrainRounds)
  native,objectControl,factorControl:=newAssoc(),newTable(true),newTable(false)
  fresh:=newAssoc()
  if err:=fresh.Observe(Transition{});err==nil{return Report{},errInvalid}
  freshRight,freshTotal:=scored(fresh,seed,0)
  models:=[]interface{Observe(Transition)error}{native,objectControl,factorControl}
  var wall [3]int64
  for i,m:=range models{
   started:=time.Now()
   for _,x:=range tape{if err:=m.Observe(x);err!=nil{return Report{},err}}
   wall[i]=time.Since(started).Nanoseconds()
  }
  if err:=native.Freeze();err!=nil{return Report{},err}
  nativeRight,total:=scored(native,seed,0)
  objectRight,_:=scored(objectControl,seed,0)
  factorRight,_:=scored(factorControl,seed,0)
  snapshot,err:=native.Snapshot();if err!=nil{return Report{},err}
  cold,err:=restoreAssoc(snapshot);if err!=nil{return Report{},err}
  coldRight,_:=scored(cold,seed,0)
  if coldRight!=nativeRight{return Report{},errInvalid}
  unknownRule,_:=scored(cold,seed,1)
  shuffled:=newAssoc()
  for _,x:=range tape{
   y:=x
   y.NextLevel=x.Observation.Level-(x.NextLevel-x.Observation.Level)
   if err:=shuffled.Observe(y);err!=nil{return Report{},err}
  }
  if err:=shuffled.Freeze();err!=nil{return Report{},err}
  shuffledRight,_:=scored(shuffled,seed,0)
  for _,x:=range suite(seed,1,true,InterferenceRounds){
   if err:=cold.Observe(x);err!=nil{return Report{},err}
  }
  if err:=cold.Freeze();err!=nil{return Report{},err}
  interferenceRight,_:=scored(cold,seed,0)
  if total!=36||freshTotal!=total||len(tape)!=TrainRounds*18||
   freshRight>=nativeRight||shuffledRight>=nativeRight{return Report{},errInvalid}
  row:=SeedReport{Seed:seed,TrainingTransitions:len(tape),TransferDecisions:total,
   FreshAccuracy:pct(freshRight,total),RelationalAccuracy:pct(nativeRight,total),
   ObjectTabularAccuracy:pct(objectRight,total),FactorTableAccuracy:pct(factorRight,total),
   ColdRestoreAccuracy:pct(coldRight,total),UnfamiliarDynamicsAccuracy:pct(unknownRule,total),
   PostInterferenceAccuracy:pct(interferenceRight,total),ShuffledFeedbackAccuracy:pct(shuffledRight,total),
   TrainingWallNs:wall,ColdSnapshotBytes:len(snapshot)}
  out.PerSeed=append(out.PerSeed,row)
  strongest:=math.Max(row.ObjectTabularAccuracy,row.FactorTableAccuracy)
  if row.RelationalAccuracy-strongest>=FrozenMinGainPP &&
     row.ColdRestoreAccuracy==row.RelationalAccuracy &&
     row.RelationalAccuracy-row.PostInterferenceAccuracy<=FrozenMaxForgettingPP{successes++}
 }
 out.CriterionMet=successes>=2
 out.DevelopmentStatus="DEV_NO_GO"
 if out.CriterionMet{out.DevelopmentStatus="SYNTHETIC_PROVISIONAL_ONLY"}
 return out,nil
}
