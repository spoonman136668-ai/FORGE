package lanecontinuity

// NextSteps is a model-free, read-only projection of classification into
// operator-visible work categories. It has no queue, API, credentials,
// admission token, executable command, or experiment start capability.
type NextSteps struct {
 Wingless Step
 Yggdrasil Step
}
type Step struct {
 Lane Lane
 Classification Decision
 CanRequestIndependentAdmission bool
}

// ProposePair never declares work runnable. A separate, independently
// authenticated FSA admission protocol must decide eligibility and start.
// In particular, RETRY_BOUNDED and CONTINUE_ELIGIBLE are not permissions.
func ProposePair(first,second Input)(NextSteps,error){
 batch,err:=AssessPair(first,second)
 if err!=nil{return NextSteps{},err}
 step:=func(out Output)Step{
  return Step{
   Lane:out.Lane,
   Classification:out.Decision,
   CanRequestIndependentAdmission:out.Decision==ContinueEligible,
  }
 }
 return NextSteps{Wingless:step(batch.Wingless),Yggdrasil:step(batch.Yggdrasil)},nil
}
