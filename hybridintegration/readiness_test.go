package hybridintegration

import (
 "encoding/json"
 "strconv"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/researchobserver"
)
func readinessSnapshot(t *testing.T,sha string,runs []researchobserver.Run)[]byte{
 t.Helper()
 items:=make([]any,0,len(runs))
 for _,r:=range runs{
  var conclusion any
  if r.Status=="completed"{conclusion=r.Conclusion}
  items=append(items,map[string]any{
   "id":r.RunID,"run_attempt":r.RunAttempt,"name":r.Workflow,
   "head_sha":r.HeadSHA,"head_branch":"research/frozen",
   "status":r.Status,"conclusion":conclusion,
   "created_at":"2026-11-07T00:00:00Z",
   "html_url":"https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/"+
    strconv.FormatUint(r.RunID,10),
   "repository":map[string]any{"full_name":"spoonman136668-ai/TTT-Hybrid-Lab"},
   "head_repository":map[string]any{"full_name":"spoonman136668-ai/TTT-Hybrid-Lab"},
  })
 }
 raw,err:=json.Marshal(map[string]any{"total_count":len(runs),"workflow_runs":items})
 if err!=nil{t.Fatal(err)}
 return raw
}
func TestReadinessPreservesObservedS25FailureAndFocusedSuccess(t *testing.T){
 sha:="275e5989aba2777bfd0b62049bc07dc37370566f"
 runs:=suiteFor(sha,"G7-S25")
 // These run IDs and results correspond to observed GitHub metadata,
 // but this is synthetic offline test input, not authenticated custody.
 ids:=[]uint64{42424118909,42424119064,42424118957,42424114015}
 for i:=range runs{
  runs[i].RunID=ids[i];runs[i].URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/"+
   strconv.FormatUint(ids[i],10)
  if i<3{runs[i].Conclusion="failure"}
 }
 raw:=readinessSnapshot(t,sha,runs)
 report,err:=DiagnoseHybrid(raw,sha,"G7-S25")
 if err!=nil||VerifyReadiness(report)!=nil{t.Fatal(err)}
 if report.EngineeringCICompleteInSuppliedSnapshot||report.ExecutionAuthorized||
  report.ScientificAccepted||report.FullCrossPlatformRegressionVerified||
  report.Required[3].Classification!="PASS_CI_METADATA_ONLY"||
  report.Required[0].Classification!="FAILED_OR_NONPASS_CI"{
  t.Fatalf("focused pass hid G4/G5/G7 negatives: %+v",report)
 }
}
func TestReadinessS26IsDevelopmentOnly(t *testing.T){
 sha:="ff2667c3eef0bf063ac2681cd03bab9935150c47"
 names,err:=readinessWorkflows("G7-S26");if err!=nil{t.Fatal(err)}
 runs:=make([]researchobserver.Run,0,len(names))
 for i,n:=range names{
  id:=uint64(42425788087+i)
  runs=append(runs,syntheticRun(sha,n,"completed","failure",id))
 }
 runs[3].RunID=42425731709
 runs[3].URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/42425731709"
 report,err:=DiagnoseHybrid(readinessSnapshot(t,sha,runs),sha,"G7-S26")
 if err!=nil||VerifyReadiness(report)!=nil||report.EngineeringCICompleteInSuppliedSnapshot||
  report.Required[3].Classification!="FAILED_OR_NONPASS_CI"{
  t.Fatal("S26 dev-run failure lost",err,report)
 }
 if _,err:=requireHybridEngineeringSuite(runs,sha,"G7-S26");err==nil{
  t.Fatal("development-only S26 was upgraded to execution admission")
 }
}
func TestReadinessAllGreenStillProvesNoOriginalOrScience(t *testing.T){
 sha:=strings.Repeat("a",40)
 for _,experiment:=range []string{"G7-S24","G7-S25","G7-S26"}{
  names,err:=readinessWorkflows(experiment);if err!=nil{t.Fatal(err)}
  runs:=make([]researchobserver.Run,0,len(names))
  for i,n:=range names{runs=append(runs,syntheticRun(sha,n,"completed","success",uint64(200+i)))}
  input:=readinessSnapshot(t,sha,runs)
  r,err:=DiagnoseHybrid(input,sha,experiment)
  if err!=nil||VerifyReadiness(r)!=nil||!r.EngineeringCICompleteInSuppliedSnapshot||
   r.Disposition!="FULL_REQUIRED_WORKFLOW_METADATA_GREEN_NOT_SCIENCE"||
   r.GitHubSourceAuthenticated||r.FullCrossPlatformRegressionVerified||
   r.FirstUseAuthenticated||r.ScientificAccepted||r.ExecutionAuthorized||
   r.ResearchDispatched{t.Fatal("all-green metadata escalated",err,r)}
 }
}
func TestReadinessMissingStalePendingDuplicates(t *testing.T){
 sha:=strings.Repeat("a",40)
 base:=suiteFor(sha,"G7-S25")
 for _,tc:=range []struct{name string;change func([]researchobserver.Run)[]researchobserver.Run;expect string}{
  {"missing",func(v []researchobserver.Run)[]researchobserver.Run{return v[:3]},"MISSING_IN_BOUNDED_SNAPSHOT"},
  {"stale",func(v []researchobserver.Run)[]researchobserver.Run{v[3].HeadSHA=strings.Repeat("b",40);return v},"MISSING_IN_BOUNDED_SNAPSHOT"},
  {"pending",func(v []researchobserver.Run)[]researchobserver.Run{v[3].Status="queued";v[3].Conclusion="";return v},"PENDING_OR_NOT_COMPLETED"},
  {"duplicate",func(v []researchobserver.Run)[]researchobserver.Run{
   dup:=v[3];dup.RunID=999;dup.URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/999"
   return append(v,dup)
  },"AMBIGUOUS_MULTIPLE_EXACT_SHA_RUNS"},
 }{
  t.Run(tc.name,func(t *testing.T){
   input:=tc.change(append([]researchobserver.Run(nil),base...))
   report,err:=DiagnoseHybrid(readinessSnapshot(t,sha,input),sha,"G7-S25")
   if err!=nil||VerifyReadiness(report)!=nil||report.Required[3].Classification!=tc.expect||
    report.EngineeringCICompleteInSuppliedSnapshot{t.Fatal("bad readiness state",err,report)}
  })
 }
}
func TestReadinessRejectsForeignInputAndForgedAuthority(t *testing.T){
 sha:=strings.Repeat("a",40)
 base:=suiteFor(sha,"G7-S24")
 raw:=readinessSnapshot(t,sha,base)
 report,err:=DiagnoseHybrid(raw,sha,"G7-S24")
 if err!=nil{t.Fatal(err)}
 if _,err:=DiagnoseHybrid(raw,"wrong","G7-S24");err==nil{t.Fatal("bad sha accepted")}
 if _,err:=DiagnoseHybrid(raw,sha,"G7-S27");err==nil{t.Fatal("unknown experiment")}
 for _,change:=range []func(*Readiness){
  func(x *Readiness){x.ScientificAccepted=true},
  func(x *Readiness){x.ExecutionAuthorized=true},
  func(x *Readiness){x.FirstUseAuthenticated=true},
  func(x *Readiness){x.GitHubSourceAuthenticated=true},
  func(x *Readiness){x.FullCrossPlatformRegressionVerified=true},
  func(x *Readiness){x.Required[0].Classification="PASS_CI_METADATA_ONLY";x.Required[0].Observations=nil},
 }{
  x:=report
  x.Required=append([]WorkflowCheck(nil),report.Required...)
  change(&x)
  if VerifyReadiness(x)==nil{t.Fatal("forged readiness output",x)}
 }
}

