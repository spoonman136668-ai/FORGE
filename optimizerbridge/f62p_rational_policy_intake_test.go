package optimizerbridge

import (
 "fmt"
 "reflect"
 "strings"
 "testing"
)
func f62Fixture(t *testing.T,lane int,count int) (F58Freeze,F59PolicyNomination,[]F62PTrial) {
 t.Helper()
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 n:=f61FixedNomination(t,f,lane)
 _,family,budget:=f61TestPublic()
 trials:=make([]F62PTrial,0,count)
 for i:=0;i<count;i++{
  slate:=fmt.Sprintf("%064x",i+4096)
  a,err:=PrepareF61OwnerSelection(f,n,slate,family,budget,f61DrawReader(uint64(i%6)))
  if err!=nil{t.Fatal(err)}
  trials=append(trials,F62PTrial{
   Assignment:a,OwnerDecisionSequence:uint64(i+1),
   OriginalReceiptSHA256:fmt.Sprintf("%064x",i+16384),
   Outcome:"SUPPORTED",ComputeUnits:10,
  })
 }
 return f,n,trials
}
func TestF62PExactOneSixthPolicyArmWeightsBothLanes(t *testing.T){
 for lane:=0;lane<2;lane++{
  f,n,trials:=f62Fixture(t,lane,6)
  a,err:=PreviewF62PExactPolicyArms(f,n,trials);if err!=nil{t.Fatal(err)}
  if a.ExactArmProbabilityNumerator!=1||a.ExactArmProbabilityDenominator!=6||
   a.Lane!=n.Lane||a.SourceOnlyTrialCount!=6||
   a.ResearchActionPropensityInterchangeable||
   a.IndependentOwnerWitnessAuthenticated||a.GenuineFirstUseEstablished||
   a.CausalComparisonAuthorized||a.OptimizerActivationAuthorized{
   t.Fatalf("false authority or propensity: %+v",a)
  }
  for _,arm:=range a.Arms{
   if arm.Assigned!=1||arm.Observed!=1||arm.ScoreIPSPreview!="3"||
    arm.ComputeIPSPreview!="10"||arm.ScorePerComputePreview!="3/10"{
    t.Fatalf("incorrect rational policy preview: %+v",arm)
   }
  }
  b,err:=PreviewF62PExactPolicyArms(f,n,trials)
  if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("non-deterministic preview",err)}
 }
}
func TestF62PMissingOutcomeNeverImputedOrCompared(t *testing.T){
 f,n,trials:=f62Fixture(t,0,6)
 trials[0].Outcome="MISSING"
 trials[0].ComputeUnits=0
 a,err:=PreviewF62PExactPolicyArms(f,n,trials)
 if err!=nil||a.MissingOutcomes!=1||a.CausalComparisonAuthorized{t.Fatal(err,a)}
 for _,arm:=range a.Arms{
  if arm.ScoreIPSPreview!=""||arm.ComputeIPSPreview!=""||
   arm.ScorePerComputePreview!=""{t.Fatal("partial outcome imputed")}
 }
 trials[0].ComputeUnits=10
 if _,err:=PreviewF62PExactPolicyArms(f,n,trials);err==nil{t.Fatal("missing with fabricated compute accepted")}
}
func TestF62PRejectsDuplicationIdentityDriftAndUnwitnessedAuthority(t *testing.T){
 f,n,trials:=f62Fixture(t,1,6)
 mutations:=[]struct{name string;change func([]F62PTrial)}{
  {"same assignment",func(x []F62PTrial){x[1].Assignment=x[0].Assignment}},
  {"same receipt",func(x []F62PTrial){x[1].OriginalReceiptSHA256=x[0].OriginalReceiptSHA256}},
  {"sequence rollback",func(x []F62PTrial){x[1].OwnerDecisionSequence=x[0].OwnerDecisionSequence}},
  {"tampered draw",func(x []F62PTrial){x[0].Assignment.RandomDrawHex=strings.Repeat("f",16)}},
  {"false external witness",func(x []F62PTrial){x[0].Assignment.ExternallyWitnessedPredecisionRegistration=true}},
  {"claimed first use",func(x []F62PTrial){x[0].Assignment.AtomicFirstUseClaimConsumed=true}},
  {"rounded probability",func(x []F62PTrial){x[0].Assignment.LoggedPropensityDenominator=10000}},
  {"budget drift",func(x []F62PTrial){x[0].Assignment.BudgetCommitmentSHA256=strings.Repeat("a",64)}},
  {"source family drift",func(x []F62PTrial){x[0].Assignment.PublicSourceFamilySHA256=strings.Repeat("b",64)}},
  {"noncanonical receipt",func(x []F62PTrial){x[0].OriginalReceiptSHA256="forged"}},
  {"unknown outcome",func(x []F62PTrial){x[0].Outcome="UNKNOWN"}},
  {"zero compute",func(x []F62PTrial){x[0].ComputeUnits=0}},
 }
 for _,m:=range mutations{
  copyTrials:=append([]F62PTrial(nil),trials...)
  m.change(copyTrials)
  if _,err:=PreviewF62PExactPolicyArms(f,n,copyTrials);err==nil{t.Fatalf("accepted %s",m.name)}
 }
 if _,err:=PreviewF62PExactPolicyArms(f,n,nil);err==nil{t.Fatal("accepted missing evidence")}
 if _,err:=PreviewF62PExactPolicyArms(f,n,append(trials,trials...));err==nil{t.Fatal("accepted replay or over cap")}
 _,otherNomination,_:=f62Fixture(t,0,1)
 if _,err:=PreviewF62PExactPolicyArms(f,otherNomination,trials);err==nil{t.Fatal("cross-lane pooling accepted")}
}
func TestF62PIPSIsPolicyAllocationNotResearchActionReplay(t *testing.T){
 f,n,trials:=f62Fixture(t,0,2)
 trials[0].Outcome="NEGATIVE"
 trials[1].Outcome="MIXED"
 a,err:=PreviewF62PExactPolicyArms(f,n,trials)
 if err!=nil{t.Fatal(err)}
 // IPW = 1/(1/6) = 6, per-arm over all two randomized units.
 if a.Arms[0].ScoreIPSPreview!="0"||a.Arms[1].ScoreIPSPreview!="3"||
  a.Arms[1].ScorePerComputePreview!="1/10"||a.CausalComparisonAuthorized{
  t.Fatalf("misinterpreted allocation propensity: %+v",a)
 }
}
