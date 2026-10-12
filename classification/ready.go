package classification

import "github.com/spoonman136668-ai/forge/researchstate"

// MarkSuccessorReady proposes a lifecycle transition only after authenticated
// independent classification and explicit eligibility. It does NOT create a
// successor experiment, worker queue item, or execution authorization.
func MarkSuccessorReady(j researchstate.Journal,a Attestation,e Expected)(researchstate.Journal,error){
 plan,err:=AssessSuccessor(j,a,e)
 if err!=nil||!plan.Eligible{return researchstate.Journal{},ErrBlocked}
 head,err:=researchstate.Head(j)
 if err!=nil{return researchstate.Journal{},err}
 next,err:=researchstate.Append(j,researchstate.Event{
  Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,
  From:researchstate.Classified,To:researchstate.SuccessorReady,
  EvidenceSHA256:plan.ParentClassificationSHA256,
 },head)
 if err!=nil{return researchstate.Journal{},ErrBlocked}
 return next,nil
}
