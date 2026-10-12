package lanecontinuity

import "errors"

var ErrDuplicateLane = errors.New("FORGE_LANE_CONTINUITY_DUPLICATE_LANE")

// Batch is an immutable, non-authorizing two-lane scheduling assessment.
// Input order cannot affect lane assignment or accidentally overwrite a lane.
type Batch struct {
 Wingless Output
 Yggdrasil Output
}

// AssessPair classifies each lane independently. An invalid input causes the
// entire assessment to fail closed; neither decision dispatches experiments.
// This function intentionally has no queue, network, model or write access.
func AssessPair(first,second Input)(Batch,error){
 if first.Lane==second.Lane{return Batch{},ErrDuplicateLane}
 if !((first.Lane==Wingless&&second.Lane==Yggdrasil)||(first.Lane==Yggdrasil&&second.Lane==Wingless)){
  return Batch{},ErrInvalidInput
 }
 a,err:=Classify(first);if err!=nil{return Batch{},err}
 b,err:=Classify(second);if err!=nil{return Batch{},err}
 out:=Batch{}
 if first.Lane==Wingless {out.Wingless=a;out.Yggdrasil=b}else{out.Wingless=b;out.Yggdrasil=a}
 return out,nil
}
