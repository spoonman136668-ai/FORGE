package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"
)

func TestF11FrozenCausalPosteriorMatchedControlAndNegativeEvidence(t *testing.T){
 report,err:=F11Development()
 if err!=nil{t.Fatal(err)}
 replay,err:=F11Development()
 if err!=nil||!reflect.DeepEqual(report,replay){t.Fatal("F11 source replay is not deterministic",err)}
 if err:=F11Validate(report);err!=nil{t.Fatal("F11 source-bound report failed",err)}
 if report.Schema!=F11Schema||report.TrainingSeeds!=[2]uint32{17,31}||
  report.Policies!=[3]string{"uncertainty","fixed","random"}||
  report.HypothesisCount!=32||report.PosteriorOdds!=3||
  report.TotalArms!=6||report.TotalInterventions!=36||
  report.MinimumAdditionalCorrect!=4||
  report.DecisionsPerModelPerGeneration!=64||
  report.TotalPlannerPredictionCalls<=0||
  report.OriginalWorldRetainedArms!=6||len(report.Arms)!=6||
  !report.DevelopmentOnly||!report.F10NegativePreserved||
  !report.SameSyntheticTrainingOnly||!report.DifferentPlannerCoordinatesAllowed||
  report.IndependentFirstUseConsumed||report.WholeProcessCostMeasured||
  report.StrongestRealWorldBaselineQualified||report.ScientificAccepted||
  report.OwnerEligible||report.DispatchAuthorized||report.ExistingF139LaneAltered||
  report.ExperimentIssued||report.AgentCalls!=0||report.PaidAPICalls!=0||
  report.DigestSHA256!=f11Digest(report){
   t.Fatal("F11 budget, original NO_GO, scientific or owner authority drift")
 }
 prior,err:=F10Development()
 if err!=nil||prior.Classification!=F10ReviewNO_GO||
  report.ParentF10DigestSHA256!=prior.DigestSHA256{
  t.Fatal("F10 NO_GO source history displaced")
 }
 f5,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 totalCalls:=0
 for i,arm:=range report.Arms{
  if arm.Seed!=report.TrainingSeeds[i/3]||arm.Policy!=report.Policies[i%3]||
   arm.TrainObservations!=48||arm.ProbeObservations!=6||
   len(arm.Probes)!=6||arm.PlannerPredictionCalls<18||
   arm.FeedbackSHA256!=f7FeedbackHash(arm.Seed,arm.Policy,arm.Probes){
   t.Fatalf("F11 budget/feedback identity changed arm=%d",i)
  }
  totalCalls+=arm.PlannerPredictionCalls
  used:=[8]bool{}
  for j,probe:=range arm.Probes{
   coordinate:=probe.Cue*2+probe.Mode
   if probe.Step!=j||coordinate<0||coordinate>=8||used[coordinate]||
    probe.Action!=j%2||probe.ObservedEffect!=1&&probe.ObservedEffect!= -1||
    probe.DivergentPairs!=f5Pairs(probe.PreObservationPredictions){
    t.Fatal("F11 action-first unique-probe evidence invalid")
   }
   used[coordinate]=true
   // Exact frozen synthetic DEV observation, obtained only AFTER selection.
   original:=f2make(arm.Seed,1,probe.Cue,probe.Mode,j%2,50+j)
   if original.Effect!=probe.ObservedEffect{t.Fatal("observed action-consequence cannot be independently reproduced")}
  }
  if arm.Policy=="fixed"||arm.Policy=="random"{
   originalIndex:=i/3*3+1
   if arm.Policy=="random"{originalIndex++}
   reference:=f5.Arms[originalIndex]
   if reference.Seed!=arm.Seed||reference.Policy!=arm.Policy||
    !reflect.DeepEqual(arm.Probes,reference.Probes){
    t.Fatal("F11 ablation is NOT the already-frozen F5 fixed/random identical information trajectory")
   }
  }
  train:=f2training(arm.Seed)
  for generation,round:=range arm.Rounds{
   count:=(generation+1)*3
   if round.Generation!=generation+1||round.ObservedProbes!=count||
    round.StrongestMatchedCorrect<round.F3Correct||
    round.StrongestMatchedCorrect<round.TabularCorrect||
    round.StrongestMatchedCorrect<round.FactorizedCorrect||
    round.StrongestMatchedCorrect<round.NativeCorrect||
    round.AdvantageOverStrongest!=round.PosteriorCorrect-round.StrongestMatchedCorrect||
    round.PosteriorCorrect<0||round.PosteriorCorrect>64||
    round.OriginalWorldBefore!=round.OriginalWorldAfter||
    !round.OriginalWorldRetained||!round.ColdPredictionMatches||
    round.SnapshotSHA256==""||round.SnapshotBytes<10||round.SnapshotBytes>4096{
    t.Fatal("F11 matched baseline, original retention or cold snapshot invalid")
   }
   model:=&f11Posterior{}
   if err:=f2teach([]f2Observer{model},train);err!=nil{t.Fatal(err)}
   observed,err:=f7ObservedTransitions(arm.Probes[:count])
   if err!=nil{t.Fatal(err)}
   if err:=f2teach([]f2Observer{model},observed);err!=nil{t.Fatal(err)}
   success,err:=f11Score(model,arm.Seed,1)
   if err!=nil||success!=round.PosteriorCorrect{t.Fatal("retention source did not reproduce original exact feedback")}
   snapshot,err:=model.Snapshot()
   if err!=nil||f3Hash(snapshot)!=round.SnapshotSHA256||
    len(snapshot)!=round.SnapshotBytes{t.Fatal("F11 cold state source identity not retained")}
   cold:=&f11Posterior{}
   if cold.Load(snapshot)!=nil{t.Fatal("cold snapshot rejected")}
   for regime:=0;regime<2;regime++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
    ctx:=f2Context{Regime:regime,Cue:cue,Mode:mode}
    if model.Predict(ctx)!=cold.Predict(ctx){t.Fatal("F11 original/changed world cold predictions differ")}
   }}}
  }
  g2:=arm.Rounds[1]
  t.Logf("F11_TRAIN_DEV seed=%d policy=%s G1=%d/64 G2=%d/64 F3=%d tabular=%d factorized=%d native=%d strongest=%s:%d delta=%+d/64 probes=%d planner_calls=%d",
   arm.Seed,arm.Policy,arm.Rounds[0].PosteriorCorrect,g2.PosteriorCorrect,
   g2.F3Correct,g2.TabularCorrect,g2.FactorizedCorrect,g2.NativeCorrect,
   g2.StrongestMatchedName,g2.StrongestMatchedCorrect,g2.AdvantageOverStrongest,
   arm.ProbeObservations,arm.PlannerPredictionCalls)
 }
 if totalCalls!=report.TotalPlannerPredictionCalls{t.Fatal("planner compute proxy dropped")}
 for seedIdx:=0;seedIdx<2;seedIdx++{
  block:=report.Arms[seedIdx*3:seedIdx*3+3]
  diffStrong:=block[0].Rounds[1].PosteriorCorrect-block[0].Rounds[1].StrongestMatchedCorrect
  best:=max(block[1].Rounds[1].PosteriorCorrect,block[2].Rounds[1].PosteriorCorrect)
  diffAblation:=block[0].Rounds[1].PosteriorCorrect-best
  if report.UncertaintyVersusStrongest[seedIdx]!=diffStrong||
   report.UncertaintyVersusBestAblation[seedIdx]!=diffAblation{
   t.Fatal("false uncertainty planner benefit against stronger matched controls/ablations")
  }
 }
 expected:=F11ReviewNO_GO
 if report.UncertaintyWinningSeeds==2{expected=F11ReviewSignal}
 if report.Classification!=expected{t.Fatal("post-result revised F11 frozen benefit threshold")}
 t.Logf("F11_FROZEN_DEV_CLASSIFICATION=%s wins=%d/2 gain_over_strong=%v gain_over_best_ablation=%v F10_NO_GO_PRESERVED=TRUE SCIENCE_UNVERIFIED=TRUE",
  report.Classification,report.UncertaintyWinningSeeds,
  report.UncertaintyVersusStrongest,report.UncertaintyVersusBestAblation)
}