func TestReadinessP32OwnerPassCannotOverrideFailedHostedSuite(t *testing.T){
 sha:="7bc49166b83788efc7bfb9da82d39fc420630c46"
 names,err:=readinessWorkflows("P32-DEV")
 if err!=nil||len(names)!=4{t.Fatal("P32 development workflow identity changed",err)}
 ids:=[]uint64{42548767052,42548767056,42548767057,42548762315}
 runs:=make([]researchobserver.Run,0,4)
 for i,name:=range names{
  verdict:="failure"
  if i==3{verdict="success"}
  runs=append(runs,syntheticRun(sha,name,"completed",verdict,ids[i]))
 }
 out,err:=DiagnoseHybrid(readinessSnapshot(t,sha,runs),sha,"P32-DEV")
 if err!=nil||VerifyReadiness(out)!=nil{t.Fatal(err)}
 if out.EngineeringCICompleteInSuppliedSnapshot||
  out.Disposition!="BLOCKED_INCOMPLETE_OR_FAILED_ENGINEERING_CI"||
  out.Required[3].Classification!="PASS_CI_METADATA_ONLY"||
  out.Required[0].Classification!="FAILED_OR_NONPASS_CI"||
  out.Required[1].Classification!="FAILED_OR_NONPASS_CI"||
  out.Required[2].Classification!="FAILED_OR_NONPASS_CI"||
  out.GitHubSourceAuthenticated||out.FirstUseAuthenticated||
  out.ScientificAccepted||out.ExecutionAuthorized||out.ResearchDispatched{
  t.Fatalf("owner success wrongly elevated despite hosted CI failures: %+v",out)
 }
 if _,err:=requireHybridEngineeringSuite(runs,sha,"P32-DEV");err==nil{
  t.Fatal("development-only P32 became an unattended execution candidate")
 }
}

func TestReadinessP32EvenAllGreenIsNotOwnerAdmission(t *testing.T){
 sha:=strings.Repeat("b",40)
 names,err:=readinessWorkflows("P32-DEV")
 if err!=nil{t.Fatal(err)}
 runs:=make([]researchobserver.Run,0,len(names))
 for i,name:=range names{
  runs=append(runs,syntheticRun(sha,name,"completed","success",uint64(42560000000+i)))
 }
 out,err:=DiagnoseHybrid(readinessSnapshot(t,sha,runs),sha,"P32-DEV")
 if err!=nil||VerifyReadiness(out)!=nil{t.Fatal(err)}
 if !out.EngineeringCICompleteInSuppliedSnapshot||
  out.GitHubSourceAuthenticated||out.FullCrossPlatformRegressionVerified||
  out.FirstUseAuthenticated||out.ScientificAccepted||
  out.ExecutionAuthorized||out.ResearchDispatched{
  t.Fatal("P32 fabricated owner or science authority",out)
 }
 if _,err:=requireHybridEngineeringSuite(runs,sha,"P32-DEV");err==nil{
  t.Fatal("all-green caller P32 metadata unexpectedly authorized source")
 }
 dup:=append(append([]researchobserver.Run(nil),runs...),runs[3])
 dup[len(dup)-1].RunID=42560000099
 dup[len(dup)-1].URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/42560000099"
 blocked,err:=DiagnoseHybrid(readinessSnapshot(t,sha,dup),sha,"P32-DEV")
 if err!=nil||VerifyReadiness(blocked)!=nil||
  blocked.EngineeringCICompleteInSuppliedSnapshot||
  blocked.Required[3].Classification!="AMBIGUOUS_MULTIPLE_EXACT_SHA_RUNS"{
  t.Fatal("duplicate owner run incorrectly treated as qualified",err,blocked)
 }
}
