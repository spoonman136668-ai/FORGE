package branchpolicy
import (
 "errors"
 "fmt"
 "strings"
 "testing"
)
const commit="6106675d55c6faec09948587e769c3fbd8e1f105"
func fixture()(string,string){
 return fmt.Sprintf(`{"name":"main","protected":false,"commit":{"sha":"%s"}}`,commit),"[]"
}
func TestRealUnprotectedMainClassificationNoFalseCutover(t *testing.T){
 b,r:=fixture()
 out,err:=Inspect("spoonman136668-ai/FORGE",commit,[]byte(b),[]byte(r))
 if err!=nil{t.Fatal(err)}
 if out.Classification!=Blocked||out.MainProtected||out.TotalRulesets!=0||
  out.ActiveBranchRulesets!=0||out.BranchProtectionQualified||
  out.IndependentAdminAttestationVerified||out.EnforcementNegativeTestVerified||
  out.OriginalScientificExecutionAuthorized||out.CutoverAuthorized||
  !validHex(out.BranchJSONSHA256,64)||!validHex(out.RulesetsJSONSHA256,64){
  t.Fatalf("unprotected branch incorrectly marked usable: %+v",out)
 }
}
func TestEvenProtectedOrActiveRuleClaimCannotSelfAuthorize(t *testing.T){
 b,_:=fixture()
 b=strings.Replace(b,`"protected":false`,`"protected":true`,1)
 rule:=`[{"id":7,"name":"require-pr-checks","target":"branch","enforcement":"active"}]`
 out,err:=Inspect("spoonman136668-ai/FORGE",commit,[]byte(b),[]byte(rule))
 if err!=nil||out.Classification!=Unverified||out.ActiveBranchRulesets!=1||
  out.BranchProtectionQualified||out.CutoverAuthorized||out.EnforcementNegativeTestVerified{
  t.Fatalf("self-reported protection promoted to authority: %+v %v",out,err)
 }
}
func TestRulesetCannotQualifyUnprotectedMainByPresence(t *testing.T){
 b,_:=fixture()
 rule:=`[{"id":7,"name":"tags-only","target":"tag","enforcement":"active"}]`
 out,err:=Inspect("spoonman136668-ai/FORGE",commit,[]byte(b),[]byte(rule))
 if err!=nil||out.Classification!=Partial||out.BranchProtectionQualified||out.CutoverAuthorized{
  t.Fatal("irrelevant policy treated as protection",out,err)
 }
}
func TestExactIdentityAndMaliciousGitHubJSONFailClosed(t *testing.T){
 b,r:=fixture()
 variants:=map[string]struct{repo,sha,branch,rules string}{
  "wrong repository":{"other/FORGE",commit,b,r},
  "wrong commit":{"spoonman136668-ai/FORGE",strings.Repeat("f",40),b,r},
  "wrong case hash":{"spoonman136668-ai/FORGE",strings.ToUpper(commit),b,r},
  "wrong branch":{"spoonman136668-ai/FORGE",commit,strings.Replace(b,`"name":"main"`,`"name":"dev"`,1),r},
  "missing protected":{"spoonman136668-ai/FORGE",commit,strings.Replace(b,`"protected":false,`,"",1),r},
  "double protected":{"spoonman136668-ai/FORGE",commit,strings.Replace(b,`"protected":false`,`"protected":false,"protected":true`,1),r},
  "case alias protected":{"spoonman136668-ai/FORGE",commit,strings.Replace(b,`"protected":false`,`"protected":false,"PROTECTED":true`,1),r},
  "nested duplicate sha":{"spoonman136668-ai/FORGE",commit,strings.Replace(b,`"sha":"`+commit+`"`,`"sha":"`+commit+`","sha":"`+commit+`"`,1),r},
  "rules null":{"spoonman136668-ai/FORGE",commit,b,"null"},
  "rules duplicate id":{"spoonman136668-ai/FORGE",commit,b,`[{"id":1,"name":"a","target":"branch","enforcement":"active"},{"id":1,"name":"b","target":"branch","enforcement":"active"}]`},
  "rules wrong enforcement":{"spoonman136668-ai/FORGE",commit,b,`[{"id":1,"name":"a","target":"branch","enforcement":"magic"}]`},
  "rules duplicate key":{"spoonman136668-ai/FORGE",commit,b,`[{"id":1,"id":2,"name":"a","target":"branch","enforcement":"active"}]`},
  "rules nested case alias":{"spoonman136668-ai/FORGE",commit,b,`[{"id":1,"ID":2,"name":"a","target":"branch","enforcement":"active"}]`},
  "rules trailing document":{"spoonman136668-ai/FORGE",commit,b,r+"{}"},
 }
 for name,v:=range variants{
  t.Run(name,func(t *testing.T){
   if got,err:=Inspect(v.repo,v.sha,[]byte(v.branch),[]byte(v.rules));!errors.Is(err,ErrUntrusted){
    t.Fatalf("admitted changed governance source: %+v %v",got,err)
   }
  })
 }
}
func TestRejectExcessiveNestingAndOversizedReadback(t *testing.T){
 b,_:=fixture()
 nested:="["+strings.Repeat("[",55)+"0"+strings.Repeat("]",55)+"]"
 for _,rules:=range []string{nested,strings.Repeat(" ",129<<10)+"[]"}{
  if _,err:=Inspect("spoonman136668-ai/FORGE",commit,[]byte(b),[]byte(rules));!errors.Is(err,ErrUntrusted){
   t.Fatal("accepted unbounded readback",err)
  }
 }
}
