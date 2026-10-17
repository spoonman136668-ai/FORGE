// forge-model-free-loop connects the existing native generators and advisory
// evaluator in a scheduled, SOURCE-ONLY synthetic rehearsal. No autonomous
// model inference, prospective science or accepted research record is created.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "strings"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/optimizerstages"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

var errBoundary=errors.New("FORGE_MODEL_FREE_LOOP_SYNTHETIC_ONLY_BOUNDARY")
const schema="forge.model-free.two-lane-untested-advisory.v1"

type laneResult struct {
 Lane string `json:"lane"`
 SourceIdentity string `json:"source_identity"`
 FrozenScreenSHA256 string `json:"frozen_screen_sha256"`
 PromptCandidates int `json:"prompt_candidates"`
 EnvironmentCandidates int `json:"environment_candidates"`
 NegativeRecords int `json:"negative_records"`
 InvalidRecords int `json:"invalid_records"`
 MixedRecords int `json:"mixed_records"`
 ProposalIDs []string `json:"proposal_ids"`
 GeneratorCandidateSHA256 []string `json:"generator_candidate_sha256"`
 PromptArtifacts []promptlineage.Candidate `json:"public_prompt_artifacts"`
 EnvironmentArtifacts []genenv.Candidate `json:"public_environment_artifacts"`
 AllCandidatesUntested bool `json:"all_candidates_untested"`
 FullPopulationScreened bool `json:"full_population_screened"`
 AdvisoryAssessment string `json:"advisory_assessment"`
 ScienceAccepted bool `json:"science_accepted"`
 OriginalDispatchAuthorized bool `json:"original_dispatch_authorized"`
}
type report struct {
 Schema string `json:"schema"`
 SourceCommitSHA string `json:"source_commit_sha"`
 EvidenceType string `json:"evidence_type"`
 Lanes []laneResult `json:"lanes"`
 ModelInvocations int `json:"model_invocations"`
 CodexInvocations int `json:"codex_invocations"`
 NetworkCalls int `json:"network_calls"`
 NewScientificOriginals int `json:"new_scientific_originals"`
 ScientificFirstUseAuthorized bool `json:"scientific_first_use_authorized"`
 RealResearchProgressEstablished bool `json:"real_research_progress_established"`
 PolicyPromotionAuthorized bool `json:"policy_promotion_authorized"`
 AcceptedRefMutations int `json:"accepted_ref_mutations"`
}

