package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"
)

func TestF5TournamentExactTrainingSourceBudgetAndNegativeRetention(t *testing.T){
 first,err:=F5Development();if err!=nil{t.Fatal(err)}
 repeat,err:=F5Development();if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(first,repeat){t.Fatal("non-deterministic intervention tournament")}
 parent,err:=F4Development();if err!=nil{t.Fatal(err)}
 if first.Schema!=F5Schema||first.F4Schema!=F4Schema||
  first.F4GeneratedSourceSHA256!=parent.ParentGeneratedSourceSHA256||
  first.NativeGeneratorFrozenSHA256!=parent.NativeGeneratorFrozenSHA256||
  first.SyntheticTrainingHistorySHA256!=parent.SyntheticTrainingHistorySHA256||
  first.TrainingSeeds!=[2]uint32{17,31}||
  first.Policies!=[3]string{"disagreement","fixed","random"}||
  first.DevelopmentStatus!="TRAIN_ONLY_SCIENCE_UNVERIFIED"||
  len(first.Arms)!=6||!first.ReusedSyntheticTraining||
  first.IndependentHoldoutConsumed||first.NewMechanismGenerated||
  first.ScientificAccepted||first.GeneralRSIProven||
  first.OwnerActivation||first.DispatchAuthorized||
  first.AgentCalls!=0||first.PaidAPICalls!=0{
  t.Fatalf("training custody, source identity or authority drift: %+v",first)
 }
 for index,arm:=range first.Arms{
  seed,policy:=first.TrainingSeeds[index/3],first.Policies[index%3]
  if arm.Seed!=seed||arm.Policy!=policy||
   arm.TrainObservations!=F2TrainCount||
   arm.ProbeObservations!=F5ProbeBudget||
   arm.ScoredDecisionsPerModel!=F2EvaluationCount||
   len(arm.Probes)!=F5ProbeBudget||len(arm.Candidates)!=3{
   t.Fatalf("source or action-observation budget drift %+v",arm)
  }
  expectedCalls:=F5ProbeBudget*3
  if policy=="disagreement"{expectedCalls=117}
  if arm.PlannerPredictionCalls!=expectedCalls{
   t.Fatalf("%s planner lookup budget unaccounted: %d != %d",policy,arm.PlannerPredictionCalls,expectedCalls)
  }
  seen:=[8]bool{}
  evidence:=[3]int{}
  disagreement:=0
  fixedKeys:=[6]int{0,2,4,6,1,5}
  for step,probe:=range arm.Probes{
   key:=probe.Cue*2+probe.Mode
   if probe.Step!=step||probe.Cue<0||probe.Cue>=4||
    probe.Mode<0||probe.Mode>=2||key<0||key>=8||seen[key]||
    probe.Action!=step%2||probe.ObservedEffect!=1&&probe.ObservedEffect!= -1{
    t.Fatalf("invalid/duplicate/nonmatching intervention: %+v",probe)
   }
   seen[key]=true
   if policy=="fixed"&&key!=fixedKeys[step]{t.Fatal("fixed conventional policy drift")}
   expected:=f2make(seed,1,probe.Cue,probe.Mode,probe.Action,50+step)
   if expected.Effect!=probe.ObservedEffect{t.Fatalf("environment outcome forged at step %d",step)}
   if probe.DivergentPairs!=f5Pairs(probe.PreObservationPredictions){
    t.Fatal("counterfactual disagreement tally drift")
   }
   if probe.DivergentPairs>0{disagreement++}
   if err:=f5ScoreFeedback(&evidence,probe.PreObservationPredictions,probe.Action,probe.ObservedEffect);err!=nil{
    t.Fatal("valid observed feedback rejected",err)
   }
  }
  if arm.DisagreementProbeCount!=disagreement{t.Fatal("disagreement encounter miscount")}
  winner:=0
  for i,candidate:=range arm.Candidates {
   if candidate.CandidateID!=parent.Candidates[i].CandidateID||
    candidate.StructuralSourceSHA256!=parent.Candidates[i].StructuralSourceSHA256||
    candidate.F4BehaviorSHA256!=parent.Candidates[i].TrainingBehaviorSHA256||
    candidate.F4DuplicateBehaviorOf!=parent.Candidates[i].DuplicateBehaviorOf||
    candidate.EvidenceScore!=evidence[i]||
    candidate.ChangedWorldAccuracyPct<0||candidate.ChangedWorldAccuracyPct>100{
    t.Fatalf("candidate source or outcome corrupted: %+v",candidate)
   }
   if candidate.EvidenceScore>arm.Candidates[winner].EvidenceScore{winner=i}
  }
  if arm.SelectedCandidateID!=arm.Candidates[winner].CandidateID||
   arm.SelectedAccuracyPct!=arm.Candidates[winner].ChangedWorldAccuracyPct{
   t.Fatal("candidate selected by revealed outcome or stale ranking")
  }
  best:=arm.TabularAccuracyPct
  if arm.FactorizedAccuracyPct>best{best=arm.FactorizedAccuracyPct}
  if arm.ExistingF2NativeAccuracyPct>best{best=arm.ExistingF2NativeAccuracyPct}
  if arm.StrongestControlAccuracyPct!=best{t.Fatal("strongest comparator not preserved")}
 }
 if err:=F5ValidatePreview(first);err!=nil{t.Fatal("exact preview rejected",err)}
 raw,err:=json.Marshal(first);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_EUREKA_F5_TRAIN_ONLY=%s",raw)
}

