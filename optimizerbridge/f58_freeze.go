package optimizerbridge

// F58 registers concrete existing Dream-RSI baseline policy IDs before any
// prospective research-selection assignment. Neither source control nor a
// green Actions run is an independent first-use witness or science authority.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "reflect"
 "github.com/spoonman136668-ai/forge/dreamrsi"
)

const F58FreezeSchema="forge.optimizer.f58.frozen-prospective-selection.v1"
const F58ParentSource="0771e3f38376cfd003eb978316d7df737f591289"
const F58DreamImplBlob="e9317c400df72b7ea45059e9e8d45d9d4f46baa5"
const F58ParetoImplBlob="c52fbca609f94fa720f78e94d2f5f71bf3eb7b68"
const F58ExternalSelectionAuditorBlob="48810d9935b0cfd119991b22300cbaa783bd9adb"
const F58StageBoundaryBlob="c1551bc4ed69fe6a997d74d96dc6fde1e7db1b8c"

var ErrF58=errors.New("FORGE_F58_FROZEN_CONTROL_OR_EXTERNAL_PROSPECTIVE_FIRSTUSE_MISSING")

type F58Baseline struct {
 Name string `json:"name"`
 SHA256 string `json:"policy_sha256"`
 Policy dreamrsi.Policy `json:"policy"`
}
type F58Challenger struct {
 Name string `json:"name"`
 ImplementationGitBlob string `json:"implementation_git_blob"`
 ExternallyAcceptedPolicySHA256 string `json:"externally_accepted_policy_sha256"`
 IndependentCustodianReceiptSHA256 string `json:"independent_custodian_receipt_sha256"`
}
type F58Lane struct {
 Lane string `json:"lane"`
 FrozenBaselineSeed uint64 `json:"frozen_baseline_seed"`
 Controls []F58Baseline `json:"controls"`
 Challengers []F58Challenger `json:"challengers"`
}
type F58Freeze struct {
 Schema string `json:"schema"`
 ParentSourceCommit string `json:"parent_source_commit"`
 PolicySelectionAuditorGitBlob string `json:"policy_selection_auditor_git_blob"`
 StageActivationBoundaryGitBlob string `json:"stage_activation_boundary_git_blob"`
 ExperimentalUnit string `json:"experimental_unit"`
 RandomizationRule string `json:"randomization_rule"`
 AllocationProbabilityBP int `json:"allocation_probability_bp"`
 ControlArms int `json:"control_arms"`
 ChallengerArms int `json:"challenger_arms"`
 PilotAssignmentsPerLaneMax int `json:"pilot_assignments_per_lane_max"`
 ConfirmatoryMinIndependentSelectionsPerLane int `json:"confirmatory_min_independent_selections_per_lane"`
 ConfirmatoryMinEffectiveSampleSizePerPolicy int `json:"confirmatory_min_effective_sample_size_per_policy"`
 BudgetMatchedCandidatesAndCompute bool `json:"budget_matched_candidates_and_compute"`
 StratifiedByLaneAndPublicSourceFamily bool `json:"stratified_by_lane_and_public_source_family"`
 FrozenBeforeFutureOutcomes bool `json:"frozen_before_future_outcomes"`
 HoldoutProtectedFromPolicyOptimization bool `json:"holdout_protected_from_policy_optimization"`
 MissingOutcomeIsNeverRewarded bool `json:"missing_outcome_is_never_rewarded"`
 IndependentCausalMultipleComparisonsGate bool `json:"independent_causal_multiple_comparisons_gate"`
 ControllerOrFirstUseDispatchAuthorized bool `json:"controller_or_firstuse_dispatch_authorized"`
 DreamParetoProspectiveGainEstablished bool `json:"dream_pareto_prospective_gain_established"`
 ThetaEvolveWeightUpdateAuthorized bool `json:"theta_evolve_weight_update_authorized"`
 Lanes []F58Lane `json:"lanes"`
}

