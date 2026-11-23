package optimizerstages

import (
 "errors"
 "fmt"
 "math"
 "strings"
 "testing"
)

type f91MockVerifier struct{ deny bool;calls int }
func (v *f91MockVerifier) VerifyIndependentProspectiveCohort(
 f FrozenSixPolicyTrial,rows []F90Observation,p F91ExternalPin)error{
 v.calls++
 if v.deny||p.Lane!=f.Lane||p.CohortSHA256!=f91CohortSHA(rows){
  return errors.New("external verification denied")
 }
 return nil
}
func f91TestPins(w FrozenSixPolicyTrial,wr []F90Observation,y FrozenSixPolicyTrial,yr []F90Observation)[]F91ExternalPin{
 return []F91ExternalPin{
  {Lane:w.Lane,FrozenDesignSHA256:F89FreezeDigest(w),
   CohortSHA256:f91CohortSHA(wr),
   OwnerLedgerSHA256:strings.Repeat("a",64),
   WitnessArchiveSHA256:strings.Repeat("b",64),
   PreregistrationArchiveSHA256:strings.Repeat("c",64)},
  {Lane:y.Lane,FrozenDesignSHA256:F89FreezeDigest(y),
   CohortSHA256:f91CohortSHA(yr),
   OwnerLedgerSHA256:strings.Repeat("d",64),
   WitnessArchiveSHA256:strings.Repeat("e",64),
   PreregistrationArchiveSHA256:strings.Repeat("f",64)},
 }
}
func f91Fixture(t *testing.T)(
 FrozenSixPolicyTrial,[]F90Observation,FrozenSixPolicyTrial,[]F90Observation){
 t.Helper()
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 return w,f90SyntheticRows(t,w,11,0,6),y,f90SyntheticRows(t,y,12,6,6)
}
func assertF91NeverPromotes(t *testing.T,got F91Review){
 t.Helper()
 if got.IndependentProspectiveSourceQualified||
  got.IndependentlyWitnessedPreOutcomeFirstUse||
  got.RealRandomizationAndCompletePopulationProven||
  got.ScientificCausalImprovementEstablished||
  got.DreamRSIPromotionAuthorized||got.ParetoPromotionAuthorized||
  got.ThetaEvolveAcceptedOutcomeTrainingAllowed||
  got.ScientificOriginalDispatchAuthorized||got.AcceptedReferenceMutation{
  t.Fatalf("synthetic or caller-supplied evidence claimed real science: %+v",got)
 }
}
func TestF91FrozenSixArmExactSourceContrasts(t *testing.T){
 w,wr,y,yr:=f91Fixture(t)
 got,err:=ReviewF91(w,wr,y,yr,nil,nil)
 if err!=nil{t.Fatal(err)}
 assertF91NeverPromotes(t,got)
 if got.Status!=F91StatusUnverified||!got.SourceCryptographyConsistent||
  got.ReportedExternalSourceVerifierAccepted||got.ConditionalComparisonCount!=16||
  got.ConditionalFamilywiseAlpha!=0.05||len(got.Lanes)!=2{
  t.Fatalf("unsafe source review %+v",got)
 }
 for _,lane:=range got.Lanes{
  if lane.MissingOutcomes!=0||!lane.EveryPolicyArmObserved||
   lane.ReportedSourceVerifierAccepted||len(lane.Comparisons)!=8{
   t.Fatalf("incomplete six-arm source review %+v",lane)
  }
  for k,contrast:=range lane.Comparisons{
   candidate:=4+k/4;control:=k%4
   want:=fmt.Sprint(candidate-control)
   if contrast.ExactIPSScoreDifference!=want||
    contrast.ExactIPSComputeDifference!=want||
    !contrast.PositivePointEstimate||
    contrast.ConditionalFamilywiseLowerAboveZero||
    contrast.ConditionalLowerScoreDifference>=0||
    contrast.ConditionalUpperScoreDifference<=0{
    t.Fatalf("false causal comparison %+v",contrast)
   }
  }
 }
 radius:=f91ConditionalRadius(6)
 want:=1200*math.Sqrt(math.Log(320)/(12))
 if math.Abs(radius-want)>1e-9 || radius<100{
  t.Fatalf("conditional uncertainty improperly tightened %v",radius)
 }
}
func TestF91MissingOutcomeAndArmCoverageNeverImputed(t *testing.T){
 w,wr,y,yr:=f91Fixture(t)
 yr[3].Classification="MISSING";yr[3].Score=0;yr[3].ComputeUnits=0
 got,err:=ReviewF91(w,wr,y,yr,nil,nil)
 if err!=nil{t.Fatal(err)}
 assertF91NeverPromotes(t,got)
 if got.Status!=F91StatusIncomplete||
  got.Lanes[1].MissingOutcomes!=1||
  len(got.Lanes[1].Comparisons)!=0{
  t.Fatalf("missing outcomes generated partial estimator %+v",got)
 }
 w2,wr2,y2,yr2:=f91Fixture(t)
 got,err=ReviewF91(w2,wr2[:3],y2,yr2,nil,nil)
 if err!=nil{t.Fatal(err)}
 if got.Status!=F91StatusIncomplete||
  got.Lanes[0].EveryPolicyArmObserved||
  len(got.Lanes[0].Comparisons)!=0{
  t.Fatalf("unobserved policy arm accepted %+v",got)
 }
 assertF91NeverPromotes(t,got)
}
func TestF91ProviderClaimsNotOwnerAuthority(t *testing.T){
 w,wr,y,yr:=f91Fixture(t)
 pins:=f91TestPins(w,wr,y,yr)
 v:=&f91MockVerifier{}
 got,err:=ReviewF91(w,wr,y,yr,pins,v)
 if err!=nil||v.calls!=2||got.Status!=F91StatusProvider||
  !got.ReportedExternalSourceVerifierAccepted||
  !got.Lanes[0].ReportedSourceVerifierAccepted||
  !got.Lanes[1].ReportedSourceVerifierAccepted{
  t.Fatalf("source verifier interface failed %+v %v",got,err)
 }
 // The provider could be a test mock or caller-controlled: its nil result
 // cannot convert an observed point estimate into an accepted science win.
 assertF91NeverPromotes(t,got)
}
func TestF91FalsifiedAndReusedExternalPinsFailClosed(t *testing.T){
 w,wr,y,yr:=f91Fixture(t)
 base:=f91TestPins(w,wr,y,yr)
 changes:=map[string]func([]F91ExternalPin){
  "wrong lane":func(p []F91ExternalPin){p[0].Lane="Yggdrasil"},
  "drifted freeze":func(p []F91ExternalPin){p[0].FrozenDesignSHA256=strings.Repeat("0",64)},
  "drifted cohort":func(p []F91ExternalPin){p[0].CohortSHA256=strings.Repeat("1",64)},
  "missing owner ledger":func(p []F91ExternalPin){p[0].OwnerLedgerSHA256=""},
  "reused witness":func(p []F91ExternalPin){p[1].WitnessArchiveSHA256=p[0].WitnessArchiveSHA256},
  "reused owner ledger":func(p []F91ExternalPin){p[1].OwnerLedgerSHA256=p[0].OwnerLedgerSHA256},
  "same admission as cohort":func(p []F91ExternalPin){p[0].OwnerLedgerSHA256=p[0].CohortSHA256},
  "same prereg as witness":func(p []F91ExternalPin){p[1].PreregistrationArchiveSHA256=p[1].WitnessArchiveSHA256},
 }
 for name,fn:=range changes{
  t.Run(name,func(t *testing.T){
   pp:=append([]F91ExternalPin(nil),base...);fn(pp)
   if _,err:=ReviewF91(w,wr,y,yr,pp,&f91MockVerifier{});!errors.Is(err,ErrF91){
    t.Fatalf("untrusted source pin admitted %v",err)
   }
  })
 }
 if _,err:=ReviewF91(w,wr,y,yr,base,nil);!errors.Is(err,ErrF91){t.Fatal("unverified pins accepted")}
 if _,err:=ReviewF91(w,wr,y,yr,nil,&f91MockVerifier{});!errors.Is(err,ErrF91){t.Fatal("verifier without pins accepted")}
 if _,err:=ReviewF91(w,wr,y,yr,base[:1],&f91MockVerifier{});!errors.Is(err,ErrF91){t.Fatal("single lane pins accepted")}
 if _,err:=ReviewF91(w,wr,y,yr,base,&f91MockVerifier{deny:true});!errors.Is(err,ErrF91){t.Fatal("provider denial bypassed")}
}
func TestF91SourceTamperingAndCrossLaneReuseDenied(t *testing.T){
 w,wr,y,yr:=f91Fixture(t)
 altered:=append([]F90Observation(nil),wr...)
 altered[1].Score=99 // score is outside the signed *predecision* claim,
 // but it must still be tied to a separately pinned cohort digest.
 pins:=f91TestPins(w,wr,y,yr)
 if _,err:=ReviewF91(w,altered,y,yr,pins,&f91MockVerifier{});!errors.Is(err,ErrF91){
  t.Fatal("changed outcome permitted against frozen external cohort digest")
 }
 tampered:=append([]F90Observation(nil),wr...)
 tampered[1].Witness.SignatureHex=strings.Repeat("f",128)
 if _,err:=ReviewF91(w,tampered,y,yr,nil,nil);!errors.Is(err,ErrF91){
  t.Fatal("tampered owner signature admitted")
 }
 reused:=f90SyntheticRows(t,y,12,0,6)
 if _,err:=ReviewF91(w,wr,y,reused,nil,nil);!errors.Is(err,ErrF91){
  t.Fatal("cross-lane same randomized draw permitted")
 }
}
func TestF91LargeConditionalBoundDeclinesWithoutRealEvidence(t *testing.T){
 for _,n:=range []int{6,64,128,1024,4096}{
  b:=f91ConditionalRadius(n)
  if math.IsNaN(b)||math.IsInf(b,0)||b<=0{t.Fatalf("bad radius n=%d: %v",n,b)}
  if n>6 && b>=f91ConditionalRadius(6){t.Fatalf("bound did not narrow n=%d",n)}
 }
}
