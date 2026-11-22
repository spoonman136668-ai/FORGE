package nativediscovery

import (
 "encoding/json"
 "go/parser"
 "go/token"
 "reflect"
 "testing"
)

func TestF6RealSourceFromInterventionFeedbackAndMatchedNegativeEvidence(t *testing.T){
 report,err:=F6Development()
 if err!=nil{t.Fatal(err)}
 again,err:=F6Development()
 if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(report,again){t.Fatal("generation changed on exact replay")}
 parent,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 if report.Schema!=F6Schema||report.F5Schema!=F5Schema||
  report.F5ParentGeneratedSourceSHA256!=parent.F4GeneratedSourceSHA256||
  report.NativeGeneratorFrozenSHA256!=parent.NativeGeneratorFrozenSHA256||
  report.SyntheticTrainingHistorySHA256!=parent.SyntheticTrainingHistorySHA256||
  report.TrainingSeeds!=[2]uint32{17,31}||
  report.Policies!=f5Policies()||report.Families!=f6Families()||
  len(report.Arms)!=6||report.TotalGeneratedSourcePrograms!=24||
  !report.DevelopmentOnly||!report.GeneratedGoSourceNotCompiled||
  report.IndependentHoldoutConsumed||report.ScientificAccepted||
  report.GeneralRSIProven||report.OwnerActivation||
  report.DispatchAuthorized||report.AgentCalls!=0||report.PaidAPICalls!=0{
  t.Fatalf("generated source, budget, or inactive authority drift: %+v",report)
 }
 generated,err:=F3Generate()
 if err!=nil{t.Fatal(err)}
 originals:=map[string]bool{}
 for _,c:=range generated.Candidates{originals[c.StructuralSourceSHA256]=true}
 for i,arm:=range report.Arms{
  old:=parent.Arms[i]
  if arm.Seed!=old.Seed||arm.ParentF5Policy!=old.Policy||
   arm.ParentF5SourceSHA256!=parent.F4GeneratedSourceSHA256||
   arm.FeedbackSHA256!=f6FeedbackSHA(old,parent)||
   arm.TrainingObservations!=F2TrainCount||
   arm.FeedbackObservations!=F5ProbeBudget||
   arm.DevScoredDecisionsPerCandidate!=F2EvaluationCount||
   len(arm.Candidates)!=F6Families||
   arm.PriorF5SelectedDevChangedWorldAccuracyPct!=old.SelectedAccuracyPct||
   arm.StrongestConventionalDevAccuracyPct!=old.StrongestControlAccuracyPct{
   t.Fatal("F5 evidence or matched comparator dropped")
  }
  best:=0
  seen:=map[string]bool{}
  for j,c:=range arm.Candidates{
   if c.Family!=report.Families[j]||c.TrainingTotal!=F5ProbeBudget||
    c.TrainingCorrect<0||c.TrainingCorrect>F5ProbeBudget||
    c.Phase!=1&&c.Phase!= -1||c.DevChangedWorldAccuracyPct<0||
    c.DevChangedWorldAccuracyPct>100||
    len(c.SourceSHA256)!=64||seen[c.SourceSHA256]||originals[c.SourceSHA256]||
    c.SourceSHA256!=f3Hash([]byte(c.GeneratedGoSource)){
    t.Fatalf("candidate source/custody invalid %+v",c)
   }
   seen[c.SourceSHA256]=true
   source,err:=f6Source(c.Family,c.Phase)
   if err!=nil||source!=c.GeneratedGoSource{
    t.Fatal("source not exactly from frozen structural grammar")
   }
   if _,err:=parser.ParseFile(token.NewFileSet(),"f6_generated.go",source,parser.AllErrors);err!=nil{
    t.Fatal("candidate Go source failed to parse",err)
   }
   positive,negative:=0,0
   for _,p:=range old.Probes{
    sign,err:=f6Pattern(c.Family,p.Cue,p.Mode)
    if err!=nil{t.Fatal(err)}
    normalized:=p.ObservedEffect
    if p.Action==1{normalized= -normalized}
    if sign==normalized{positive++}else{negative++}
   }
   wantPhase,wantCorrect:=1,positive
   if negative>positive{wantPhase,wantCorrect= -1,negative}
   if c.Phase!=wantPhase||c.TrainingCorrect!=wantCorrect{
    t.Fatal("candidate generator used non-training data or wrong feedback normalization")
   }
   if c.TrainingCorrect>arm.Candidates[best].TrainingCorrect{best=j}
  }
  winner:=arm.Candidates[best]
  if arm.SelectedFamily!=winner.Family||
   arm.SelectedSourceSHA256!=winner.SourceSHA256||
   arm.SelectedTrainingCorrect!=winner.TrainingCorrect||
   arm.SelectedDevChangedWorldAccuracyPct!=winner.DevChangedWorldAccuracyPct||
   arm.GainOverF5PP!=winner.DevChangedWorldAccuracyPct-old.SelectedAccuracyPct||
   arm.GainOverStrongestControlPP!=winner.DevChangedWorldAccuracyPct-old.StrongestControlAccuracyPct{
   t.Fatal("selection illegally used dev score or lost comparison")
  }
  if arm.GainOverStrongestControlPP<=0&&arm.DevelopmentClassification!="F6_DEV_NO_GO"||
   arm.GainOverStrongestControlPP>0&&arm.DevelopmentClassification!="F6_DEV_DIAGNOSTIC_AHEAD_UNVERIFIED"{
   t.Fatal("negative control defeat relabeled as benefit")
  }
  t.Logf("F6_DEV_METRIC seed=%d policy=%s selected=%s source_sha=%s train_fit=%d/%d f6_accuracy=%.3f f5_accuracy=%.3f strongest_control=%.3f gain_vs_strongest_pp=%.3f status=%s",arm.Seed,arm.ParentF5Policy,arm.SelectedFamily,arm.SelectedSourceSHA256,arm.SelectedTrainingCorrect,F5ProbeBudget,arm.SelectedDevChangedWorldAccuracyPct,arm.PriorF5SelectedDevChangedWorldAccuracyPct,arm.StrongestConventionalDevAccuracyPct,arm.GainOverStrongestControlPP,arm.DevelopmentClassification)
 }
 if err:=F6ValidatePreview(report);err!=nil{t.Fatal("exact source validation failure",err)}
}