func f58Hex(s string,n int)bool {
 if len(s)!=n{return false}
 for _,b:=range s {if !(b>='0'&&b<='9'||b>='a'&&b<='f'){return false}}
 return true
}
func f58Digest(v interface{}) string {
 raw,_:=json.Marshal(v)
 s:=sha256.Sum256(append([]byte("FORGE-F58-POLICY-CONTROLS-V1\n"),raw...))
 return hex.EncodeToString(s[:])
}

// Actual Go policy IDs are derived directly from the pre-existing production
// dreamrsi.BasePolicies function, never invented or copied from a test fixture.
// The two optimizers are placeholders until *external*, authenticated policy
// custody supplies real final selected and Pareto policy identity.
func FreezeF58() (F58Freeze,error) {
 out:=F58Freeze{
 Schema:F58FreezeSchema,ParentSourceCommit:F58ParentSource,
 PolicySelectionAuditorGitBlob:F58ExternalSelectionAuditorBlob,
 StageActivationBoundaryGitBlob:F58StageBoundaryBlob,
 ExperimentalUnit:"ONE_REAL_PREDECISION_RESEARCH_SELECTION_BY_EXISTING_OWNER",
 RandomizationRule:"EXISTING_OWNER_VERIFIABLY_RANDOMIZED_EQUAL_PROBABILITY_BEFORE_ANY_OUTCOME_NO_SYNTHETIC_ASSIGNMENTS",
 AllocationProbabilityBP:0, // 1/6 is nonintegral in basis points; require actual logged design/probability
 ControlArms:4,ChallengerArms:2,
 PilotAssignmentsPerLaneMax:12,
 ConfirmatoryMinIndependentSelectionsPerLane:72,
 ConfirmatoryMinEffectiveSampleSizePerPolicy:8,
 BudgetMatchedCandidatesAndCompute:true,
 StratifiedByLaneAndPublicSourceFamily:true,
 FrozenBeforeFutureOutcomes:true,
 HoldoutProtectedFromPolicyOptimization:true,
 MissingOutcomeIsNeverRewarded:true,
 IndependentCausalMultipleComparisonsGate:true,
 }
 for _,lane:=range []struct{name string;seed uint64}{{"Wingless",2026101501},{"Yggdrasil",2026101502}} {
  items:=dreamrsi.BasePolicies(lane.name,lane.seed)
  if len(items)!=4{return F58Freeze{},ErrF58}
  controls:=make([]F58Baseline,0,4)
  for i,p:=range items{
   if dreamrsi.VerifyPolicy(p)!=nil{return F58Freeze{},ErrF58}
   names:=[]string{"impact_novelty","balanced","conservative","deterministic_uniform_control"}
   controls=append(controls,F58Baseline{Name:names[i],SHA256:p.ID(),Policy:p})
  }
  out.Lanes=append(out.Lanes,F58Lane{
   Lane:lane.name,FrozenBaselineSeed:lane.seed,Controls:controls,
   Challengers:[]F58Challenger{
    {Name:"dream_rsi_selected",ImplementationGitBlob:F58DreamImplBlob},
    {Name:"shinka_pareto_diverse",ImplementationGitBlob:F58ParetoImplBlob},
   },
  })
 }
 if err:=ValidateF58(out);err!=nil{return F58Freeze{},err}
 return out,nil
}

