package nativediscovery

import (
 "bytes"
 "encoding/json"
 "reflect"
 "testing"
)

type f12Golden struct{
 seed uint32
 policy string
 g1Changed [5]int
 g2Changed [5]int
 g1Original [5]int
 g2Original [5]int
}
func f12IndependentGolden()[]f12Golden{
 // Independently calculated from frozen unsigned generator arithmetic and
 // 16-rule two-action posterior, NOT used by the F12 learner or to tune it.
 return []f12Golden{
  {17,"fixed",[5]int{64,64,20,12,20},[5]int{64,64,16,17,64},
   [5]int{64,64,64,19,64},[5]int{64,64,64,19,64}},
  {17,"random",[5]int{64,64,20,12,20},[5]int{64,64,16,17,8},
   [5]int{64,64,64,19,64},[5]int{64,64,64,19,46}},
  {31,"fixed",[5]int{64,64,21,10,0},[5]int{64,64,28,10,0},
   [5]int{64,64,64,22,0},[5]int{64,64,64,22,0}},
  {31,"random",[5]int{64,64,25,22,25},[5]int{64,64,33,22,0},
   [5]int{64,64,64,22,0},[5]int{64,64,64,22,0}},
 }
}

func TestF12IndependentGoldenDelayedCausalOutcomeAndStrongMLE(t *testing.T){
 v,err:=F12Development()
 if err!=nil{t.Fatal(err)}
 if err:=F12Validate(v);err!=nil{t.Fatal("F12 source-bound report changed",err)}
 expected:=f12IndependentGolden()
 if len(v.Arms)!=4||len(expected)!=4||
  v.Schema!=F12Schema||v.Seeds!=[2]uint32{17,31}||
  v.Policies!=[2]string{"fixed","random"}||
  v.DelaySteps!=2||v.TrainingActions!=48||v.ProbeActions!=6||
  v.PriorOdds!=3||v.CandidateRuleCount!=16||
  v.HiddenStateCount!=4||v.ScoredDecisionsPerModel!=64||
  v.MinimumStrongGain!=4||v.MinimumAblationGain!=8||
  !v.DevelopmentOnly||!v.F10AndF11NegativePreserved||
  v.IndependentScienceSeedsConsumed||v.ScientificAccepted||
  v.FullProcessEfficiencyProven||v.OwnerEligible||v.DispatchAuthorized||
  v.LiveFORGEResearchChanged||v.AgentCalls!=0||v.PaidAPICalls!=0||
  v.DigestSHA256!=f12Digest(v){
  t.Fatal("F12 source, frozen thresholds, hypothesis or authority changed")
 }
 if v.Classification!=F12NO_GO||v.PassingArms!=0{
  t.Fatalf("F12 source should honestly preserve NO_GO: class=%s passing=%d",v.Classification,v.PassingArms)
 }
 checks:=0
 for i,w:=range expected{
  arm:=v.Arms[i]
  if arm.Seed!=w.seed||arm.Policy!=w.policy||
   !arm.OriginalWorldRetained||arm.MeetsFrozenThreshold||
   len(arm.Actions)!=F12Actions||
   arm.HistorySHA256!=f8Digest("FORGE-EUREKA-F12-EVENTS-V1\n",arm.Actions){
   t.Fatalf("F12 omitted an arm or failed an original-world/custody control index=%d",i)
  }
  for j,round:=range arm.Rounds{
   expectedChanged,expectedOriginal:=w.g1Changed,w.g1Original
   if j==1{expectedChanged,expectedOriginal=w.g2Changed,w.g2Original}
   if round.Generation!=j+1||round.ActionCount!=51+3*j||
    round.CreditedDelayedConsequences!=49+3*j||
    round.UnresolvedPendingActions!=2||
    !round.ColdStateMatches||round.ChangedCorrect!=expectedChanged||
    round.OriginalCorrect!=expectedOriginal||
    round.CausalCorrect!=64||round.MLECorrect!=64||
    round.StrongestCorrect!=64||round.AdvantageOverStrongest!=0||
    round.NoActionCorrect!=expectedChanged[3]||
    round.WrongLagCorrect!=expectedChanged[4]||
    round.TableCorrect!=expectedChanged[2]||
    round.AdvantageOverNoAction!=64-expectedChanged[3]||
    round.AdvantageOverWrongLag!=64-expectedChanged[4]||
    round.PredictionRuleChecks!=8320{
    t.Fatalf("F12_GOLDEN_RESULT_DRIFT seed=%d policy=%s generation=%d round=%+v expectedChanged=%v expectedOriginal=%v",
     w.seed,w.policy,j+1,round,expectedChanged,expectedOriginal)
   }
   for _,d:=range round.SnapshotSHA256{
    if len(d)!=64{t.Fatal("missing cold-source checkpoint SHA")}
   }
   checks+=round.PredictionRuleChecks
  }
  t.Logf("F12_INDEPENDENT_GOLDEN seed=%d policy=%s G1=%v G2=%v original_G2=%v causal_vs_MLE=%+d/64 causal_vs_no_action=%+d/64 causal_vs_wrong_lag=%+d/64",
   w.seed,w.policy,w.g1Changed,w.g2Changed,w.g2Original,
   arm.Rounds[1].AdvantageOverStrongest,arm.Rounds[1].AdvantageOverNoAction,
   arm.Rounds[1].AdvantageOverWrongLag)
 }
 if v.TotalRuleChecks!=checks||checks!=66560{
  t.Fatalf("F12 frozen prediction-work proxy changed %d",checks)
 }
 t.Log("F12_INDEPENDENT_GOLDEN_VERDICT=F12_DEV_NO_GO; CAUSAL_DYNAMIC_PREDICTION=64/64; STRONG_MLE=64/64; SCIENTIFIC_ACCEPTED=FALSE; OWNER_INACTIVE=TRUE")
}

