package main

import "testing"

func TestFrozenNativeGoProbeDimensionsAndFIT(t *testing.T){
 if InputBits!=24||Nodes!=32||Rounds!=96||Events!=4096{t.Fatal("registered microkernel drift")}
 deps,n:=inferSingleBitFromFIT()
 if n!=24{t.Fatal("FIT discovery not fully charged")}
 if deps[0][0]||deps[1][0]{t.Fatal("hidden interaction leaked from single-bit FIT")}
 for node:=0;node<Nodes;node++{
  if !deps[primary(node)][node]||!deps[secondary(node)][node]{
   t.Fatalf("known FIT output dependency not learned at node %d",node)
  }
 }
}
func TestNativeGoFullAndGuardedTraceParitiesBothContexts(t *testing.T){
 for _,scenario:=range []string{"benign","hidden"}{
  full,e:=worker("full",scenario,Events);if e!=nil{t.Fatal(e)}
  guarded,e:=worker("verified",scenario,Events);if e!=nil{t.Fatal(e)}
  oracle,e:=worker("oracle",scenario,Events);if e!=nil{t.Fatal(e)}
  if guarded.OutputDigest!=full.OutputDigest||oracle.OutputDigest!=full.OutputDigest{
   t.Fatalf("safe/source-privileged equality failed on %s",scenario)
  }
  if guarded.FitInterventionProbes!=InputBits||guarded.VerificationFullNodeCalls!=Events*Nodes{
   t.Fatal("verification or FIT cost not charged")
  }
  if full.FitInterventionProbes!=0||oracle.FitInterventionProbes!=0{
   t.Fatal("baseline incorrectly charged FIT")
  }
 }
}
func TestHiddenConjunctionFalsifiesUnverifiedTraining(t *testing.T){
 full,e:=worker("full","hidden",Events);if e!=nil{t.Fatal(e)}
 unsafe,e:=worker("unverified","hidden",Events);if e!=nil{t.Fatal(e)}
 verified,e:=worker("verified","hidden",Events);if e!=nil{t.Fatal(e)}
 if unsafe.OutputDigest==full.OutputDigest{
  t.Fatal("missing hidden causal interaction was not detected")
 }
 if verified.OutputDigest!=full.OutputDigest||verified.CorrectedCacheMismatches==0{
  t.Fatal("guarded correction didn't pay for hidden causal interaction")
 }
}
func TestBenignNativeGoDoesNotInventCauseErrors(t *testing.T){
 base,e:=worker("full","benign",Events);if e!=nil{t.Fatal(e)}
 unsafe,e:=worker("unverified","benign",Events);if e!=nil{t.Fatal(e)}
 if base.OutputDigest!=unsafe.OutputDigest{
  t.Fatal("benign source-only trace mismatch unexpectedly")
 }
 if unsafe.VerificationFullNodeCalls!=0{
  t.Fatal("unsafe arm falsely claims verification cost")
 }
}
func TestEventScheduleSeparatesBenignAndHidden(t *testing.T){
 for _,scenario:=range []string{"benign","hidden"}{
  var b Bits
  conjunction:=0
  for i:=0;i<Events;i++{
   change(&b,i,scenario)
   if b[0]==1&&b[1]==1{conjunction++}
  }
  if scenario=="benign"&&conjunction!=0{t.Fatal("benign environment exposed hidden pair")}
  if scenario=="hidden"&&conjunction==0{t.Fatal("hidden-world test missed conjunction")}
 }
}
func TestFailClosedUnregisteredModeAndNoScientificResult(t *testing.T){
 if _,e:=worker("unknown","benign",Events);e==nil{t.Fatal("unregistered mode accepted")}
 if _,e:=worker("verified","source_oracle",Events);e==nil{t.Fatal("unregistered context accepted")}
 if _,e:=worker("verified","hidden",Events-1);e==nil{t.Fatal("posthoc event count accepted")}
 if Schema!="forge.acc34.acd1.real-go-kernel-resource.v1"{
  t.Fatal("scope drift")
 }
}

func TestNewMeterVersionChargesAll32ColdFITAndGuards(t *testing.T){
 safe,e:=workerBatch("verified","hidden");if e!=nil{t.Fatal(e)}
 full,e:=workerBatch("full","hidden");if e!=nil{t.Fatal(e)}
 unsafe,e:=workerBatch("unverified","hidden");if e!=nil{t.Fatal(e)}
 if safe.Events!=Events*BatchSessions||safe.FitInterventionProbes!=InputBits*BatchSessions{
  t.Fatal("batched worker concealed cold events or FIT cost")
 }
 if safe.VerificationFullNodeCalls!=Events*Nodes*BatchSessions{
  t.Fatal("batched worker concealed expensive validation cost")
 }
 if safe.OutputDigest!=full.OutputDigest||unsafe.OutputDigest==full.OutputDigest{
  t.Fatal("source-free bounded real Go cold ensemble lost safety falsification")
 }
 if safe.CorrectedCacheMismatches==0{
  t.Fatal("hidden conjunction no longer exposes FIT-undercoverage")
 }
}
