package hybridintegration

import (
 "encoding/json"
 "strconv"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/researchobserver"
)
func syntheticRun(sha,name,status,conclusion string,id uint64)researchobserver.Run{
 return researchobserver.Run{
  RunID:id,RunAttempt:1,Workflow:name,HeadSHA:sha,
  Status:status,Conclusion:conclusion,
  URL:"https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/"+
   func()string {return strconv.FormatUint(id,10)}(),
  ScientificClassification:"UNVERIFIED_NOT_A_SCIENTIFIC_RESULT",
 }
}
func suiteFor(sha,experiment string)[]researchobserver.Run{
 wanted,_:=requiredHybridWorkflows(experiment)
 out:=make([]researchobserver.Run,0,len(wanted))
 for i,n:=range wanted{
  out=append(out,syntheticRun(sha,n,"completed","success",uint64(100+i)))
 }
 return out
}
func TestMandatoryHybridSuiteBothFrozenExperiments(t *testing.T){
 sha:=strings.Repeat("a",40)
 for _,id:=range []string{"G7-S24","G7-S25"}{
  t.Run(id,func(t *testing.T){
   runs:=suiteFor(sha,id)
   results,err:=requireHybridEngineeringSuite(runs,sha,id)
   if err!=nil||len(results)!=4||
    validateEngineeringQualifiers(results,sha,id)!=nil{t.Fatal("valid engineering suite rejected",err)}
   for _,r:=range results{
    if r.Conclusion!="success"||r.RunAttempt!=1{t.Fatal("unexpected receipt",r)}
   }
  })
 }
}
func TestMandatorySuiteNeverAcceptsOneGreenAmongFailures(t *testing.T){
 // This models observed S25 PR #40: the focused surprise-residual check
 // passed but the essential G4/G5/G7 workflows reported failure.
 sha:="275e5989aba2777bfd0b62049bc07dc37370566f"
 runs:=suiteFor(sha,"G7-S25")
 for i:=0;i<3;i++{runs[i].Conclusion="failure"}
 runs[0].RunID=42424118909
 runs[1].RunID=42424119064
 runs[2].RunID=42424118957
 // URLs are rewritten with the real readback IDs to keep identity exact.
 for i:=0;i<3;i++{
  runs[i].URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/"+
   strconv.FormatUint(runs[i].RunID,10)
 }
 runs[3].RunID=42424114015
 runs[3].URL="https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/42424114015"
 if _,err:=requireHybridEngineeringSuite(runs,sha,"G7-S25");err==nil{
  t.Fatal("a green focused S25 check masked mandatory G4/G5/G7 failures")
 }
 // S24 also has no qualified full-suite evidence on its current PR head.
 s24:="d97c15cf709be63d186adcb58e01e3730cb539e1"
 bad:=suiteFor(s24,"G7-S24")
 for i:=range bad {bad[i].Conclusion="failure"}
 if _,err:=requireHybridEngineeringSuite(bad,s24,"G7-S24");err==nil{
  t.Fatal("failed S24 full suite was admitted")
 }
}
func TestMandatorySuiteRejectsMissingStaleDuplicateAndUnknown(t *testing.T){
 sha:=strings.Repeat("a",40)
 base:=suiteFor(sha,"G7-S24")
 for _,caseData:=range []struct{name string;edit func([]researchobserver.Run)[]researchobserver.Run}{
  {"missing G7",func(x []researchobserver.Run)[]researchobserver.Run{return append(x[:2],x[3:]...)}},
  {"stale SHA",func(x []researchobserver.Run)[]researchobserver.Run{x[2].HeadSHA=strings.Repeat("f",40);return x}},
  {"cancelled",func(x []researchobserver.Run)[]researchobserver.Run{x[0].Conclusion="cancelled";return x}},
  {"pending",func(x []researchobserver.Run)[]researchobserver.Run{x[0].Status="in_progress";x[0].Conclusion="";return x}},
  {"unexpected conclusion",func(x []researchobserver.Run)[]researchobserver.Run{x[0].Conclusion="failure";return x}},
  {"duplicate passed run",func(x []researchobserver.Run)[]researchobserver.Run{
   return append(x,x[0])}},
  {"mismatched run id",func(x []researchobserver.Run)[]researchobserver.Run{x[1].RunID=x[0].RunID;return x}},
  {"forged scientific acceptance",func(x []researchobserver.Run)[]researchobserver.Run{x[1].ScientificAccepted=true;return x}},
 }{
  t.Run(caseData.name,func(t *testing.T){
   input:=append([]researchobserver.Run(nil),base...)
   changed:=caseData.edit(input)
   if _,err:=requireHybridEngineeringSuite(changed,sha,"G7-S24");err==nil{
    t.Fatal("unsafe mandatory CI admitted")
   }
  })
 }
 if _,err:=requireHybridEngineeringSuite(base,sha,"G7-S26");err==nil{
  t.Fatal("unregistered experiment admitted")
 }
}
func TestAssembleRequiresFullHybridSuiteNotJustAttestation(t *testing.T){
 in:=fixture(t)
 if _,err:=Assemble(in);err!=nil{t.Fatal("new suite fixture rejected",err)}
 var snapshot struct{
  TotalCount uint64 `json:"total_count"`
  WorkflowRuns []map[string]any `json:"workflow_runs"`
 }
 if err:=json.Unmarshal(in.HybridWorkflowRaw,&snapshot);err!=nil{t.Fatal(err)}
 // Only the selected engineering receipt remains green.
 for i:=1;i<len(snapshot.WorkflowRuns);i++{
  snapshot.WorkflowRuns[i]["conclusion"]="failure"
 }
 raw,err:=json.Marshal(snapshot);if err!=nil{t.Fatal(err)}
 in.HybridWorkflowRaw=raw
 if _,err:=Assemble(in);err==nil{
  t.Fatal("selected successful engineering receipt hid failed mandatory suite")
 }
}
