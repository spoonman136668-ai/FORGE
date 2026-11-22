package nativediscovery

import (
 "bytes"
 "encoding/json"
 "fmt"
 "math"
 "testing"
)

// g189ReplayV2 independently evaluates the G188 scorer on each physical
// observation of the unchanged G187 paired trace. Only result accounting
// differs; real world dynamics and all observer updates are original.
func g189ReplayV2(archive f36Archive, kind string, seed uint32, schedule string, eps float64, fixedActions []int, isF38 bool) (g187ForensicTrial, error) {
 var result g187ForensicTrial
 if len(fixedActions)!=96 || (eps!=0 && eps!=F37Epsilon) ||
  (kind!="compositional-issued-memory" && kind!="two-bank-issued-bayes") {
  return result, fmt.Errorf("G189 invalid source or actions")
 }
 var initial [2]int
 var cueFn func(int)(int,error)
 var goalFn func(int)(int,error)
 var stepFn func(int,int,int)(int,[2]int,error)
 if isF38 {
  world,err:=f38NewWorld(seed,schedule)
  if err!=nil {return result,err}
  initial=world.Sensors
  cueFn=func(t int)(int,error){return f38Cue(world.Spec,t)}
  goalFn=func(t int)(int,error){return f38Goal(world.Spec,t)}
  stepFn=func(t,c,a int)(int,[2]int,error){return world.step(t,c,a)}
 } else {
  allowed:=false
  for _,w:=range f36Worlds(){if seed==w.Seed && schedule==w.Schedule {allowed=true}}
  if !allowed {return result,fmt.Errorf("G189 unqualified F37 world")}
  world,err:=f36NewWorld(seed)
  if err!=nil {return result,err}
  initial=world.Sensors
  cueFn=func(t int)(int,error){return f36Cue(seed,schedule,t)}
  goalFn=func(t int)(int,error){return f36Goal(seed,t)}
  stepFn=func(t,c,a int)(int,[2]int,error){return world.step(t,c,a)}
 }
 model,err:=f36Init(archive,kind,initial)
 if err!=nil {return result,err}
 if !isF38 {
  initialBytes,e:=json.Marshal(model)
  if e!=nil {return result,e}
  model,err=f36LoadModel(initialBytes)
  if err!=nil {return result,err}
 }
 actions:=make([]int,0,96)
 sensors:=make([][2]int,0,97)
 goals:=make([]int,0,24)
 sensors=append(sensors,initial)
 interventions:=0
 for t:=0;t<96;t++ {
  cue,e:=cueFn(t)
  if e!=nil {return result,e}
  goal,e:=goalFn(t)
  if e!=nil {return result,e}
  if t%4==0 {goals=append(goals,goal)}
  // Count original policy forecast work, but execute the frozen action trace.
  if _,e=f37Decision(&model,t,cue,goal,interventions);e!=nil{return result,e}
  action:=fixedActions[t]
  if action<0 || action>2 {return result,fmt.Errorf("G189 invalid action at t=%d",t)}
  if action>0 {interventions++}
  if interventions>36 {return result,fmt.Errorf("G189 action cap exceeded")}
  actions=append(actions,action)
  clean,observed,e:=stepFn(t,cue,action)
  if e!=nil {return result,e}
  sensors=append(sensors,observed)
  before,e:=json.Marshal(model)
  if e!=nil {return result,e}
  observedP,e:=g188SensorProbabilityV2(model,t,cue,action,observed,eps)
  if e!=nil {return result,fmt.Errorf("G189 sensor V2 at t=%d: %w",t,e)}
  cleanP,e:=g188CleanProbabilityScorerOnlyV2(model,t,cue,action,clean,eps)
  if e!=nil {return result,fmt.Errorf("G189 scorer-only clean V2 at t=%d: %w",t,e)}
  after,e:=json.Marshal(model)
  if e!=nil{return result,e}
  if !bytes.Equal(before,after){return result,fmt.Errorf("G189 scorer mutated policy at t=%d",t)}
  if math.IsNaN(observedP)||math.IsInf(observedP,0)||observedP<0||observedP>1+1e-9||
   math.IsNaN(cleanP)||math.IsInf(cleanP,0)||cleanP<0||cleanP>1+1e-9 {
   return result,fmt.Errorf("G189 probability invalid")
  }
  result.HazardSensorNLL-=math.Log(math.Max(observedP,1e-12))
  result.HazardCleanNLL-=math.Log(math.Max(cleanP,1e-12))
  if isF38 {e=f38Observe(&model,t,cue,action,observed,eps)
  } else if eps==0 {e=model.observe(t,cue,action,observed)
  } else {e=f37CalibratedObserve(&model,t,cue,action,observed)}
  if e!=nil {return result,e}
  if t==47 {
   raw,err:=json.Marshal(model)
   if err!=nil{return result,err}
   result.MidCheckpointSHA256=f27Hash(raw)
  }
 }
 result.HazardSensorNLL/=96
 result.HazardCleanNLL/=96
 result.Work=model.Work
 raw,err:=json.Marshal(actions)
 if err!=nil{return result,err}
 result.ActionsSHA256=f27Hash(raw)
 raw,err=json.Marshal(sensors)
 if err!=nil{return result,err}
 result.SensorsSHA256=f27Hash(raw)
 raw,err=json.Marshal(goals)
 if err!=nil{return result,err}
 result.GoalsSHA256=f27Hash(raw)
 raw,err=json.Marshal(model)
 if err!=nil{return result,err}
 result.TerminalSHA256=f27Hash(raw)
 return result,nil
}

