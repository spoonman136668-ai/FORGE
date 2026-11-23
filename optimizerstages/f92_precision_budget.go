package optimizerstages

// F92 is a prospective policy-comparison PRECISION DESIGN audit, not a
// research controller, scientific owner, power guarantee, or experimental
// authorization. It exposes the interaction of F91's conservative bound and
// F90's bounded source-cohort reader BEFORE anyone commits a research budget.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
)

const F92Schema="forge.optimizer.f92.frozen-six-arm-precision-feasibility.v1"
const F92Domain="FORGE-F92-CONDITIONAL-PRECISION-PLAN-V1\n"
const F92Status="FROZEN_DESIGN_PRECISION_ONLY_NO_AUTHENTIC_PROSPECTIVE_EVIDENCE"
const F92CurrentF90CapPerLane=16384

var ErrF92=errors.New("FORGE_F92_PROSPECTIVE_POLICY_COMPARISON_PRECISION_OR_FROZEN_DESIGN_NOT_QUALIFIED")

type F92PrecisionPlan struct{
 Schema string `json:"schema"`
 WinglessFrozenDesignSHA256 string `json:"wingless_frozen_design_sha256"`
 YggdrasilFrozenDesignSHA256 string `json:"yggdrasil_frozen_design_sha256"`
 FamilywiseAlpha float64 `json:"familywise_alpha"`
 FrozenComparisonCount int `json:"frozen_comparison_count"`
 ScoreScaleMinimum int `json:"score_scale_minimum"`
 ScoreScaleMaximum int `json:"score_scale_maximum"`
 DesiredHalfWidthScorePoints int `json:"desired_half_width_score_points"`
 PlannedMaximumObservationsPerLane int `json:"planned_maximum_observations_per_lane"`
 ReaderMaximumObservationsPerLane int `json:"reader_maximum_observations_per_lane"`
 MinimumObservationsForStrictHalfWidth int `json:"minimum_observations_for_strict_half_width"`
 ConditionalHalfWidthAtPlannedMaximum float64 `json:"conditional_half_width_at_planned_maximum"`
 ConditionalHalfWidthAtReaderMaximum float64 `json:"conditional_half_width_at_reader_maximum"`
 MathematicalPrecisionFeasibleWithinPlan bool `json:"mathematical_precision_feasible_within_plan"`
 RequiresLargerQualifiedReaderOrPreregisteredEstimator bool `json:"requires_larger_qualified_reader_or_preregistered_estimator"`
 CompleteIndependentOriginalsObserved bool `json:"complete_independent_originals_observed"`
 IndependentlyVerifiedPreOutcomeWitness bool `json:"independently_verified_pre_outcome_witness"`
 AuthenticatedRandomizationAndOwnerFirstUse bool `json:"authenticated_randomization_and_owner_firstuse"`
 ScientificImprovementClaimed bool `json:"scientific_improvement_claimed"`
 DreamRSIOrParetoActivationAuthorized bool `json:"dream_rsi_or_pareto_activation_authorized"`
 ThetaEvolveAcceptedTrainingAllowed bool `json:"theta_evolve_accepted_training_allowed"`
 ScientificDispatchAuthorized bool `json:"scientific_dispatch_authorized"`
 CloudflareWriteAuthorized bool `json:"cloudflare_write_authorized"`
 Status string `json:"status"`
 PlanSHA256 string `json:"plan_sha256"`
}

func f92PlanHash(p F92PrecisionPlan)string{
 p.PlanSHA256=""
 raw,_:=json.Marshal(p)
 sum:=sha256.Sum256(append([]byte(F92Domain),raw...))
 return hex.EncodeToString(sum[:])
}

