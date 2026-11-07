package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"
)
func TestF2FrozenUnfamiliarWorldDevelopment(t *testing.T){
 report,err:=F2Development();if err!=nil{t.Fatal(err)}
 again,err:=F2Development();if err!=nil{t.Fatal(err)}
 // Wall-time diagnostics cannot be compared for exact numerical parity.
 for i:=range report.Results{
  report.Results[i].LearnerTrainWallNs=[3]int64{}
  again.Results[i].LearnerTrainWallNs=[3]int64{}
 }
 if !reflect.DeepEqual(report,again){t.Fatal("nondeterministic procedural outcomes")}
 if report.Schema!=F2Schema||report.AcceptedBaseline!=F2AcceptedBase||
  report.Seeds!=F2Seeds||report.NoiseBP!=2000||
  report.FrozenRequiredGainPP!=5||report.FrozenMaxRetentionLossPP!=10||
  !report.NonCeilingHoldout||!report.SyntheticData||
  len(report.Results)!=len(F2Seeds)||report.NativeSourceGenerated||
  report.ScientificFirstUse||report.ScientificAccepted||
  report.AgentCalls!=0||report.PaidAPICalls!=0||report.OwnerWrites!=0||
  report.GeneralRSIProven{
  t.Fatalf("source-only task or authority drift %+v",report)
 }
 if report.DevelopmentCriterionMet&&report.DevelopmentStatus!="SYNTHETIC_PROVISIONAL_ONLY"{
  t.Fatal("provisional success incorrectly labeled")
 }
 if !report.DevelopmentCriterionMet&&report.DevelopmentStatus!="DEV_NO_GO"{
  t.Fatal("negative scientific result dropped")
 }
 for i,row:=range report.Results{
  if row.Seed!=F2Seeds[i]||row.TrainObservations!=48||
   row.ChangedRegimeProbes!=6||row.InterferenceObservations!=16||
   row.EvaluationDecisions!=64||!row.MatchedInformationAndActions||
   row.NativeColdBasePct!=row.NativeBaseAfterPct||
   row.SnapshotBytes<100||row.SnapshotBytes>4096{
   t.Fatalf("data/cold/negative control invalid %+v",row)
  }
 }
 serialized,err:=json.Marshal(report);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_NATIVE_DISCOVERY_F2=%s",serialized)
}
func TestF2BadEvidenceAndSnapshotFailClosed(t *testing.T){
 m:=&f2Native{}
 for _,tr:=range []f2Transition{
  {Context:f2Context{Regime:2,Cue:0,Mode:0},Action:0,Effect:1},
  {Context:f2Context{Regime:0,Cue:4,Mode:0},Action:0,Effect:1},
  {Context:f2Context{Regime:0,Cue:0,Mode:0},Action:2,Effect:1},
  {Context:f2Context{Regime:0,Cue:0,Mode:0},Action:0,Effect:0},
 }{
  if err:=m.Observe(tr);err==nil{t.Fatalf("invalid action evidence accepted: %+v",tr)}
 }
 overflow:=&f2Native{}
 overflow.Counts[0][0][0][1]=256
 prior:=overflow.Counts
 if err:=overflow.Observe(f2Transition{Context:f2Context{0,0,0},Action:0,Effect:1});err==nil||
  overflow.Counts!=prior{t.Fatal("over-cap observation mutated native evidence")}
 if err:=m.Observe(f2make(17,0,0,0,0,0));err!=nil{t.Fatal(err)}
 if err:=m.Freeze();err!=nil{t.Fatal(err)}
 original,err:=m.Snapshot();if err!=nil{t.Fatal(err)}
 cold,err:=f2restore(original);if err!=nil{t.Fatal(err)}
 context:=f2Context{Regime:0,Cue:0,Mode:0}
 if cold.Predict(context)!=m.Predict(context){t.Fatal("cold learned state drift")}
 for _,bad:=range [][]byte{
  nil,[]byte(`{}`),
  []byte(`{"schema":"wrong","counts":[]}`),
  []byte(`{"schema":"forge.native-discovery.unfamiliar-world-development.v1","counts":[]}`),
 }{
  if _,err:=f2restore(bad);err==nil{t.Fatalf("corrupt snapshot accepted: %s",bad)}
 }
}
func TestF2MatchedActionTapeAndUnfamiliarRegime(t *testing.T){
 for _,seed:=range F2Seeds{
  train,probes:=f2training(seed),f2probes(seed)
  if len(train)!=48||len(probes)!=6{t.Fatal("frozen action budget changed")}
  for _,row:=range train{
   if row.Context.Regime!=0||!f2Good(row){t.Fatal("invalid original history")}
  }
  for _,row:=range probes{
   if row.Context.Regime!=1||!f2Good(row){t.Fatal("invalid changed-regime probe")}
  }
  m:=&f2Native{}
  if err:=f2teach([]f2Observer{m},train);err!=nil{t.Fatal(err)}
  if err:=m.Freeze();err!=nil{t.Fatal(err)}
  if m.Predict(f2Context{Regime:1,Cue:0,Mode:0})!=1{
   t.Fatal("unobserved new-world oracle leaked")
  }
 }
}
