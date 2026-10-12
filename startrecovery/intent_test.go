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
   got,err:=ReconcileIntent(i,Observation{Intent:i,Status:tc.status,IndependentlyAuthenticated:true})
   if err!=nil||got!=tc.want{t.Fatalf("%s %s => %s %v",lane,tc.status,got,err)}
  }
 }
}
func TestUnauthenticatedOrMalformedStartCannotBeReplayed(t *testing.T){
 good:=fixedIntent()
 if got,err:=ReconcileIntent(good,Observation{Intent:good,Status:NoReservation});got!=""||!errors.Is(err,ErrInvalidIntent){
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
  if got,err:=ReconcileIntent(i,Observation{Intent:i,Status:NoReservation,IndependentlyAuthenticated:true});got!=""||!errors.Is(err,ErrInvalidIntent){
   t.Fatalf("invalid intent accepted: %+v => %s %v",i,got,err)
  }
 }
 if got,err:=ReconcileIntent(good,Observation{Intent:good,Status:"UNRECOGNIZED",IndependentlyAuthenticated:true});got!=""||!errors.Is(err,ErrInvalidIntent){
  t.Fatalf("unknown recovery state accepted: %s %v",got,err)
 }
}

func TestObservationMustBindExactIntent(t *testing.T){
 a:=fixedIntent()
 b:=a;b.ExperimentID="W002"
 obs:=Observation{Intent:a,Status:NoReservation,IndependentlyAuthenticated:true}
 if got,err:=ReconcileIntent(b,obs);got!=""||!errors.Is(err,ErrInvalidIntent){
  t.Fatalf("cross-intent status reused: %s %v",got,err)
 }
}
func TestExperimentIDMatchesJournalConstraints(t *testing.T){
 for _,id:=range []string{"W.001","W001\talias","W/001","W 001"}{
  i:=fixedIntent();i.ExperimentID=id
  got,err:=ReconcileIntent(i,Observation{Intent:i,Status:NoReservation,IndependentlyAuthenticated:true})
  if got!=""||!errors.Is(err,ErrInvalidIntent){t.Fatalf("invalid journal ID accepted: %q %s %v",id,got,err)}
 }
}

func TestGenerationAboveJournalLimitFailsClosed(t *testing.T){
 i:=fixedIntent();i.Generation=1000000001
 got,err:=ReconcileIntent(i,Observation{Intent:i,Status:NoReservation,IndependentlyAuthenticated:true})
 if got!=""||!errors.Is(err,ErrInvalidIntent){t.Fatalf("out-of-range generation accepted: %s %v",got,err)}
}
