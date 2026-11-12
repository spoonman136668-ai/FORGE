package nativediscovery

import (
 "encoding/json"
 "math"
 "reflect"
 "testing"
)

// This is a falsifiable benefit gate, not a SCIENTIFIC_PASS or new owner.
func TestF10FullStrongestBaselineBenefitAndEveryNegativePreserved(t *testing.T){
 got,err:=F10Development()
 if err!=nil{t.Fatal(err)}
 replay,err:=F10Development()
 if err!=nil||!reflect.DeepEqual(got,replay){t.Fatal("benefit review is not deterministic",err)}
 if err:=F10Validate(got);err!=nil{t.Fatal("source-bound review invalid",err)}
 if got.Schema!=F10Schema||got.TotalArms!=6||got.TotalGenerations!=2||
  got.TrainingSeeds!=[2]uint32{17,31}||got.Policies!=f5Policies()||
  got.DecisionsPerModelPerGeneration!=F2EvaluationCount||
  got.MinimumAdditionalCorrect!=4||
  got.SourceCandidateRecordsRetained!=48||len(got.Arms)!=6||
  got.OriginalWorldRetentionPassingArms!=6||
  !got.DevelopmentOnly||!got.SameSyntheticTrainingOnly||
  got.IndependentFirstUseConsumed||got.StrongestRealWorldBaselineQualified||
  got.WholeProcessCostMeasured||got.ScientificAccepted||got.OwnerEligible||
  got.DispatchAuthorized||got.ExistingF139LaneAltered||
  got.ExperimentIssued||got.AgentCalls!=0||got.PaidAPICalls!=0{
  t.Fatal("F10 cohort, controls, negatives or hard scientific authority changed")
 }
 positives,gains,changed,threshold,retained:=0,0,0,0,0
 totalStrong,totalNew,worst:=0,0,F2EvaluationCount
 f7,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 f8,err:=F8Development()
 if err!=nil{t.Fatal(err)}
 for i,arm:=range got.Arms{
  if arm.Seed!=f7.Arms[i].Seed||arm.Policy!=f7.Arms[i].Policy||
   arm.Seed!=f8.Arms[i].Seed||arm.Policy!=f8.Arms[i].Policy{
   t.Fatal("source cohort reordered, dropped or substituted")
  }
  prev:=arm.G1G2[0]
  for j,round:=range arm.G1G2{
   original:=f7.Arms[i].Generations[j]
   stored:=f8.Arms[i].Steps[j]
   if round.Generation!=j+1||
    round.SelectedSourceSHA256!=original.SelectedSourceSHA256||
    round.F7ReceiptSHA256!=original.GenerationReceiptSHA256||
    round.F8CheckpointRecordSHA256!=stored.RecordSHA256||
    !round.OriginalWorldRetained||!round.ColdSnapshotVerified||
    round.SelectedCorrect<0||round.SelectedCorrect>F2EvaluationCount||
    round.StrongestMatchedCorrect<round.F3Correct||
    round.StrongestMatchedCorrect<round.TabularCorrect||
    round.StrongestMatchedCorrect<round.FactorizedCorrect||
    round.StrongestMatchedCorrect<round.NativeCorrect||
    round.ExtraCorrectOverStrongest!=round.SelectedCorrect-round.StrongestMatchedCorrect{
    t.Fatal("strongest control omitted or source/retention record drift")
   }
   if j==1&&round.ExtraCorrectSincePrevious!=
    round.SelectedCorrect-prev.SelectedCorrect{
    t.Fatal("G1->G2 benefit or hindsight changed")
   }
  }
  g2:=arm.G1G2[1]
  if arm.G2SourceChanged!=(g2.SelectedSourceSHA256!=prev.SelectedSourceSHA256)||
   arm.G2ClearsStrongestControl!=(g2.ExtraCorrectOverStrongest>=4)||
   arm.G2ImprovesOnG1!=(g2.ExtraCorrectSincePrevious>=4)||
   !arm.G2RetainsOriginalWorld{
   t.Fatal("reported threshold, source update or retention inconsistent")
  }
  if g2.ExtraCorrectOverStrongest>0{positives++}
  if g2.ExtraCorrectSincePrevious>0{gains++}
  if arm.G2SourceChanged{changed++}
  if arm.G2ClearsStrongestControl&&arm.G2ImprovesOnG1&&arm.G2RetainsOriginalWorld{
   threshold++
  }
  if arm.G2RetainsOriginalWorld{retained++}
  totalStrong+=g2.ExtraCorrectOverStrongest
  totalNew+=g2.ExtraCorrectSincePrevious
  if g2.ExtraCorrectOverStrongest<worst{worst=g2.ExtraCorrectOverStrongest}
  t.Logf("F10_TRAIN_DEV seed=%d policy=%s G1=%d/64 G2=%d/64 F3=%d tabular=%d factorized=%d native=%d strongest=%s:%d delta_strong=%+d/64 delta_G1=%+d/64 source_changed=%t",
   arm.Seed,arm.Policy,prev.SelectedCorrect,g2.SelectedCorrect,
   g2.F3Correct,g2.TabularCorrect,g2.FactorizedCorrect,
   g2.NativeCorrect,g2.StrongestMatchedName,g2.StrongestMatchedCorrect,
   g2.ExtraCorrectOverStrongest,g2.ExtraCorrectSincePrevious,arm.G2SourceChanged)
 }
 if got.G2PositiveVersusStrongestArms!=positives||
  got.G2PositiveSinceG1Arms!=gains||got.G2ChangedSourceArms!=changed||
  got.G2ThresholdPassingArms!=threshold||
  got.OriginalWorldRetentionPassingArms!=retained||
  got.TotalG2AdditionalCorrectOverStrongest!=totalStrong||
  got.TotalG2AdditionalCorrectOverG1!=totalNew||
  got.WorstG2AdditionalCorrectOverStrongest!=worst{
  t.Fatal("benefit report hid losses, negatives or failed strict comparisons")
 }
 expectation:=F10ReviewNO_GO
 if threshold==6{expectation=F10ReviewPositive}
 if got.Classification!=expectation||
  (got.Classification!=F10ReviewNO_GO&&got.Classification!=F10ReviewPositive){
  t.Fatal("predeclared F10 threshold outcome relabeled")
 }
 t.Logf("F10_DEV_CLASSIFICATION=%s; strong-positive-arms=%d/6; new-positive-arms=%d/6; full-threshold-arms=%d/6; all-negative-retained=%t; scientific_accepted=false; owner_eligible=false",
  got.Classification,positives,gains,threshold,got.SourceCandidateRecordsRetained==48)
}

