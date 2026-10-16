package optimizerstages

// F94 combines REAL outputs from FORGE's existing Promptbreeder-style
// promptlineage and DGM/GenEnv generators into a bounded, source-only novelty
// proposal screen. A claimed artifact digest is NOT proof that the artifact
// exists or that the mechanism works; no proposal becomes scientific evidence.
import (
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

const F94FreezeSchema="forge.optimizer.f94.structural-novelty-freeze.v1"
const F94ReviewSchema="forge.optimizer.f94.generator-joined-untested-structure.v1"
const F94Status="UNTESTED_STRUCTURAL_CLAIMS_REQUIRE_INDEPENDENT_IMPLEMENTATION_AND_EXPERIMENT"
var ErrF94=errors.New("FORGE_F94_FROZEN_NOVELTY_LINEAGE_OR_STRUCTURAL_CLAIM_UNQUALIFIED")

// F94Freeze is the preregistration of what constitutes a substantively
// different mechanism. independentPin is expected from outside the producer;
// the function only checks equality, never establishes the pin's custody.
type F94Freeze struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 Epoch uint64 `json:"epoch"`
 PromptPlanSHA256 string `json:"prompt_plan_sha256"`
 EnvironmentPlanSHA256 string `json:"environment_plan_sha256"`
 TrainingHistorySHA256 string `json:"training_history_sha256"`
 ParentRepresentationSHA256 string `json:"parent_representation_sha256"`
 ParentConsumerSHA256 string `json:"parent_consumer_sha256"`
 ParentTestEnvironmentSHA256 string `json:"parent_test_environment_sha256"`
 FrozenTestProtocolSHA256 string `json:"frozen_test_protocol_sha256"`
 FrozenControlsSHA256 []string `json:"frozen_controls_sha256"`
 MinimumHistoricalDistance int64 `json:"minimum_historical_distance"`
 MaximumProposals int `json:"maximum_proposals"`
}
// Each link is an UNVERIFIED proposed future code/artifact change. A candidate
// from either generator must provide at least two independently named
// structural dimensions differing from the common frozen parent, and a
// declared test environment. These SHA claims can be forged and are not
// source-code diff validation, build receipts or scientific admissions.
type F94ImplementationClaim struct {
 Generator string `json:"generator"`
 GeneratorCandidateSHA256 string `json:"generator_candidate_sha256"`
 NewRepresentationSHA256 string `json:"new_representation_sha256"`
 NewConsumerSHA256 string `json:"new_consumer_sha256"`
 NewTestEnvironmentSHA256 string `json:"new_test_environment_sha256"`
}
type F94CandidateScreen struct {
 Generator string `json:"generator"`
 GeneratorCandidateSHA256 string `json:"generator_candidate_sha256"`
 ProposedMechanismSHA256 string `json:"proposed_mechanism_sha256"`
 ChangedDimensions []string `json:"changed_dimensions"`
 HistoricalDistance int64 `json:"historical_distance"`
 FrozenControlCount int `json:"frozen_control_count"`
 Status string `json:"status"`
}
type F94NoveltyReview struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenScreenSHA256 string `json:"frozen_screen_sha256"`
 PromptLineageSHA256 string `json:"prompt_lineage_sha256"`
 EnvironmentHistorySHA256 string `json:"environment_history_sha256"`
 GeneratedPromptCandidates int `json:"generated_prompt_candidates"`
 GeneratedEnvironmentCandidates int `json:"generated_environment_candidates"`
 NegativeHistoricalRecords int `json:"negative_historical_records"`
 InvalidHistoricalRecords int `json:"invalid_historical_records"`
 MixedHistoricalRecords int `json:"mixed_historical_records"`
 UnmodifiedProposalPopulationPreserved bool `json:"unmodified_proposal_population_preserved"`
 CandidateScreens []F94CandidateScreen `json:"candidate_screens"`
 SourceOnlyStructuralClaimsConsistent bool `json:"source_only_structural_claims_consistent"`
 StructuralSourceChangesIndependentlyVerified bool `json:"structural_source_changes_independently_verified"`
 NovelScientificMechanismDemonstrated bool `json:"novel_scientific_mechanism_demonstrated"`
 ScientificHoldoutConsumed bool `json:"scientific_holdout_consumed"`
 IndependentlyAcceptedScientificResults bool `json:"independently_accepted_scientific_results"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveAcceptedTrainingEnabled bool `json:"theta_evolve_accepted_training_enabled"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedReferenceMutation bool `json:"accepted_reference_mutation"`
 Status string `json:"status"`
}

