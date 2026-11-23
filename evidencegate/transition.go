package evidencegate

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// SealOriginal constructs a proposed, evidence-bound lifecycle transition for
// an existing scientific original. It does not mutate custody or issue an
// independently witnessed transaction or scientific acceptance.
func SealOriginal(j researchstate.Journal, lane,id,frozen string, m Manifest, originalPath string)(researchstate.Journal,error){
 if m.Lane!=lane||m.ExperimentID!=id||m.FrozenSHA256!=frozen{return researchstate.Journal{},ErrBlocked}
 if err:=VerifyOriginal(m,originalPath);err!=nil{return researchstate.Journal{},err}
 phase,found,err:=researchstate.Status(j,lane,id)
 if err!=nil||!found||phase!=researchstate.Executing{return researchstate.Journal{},ErrBlocked}
 head,err:=researchstate.Head(j)
 if err!=nil{return researchstate.Journal{},err}
 next,err:=researchstate.Append(j,researchstate.Event{
  Lane:lane,ExperimentID:id,FrozenSHA256:frozen,
  From:researchstate.Executing,To:researchstate.EvidenceSealed,
  EvidenceSHA256:m.OriginalSHA256,
 },head)
 if err!=nil{return researchstate.Journal{},errors.Join(ErrBlocked,err)}
 return next,nil
}

// Eligibility only describes the lifecycle's position. It is not permission
// to pick or launch a successor, nor proof of authentic scientific review.
func SuccessorEligibility(j researchstate.Journal,lane,id string)(bool,error){
 phase,found,err:=researchstate.Status(j,lane,id)
 if err!=nil{return false,err}
 return found&&phase==researchstate.SuccessorReady,nil
}
