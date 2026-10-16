package optimizerbridge

import (
 "errors"
 "reflect"
 "testing"
)
func genuineF57FITSources()[]F57StructuralInput{
 return []F57StructuralInput{
  {Lane:"Wingless",SourceSHA:"4f30c36b53bb6a6a472a50a6545850b286590384",
   OriginalFITRun:38827325626,
   FITResultSHA256:"ec7743b0782dc6df4bf6e58ddb3f7bf8b822f8df935d98ffc664e891a5cffe6b",
   IndependentAuditSHA256:"de974b26919a05ed983e02059590d75d0b1cce7709313ea2068cba61eeaab851",
   FITCases:64,CandidateCorrect:49,StrongestFairCorrect:44},
  {Lane:"Yggdrasil",SourceSHA:"e6c2aa8fc0b0a2d4acb5eded160d34e9fa85c3b6",
   OriginalFITRun:38827162260,
   FITResultSHA256:"a81faaea92517833041aaa9e1d518b3fabaf096f3f7c1e70eaf7866654148bef",
   IndependentAuditSHA256:"7318b18d83121892eb2b377a5d1cfa30f5de83669bdba3f809f790aafe0b8e78",
   FITCases:64,CandidateCorrect:29,StrongestFairCorrect:29},
 }
}
func TestF57GenuineFITNoveltyIsBoundedAndNeverAnActivation(t *testing.T){
 evidence:=genuineF57FITSources()
 report,err:=PrepareF57Novelty(evidence)
 if err!=nil{t.Fatal(err)}
 if report.Schema!="forge.f57.authentic-fit-novelty-advisory.v1"||
  report.Mode!="BOUNDED_PROMPTBREEDER_AND_GENENV_STRUCTURAL_PROPOSALS_ONLY"||
  !report.NovelProposalsAreOnlyUntested||len(report.Proposals)!=2||
  report.ScientificOriginalsExecuted!=0||report.ControllerDispatchAuthorized||
  report.AcceptedRefMutation||report.DreamParetoProspectivelyQualified||
  report.ThetaEvolveIndependentAcceptanceEligible{
  t.Fatalf("unsafe novelty classification: %+v",report)
 }
 repeat,err:=PrepareF57Novelty(genuineF57FITSources())
 if err!=nil||!reflect.DeepEqual(report,repeat){t.Fatal("not deterministic",err)}
 w,y:=report.Proposals[0],report.Proposals[1]
 if w.Generator!="Promptbreeder"||y.Generator!="DGM/GenEnv"||
  w.NewRepresentation==w.ParentRepresentation||y.NewRepresentation==y.ParentRepresentation||
  w.NewConsumer==w.ParentConsumer||y.NewConsumer==y.ParentConsumer||
  w.NewTestEnvironment==w.ParentTestEnvironment||y.NewTestEnvironment==y.ParentTestEnvironment||
  w.Status!="UNTESTED"||y.Status!="UNTESTED"||
  w.CandidateSHA256==y.CandidateSHA256{
  t.Fatalf("cosmetic or duplicate proposal %+v %+v",w,y)
 }
 activated,err:=AssessActivation(nil,nil,report.Proposals,nil)
 if err!=nil||activated.DreamPareto!="WAITING_AUTHENTIC_PROSPECTIVE_COMPARISON"||
  activated.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
  activated.PromptbreederAndGenEnv!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"||
  activated.ControllerCutoverAuthorized||activated.ScientificOriginalDispatchAuthorized||
  activated.ScientificOriginalDispatchAuthorized||activated.AcceptedRefMutation{
  t.Fatalf("proposal falsely promoted policy or experiment: %+v %v",activated,err)
 }
}
func TestF57NoveltiesRejectFalseSourceAndTrainingClaims(t *testing.T){
 seed:=genuineF57FITSources()
 for name,mutate:=range map[string]func([]F57StructuralInput){
  "missing lane":func(v []F57StructuralInput){v[1].Lane=""},
  "same first-use run":func(v []F57StructuralInput){v[1].OriginalFITRun=v[0].OriginalFITRun},
  "reused source":func(v []F57StructuralInput){v[1].SourceSHA=v[0].SourceSHA},
  "duplicate report":func(v []F57StructuralInput){v[1].FITResultSHA256=v[0].FITResultSHA256},
  "dubious audit":func(v []F57StructuralInput){v[0].IndependentAuditSHA256=""},
  "false scientific acceptance":func(v []F57StructuralInput){v[0].ScientificAccepted=true},
  "consumed diagnostic":func(v []F57StructuralInput){v[1].DiagnosticExecuted=true},
  "wrong positive claim":func(v []F57StructuralInput){v[1].CandidateCorrect=64},
 }{
  t.Run(name,func(t *testing.T){
   v:=append([]F57StructuralInput(nil),seed...)
   mutate(v)
   if _,err:=PrepareF57Novelty(v);!errors.Is(err,ErrF57Novelty){
    t.Fatalf("unqualified novelty accepted %v",err)
   }
  })
 }
}