func TestF12DelayedActionConsequenceNoFutureLabelsOrWorldRuleLeak(t *testing.T){
 for _,seed:=range f12Seeds(){
  rule,err:=f12TrueRule(seed)
  if err!=nil{t.Fatal(err)}
  for _,policy:=range f12Policies(){
   events,err:=f12Generate(seed,policy)
   if err!=nil||len(events)!=54{t.Fatal("bounded synthetic world generator invalid",err)}
   state:=int(f12Mix(seed^0x125ecafe)&3)
   initial:=state
   after:=[F12Actions]int{}
   for tIdx,e:=range events{
    if e.Step!=tIdx||e.Phase!=tIdx/F12LearnActions||
     e.Sensor!=state&1||e.Action<0||e.Action>1||
     e.Cue<0||e.Cue>=4{returnEarlyF12(t,"unbounded world observation")}
    action,err:=f12Action(seed,policy,tIdx)
    if err!=nil||e.Action!=action{t.Fatal("action schedule changed AFTER world outcome")}
    delay:= -1
    if tIdx==1{delay=initial}
    if tIdx>=2{delay=after[tIdx-F12Delay]}
    if e.DelayedState!=delay{t.Fatal("future hidden consequence leaked before two actions")}
    if tIdx>=F12LearnActions&&e.Phase!=1{t.Fatal("world didn't undergo phase change")}
    toggled:=f12Next(rule,state,e.Phase,e.Cue,1-e.Action)
    observed:=f12Next(rule,state,e.Phase,e.Cue,e.Action)
    if observed==toggled{t.Fatal("changing intervention action did not change hidden causal consequence")}
    state=observed
    after[tIdx]=state
   }
   m,_:=f12New("causal")
   for j,e:=range events{
    if err:=m.Observe(e);err!=nil{t.Fatal(err)}
    expected:=max(0,j+1-F12Delay)
    if m.Credited!=expected{t.Fatalf("F12_DELAYED_CREDIT_LEAK step=%d got=%d want=%d",j,m.Credited,expected)}
    if j==50&&expected!=49||j==53&&expected!=52{t.Fatal("false future label at G1/G2 cut")}
   }
  }
 }
 for _,seed:=range []uint32{59,83,0,18}{
  if _,err:=f12Generate(seed,"fixed");err==nil{t.Fatal("protected heldout/unknown development seed admitted")}
 }
 for _,bad:=range []string{"", "uncertainty", "oracle", "full-sweep"}{
  if _,err:=f12Generate(17,bad);err==nil{t.Fatal("unapproved action planner admitted")}
 }
}

