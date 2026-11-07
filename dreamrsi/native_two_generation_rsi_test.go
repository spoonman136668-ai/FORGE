package dreamrsi

import (
 "encoding/json"
 "reflect"
 "testing"
)

// Pre-registered source-only diagnostic of the EXISTING Dream-RSI mutation
// mechanism. Fixtures are synthetic: no research benefit or authentic RSI
// claim is permitted, even if a heldout ratio happens to pass.
const twoGenFrozenSeed uint64 = 412021
const twoGenMinHeldoutGainRatio = 1.03
const twoGenMaxEvaluations = 128
const twoGenMaxReplays = 24000

func twoGenChampion(records []PolicyRecord, maxGen int)(PolicyRecord,bool){
 var best PolicyRecord
 found:=false
 for _,rec:=range records{
  if rec.Policy.Generation>maxGen||!rec.Validation.CanCompare{continue}
  if !found||better(
   ranked{policy:rec.Policy,train:rec.Train,validation:rec.Validation},
   ranked{policy:best.Policy,train:best.Train,validation:best.Validation}){
   best=rec
   found=true
  }
 }
 return best,found
}

func TestAgentFreeTwoGenerationSelectorRehearsal(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   // Freeze source-internal, deliberately synthetic chronological histories
   // before optimizing. Holdout data must not be passed into Optimize.
   train,validation,spec,_:=frozen(t,lane)
   _,_,hold:=signedFixture(t,lane,220,90)
   spec.MaxGenerations=2
   spec.Seed=twoGenFrozenSeed
   spec.MaxEvaluations=twoGenMaxEvaluations
   spec.MaxReplayDecisions=twoGenMaxReplays
   raw,err:=json.Marshal(spec)
   if err!=nil{t.Fatal(err)}
   pin:=hash(raw)
   if err:=VerifyTemporalHoldout(train,validation,hold,200);err!=nil{t.Fatal(err)}
   result,err:=Optimize(train,validation,spec,pin)
   if err!=nil{t.Fatal(err)}
   if err:=ValidateOptimization(result);err!=nil{t.Fatal(err)}
   other,err:=Optimize(train,validation,spec,pin)
   if err!=nil||!reflect.DeepEqual(result,other){t.Fatal("native replay not deterministic")}
   drift:=spec
   drift.Seed++
   if _,err:=Optimize(train,validation,drift,pin);err==nil{t.Fatal("frozen seed drift accepted")}
   baseline,ok0:=twoGenChampion(result.Records[:4],0)
   g1,ok1:=twoGenChampion(result.Records,1)
   g2,ok2:=twoGenChampion(result.Records,2)
   if !ok0||!ok1||!ok2{t.Fatal("no comparable generation champion")}
   n1,n2:=0,0
   for _,rec:=range result.Records{
    if rec.Policy.Generation==1{n1++}
    if rec.Policy.Generation==2{n2++}
   }
   if n1==0||n2==0{t.Fatal("two native generations were not evaluated")}
   b,err:=Evaluate(baseline.Policy,hold,spec.MinEffectiveSampleSize,spec.MinMatchBP)
   if err!=nil{t.Fatal(err)}
   one,err:=Evaluate(g1.Policy,hold,spec.MinEffectiveSampleSize,spec.MinMatchBP)
   if err!=nil{t.Fatal(err)}
   two,err:=Evaluate(g2.Policy,hold,spec.MinEffectiveSampleSize,spec.MinMatchBP)
   if err!=nil{t.Fatal(err)}
   // Frozen development diagnostic, NOT scientific acceptance. The final
   // policy may remain an ancestor. Count a null result honestly.
   improved:=g1.Policy.Generation==1&&g2.Policy.Generation==2&&
    b.CanCompare&&one.CanCompare&&two.CanCompare&&
    SafeImprovement(two,one)&&SafeImprovement(two,b)&&
    two.GainPerCompute>=one.GainPerCompute*twoGenMinHeldoutGainRatio&&
    two.GainPerCompute>=b.GainPerCompute*twoGenMinHeldoutGainRatio
   status:="SYNTHETIC_NO_GO"
   if improved{status="SYNTHETIC_PROVISIONAL_ONLY"}
   receipt:=map[string]interface{}{
    "schema":"forge.rsi.native-two-generation-rehearsal.v1",
    "lane":lane,"source":"SYNTHETIC_NOT_ORIGINAL_FORGE_RESEARCH_HISTORY",
    "spec_sha256":pin,
    "train_sha256":train.HistorySHA256,
    "validation_sha256":validation.HistorySHA256,
    "heldout_sha256":hold.HistorySHA256,
    "lineage_sha256":result.LineageHeadSHA256,
    "baseline_policy_sha256":baseline.PolicySHA256,
    "g1_policy_sha256":g1.PolicySHA256,
    "g2_policy_sha256":g2.PolicySHA256,
    "g1_generation":g1.Policy.Generation,
    "g2_generation":g2.Policy.Generation,
    "g1_new_policies":n1,"g2_new_policies":n2,
    "baseline_heldout_gain_per_compute":b.GainPerCompute,
    "g1_heldout_gain_per_compute":one.GainPerCompute,
    "g2_heldout_gain_per_compute":two.GainPerCompute,
    "baseline_holdout_comparable":b.CanCompare,
    "g1_holdout_comparable":one.CanCompare,
    "g2_holdout_comparable":two.CanCompare,
    "evals":result.EvaluationsUsed,
    "max_evals":spec.MaxEvaluations,
    "replays":result.DecisionReplaysUsed,
    "max_replays":spec.MaxReplayDecisions,
    "frozen_min_ratio":twoGenMinHeldoutGainRatio,
    "frozen_criterion_met":improved,
    "result":status,
    "agent_calls":0,
    "authentic_rsi_proven":false,
    "scientific_accepted":false,
    "owner_activation":false,
    "accepted_ref_promotion":false,
   }
   out,err:=json.Marshal(receipt)
   if err!=nil{t.Fatal(err)}
   t.Logf("FORGE_NATIVE_RSI_TWO_GEN=%s",out)
   if result.EvaluationsUsed>spec.MaxEvaluations||
    result.DecisionReplaysUsed>spec.MaxReplayDecisions||
    result.ScientificAccepted||result.DispatchAuthorized||
    result.ImprovementEstablished{
    t.Fatal("native budget/authority boundary violated")
   }
  })
 }
}
