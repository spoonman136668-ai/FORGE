package lanecontinuity

import "testing"

func TestPairProposalNeverGrantsAdmission(t *testing.T){
 failures:=[]Failure{None,ModelQuota,ModelOffline,RunnerOffline,TestFailure,NegativeResult,EvidenceMissing,AuthorityUnavailable,UnknownStart,BudgetExhausted}
 for _,w:=range failures {for _,y:=range failures {
  a:=Input{Lane:Wingless,Failure:w,QualifiedWorkAvailable:true,QualifiedAlternativeRunner:true,RetryLimit:1}
  b:=Input{Lane:Yggdrasil,Failure:y,QualifiedWorkAvailable:true,QualifiedAlternativeRunner:true,RetryLimit:1}
  p,err:=ProposePair(a,b);if err!=nil{t.Fatal(err)}
  pair,err:=AssessPair(a,b);if err!=nil{t.Fatal(err)}
  if p.Wingless.Lane!=Wingless || p.Yggdrasil.Lane!=Yggdrasil ||
   p.Wingless.Classification!=pair.Wingless.Decision ||
   p.Yggdrasil.Classification!=pair.Yggdrasil.Decision {
   t.Fatalf("projection altered classification %s/%s %+v",w,y,p)
  }
  if p.Wingless.CanRequestIndependentAdmission != (pair.Wingless.Decision==ContinueEligible) ||
   p.Yggdrasil.CanRequestIndependentAdmission != (pair.Yggdrasil.Decision==ContinueEligible) {
   t.Fatal("request-permission drift")
  }
  if w==UnknownStart||w==AuthorityUnavailable||w==EvidenceMissing||w==BudgetExhausted {
   if p.Wingless.CanRequestIndependentAdmission {t.Fatal("unsafe Wingless request")}
  }
  if y==UnknownStart||y==AuthorityUnavailable||y==EvidenceMissing||y==BudgetExhausted {
   if p.Yggdrasil.CanRequestIndependentAdmission {t.Fatal("unsafe Yggdrasil request")}
  }
 }}
}
func TestMalformedPairDoesNotProducePartialProposal(t *testing.T){
 got,err:=ProposePair(Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true},Input{Lane:"not-a-lane",Failure:None})
 if err==nil||got!=(NextSteps{}) {t.Fatalf("fail-open proposal: %+v %v",got,err)}
}

func TestModelFreeProposalDoesNotPromoteUnqualifiedWork(t *testing.T){
 first:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:false}
 second:=Input{Lane:Yggdrasil,Failure:ModelOffline,QualifiedWorkAvailable:true}
 got,err:=ProposePair(first,second)
 if err!=nil{t.Fatal(err)}
 if got.Wingless.CanRequestIndependentAdmission || got.Wingless.Classification!=DeferModelWork {
  t.Fatalf("unqualified Wingless proposal advanced: %+v",got.Wingless)
 }
 if !got.Yggdrasil.CanRequestIndependentAdmission || got.Yggdrasil.Classification!=ContinueEligible {
  t.Fatalf("qualified Yggdrasil proposal stalled: %+v",got.Yggdrasil)
 }
}
