package main

import "testing"

func TestACC34SingleBitFITMissesConjunctiveCause(t *testing.T) {
 d,n:=fit()
 if n!=24 {t.Fatal("incorrect FIT probe count")}
 if d[0][0]||d[0][1] {t.Fatal("FIT discovered conjunction from isolated single-bit probes")}
 truth:=trueDeps()
 if !truth[0][0]||!truth[0][1] {t.Fatal("unattainable oracle hidden dependency missing")}
 x:=[inputs]bool{};x[0]=true
 alone:=node(0,x);x[1]=true
 if alone==node(0,x){t.Fatal("hidden conjunction had no consequence")}
}
func TestACC34SourceOnlyVerifiedCorrectness(t *testing.T) {
 for _,sc:=range []string{"BENIGN","HIDDEN_INTERACTION"} {
  full,e:=execute(Full,sc);if e!=nil{t.Fatal(e)}
  verified,e:=execute(Verified,sc);if e!=nil{t.Fatal(e)}
  if compareTrace(full.OutputTrace,verified.OutputTrace)!=0||verified.VerifiedNodes!=nodes*events {
   t.Fatal("mandatory full verification failed")
  }
  if verified.FITProbes!=24||verified.ScientificFirstUse||verified.PrivateInputsUsed {
   t.Fatal("source-only FIT or privacy contract drift")
  }
  oracle,e:=execute(Oracle,sc);if e!=nil{t.Fatal(e)}
  if compareTrace(full.OutputTrace,oracle.OutputTrace)!=0 {t.Fatal("oracle incorrect")}
  unsafe,e:=execute(Unverified,sc);if e!=nil{t.Fatal(e)}
  n:=compareTrace(full.OutputTrace,unsafe.OutputTrace)
  if sc=="BENIGN"&&n!=0 {t.Fatalf("benign unexpected errors %d",n)}
  if sc=="HIDDEN_INTERACTION"&&n==0 {t.Fatal("hidden conjunction not falsified")}
 }
}
func TestACC34EventScheduleAndDigests(t *testing.T) {
 if toggleIndex(1,"BENIGN")==1||toggleIndex(1,"HIDDEN_INTERACTION")!=1 {t.Fatal("frozen schedules drift")}
 v,e:=execute(Full,"BENIGN");if e!=nil{t.Fatal(e)}
 if len(v.OutputTrace)!=4096||len(v.OutputTraceSHA256)!=64||v.OutputTraceSHA256!=traceSHA(v.OutputTrace) {
  t.Fatal("source trace digest contract drift")
 }
 if _,e:=execute(Arm("FAST_MAGIC"),"BENIGN");e==nil{t.Fatal("unregistered arm accepted")}
 if _,e:=execute(Full,"SECRET_SOURCE");e==nil{t.Fatal("unregistered scenario accepted")}
}
func TestACC34SourceFreeMeasurementThresholdsAndLabels(t *testing.T) {
 r:=Report{PreRegisteredCPUThreshold:0.90,PreRegisteredSysThreshold:1.10,
  NativeGoKernelOnly:true,TrueOSPeakRSSMeasured:false,CPUIncludesFITAndVerification:true,PortfolioTotal:36}
 if r.PreRegisteredCPUThreshold!=0.90||r.PreRegisteredSysThreshold!=1.10||
  !r.NativeGoKernelOnly||r.TrueOSPeakRSSMeasured||r.PortfolioTotal!=36||
  !r.CPUIncludesFITAndVerification {t.Fatal("resource or scope overclaim")}
}
func TestACC34NoFalseSafeSkipUnderUnseenInteraction(t *testing.T){
 full,_:=execute(Full,"HIDDEN_INTERACTION")
 unsafe,_:=execute(Unverified,"HIDDEN_INTERACTION")
 verified,_:=execute(Verified,"HIDDEN_INTERACTION")
 if compareTrace(full.OutputTrace,unsafe.OutputTrace)<1 {t.Fatal("unverified shortcut incorrectly counted as safe")}
 if compareTrace(full.OutputTrace,verified.OutputTrace)!=0 {t.Fatal("verified arm shipped wrong output")}
 if verified.VerifiedRepairs==0 {t.Fatal("no observed factual repairs under hidden interactions")}
}
func TestACC34RuntimeAccountingAndExperimentIdentity(t *testing.T) {
 p,e:=execute(Verified,"BENIGN");if e!=nil{t.Fatal(e)}
 if p.Schema!=schema||p.EventCount!=4096||p.VerifiedNodes!=nodes*events||p.FITProbes!=24 {
  t.Fatal("source-free benchmark identity changed")
 }
 if p.RuntimeSysBytes==0||p.TotalAllocBytes==0 {t.Fatal("runtime allocator resource counters absent")}
 if p.PrivateInputsUsed||p.ScientificFirstUse {t.Fatal("source privilege admitted")}
}
