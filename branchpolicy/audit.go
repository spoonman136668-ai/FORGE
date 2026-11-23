// Package branchpolicy audits live GitHub repository protection metadata.
// A clean readback is evidence of observation, NOT cutover authorization.
package branchpolicy

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "strings"
)

const (
 Schema="forge.main-policy-observation.v1"
 Blocked="BLOCKED_MAIN_UNPROTECTED_NO_RULESETS"
 Unverified="MAIN_PROTECTION_CLAIMED_NOT_INDEPENDENTLY_QUALIFIED"
 Partial="MAIN_RULESET_APPLICABILITY_UNVERIFIED"
)
var ErrUntrusted=errors.New("FORGE_MAIN_BRANCH_PROTECTION_PROVENANCE_UNTRUSTED")
type Report struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 MainCommitSHA string `json:"main_commit_sha"`
 BranchJSONSHA256 string `json:"branch_json_sha256"`
 RulesetsJSONSHA256 string `json:"rulesets_json_sha256"`
 MainProtected bool `json:"main_protected"`
 TotalRulesets int `json:"total_rulesets"`
 ActiveBranchRulesets int `json:"active_branch_rulesets"`
 Classification string `json:"classification"`
 IndependentAdminAttestationVerified bool `json:"independent_admin_attestation_verified"`
 EnforcementNegativeTestVerified bool `json:"enforcement_negative_test_verified"`
 BranchProtectionQualified bool `json:"branch_protection_qualified"`
 OriginalScientificExecutionAuthorized bool `json:"original_scientific_execution_authorized"`
 CutoverAuthorized bool `json:"cutover_authorized"`
}
type branch struct {
 Name string `json:"name"`
 Protected *bool `json:"protected"`
 Commit struct{SHA string `json:"sha"`} `json:"commit"`
}
type ruleset struct {
 ID int64 `json:"id"`
 Name string `json:"name"`
 Target string `json:"target"`
 Enforcement string `json:"enforcement"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='a'&&c<='f'||c>='0'&&c<='9'){return false}}
 return true
}
func sum(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
// Reject duplicate/case-alias fields at every depth, so JSON decoder's
// case-insensitive last-write-wins cannot substitute GitHub identities.
func unambiguous(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw))
 var walk func(int)bool
 walk=func(depth int)bool{
  if depth>48{return false}
  tok,err:=d.Token();if err!=nil{return false}
  open,ok:=tok.(json.Delim)
  if !ok{return true}
  if open!='{'&&open!='['{return false}
  seen:=map[string]bool{}
  for d.More(){
   if open=='{'{
    key,err:=d.Token();if err!=nil{return false}
    name,ok:=key.(string)
    if !ok||len(name)==0||len(name)>256{return false}
    canonical:=strings.ToLower(name)
    if seen[canonical]{return false}
    seen[canonical]=true
   }
   if !walk(depth+1){return false}
  }
  close,err:=d.Token()
  return err==nil&&(open=='{'&&close==json.Delim('}')||
    open=='['&&close==json.Delim(']'))
 }
 if !walk(0){return false}
 _,err:=d.Token()
 return errors.Is(err,io.EOF)
}
// Inspect requires independently selected exact main SHA and both live
// GitHub metadata snapshots. Even a "protected" claim is NEVER an admin
// attestation or a proven bypass rejection test.
func Inspect(repository,expectedSHA string,branchJSON,rulesJSON []byte)(Report,error){
 var zero Report
 if repository!="spoonman136668-ai/FORGE"||!validHex(expectedSHA,40)||
 len(branchJSON)==0||len(branchJSON)>1<<20||
 len(rulesJSON)==0||len(rulesJSON)>128<<10||
 !unambiguous(branchJSON)||!unambiguous(rulesJSON){return zero,ErrUntrusted}
 var b branch
 if json.Unmarshal(branchJSON,&b)!=nil||b.Name!="main"||
 b.Protected==nil||b.Commit.SHA!=expectedSHA{return zero,ErrUntrusted}
 var rules []ruleset
 if json.Unmarshal(rulesJSON,&rules)!=nil||rules==nil||len(rules)>100{
  return zero,ErrUntrusted
 }
 seen:=map[int64]bool{}
 active:=0
 for _,r:=range rules{
  if r.ID<=0||seen[r.ID]||len(r.Name)==0||len(r.Name)>256||
  (r.Target!="branch"&&r.Target!="tag"&&r.Target!="push")||
  (r.Enforcement!="active"&&r.Enforcement!="disabled"&&r.Enforcement!="evaluate"){
   return zero,ErrUntrusted
  }
  seen[r.ID]=true
  if r.Target=="branch"&&r.Enforcement=="active"{active++}
 }
 class:=Partial
 if !*b.Protected&&active==0&&len(rules)==0{class=Blocked}
 if *b.Protected{class=Unverified}
 return Report{Schema:Schema,Repository:repository,MainCommitSHA:expectedSHA,
  BranchJSONSHA256:sum(branchJSON),RulesetsJSONSHA256:sum(rulesJSON),
  MainProtected:*b.Protected,TotalRulesets:len(rules),
  ActiveBranchRulesets:active,Classification:class},nil
}