func TestF6CounterfactualFeedbackChangesGeneratedProgramNotJustAWeight(t *testing.T){
 parent,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 // Inject only hypothetical TRAIN feedback into the pure proposal function;
 // this is a mutation control, not a new world or consumed science evidence.
 positive:=append([]F5Probe(nil),parent.Arms[0].Probes...)
 for i:=range positive{
  positive[i].ObservedEffect=1
  if positive[i].Action==1{positive[i].ObservedEffect= -1}
 }
 before,err:=f6Propose(positive)
 if err!=nil{t.Fatal(err)}
 opposite:=append([]F5Probe(nil),positive...)
 for i:=range opposite{opposite[i].ObservedEffect*= -1}
 after,err:=f6Propose(opposite)
 if err!=nil{t.Fatal(err)}
 if len(before)!=F6Families||len(after)!=F6Families{t.Fatal("missing generation family")}
 if before[0].Family!="constant"||before[0].Phase!=1||
  after[0].Family!="constant"||after[0].Phase!= -1||
  before[0].SourceSHA256==after[0].SourceSHA256||
  before[0].TrainingCorrect!=6||after[0].TrainingCorrect!=6{
  t.Fatal("opposite consequence feedback failed to generate opposite winning source")
 }
 for i:=range before{
  if before[i].TrainingCorrect!=after[i].TrainingCorrect{
   t.Fatal("effect inversion must preserve maximal train fit")
  }
  if before[i].TrainingCorrect>3&&(
   before[i].SourceSHA256==after[i].SourceSHA256||
   before[i].GeneratedGoSource==after[i].GeneratedGoSource||
   before[i].Phase==after[i].Phase){
   t.Fatalf("non-tied feedback did not produce changed source: %s",before[i].Family)
  }
 }
 // A changed *evaluation* score alone is not permitted to change selection.
 altered:=parent.Arms[0]
 altered.SelectedAccuracyPct=0
 altered.StrongestControlAccuracyPct=0
 a,err:=f6BuildArm(parent.Arms[0],parent)
 if err!=nil{t.Fatal(err)}
 z,err:=f6BuildArm(altered,parent)
 if err!=nil{t.Fatal(err)}
 if a.SelectedSourceSHA256!=z.SelectedSourceSHA256||
  a.SelectedFamily!=z.SelectedFamily||
  a.SelectedTrainingCorrect!=z.SelectedTrainingCorrect{
  t.Fatal("diagnostic score was leaked into candidate generation")
 }
}

