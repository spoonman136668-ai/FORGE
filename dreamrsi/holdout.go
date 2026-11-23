package dreamrsi

// Holdout assessment is an independently pinned and explicitly separate,
// read-only audit operation. Optimize NEVER sees heldout records or outcomes.
// Repeat-consumption protection must be supplied by the future FSA's
// protected external monotonic first-use register, not by this source-only API.
import (
 "encoding/json"
)
const HoldoutSpecSchema="forge.dreamrsi.sealed-policy-holdout.v1"
const HoldoutReportSchema="forge.dreamrsi.holdout-observation.v1"
type HoldoutSpec struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 SelectedPolicySHA256 string `json:"selected_policy_sha256"`
 FrozenOptimizerHeadSHA256 string `json:"frozen_optimizer_head_sha256"`
 HoldoutHistorySHA256 string `json:"holdout_history_sha256"`
 HoldoutAfterTick uint64 `json:"holdout_after_tick"`
 MaxHoldoutDecisions int `json:"max_holdout_decisions"`
 MinEffectiveSampleSize float64 `json:"min_effective_sample_size"`
 MinMatchBP int `json:"min_match_bp"`
 FirstUseReceiptSHA256 string `json:"first_use_receipt_sha256"`
}
type HoldoutReport struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenHoldoutSpecSHA256 string `json:"frozen_holdout_spec_sha256"`
 OriginalHoldoutHistorySHA256 string `json:"original_holdout_history_sha256"`
 OptimizerLineageHeadSHA256 string `json:"optimizer_lineage_head_sha256"`
 Selected Replay `json:"selected"`
 Baselines []Replay `json:"baselines"`
 AllComparable bool `json:"all_comparable"`
 ProvisionalQualityDominance bool `json:"provisional_quality_dominance"`
 MultipleComparisonsAndCausalAuditRequired bool `json:"multiple_comparisons_and_causal_audit_required"`
 ImprovementEstablished bool `json:"improvement_established"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func AssessHoldout(frozen Optimization,train,validation,heldout Verified,
 spec HoldoutSpec,independentlyPinnedSpecSHA string)(HoldoutReport,error){
 var empty HoldoutReport
 if ValidateOptimization(frozen)!=nil||!frozen.QualifiedForProspectiveTest||
  !validHex(independentlyPinnedSpecSHA,64)||
  spec.Schema!=HoldoutSpecSchema||spec.Lane!=frozen.Lane||
  spec.Epoch!=train.Epoch||spec.Epoch!=validation.Epoch||spec.Epoch!=heldout.Epoch||
  spec.SelectedPolicySHA256!=frozen.SelectedPolicySHA256||
  spec.FrozenOptimizerHeadSHA256!=frozen.LineageHeadSHA256||
  spec.HoldoutHistorySHA256!=heldout.HistorySHA256||
  spec.MaxHoldoutDecisions<1||spec.MaxHoldoutDecisions>20000||
  len(heldout.Decisions)==0||len(heldout.Decisions)>spec.MaxHoldoutDecisions||
  spec.MinMatchBP<1000||spec.MinMatchBP>10000||
  spec.MinEffectiveSampleSize<4||spec.MinEffectiveSampleSize>10000||
  !validHex(spec.FirstUseReceiptSHA256,64)||
  train.HistorySHA256!=frozen.TrainingSHA256||
  validation.HistorySHA256!=frozen.ValidationSHA256{
  return empty,ErrFrozen
 }
 raw,err:=json.Marshal(spec)
 if err!=nil||hash(raw)!=independentlyPinnedSpecSHA{return empty,ErrFrozen}
 if err=VerifyTemporalHoldout(train,validation,heldout,spec.HoldoutAfterTick);err!=nil{
  return empty,err
 }
 for _,d:=range heldout.Decisions{
  if d.LoggingMode!=Randomized{return empty,ErrUnsupported}
 }
 selected,err:=Evaluate(frozen.Selected,heldout,spec.MinEffectiveSampleSize,spec.MinMatchBP)
 if err!=nil{return empty,err}
 result:=HoldoutReport{Schema:HoldoutReportSchema,Lane:frozen.Lane,
  FrozenHoldoutSpecSHA256:independentlyPinnedSpecSHA,
  OriginalHoldoutHistorySHA256:heldout.HistorySHA256,
  OptimizerLineageHeadSHA256:frozen.LineageHeadSHA256,Selected:selected,
  AllComparable:selected.CanCompare,
  MultipleComparisonsAndCausalAuditRequired:true}
 for i:=0;i<4;i++{
  baseline:=frozen.Records[i].Policy
  r,err:=Evaluate(baseline,heldout,spec.MinEffectiveSampleSize,spec.MinMatchBP)
  if err!=nil{return empty,err}
  result.Baselines=append(result.Baselines,r)
  result.AllComparable=result.AllComparable&&r.CanCompare
 }
 if result.AllComparable{
  result.ProvisionalQualityDominance=true
  for _,baseline:=range result.Baselines{
   if !SafeImprovement(selected,baseline){
    result.ProvisionalQualityDominance=false
   }
  }
 }
 // "Provisional" is intentionally NOT confirmed generalizable quality,
 // causal discovery, lower compute or independent FSA scientific acceptance.
 return result,nil
}
