// forge-ci-triage performs an offline exact historical CI failure lookup.
// Inputs require independent authentication; results never approve a patch.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/spoonman136668-ai/forge/citriage"
 "github.com/spoonman136668-ai/forge/repairregistry"
)
type Report struct{
 Status string `json:"status"`
 RunID uint64 `json:"run_id"`
 SourceSHA string `json:"source_sha"`
 Findings []repairregistry.Finding `json:"findings"`
}
func run(args []string)(Report,error){
 f:=flag.NewFlagSet("forge-ci-triage",flag.ContinueOnError)
 registry:=f.String("registry","","existing validated records directory")
 repo:=f.String("repository","","exact repository")
 runID:=f.Uint64("run-id",0,"observed CI run")
 sha:=f.String("sha","","exact source commit")
 job:=f.String("job","","failed job")
 step:=f.String("step","","failed step")
 workflow:=f.String("workflow","","workflow name")
 if err:=f.Parse(args);err!=nil{return Report{},err}
 if *registry==""||f.NArg()!=0{return Report{},citriage.ErrUnsafe}
 failure:=citriage.Failure{Repository:*repo,RunID:*runID,CommitSHA:*sha,
  JobName:*job,FailedStep:*step,WorkflowName:*workflow}
 matches,err:=citriage.Diagnose(*registry,failure)
 if err!=nil{return Report{},err}
 if matches==nil{matches=[]repairregistry.Finding{}}
 return Report{Status:repairregistry.AdvisoryOnly,RunID:*runID,SourceSHA:*sha,Findings:matches},nil
}
func main(){r,err:=run(os.Args[1:]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)};_ = json.NewEncoder(os.Stdout).Encode(r)}