func TestF5DisagreementPlannerChoosesMaximalPreOutcomeSplit(t *testing.T){
 generated,err:=F3Generate();if err!=nil{t.Fatal(err)}
 models:=[3]f3Executable{}
 for i,row:=range generated.Candidates{
  model,err:=f3New(row.ID);if err!=nil{t.Fatal(err)}
  models[i]=model
  if err:=f2teach([]f2Observer{model},f2training(17));err!=nil{t.Fatal(err)}
  if err:=model.Observe(f2make(17,1,0,0,0,50));err!=nil{t.Fatal(err)}
 }
 used:=[8]bool{true,false,false,false,false,false,false,false}
 context,preds,pairs,calls,err:=f5Select("disagreement",17,1,used,models)
 if err!=nil{t.Fatal(err)}
 expectedIndex,bestPairs:=-1,-1
 for ix:=1;ix<8;ix++{
  signs,err:=f5Read(models,ix/2,ix%2);if err!=nil{t.Fatal(err)}
  score:=f5Pairs(signs)
  if score>bestPairs{bestPairs=score;expectedIndex=ix}
 }
 if pairs<=0||pairs!=bestPairs||context.Cue*2+context.Mode!=expectedIndex||
  preds!=func()[3]int{p,_:=f5Read(models,context.Cue,context.Mode);return p}()||
  calls!=7*3+3{
  t.Fatalf("not selecting informative unseen action context: %v %v %d %d",context,preds,pairs,calls)
 }
 unchanged,err:=f5Read(models,0,0)
 if err!=nil{t.Fatal(err)}
 if f5Pairs(unchanged)!=0{t.Fatal("all models should agree at directly observed context")}
}

func TestF5FeedbackIsConsequenceDependentAndRejectsInversionForgery(t *testing.T){
 p:=[3]int{1,-1,1}
 good,bad:=[3]int{},[3]int{}
 if err:=f5ScoreFeedback(&good,p,0,1);err!=nil{t.Fatal(err)}
 if err:=f5ScoreFeedback(&bad,p,0,-1);err!=nil{t.Fatal(err)}
 if good!=[3]int{1,-1,1}||bad!=[3]int{-1,1,-1}{
  t.Fatal("feedback inversion did not reverse hypothesis evidence")
 }
 parity:=[3]int{}
 if err:=f5ScoreFeedback(&parity,p,1,-1);err!=nil{t.Fatal(err)}
 if parity!=good{t.Fatal("chosen action not normalized to action-0 predictions")}
 for _,testCase:=range []struct{prediction [3]int;action,effect int}{
  {p,2,1},{p,0,0},{[3]int{1,0,1},0,1},
 }{
  state:=[3]int{}
  if err:=f5ScoreFeedback(&state,testCase.prediction,testCase.action,testCase.effect);err==nil{
   t.Fatal("invalid action, effect or prediction allowed")
  }
  if state!=[3]int{} {t.Fatal("rejected feedback partially modified evidence scores")}
 }
}

