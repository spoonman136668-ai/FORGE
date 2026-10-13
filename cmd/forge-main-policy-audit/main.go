// forge-main-policy-audit reads only snapshots of GitHub public governance.
// It never changes repository settings or issues any research authority.
package main
import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "github.com/spoonman136668-ai/forge/branchpolicy"
)
var ErrInput=errors.New("FORGE_MAIN_POLICY_READBACK_INPUT_UNTRUSTED")
func read(path string,max int64)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrInput}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()==0||st.Size()>max{return nil,ErrInput}
 raw,err:=os.ReadFile(path)
 if err!=nil||int64(len(raw))!=st.Size(){return nil,ErrInput}
 return raw,nil
}
func run(args []string)(branchpolicy.Report,error){
 var zero branchpolicy.Report
 flags:=flag.NewFlagSet("forge-main-policy-audit",flag.ContinueOnError)
 repo:=flags.String("repository","","fixed repository")
 sha:=flags.String("expected-main-sha","","independently pinned GitHub main commit")
 branch:=flags.String("branch","","absolute read-only GitHub branch JSON")
 rules:=flags.String("rulesets","","absolute read-only GitHub ruleset JSON")
 if err:=flags.Parse(args);err!=nil||flags.NArg()!=0||
  *branch==*rules{return zero,ErrInput}
 b,err:=read(*branch,1<<20);if err!=nil{return zero,err}
 r,err:=read(*rules,128<<10);if err!=nil{return zero,err}
 return branchpolicy.Inspect(*repo,*sha,b,r)
}
func main(){
 result,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
