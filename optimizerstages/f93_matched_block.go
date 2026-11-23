package optimizerstages

// F93 is a source-only design for a NEW future six-arm matched-block
// prospective comparison. It CANNOT retrospectively relabel F89/F90/F91
// individually randomized trials as matched blocks: every new block needs
// six separate genuine originals on a preregistered comparable task, with
// a uniform independent six-way position permutation and no interference.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
 "math/big"
)

const F93Schema="forge.optimizer.f93.preregistered-six-arm-matched-block-design.v1"
const F93ReviewSchema="forge.optimizer.f93.matched-block-source-only-diagnostics.v1"
const F93Domain="FORGE-F93-MATCHED-BLOCK-DESIGN-V1\n"
const F93MaxBlocksPerLane=F92CurrentF90CapPerLane/6
const F93Status="NEW_ALTERNATIVE_DESIGN_ONLY_NO_INDEPENDENT_SCIENCE_EVIDENCE"
var ErrF93=errors.New("FORGE_F93_MATCHED_BLOCK_ORIGINALS_AND_INDEPENDENT_CUSTODY_REQUIRED")

type F93MatchedPlan struct {
 Schema string `json:"schema"`
 WinglessFrozenDesignSHA256 string `json:"wingless_frozen_design_sha256"`
 YggdrasilFrozenDesignSHA256 string `json:"yggdrasil_frozen_design_sha256"`
 MatchedTaskDefinitionSHA256 string `json:"matched_task_definition_sha256"`
 OutcomeScoringProtocolSHA256 string `json:"outcome_scoring_protocol_sha256"`
 PositionRandomizationProtocolSHA256 string `json:"position_randomization_protocol_sha256"`
 NoInterferenceProtocolSHA256 string `json:"no_interference_protocol_sha256"`
 TargetOneSidedLowerOffsetPoints int `json:"target_one_sided_lower_offset_points"`
 PlannedMaximumBlocksPerLane int `json:"planned_maximum_blocks_per_lane"`
 SixArmOriginalsPerBlock int `json:"six_arm_originals_per_block"`
 PlannedOriginalsPerLane int `json:"planned_originals_per_lane"`
 StrictMinimumIndependentBlocks int `json:"strict_minimum_independent_blocks"`
 ConditionalOneSidedOffsetAtPlanMaximum float64 `json:"conditional_one_sided_offset_at_plan_maximum"`
 MathematicallyResolvesTargetWithinPlan bool `json:"mathematically_resolves_target_within_plan"`
 GenuineIndependentMatchedTasksVerified bool `json:"genuine_independent_matched_tasks_verified"`
 UniformOrderRandomizationVerified bool `json:"uniform_order_randomization_verified"`
 NoInterferenceIndependentlyVerified bool `json:"no_interference_independently_verified"`
 TruePreOutcomeWitnessAndFirstUseVerified bool `json:"true_pre_outcome_witness_and_firstuse_verified"`
 AuthenticAcceptedProspectiveImprovement bool `json:"authentic_accepted_prospective_improvement"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveTrainingEnabled bool `json:"theta_evolve_training_enabled"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 CloudflareMutationAuthorized bool `json:"cloudflare_mutation_authorized"`
 Status string `json:"status"`
 PlanSHA256 string `json:"plan_sha256"`
}

