package startrecovery

import (
 "errors"
 "strings"
 "testing"
)

func fixedIntent()Intent{
 return Intent{Lane:"Wingless",ExperimentID:"W001",
  FrozenSHA256:strings.Repeat("a",64),SourceSHA:strings.Repeat("b",40),
  CohortSHA256:strings.Repeat("c",64),NonceSHA256:strings.Repeat("d",64),
  Generation:7}
}
func TestStartIntentNoReplayAcrossCrashStates(t *testing.T){
 base:=fixedIntent()
 cases:=[]struct{status Status;want Recovery}{
  {NoReservation,RequestIndependentReservation},
  {Reserved,HoldNoReplay},
  {Dispatched,HoldNoReplay},
  {Completed,HoldNoReplay},
  {Uncertain,HoldNoReplay},
 }
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  for _,tc:=range cases{
   i:=base;i.Lane=lane
   got,err:=ReconcileIntent(i,tc.status,true)
   if err!=nil||got!=tc.want{t.Fatalf("%s %s => %s %v",lane,tc.status,got,err)}
  }
 }
}
func TestUnauthenticatedOrMalformedStartCannotBeReplayed(t *testing.T){
 good:=fixedIntent()
 if got,err:=ReconcileIntent(good,NoReservation,false);got!=""||!errors.Is(err,ErrInvalidIntent){
  t.Fatalf("unauthenticated status accepted: %s %v",got,err)
 }
 for _,mutate:=range []func(*Intent){
  func(i *Intent){i.Lane="OTHER"},
  func(i *Intent){i.ExperimentID="../escape"},
  func(i *Intent){i.FrozenSHA256=""},
  func(i *Intent){i.SourceSHA=""},
  func(i *Intent){i.CohortSHA256=""},
  func(i *Intent){i.NonceSHA256=""},
  func(i *Intent){i.Generation=0},
 }{
  i:=good;mutate(&i)
  if got,err:=ReconcileIntent(i,NoReservation,true);got!=""||!errors.Is(err,ErrInvalidIntent){
   t.Fatalf("invalid intent accepted: %+v => %s %v",i,got,err)
  }
 }
 if got,err:=ReconcileIntent(good,"UNRECOGNIZED",true);got!=""||!errors.Is(err,ErrInvalidIntent){
  t.Fatalf("unknown recovery state accepted: %s %v",got,err)
 }
}
