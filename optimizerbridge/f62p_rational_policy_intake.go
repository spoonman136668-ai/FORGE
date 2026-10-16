package optimizerbridge

// F62P is a SOURCE-ONLY prospective policy-arm weighting preview.
// It never receives trusted first-use evidence and cannot independently
// establish genuine owner nominations, timing, randomization custody,
// complete original outcomes, or comparative scientific policy gains.
// Unlike dreamrsi.Evaluate, this computes policy-ARM assignment weights,
// NOT conditional research-ACTION propensities.
import (
 "errors"
 "math/big"
)

const F62PPreviewSchema="forge.optimizer.f62p.exact-policy-arm-intake-preview.v1"
var ErrF62P=errors.New("FORGE_F62P_AUTHENTIC_OWNER_WITNESS_AND_EXACT_POLICY_EVIDENCE_REQUIRED")

type F62PTrial struct {
 Assignment F61PilotAssignment `json:"assignment"`
 OwnerDecisionSequence uint64 `json:"owner_decision_sequence"`
 OriginalReceiptSHA256 string `json:"original_receipt_sha256"`
 Outcome string `json:"outcome"`
 ComputeUnits int64 `json:"compute_units"`
}
type F62PArmPreview struct {
 Name string `json:"name"`
 PolicySHA256 string `json:"policy_sha256"`
 Assigned int `json:"assigned"`
 Observed int `json:"observed"`
 Missing int `json:"missing"`
 // These are exact source-only inverse assignment probability statistics,
 // never a signed causal estimate or permission for policy promotion.
 ScoreIPSPreview string `json:"score_ips_preview,omitempty"`
 ComputeIPSPreview string `json:"compute_ips_preview,omitempty"`
 ScorePerComputePreview string `json:"score_per_compute_preview,omitempty"`
}
type F62PPreview struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceOnlyTrialCount int `json:"source_only_trial_count"`
 ExactArmProbabilityNumerator int `json:"exact_arm_probability_numerator"`
 ExactArmProbabilityDenominator int `json:"exact_arm_probability_denominator"`
 MissingOutcomes int `json:"missing_outcomes"`
 Arms []F62PArmPreview `json:"arms"`
 ResearchActionPropensityInterchangeable bool `json:"research_action_propensity_interchangeable"`
 IndependentOwnerWitnessAuthenticated bool `json:"independent_owner_witness_authenticated"`
 GenuineFirstUseEstablished bool `json:"genuine_firstuse_established"`
 CausalComparisonAuthorized bool `json:"causal_comparison_authorized"`
 OptimizerActivationAuthorized bool `json:"optimizer_activation_authorized"`
 Status string `json:"status"`
}
func f62Score(outcome string)(int64,bool){
 switch outcome {
 case "SUPPORTED":return 3,true
 case "MIXED":return 1,true
 case "NEGATIVE","INVALID","CONSUMED_INDETERMINATE":return 0,true
 default:return 0,false
 }
}

// PreviewF62PExactPolicyArms checks the integrity of F61P *unwitnessed*
// assignments and computes rational 1/6 policy-arm IPS diagnostics only.
// It cannot consume or verify external first-use; the existing scientific
// owner must independently authenticate every source, receipt and outcome.
// A missing outcome suppresses all estimators, never silently yields zero.
// Its historical dreamrsi basis-point estimator is deliberately untouched.
func PreviewF62PExactPolicyArms(f F58Freeze,n F59PolicyNomination,trials []F62PTrial)(F62PPreview,error){
 var zero F62PPreview
 if err:=ValidateF58(f);err!=nil||len(trials)==0||len(trials)>f.PilotAssignmentsPerLaneMax{
  return zero,ErrF62P
 }
 reference,err:=f61Arms(f,n)
 if err!=nil||len(reference)!=6{return zero,ErrF62P}
 out:=F62PPreview{
  Schema:F62PPreviewSchema,Lane:n.Lane,SourceOnlyTrialCount:len(trials),
  ExactArmProbabilityNumerator:1,ExactArmProbabilityDenominator:6,
  Arms:make([]F62PArmPreview,6),
  Status:"SOURCE_ONLY_UNWITNESSED_NO_CUSTODY_NO_CAUSAL_COMPARISON_NO_FIRSTUSE",
 }
 sums:=make([]int64,6)
 costs:=make([]int64,6)
 for i,a:=range reference {
  out.Arms[i]=F62PArmPreview{Name:a.Name,PolicySHA256:a.PolicySHA256}
 }
 seenAssignments:=map[string]bool{}
 seenReceipts:=map[string]bool{}
 var last uint64
 var family,budget string
 for i,t:=range trials{
  a:=t.Assignment
  if err:=ValidateF61Prepared(f,n,a);err!=nil||
   t.OwnerDecisionSequence==0||t.OwnerDecisionSequence<=last||
   !f59Hex(t.OriginalReceiptSHA256,64)||
   seenReceipts[t.OriginalReceiptSHA256]||
   seenAssignments[a.AssignmentSHA256]{
   return zero,ErrF62P
  }
  last=t.OwnerDecisionSequence
  seenAssignments[a.AssignmentSHA256]=true
  seenReceipts[t.OriginalReceiptSHA256]=true
  if i==0{family=a.PublicSourceFamilySHA256;budget=a.BudgetCommitmentSHA256}
  if a.PublicSourceFamilySHA256!=family||a.BudgetCommitmentSHA256!=budget {
   // Comparisons across different source families or budget designs require
   // independent stratum-specific qualification; do not pool.
   return zero,ErrF62P
  }
  arm:=a.ChoiceIndex
  out.Arms[arm].Assigned++
  if t.Outcome=="MISSING"{
   if t.ComputeUnits!=0{return zero,ErrF62P}
   out.Arms[arm].Missing++
   out.MissingOutcomes++
   continue
  }
  score,ok:=f62Score(t.Outcome)
  if !ok||t.ComputeUnits<=0||t.ComputeUnits>1_000_000_000{return zero,ErrF62P}
  out.Arms[arm].Observed++
  sums[arm]+=score
  costs[arm]+=t.ComputeUnits
 }
 // Exact inverse policy-arm assignment probability is 6; the published
 // historical action-level basis-point replay has different estimands.
 // Neither is a trusted experiment without independent custody.
 if out.MissingOutcomes==0{
  denominator:=int64(len(trials))
  for i:=range out.Arms{
   score:=new(big.Rat).SetFrac(big.NewInt(sums[i]*6),big.NewInt(denominator))
   compute:=new(big.Rat).SetFrac(big.NewInt(costs[i]*6),big.NewInt(denominator))
   out.Arms[i].ScoreIPSPreview=score.RatString()
   out.Arms[i].ComputeIPSPreview=compute.RatString()
   if costs[i]>0{
    out.Arms[i].ScorePerComputePreview=new(big.Rat).SetFrac(
     big.NewInt(sums[i]),big.NewInt(costs[i])).RatString()
   }
  }
 }
 return out,nil
}
