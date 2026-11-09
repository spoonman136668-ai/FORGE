// Eureka F10: strongest-matched-control benefit gate BEFORE any FORGE owner
// eligibility or native research intake changes. Entirely development-only.
// Reuses existing F7/F8 recorded outcomes; no new observation or execution.
package nativediscovery

import (
 "errors"
 "math"
 "reflect"
 "sync"
)

const F10Schema = "forge.native-discovery.eureka-benefit-before-owner.dev.v1"
const F10MinimumAdditionalCorrect = 4
const F10ReviewNO_GO = "F10_DEV_NO_GO_AGAINST_STRONGEST_CONTROL"
const F10ReviewPositive = "F10_DEV_POSITIVE_DIAGNOSTIC_ONLY"
var errF10=errors.New("FORGE_EUREKA_F10_BENEFIT_OR_OWNER_FENCE_INVALID")

type F10Round struct{
 Generation int `json:"generation"`
 F7ReceiptSHA256 string `json:"f7_receipt_sha256"`
 F8CheckpointRecordSHA256 string `json:"f8_checkpoint_record_sha256"`
 SelectedSourceSHA256 string `json:"selected_source_sha256"`
 SelectedFamily string `json:"selected_family"`
 SelectedCorrect int `json:"selected_correct_of_64"`
 F3Correct int `json:"f3_correct_of_64"`
 TabularCorrect int `json:"tabular_correct_of_64"`
 FactorizedCorrect int `json:"factorized_correct_of_64"`
 NativeCorrect int `json:"native_correct_of_64"`
 StrongestMatchedCorrect int `json:"strongest_matched_correct_of_64"`
 StrongestMatchedName string `json:"strongest_matched_name"`
 ExtraCorrectOverStrongest int `json:"extra_correct_over_strongest"`
 ExtraCorrectSincePrevious int `json:"extra_correct_since_previous"`
 OriginalWorldRetained bool `json:"original_world_retained"`
 ColdSnapshotVerified bool `json:"cold_snapshot_verified"`
}

type F10Arm struct{
 Seed uint32 `json:"seed"`
 Policy string `json:"policy"`
 G1G2 [F7Generations]F10Round `json:"g1_g2"`
 G2ClearsStrongestControl bool `json:"g2_clears_strongest_control"`
 G2ImprovesOnG1 bool `json:"g2_improves_on_g1"`
 G2SourceChanged bool `json:"g2_source_changed"`
 G2RetainsOriginalWorld bool `json:"g2_retains_original_world"`
}

type F10Review struct{
 Schema string `json:"schema"`
 ParentF7SHA256 string `json:"parent_f7_sha256"`
 ParentF8CheckpointSHA256 string `json:"parent_f8_checkpoint_sha256"`
 TrainingSeeds [2]uint32 `json:"training_seeds"`
 Policies [3]string `json:"policies"`
 TotalArms int `json:"total_arms"`
 TotalGenerations int `json:"total_generations"`
 DecisionsPerModelPerGeneration int `json:"decisions_per_model_per_generation"`
 MinimumAdditionalCorrect int `json:"minimum_additional_correct"`
 TotalG2AdditionalCorrectOverStrongest int `json:"total_g2_additional_correct_over_strongest"`
 WorstG2AdditionalCorrectOverStrongest int `json:"worst_g2_additional_correct_over_strongest"`
 TotalG2AdditionalCorrectOverG1 int `json:"total_g2_additional_correct_over_g1"`
 G2PositiveVersusStrongestArms int `json:"g2_positive_versus_strongest_arms"`
 G2PositiveSinceG1Arms int `json:"g2_positive_since_g1_arms"`
 G2ChangedSourceArms int `json:"g2_changed_source_arms"`
 G2ThresholdPassingArms int `json:"g2_threshold_passing_arms"`
 OriginalWorldRetentionPassingArms int `json:"original_world_retention_passing_arms"`
 SourceCandidateRecordsRetained int `json:"source_candidate_records_retained"`
 Arms []F10Arm `json:"arms"`
 Classification string `json:"classification"`
 DevelopmentOnly bool `json:"development_only"`
 SameSyntheticTrainingOnly bool `json:"same_synthetic_training_only"`
 IndependentFirstUseConsumed bool `json:"independent_first_use_consumed"`
 StrongestRealWorldBaselineQualified bool `json:"strongest_real_world_baseline_qualified"`
 WholeProcessCostMeasured bool `json:"whole_process_cost_measured"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OwnerEligible bool `json:"owner_eligible"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ExistingF139LaneAltered bool `json:"existing_f139_lane_altered"`
 ExperimentIssued bool `json:"experiment_issued"`
 AgentCalls int `json:"agent_calls"`
 PaidAPICalls int `json:"paid_api_calls"`
 DigestSHA256 string `json:"digest_sha256"`
}