func F94FreezeDigest(f F94Freeze)string{return f93Hash("FORGE-F94-FROZEN-NOVELTY-V1",f)}
func f94FreezeValid(f F94Freeze)bool{
 if f.Schema!=F94FreezeSchema||!checkLane(f.Lane)||f.Epoch==0||
  !exactHex(f.SourceSHA,40)||f.MinimumHistoricalDistance<1||
  f.MaximumProposals<2||f.MaximumProposals>32||
  len(f.FrozenControlsSHA256)<2||len(f.FrozenControlsSHA256)>8{return false}
 pins:=[]string{
  f.PromptPlanSHA256,f.EnvironmentPlanSHA256,f.TrainingHistorySHA256,
  f.ParentRepresentationSHA256,f.ParentConsumerSHA256,
  f.ParentTestEnvironmentSHA256,f.FrozenTestProtocolSHA256,
 }
 pins=append(pins,f.FrozenControlsSHA256...)
 seen:=map[string]bool{}
 for _,h:=range pins{
  if !exactHex(h,64)||seen[h]{return false}
  seen[h]=true
 }
 return true
}
func f94Changed(f F94Freeze,l F94ImplementationClaim)([]string,bool){
 vals:=[]struct{name,parent,after string}{
  {"representation",f.ParentRepresentationSHA256,l.NewRepresentationSHA256},
  {"consumer",f.ParentConsumerSHA256,l.NewConsumerSHA256},
  {"test_environment",f.ParentTestEnvironmentSHA256,l.NewTestEnvironmentSHA256},
 }
 changed:=[]string{}
 seen:=map[string]bool{}
 for _,v:=range vals{
  if !exactHex(v.after,64)||seen[v.after]{return nil,false}
  seen[v.after]=true
  if v.parent!=v.after{changed=append(changed,v.name)}
 }
 return changed,len(changed)>=2
}

