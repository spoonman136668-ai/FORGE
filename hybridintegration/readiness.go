package hybridintegration

// The readiness reporter is advisory-only: it explains why an independently
// supplied Hybrid CI observation is blocked without dropping negative runs.
// It never authorizes training, first use, accepted refs or runner dispatch.
import (
 "sort"
 "strconv"

 "github.com/spoonman136668-ai/forge/hybridcustody"
 "github.com/spoonman136668-ai/forge/researchobserver"
)

const ReadinessSchema="forge.hybrid.offline-readiness.v1"
const ReadinessMode="UNAUTHENTICATED_CI_OBSERVATION_ONLY_NO_EXECUTION"

type CheckRun struct{
 RunID uint64 `json:"run_id"`
 RunAttempt uint64 `json:"run_attempt"`
 Conclusion string `json:"conclusion"`
 Status string `json:"status"`
 URL string `json:"url"`
}
type WorkflowCheck struct{
 Workflow string `json:"workflow"`
 Classification string `json:"classification"`
 Observations []CheckRun `json:"observations"`
}
type Readiness struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Repository string `json:"repository"`
 ExperimentID string `json:"experiment_id"`
 HeadSHA string `json:"head_sha"`
 WorkflowSnapshotSHA256 string `json:"workflow_snapshot_sha256"`
 WorkflowObservationCount int `json:"workflow_observation_count"`
 TotalReportedGitHubRuns uint64 `json:"total_reported_github_runs"`
 Required []WorkflowCheck `json:"required"`
 Disposition string `json:"disposition"`
 EngineeringCICompleteInSuppliedSnapshot bool `json:"engineering_ci_complete_in_supplied_snapshot"`
 HistoricalCompletenessVerified bool `json:"historical_completeness_verified"`
 GitHubSourceAuthenticated bool `json:"github_source_authenticated"`
 FullCrossPlatformRegressionVerified bool `json:"full_cross_platform_regression_verified"`
 FirstUseAuthenticated bool `json:"first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ResearchDispatched bool `json:"research_dispatched"`
}
func readinessWorkflows(experiment string)([]string,error){
 if experiment=="P32-DEV"{
  // The exact original-owner qualification run is independently useful
  // development evidence, but never overrides missing/failed hosted checks.
  // P32-DEV is deliberately NOT in requiredHybridWorkflows: it is ineligible
  // for unattended training admission, even with four green run observations.
  return []string{
   "G4 CPU qualification",
   "G5 authentic TTT CPU",
   "G7 pinned Mamba2 CPU import",
   "Native P32-R2 final source actor recurrence damage qualification once",
  },nil
 }
 if experiment=="G7-S26"{
  // S26 is a development-only, still unqualified research branch.
  // The execution admission contract intentionally DOES NOT accept it.
  return []string{"G4 CPU qualification","G5 authentic TTT CPU",
   "G7 pinned Mamba2 CPU import",
   "G7-S26 preregistered quarter-reserve development comparison"},nil
 }
 return requiredHybridWorkflows(experiment)
}
func classifyOne(runs []researchobserver.Run,name,sha string)WorkflowCheck{
 out:=WorkflowCheck{Workflow:name,Classification:"MISSING_IN_BOUNDED_SNAPSHOT",Observations:[]CheckRun{}}
 for _,r:=range runs{
  if r.Workflow!=name||r.HeadSHA!=sha{continue}
  out.Observations=append(out.Observations,CheckRun{
   RunID:r.RunID,RunAttempt:r.RunAttempt,Conclusion:r.Conclusion,
   Status:r.Status,URL:r.URL,
  })
 }
 sort.Slice(out.Observations,func(i,j int)bool{
  if out.Observations[i].RunID!=out.Observations[j].RunID{
   return out.Observations[i].RunID<out.Observations[j].RunID
  }
  return out.Observations[i].RunAttempt<out.Observations[j].RunAttempt
 })
 if len(out.Observations)>1{out.Classification="AMBIGUOUS_MULTIPLE_EXACT_SHA_RUNS";return out}
 if len(out.Observations)==0{return out}
 r:=out.Observations[0]
 switch{
 case r.Status!="completed":
  out.Classification="PENDING_OR_NOT_COMPLETED"
 case r.Conclusion=="success":
  out.Classification="PASS_CI_METADATA_ONLY"
 default:
  out.Classification="FAILED_OR_NONPASS_CI"
 }
 return out
}
// DiagnoseHybrid consumes a single pre-fetched, bounded GitHub workflow
// snapshot. No network or project read access is implied by these bytes.
// Even all-green CI is NOT scientific qualification or an execution permit.
func DiagnoseHybrid(raw []byte,sourceSHA,experiment string)(Readiness,error){
 var zero Readiness
 if !validHex(sourceSHA,40){return zero,ErrBlocked}
 needed,err:=readinessWorkflows(experiment)
 if err!=nil{return zero,ErrBlocked}
 lane,err:=researchobserver.InspectHybrid(raw)
 if err!=nil||lane.Repository!=hybridcustody.Project{return zero,ErrBlocked}
 out:=Readiness{
  Schema:ReadinessSchema,Mode:ReadinessMode,
  Repository:hybridcustody.Project,ExperimentID:experiment,
  HeadSHA:sourceSHA,WorkflowSnapshotSHA256:lane.InputRawSHA256,
  WorkflowObservationCount:lane.ObservationWindow,
  TotalReportedGitHubRuns:lane.TotalGitHubRuns,
  Required:make([]WorkflowCheck,0,len(needed)),
  Disposition:"BLOCKED_INCOMPLETE_OR_FAILED_ENGINEERING_CI",
 }
 allPass:=true
 for _,name:=range needed{
  check:=classifyOne(lane.Runs,name,sourceSHA)
  if check.Classification!="PASS_CI_METADATA_ONLY"{allPass=false}
  out.Required=append(out.Required,check)
 }
 if allPass{
  out.EngineeringCICompleteInSuppliedSnapshot=true
  out.Disposition="FULL_REQUIRED_WORKFLOW_METADATA_GREEN_NOT_SCIENCE"
 }
 if VerifyReadiness(out)!=nil{return zero,ErrBlocked}
 return out,nil
}
// The renderer and any future consumer must reject elevation attempts.
// It deliberately does not claim the supplied snapshot is authoritative.
func VerifyReadiness(r Readiness)error{
 names,err:=readinessWorkflows(r.ExperimentID)
 if err!=nil||r.Schema!=ReadinessSchema||r.Mode!=ReadinessMode||
  r.Repository!=hybridcustody.Project||!validHex(r.HeadSHA,40)||
  !validHex(r.WorkflowSnapshotSHA256,64)||
  r.WorkflowObservationCount<1||r.WorkflowObservationCount>researchobserver.MaximumRuns||
  r.TotalReportedGitHubRuns<uint64(r.WorkflowObservationCount)||
  r.HistoricalCompletenessVerified||r.GitHubSourceAuthenticated||
  r.FullCrossPlatformRegressionVerified||r.FirstUseAuthenticated||
  r.ScientificAccepted||r.ExecutionAuthorized||r.ResearchDispatched||
  len(r.Required)!=len(names){return ErrBlocked}
 allPass:=true
 for i,c:=range r.Required{
  if c.Workflow!=names[i]||len(c.Observations)>researchobserver.MaximumRuns{
   return ErrBlocked
  }
  prevID,prevAttempt:=uint64(0),uint64(0)
  for _,obs:=range c.Observations{
   if obs.RunID==0||obs.RunAttempt==0||
    (obs.RunID<prevID||(obs.RunID==prevID&&obs.RunAttempt<=prevAttempt))||
    obs.URL!="https://github.com/"+hybridcustody.Project+
      "/actions/runs/"+strconv.FormatUint(obs.RunID,10){
    return ErrBlocked
   }
   prevID,prevAttempt=obs.RunID,obs.RunAttempt
  }
  expect:="MISSING_IN_BOUNDED_SNAPSHOT"
  switch{
  case len(c.Observations)>1:expect="AMBIGUOUS_MULTIPLE_EXACT_SHA_RUNS"
  case len(c.Observations)==1:
   if c.Observations[0].Status!="completed"{expect="PENDING_OR_NOT_COMPLETED"}else if c.Observations[0].Conclusion=="success"{expect="PASS_CI_METADATA_ONLY"}else{expect="FAILED_OR_NONPASS_CI"}
  }
  if c.Classification!=expect{return ErrBlocked}
  if expect!="PASS_CI_METADATA_ONLY"{allPass=false}
 }
 if r.EngineeringCICompleteInSuppliedSnapshot!=allPass{return ErrBlocked}
 want:="BLOCKED_INCOMPLETE_OR_FAILED_ENGINEERING_CI"
 if allPass{want="FULL_REQUIRED_WORKFLOW_METADATA_GREEN_NOT_SCIENCE"}
 if r.Disposition!=want{return ErrBlocked}
 return nil
}
