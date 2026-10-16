package optimizerstages

// F91 links F89 frozen six-arm POLICY assignments to F90 independently
// PINNABLE signed outcome cohorts. Only a separate, genuinely independent
// source provider can authenticate a real prospective original; this
// package calculates conditional diagnostics and can never promote science.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
 "math/big"
)

const F91ReviewSchema="forge.optimizer.f91.frozen-six-arm-conditional-evidence-review.v1"
const F91StatusUnverified="SOURCE_ONLY_NO_INDEPENDENT_PROSPECTIVE_AUTHENTICATION"
const F91StatusProvider="EXTERNAL_PROVIDER_CLAIM_CHECKED_NO_INDEPENDENT_SCIENCE_ACCEPTANCE"
const F91StatusIncomplete="BLOCKED_MISSING_OR_UNOBSERVED_POLICY_ARM_OUTCOMES"
var ErrF91=errors.New("FORGE_F91_AUTHENTIC_PROSPECTIVE_SCIENTIFIC_EVIDENCE_REQUIRED")

// No field is a signing credential. Pins must originate from a *separate*
// qualified owner/archival source, never from the candidate's own output.
type F91ExternalPin struct{
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 CohortSHA256 string `json:"cohort_sha256"`
 OwnerLedgerSHA256 string `json:"owner_ledger_sha256"`
 WitnessArchiveSHA256 string `json:"witness_archive_sha256"`
 PreregistrationArchiveSHA256 string `json:"preregistration_archive_sha256"`
}
// Even a mock accepting the interface does not independently prove genuine
// ownership, owner-firstuse, or its own impartiality. The calling environment
// must qualify that provider outside FORGE's optimizer source branch.
type F91ExternalVerifier interface{
 VerifyIndependentProspectiveCohort(
  FrozenSixPolicyTrial,[]F90Observation,F91ExternalPin)error
}