func TestF10PreviouslyMissingF3ControlPreventsFalseGo(t *testing.T){
 if n,c,err:=f10StrongestCounts(60,36,42,45);err!=nil||
  n!="f3_prefix_selected"||c!=60{
  t.Fatal("strong existing F3 control omitted from best matched baseline")
 }
 // A selected source that seems +20/64 above the old three-control
 // comparator is actually -15/64 below the original matched F3 control.
 selected,threeWay:=45,25
 if selected-threeWay<4{t.Fatal("invalid negative-control scenario")}
 _,fourWay,err:=f10StrongestCounts(60,threeWay,22,20)
 if err!=nil||selected-fourWay>=F10MinimumAdditionalCorrect{
  t.Fatal("false claimed improvement survived stronger F3 control")
 }
 if n,_,err:=f10StrongestCounts(50,50,50,50);err!=nil||
  n!="f3_prefix_selected"{t.Fatal("nondeterministic tie baseline")}
 for _,bad:=range []int{-1,F2EvaluationCount+1}{
  if _,_,err:=f10StrongestCounts(bad,1,1,1);err==nil{
   t.Fatal("invalid control admitted")
  }
 }
 for _,bad:=range []float64{-1,100.001,math.NaN(),math.Inf(1),33.33}{
  if _,err:=f10Count(bad);err==nil{t.Fatal("invalid or nonintegral decision count admitted")}
 }
}