// ScreenF94 regenerates both source-only populations rather than trusting
// caller-supplied result blobs. The complete bounded proposal population MUST
// be provided; subsets are rejected to deter cherry-picking novelty wins.
// No model, network, Cloudflare, filesystem, controller or sealed results.
func ScreenF94(f F94Freeze,independentPin string,
 pf promptlineage.Frozen,ef genenv.Frozen,h genenv.History,
 links []F94ImplementationClaim)(F94NoveltyReview,error){
 var zero F94NoveltyReview
 if !f94FreezeValid(f)||!exactHex(independentPin,64)||
  F94FreezeDigest(f)!=independentPin||
  pf.Lane!=f.Lane||ef.Lane!=f.Lane||h.Lane!=f.Lane||
  pf.SourceSHA!=f.SourceSHA||ef.SourceSHA!=f.SourceSHA||
  h.SourceSHA!=f.SourceSHA||pf.Epoch!=f.Epoch||ef.Epoch!=f.Epoch||
  promptlineage.Digest(pf)!=f.PromptPlanSHA256||
  genenv.FrozenDigest(ef)!=f.EnvironmentPlanSHA256||
  genenv.HistoryDigest(h)!=f.TrainingHistorySHA256||
  ef.HistorySHA256!=f.TrainingHistorySHA256{return zero,ErrF94}
 prompts,err:=promptlineage.Generate(pf,f.PromptPlanSHA256)
 if err!=nil{return zero,fmt.Errorf("%w:prompt_lineage",ErrF94)}
 env,err:=genenv.Generate(ef,f.EnvironmentPlanSHA256,h,f.TrainingHistorySHA256)
 if err!=nil{return zero,fmt.Errorf("%w:environment_lineage",ErrF94)}
 if prompts.ScientificAccepted||prompts.DispatchAuthorized||prompts.SealedEvaluationConsumed||
  env.ScientificAccepted||env.DispatchAuthorized||env.SealedHoldoutConsumed||
  len(prompts.Candidates)==0||len(env.Candidates)==0||
  len(links)!=len(prompts.Candidates)+len(env.Candidates)||
  len(links)>f.MaximumProposals{return zero,ErrF94}
 expected:=map[string]int64{}
 for _,c:=range prompts.Candidates{
  if c.Classification!="UNTESTED"||!exactHex(c.CandidateSHA256,64){return zero,ErrF94}
  expected["Promptbreeder:"+c.CandidateSHA256]=0
 }
 for _,c:=range env.Candidates{
  if c.Classification!="UNTESTED_PROPOSAL"||!exactHex(c.EnvironmentSHA256,64)||
   c.HistoricalDistance<f.MinimumHistoricalDistance{return zero,ErrF94}
  expected["DGM/GenEnv:"+c.EnvironmentSHA256]=c.HistoricalDistance
 }
 result:=F94NoveltyReview{
  Schema:F94ReviewSchema,Lane:f.Lane,FrozenScreenSHA256:independentPin,
  PromptLineageSHA256:f.PromptPlanSHA256,
  EnvironmentHistorySHA256:f.TrainingHistorySHA256,
  GeneratedPromptCandidates:len(prompts.Candidates),
  GeneratedEnvironmentCandidates:len(env.Candidates),
  NegativeHistoricalRecords:env.NegativeCount,
  InvalidHistoricalRecords:env.InvalidCount,
  MixedHistoricalRecords:env.MixedCount,
  CandidateScreens:make([]F94CandidateScreen,0,len(links)),
  Status:F94Status,
 }
 usedCandidate:=map[string]bool{}
 usedMechanism:=map[string]bool{}
 usedCombination:=map[string]bool{}
 for _,l:=range links{
  key:=l.Generator+":"+l.GeneratorCandidateSHA256
  distance,found:=expected[key]
  if !found||usedCandidate[key]||!exactHex(l.GeneratorCandidateSHA256,64){return zero,ErrF94}
  changed,ok:=f94Changed(f,l)
  if !ok{return zero,ErrF94}
  fingerprint:=f93Hash("FORGE-F94-STRUCTURAL-FINGERPRINT-V1",
   []string{l.NewRepresentationSHA256,l.NewConsumerSHA256,l.NewTestEnvironmentSHA256})
  if usedCombination[fingerprint]{return zero,ErrF94}
  usedCombination[fingerprint]=true
  id:=f93Hash("FORGE-F94-CANDIDATE-LINEAGE-V1",struct{
   FrozenSHA string
   SourceSHA string
   Generator string
   CandidateSHA string
   Fingerprint string
   TestProtocolSHA string
  }{independentPin,f.SourceSHA,l.Generator,l.GeneratorCandidateSHA256,
   fingerprint,f.FrozenTestProtocolSHA256})
  if usedMechanism[id]{return zero,ErrF94}
  usedMechanism[id]=true;usedCandidate[key]=true
  result.CandidateScreens=append(result.CandidateScreens,F94CandidateScreen{
   Generator:l.Generator,GeneratorCandidateSHA256:l.GeneratorCandidateSHA256,
   ProposedMechanismSHA256:id,ChangedDimensions:changed,
   HistoricalDistance:distance,FrozenControlCount:len(f.FrozenControlsSHA256),
   Status:"UNTESTED_ARTIFACT_SHA_CLAIMS_NOT_VERIFIED_CODE_OR_SCIENCE",
  })
 }
 if len(usedCandidate)!=len(expected){return zero,ErrF94}
 result.UnmodifiedProposalPopulationPreserved=true
 result.SourceOnlyStructuralClaimsConsistent=true
 return result,nil
}