func TestF12CumulativeColdResumeWithTwoOutstandingEffects(t *testing.T){
 for _,seed:=range f12Seeds(){
  for _,policy:=range f12Policies(){
   events,err:=f12Generate(seed,policy);if err!=nil{t.Fatal(err)}
   for _,kind:=range f12Kinds(){
    g1,err:=f12New(kind);if err!=nil{t.Fatal(err)}
    for _,e:=range events[:51]{if err:=g1.Observe(e);err!=nil{t.Fatal(err)}}
    if g1.Seen!=51||g1.Credited!=49||
     g1.Pending[0].Step!=49||g1.Pending[1].Step!=50{
     t.Fatal("G1 hidden transition credit or pending causal IDs missing")
    }
    snap,err:=g1.Snapshot();if err!=nil{t.Fatal(err)}
    digest:=f3Hash(snap)
    cold,err:=f12Load(snap,digest)
    if err!=nil||!reflect.DeepEqual(g1,cold){t.Fatal("G1 cold snapshot state lost",err)}
    for _,e:=range events[51:54]{
     if err:=cold.Observe(e);err!=nil{t.Fatal(err)}
    }
    if cold.Seen!=54||cold.Credited!=52||
     cold.Pending[0].Step!=52||cold.Pending[1].Step!=53{
     t.Fatal("G2 did not append only three new actions with two outputs pending")
    }
    full,_:=f12New(kind)
    for _,e:=range events{if err:=full.Observe(e);err!=nil{t.Fatal(err)}}
    fromCold,err:=cold.Snapshot();if err!=nil{t.Fatal(err)}
    fromFresh,err:=full.Snapshot();if err!=nil{t.Fatal(err)}
    if !bytes.Equal(fromCold,fromFresh){
     t.Fatalf("G2 does not reconstruct identical actual learned state seed=%d policy=%s model=%s",
      seed,policy,kind)
    }
    for _,phase:=range []int{0,1}{
     p1,_,err:=f12Score(cold,seed,phase);if err!=nil{t.Fatal(err)}
     p2,_,err:=f12Score(full,seed,phase)
     if err!=nil||p1!=p2{t.Fatal("cold predictions changed after incremental continuation")}
    }
    if _,err:=f12Load(snap,"");err==nil{t.Fatal("missing externally expected snapshot SHA accepted")}
    if _,err:=f12Load(snap,f3Hash([]byte("stale historical source")));err==nil{
     t.Fatal("wrong external expected source accepted")
    }
    altered:=append([]byte{},snap...)
    altered[len(altered)-2]^=1
    if _,err:=f12Load(altered,f3Hash(altered));err==nil{
     t.Fatal("tampered/counterfeit-but-locally-rehashed learning state accepted")
    }
    // A replay of the old 48+3 events must fail the strict global step ID
    // rather than silently double-count previous learning.
    if err:=cold.Observe(events[0]);err==nil{t.Fatal("old observations reapplied after cold restoration")}
   }
  }
 }
}