func TestF11CausalActionNormalizationAndEpistemicContradictions(t *testing.T){
 a,b,c:=&f11Posterior{},&f11Posterior{},&f11Posterior{}
 ctx:=f2Context{Regime:1,Cue:0,Mode:0}
 if err:=a.Observe(f2Transition{Context:ctx,Action:0,Effect:1});err!=nil{t.Fatal(err)}
 if err:=b.Observe(f2Transition{Context:ctx,Action:1,Effect:-1});err!=nil{t.Fatal(err)}
 if err:=c.Observe(f2Transition{Context:ctx,Action:0,Effect:-1});err!=nil{t.Fatal(err)}
 if a.Predict(ctx)!=1||b.Predict(ctx)!=1||c.Predict(ctx)!= -1{
  t.Fatal("intervention action normalization or causal counterexample ignored")
 }
 weightsA,err:=f11Weights(a.Counts)
 if err!=nil{t.Fatal(err)}
 pos,neg:=f11Vote(weightsA,0,0)
 if pos<=neg{t.Fatal("posterior did not update toward observed causal explanation")}
 weightsC,err:=f11Weights(c.Counts)
 if err!=nil{t.Fatal(err)}
 pos,neg=f11Vote(weightsC,0,0)
 if pos>=neg{t.Fatal("contradictory intervention did not reverse hypothesis evidence")}
 virgin:=&f11Posterior{}
 var f3 [3]f3Executable
 ids:=[]string{"prior-down","prior-hold","prior-up"}
 for i,id:=range ids{m,err:=f3New(id);if err!=nil{t.Fatal(err)};f3[i]=m}
 ctx1,_,_,err:=f11Choose(17,"uncertainty",0,[8]bool{},virgin,f3)
 if err!=nil||ctx1.Regime!=1{t.Fatal("posterior planner invalid before observing any effect")}
 ctx2,_,_,err:=f11Choose(17,"uncertainty",0,[8]bool{},virgin,f3)
 if err!=nil||ctx1!=ctx2{t.Fatal("uncertainty selection is nondeterministic")}
 if _,_,_,err:=f11Choose(59,"uncertainty",0,[8]bool{},virgin,f3);err==nil{
  t.Fatal("independent heldout seed 59 admitted")
 }
 for _,policy:=range []string{"", "disagreement", "unapproved"}{
  if _,_,_,err:=f11Choose(17,policy,0,[8]bool{},virgin,f3);err==nil{
   t.Fatal("unapproved policy admitted")
  }
 }
 for _,step:=range []int{-1,6,7}{
  if _,_,_,err:=f11Choose(17,"uncertainty",step,[8]bool{},virgin,f3);err==nil{
   t.Fatal("unbounded experiment action admitted")
  }
 }
 if _,err:=f11Arm(59,"uncertainty",F4Preview{});err==nil{t.Fatal("reserved independent science seed admitted")}
}