func TestF6TypedCandidateMatchesAllEmittedFallbackFormulaeAndColdState(t *testing.T){
 for _,family:=range f6Families(){
  for _,phase:=range []int{1,-1}{
   source,err:=f6Source(family,phase)
   if err!=nil||len(source)<100{t.Fatal("new source missing",err)}
   m:=&f6Repair{Family:family,Phase:phase}
   for regime:=0;regime<2;regime++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
    predicted:=m.Predict(f2Context{Regime:regime,Cue:cue,Mode:mode})
    pattern,err:=f6Pattern(family,cue,mode)
    if err!=nil||predicted!=phase*pattern{t.Fatal("emitted fallback and typed readout disagree")}
   }}}
   for _,seed:=range []uint32{17,31}{
    if err:=f2teach([]f2Observer{m},f2training(seed));err!=nil{t.Fatal(err)}
    if err:=m.Observe(f2make(seed,1,0,0,0,50));err!=nil{t.Fatal(err)}
    raw,err:=m.Snapshot();if err!=nil{t.Fatal(err)}
    cold:=&f6Repair{Family:family,Phase:phase}
    if err:=cold.Load(raw);err!=nil{t.Fatal(err)}
    for regime:=0;regime<2;regime++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
     ctx:=f2Context{Regime:regime,Cue:cue,Mode:mode}
     if m.Predict(ctx)!=cold.Predict(ctx){t.Fatal("cold state lost original learning")}
    }}}
   }
  }
 }
 for _,invalid:=range []struct{family string;phase int}{
  {"novel-unapproved-family",1},{"constant",0},{"constant",2},
 }{
  if _,err:=f6Source(invalid.family,invalid.phase);err==nil{
   t.Fatal("unknown/unbounded source mutation accepted")
  }
 }
}