func TestF12AllControlsSeeExactlySameDelayedEvidenceAndNoOracleFallback(t *testing.T){
 for _,seed:=range f12Seeds(){
  for _,policy:=range f12Policies(){
   events,_:=f12Generate(seed,policy)
   var models [5]*f12Memory
   for i,k:=range f12Kinds(){models[i],_=f12New(k)}
   for _,e:=range events[:51]{
    for _,m:=range models{if err:=m.Observe(e);err!=nil{t.Fatal(err)}}
   }
   for i:=1;i<5;i++{
    if models[i].Seen!=models[0].Seen||models[i].Credited!=models[0].Credited{
     t.Fatal("a matched conventional comparator received less causal information")
    }
   }
   // Evaluating candidate must NOT update learned counts with evaluation
   // state labels or world oracle; test before/after exact state bytes.
   pre,err:=models[0].Snapshot();if err!=nil{t.Fatal(err)}
   for _,phase:=range []int{0,1}{
    _,_,err:=f12Score(models[0],seed,phase);if err!=nil{t.Fatal(err)}
   }
   post,err:=models[0].Snapshot()
   if err!=nil||!bytes.Equal(pre,post){t.Fatal("future evaluation answers leaked into training")}
   if models[0].Match==[F12RuleCount]int{}{
    t.Fatal("causal learner did not update from delayed action consequences")
   }
  }
 }
}

func TestF12RejectsForgedExperimentScienceAndPredictionRecords(t *testing.T){
 orig,err:=F12Development();if err!=nil{t.Fatal(err)}
 clone:=func()F12Report{
  raw,err:=json.Marshal(orig);if err!=nil{t.Fatal(err)}
  var out F12Report
  if err:=json.Unmarshal(raw,&out);err!=nil{t.Fatal(err)}
  return out
 }
 cases:=[]struct{name string;change func(*F12Report)}{
  {"parent-negative",func(v *F12Report){v.ParentF11DigestSHA256="forged"}},
  {"missing-training-negative",func(v *F12Report){v.F10AndF11NegativePreserved=false}},
  {"schema",func(v *F12Report){v.Schema="counterfeit"}},
  {"seed",func(v *F12Report){v.Seeds[1]=59}},
  {"action-budget",func(v *F12Report){v.ProbeActions=100}},
  {"original-phase",func(v *F12Report){v.Arms[0].Rounds[1].OriginalCorrect[0]=0}},
  {"future credit",func(v *F12Report){v.Arms[0].Rounds[0].CreditedDelayedConsequences=51}},
  {"missing pending",func(v *F12Report){v.Arms[0].Rounds[1].UnresolvedPendingActions=0}},
  {"false improvement",func(v *F12Report){v.Arms[0].Rounds[1].CausalCorrect=100}},
  {"weakened conventional",func(v *F12Report){v.Arms[0].Rounds[1].MLECorrect=0}},
  {"missing fixed",func(v *F12Report){v.Arms=v.Arms[:3]}},
  {"discard one loser",func(v *F12Report){v.Arms=v.Arms[1:]}},
  {"reordered experiment",func(v *F12Report){v.Arms[0],v.Arms[1]=v.Arms[1],v.Arms[0]}},
  {"new future outcome",func(v *F12Report){v.Arms[0].Actions[53].DelayedState=3-v.Arms[0].Actions[53].DelayedState}},
  {"cold corruption",func(v *F12Report){v.Arms[0].Rounds[0].SnapshotSHA256[0]="forged"}},
  {"model family",func(v *F12Report){v.CandidateRuleCount=999}},
  {"threshold",func(v *F12Report){v.MinimumStrongGain=0}},
  {"first use",func(v *F12Report){v.IndependentScienceSeedsConsumed=true}},
  {"science",func(v *F12Report){v.ScientificAccepted=true}},
  {"performance claim",func(v *F12Report){v.FullProcessEfficiencyProven=true}},
  {"owner",func(v *F12Report){v.OwnerEligible=true}},
  {"dispatch",func(v *F12Report){v.DispatchAuthorized=true}},
  {"live forge",func(v *F12Report){v.LiveFORGEResearchChanged=true}},
  {"paid",func(v *F12Report){v.PaidAPICalls=1}},
  {"agent",func(v *F12Report){v.AgentCalls=1}},
  {"false signal",func(v *F12Report){v.Classification=F12Signal}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  v:=clone();tc.change(&v)
  v.DigestSHA256=f12Digest(v)
  if F12Validate(v)==nil{t.Fatal("self-hashed false causal benefit or unauthorized science/owner accepted")}
 })}
}

func returnEarlyF12(t *testing.T,reason string){t.Fatal(reason)}