// One block contains one row per frozen policy, not six independent F89
// selections that were retrospectively grouped. Position and case identity
// are source claims. The genuine external witness may later attest them;
// this library never can.
type F93Cell struct {
 ArmIndex int `json:"arm_index"`
 ArmName string `json:"arm_name"`
 PolicySHA256 string `json:"policy_sha256"`
 RandomizedPosition int `json:"randomized_position"`
 PredecisionReceiptSHA256 string `json:"predecision_receipt_sha256"`
 OutcomeArtifactSHA256 string `json:"outcome_artifact_sha256"`
 Classification string `json:"classification"`
 Score int64 `json:"score"`
 ComputeUnits int64 `json:"compute_units"`
}
type F93MatchedBlock struct {
 Lane string `json:"lane"`
 BlockCaseSHA256 string `json:"block_case_sha256"`
 BlockProtocolSHA256 string `json:"block_protocol_sha256"`
 ClaimedPositionDrawSHA256 string `json:"claimed_position_draw_sha256"`
 Cells [6]F93Cell `json:"cells"`
}
type F93MatchedContrast struct {
 CandidateName string `json:"candidate_name"`
 ControlName string `json:"control_name"`
 ExactMeanMatchedScoreDifference string `json:"exact_mean_matched_score_difference"`
 ExactMeanMatchedComputeDifference string `json:"exact_mean_matched_compute_difference"`
 ConditionalOneSidedLowerScore float64 `json:"conditional_one_sided_lower_score"`
 PositiveDiagnosticPointDifference bool `json:"positive_diagnostic_point_difference"`
 ConditionalLowerAboveZero bool `json:"conditional_lower_above_zero"`
}
type F93LaneAudit struct {
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 BlocksReviewed int `json:"blocks_reviewed"`
 SixCellsPerCompleteBlock bool `json:"six_cells_per_complete_block"`
 MissingOutcomeCells int `json:"missing_outcome_cells"`
 ConditionalComparisons []F93MatchedContrast `json:"conditional_comparisons"`
}
type F93SourceReview struct {
 Schema string `json:"schema"`
 DesignSHA256 string `json:"design_sha256"`
 Lanes []F93LaneAudit `json:"lanes"`
 MatchedBlockSourceClaimsWellFormed bool `json:"matched_block_source_claims_well_formed"`
 OneSidedFamilywiseAlpha float64 `json:"one_sided_familywise_alpha"`
 PrespecifiedComparisons int `json:"prespecified_comparisons"`
 IndependentBlocksExternallyAuthenticated bool `json:"independent_blocks_externally_authenticated"`
 PreOutcomeAssignmentsExternallyWitnessed bool `json:"pre_outcome_assignments_externally_witnessed"`
 AuthenticOriginalFirstUseVerified bool `json:"authentic_original_first_use_verified"`
 CompleteUnselectedPopulationVerified bool `json:"complete_unselected_population_verified"`
 AcceptedScientificCausalGain bool `json:"accepted_scientific_causal_gain"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveAcceptedTrainingEnabled bool `json:"theta_evolve_accepted_training_enabled"`
 ScienceDispatchAuthorized bool `json:"science_dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 Status string `json:"status"`
}

