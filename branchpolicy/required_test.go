package branchpolicy

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "strings"
 "testing"
)
const mainSHA="3e94421896f32ffde4a3800834214a2ee7605207"
func proposed(t *testing.T)[]byte{
 t.Helper()
 raw,err:=os.ReadFile("../reference/governance/forge-main-ruleset-proposal.json")
 if err!=nil{t.Fatal(err)}
 return raw
}
func TestRulesetPlanMatchesSourceAndRemainsNonAuthorizing(t *testing.T){
 raw:=proposed(t)
 digest,err:=ValidateProposedRuleset(raw)
 if err!=nil||!validHex(digest,64){t.Fatal("admin ruleset proposal source drift",err)}
 if bytes.Contains(raw,[]byte(`"required_approving_review_count": 1`)){
  t.Fatal("unapproved human-review burden added to autonomous PR flow")
 }
}
func TestUnsafeGovernancePlanDriftFailsClosed(t *testing.T){
 src:=proposed(t)
 type change func(map[string]any)
 cases:=map[string]change{
  "bypass admin":func(m map[string]any){m["bypass_actors"]=[]any{map[string]any{"actor_type":"RepositoryRole","actor_id":5,"bypass_mode":"always"}}},
  "deactivated":func(m map[string]any){m["enforcement"]="evaluate"},
  "tag instead of branch":func(m map[string]any){m["target"]="tag"},
  "unscoped main":func(m map[string]any){m["conditions"].(map[string]any)["ref_name"].(map[string]any)["include"]=[]any{"~ALL"}},
  "alternate branch":func(m map[string]any){m["conditions"].(map[string]any)["ref_name"].(map[string]any)["include"]=[]any{"refs/heads/dev"}},
  "remove force push denial":func(m map[string]any){m["rules"]=append([]any(nil),m["rules"].([]any)[:1]...)},
  "human approval":func(m map[string]any){m["rules"].([]any)[2].(map[string]any)["parameters"].(map[string]any)["required_approving_review_count"]=float64(1)},
  "non-strict checks":func(m map[string]any){m["rules"].([]any)[3].(map[string]any)["parameters"].(map[string]any)["strict_required_status_checks_policy"]=false},
  "untrusted check context":func(m map[string]any){m["rules"].([]any)[3].(map[string]any)["parameters"].(map[string]any)["required_status_checks"].([]any)[0].(map[string]any)["context"]="other"},
  "untrusted check app":func(m map[string]any){m["rules"].([]any)[3].(map[string]any)["parameters"].(map[string]any)["required_status_checks"].([]any)[1].(map[string]any)["integration_id"]=float64(0)},
  "unrestricted direct push":func(m map[string]any){m["rules"].([]any)[2].(map[string]any)["type"]="creation"},
 }
 for name,mutate:=range cases{t.Run(name,func(t *testing.T){
  var m map[string]any
  if err:=json.Unmarshal(src,&m);err!=nil{t.Fatal(err)}
  mutate(m)
  changed,_:=json.Marshal(m)
  if _,err:=ValidateProposedRuleset(changed);!errors.Is(err,ErrRulesetPlan){
   t.Fatalf("unsafe admin configuration accepted: %v",err)
  }
 })}
 dup:=bytes.Replace(src,[]byte(`"enforcement": "active"`),[]byte(`"enforcement": "active", "ENFORCEMENT": "evaluate"`),1)
 if _,err:=ValidateProposedRuleset(dup);!errors.Is(err,ErrRulesetPlan){
  t.Fatal("accepted duplicate case-folded GitHub ruleset property",err)
 }
}
type run struct{
 Name string `json:"name"`
 HeadSHA string `json:"head_sha"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 App struct{ID int64 `json:"id"`; Slug string `json:"slug"`} `json:"app"`
 CheckSuite struct{ID int64 `json:"id"`} `json:"check_suite"`
}
func makeCheck(name string)run{
 r:=run{Name:name,HeadSHA:mainSHA,Status:"completed",Conclusion:"success"}
 r.App.ID=ExpectedGitHubActionsAppID
 r.App.Slug="github-actions"
 r.CheckSuite.ID=100
 return r
}
func checksData(checks []run)[]byte{
 raw,_:=json.Marshal(map[string]any{"total_count":len(checks),"check_runs":checks})
 return raw
}
func TestIndependentlyPinnedRequiredChecksWithoutFakingRuleset(t *testing.T){
 raw:=checksData([]run{makeCheck("linux"),makeCheck("windows"),makeCheck("other")})
 out,err:=InspectActualChecks("spoonman136668-ai/FORGE",mainSHA,raw)
 if err!=nil||!out.CheckSourceVerified||out.BranchProtectionQualified||
  out.EnforcementNegativeTestVerified||out.CutoverAuthorized||
  out.Classification!=ContextsOnly||out.MainCommitSHA!=mainSHA||
  len(out.RequiredContexts)!=2{
  t.Fatalf("incorrect GitHub Actions check classification: %+v %v",out,err)
 }
}
func TestRequiredCheckForgeryAndAmbiguityRejected(t *testing.T){
 cases:=map[string]func(*[]run){
  "no Linux":func(r *[]run){(*r)[0].Name="other"},
  "wrong SHA":func(r *[]run){(*r)[0].HeadSHA=strings.Repeat("f",40)},
  "failure":func(r *[]run){(*r)[1].Conclusion="failure"},
  "pending":func(r *[]run){(*r)[0].Status="in_progress"},
  "spoofed integration":func(r *[]run){(*r)[1].App.ID=123},
  "spoofed integration slug":func(r *[]run){(*r)[1].App.Slug="attacker"},
  "missing suite":func(r *[]run){(*r)[0].CheckSuite.ID=0},
  "duplicate context":func(r *[]run){*r=append(*r,makeCheck("linux"))},
 }
 for name,fn:=range cases{t.Run(name,func(t *testing.T){
  rs:=[]run{makeCheck("linux"),makeCheck("windows")}
  fn(&rs)
  if _,err:=InspectActualChecks("spoonman136668-ai/FORGE",mainSHA,checksData(rs));!errors.Is(err,ErrChecks){
   t.Fatalf("spoofed GitHub check admitted: %v",err)
  }
 })}
 raw:=checksData([]run{makeCheck("linux"),makeCheck("windows")})
 modified:=bytes.Replace(raw,[]byte(`"name":"linux"`),[]byte(`"name":"linux","NAME":"windows"`),1)
 if _,err:=InspectActualChecks("spoonman136668-ai/FORGE",mainSHA,modified);!errors.Is(err,ErrChecks){
  t.Fatal("admitted duplicate status check alias",err)
 }
 if _,err:=InspectActualChecks("spoonman136668-ai/FORGE",strings.Repeat("f",40),raw);!errors.Is(err,ErrChecks){
  t.Fatal("admitted wrong commit",err)
 }
}