func TestF5TournamentFailsClosedOnHoldoutBudgetTamperingAndAuthClaims(t *testing.T){
 first,err:=F5Development();if err!=nil{t.Fatal(err)}
 clone:=func()F5Report{
  raw,err:=json.Marshal(first);if err!=nil{t.Fatal(err)}
  var out F5Report
  if err:=json.Unmarshal(raw,&out);err!=nil{t.Fatal(err)}
  return out
 }
 changes:=[]struct{name string;change func(*F5Report)}{
  {"fake parent source",func(x *F5Report){x.F4GeneratedSourceSHA256="forged"}},
  {"heldout seed",func(x *F5Report){x.TrainingSeeds[1]=59}},
  {"holdout consumed",func(x *F5Report){x.IndependentHoldoutConsumed=true}},
  {"source invention claimed",func(x *F5Report){x.NewMechanismGenerated=true}},
  {"scientific claim",func(x *F5Report){x.ScientificAccepted=true}},
  {"RSI claim",func(x *F5Report){x.GeneralRSIProven=true}},
  {"owner activation",func(x *F5Report){x.OwnerActivation=true}},
  {"dispatch",func(x *F5Report){x.DispatchAuthorized=true}},
  {"paid model",func(x *F5Report){x.PaidAPICalls=1;x.AgentCalls=1}},
  {"missing negative arm",func(x *F5Report){x.Arms=x.Arms[:5]}},
  {"reused step",func(x *F5Report){x.Arms[0].Probes[1]=x.Arms[0].Probes[0]}},
  {"budget increase",func(x *F5Report){x.Arms[0].ProbeObservations=7}},
  {"forged outcome",func(x *F5Report){x.Arms[0].Probes[0].ObservedEffect*= -1}},
  {"forged winner",func(x *F5Report){x.Arms[0].SelectedCandidateID="unknown"}},
  {"evidence score fraud",func(x *F5Report){x.Arms[0].Candidates[0].EvidenceScore++}},
  {"conventional control suppression",func(x *F5Report){x.Arms[0].StrongestControlAccuracyPct=0}},
  {"source identity fraud",func(x *F5Report){x.Arms[0].Candidates[0].StructuralSourceSHA256="bad"}},
 }
 for _,tc:=range changes{t.Run(tc.name,func(t *testing.T){
  altered:=clone();tc.change(&altered)
  if err:=F5ValidatePreview(altered);err==nil{t.Fatal("tampered intervention evidence accepted")}
 })}
 parent,err:=F4Development();if err!=nil{t.Fatal(err)}
 if _,err:=f5Run("disagreement",59,parent);err==nil{t.Fatal("published F3 heldout seed accepted")}
 if _,err:=f5Run("unrecognized",17,parent);err==nil{t.Fatal("unfrozen planner accepted")}
 generated,err:=F3Generate();if err!=nil{t.Fatal(err)}
 models:=[3]f3Executable{}
 for i,row:=range generated.Candidates{
  models[i],err=f3New(row.ID);if err!=nil{t.Fatal(err)}
 }
 all:=[8]bool{true,true,true,true,true,true,true,true}
 if _,_,_,_,err:=f5Select("disagreement",17,0,all,models);err==nil{
  t.Fatal("probe budget exhaustion not rejected")
 }
 if _,_,_,_,err:=f5Select("disagreement",17,6,[8]bool{},models);err==nil{
  t.Fatal("extra seventh probe accepted")
 }
}