func TestF10NoOwnerAdmissionByTamperedOrRehashedDevelopmentEvidence(t *testing.T){
 orig,err:=F10Development()
 if err!=nil{t.Fatal(err)}
 clone:=func()F10Review{
  data,err:=json.Marshal(orig)
  if err!=nil{t.Fatal(err)}
  var out F10Review
  if err:=json.Unmarshal(data,&out);err!=nil{t.Fatal(err)}
  return out
 }
 changes:=[]struct{name string;fn func(*F10Review)}{
  {"source",func(r *F10Review){r.ParentF7SHA256="fake"}},
  {"checkpoint",func(r *F10Review){r.ParentF8CheckpointSHA256="fake"}},
  {"holdout",func(r *F10Review){r.IndependentFirstUseConsumed=true}},
  {"science",func(r *F10Review){r.ScientificAccepted=true}},
  {"realworld",func(r *F10Review){r.StrongestRealWorldBaselineQualified=true}},
  {"cost",func(r *F10Review){r.WholeProcessCostMeasured=true}},
  {"owner",func(r *F10Review){r.OwnerEligible=true}},
  {"dispatch",func(r *F10Review){r.DispatchAuthorized=true}},
  {"lane",func(r *F10Review){r.ExistingF139LaneAltered=true}},
  {"issue",func(r *F10Review){r.ExperimentIssued=true}},
  {"agent",func(r *F10Review){r.AgentCalls=1}},
  {"paid",func(r *F10Review){r.PaidAPICalls=1}},
  {"seed",func(r *F10Review){r.TrainingSeeds[0]=59}},
  {"missing arm",func(r *F10Review){r.Arms=r.Arms[:5]}},
  {"score",func(r *F10Review){r.Arms[0].G1G2[1].SelectedCorrect=64}},
  {"baseline",func(r *F10Review){r.Arms[0].G1G2[1].F3Correct=0}},
  {"family",func(r *F10Review){r.Arms[0].G1G2[1].SelectedFamily="new-unproven"}},
  {"source",func(r *F10Review){r.Arms[0].G1G2[1].SelectedSourceSHA256="false"}},
  {"receipt",func(r *F10Review){r.Arms[0].G1G2[0].F7ReceiptSHA256="false"}},
  {"missing negatives",func(r *F10Review){r.SourceCandidateRecordsRetained=47}},
  {"class",func(r *F10Review){r.Classification=F10ReviewPositive}},
  {"threshold",func(r *F10Review){r.MinimumAdditionalCorrect=0}},
  {"reorder",func(r *F10Review){r.Arms[0],r.Arms[1]=r.Arms[1],r.Arms[0]}},
 }
 for _,tc:=range changes{t.Run(tc.name,func(t *testing.T){
  r:=clone();tc.fn(&r)
  // Even a self-consistent forged local hash is not independent custody.
  r.DigestSHA256=f10Digest(r)
  if err:=F10Validate(r);err==nil{t.Fatal("forged F10 source/authority/go claim accepted")}
 })}
}

