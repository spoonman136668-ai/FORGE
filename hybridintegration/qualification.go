package hybridintegration

import (
 "strconv"

 "github.com/spoonman136668-ai/forge/hybridcustody"
 "github.com/spoonman136668-ai/forge/researchobserver"
)

// EngineeringQualifier is *caller-supplied* GitHub workflow metadata.
// Its inclusion in an offline report does not authenticate GitHub custody
// or prove scientific first-use, experimental results or runner authority.
type EngineeringQualifier struct {
 Workflow string `json:"workflow"`
 HeadSHA string `json:"head_sha"`
 RunID uint64 `json:"run_id"`
 RunAttempt uint64 `json:"run_attempt"`
 Conclusion string `json:"conclusion"`
 URL string `json:"url"`
}

// Each frozen experiment has its own admission workflow. A passing *focused*
// workflow alone cannot conceal failed mandatory G4/G5/G7 checks.
func requiredHybridWorkflows(experiment string)([]string,error){
 shared:=[]string{
  "G4 CPU qualification",
  "G5 authentic TTT CPU",
  "G7 pinned Mamba2 CPU import",
 }
 switch experiment {
 case "G7-S24":
  return append(shared,
   "G7-S24 existing-runtime Windows and WSL regression admission"),nil
 case "G7-S25":
  return append(shared,
   "G7-S25 observed primary-action surprise residual qualification"),nil
 default:return nil,ErrBlocked
 }
}

// Fail closed on missing, stale, failed, cancelled, ambiguous or duplicate
// required CI for the exact experiment source SHA. This is engineering-only.
func requireHybridEngineeringSuite(runs []researchobserver.Run,source,experiment string)([]EngineeringQualifier,error){
 needed,err:=requiredHybridWorkflows(experiment)
 if err!=nil||!validHex(source,40){return nil,ErrBlocked}
 picked:=make([]EngineeringQualifier,0,len(needed))
 seenRun:=map[uint64]bool{}
 for _,want:=range needed {
  found:=false
  for _,r:=range runs {
   if r.HeadSHA!=source||r.Workflow!=want{continue}
   // Ambiguous multiple workflow runs, including succeeded reruns, require
   // explicit exact-source reconciliation outside this disabled integration.
   if found||r.Status!="completed"||r.Conclusion!="success"||
    r.RunID==0||r.RunAttempt==0||seenRun[r.RunID]||
    r.ScientificClassification!="UNVERIFIED_NOT_A_SCIENTIFIC_RESULT"||
    r.ScientificAccepted||r.OriginalFirstUseReconciled{
    return nil,ErrBlocked
   }
   found=true
   seenRun[r.RunID]=true
   picked=append(picked,EngineeringQualifier{
    Workflow:r.Workflow,HeadSHA:r.HeadSHA,
    RunID:r.RunID,RunAttempt:r.RunAttempt,
    Conclusion:r.Conclusion,URL:r.URL,
   })
  }
  if !found{return nil,ErrBlocked}
 }
 if validateEngineeringQualifiers(picked,source,experiment)!=nil{return nil,ErrBlocked}
 return picked,nil
}
func validateEngineeringQualifiers(rows []EngineeringQualifier,source,experiment string)error{
 names,err:=requiredHybridWorkflows(experiment)
 if err!=nil||!validHex(source,40)||len(rows)!=len(names){return ErrBlocked}
 ids:=map[uint64]bool{}
 for i,r:=range rows {
  if r.Workflow!=names[i]||r.HeadSHA!=source||
   r.RunID==0||r.RunAttempt==0||ids[r.RunID]||
   r.Conclusion!="success"||
   r.URL!="https://github.com/"+hybridcustody.Project+
    "/actions/runs/"+strconv.FormatUint(r.RunID,10){
   return ErrBlocked
  }
  ids[r.RunID]=true
 }
 return nil
}
