package lanecontinuity

import (
 "errors"
 "testing"
)

func TestIndependentPairedProgression(t *testing.T){
 a:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true}
 b:=Input{Lane:Yggdrasil,Failure:UnknownStart,QualifiedWorkAvailable:true}
 forward,err:=AssessPair(a,b);if err!=nil{t.Fatal(err)}
 reverse,err:=AssessPair(b,a);if err!=nil{t.Fatal(err)}
 if forward!=reverse {t.Fatalf("input order drift: %+v != %+v",forward,reverse)}
 if forward.Wingless.Decision!=ContinueEligible||forward.Yggdrasil.Decision!=HoldLane{
  t.Fatalf("independent lane isolation failed: %+v",forward)
 }
 if !forward.Wingless.RequiresIndependentAdmission||!forward.Yggdrasil.RequiresIndependentAdmission {
  t.Fatal("paired classification accidentally granted admission")
 }
}
func TestPairFailClosedOnMalformedOrDuplicateInput(t *testing.T){
 valid:=Input{Lane:Wingless,Failure:None,QualifiedWorkAvailable:true}
 cases:=[]struct{in Input;want error}{
  {Input{Lane:Wingless,Failure:None},ErrDuplicateLane},
  {Input{Lane:"Other",Failure:None},ErrInvalidInput},
  {Input{Lane:Yggdrasil,Failure:"UNKNOWN"},ErrInvalidInput},
  {Input{Lane:Yggdrasil,Failure:None,RetryLimit:4},ErrInvalidInput},
 }
 for _,tc:=range cases{
  out,err:=AssessPair(valid,tc.in)
  if !errors.Is(err,tc.want)||out!=(Batch{}) {t.Fatalf("invalid pair accepted: %+v -> %+v %v",tc.in,out,err)}
 }
}
func TestCrossLaneAdversarialExhaustive(t *testing.T){
 failures:=[]Failure{None,ModelQuota,ModelOffline,RunnerOffline,TestFailure,NegativeResult,EvidenceMissing,AuthorityUnavailable,UnknownStart,BudgetExhausted}
 for _,left:=range failures {for _,right:=range failures {
  w:=Input{Lane:Wingless,Failure:left,QualifiedWorkAvailable:true,QualifiedAlternativeRunner:true,RetryLimit:1}
  y:=Input{Lane:Yggdrasil,Failure:right,QualifiedWorkAvailable:true,QualifiedAlternativeRunner:true,RetryLimit:1}
  out,err:=AssessPair(w,y);if err!=nil{t.Fatal(err)}
  standaloneW,err:=Classify(w);if err!=nil{t.Fatal(err)}
  standaloneY,err:=Classify(y);if err!=nil{t.Fatal(err)}
  if out.Wingless!=standaloneW||out.Yggdrasil!=standaloneY {
   t.Fatalf("cross-lane contamination %s/%s: %+v",left,right,out)
  }
 }}
}

func TestPairRejectsInvalidSecondWithoutPartialFirst(t *testing.T){
 first:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true}
 second:=Input{Lane:Yggdrasil,Failure:AuthorityUnavailable,RetryCount:2,RetryLimit:1}
 out,err:=AssessPair(first,second)
 if !errors.Is(err,ErrInvalidInput)||out!=(Batch{}){
  t.Fatalf("partial lane progression on invalid paired evidence: %+v %v",out,err)
 }
}