// This fixed numerical witness was reconstructed independently from the
// previously frozen F2 action-consequence generator, F3 readouts, F5 action
// policy and F6 source grammar. It is NOT used to select an algorithm or
// alter the F10 development criterion. It makes the exact observed NO_GO
// reproducible under the ORIGINAL mandatory Go test suite, without a new
// workflow, source owner, research runner or synthetic first use.
func TestF10IndependentSixArmGoldenScorecard(t *testing.T){
 report,err:=F10Development()
 if err!=nil{t.Fatal(err)}
 if err:=F10Validate(report);err!=nil{t.Fatal(err)}
 type witness struct{
  seed uint32
  policy string
  g1,g2 int
  f3,tab,factor,native int
  strongest int
  strongestName string
  deltaStrong,deltaPrevious int
  g1Family,g2Family string
 }
 expected:=[]witness{
  {17,"disagreement",40,48,48,48,40,48,48,"f3_prefix_selected",0,8,"cue-mode-xor","cue-mode-xor"},
  {17,"fixed",44,52,52,52,52,52,52,"f3_prefix_selected",0,8,"constant","constant"},
  {17,"random",46,42,46,46,42,42,46,"f3_prefix_selected",-4,-4,"cue-parity","constant"},
  {31,"disagreement",34,44,40,40,42,36,42,"factorized",2,10,"cue-parity","cue-mode-xor"},
  {31,"fixed",34,50,50,50,50,50,50,"f3_prefix_selected",0,16,"cue-parity","cue-mode-xor"},
  {31,"random",32,44,40,40,42,36,42,"factorized",2,12,"constant","cue-mode-xor"},
 }
 if len(report.Arms)!=len(expected){t.Fatalf("missing or extra arms: %d",len(report.Arms))}
 for i,w:=range expected{
  arm:=report.Arms[i]
  g1,g2:=arm.G1G2[0],arm.G1G2[1]
  if arm.Seed!=w.seed||arm.Policy!=w.policy||
   g1.SelectedCorrect!=w.g1||g2.SelectedCorrect!=w.g2||
   g2.F3Correct!=w.f3||g2.TabularCorrect!=w.tab||
   g2.FactorizedCorrect!=w.factor||g2.NativeCorrect!=w.native||
   g2.StrongestMatchedCorrect!=w.strongest||
   g2.StrongestMatchedName!=w.strongestName||
   g2.ExtraCorrectOverStrongest!=w.deltaStrong||
   g2.ExtraCorrectSincePrevious!=w.deltaPrevious||
   g1.SelectedFamily!=w.g1Family||g2.SelectedFamily!=w.g2Family{
   t.Fatalf("F10_INDEPENDENT_GOLDEN_SCORE_DRIFT index=%d seed=%d policy=%s "+
    "actual G1=%d/64 G2=%d/64 F3=%d tab=%d factor=%d native=%d "+
    "best=%s:%d deltaStrong=%+d deltaG1=%+d family=%s->%s "+
    "expected=%+v",
    i,arm.Seed,arm.Policy,g1.SelectedCorrect,g2.SelectedCorrect,
    g2.F3Correct,g2.TabularCorrect,g2.FactorizedCorrect,g2.NativeCorrect,
    g2.StrongestMatchedName,g2.StrongestMatchedCorrect,
    g2.ExtraCorrectOverStrongest,g2.ExtraCorrectSincePrevious,
    g1.SelectedFamily,g2.SelectedFamily,w)
  }
  t.Logf("F10_INDEPENDENT_GOLDEN_PASS seed=%d policy=%s G1=%d/64 G2=%d/64 "+
   "F3=%d/64 tab=%d/64 factor=%d/64 native=%d/64 "+
   "strongest=%d/64 deltaStrong=%+d/64 deltaG1=%+d/64",
   arm.Seed,arm.Policy,g1.SelectedCorrect,g2.SelectedCorrect,
   g2.F3Correct,g2.TabularCorrect,g2.FactorizedCorrect,
   g2.NativeCorrect,g2.StrongestMatchedCorrect,
   g2.ExtraCorrectOverStrongest,g2.ExtraCorrectSincePrevious)
 }
 if report.Classification!=F10ReviewNO_GO||
  report.G2PositiveVersusStrongestArms!=2||
  report.G2PositiveSinceG1Arms!=5||
  report.G2ThresholdPassingArms!=0||
  report.G2ChangedSourceArms!=4||
  report.TotalG2AdditionalCorrectOverStrongest!=0||
  report.WorstG2AdditionalCorrectOverStrongest!= -4||
  report.TotalG2AdditionalCorrectOverG1!=50||
  report.SourceCandidateRecordsRetained!=48||
  report.OriginalWorldRetentionPassingArms!=6||
  report.ScientificAccepted||report.OwnerEligible||
  report.DispatchAuthorized||report.ExperimentIssued{
  t.Fatalf("F10_RECONSTRUCTED_NO_GO_AND_OWNER_FENCE_MISMATCH class=%s strongPositive=%d "+
   "g1Positive=%d threshold=%d sourceChanges=%d sumStrong=%d worstStrong=%d "+
   "sumNew=%d retained=%d originalRetained=%d",
   report.Classification,report.G2PositiveVersusStrongestArms,
   report.G2PositiveSinceG1Arms,report.G2ThresholdPassingArms,
   report.G2ChangedSourceArms,report.TotalG2AdditionalCorrectOverStrongest,
   report.WorstG2AdditionalCorrectOverStrongest,
   report.TotalG2AdditionalCorrectOverG1,
   report.SourceCandidateRecordsRetained,report.OriginalWorldRetentionPassingArms)
 }
 t.Log("F10_INDEPENDENT_GOLDEN_CLASSIFICATION=F10_DEV_NO_GO_AGAINST_STRONGEST_CONTROL")
}