func g189AssertEqual(t *testing.T, label string, source g187ForensicTrial, scored g187ForensicTrial) {
 t.Helper()
 if math.Abs(source.HazardSensorNLL-scored.HazardSensorNLL)>1e-10 ||
  math.Abs(source.HazardCleanNLL-scored.HazardCleanNLL)>1e-10 ||
  source.ActionsSHA256!=scored.ActionsSHA256 ||
  source.SensorsSHA256!=scored.SensorsSHA256 ||
  source.GoalsSHA256!=scored.GoalsSHA256 ||
  source.MidCheckpointSHA256!=scored.MidCheckpointSHA256 ||
  source.TerminalSHA256!=scored.TerminalSHA256 ||
  source.Work!=scored.Work {
  t.Fatalf("G189 source V2/G187 replay or original model custody discrepancy %s: source_sensor=%.12f v2_sensor=%.12f source_clean=%.12f v2_clean=%.12f",label,source.HazardSensorNLL,scored.HazardSensorNLL,source.HazardCleanNLL,scored.HazardCleanNLL)
 }
}

func TestG189V2VersusG187FullFrozenReplayAllFamilies(t *testing.T) {
 archive,e:=f36Train()
 if e!=nil{t.Fatal(e)}
 f37,e:=F37Development()
 if e!=nil||F37Validate(f37)!=nil||f37.Classification!=F37CalNoGo||f37.PassingPairs!=6 {
  t.Fatal("G189 frozen F37 science drift",e)
 }
 f38,e:=F38Development()
 if e!=nil||F38Validate(f38)!=nil||f38.Classification!=F38NoGo||
  f38.PassingCalibration!=6||f38.PassingControl!=0 {
  t.Fatal("G189 frozen F38 science drift",e)
 }
 pairs,modes:=0,0
 kinds:=[2]string{"compositional-issued-memory","two-bank-issued-bayes"}
 check:=func(label string, seed uint32,sched,kind string, f38World bool){
  t.Helper()
  var actions []int
  var err error
  if f38World {
   _,actions,_,err=f38Trial(archive,f36Model{},kind,seed,sched,0,nil,false)
  } else {
   _,actions,_,err=f37Trial(archive,kind,seed,sched,0,nil,false)
  }
  if err!=nil {t.Fatal(err)}
  for _,eps:=range []float64{0,F37Epsilon} {
   reference,err:=g187Replay(archive,kind,seed,sched,eps,actions,f38World)
   if err!=nil {t.Fatal(err)}
   actual,err:=g189ReplayV2(archive,kind,seed,sched,eps,actions,f38World)
   if err!=nil {t.Fatal(err)}
   g189AssertEqual(t,fmt.Sprintf("%s seed=%d kind=%s eps=%g",label,seed,kind,eps),reference,actual)
   modes++
   t.Logf("G189_V2_PARITY=PASS family=%s seed=%d kind=%s eps=%g original_nll=%.9f corrected_sensor_nll=%.9f corrected_clean_nll=%.9f",label,seed,kind,eps,reference.LegacySensorNLL,actual.HazardSensorNLL,actual.HazardCleanNLL)
  }
  pairs++
 }
 for _,w:=range f36Worlds(){
  for _,kind:=range kinds {check("F37",w.Seed,w.Schedule,kind,false)}
 }
 for _,w:=range f38Worlds(){
  for _,kind:=range kinds {check("F38",w.Seed,w.Schedule,kind,true)}
 }
 if pairs!=16||modes!=32 {t.Fatalf("G189 missing required frozen worlds: pairs=%d modes=%d",pairs,modes)}
 t.Logf("G189_SCORER_V2_REPLAY_PARITY=PASS matched_pairs=%d modes=%d observations=%d original_F37=%s original_F38=%s F38_goal_control=%d SCIENTIFIC_PASS=false FIRST_USE=false",pairs,modes,modes*96,f37.Classification,f38.Classification,f38.PassingControl)
}
