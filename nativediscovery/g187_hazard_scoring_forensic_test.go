package nativediscovery

import (
 "encoding/json"
 "fmt"
 "math"
 "reflect"
 "testing"
)

// G187 is test-only: these values never enter F37/F38 models or frozen reports.
type g187ForensicTrial struct {
 LegacySensorNLL float64
 HazardSensorNLL float64
 LegacyCleanNLL float64
 HazardCleanNLL float64
 ActionsSHA256 string
 SensorsSHA256 string
 GoalsSHA256 string
 MidCheckpointSHA256 string
 TerminalSHA256 string
 Work int
}

func g187Replay(archive f36Archive, kind string, seed uint32, sched string, eps float64, fixedActions []int, f38 bool) (g187ForensicTrial, error) {
 var out g187ForensicTrial
 if len(fixedActions) != 96 || (kind != "compositional-issued-memory" && kind != "two-bank-issued-bayes") || (eps != 0 && eps != F37Epsilon) { return out, fmt.Errorf("G187 invalid frozen replay source") }
 var initial [2]int
 var cueFn func(int) (int, error)
 var goalFn func(int) (int, error)
 var stepFn func(int, int, int) (int, [2]int, error)
 if f38 {
  world, err := f38NewWorld(seed, sched)
  if err != nil { return out, err }
  initial = world.Sensors
  cueFn = func(t int) (int, error) { return f38Cue(world.Spec, t) }
  goalFn = func(t int) (int, error) { return f38Goal(world.Spec, t) }
  stepFn = func(t, c, a int) (int, [2]int, error) { return world.step(t, c, a) }
 } else {
  valid := false
  for _, w := range f36Worlds() { if w.Seed == seed && w.Schedule == sched { valid = true } }
  if !valid { return out, fmt.Errorf("G187 wrong F37 world") }
  world, err := f36NewWorld(seed)
  if err != nil { return out, err }
  initial = world.Sensors
  cueFn = func(t int) (int, error) { return f36Cue(seed, sched, t) }
  goalFn = func(t int) (int, error) { return f36Goal(seed, t) }
  stepFn = func(t, c, a int) (int, [2]int, error) { return world.step(t, c, a) }
 }
 model, err := f36Init(archive, kind, initial)
 if err != nil { return out, err }
 if !f38 {
  raw, err := json.Marshal(model)
  if err != nil { return out, err }
  model, err = f36LoadModel(raw)
  if err != nil { return out, err }
 }
 steps := make([]int, 0, 96)
 sensors := make([][2]int, 0, 97)
 goals := make([]int, 0, 24)
 sensors = append(sensors, initial)
 interventions := 0
 for t := 0; t < 96; t++ {
  cue, err := cueFn(t)
  if err != nil { return out, err }
  goal, err := goalFn(t)
  if err != nil { return out, err }
  if t%4 == 0 { goals = append(goals, goal) }
  // Original fixed-action replay charges each policy forecast to Work.
  if _, err = f37Decision(&model, t, cue, goal, interventions); err != nil { return out, err }
  action := fixedActions[t]
  if action < 0 || action > 2 { return out, fmt.Errorf("G187 invalid action") }
  if action > 0 { interventions++ }
  if interventions > 36 { return out, fmt.Errorf("G187 action cap") }
  steps = append(steps, action)
  clean, observed, err := stepFn(t, cue, action)
  if err != nil { return out, err }
  sensors = append(sensors, observed)
  prior, evidence, historicalP, err := f37Evidence(model, t, cue, action, observed, eps)
  if err != nil { return out, err }
  hazardP, historicalCleanP, hazardCleanP := 0.0, 0.0, 0.0
  for k := 0; k < 4; k++ {
   mixed := .95*model.Weights[k] + .05/4
   hazardP += mixed*evidence[k]
   historicalCleanP += model.Weights[k]*prior[k][clean]
   hazardCleanP += mixed*prior[k][clean]
  }
  for _, v := range []float64{historicalP, hazardP, historicalCleanP, hazardCleanP} {
   if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 || v > 1+1e-8 { return out, fmt.Errorf("G187 invalid probability: %g", v) }
  }
  out.LegacySensorNLL -= math.Log(math.Max(historicalP, 1e-12))
  out.HazardSensorNLL -= math.Log(math.Max(hazardP, 1e-12))
  out.LegacyCleanNLL -= math.Log(math.Max(historicalCleanP, 1e-12))
  out.HazardCleanNLL -= math.Log(math.Max(hazardCleanP, 1e-12))
  if f38 { err = f38Observe(&model, t, cue, action, observed, eps) } else if eps == 0 { err = model.observe(t, cue, action, observed) } else { err = f37CalibratedObserve(&model, t, cue, action, observed) }
  if err != nil { return out, err }
  if t == 47 {
   raw, err := json.Marshal(model)
   if err != nil { return out, err }
   out.MidCheckpointSHA256 = f27Hash(raw)
  }
 }
 out.LegacySensorNLL /= 96
 out.HazardSensorNLL /= 96
 out.LegacyCleanNLL /= 96
 out.HazardCleanNLL /= 96
 out.Work = model.Work
 raw, err := json.Marshal(steps)
 if err != nil { return out, err }
 out.ActionsSHA256 = f27Hash(raw)
 raw, err = json.Marshal(sensors)
 if err != nil { return out, err }
 out.SensorsSHA256 = f27Hash(raw)
 raw, err = json.Marshal(goals)
 if err != nil { return out, err }
 out.GoalsSHA256 = f27Hash(raw)
 raw, err = json.Marshal(model)
 if err != nil { return out, err }
 out.TerminalSHA256 = f27Hash(raw)
 return out, nil
}