func f10Count(pct float64)(int,error){
 if math.IsNaN(pct)||math.IsInf(pct,0)||pct<0||pct>100{return 0,errF10}
 count:=int(math.Round(pct*float64(F2EvaluationCount)/100))
 if count<0||count>F2EvaluationCount||
  math.Abs(pct-float64(count)*100/float64(F2EvaluationCount))>1e-9{
  return 0,errF10
 }
 return count,nil
}

func f10StrongestCounts(f3,tabular,factorized,native int)(string,int,error){
 controls:=[4]struct{name string;n int}{
  {"f3_prefix_selected",f3},
  {"tabular",tabular},
  {"factorized",factorized},
  {"f2_native",native},
 }
 for _,c:=range controls{if c.n<0||c.n>F2EvaluationCount{return "",0,errF10}}
 winner:=controls[0]
 for _,c:=range controls[1:]{
  if c.n>winner.n{winner=c}
 }
 return winner.name,winner.n,nil
}

func f10Round(g F7Generation,step F8Step,previous *F10Round)(F10Round,error){
 if g.Generation!=step.Generation||g.Generation<1||g.Generation>F7Generations||
  g.GenerationReceiptSHA256!=step.F7GenerationReceiptSHA256||
  g.SelectedFamily!=step.SelectedFamily||g.SelectedPhase!=step.SelectedPhase||
  g.SelectedSourceSHA256!=step.SelectedSourceSHA256||
  g.OriginalWorldColdPct!=g.OriginalWorldBeforePct||
  g.OriginalWorldColdPct!=g.OriginalWorldAfterPct||
  !g.ColdReadbackIdentical||
  !step.ExactFullReplayMatches||!step.ColdStateReadbackMatches||
  step.RecordSHA256!=f8StepDigest(step)||step.SnapshotSHA256!=f3Hash(step.SnapshotBytes){
  return F10Round{},errF10
 }
 v:=[]float64{
  g.SelectedDevAccuracyPct,g.PriorF5SelectedAccuracyPct,
  g.TabularAccuracyPct,g.FactorizedAccuracyPct,g.ExistingNativeAccuracyPct,
 }
 var counts [5]int
 for i,pct:=range v{
  count,err:=f10Count(pct)
  if err!=nil{return F10Round{},err}
  counts[i]=count
 }
 name,strongest,err:=f10StrongestCounts(counts[1],counts[2],counts[3],counts[4])
 if err!=nil{return F10Round{},err}
 if best,err:=f10Count(g.StrongestControlAccuracyPct);err!=nil||
  best!=max(counts[2],max(counts[3],counts[4])){
  return F10Round{},errF10
 }
 row:=F10Round{Generation:g.Generation,F7ReceiptSHA256:g.GenerationReceiptSHA256,
  F8CheckpointRecordSHA256:step.RecordSHA256,
  SelectedSourceSHA256:g.SelectedSourceSHA256,SelectedFamily:g.SelectedFamily,
  SelectedCorrect:counts[0],F3Correct:counts[1],TabularCorrect:counts[2],
  FactorizedCorrect:counts[3],NativeCorrect:counts[4],
  StrongestMatchedCorrect:strongest,StrongestMatchedName:name,
  ExtraCorrectOverStrongest:counts[0]-strongest,
  OriginalWorldRetained:true,ColdSnapshotVerified:true}
 if previous!=nil{
  if previous.Generation!=1||g.Generation!=2{return F10Round{},errF10}
  row.ExtraCorrectSincePrevious=row.SelectedCorrect-previous.SelectedCorrect
  if prev,err:=f10Count(g.GainOverPreviousGenerationPP+float64(previous.SelectedCorrect)*100/float64(F2EvaluationCount));err!=nil||
   prev!=row.SelectedCorrect{return F10Round{},errF10}
 }else if g.Generation!=1{return F10Round{},errF10}
 return row,nil
}

func f10Digest(out F10Review)string{
 out.DigestSHA256=""
 return f8Digest("FORGE-EUREKA-F10-BENEFIT-REVIEW-V1\n",out)
}

