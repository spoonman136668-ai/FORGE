package lanecontinuity

import "testing"

func TestModelFailureCannotBlockIndependentQualifiedWork(t *testing.T){
 for _,lane:=range []Lane{Wingless,Yggdrasil}{
  for _,failure:=range []Failure{ModelQuota,ModelOffline}{
   got,err:=Classify(Input{Lane:lane,Failure:failure,QualifiedWorkAvailable:true})
   if err!=nil||got.Decision!=ContinueEligible||!got.OtherLaneUnaffected||!got.RequiresIndependentAdmission {
    t.Fatalf("%s %s: %+v %v",lane,failure,got,err)
   }
  }
 }
}
func TestSafetyAndIsolation(t *testing.T){
 table:=[]struct{name string;in Input;want Decision}{
  {"no-work",Input{Lane:Wingless,Failure:None},HoldLane},
  {"no-model-proposal",Input{Lane:Yggdrasil,Failure:ModelQuota},DeferModelWork},
  {"no-alt-runner",Input{Lane:Wingless,Failure:RunnerOffline,QualifiedWorkAvailable:true},HoldLane},
  {"qualified-alt-runner",Input{Lane:Yggdrasil,Failure:RunnerOffline,QualifiedWorkAvailable:true,QualifiedAlternativeRunner:true},ContinueEligible},
  {"no-eligible-work",Input{Lane:Wingless,Failure:RunnerOffline,QualifiedAlternativeRunner:true},HoldLane},
  {"retry-limited",Input{Lane:Wingless,Failure:TestFailure,RetryCount:1,RetryLimit:2},RetryBounded},
  {"retry-exhausted",Input{Lane:Wingless,Failure:TestFailure,RetryCount:2,RetryLimit:2},RequireQualification},
  {"negative-is-not-infra-failure",Input{Lane:Yggdrasil,Failure:NegativeResult},PreserveNegative},
  {"unknown-start",Input{Lane:Wingless,Failure:UnknownStart,QualifiedWorkAvailable:true},HoldLane},
  {"authority-unavailable",Input{Lane:Yggdrasil,Failure:AuthorityUnavailable,QualifiedWorkAvailable:true},HoldLane},
  {"missing-evidence",Input{Lane:Yggdrasil,Failure:EvidenceMissing,QualifiedWorkAvailable:true},HoldLane},
  {"budget-exhausted",Input{Lane:Wingless,Failure:BudgetExhausted,QualifiedWorkAvailable:true},HoldLane},
 }
 for _,tc:=range table {t.Run(tc.name,func(t *testing.T){
  got,err:=Classify(tc.in);if err!=nil||got.Decision!=tc.want||!got.OtherLaneUnaffected||!got.RequiresIndependentAdmission{
   t.Fatalf("got %+v err %v want %s",got,err,tc.want)
  }
 })}
}
func TestMalformedClassificationFailsClosed(t *testing.T){
 cases:=[]Input{
  {Lane:"UNKNOWN",Failure:ModelQuota,QualifiedWorkAvailable:true},
  {Lane:Wingless,Failure:"",QualifiedWorkAvailable:true},
  {Lane:Yggdrasil,Failure:"OTHER",QualifiedWorkAvailable:true},
  {Lane:Wingless,Failure:None,RetryLimit:4},
  {Lane:Wingless,Failure:TestFailure,RetryLimit:1,RetryCount:2},
 }
 for _,in:=range cases{
  out,err:=Classify(in)
  if err==nil||out!= (Output{}){t.Fatalf("fail-open: %+v -> %+v, %v",in,out,err)}
 }
}
