package main

import "testing"

func TestTrueTargetTransitionFrozenRegimes(t *testing.T){
 for s:=byte(0);s<32;s++{
  if targetNext(s,false)!=((5*s+1)&31) {t.Fatal("repeatable target law changed")}
  if targetNext(s,true)!=((7*s+3)&31) {t.Fatal("shifted target law changed")}
 }
}
func TestNonparametricFitChargedAndAllStatesVisited(t *testing.T){
 w:=Worker{}
 var tab [32]byte
 var seen [32]bool
 fit(0,&tab,&seen,&w)
 if w.SourceCalls!=FitCallsPerDraftSession||w.FitCalls!=FitCallsPerDraftSession{
  t.Fatalf("FIT not charged: %+v",w)
 }
 for i,known:=range seen{if !known||tab[i]!=targetNext(byte(i),false){
  t.Fatalf("not learned from FIT state %d",i)
 }}
}
func TestVerifiedMatchesFullOnRepeatable(t *testing.T){
 f,e:=runWorker("full","repeatable",11);if e!=nil{t.Fatal(e)}
 v,e:=runWorker("verified","repeatable",11);if e!=nil{t.Fatal(e)}
 if f.TranscriptSHA256!=v.TranscriptSHA256||v.Mismatches!=0 {
  t.Fatal("wrong or inaccurate exact verified repeatable transcript")
 }
 if f.SourceCalls!=Sessions*OutputsPerSession ||
    v.SourceCalls!=Sessions*(OutputsPerSession+FitCallsPerDraftSession) ||
    v.VerificationCalls!=Sessions*OutputsPerSession||
    v.FitCalls!=Sessions*FitCallsPerDraftSession {
  t.Fatalf("scalar target verified work not paid: %+v %+v",f,v)
 }
}
func TestVerifiedRollbackOnUnseenShift(t *testing.T){
 f,e:=runWorker("full","shifted",29);if e!=nil{t.Fatal(e)}
 v,e:=runWorker("verified","shifted",29);if e!=nil{t.Fatal(e)}
 if f.TranscriptSHA256!=v.TranscriptSHA256||v.Mismatches==0{
  t.Fatal("hidden shift not recovered by mandatory exact verification")
 }
 if v.VerificationCalls!=Sessions*OutputsPerSession{
  t.Fatal("missed true target check on rollback")
 }
}
func TestUnsafeDraftFailsTrueUnseenTargetShift(t *testing.T){
 f,e:=runWorker("full","shifted",47);if e!=nil{t.Fatal(e)}
 u,e:=runWorker("unsafe","shifted",47);if e!=nil{t.Fatal(e)}
 if f.TranscriptSHA256==u.TranscriptSHA256{
  t.Fatal("unsafe speculative draft falsely correct after source-law change")
 }
 if u.VerificationCalls!=0||u.FitCalls!=Sessions*FitCallsPerDraftSession{
  t.Fatal("unsafe draft incorrectly charged as verified")
 }
}
func TestOracleIsPrivilegedAndFullTargetCorrect(t *testing.T){
 for _,r:=range Regimes {
  f,e:=runWorker("full",r,61);if e!=nil{t.Fatal(e)}
  o,e:=runWorker("oracle",r,61);if e!=nil{t.Fatal(e)}
  if f.TranscriptSHA256!=o.TranscriptSHA256||o.SourceCalls!=0{
   t.Fatal("oracle truth mismatch or fake target verification")
  }
 }
}
func TestInvalidWorkerInputFailsClosed(t *testing.T){
 for _,tc:=range []struct{arm,regime string;seed int}{
  {"not-valid","shifted",11},{"verified","not-valid",11},{"full","repeatable",-1},
 }{
  if _,e:=runWorker(tc.arm,tc.regime,tc.seed);e==nil{
   t.Fatalf("accepted unsupported or negative input: %+v",tc)
  }
 }
}
func TestPublicTraceDeterministicColdWorker(t *testing.T){
 a,e:=runWorker("verified","shifted",79);if e!=nil{t.Fatal(e)}
 b,e:=runWorker("verified","shifted",79);if e!=nil{t.Fatal(e)}
 if a.TranscriptSHA256!=b.TranscriptSHA256||
    a.SourceCalls!=b.SourceCalls||a.Mismatches!=b.Mismatches{
  t.Fatal("identical cold source-only worker changed sequence")
 }
}