// f92MinimumN returns a STRICT half-width target under the particular F91
// simultaneous conservative bound. It is not frequentist statistical power,
// an effect-size guarantee, a sample requirement for other estimators or
// evidence that independent research observations exist.
func f92MinimumN(targetScorePoints int)(int,error){
 if targetScorePoints<1||targetScorePoints>100{return 0,ErrF92}
 // Hoeffding radius(n)=1200 sqrt(log(16/.05)/(2n)).
 // Strictly require radius(n)<targetScorePoints.
 theory:=720000*math.Log(16/0.05)/float64(targetScorePoints*targetScorePoints)
 if math.IsNaN(theory)||math.IsInf(theory,0)||theory<0||theory>1000000000{
  return 0,ErrF92
 }
 n:=int(math.Floor(theory))+1
 // Numerically protect the strict bound at a rounded floating boundary.
 for n>1 && f91ConditionalRadius(n-1)<float64(targetScorePoints){n--}
 for f91ConditionalRadius(n)>=float64(targetScorePoints){n++}
 return n,nil
}

func f92ValidPairedFreezes(w,y FrozenSixPolicyTrial)bool{
 return ValidateF89Freeze(w)==nil&&ValidateF89Freeze(y)==nil&&
  w.Lane=="Wingless"&&y.Lane=="Yggdrasil"&&
  w.OwnerSourceSHA!=y.OwnerSourceSHA&&
  w.PreregistrationSHA256!=y.PreregistrationSHA256&&
  w.CandidateSlateSHA256!=y.CandidateSlateSHA256&&
  w.SourceFamilySHA256!=y.SourceFamilySHA256&&
  F89FreezeDigest(w)!=F89FreezeDigest(y)
}

// PlanF92Precision binds both frozen policy-comparison designs and the chosen
// prospective precision target before outcomes are considered. Its precise
// output is a math-only non-authorizing preflight; it never executes work.
func PlanF92Precision(w,y FrozenSixPolicyTrial,targetScorePoints,plannedMaximumPerLane int)(F92PrecisionPlan,error){
 var zero F92PrecisionPlan
 if !f92ValidPairedFreezes(w,y)||
  plannedMaximumPerLane<6||plannedMaximumPerLane>F92CurrentF90CapPerLane{
  return zero,ErrF92
 }
 minimum,err:=f92MinimumN(targetScorePoints)
 if err!=nil{return zero,ErrF92}
 p:=F92PrecisionPlan{
  Schema:F92Schema,
  WinglessFrozenDesignSHA256:F89FreezeDigest(w),
  YggdrasilFrozenDesignSHA256:F89FreezeDigest(y),
  FamilywiseAlpha:0.05,FrozenComparisonCount:16,
  ScoreScaleMinimum:0,ScoreScaleMaximum:100,
  DesiredHalfWidthScorePoints:targetScorePoints,
  PlannedMaximumObservationsPerLane:plannedMaximumPerLane,
  ReaderMaximumObservationsPerLane:F92CurrentF90CapPerLane,
  MinimumObservationsForStrictHalfWidth:minimum,
  ConditionalHalfWidthAtPlannedMaximum:f91ConditionalRadius(plannedMaximumPerLane),
  ConditionalHalfWidthAtReaderMaximum:f91ConditionalRadius(F92CurrentF90CapPerLane),
  MathematicalPrecisionFeasibleWithinPlan:minimum<=plannedMaximumPerLane,
  RequiresLargerQualifiedReaderOrPreregisteredEstimator:minimum>F92CurrentF90CapPerLane,
  Status:F92Status,
 }
 p.PlanSHA256=f92PlanHash(p)
 return p,nil
}

// ValidateF92FrozenPlan is a content-identity check, not external custody.
// It rejects caller-forged authority bits and changed preregistration values.
func ValidateF92FrozenPlan(w,y FrozenSixPolicyTrial,p F92PrecisionPlan)error{
 expected,err:=PlanF92Precision(w,y,p.DesiredHalfWidthScorePoints,p.PlannedMaximumObservationsPerLane)
 if err!=nil||p!=expected||!exactHex(p.PlanSHA256,64){return ErrF92}
 return nil
}
