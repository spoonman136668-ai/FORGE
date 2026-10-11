package evoportfolio

import "errors"

// ProgressState is a source-pinned R196 semantic fixture, not an authority.
type ProgressState struct {
 Status string
 Classification string
}
func R196Disposition(states []ProgressState)(string,error){
 if len(states)==0||len(states)>5{return "",ErrFrozen}
 for _,s:=range states{
  switch s.Status{
  case "PLANNED","QUALIFIED","BLOCKED","RUNNING":
   if s.Classification!=""{return "",ErrFrozen}
  case "CLASSIFIED":
   if s.Classification!="SUPPORTED"&&s.Classification!="MIXED"&&s.Classification!="NEGATIVE"&&s.Classification!="INVALID"{return "",ErrFrozen}
  default:return "",ErrFrozen
  }
  if s.Status=="CLASSIFIED"&&(s.Classification=="SUPPORTED"||s.Classification=="MIXED"||s.Classification=="NEGATIVE"){continue}
  switch s.Status{
  case "PLANNED":return "AWAITING_INDEPENDENT_CANDIDATE_QUALIFICATION",nil
  case "BLOCKED":return "AWAITING_BOUNDED_INFRASTRUCTURE_REQUALIFICATION",nil
  case "RUNNING":return "EXISTING_SCIENTIFIC_RUN_ACTIVE",nil
  case "CLASSIFIED":return "INVALID_RESULT_REQUIRES_EXISTING_CKB_RECOVERY",nil
  case "QUALIFIED":return "AWAITING_INDEPENDENT_SCIENCE_QUALIFICATION",nil
  }
 }
 return "REQUEST_NEW_FROZEN_SCREEN_GENERATION",nil
}
// Qualified with admitted source requires the separate CKB authority
// and cannot be inferred by this fixture.
var ErrIndependentGate=errors.New("R196_INDEPENDENT_GATE_REQUIRED")