func TestF11HypothesisWeightsBoundedAndPriorCohortIsolation(t *testing.T){
 model:=&f11Posterior{}
 var first [F11Hypotheses]int
 first,err:=f11Weights(model.Counts)
 if err!=nil{t.Fatal(err)}
 for _,w:=range first{if w!=1{t.Fatal("nonuniform unfrozen hypothesis prior")}}
 for _,row:=range f2training(17){if err:=model.Observe(row);err!=nil{t.Fatal(err)}}
 afterTraining,err:=f11Weights(model.Counts)
 if err!=nil||afterTraining!=first{t.Fatal("regime-0 training leaked into newly changed world posterior")}
 ctx:=f2Context{Regime:1,Cue:1,Mode:1}
 for i:=0;i<6;i++{if err:=model.Observe(f2Transition{Context:ctx,Action:i%2,Effect:1-2*(i%2)});err!=nil{t.Fatal(err)}}
 weights,err:=f11Weights(model.Counts)
 if err!=nil{t.Fatal(err)}
 for _,w:=range weights{if w<1||w>729{t.Fatal("posterior exceeds frozen six-query cost budget")}}
 if err:=model.Observe(f2Transition{Context:ctx,Action:0,Effect:1});err!=nil{t.Fatal(err)}
 if _,err:=f11Weights(model.Counts);err==nil{
  t.Fatal("seventh intervention bypassed six-observation development fence")
 }
}

func TestF11RejectsForgedOutcomeHistoryBudgetAndAuthority(t *testing.T){
 orig,err:=F11Development();if err!=nil{t.Fatal(err)}
 clone:=func()F11Report{
  data,err:=json.Marshal(orig);if err!=nil{t.Fatal(err)}
  var copy F11Report;if err:=json.Unmarshal(data,&copy);err!=nil{t.Fatal(err)}
  return copy
 }
 cases:=[]struct{name string;mutate func(*F11Report)}{
  {"parent F10 no-go",func(x *F11Report){x.ParentF10DigestSHA256="forged"}},
  {"schema",func(x *F11Report){x.Schema="forged"}},
  {"posterior ratio",func(x *F11Report){x.PosteriorOdds=999}},
  {"hypothesis count",func(x *F11Report){x.HypothesisCount=999}},
  {"threshold",func(x *F11Report){x.MinimumAdditionalCorrect=0}},
  {"heldout",func(x *F11Report){x.TrainingSeeds[1]=59}},
  {"unknown policy",func(x *F11Report){x.Policies[1]="oracle"}},
  {"missing arm",func(x *F11Report){x.Arms=x.Arms[:5]}},
  {"omitted negative",func(x *F11Report){x.Arms=x.Arms[1:]}},
  {"fake score",func(x *F11Report){x.Arms[0].Rounds[1].PosteriorCorrect=64}},
  {"fake ablation",func(x *F11Report){x.Arms[1].Rounds[1].PosteriorCorrect=0}},
  {"future outcome",func(x *F11Report){x.Arms[0].Probes[5].ObservedEffect*= -1}},
  {"lost snapshot",func(x *F11Report){x.Arms[0].Rounds[0].SnapshotSHA256=""}},
  {"science",func(x *F11Report){x.ScientificAccepted=true}},
  {"owner",func(x *F11Report){x.OwnerEligible=true}},
  {"dispatch",func(x *F11Report){x.DispatchAuthorized=true}},
  {"first use",func(x *F11Report){x.IndependentFirstUseConsumed=true}},
  {"new F139 lane",func(x *F11Report){x.ExistingF139LaneAltered=true}},
  {"paid",func(x *F11Report){x.PaidAPICalls=1}},
  {"signal",func(x *F11Report){x.Classification=F11ReviewSignal}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  v:=clone();tc.mutate(&v);v.DigestSHA256=f11Digest(v)
  if err:=F11Validate(v);err==nil{t.Fatal("forged self-hashed scientific/owner/gain evidence passed")}
 })}
}
