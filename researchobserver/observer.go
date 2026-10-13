// Package researchobserver reads GitHub workflow metadata for the existing
// Wingless and Yggdrasil repositories without dispatching or classifying
// science. A green CI run is NOT a supported scientific outcome.
package researchobserver

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strconv"
 "strings"
 "time"
)
const Schema="forge.research.metadata-observation.v1"
const MaximumBytes=2<<20
const MaximumRuns=50
var ErrUnverified=errors.New("FORGE_RESEARCH_OBSERVATION_UNVERIFIED_OR_MALFORMED")
type Run struct {
 RunID uint64 `json:"run_id"`
 RunAttempt uint64 `json:"run_attempt"`
 Workflow string `json:"workflow"`
 HeadSHA string `json:"head_sha"`
 Branch string `json:"branch"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 CreatedAt string `json:"created_at"`
 URL string `json:"url"`
 ScientificClassification string `json:"scientific_classification"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OriginalFirstUseReconciled bool `json:"original_first_use_reconciled"`
}
type LaneReport struct{
 Lane string `json:"lane"`
 Repository string `json:"repository"`
 InputRawSHA256 string `json:"input_raw_sha256"`
 TotalGitHubRuns uint64 `json:"total_github_runs"`
 ObservationWindow int `json:"observation_window"`
 HistoricalCompletenessVerified bool `json:"historical_completeness_verified"`
 ScientificEvidenceAuthenticated bool `json:"scientific_evidence_authenticated"`
 Runs []Run `json:"runs"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Wingless LaneReport `json:"wingless"`
 Yggdrasil LaneReport `json:"yggdrasil"`
 ResearchOriginalsExecuted uint64 `json:"research_originals_executed"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
type rawEnvelope struct{
 TotalCount uint64 `json:"total_count"`
 WorkflowRuns []struct{
  ID uint64 `json:"id"`
  RunAttempt uint64 `json:"run_attempt"`
  Name string `json:"name"`
  HeadSHA string `json:"head_sha"`
  HeadBranch string `json:"head_branch"`
  Status string `json:"status"`
  Conclusion *string `json:"conclusion"`
  CreatedAt string `json:"created_at"`
  HTMLURL string `json:"html_url"`
  Repository struct{FullName string `json:"full_name"`} `json:"repository"`
  HeadRepository *struct{FullName string `json:"full_name"`} `json:"head_repository"`
 } `json:"workflow_runs"`
}
func validSHA(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validText(s string,max int)bool{
 if len(s)==0||len(s)>max{return false}
 for _,c:=range s{if c<32||c==127{return false}}
 return true
}
func knownStatus(s string)bool{
 switch s{
 case "queued","in_progress","pending","waiting","requested","action_required","completed":return true
 default:return false
 }
}
func knownConclusion(s string)bool{
 switch s{
 case "success","failure","cancelled","skipped","timed_out","neutral","action_required","startup_failure","stale":return true
 default:return false
 }
}
func readLane(raw []byte,lane string)(LaneReport,error){
 var empty LaneReport
 if (lane!="Wingless"&&lane!="Yggdrasil")||len(raw)==0||len(raw)>MaximumBytes{
  return empty,ErrUnverified
 }
 repo:="spoonman136668-ai/"+lane
 var body rawEnvelope
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 if err:=decoder.Decode(&body);err!=nil{return empty,ErrUnverified}
 var extra any
 if err:=decoder.Decode(&extra);err==nil{return empty,ErrUnverified}
 if len(body.WorkflowRuns)==0||len(body.WorkflowRuns)>MaximumRuns||
  body.TotalCount<uint64(len(body.WorkflowRuns)){
  return empty,ErrUnverified
 }
 sum:=sha256.Sum256(raw)
 out:=LaneReport{Lane:lane,Repository:repo,InputRawSHA256:hex.EncodeToString(sum[:]),
  TotalGitHubRuns:body.TotalCount,ObservationWindow:len(body.WorkflowRuns),
  Runs:make([]Run,0,len(body.WorkflowRuns))}
 seen:=map[string]bool{}
 for _,r:=range body.WorkflowRuns{
  if r.ID==0||r.RunAttempt==0||!validSHA(r.HeadSHA)||
   !validText(r.Name,160)||!validText(r.HeadBranch,256)||
   r.Repository.FullName!=repo||r.HeadRepository==nil||
   r.HeadRepository.FullName!=repo||!knownStatus(r.Status)||
   _,err:=time.Parse(time.RFC3339,r.CreatedAt);err!=nil{
   return empty,ErrUnverified
  }
  key:=fmt.Sprintf("%d:%d",r.ID,r.RunAttempt)
  if seen[key]{return empty,ErrUnverified}
  seen[key]=true
  wantURL:="https://github.com/"+repo+"/actions/runs/"+strconv.FormatUint(r.ID,10)
  if r.HTMLURL!=wantURL{return empty,ErrUnverified}
  conclusion:=""
  if r.Status=="completed"{
   if r.Conclusion==nil||!knownConclusion(*r.Conclusion){return empty,ErrUnverified}
   conclusion=*r.Conclusion
  }else if r.Conclusion!=nil{return empty,ErrUnverified}
  out.Runs=append(out.Runs,Run{RunID:r.ID,RunAttempt:r.RunAttempt,
   Workflow:r.Name,HeadSHA:r.HeadSHA,Branch:r.HeadBranch,Status:r.Status,
   Conclusion:conclusion,CreatedAt:r.CreatedAt,URL:r.HTMLURL,
   ScientificClassification:"UNVERIFIED_NOT_A_SCIENTIFIC_RESULT"})
 }
 return out,nil
}
func Build(wingless,yggdrasil []byte)(Report,error){
 w,err:=readLane(wingless,"Wingless")
 if err!=nil{return Report{},fmt.Errorf("%w: Wingless",ErrUnverified)}
 y,err:=readLane(yggdrasil,"Yggdrasil")
 if err!=nil{return Report{},fmt.Errorf("%w: Yggdrasil",ErrUnverified)}
 if w.InputRawSHA256==y.InputRawSHA256{
  return Report{},ErrUnverified
 }
 return Report{Schema:Schema,Mode:"READ_ONLY_GITHUB_RUN_METADATA_NOT_SCIENTIFIC_EVIDENCE",
  Wingless:w,Yggdrasil:y},nil
}