// Reject changes to controls, source implementation, comparison budget or
// fields that would upgrade a frozen SOURCE registration into scientific trust.
// Passing this check does NOT validate the owner-logged randomization itself.
func ValidateF58(f F58Freeze)error{
 if f.Schema!=F58FreezeSchema||f.ParentSourceCommit!=F58ParentSource||
  f.PolicySelectionAuditorGitBlob!=F58ExternalSelectionAuditorBlob||
  f.StageActivationBoundaryGitBlob!=F58StageBoundaryBlob||
  f.ExperimentalUnit!="ONE_REAL_PREDECISION_RESEARCH_SELECTION_BY_EXISTING_OWNER"||
  f.RandomizationRule!="EXISTING_OWNER_VERIFIABLY_RANDOMIZED_EQUAL_PROBABILITY_BEFORE_ANY_OUTCOME_NO_SYNTHETIC_ASSIGNMENTS"||
  f.AllocationProbabilityBP!=0||f.ControlArms!=4||f.ChallengerArms!=2||
  f.PilotAssignmentsPerLaneMax!=12||
  f.ConfirmatoryMinIndependentSelectionsPerLane!=72||
  f.ConfirmatoryMinEffectiveSampleSizePerPolicy!=8||
  !f.BudgetMatchedCandidatesAndCompute||!f.StratifiedByLaneAndPublicSourceFamily||
  !f.FrozenBeforeFutureOutcomes||!f.HoldoutProtectedFromPolicyOptimization||
  !f.MissingOutcomeIsNeverRewarded||!f.IndependentCausalMultipleComparisonsGate||
  f.ControllerOrFirstUseDispatchAuthorized||f.DreamParetoProspectiveGainEstablished||
  f.ThetaEvolveWeightUpdateAuthorized||len(f.Lanes)!=2{return ErrF58}
 for j,l:=range f.Lanes{
  lane:="Wingless";seed:=uint64(2026101501)
  if j==1{lane="Yggdrasil";seed=2026101502}
  if l.Lane!=lane||l.FrozenBaselineSeed!=seed||
   len(l.Controls)!=4||len(l.Challengers)!=2{return ErrF58}
  canonical:=dreamrsi.BasePolicies(lane,seed)
  used:=map[string]bool{}
  for i,c:=range l.Controls{
   if c.Name!=[]string{"impact_novelty","balanced","conservative","deterministic_uniform_control"}[i]||
    !reflect.DeepEqual(c.Policy,canonical[i])||c.SHA256!=canonical[i].ID()||
    !f58Hex(c.SHA256,64)||used[c.SHA256]{return ErrF58}
   used[c.SHA256]=true
  }
  for i,c:=range l.Challengers{
   name,blob:="dream_rsi_selected",F58DreamImplBlob
   if i==1{name,blob="shinka_pareto_diverse",F58ParetoImplBlob}
   if c.Name!=name||c.ImplementationGitBlob!=blob||
    c.ExternallyAcceptedPolicySHA256!=""||c.IndependentCustodianReceiptSHA256!=""{
    return ErrF58
   }
  }
 }
 return nil
}

type F58Readiness struct {
 Schema string `json:"schema"`
 FrozenControlPolicies int `json:"frozen_control_policies"`
 ReservedProspectiveChallengers int `json:"reserved_prospective_challengers"`
 FrozenControlRegistrySHA256 string `json:"frozen_control_registry_sha256"`
 OwnerPublishedChallengerPolicies bool `json:"owner_published_challenger_policies"`
 IndependentFirstUseAndRandomizationQualified bool `json:"independent_first_use_and_randomization_qualified"`
 FutureProspectiveCausalOutcomesQualified bool `json:"future_prospective_causal_outcomes_qualified"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaWeightPromotionAuthorized bool `json:"theta_weight_promotion_authorized"`
 SelectionTrialExecutionAuthorized bool `json:"selection_trial_execution_authorized"`
 Status string `json:"status"`
}
func ReadinessF58(f F58Freeze)(F58Readiness,error){
 if err:=ValidateF58(f);err!=nil{return F58Readiness{},err}
 controls:=[]F58Baseline{}
 for _,l:=range f.Lanes{controls=append(controls,l.Controls...)}
 return F58Readiness{
  Schema:"forge.optimizer.f58.selection-firstuse-readiness.v1",
  FrozenControlPolicies:8,ReservedProspectiveChallengers:4,
  FrozenControlRegistrySHA256:f58Digest(controls),
  Status:"CONTROL_IDS_FROZEN_BUT_AUTHENTIC_CHALLENGER_AND_RANDOMIZED_FIRSTUSE_NOT_YET_RECEIVED",
 },nil
}
