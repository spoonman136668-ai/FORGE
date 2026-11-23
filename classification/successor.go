package classification

import "github.com/spoonman136668-ai/forge/researchstate"

// SuccessorPlan is a read-only eligibility assessment for a NEW, independent
// original; it never schedules or consumes the historical original attempt.
type SuccessorPlan struct{
 Lane string
 ParentExperimentID string
 ParentClassificationSHA256 string
 Eligible bool
 Reason string
}
// AssessSuccessor requires an exact independently signed classification,
// and an already-persisted Classified journal state. Positive, negative and
// inconclusive outcomes can yield a separately qualified *new* proposal;
// INVALID is ineligible until independent provenance repair and re-review.
func AssessSuccessor(j researchstate.Journal,a Attestation,e Expected)(SuccessorPlan,error){
 hash,err:=Verify(a,e);if err!=nil{return SuccessorPlan{},err}
 phase,exists,err:=researchstate.Status(j,e.Lane,e.ExperimentID)
 if err!=nil||!exists||phase!=researchstate.Classified{return SuccessorPlan{},ErrBlocked}
 // The classification attestation must be the last transition of this exact
 // parent: reject an unrelated or unbound classification record.
 found:=false
 for i:=len(j.Entries)-1;i>=0;i--{
  v:=j.Entries[i]
  if v.Lane==e.Lane&&v.ExperimentID==e.ExperimentID{
   found=v.To==researchstate.Classified&&v.EvidenceSHA256==hash
   break
  }
 }
 if !found{return SuccessorPlan{},ErrBlocked}
 result:=SuccessorPlan{Lane:e.Lane,ParentExperimentID:e.ExperimentID,ParentClassificationSHA256:hash}
 if a.Statement.Outcome=="INVALID"{
  result.Reason="INVALID_REQUIRES_INDEPENDENT_PROVENANCE_REVIEW"
  return result,nil
 }
 result.Eligible=true
 result.Reason="ELIGIBLE_FOR_NEW_SEPARATELY_QUALIFIED_SUCCESSOR"
 return result,nil
}
