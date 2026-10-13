// forge-required-policy-check qualifies an admin-ready PROPOSAL against
// independent public GitHub Actions job identities; it cannot install rules.
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
var ErrRead=errors.New("FORGE_REQUIRED_POLICY_READONLY_INPUT_BLOCKED")
type result struct{
 Schema string `json:"schema"`
 ProposedRulesetSHA256 string `json:"proposed_ruleset_sha256"`
 Checks branchpolicy.ContextReport `json:"checks"`
 AdministrativeSettingsChanged bool `json:"administrative_settings_changed"`
 BranchProtectionQualified bool `json:"branch_protection_qualified"`
 CutoverAuthorized bool `json:"cutover_authorized"`
}
func read(path string,max int64)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrRead}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>max{return nil,ErrRead}
 b,err:=os.ReadFile(path)
 if err!=nil||int64(len(b))!=st.Size(){return nil,ErrRead}
 return b,nil
}
func run(args []string)(result,error){
 var zero result
 f:=flag.NewFlagSet("forge-required-policy-check",flag.ContinueOnError)
 repo:=f.String("repository","","fixed FORGE repository")
 sha:=f.String("main-sha","","independently pinned main commit")
 plan:=f.String("plan","","absolute main ruleset proposal path")
 checks:=f.String("checks","","absolute GitHub check-runs path")
 if err:=f.Parse(args);err!=nil||f.NArg()!=0||*plan==*checks{return zero,ErrRead}
 pr,err:=read(*plan,65536);if err!=nil{return zero,err}
 h,err:=branchpolicy.ValidateProposedRuleset(pr);if err!=nil{return zero,err}
 cr,err:=read(*checks,2<<20);if err!=nil{return zero,err}
 observation,err:=branchpolicy.InspectActualChecks(*repo,*sha,cr)
 if err!=nil{return zero,err}
 return result{Schema:"forge.ruleset-proposal-and-check-readonly.v1",ProposedRulesetSHA256:h,Checks:observation},nil
}
func main(){
 r,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err:=json.NewEncoder(os.Stdout).Encode(r);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
