// Package noveltyeval runs a complete, frozen SOURCE-ONLY comparator suite
// for F95's typed relational mechanism. No holdout, scientific first-use,
// superiority claim, or optimizer promotion can arise from these fixtures.
package noveltyeval

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"

 "github.com/spoonman136668-ai/forge/noveltymechanisms"
)

const FixtureSchema="forge.optimizer.f96.frozen-source-fixtures.v1"
const ReportSchema="forge.optimizer.f96.comparator-source-results.v1"
const FrozenBeforeEvaluationCommit="dcb7777199fcaf9d52d78ef9961fc73e2e018911"
const BaseF95Commit="b61fa60084fc487b4d010b3662a2b85872488deb"
var ErrF96=errors.New("FORGE_F96_FROZEN_NOVELTY_BENCHMARK_INVALID")

type Case struct {
 ID string `json:"id"`
 Category string `json:"category"`
 Relations []noveltymechanisms.Relation `json:"relations"`
 Root string `json:"root"`
 Roles []string `json:"roles"`
 ExpectedTargets []string `json:"expected_targets"`
}
type Suite struct{
 Schema string `json:"schema"`
 BaselineSourceSHA string `json:"baseline_source_sha"`
 Origin string `json:"origin"`
 ScientificHoldout bool `json:"scientific_holdout"`
 AllCasesRetained bool `json:"all_cases_retained"`
 Cases []Case `json:"cases"`
}
type ModelResult struct{
 Name string `json:"name"`
 ActualTargets []string `json:"actual_targets"`
 Correct bool `json:"correct"`
 ErrorClass string `json:"error_class"`
}
type CaseResult struct{
 ID string `json:"id"`
 Category string `json:"category"`
 ExpectedTargets []string `json:"expected_targets"`
 Models []ModelResult `json:"models"`
}
type Totals struct{
 Model string `json:"model"`
 Cases int `json:"cases"`
 Correct int `json:"correct"`
 Errors int `json:"errors"`
}
type Report struct{
 Schema string `json:"schema"`
 BaselineSourceSHA string `json:"baseline_source_sha"`
 FixtureFreezeCommit string `json:"fixture_freeze_commit"`
 FixtureBytesSHA256 string `json:"fixture_bytes_sha256"`
 FixtureCaseCount int `json:"fixture_case_count"`
 EveryCaseRetained bool `json:"every_case_retained"`
 Results []CaseResult `json:"results"`
 Totals []Totals `json:"totals"`
 EquivalentReferenceIsRequiredControl bool `json:"equivalent_reference_is_required_control"`
 SyntheticIndependentScience bool `json:"synthetic_independent_science"`
 IndependentSealedHoldoutConsumed bool `json:"independent_sealed_holdout_consumed"`
 AuthenticOriginalFirstUse bool `json:"authentic_original_first_use"`
 AnyScientificSuperiorityEstablished bool `json:"any_scientific_superiority_established"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveAcceptedTrainingEnabled bool `json:"theta_evolve_accepted_training_enabled"`
 AcceptedScientificReferenceMutation bool `json:"accepted_scientific_reference_mutation"`
 ScientificDispatchAuthorized bool `json:"scientific_dispatch_authorized"`
 Status string `json:"status"`
}

func digest(raw []byte) string {
 sum:=sha256.Sum256(raw)
 return hex.EncodeToString(sum[:])
}
func nameOK(s string)bool{
 if len(s)<1||len(s)>48{return false}
 for _,r:=range s{
  if !((r>='a'&&r<='z')||(r>='0'&&r<='9')||r=='-'||r=='_'){return false}
 }
 return true
}
func uniqueSorted(values []string)([]string,error){
 if values==nil{return []string{},nil}
 if len(values)>128{return nil,ErrF96}
 seen:=map[string]bool{}
 out:=make([]string,0,len(values))
 for _,v:=range values{
  if !nameOK(v)||seen[v]{return nil,ErrF96}
  seen[v]=true;out=append(out,v)
 }
 sort.Strings(out)
 return out,nil
}
func same(a,b []string)bool{
 if len(a)!=len(b){return false}
 for i:=range a{if a[i]!=b[i]{return false}}
 return true
}
func decodeStrict(raw []byte)(Suite,error){
 var s Suite
 if len(raw)<100||len(raw)>150000{return s,ErrF96}
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&s);err!=nil{return s,ErrF96}
 var extra any
 if err:=decoder.Decode(&extra);err!=io.EOF{return s,ErrF96}
 if s.Schema!=FixtureSchema||s.BaselineSourceSHA!=BaseF95Commit||
  s.Origin!="AUTHOR_PREPARED_SOURCE_FIXTURES_NOT_INDEPENDENT_SCIENCE"||
  s.ScientificHoldout||!s.AllCasesRetained||len(s.Cases)!=16{return s,ErrF96}
 ids:=map[string]bool{};cats:=map[string]bool{}
 for _,c:=range s.Cases{
  if !nameOK(c.ID)||!nameOK(c.Category)||ids[c.ID]||
   len(c.Relations)<1||len(c.Relations)>128||
   len(c.Roles)<1||len(c.Roles)>8||!nameOK(c.Root){return s,ErrF96}
  ids[c.ID]=true;cats[c.Category]=true
  for _,role:=range c.Roles{if !nameOK(role){return s,ErrF96}}
  exp,err:=uniqueSorted(c.ExpectedTargets)
  if err!=nil||!same(exp,c.ExpectedTargets){return s,ErrF96}
  if _,err:=noveltymechanisms.Compile(c.Relations);err!=nil{return s,ErrF96}
 }
 if len(cats)<7{return s,ErrF96}
 return s,nil
}

// exactReference is an independently coded deterministic typed-graph
// oracle with the SAME expressivity as F95. Tying this strong positive
// control does not demonstrate scientific superiority or generalization.
func exactReference(c Case)([]string,error){
 curr:=map[string]bool{c.Root:true}
 for _,role:=range c.Roles{
  next:=map[string]bool{}
  for _,edge:=range c.Relations{
   if edge.Role==role&&curr[edge.From]{next[edge.To]=true}
  }
  if len(next)>128{return nil,ErrF96}
  curr=next
 }
 out:=make([]string,0,len(curr))
 for v:=range curr{out=append(out,v)}
 sort.Strings(out)
 return out,nil
}
// oneHop is a deliberately weak but meaningful role-filtered direct lookup;
// it cannot consume a role sequence longer than one edge.
func oneHop(c Case)([]string,error){
 if len(c.Roles)!=1{return []string{},nil}
 result:=map[string]bool{}
 for _,edge:=range c.Relations{
  if edge.From==c.Root&&edge.Role==c.Roles[0]{result[edge.To]=true}
 }
 out:=make([]string,0,len(result))
 for v:=range result{out=append(out,v)}
 sort.Strings(out)
 return out,nil
}
// blindHop is a genuine multi-step connectivity baseline with equal maximum
// path length, but no role binding: it traverses all available edge types.
func blindHop(c Case)([]string,error){
 curr:=map[string]bool{c.Root:true}
 for range c.Roles{
  next:=map[string]bool{}
  for _,edge:=range c.Relations{
   if curr[edge.From]{next[edge.To]=true}
  }
  if len(next)>128{return nil,ErrF96}
  curr=next
 }
 out:=make([]string,0,len(curr))
 for v:=range curr{out=append(out,v)}
 sort.Strings(out)
 return out,nil
}
func class(actual,want []string)string{
 if same(actual,want){return "CORRECT"}
 if len(want)==0&&len(actual)>0{return "SPURIOUS_ANSWER"}
 if len(want)>0&&len(actual)==0{return "MISSED_ANSWER"}
 return "WRONG_OR_AMBIGUOUS_BINDING"
}
func EvaluateFrozen(raw []byte)(Report,error){
 var zero Report
 s,err:=decodeStrict(raw)
 if err!=nil{return zero,err}
 names:=[]string{"f95_typed_composition","direct_typed_onehop_control",
  "role_blind_multihop_control","independent_typed_reference_control"}
 totals:=make([]Totals,0,len(names))
 for _,name:=range names{totals=append(totals,Totals{Model:name,Cases:len(s.Cases)})}
 report:=Report{Schema:ReportSchema,BaselineSourceSHA:s.BaselineSourceSHA,
  FixtureFreezeCommit:FrozenBeforeEvaluationCommit,FixtureBytesSHA256:digest(raw),
  FixtureCaseCount:len(s.Cases),EveryCaseRetained:true,
  Results:make([]CaseResult,0,len(s.Cases)),Totals:totals,
  EquivalentReferenceIsRequiredControl:true,
  Status:"FROZEN_SOURCE_FIXTURE_REGRESSION_ONLY_NOT_INDEPENDENT_SCIENTIFIC_ORIGINALS",
 }
 for _,c:=range s.Cases{
  ref,err:=exactReference(c)
  if err!=nil||!same(ref,c.ExpectedTargets){
   return zero,fmt.Errorf("%w:case_expectation_not_verified:%s",ErrF96,c.ID)
  }
  memory,err:=noveltymechanisms.Compile(c.Relations)
  if err!=nil{return zero,ErrF96}
  prediction,err:=noveltymechanisms.Resolve(memory,c.Root,c.Roles)
  if err!=nil{return zero,ErrF96}
  direct,err:=oneHop(c);if err!=nil{return zero,ErrF96}
  blind,err:=blindHop(c);if err!=nil{return zero,ErrF96}
  candidates:=[][]string{prediction.Targets,direct,blind,ref}
  cr:=CaseResult{ID:c.ID,Category:c.Category,ExpectedTargets:c.ExpectedTargets,
   Models:make([]ModelResult,0,len(candidates))}
  for idx,result:=range candidates{
   if result==nil{result=[]string{}}
   sorted,err:=uniqueSorted(result)
   if err!=nil||!same(sorted,result){return zero,ErrF96}
   ok:=same(result,c.ExpectedTargets)
   if ok{report.Totals[idx].Correct++}else{report.Totals[idx].Errors++}
   cr.Models=append(cr.Models,ModelResult{Name:names[idx],
    ActualTargets:result,Correct:ok,ErrorClass:class(result,c.ExpectedTargets)})
  }
  report.Results=append(report.Results,cr)
 }
 return report,nil
}