func f93Hash(domain string,object any)string {
 raw,_:=json.Marshal(object)
 d:=sha256.Sum256(append([]byte(domain+"\n"),raw...))
 return hex.EncodeToString(d[:])
}
func f93PlanHash(p F93MatchedPlan)string {
 p.PlanSHA256=""
 raw,_:=json.Marshal(p)
 h:=sha256.Sum256(append([]byte(F93Domain),raw...))
 return hex.EncodeToString(h[:])
}
// Under complete, independent, noninterfering matched blocks, a difference
// in bounded scores 0..100 is in [-100,100]. Bonferroni over 16 frozen
// one-sided policy contrasts gives range-200 Hoeffding offset.
func f93ConditionalRadius(blocks int)float64 {
 return 200*math.Sqrt(math.Log(16/0.05)/(2*float64(blocks)))
}
func f93StrictMinimumBlocks(target int)(int,error) {
 if target<1||target>100{return 0,ErrF93}
 n:=int(math.Floor(20000*math.Log(16/0.05)/float64(target*target)))+1
 for n>1&&f93ConditionalRadius(n-1)<float64(target){n--}
 for f93ConditionalRadius(n)>=float64(target){n++}
 return n,nil
}
func PlanF93MatchedBlocks(w,y FrozenSixPolicyTrial,taskDef,scoreProtocol,
 positionProtocol,noInterference string,target,plannedBlocks int)(F93MatchedPlan,error){
 var zero F93MatchedPlan
 if !f92ValidPairedFreezes(w,y)||plannedBlocks<1||plannedBlocks>F93MaxBlocksPerLane {
  return zero,ErrF93
 }
 seen:=map[string]bool{}
 for _,h:=range []string{taskDef,scoreProtocol,positionProtocol,noInterference}{
  if !exactHex(h,64)||seen[h]{return zero,ErrF93}
  seen[h]=true
 }
 n,err:=f93StrictMinimumBlocks(target)
 if err!=nil{return zero,ErrF93}
 p:=F93MatchedPlan{
  Schema:F93Schema,WinglessFrozenDesignSHA256:F89FreezeDigest(w),
  YggdrasilFrozenDesignSHA256:F89FreezeDigest(y),
  MatchedTaskDefinitionSHA256:taskDef,
  OutcomeScoringProtocolSHA256:scoreProtocol,
  PositionRandomizationProtocolSHA256:positionProtocol,
  NoInterferenceProtocolSHA256:noInterference,
  TargetOneSidedLowerOffsetPoints:target,
  PlannedMaximumBlocksPerLane:plannedBlocks,SixArmOriginalsPerBlock:6,
  PlannedOriginalsPerLane:6*plannedBlocks,
  StrictMinimumIndependentBlocks:n,
  ConditionalOneSidedOffsetAtPlanMaximum:f93ConditionalRadius(plannedBlocks),
  MathematicallyResolvesTargetWithinPlan:n<=plannedBlocks,
  Status:F93Status,
 }
 p.PlanSHA256=f93PlanHash(p)
 return p,nil
}
func ValidateF93MatchedPlan(w,y FrozenSixPolicyTrial,p F93MatchedPlan)error{
 expected,err:=PlanF93MatchedBlocks(w,y,p.MatchedTaskDefinitionSHA256,
  p.OutcomeScoringProtocolSHA256,p.PositionRandomizationProtocolSHA256,
  p.NoInterferenceProtocolSHA256,p.TargetOneSidedLowerOffsetPoints,
  p.PlannedMaximumBlocksPerLane)
 if err!=nil||expected!=p||!exactHex(p.PlanSHA256,64){return ErrF93}
 return nil
}
// ValidateF93PinnedPlan compares the new protocol to an independently
// obtained pre-outcome design digest. Caller-supplied pins are NOT independent
// evidence: this only rejects change relative to the pin actually supplied.
func ValidateF93PinnedPlan(w,y FrozenSixPolicyTrial,p F93MatchedPlan,precommittedSHA256 string)error{
 if !exactHex(precommittedSHA256,64)||ValidateF93MatchedPlan(w,y,p)!=nil||
  p.PlanSHA256!=precommittedSHA256{return ErrF93}
 return nil
}
// Source review NEVER implies the requested matched tasks existed or the
// order was independently randomized. Every record and SHA here is supplied.
func auditF93Lane(f FrozenSixPolicyTrial,blocks []F93MatchedBlock,
 p F93MatchedPlan,used map[string]bool)(F93LaneAudit,error){
 var zero F93LaneAudit
 if len(blocks)==0||len(blocks)>p.PlannedMaximumBlocksPerLane{return zero,ErrF93}
 names,policies:=f89Arms(f)
 out:=F93LaneAudit{Lane:f.Lane,FrozenDesignSHA256:F89FreezeDigest(f),
  BlocksReviewed:len(blocks),SixCellsPerCompleteBlock:true}
 var scores [6]int64
 var costs [6]int64
 for _,b:=range blocks{
  if b.Lane!=f.Lane||!exactHex(b.BlockCaseSHA256,64)||
   !exactHex(b.ClaimedPositionDrawSHA256,64)||
   b.BlockProtocolSHA256!=p.PlanSHA256{
   return zero,ErrF93
  }
  for _,key:=range []string{"case:"+b.BlockCaseSHA256,"draw:"+b.ClaimedPositionDrawSHA256}{
   if used[key]{return zero,ErrF93}
   used[key]=true
  }
  var arms,positions [6]bool
  for _,c:=range b.Cells{
   if c.ArmIndex<0||c.ArmIndex>5||c.RandomizedPosition<0||
    c.RandomizedPosition>5||arms[c.ArmIndex]||positions[c.RandomizedPosition]||
    c.ArmName!=names[c.ArmIndex]||c.PolicySHA256!=policies[c.ArmIndex]||
    !exactHex(c.PredecisionReceiptSHA256,64)||
    !f90ClassAllowed(c.Classification){return zero,ErrF93}
   arms[c.ArmIndex]=true;positions[c.RandomizedPosition]=true
   rkey:="receipt:"+c.PredecisionReceiptSHA256
   if used[rkey]{return zero,ErrF93};used[rkey]=true
   if c.Classification=="MISSING"{
    if c.OutcomeArtifactSHA256!=""||c.Score!=0||c.ComputeUnits!=0{
     return zero,ErrF93
    }
    out.MissingOutcomeCells++
    continue
   }
   if !exactHex(c.OutcomeArtifactSHA256,64)||
    c.Score<0||c.Score>100||c.ComputeUnits<1||c.ComputeUnits>1000000||
    ((c.Classification=="INVALID"||c.Classification=="CONSUMED_INDETERMINATE")&&c.Score!=0){
    return zero,ErrF93
   }
   key:="outcome:"+c.OutcomeArtifactSHA256
   if used[key]{return zero,ErrF93};used[key]=true
   scores[c.ArmIndex]+=c.Score
   costs[c.ArmIndex]+=c.ComputeUnits
  }
  for i:=0;i<6;i++{if !arms[i]||!positions[i]{return zero,ErrF93}}
 }
 if out.MissingOutcomeCells!=0{return out,nil}
 offset:=f93ConditionalRadius(len(blocks))
 for candidate:=4;candidate<6;candidate++{
  for control:=0;control<4;control++{
   difference:=new(big.Rat).SetFrac(
    big.NewInt(scores[candidate]-scores[control]),big.NewInt(int64(len(blocks))))
   compute:=new(big.Rat).SetFrac(
    big.NewInt(costs[candidate]-costs[control]),big.NewInt(int64(len(blocks))))
   point,_:=difference.Float64()
   out.ConditionalComparisons=append(out.ConditionalComparisons,F93MatchedContrast{
    CandidateName:names[candidate],ControlName:names[control],
    ExactMeanMatchedScoreDifference:difference.RatString(),
    ExactMeanMatchedComputeDifference:compute.RatString(),
    ConditionalOneSidedLowerScore:point-offset,
    PositiveDiagnosticPointDifference:difference.Sign()>0,
    ConditionalLowerAboveZero:point-offset>0,
   })
  }
 }
 return out,nil
}
func AuditF93MatchedSource(w,y FrozenSixPolicyTrial,p F93MatchedPlan,
 wingless,yggdrasil []F93MatchedBlock)(F93SourceReview,error){
 var zero F93SourceReview
 if ValidateF93MatchedPlan(w,y,p)!=nil{return zero,ErrF93}
 used:=map[string]bool{}
 wa,err:=auditF93Lane(w,wingless,p,used)
 if err!=nil{return zero,ErrF93}
 ya,err:=auditF93Lane(y,yggdrasil,p,used)
 if err!=nil{return zero,ErrF93}
 return F93SourceReview{
  Schema:F93ReviewSchema,DesignSHA256:p.PlanSHA256,
  Lanes:[]F93LaneAudit{wa,ya},
  MatchedBlockSourceClaimsWellFormed:true,
  OneSidedFamilywiseAlpha:0.05,PrespecifiedComparisons:16,
  Status:"SYNTACTIC_MATCHED_BLOCKS_ONLY_NOT_INDEPENDENT_PROSPECTIVE_SCIENCE",
 },nil
}
