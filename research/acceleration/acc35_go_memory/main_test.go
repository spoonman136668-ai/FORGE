package main
import (
 "encoding/json"
 "testing"
)
func TestFrozenSourceFreeEventCountAndRealDelayedContradictions(t *testing.T){
 if Identities!=256||Rounds!=16||Events!=4096||Sessions!=16||Repetitions!=5{
  t.Fatal("ACC35 preregistered timeline/resource dimensions changed")
 }
 conflicts:=0
 for id:=0;id<Identities;id++{
  initial:=event(id,0,"delayed_counterexample")
  early:=event(id,7,"delayed_counterexample")
  if initial.Observation!=early.Observation{t.Fatal("early family drift")}
  delayed:=event(id,8,"delayed_counterexample")
  stable:=event(id,8,"nonconflicting")
  if delayed.Outcome!=stable.Outcome{conflicts++}
 }
 if conflicts==0||conflicts>=Identities{t.Fatal("source-constructed delayed counterexample not tested")}
}
func TestFullDictionaryAndReversibleColdReplayAllScenarios(t *testing.T){
 for _,scenario:=range scenarios{
  for _,mode:=range []string{"raw","dict","fusion"}{
   exact,cold,wrong,exceptions,bytes,trace,e:=once(mode,scenario)
   if e!=nil||!exact||!cold||wrong!=0||bytes<=0||len(trace)!=64{
    t.Fatalf("original equality mode=%s scenario=%s exact=%t cold=%t wrong=%d exceptions=%d bytes=%d err=%v",mode,scenario,exact,cold,wrong,exceptions,bytes,e)
   }
   if mode=="fusion"&&scenario=="delayed_counterexample"&&exceptions==0{
    t.Fatal("reversible grouping failed to split contradictory public identities")
   }
  }
 }
}
func TestUnsafeEarlyFusionActuallyLosesLaterCounterexamples(t *testing.T){
 benign,_,missed,_,_,_,e:=once("lossy","nonconflicting")
 if e!=nil||!benign||missed!=0{t.Fatal("benign source should not diverge")}
 exact,cold,wrong,_,_,_,e:=once("lossy","delayed_counterexample")
 if e!=nil||exact||cold||wrong==0{
  t.Fatalf("lossy source incorrectly qualifies delayed exactness: %t %t %d %v",exact,cold,wrong,e)
 }
}
func TestPublicStreamingRejectsIdentityDriftAndNoInventedMissingEvents(t *testing.T){
 m,e:=New("fusion");if e!=nil{t.Fatal(e)}
 first:=event(0,0,"delayed_counterexample")
 first.ID=1
 if m.Push(first)==nil{t.Fatal("forged timeline ID accepted")}
 first.ID=0
 if e=m.Push(first);e!=nil{t.Fatal(e)}
 if e=m.Push(first);e==nil{t.Fatal("duplicate public selected episode accepted")}
 if m.size()!=1{t.Fatal("bad event mutated actor state")}
 if _,e:=New("magic");e==nil{t.Fatal("unregistered source control accepted")}
}
func TestNativeGoSnapshotDetectsCorruptionAndRetainsFullPublicHistory(t *testing.T){
 m,e:=New("fusion");if e!=nil{t.Fatal(e)}
 for i:=0;i<Events;i++{
  if e=m.Push(event(i%Identities,i/Identities,"delayed_counterexample"));e!=nil{t.Fatal(e)}
 }
 bytes:=m.Snapshot()
 restored,e:=Restore(bytes);if e!=nil{t.Fatal(e)}
 if string(restored.Snapshot())!=string(bytes){t.Fatal("cold restore drift")}
 var env map[string]any
 if e=json.Unmarshal(bytes,&env);e!=nil{t.Fatal(e)}
 state:=env["state"].(map[string]any)
 state["mode"]="lossy"
 corrupted,e:=json.Marshal(env);if e!=nil{t.Fatal(e)}
 if _,e=Restore(corrupted);e==nil{t.Fatal("forged state accepted")}
 if _,e=Restore(append(append([]byte{},bytes...),byte('0')));e==nil{
  t.Fatal("noncanonical trailing content accepted")
 }
}
func TestNewNativeGoBatchActuallyChargesSixteenColdHistories(t *testing.T){
 f,e:=worker("fusion","delayed_counterexample");if e!=nil{t.Fatal(e)}
 raw,e:=worker("raw","delayed_counterexample");if e!=nil{t.Fatal(e)}
 loss,e:=worker("lossy","delayed_counterexample");if e!=nil{t.Fatal(e)}
 if f.TotalEvents!=4096*16||f.Sessions!=16||f.OriginalSourceEpisodes!=0||f.ScientificFirstUse{
  t.Fatal("cold history, source scope or qualification falsely attributed")
 }
 if !f.CheckedReplayExact||!f.ColdRestoreExact||f.TraceSHA!=raw.TraceSHA||
   loss.WrongReplayedOutcomes==0||f.DelayedExceptionCount==0{
  t.Fatal("full non-oracle causal memory replay evidence missing")
 }
}
