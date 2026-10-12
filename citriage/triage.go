// Package citriage converts explicitly supplied, authenticated-by-caller
// GitHub CI job observations into bounded read-only repair references.
package citriage
import(
 "errors"
 "strings"
 "github.com/spoonman136668-ai/forge/repairregistry"
)
var ErrUnsafe=errors.New("FORGE_CI_TRIAGE_INPUT_UNTRUSTED")
type Failure struct{
 Repository string
 RunID uint64
 CommitSHA string
 JobName string
 FailedStep string
 WorkflowName string
}
const publicIsolationSignature="CI_PUBLIC_ISOLATION_EXEC_COMMAND"
const publicIsolationScope="FORGE qualify.yml public isolation synthetic subprocess tests"
var isolationConditions=[]string{
 "Exact subprocess file inventory independently reviewed",
 "No live execution or CKB authority",
}
func validSHA(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// QueryFor rejects any failure not already in an explicit, frozen inventory.
// A caller must independently authenticate the GitHub run, commit, and job;
// passing a struct is NOT proof of origin. No patches can be applied here.
func QueryFor(f Failure)(repairregistry.Query,error){
 if f.Repository!="spoonman136668-ai/FORGE"||f.RunID==0||!validSHA(f.CommitSHA)||
 f.JobName!="linux"||f.FailedStep!="Public isolation"||
 f.WorkflowName!="FORGE public Linux and Windows qualification"{
  return repairregistry.Query{},ErrUnsafe
 }
 return repairregistry.Query{
  Repository:f.Repository,Component:"public-isolation",
  FailureSignature:publicIsolationSignature,Scope:publicIsolationScope,
  Preconditions:append([]string(nil),isolationConditions...),
 },nil
}
// Diagnose never permits a signature substring or an unknown CI failure to
// inherit an old repair. It produces advisory reference pointers only.
func Diagnose(root string,f Failure)([]repairregistry.Finding,error){
 q,err:=QueryFor(f);if err!=nil{return nil,err}
 findings,err:=repairregistry.Diagnose(root,q)
 if err!=nil{return nil,err}
 for _,v:=range findings{if !strings.HasPrefix(v.Disposition,"REFERENCE_ONLY_"){return nil,ErrUnsafe}}
 return findings,nil
}
