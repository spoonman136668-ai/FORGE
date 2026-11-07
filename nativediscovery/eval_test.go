package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"
)
// Engineering PASS and scientific benefit are separate. Keep development
// negatives and never assert acceptance merely because the harness executes.
func TestFrozenActionConsequenceDevelopment(t *testing.T){
 got,err:=RunDevelopment()
 if err!=nil{t.Fatal(err)}
 if got.Schema!=ReportSchema||got.ScientificAccepted||got.ScientificFirstUse||
  got.GeneralRSIProven||got.ModelCalls!=0||got.PaidAPICalls!=0||
  got.ActiveControllerWrites!=0||got.TrainingRounds!=TrainRounds||
  got.InterferenceRounds!=InterferenceRounds||
  got.FrozenRequiredGainPP!=FrozenMinGainPP||
  got.FrozenMaxForgettingPP!=FrozenMaxForgettingPP||
  got.Seeds!=Seeds||len(got.PerSeed)!=3||!got.SyntheticWorld{
  t.Fatalf("source-only protocol or authority drift %+v",got)
 }
 for i,row:=range got.PerSeed{
  if row.Seed!=Seeds[i]||row.TrainingTransitions!=90||
   row.TransferDecisions!=36||
   row.ColdRestoreAccuracy!=row.RelationalAccuracy||
   row.FreshAccuracy>=row.RelationalAccuracy||
   row.ShuffledFeedbackAccuracy>=row.RelationalAccuracy||
   row.ColdSnapshotBytes<20||row.ColdSnapshotBytes>20000{
   t.Fatalf("consequence learning/cold/negative controls failed %+v",row)
  }
  if row.FactorTableAccuracy<row.RelationalAccuracy{
   t.Fatalf("strongest conventional comparator weakened %+v",row)
  }
 }
 receipt,err:=json.Marshal(got);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_NATIVE_DISCOVERY_F0=%s",receipt)
}
func TestNativeConsequenceAndColdBoundaries(t *testing.T){
 o:=Observation{Object:"train-unit",Cue:"amber",Mode:"north",Level:3}
 m:=newAssoc()
 if err:=m.Observe(Transition{Observation:o,Action:0,NextLevel:8});err==nil{
  t.Fatal("unbounded transition admitted")
 }
 if err:=m.Observe(Transition{});err==nil{
  t.Fatal("unobserved context admitted")
 }
 if _,err:=restoreAssoc([]byte(`{"counts":{}}`));err==nil{
  t.Fatal("missing evidence admitted as learning")
 }
 if err:=m.Observe(outcome(o,0,0));err!=nil{t.Fatal(err)}
 if err:=m.Freeze();err!=nil{t.Fatal(err)}
 snap,err:=m.Snapshot();if err!=nil{t.Fatal(err)}
 cold,err:=restoreAssoc(snap);if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(m.Counts,cold.Counts)||m.Predict(o,0)!=cold.Predict(o,0){
  t.Fatal("cold restoration changed learned effects")
 }
 unseen:=o;unseen.Object="hold-new"
 if m.Predict(unseen,0)!=1{
  t.Fatal("unseen object cannot reuse learned action consequence")
 }
 tab:=newTable(true)
 if err:=tab.Observe(outcome(o,0,0));err!=nil{t.Fatal(err)}
 if tab.Predict(unseen,0)!=0{
  t.Fatal("object-conditioned control leaked an unseen identity")
 }
}
func TestNativeSnapshotAdversarialControls(t *testing.T){
 invalid:=[][]byte{
  nil,
  []byte("{"counts":{"unknown-north-a0":[1,0,0]}}"),
  []byte("{"counts":{"amber-north-a0":[-1,2,0]}}"),
  []byte("{"counts":{"amber-north-a0":[0,0,0]}}"),
  []byte("{"counts":{"amber-north-a0":[10000,0,0]}}"),
 }
 for _,raw:=range invalid{
  if _,err:=restoreAssoc(raw);err==nil{
   t.Fatalf("untrusted snapshot accepted: %q",raw)
  }
 }
}