type F91PolicyContrast struct{
 CandidateName string `json:"candidate_name"`
 ControlName string `json:"control_name"`
 CandidatePolicySHA256 string `json:"candidate_policy_sha256"`
 ControlPolicySHA256 string `json:"control_policy_sha256"`
 ExactIPSScoreDifference string `json:"exact_ips_score_difference"`
 ExactIPSComputeDifference string `json:"exact_ips_compute_difference"`
 ConditionalLowerScoreDifference float64 `json:"conditional_lower_score_difference"`
 ConditionalUpperScoreDifference float64 `json:"conditional_upper_score_difference"`
 PositivePointEstimate bool `json:"positive_point_estimate"`
 ConditionalFamilywiseLowerAboveZero bool `json:"conditional_familywise_lower_above_zero"`
}
type F91LaneReview struct{
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 CohortSHA256 string `json:"cohort_sha256"`
 Observations int `json:"observations"`
 MissingOutcomes int `json:"missing_outcomes"`
 EveryPolicyArmObserved bool `json:"every_policy_arm_observed"`
 ReportedSourceVerifierAccepted bool `json:"reported_source_verifier_accepted"`
 Comparisons []F91PolicyContrast `json:"comparisons"`
}
type F91Review struct{
 Schema string `json:"schema"`
 Lanes []F91LaneReview `json:"lanes"`
 SourceCryptographyConsistent bool `json:"source_cryptography_consistent"`
 ReportedExternalSourceVerifierAccepted bool `json:"reported_external_source_verifier_accepted"`
 ConditionalFamilywiseAlpha float64 `json:"conditional_familywise_alpha"`
 ConditionalComparisonCount int `json:"conditional_comparison_count"`
 ConditionalPolicyDifferenceBoundScore100 string `json:"conditional_policy_difference_bound_score_0_to_100"`
 IndependentProspectiveSourceQualified bool `json:"independent_prospective_source_qualified"`
 IndependentlyWitnessedPreOutcomeFirstUse bool `json:"independently_witnessed_pre_outcome_first_use"`
 RealRandomizationAndCompletePopulationProven bool `json:"real_randomization_and_complete_population_proven"`
 ScientificCausalImprovementEstablished bool `json:"scientific_causal_improvement_established"`
 DreamRSIPromotionAuthorized bool `json:"dream_rsi_promotion_authorized"`
 ParetoPromotionAuthorized bool `json:"pareto_promotion_authorized"`
 ThetaEvolveAcceptedOutcomeTrainingAllowed bool `json:"theta_evolve_accepted_outcome_training_allowed"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedReferenceMutation bool `json:"accepted_reference_mutation"`
 Status string `json:"status"`
}

func f91CohortSHA(rows []F90Observation)string{
 raw,_:=json.Marshal(rows)
 h:=sha256.Sum256(append([]byte("FORGE-F91-SOURCE-COHORT-V1\n"),raw...))
 return hex.EncodeToString(h[:])
}
func f91ValidPin(f FrozenSixPolicyTrial,p F91ExternalPin,rows []F90Observation)bool{
 if p.Lane!=f.Lane||p.FrozenDesignSHA256!=F89FreezeDigest(f)||
  !exactHex(p.CohortSHA256,64)||p.CohortSHA256!=f91CohortSHA(rows)||
  !exactHex(p.OwnerLedgerSHA256,64)||
  !exactHex(p.WitnessArchiveSHA256,64)||
  !exactHex(p.PreregistrationArchiveSHA256,64){return false}
 seen:=map[string]bool{}
 for _,s:=range []string{p.CohortSHA256,p.OwnerLedgerSHA256,
  p.WitnessArchiveSHA256,p.PreregistrationArchiveSHA256}{
  if seen[s]{return false};seen[s]=true
 }
 return true
}
// Conditional bounded-difference range for IPW candidate-vs-control score:
// Z_i=6*Y_i*(I[arm=candidate]-I[arm=control]), Y in [0,100],
// Z in [-600,600]. Hoeffding + Bonferroni over 16 planned comparisons
// (2 lanes * 2 candidates * 4 controls): ONE-SIDED simultaneous
// lower confidence offset (600-(-600))*sqrt(log(16/alpha)/(2*n)).
// The upper value displayed below is descriptive and MUST NOT be represented
// as part of a simultaneous two-sided familywise 95% interval: that would
// require an extra factor of 2 inside the logarithm (log(32/alpha)).
// This is NOT a valid confidence bound for the real population until the
// source verifies independent unbiased assignment, complete intended sample,
// timing, comparable budgets and preregistered experimental design.
func f91ConditionalRadius(n int)float64{
 return 1200*math.Sqrt(math.Log(16/0.05)/(2*float64(n)))
}
func f91ReviewLane(f FrozenSixPolicyTrial,rows []F90Observation,
 source F90LaneAudit)(F91LaneReview,error){
 var zero F91LaneReview
 if len(rows)==0||source.Lane!=f.Lane||source.FrozenDesignSHA256!=F89FreezeDigest(f){
  return zero,ErrF91
 }
 l:=F91LaneReview{
  Lane:f.Lane,FrozenDesignSHA256:F89FreezeDigest(f),CohortSHA256:f91CohortSHA(rows),
  Observations:len(rows),MissingOutcomes:source.MissingOutcomes,
 }
 if source.MissingOutcomes!=0{return l,nil}
 names,policies:=f89Arms(f)
 var score [6]int64
 var compute [6]int64
 var counts [6]int
 for _,o:=range rows{
  if o.Classification=="MISSING"{return zero,ErrF91}
  idx:=o.Assignment.ArmIndex
  if idx<0||idx>=6{return zero,ErrF91}
  score[idx]+=o.Score
  compute[idx]+=o.ComputeUnits
  counts[idx]++
 }
 for i,a:=range source.Arms{
  if a.ArmName!=names[i]||a.PolicySHA256!=policies[i]||
   a.Assigned!=counts[i]||a.Observed!=counts[i]||a.Missing!=0{return zero,ErrF91}
  if counts[i]==0{return l,nil}
 }
 l.EveryPolicyArmObserved=true
 radius:=f91ConditionalRadius(len(rows))
 for _,candidate:=range []int{4,5}{
  for control:=0;control<4;control++{
   difference:=new(big.Rat).SetFrac(
    big.NewInt(6*(score[candidate]-score[control])),
    big.NewInt(int64(len(rows))))
   computeDifference:=new(big.Rat).SetFrac(
    big.NewInt(6*(compute[candidate]-compute[control])),
    big.NewInt(int64(len(rows))))
   estimate,_:=difference.Float64()
   l.Comparisons=append(l.Comparisons,F91PolicyContrast{
    CandidateName:names[candidate],ControlName:names[control],
    CandidatePolicySHA256:policies[candidate],ControlPolicySHA256:policies[control],
    ExactIPSScoreDifference:difference.RatString(),
    ExactIPSComputeDifference:computeDifference.RatString(),
    ConditionalLowerScoreDifference:estimate-radius,
    ConditionalUpperScoreDifference:estimate+radius,
    PositivePointEstimate:difference.Sign()>0,
    ConditionalFamilywiseLowerAboveZero:estimate-radius>0,
   })
  }
 }
 return l,nil
}

// ReviewF91 first verifies every F89/F90 receipt and signature. External
// verifier and separately sourced SHA pins are OPTIONAL for diagnostic-only
// use; when supplied they are checked, never upgraded into independent
// scientific acceptance by this library. No execution/network access.
func ReviewF91(w FrozenSixPolicyTrial,wr []F90Observation,
 y FrozenSixPolicyTrial,yr []F90Observation,
 pins []F91ExternalPin,verifier F91ExternalVerifier)(F91Review,error){
 var zero F91Review
 a,err:=AuditF90PreparedOutcomes(w,wr,y,yr)
 if err!=nil||!a.SourceCryptographyConsistent||len(a.Lanes)!=2{return zero,ErrF91}
 out:=F91Review{
  Schema:F91ReviewSchema,SourceCryptographyConsistent:true,
  ConditionalFamilywiseAlpha:0.05,ConditionalComparisonCount:16,
  ConditionalPolicyDifferenceBoundScore100:"BONFERRONI_HOEFFDING_CONDITIONAL_ONLY",
  Status:F91StatusUnverified,
 }
 if (len(pins)!=0||verifier!=nil)&&(len(pins)!=2||verifier==nil){
  return zero,ErrF91
 }
 if len(pins)==2{
  if !f91ValidPin(w,pins[0],wr)||!f91ValidPin(y,pins[1],yr)||
   pins[0].OwnerLedgerSHA256==pins[1].OwnerLedgerSHA256||
   pins[0].WitnessArchiveSHA256==pins[1].WitnessArchiveSHA256||
   pins[0].PreregistrationArchiveSHA256==pins[1].PreregistrationArchiveSHA256{
   return zero,ErrF91
  }
  if verifier.VerifyIndependentProspectiveCohort(w,wr,pins[0])!=nil||
   verifier.VerifyIndependentProspectiveCohort(y,yr,pins[1])!=nil{
   return zero,ErrF91
  }
  out.ReportedExternalSourceVerifierAccepted=true
  out.Status=F91StatusProvider
 }
 for i,src:=range []struct{f FrozenSixPolicyTrial;rows []F90Observation}{
  {w,wr},{y,yr},
 }{
  lr,err:=f91ReviewLane(src.f,src.rows,a.Lanes[i])
  if err!=nil{return zero,ErrF91}
  lr.ReportedSourceVerifierAccepted=out.ReportedExternalSourceVerifierAccepted
  out.Lanes=append(out.Lanes,lr)
  if lr.MissingOutcomes!=0||!lr.EveryPolicyArmObserved{
   out.Status=F91StatusIncomplete
  }
 }
 if out.Status==F91StatusIncomplete{
  out.ReportedExternalSourceVerifierAccepted=false
  for i:=range out.Lanes{out.Lanes[i].ReportedSourceVerifierAccepted=false}
 }
 return out,nil
}