// F10Development is a READ-ONLY result, not an optimizer, FORGE owner
// admission, F139 ticket, experiment runner or scientific acceptance.
func F10Development()(F10Review,error){
 f7,err:=F7Development()
 if err!=nil||F7ValidatePreview(f7)!=nil||len(f7.Arms)!=6||
  f7.NewExperimentObservations!=0||f7.IndependentHoldoutConsumed||
  f7.ScientificAccepted||f7.OwnerActivation||f7.DispatchAuthorized{
  return F10Review{},errF10
 }
 f8,err:=F8Development()
 if err!=nil||F8Validate(f8)!=nil||len(f8.Arms)!=6||
  f8.ScientificAccepted||f8.OwnerActivation||f8.DispatchAuthorized||
  f8.GeneratedSourceExecuted||f8.NewGeneratedObservations!=0{
  return F10Review{},errF10
 }
 out:=F10Review{
  Schema:F10Schema,
  ParentF7SHA256:f8.F7ReportSHA256,
  ParentF8CheckpointSHA256:f8.CheckpointSHA256,
  TrainingSeeds:f7.TrainingSeeds,Policies:f7.Policies,
  TotalArms:len(f7.Arms),TotalGenerations:F7Generations,
  DecisionsPerModelPerGeneration:F2EvaluationCount,
  MinimumAdditionalCorrect:F10MinimumAdditionalCorrect,
  Arms:make([]F10Arm,0,6),DevelopmentOnly:true,
  SameSyntheticTrainingOnly:true,
  WorstG2AdditionalCorrectOverStrongest:F2EvaluationCount,
 }
 for i,arm:=range f7.Arms{
  history:=f8.Arms[i]
  if arm.Seed!=history.Seed||arm.Policy!=history.Policy||
   arm.Seed!=f7.TrainingSeeds[i/3]||arm.Policy!=f7.Policies[i%3]||
   len(arm.Generations)!=F7Generations{
   return F10Review{},errF10
  }
  review:=F10Arm{Seed:arm.Seed,Policy:arm.Policy}
  g1,err:=f10Round(arm.Generations[0],history.Steps[0],nil)
  if err!=nil{return F10Review{},err}
  g2,err:=f10Round(arm.Generations[1],history.Steps[1],&g1)
  if err!=nil{return F10Review{},err}
  review.G1G2=[F7Generations]F10Round{g1,g2}
  review.G2ClearsStrongestControl=g2.ExtraCorrectOverStrongest>=F10MinimumAdditionalCorrect
  review.G2ImprovesOnG1=g2.ExtraCorrectSincePrevious>=F10MinimumAdditionalCorrect
  review.G2SourceChanged=g2.SelectedSourceSHA256!=g1.SelectedSourceSHA256
  review.G2RetainsOriginalWorld=g2.OriginalWorldRetained&&g2.ColdSnapshotVerified&&
   g1.OriginalWorldRetained&&g1.ColdSnapshotVerified
  out.TotalG2AdditionalCorrectOverStrongest+=g2.ExtraCorrectOverStrongest
  out.TotalG2AdditionalCorrectOverG1+=g2.ExtraCorrectSincePrevious
  if g2.ExtraCorrectOverStrongest<out.WorstG2AdditionalCorrectOverStrongest{
   out.WorstG2AdditionalCorrectOverStrongest=g2.ExtraCorrectOverStrongest
  }
  if g2.ExtraCorrectOverStrongest>0{out.G2PositiveVersusStrongestArms++}
  if g2.ExtraCorrectSincePrevious>0{out.G2PositiveSinceG1Arms++}
  if review.G2SourceChanged{out.G2ChangedSourceArms++}
  if review.G2RetainsOriginalWorld{out.OriginalWorldRetentionPassingArms++}
  if review.G2ClearsStrongestControl&&review.G2ImprovesOnG1&&
   review.G2RetainsOriginalWorld{
   out.G2ThresholdPassingArms++
  }
  out.SourceCandidateRecordsRetained+=
   len(arm.Generations[0].Candidates)+len(arm.Generations[1].Candidates)
  out.Arms=append(out.Arms,review)
 }
 if out.SourceCandidateRecordsRetained!=48||
  out.TotalArms!=6||out.OriginalWorldRetentionPassingArms!=6{return F10Review{},errF10}
 if out.G2ThresholdPassingArms==out.TotalArms{
  out.Classification=F10ReviewPositive
 }else{out.Classification=F10ReviewNO_GO}
 out.DigestSHA256=f10Digest(out)
 return out,nil
}


// Immutable per-process reference used only to validate external F10 evidence.
// F10Development itself remains fully independent and cold-regenerating.
var f10ValidationCanonical struct{
 once sync.Once
 report F10Review
 err error
}
func f10CanonicalEqual(v F10Review)bool{
 f10ValidationCanonical.once.Do(func(){
  f10ValidationCanonical.report, f10ValidationCanonical.err=F10Development()
 })
 return f10ValidationCanonical.err==nil && reflect.DeepEqual(v,f10ValidationCanonical.report)
}

func F10Validate(review F10Review)error{
 if review.Schema!=F10Schema||review.DigestSHA256!=f10Digest(review)||
  !review.DevelopmentOnly||!review.SameSyntheticTrainingOnly||
  review.IndependentFirstUseConsumed||review.StrongestRealWorldBaselineQualified||
  review.WholeProcessCostMeasured||review.ScientificAccepted||review.OwnerEligible||
  review.DispatchAuthorized||review.ExistingF139LaneAltered||
  review.ExperimentIssued||review.AgentCalls!=0||review.PaidAPICalls!=0{
  return errF10
 }
 if !f10CanonicalEqual(review){return errF10}
 return nil
}