// These are SOURCE-INTERNAL SYNTHETIC records, not authentic historical
// research evidence. They intentionally match the F94 frozen test lineage.
func fixture(lane string)(optimizerstages.F94Freeze,promptlineage.Frozen,genenv.Frozen,genenv.History,[]optimizerstages.F94ImplementationClaim){
 source:=strings.Repeat("a",40)
 if lane=="Yggdrasil"{source=strings.Repeat("b",40)}
 hist:=genenv.History{Schema:genenv.HistorySchema,Lane:lane,SourceSHA:source,
  Records:[]genenv.Record{
   {Sequence:1,EvidenceSHA256:strings.Repeat("b",64),TrainingOnly:true,Classification:"NEGATIVE",Vector:[]int64{0,1,1}},
   {Sequence:2,EvidenceSHA256:strings.Repeat("c",64),TrainingOnly:true,Classification:"INVALID",Vector:[]int64{1,0,1}},
   {Sequence:3,EvidenceSHA256:strings.Repeat("d",64),TrainingOnly:true,Classification:"MIXED",Vector:[]int64{1,1,0}},
  },
 }
 prompt:=promptlineage.Frozen{Schema:promptlineage.Schema,Lane:lane,Epoch:1,SourceSHA:source,
  Parent:"reason with bounded evidence",Vocabulary:[]string{"verified","strict"},MaxOperations:2,
  Operations:[]promptlineage.Operation{
   {Kind:"replace",Position:2,Replacement:"verified"},
   {Kind:"swap-next",Position:0},
  },
 }
 env:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:lane,SourceSHA:source,Epoch:1,
  HistorySHA256:genenv.HistoryDigest(hist),Base:[]int64{1,1,1},MaxLevel:3,
  MaxCandidates:2,MaxOperations:3,
  Requests:[]genenv.Request{
   {ID:"new-case-a",Changes:[]genenv.Change{{Index:2,Delta:1}}},
   {ID:"new-case-b",Changes:[]genenv.Change{{Index:0,Delta:1},{Index:1,Delta:1}}},
  },
 }
 freeze:=optimizerstages.F94Freeze{Schema:optimizerstages.F94FreezeSchema,Lane:lane,SourceSHA:source,
  Epoch:1,PromptPlanSHA256:promptlineage.Digest(prompt),
  EnvironmentPlanSHA256:genenv.FrozenDigest(env),TrainingHistorySHA256:genenv.HistoryDigest(hist),
  ParentRepresentationSHA256:strings.Repeat("5",64),ParentConsumerSHA256:strings.Repeat("6",64),
  ParentTestEnvironmentSHA256:strings.Repeat("7",64),FrozenTestProtocolSHA256:strings.Repeat("e",64),
  FrozenControlsSHA256:[]string{strings.Repeat("8",64),strings.Repeat("9",64)},
  MinimumHistoricalDistance:1,MaximumProposals:4,
 }
 prompts,_:=promptlineage.Generate(prompt,freeze.PromptPlanSHA256)
 envs,_:=genenv.Generate(env,freeze.EnvironmentPlanSHA256,hist,freeze.TrainingHistorySHA256)
 links:=[]optimizerstages.F94ImplementationClaim{
  {Generator:"Promptbreeder",GeneratorCandidateSHA256:prompts.Candidates[0].CandidateSHA256,
   NewRepresentationSHA256:strings.Repeat("a",64),NewConsumerSHA256:strings.Repeat("b",64),
   NewTestEnvironmentSHA256:freeze.ParentTestEnvironmentSHA256},
  {Generator:"Promptbreeder",GeneratorCandidateSHA256:prompts.Candidates[1].CandidateSHA256,
   NewRepresentationSHA256:strings.Repeat("c",64),NewConsumerSHA256:strings.Repeat("d",64),
   NewTestEnvironmentSHA256:freeze.ParentTestEnvironmentSHA256},
  {Generator:"DGM/GenEnv",GeneratorCandidateSHA256:envs.Candidates[0].EnvironmentSHA256,
   NewRepresentationSHA256:freeze.ParentRepresentationSHA256,
   NewConsumerSHA256:strings.Repeat("a",64),NewTestEnvironmentSHA256:strings.Repeat("b",64)},
  {Generator:"DGM/GenEnv",GeneratorCandidateSHA256:envs.Candidates[1].EnvironmentSHA256,
   NewRepresentationSHA256:strings.Repeat("f",64),
   NewConsumerSHA256:freeze.ParentConsumerSHA256,NewTestEnvironmentSHA256:strings.Repeat("c",64)},
 }
 return freeze,prompt,env,hist,links
}
func hex40(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func execute(source string)(report,error){
 var zero report
 if !hex40(source){return zero,errBoundary}
 out:=report{Schema:schema,SourceCommitSHA:source,
  EvidenceType:"SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE",
  Lanes:make([]laneResult,0,2)}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  f,p,e,h,links:=fixture(lane)
  digest:=optimizerstages.F94FreezeDigest(f)
  prompts,perr:=promptlineage.Generate(p,f.PromptPlanSHA256)
  envs,eerr:=genenv.Generate(e,f.EnvironmentPlanSHA256,h,f.TrainingHistorySHA256)
  if perr!=nil||eerr!=nil{return zero,errBoundary}
  review,err:=optimizerstages.ScreenF94(f,digest,p,e,h,links)
  if err!=nil{return zero,fmt.Errorf("%w: %s: %v",errBoundary,lane,err)}
  stage,err:=optimizerstages.AssessActivation(nil,nil,review.StageProposals,nil)
  if err!=nil{return zero,fmt.Errorf("%w: stage %s: %v",errBoundary,lane,err)}
  if len(review.CandidateScreens)!=4||len(review.StageProposals)!=4||
   review.GeneratedPromptCandidates!=2||review.GeneratedEnvironmentCandidates!=2||
   review.NegativeHistoricalRecords!=1||review.InvalidHistoricalRecords!=1||
   review.MixedHistoricalRecords!=1||!review.UnmodifiedProposalPopulationPreserved||
   !review.SourceOnlyStructuralClaimsConsistent||
   review.StructuralSourceChangesIndependentlyVerified||
   review.NovelScientificMechanismDemonstrated||
   review.ScientificHoldoutConsumed||review.IndependentlyAcceptedScientificResults||
   review.ScientificOriginalDispatchAuthorized||review.AcceptedReferenceMutation||
   review.DreamParetoPromotionAuthorized||review.ThetaEvolveAcceptedTrainingEnabled||
   stage.ScientificOriginalDispatchAuthorized||stage.AuthenticatedProspectiveResearchSelection||
   stage.ControllerCutoverAuthorized||stage.AcceptedRefMutation||
   stage.PromptbreederAndGenEnv!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"{
   return zero,errBoundary
  }
  ids:=make([]string,0,len(review.CandidateScreens))
  sourceIDs:=make([]string,0,len(review.CandidateScreens))
  for _,candidate:=range review.CandidateScreens{
   if candidate.Status!="UNTESTED_ARTIFACT_SHA_CLAIMS_NOT_VERIFIED_CODE_OR_SCIENCE"{
    return zero,errBoundary
   }
   ids=append(ids,candidate.ProposedMechanismSHA256)
   sourceIDs=append(sourceIDs,candidate.GeneratorCandidateSHA256)
  }
  out.Lanes=append(out.Lanes,laneResult{Lane:lane,SourceIdentity:f.SourceSHA,
   FrozenScreenSHA256:digest,PromptCandidates:2,EnvironmentCandidates:2,
   NegativeRecords:1,InvalidRecords:1,MixedRecords:1,ProposalIDs:ids,
   GeneratorCandidateSHA256:sourceIDs,
   PromptArtifacts:prompts.Candidates,EnvironmentArtifacts:envs.Candidates,
   AllCandidatesUntested:true,FullPopulationScreened:true,
   AdvisoryAssessment:stage.PromptbreederAndGenEnv})
 }
 return out,nil
}
func run(args []string)(report,error){
 f:=flag.NewFlagSet("forge-model-free-loop",flag.ContinueOnError)
 fixtureOnly:=f.Bool("synthetic-only",false,"require synthetic-only advisory")
 source:=f.String("source-ref","","exact Git commit under source-only qualification")
 if err:=f.Parse(args);err!=nil{return report{},err}
 if !*fixtureOnly||f.NArg()!=0{return report{},errBoundary}
 if expected:=os.Getenv("GITHUB_SHA");expected!=""&&expected!=*source{return report{},errBoundary}
 return execute(*source)
}
func main(){
 result,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err:=json.NewEncoder(os.Stdout).Encode(result);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