func TestF6RejectsForgedFeedbackAndUnqualifiedPromotions(t *testing.T){
 p,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 base:=p.Arms[0].Probes
 cases:=[]struct{name string;modify func([]F5Probe)}{
  {"duplicate coordinate",func(v []F5Probe){v[1].Cue=v[0].Cue;v[1].Mode=v[0].Mode}},
  {"invalid action",func(v []F5Probe){v[0].Action=2}},
  {"action schedule",func(v []F5Probe){v[0].Action=1}},
  {"invalid effect",func(v []F5Probe){v[0].ObservedEffect=0}},
  {"altered step",func(v []F5Probe){v[0].Step=1}},
  {"false divergence",func(v []F5Probe){v[0].DivergentPairs++}},
  {"invalid prediction",func(v []F5Probe){v[0].PreObservationPredictions[0]=0}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  bad:=append([]F5Probe(nil),base...)
  tc.modify(bad)
  if _,err:=f6Propose(bad);err==nil{t.Fatal("malformed training feedback accepted")}
 })}
 if _,err:=f6Propose(base[:5]);err==nil{t.Fatal("incomplete feedback accepted")}
 bad:=p.Arms[0];bad.Seed=59
 if _,err:=f6BuildArm(bad,p);err==nil{t.Fatal("reused F3 heldout seed accepted")}
 bad=p.Arms[0];bad.Policy="agent"
 if _,err:=f6BuildArm(bad,p);err==nil{t.Fatal("unfrozen policy accepted")}
 report,err:=F6Development()
 if err!=nil{t.Fatal(err)}
 clone:=func()F6Report{
  raw,err:=json.Marshal(report);if err!=nil{t.Fatal(err)}
  var out F6Report
  if err:=json.Unmarshal(raw,&out);err!=nil{t.Fatal(err)}
  return out
 }
 modifications:=[]struct{name string;apply func(*F6Report)}{
  {"fake F5 parent SHA",func(x *F6Report){x.F5ParentGeneratedSourceSHA256="forged"}},
  {"heldout seed",func(x *F6Report){x.TrainingSeeds[1]=59}},
  {"relabel generated compile",func(x *F6Report){x.GeneratedGoSourceNotCompiled=false}},
  {"science firstuse",func(x *F6Report){x.IndependentHoldoutConsumed=true}},
  {"science claim",func(x *F6Report){x.ScientificAccepted=true}},
  {"RSI claim",func(x *F6Report){x.GeneralRSIProven=true}},
  {"owner active",func(x *F6Report){x.OwnerActivation=true}},
  {"dispatch enabled",func(x *F6Report){x.DispatchAuthorized=true}},
  {"paid/agent",func(x *F6Report){x.PaidAPICalls=1;x.AgentCalls=1}},
  {"fake source",func(x *F6Report){x.Arms[0].Candidates[0].GeneratedGoSource+="\n// forged"}},
  {"fake source SHA",func(x *F6Report){x.Arms[0].Candidates[0].SourceSHA256="forged"}},
  {"forged winner",func(x *F6Report){x.Arms[0].SelectedFamily="unknown"}},
  {"score laundering",func(x *F6Report){x.Arms[0].GainOverStrongestControlPP+=1}},
  {"negative suppression",func(x *F6Report){x.Arms[0].Candidates=x.Arms[0].Candidates[:3]}},
  {"missing F5 arm",func(x *F6Report){x.Arms=x.Arms[:5]}},
 }
 for _,tc:=range modifications{t.Run(tc.name,func(t *testing.T){
  changed:=clone();tc.apply(&changed)
  if err:=F6ValidatePreview(changed);err==nil{t.Fatal("forged preview accepted")}
 })}
}

func TestF6InterventionStructureChangesSelectedMechanismFamily(t *testing.T){
 parent,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 raw:=parent.Arms[0].Probes
 constant:=append([]F5Probe(nil),raw...)
 cueRule:=append([]F5Probe(nil),raw...)
 for i:=range constant{
  // Construct two equal-budget hypothetical TRAIN feedback histories, NOT
  // scored-world data; the source rule must respond to effect structure.
  constant[i].ObservedEffect=1
  if constant[i].Action==1{constant[i].ObservedEffect= -1}
  cueRule[i].ObservedEffect=1
  if cueRule[i].Cue%2==1{cueRule[i].ObservedEffect= -1}
  if cueRule[i].Action==1{cueRule[i].ObservedEffect= -cueRule[i].ObservedEffect}
 }
 a,err:=f6Propose(constant)
 if err!=nil{t.Fatal(err)}
 z,err:=f6Propose(cueRule)
 if err!=nil{t.Fatal(err)}
 choose:=func(candidates []F6GeneratedCandidate)F6GeneratedCandidate{
  best:=0
  for i:=1;i<len(candidates);i++{
   if candidates[i].TrainingCorrect>candidates[best].TrainingCorrect{best=i}
  }
  return candidates[best]
 }
 first,second:=choose(a),choose(z)
 if first.Family!="constant"||second.Family!="cue-parity"||
  first.TrainingCorrect!=F5ProbeBudget||second.TrainingCorrect!=F5ProbeBudget||
  first.SourceSHA256==second.SourceSHA256||
  first.GeneratedGoSource==second.GeneratedGoSource{
  t.Fatalf("changed causal feedback failed to generate a changed structural hypothesis: first=%+v second=%+v",first,second)
 }
}
