package optimizerstages

import (
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

func f94Base(lane string)(F94Freeze,promptlineage.Frozen,genenv.Frozen,genenv.History,[]F94ImplementationClaim){
 source:=strings.Repeat("a",40)
 if lane=="Yggdrasil"{source=strings.Repeat("b",40)}
 h:=genenv.History{Schema:genenv.HistorySchema,Lane:lane,SourceSHA:source,
  Records:[]genenv.Record{
   {Sequence:1,EvidenceSHA256:strings.Repeat("b",64),TrainingOnly:true,
    Classification:"NEGATIVE",Vector:[]int64{0,1,1}},
   {Sequence:2,EvidenceSHA256:strings.Repeat("c",64),TrainingOnly:true,
    Classification:"INVALID",Vector:[]int64{1,0,1}},
  },
 }
 pf:=promptlineage.Frozen{Schema:promptlineage.Schema,Lane:lane,Epoch:1,
  SourceSHA:source,Parent:"reason with bounded evidence",
  Vocabulary:[]string{"verified","strict"},MaxOperations:2,
  Operations:[]promptlineage.Operation{
   {Kind:"replace",Position:2,Replacement:"verified"},
   {Kind:"swap-next",Position:0},
  },
 }
 ef:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:lane,SourceSHA:source,Epoch:1,
  HistorySHA256:genenv.HistoryDigest(h),Base:[]int64{1,1,1},
  MaxLevel:3,MaxCandidates:2,MaxOperations:3,
  Requests:[]genenv.Request{
   {ID:"new-case-a",Changes:[]genenv.Change{{Index:2,Delta:1}}},
   {ID:"new-case-b",Changes:[]genenv.Change{{Index:0,Delta:1},{Index:1,Delta:1}}},
  },
 }
 freeze:=F94Freeze{Schema:F94FreezeSchema,Lane:lane,SourceSHA:source,Epoch:1,
  PromptPlanSHA256:promptlineage.Digest(pf),
  EnvironmentPlanSHA256:genenv.FrozenDigest(ef),
  TrainingHistorySHA256:genenv.HistoryDigest(h),
  ParentRepresentationSHA256:strings.Repeat("5",64),
  ParentConsumerSHA256:strings.Repeat("6",64),
  ParentTestEnvironmentSHA256:strings.Repeat("7",64),
  FrozenTestProtocolSHA256:strings.Repeat("e",64),
  FrozenControlsSHA256:[]string{strings.Repeat("8",64),strings.Repeat("9",64)},
  MinimumHistoricalDistance:1,MaximumProposals:4,
 }
 p,_:=promptlineage.Generate(pf,freeze.PromptPlanSHA256)
 e,_:=genenv.Generate(ef,freeze.EnvironmentPlanSHA256,h,freeze.TrainingHistorySHA256)
 links:=[]F94ImplementationClaim{
  {Generator:"Promptbreeder",GeneratorCandidateSHA256:p.Candidates[0].CandidateSHA256,
   NewRepresentationSHA256:strings.Repeat("a",64),
   NewConsumerSHA256:strings.Repeat("b",64),
   NewTestEnvironmentSHA256:freeze.ParentTestEnvironmentSHA256},
  {Generator:"Promptbreeder",GeneratorCandidateSHA256:p.Candidates[1].CandidateSHA256,
   NewRepresentationSHA256:strings.Repeat("c",64),
   NewConsumerSHA256:strings.Repeat("d",64),
   NewTestEnvironmentSHA256:freeze.ParentTestEnvironmentSHA256},
  {Generator:"DGM/GenEnv",GeneratorCandidateSHA256:e.Candidates[0].EnvironmentSHA256,
   NewRepresentationSHA256:freeze.ParentRepresentationSHA256,
   NewConsumerSHA256:strings.Repeat("a",64),
   NewTestEnvironmentSHA256:strings.Repeat("b",64)},
  {Generator:"DGM/GenEnv",GeneratorCandidateSHA256:e.Candidates[1].EnvironmentSHA256,
   NewRepresentationSHA256:strings.Repeat("f",64),
   NewConsumerSHA256:freeze.ParentConsumerSHA256,
   NewTestEnvironmentSHA256:strings.Repeat("c",64)},
 }
 return freeze,pf,ef,h,links
}
func TestF94TwoGeneratorOutputsEnterRealStageAdvisory(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   f,p,e,h,links:=f94Base(lane)
   a,err:=ScreenF94(f,F94FreezeDigest(f),p,e,h,links)
   if err!=nil{t.Fatal(err)}
   b,err:=ScreenF94(f,F94FreezeDigest(f),p,e,h,links)
   if err!=nil||!reflect.DeepEqual(a,b){t.Fatalf("not deterministic %v",err)}
   if a.Lane!=lane||a.Schema!=F94ReviewSchema||
    a.GeneratedPromptCandidates!=2||a.GeneratedEnvironmentCandidates!=2||
    a.NegativeHistoricalRecords!=1||a.InvalidHistoricalRecords!=1||
    a.MixedHistoricalRecords!=0||len(a.CandidateScreens)!=4||
    len(a.StageProposals)!=4||!a.UnmodifiedProposalPopulationPreserved||
    !a.SourceOnlyStructuralClaimsConsistent||
    a.StructuralSourceChangesIndependentlyVerified||
    a.NovelScientificMechanismDemonstrated||
    a.ScientificHoldoutConsumed||a.IndependentlyAcceptedScientificResults||
    a.DreamParetoPromotionAuthorized||a.ThetaEvolveAcceptedTrainingEnabled||
    a.ScientificOriginalDispatchAuthorized||a.AcceptedReferenceMutation{
    t.Fatalf("unsafe joined novelty review %+v",a)
   }
   for i,c:=range a.CandidateScreens{
    if len(c.ChangedDimensions)!=2||c.Status!="UNTESTED_ARTIFACT_SHA_CLAIMS_NOT_VERIFIED_CODE_OR_SCIENCE"||
     !exactHex(c.ProposedMechanismSHA256,64)||!validMechanism(a.StageProposals[i]){
     t.Fatalf("unverified structural output elevated %+v",c)
    }
   }
   for _,c:=range a.CandidateScreens[2:]{
    if c.HistoricalDistance<1{t.Fatalf("historical negatives ignored %+v",c)}
   }
   outcome,err:=AssessActivation(nil,nil,a.StageProposals,nil)
   if err!=nil||outcome.PromptbreederAndGenEnv!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"||
    outcome.AuthenticatedProspectiveResearchSelection||outcome.AcceptedRefMutation||
    outcome.ScientificOriginalDispatchAuthorized||outcome.ControllerCutoverAuthorized{
    t.Fatalf("source claims became optimizer authority %+v %v",outcome,err)
   }
  })
 }
}
func TestF94MissingAndCherryPickedGeneratorPopulationRejected(t *testing.T){
 f,p,e,h,links:=f94Base("Wingless")
 cases:=map[string]func(*F94Freeze,*promptlineage.Frozen,*genenv.Frozen,*genenv.History,*[]F94ImplementationClaim){
  "missing candidate":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){*l=(*l)[:3]},
  "duplicate candidate":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[3]=(*l)[0]},
  "relabel generator":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[0].Generator="DGM/GenEnv"},
  "unknown candidate":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[0].GeneratorCandidateSHA256=strings.Repeat("0",64)},
  "only prompt mutation":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[0].NewConsumerSHA256=q.ParentConsumerSHA256},
  "unchanged artifact":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[0].NewRepresentationSHA256=q.ParentRepresentationSHA256},
  "invalid claimed digest":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[0].NewRepresentationSHA256="unsigned"},
  "reused structural output":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,l *[]F94ImplementationClaim){(*l)[1].NewRepresentationSHA256=(*l)[0].NewRepresentationSHA256;(*l)[1].NewConsumerSHA256=(*l)[0].NewConsumerSHA256},
  "freeze one operation":func(_ *F94Freeze,p *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){p.Operations=p.Operations[:1]},
  "changed training history":func(_ *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,h *genenv.History,_ *[]F94ImplementationClaim){h.Records[0].Classification="SUPPORTED"},
  "changed environment":func(_ *F94Freeze,_ *promptlineage.Frozen,e *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){e.Base[1]=2},
  "historical distance too small":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){q.MinimumHistoricalDistance=2},
  "insufficient operations":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){q.MaximumProposals=3},
  "only one control":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){q.FrozenControlsSHA256=q.FrozenControlsSHA256[:1]},
  "duplicated controls":func(q *F94Freeze,_ *promptlineage.Frozen,_ *genenv.Frozen,_ *genenv.History,_ *[]F94ImplementationClaim){q.FrozenControlsSHA256[1]=q.FrozenControlsSHA256[0]},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   f1,p1,e1,h1,l1:=f94Base("Wingless")
   mutate(&f1,&p1,&e1,&h1,&l1)
   if _,err:=ScreenF94(f1,F94FreezeDigest(f1),p1,e1,h1,l1);err==nil{
    t.Fatalf("unsafe novelty case passed %s",name)
   }
  })
 }
 if _,err:=ScreenF94(f,strings.Repeat("0",64),p,e,h,links);err==nil{
  t.Fatal("independently frozen pin ignored")
 }
}
func TestF94OneLaneDoesNotRequireOtherLaneScience(t *testing.T){
 f,p,e,h,links:=f94Base("Yggdrasil")
 r,err:=ScreenF94(f,F94FreezeDigest(f),p,e,h,links)
 if err!=nil||r.Lane!="Yggdrasil"||len(r.StageProposals)!=4{
  t.Fatalf("Yggdrasil advisory blocked by absent Wingless evidence: %v",err)
 }
 if r.ScientificOriginalDispatchAuthorized||r.ThetaEvolveAcceptedTrainingEnabled{
  t.Fatal("independent advisory became scientific execution")
 }
}
