package main

import (
 "bytes"
 "encoding/json"
 "os"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/optimizerstages"
)

const sampleCommit="b61fa60084fc487b4d010b3662a2b85872488deb"

func TestFrozenSourceOnlyDualLaneAdvisory(t *testing.T){
 a,err:=execute(sampleCommit)
 if err!=nil{t.Fatal(err)}
 b,err:=execute(sampleCommit)
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatalf("nondeterministic bounded loop %v",err)}
 if len(a.Lanes)!=2||a.Lanes[0].Lane!="Wingless"||a.Lanes[1].Lane!="Yggdrasil"||
  a.Lanes[0].SourceIdentity==a.Lanes[1].SourceIdentity||
  a.ModelInvocations!=0||a.CodexInvocations!=0||a.NetworkCalls!=0||
  a.NewScientificOriginals!=0||a.ScientificFirstUseAuthorized||
  a.RealResearchProgressEstablished||a.PolicyPromotionAuthorized||a.AcceptedRefMutations!=0||
  !strings.Contains(a.EvidenceType,"SYNTHETIC"){
  t.Fatalf("synthetic advisory claimed real autonomous science: %+v",a)
 }
 unique:=map[string]bool{}
 for _,lane:=range a.Lanes{
  if lane.PromptCandidates!=2||lane.EnvironmentCandidates!=2||
   lane.NegativeRecords!=1||lane.MixedRecords!=1||lane.InvalidRecords!=1||
   !lane.AllCandidatesUntested||!lane.FullPopulationScreened||
   lane.ScienceAccepted||lane.OriginalDispatchAuthorized||
   len(lane.ProposalIDs)!=4||lane.AdvisoryAssessment!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"{
   t.Fatalf("lane authority or candidate population drift: %+v",lane)
  }
  for _,id:=range lane.ProposalIDs{
   if unique[id]{t.Fatalf("cross-lane candidate ID alias: %s",id)}
   unique[id]=true
  }
 }
 raw,err:=json.Marshal(a)
 if err!=nil{t.Fatal(err)}
 for _,flag:=range [][]byte{
  []byte(`"scientific_first_use_authorized":false`),
  []byte(`"real_research_progress_established":false`),
  []byte(`"new_scientific_originals":0`),
 }{
  if !bytes.Contains(raw,flag){t.Fatalf("missing nonauthority output field %s",flag)}
 }
}
func TestRejectNonSyntheticAndSourceSpoof(t *testing.T){
 t.Setenv("GITHUB_SHA","")
 for _,args:=range [][]string{
  nil,
  {"--source-ref",sampleCommit},
  {"--synthetic-only"},
  {"--synthetic-only","--source-ref","f"},
  {"--synthetic-only","--source-ref",strings.Repeat("A",40)},
  {"--synthetic-only","--source-ref",sampleCommit,"extra"},
 }{
  if _,err:=run(args);err==nil{t.Fatalf("unsafe CLI allowed args %+v",args)}
 }
 t.Setenv("GITHUB_SHA",strings.Repeat("f",40))
 if _,err:=run([]string{"--synthetic-only","--source-ref",sampleCommit});err==nil{
  t.Fatal("untrusted source overrode workflow commit identity")
 }
 t.Setenv("GITHUB_SHA",sampleCommit)
 if _,err:=run([]string{"--synthetic-only","--source-ref",sampleCommit});err!=nil{t.Fatal(err)}
}
func TestTamperedFrozenPlanOrMissingCompleteGeneratorCohort(t *testing.T){
 f,p,e,h,links:=fixture("Wingless")
 p.Operations[0].Replacement="strict"
 if _,err:=optimizerstages.ScreenF94(f,optimizerstages.F94FreezeDigest(f),p,e,h,links);err==nil{
  t.Fatal("mutated candidate plan passed frozen source gate")
 }
 f,p,e,h,links=fixture("Wingless")
 if _,err:=optimizerstages.ScreenF94(f,optimizerstages.F94FreezeDigest(f),p,e,h,links[:3]);err==nil{
  t.Fatal("cherry-picked candidate subset passed")
 }
 f,p,e,h,links=fixture("Wingless")
 h.Records[0].Classification="SUPPORTED"
 if _,err:=optimizerstages.ScreenF94(f,optimizerstages.F94FreezeDigest(f),p,e,h,links);err==nil{
  t.Fatal("historical negative relabeled as positive")
 }
 f,p,e,h,links=fixture("Yggdrasil")
 f.FrozenControlsSHA256=f.FrozenControlsSHA256[:1]
 if _,err:=optimizerstages.ScreenF94(f,optimizerstages.F94FreezeDigest(f),p,e,h,links);err==nil{
  t.Fatal("removed frozen negative control passed")
 }
}
func TestNoRuntimeCredentialOrImplicitModelExecutor(t *testing.T){
 t.Setenv("OPENAI_API_KEY","SHOULD_NOT_BE_USED")
 t.Setenv("CODEX_HOME","SHOULD_NOT_BE_USED")
 t.Setenv("NVIDIA_API_KEY","SHOULD_NOT_BE_USED")
 t.Setenv("GITHUB_SHA","")
 a,err:=run([]string{"--synthetic-only","--source-ref",sampleCommit})
 if err!=nil||a.CodexInvocations!=0||a.NetworkCalls!=0||a.ModelInvocations!=0{
  t.Fatalf("source-only run depended on external model or keys: %+v %v",a,err)
 }
}
