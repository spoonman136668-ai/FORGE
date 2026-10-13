package branchpolicy

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
)

const (
 ExpectedGitHubActionsAppID=15368
 ContextsOnly="REQUIRED_CHECK_CONTEXTS_VERIFIED_NOT_RULESET_ENFORCEMENT"
)
var ErrRulesetPlan=errors.New("FORGE_MAIN_REQUIRED_RULESET_PLAN_INVALID_OR_DRIFT")
var ErrChecks=errors.New("FORGE_MAIN_REQUIRED_CHECK_SOURCE_UNVERIFIED")

// ExpectedMainPlan is a PROPOSAL for a separately authorized repository admin.
// A verified config proposal does not install a rule or qualify cutover.
func ExpectedMainPlan()map[string]any{
 return map[string]any{
  "name":"FORGE main qualified-source only",
  "target":"branch",
  "enforcement":"active",
  "bypass_actors":[]any{},
  "conditions":map[string]any{"ref_name":map[string]any{
   "include":[]any{"refs/heads/main"}, "exclude":[]any{},
  }},
  "rules":[]any{
   map[string]any{"type":"deletion"},
   map[string]any{"type":"non_fast_forward"},
   map[string]any{"type":"pull_request","parameters":map[string]any{
    "allowed_merge_methods":[]any{"merge"},
    "dismiss_stale_reviews_on_push":true,
    "require_code_owner_review":false,
    "require_last_push_approval":false,
    "required_approving_review_count":0,
    "required_review_thread_resolution":true,
   }},
   map[string]any{"type":"required_status_checks","parameters":map[string]any{
    "do_not_enforce_on_create":false,
    "strict_required_status_checks_policy":true,
    "required_status_checks":[]any{
     map[string]any{"context":"linux","integration_id":ExpectedGitHubActionsAppID},
     map[string]any{"context":"windows","integration_id":ExpectedGitHubActionsAppID},
    },
   }},
  },
 }
}

// ValidateProposedRuleset enforces exact rule semantics, prohibits privileges
// that would bypass source qualification, and never installs the proposed rule.
func ValidateProposedRuleset(raw []byte)(string,error){
 if len(raw)==0||len(raw)>65536||!unambiguous(raw){return "",ErrRulesetPlan}
 var proposed any
 if json.Unmarshal(raw,&proposed)!=nil{return "",ErrRulesetPlan}
 actualJSON,err:=json.Marshal(proposed)
 if err!=nil{return "",ErrRulesetPlan}
 expectedJSON,err:=json.Marshal(ExpectedMainPlan())
 if err!=nil||!bytes.Equal(actualJSON,expectedJSON){return "",ErrRulesetPlan}
 return sum(raw),nil
}
type checkMetadata struct{
 TotalCount int `json:"total_count"`
 CheckRuns []struct{
  Name string `json:"name"`
  HeadSHA string `json:"head_sha"`
  Status string `json:"status"`
  Conclusion string `json:"conclusion"`
  App struct{
   ID int64 `json:"id"`
   Slug string `json:"slug"`
  } `json:"app"`
  CheckSuite struct{ID int64 `json:"id"`} `json:"check_suite"`
 } `json:"check_runs"`
}
type ContextReport struct{
 Schema string `json:"schema"`
 MainCommitSHA string `json:"main_commit_sha"`
 CheckRunsSHA256 string `json:"check_runs_sha256"`
 RequiredContexts []string `json:"required_contexts"`
 CheckSourceVerified bool `json:"check_source_verified"`
 BranchProtectionQualified bool `json:"branch_protection_qualified"`
 EnforcementNegativeTestVerified bool `json:"enforcement_negative_test_verified"`
 CutoverAuthorized bool `json:"cutover_authorized"`
 Classification string `json:"classification"`
}
// InspectActualChecks binds both real success contexts to the exact GitHub
// main SHA and GitHub Actions integration. It cannot establish branch rules.
func InspectActualChecks(repository,expectedSHA string,raw []byte)(ContextReport,error){
 var zero ContextReport
 if repository!="spoonman136668-ai/FORGE"||!validHex(expectedSHA,40)||
  len(raw)==0||len(raw)>2<<20||!unambiguous(raw){return zero,ErrChecks}
 var observed checkMetadata
 if json.Unmarshal(raw,&observed)!=nil||observed.CheckRuns==nil||
  observed.TotalCount<2||observed.TotalCount>100||
  len(observed.CheckRuns)!=observed.TotalCount{return zero,ErrChecks}
 required:=map[string]bool{"linux":false,"windows":false}
 for _,run:=range observed.CheckRuns{
  if _,ok:=required[run.Name];!ok{continue}
  if required[run.Name]||run.HeadSHA!=expectedSHA||
   run.Status!="completed"||run.Conclusion!="success"||
   run.App.ID!=ExpectedGitHubActionsAppID||run.App.Slug!="github-actions"||
   run.CheckSuite.ID<=0{return zero,ErrChecks}
  required[run.Name]=true
 }
 if !required["linux"]||!required["windows"]{return zero,ErrChecks}
 return ContextReport{
  Schema:"forge.main-required-checks-observation.v1",
  MainCommitSHA:expectedSHA,CheckRunsSHA256:sum(raw),
  RequiredContexts:[]string{"linux","windows"},
  CheckSourceVerified:true,Classification:ContextsOnly,
 },nil
}
func (r ContextReport)String()string{
 return fmt.Sprintf("%s: %s; protected=%t cutover=%t",r.Schema,
  r.Classification,r.BranchProtectionQualified,r.CutoverAuthorized)
}