func g187CheckCustody(t *testing.T, scope string, seed uint32, kind string, replay g187ForensicTrial, sensorNLL, cleanNLL float64, actionSHA, sensorSHA, goalSHA, midSHA, terminalSHA string, work int) {
 t.Helper()
 if math.Abs(replay.LegacySensorNLL-sensorNLL)>1e-9 || math.Abs(replay.LegacyCleanNLL-cleanNLL)>1e-9 ||
  replay.ActionsSHA256!=actionSHA || replay.SensorsSHA256!=sensorSHA || replay.GoalsSHA256!=goalSHA ||
  replay.MidCheckpointSHA256!=midSHA || replay.TerminalSHA256!=terminalSHA || replay.Work!=work {
  t.Fatalf("G187 original-score/trace/cold-custody mismatch: %s seed=%d model=%s scorer=%.9f source=%.9f clean=%.9f source_clean=%.9f",scope,seed,kind,replay.LegacySensorNLL,sensorNLL,replay.LegacyCleanNLL,cleanNLL)
 }
}

// This test does NOT alter the frozen F37/F38 classifications or use first-use worlds.
func TestG187FrozenPredictiveHazardForensic(t *testing.T) {
 archive, err := f36Train()
 if err != nil { t.Fatal(err) }
 original37, err := F37Development()
 if err != nil || F37Validate(original37)!=nil || original37.Classification!=F37CalNoGo || original37.PassingPairs!=6 { t.Fatal("G187 F37 frozen source/negative drift",err) }
 original38, err := F38Development()
 if err != nil || F38Validate(original38)!=nil || original38.Classification!=F38NoGo || original38.PassingCalibration!=6 || original38.PassingControl!=0 { t.Fatal("G187 F38 frozen source/negative drift",err) }
 differences,revised37,revised38 := 0,0,0
 kinds := [2]string{"compositional-issued-memory","two-bank-issued-bayes"}
 for _,world := range original37.Worlds {
  for j,kind := range kinds {
   frozen := world.Comparisons[j]
   legacy,actions,_,err := f37Trial(archive,kind,world.Seed,world.Schedule,0,nil,false)
   if err != nil || !reflect.DeepEqual(legacy,frozen.Legacy) { t.Fatalf("G187 F37 legacy drift: %d %s %v",world.Seed,kind,err) }
   calibrated,_,_,err := f37Trial(archive,kind,world.Seed,world.Schedule,F37Epsilon,actions,false)
   if err != nil || !reflect.DeepEqual(calibrated,frozen.Calibrated) { t.Fatalf("G187 F37 calibrated drift: %d %s %v",world.Seed,kind,err) }
   if legacy.ActionsSHA256!=calibrated.ActionsSHA256 || legacy.SensorsSHA256!=calibrated.SensorsSHA256 || legacy.GoalsSHA256!=calibrated.GoalsSHA256 || !legacy.ColdMatches || !calibrated.ColdMatches { t.Fatal("G187 F37 paired evidence mismatch") }
   oldReplay,err := g187Replay(archive,kind,world.Seed,world.Schedule,0,actions,false)
   if err != nil { t.Fatal(err) }
   calReplay,err := g187Replay(archive,kind,world.Seed,world.Schedule,F37Epsilon,actions,false)
   if err != nil { t.Fatal(err) }
   g187CheckCustody(t,"F37 legacy",world.Seed,kind,oldReplay,legacy.MeanSensorNLL,legacy.MeanScorerCleanNLL,legacy.ActionsSHA256,legacy.SensorsSHA256,legacy.GoalsSHA256,legacy.MidCheckpointSHA256,legacy.TerminalSHA256,legacy.Work)
   g187CheckCustody(t,"F37 calibrated",world.Seed,kind,calReplay,calibrated.MeanSensorNLL,calibrated.MeanScorerCleanNLL,calibrated.ActionsSHA256,calibrated.SensorsSHA256,calibrated.GoalsSHA256,calibrated.MidCheckpointSHA256,calibrated.TerminalSHA256,calibrated.Work)
   gain := oldReplay.HazardSensorNLL-calReplay.HazardSensorNLL
   if gain>=.05 && calibrated.ZeroProbabilityUpdates==0 && legacy.LegacyFallbacks>0 { revised37++ }
   if math.Abs(oldReplay.HazardSensorNLL-oldReplay.LegacySensorNLL)>1e-10 || math.Abs(calReplay.HazardSensorNLL-calReplay.LegacySensorNLL)>1e-10 { differences++ }
   t.Logf("G187_SCOPE=F37 seed=%d family=%s historical_legacy=%.6f historical_cal=%.6f historical_gain=%+.6f corrected_legacy=%.6f corrected_cal=%.6f corrected_gain=%+.6f old_clean=%.6f corrected_clean=%.6f",world.Seed,kind,legacy.MeanSensorNLL,calibrated.MeanSensorNLL,frozen.SensorNLLGain,oldReplay.HazardSensorNLL,calReplay.HazardSensorNLL,gain,calReplay.LegacyCleanNLL,calReplay.HazardCleanNLL)
  }
 }
 for _,world := range original38.Worlds {
  for j,kind := range kinds {
   frozen := world.Matched[j]
   legacy,actions,_,err := f38Trial(archive,f36Model{},kind,world.Seed,world.Schedule,0,nil,false)
   if err != nil || !reflect.DeepEqual(legacy,frozen.Legacy) { t.Fatalf("G187 F38 legacy drift: %d %s %v",world.Seed,kind,err) }
   calibrated,_,_,err := f38Trial(archive,f36Model{},kind,world.Seed,world.Schedule,F37Epsilon,actions,false)
   if err != nil || !reflect.DeepEqual(calibrated,frozen.Calibrated) { t.Fatalf("G187 F38 calibrated drift: %d %s %v",world.Seed,kind,err) }
   if legacy.ActionsSHA256!=calibrated.ActionsSHA256 || legacy.SensorsSHA256!=calibrated.SensorsSHA256 || legacy.GoalsSHA256!=calibrated.GoalsSHA256 || !legacy.ColdMatches || !calibrated.ColdMatches { t.Fatal("G187 F38 paired evidence mismatch") }
   oldReplay,err := g187Replay(archive,kind,world.Seed,world.Schedule,0,actions,true)
   if err != nil { t.Fatal(err) }
   calReplay,err := g187Replay(archive,kind,world.Seed,world.Schedule,F37Epsilon,actions,true)
   if err != nil { t.Fatal(err) }
   g187CheckCustody(t,"F38 legacy",world.Seed,kind,oldReplay,legacy.MeanSensorNLL,legacy.ScorerCleanNLL,legacy.ActionsSHA256,legacy.SensorsSHA256,legacy.GoalsSHA256,legacy.MidCheckpointSHA256,legacy.TerminalSHA256,legacy.Work)
   g187CheckCustody(t,"F38 calibrated",world.Seed,kind,calReplay,calibrated.MeanSensorNLL,calibrated.ScorerCleanNLL,calibrated.ActionsSHA256,calibrated.SensorsSHA256,calibrated.GoalsSHA256,calibrated.MidCheckpointSHA256,calibrated.TerminalSHA256,calibrated.Work)
   gain := oldReplay.HazardSensorNLL-calReplay.HazardSensorNLL
   if gain>=.05 && calibrated.Unsupported==0 && legacy.LegacyFallbacks>0 { revised38++ }
   if math.Abs(oldReplay.HazardSensorNLL-oldReplay.LegacySensorNLL)>1e-10 || math.Abs(calReplay.HazardSensorNLL-calReplay.LegacySensorNLL)>1e-10 { differences++ }
   t.Logf("G187_SCOPE=F38 seed=%d family=%s historical_legacy=%.6f historical_cal=%.6f historical_gain=%+.6f corrected_legacy=%.6f corrected_cal=%.6f corrected_gain=%+.6f old_clean=%.6f corrected_clean=%.6f",world.Seed,kind,legacy.MeanSensorNLL,calibrated.MeanSensorNLL,frozen.SensorNLLGain,oldReplay.HazardSensorNLL,calReplay.HazardSensorNLL,gain,calReplay.LegacyCleanNLL,calReplay.HazardCleanNLL)
  }
 }
 if differences==0 { t.Fatal("G187 suspected scorer discrepancy not independently reproduced") }
 t.Logf("G187_FORENSIC=DIAGNOSTIC_ONLY changed_pairs=%d/16 corrected_F37_threshold_arms=%d/8 corrected_F38_threshold_arms=%d/8 frozen_F37=%s frozen_F38=%s frozen_F38_goal_control=%d/4 FIRST_USE=false SCIENTIFIC_PASS=false",differences,revised37,revised38,original37.Classification,original38.Classification,original38.PassingControl)
}
