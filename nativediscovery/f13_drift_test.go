package nativediscovery

import (
 "bytes"
 "encoding/json"
 "reflect"
 "testing"
)

func TestF13UnannouncedDriftVersusEveryFullyTrainedControl(t *testing.T){
 report,err:=F13Development()
 if err!=nil{t.Fatal(err)}
 replay,err:=F13Development()
 if err!=nil||!reflect.DeepEqual(report,replay){t.Fatal("F13 deterministic training history drift",err)}
 if err:=F13Validate(report);err!=nil{t.Fatal("F13 source-bound review rejected",err)}
 prior,err:=F12Development()
 if err!=nil||F12Validate(prior)!=nil||prior.Classification!=F12NO_GO||
  report.F12SourceDigestSHA256!=prior.DigestSHA256{
  t.Fatal("original F12 negative evidence not retained")
 }
 if report.Schema!=F13Schema||len(report.Arms)!=4||
  report.Seeds!=[2]uint32{17,31}||report.Policies!=[2]string{"fixed","random"}||
  report.ChangeStep!=48||report.TotalActions!=60||report.Delay!=2||
  report.CandidateRules!=16||report.ScoredDecisions!=64||
  report.MinStrongGain!=4||report.MinAblationGain!=8||
  report.TotalRuleWorkChecks<=0||!report.EarlierNegativePreserved||
  !report.DevelopmentOnly||report.ScientificAccepted||
  report.IndependentHoldoutConsumed||report.FullProcessEfficiencyProven||
  report.OwnerEligible||report.DispatchAuthorized||
  report.LiveFORGEResearchChanged||report.AgentCalls!=0||report.PaidAPICalls!=0{
  t.Fatal("F13 source, control, budget or science fence drift")
 }
 passing,work:=0,0
 for i,arm:=range report.Arms{
  if arm.Seed!=report.Seeds[i/2]||arm.Policy!=report.Policies[i%2]||
   len(arm.TraceSHA256)!=64{returnEarlyF13(t,"missing/duplicate seed-policy arm")}
  trace,err:=f13Generate(arm.Seed,arm.Policy)
  if err!=nil||arm.TraceSHA256!=f8Digest("FORGE-EUREKA-F13-OBSERVATIONS-V1\n",trace){
   t.Fatal("causal transition history provenance mismatch")
  }
  for generation,round:=range arm.Rounds{
   count:=54+generation*6
   if round.Generation!=generation+1||round.ActionsSeen!=count||
    round.CreditedConsequences!=count-2||
    round.PendingConsequences!=2||!round.ColdStateMatches||
    len(round.SnapshotSHA256)!=64||round.RuleWorkChecks<=0{
    t.Fatal("F13 delayed credit/frozen budget/cold snapshot violated")
   }
   for _,score:=range append(round.OriginalCorrect[:],round.ChangedCorrect[:]...){
    if score<0||score>64{t.Fatal("an unbounded or noninteger evaluation result was accepted")}
   }
   strongest:=max(max(round.ChangedCorrect[1],round.ChangedCorrect[2]),
    max(round.ChangedCorrect[3],round.ChangedCorrect[4]))
   if round.StrongestMatchedCorrect!=strongest||
    round.AdvantageOverStrongest!=round.ChangedCorrect[0]-strongest||
    round.AdvantageOverNoAction!=round.ChangedCorrect[0]-round.ChangedCorrect[5]||
    round.AdvantageOverWrongLag!=round.ChangedCorrect[0]-round.ChangedCorrect[6]{
    t.Fatal("strongest conventional or negative control omitted")
   }
   // All seven mechanisms read the same exact cold source; none receive
   // post-cutoff training transitions or synthetic scorer answers.
   trained:=f13New()
   for _,e:=range trace[:count]{
    if err:=trained.Observe(e);err!=nil{t.Fatal(err)}
   }
   raw,err:=trained.Snapshot()
   if err!=nil||f3Hash(raw)!=round.SnapshotSHA256{t.Fatal("F13 source snapshot diverged",err)}
   before:=append([]byte(nil),raw...)
   for k,kind:=range f13Kinds(){
    got,_,err:=f13Score(kind,trained,arm.Seed,true)
    if err!=nil||got!=round.ChangedCorrect[k]{
     t.Fatalf("unmatched evaluation outcome seed=%d policy=%s model=%s",arm.Seed,arm.Policy,kind)
    }
    old,_,err:=f13Score(kind,trained,arm.Seed,false)
    if err!=nil||old!=round.OriginalCorrect[k]{
     t.Fatal("original-world retention comparison corrupted")
    }
   }
   after,err:=trained.Snapshot()
   if err!=nil||!bytes.Equal(before,after){t.Fatal("evaluation answers leaked into learned state")}
   work+=round.RuleWorkChecks
  }
  g2:=arm.Rounds[1]
  expectedRetention:=g2.OriginalCorrect[0]>=arm.Rounds[0].OriginalCorrect[0]
  meets:=expectedRetention&&g2.AdvantageOverStrongest>=4&&
   g2.AdvantageOverNoAction>=8&&g2.AdvantageOverWrongLag>=8
  if arm.RetainedOriginal!=expectedRetention||arm.PassesThreshold!=meets{
   t.Fatal("changed post-result threshold or hidden original retention loss")
  }
  if meets{passing++}
  t.Logf("F13_DEV seed=%d policy=%s G1_changed=%v G2_changed=%v "+
   "G1_original=%v G2_original=%v strongest=%d "+
   "adv_strong=%+d/64 adv_no_action=%+d/64 adv_wrong_lag=%+d/64 "+
   "surprise_g1=%t surprise_g2=%t retained=%t passing=%t",
   arm.Seed,arm.Policy,arm.Rounds[0].ChangedCorrect,g2.ChangedCorrect,
   arm.Rounds[0].OriginalCorrect,g2.OriginalCorrect,
   g2.StrongestMatchedCorrect,g2.AdvantageOverStrongest,
   g2.AdvantageOverNoAction,g2.AdvantageOverWrongLag,
   arm.Rounds[0].SurpriseAlarm,g2.SurpriseAlarm,arm.RetainedOriginal,arm.PassesThreshold)
 }
 if work!=report.TotalRuleWorkChecks||passing!=report.PassingArms{t.Fatal("cost or negative arms missing")}
 classification:=F13NO_GO
 if passing==4{classification=F13Signal}
 if report.Classification!=classification{t.Fatal("frozen classification relabeled after results")}
 t.Logf("F13_FROZEN_DEV=%s passing=%d/4 research_owner_eligible=false science_unverified=true",
  report.Classification,passing)
}

func TestF13TrueDelayedConsequencesAndHiddenUnannouncedSwitch(t *testing.T){
 for _,seed:=range f13Seeds(){
  oldRule,newRule,err:=f13Rules(seed)
  if err!=nil||oldRule==newRule{t.Fatal("causal shift didn't change")}
  for _,policy:=range f13Policies(){
   trace,err:=f13Generate(seed,policy)
   if err!=nil||len(trace)!=60{t.Fatal("invalid action trace",err)}
   state:=int(f12Mix(seed^0x125ecafe)&3)
   initial:=state
   var after [F13Actions]int
   notebook:=f13New()
   for step,e:=range trace{
    if e.Step!=step||e.Phase!=0||e.Sensor!=state&1||
     e.Cue!=f12Cue(seed,step,0)||
     e.DelayedState< -1||e.DelayedState>3{
     t.Fatal("the unannounced world exposed a phase indicator or inconsistent sensor")
    }
    act,err:=f13Action(seed,policy,step)
    if err!=nil||act!=e.Action{t.Fatal("action chosen after hidden rule outcome")}
    expected:= -1
    if step==1{expected=initial}
    if step>=2{expected=after[step-2]}
    if e.DelayedState!=expected{t.Fatal("future state observed before two-step delay")}
    rule:=oldRule
    if step>=F13SwitchStep{rule=newRule}
    state=f12Next(rule,state,0,e.Cue,e.Action)
    after[step]=state
    if err:=notebook.Observe(e);err!=nil{t.Fatal(err)}
    if len(notebook.Credits)!=max(0,step+1-2){
     t.Fatal("future post-switch action effect counted prematurely")
    }
   }
   if notebook.Seen!=60||len(notebook.Credits)!=58||
    notebook.Pending[0].Step!=58||notebook.Pending[1].Step!=59{
    t.Fatal("F13 end-of-budget state or pending causal IDs lost")
   }
  }
 }
 for _,seed:=range []uint32{0,18,59,83}{
  if _,err:=f13Generate(seed,"fixed");err==nil{t.Fatal("independent first-use/unknown seed admitted")}
 }
 for _,policy:=range []string{"", "oracle", "disagreement", "unapproved"}{
  if _,err:=f13Generate(17,policy);err==nil{t.Fatal("unknown oracle-probe route admitted")}
 }
}

func TestF13ColdSixNewActionsAndRejectReplayedTraining(t *testing.T){
 for _,seed:=range f13Seeds(){
  for _,policy:=range f13Policies(){
   trace,err:=f13Generate(seed,policy)
   if err!=nil{t.Fatal(err)}
   g1:=f13New()
   for _,e:=range trace[:54]{if err:=g1.Observe(e);err!=nil{t.Fatal(err)}}
   if g1.Seen!=54||len(g1.Credits)!=52||
    g1.Pending[0].Step!=52||g1.Pending[1].Step!=53{
    t.Fatal("G1 checkpoint credited not-yet-revealed causal outcome")
   }
   state,err:=g1.Snapshot();if err!=nil{t.Fatal(err)}
   expectedSHA:=f3Hash(state)
   cold,err:=f13Load(state,expectedSHA)
   if err!=nil||!reflect.DeepEqual(cold,g1){t.Fatal("cold snapshot invalid",err)}
   for _,e:=range trace[54:]{if err:=cold.Observe(e);err!=nil{t.Fatal(err)}}
   all:=f13New()
   for _,e:=range trace{if err:=all.Observe(e);err!=nil{t.Fatal(err)}}
   a,err:=cold.Snapshot();if err!=nil{t.Fatal(err)}
   b,err:=all.Snapshot()
   if err!=nil||!bytes.Equal(a,b){t.Fatal("G1 to G2 cumulative state did not match full source replay")}
   if err:=cold.Observe(trace[0]);err==nil{t.Fatal("duplicated old training data accepted")}
   if _,err:=f13Load(state,"");err==nil{t.Fatal("missing external expected digest accepted")}
   if _,err:=f13Load(state,f3Hash([]byte("older valid checkpoint")));err==nil{
    t.Fatal("stale expected head accepted")
   }
   bad:=append([]byte{},state...)
   bad[len(bad)-4]^=1
   if _,err:=f13Load(bad,expectedSHA);err==nil{t.Fatal("state tampering accepted")}
   // A valid prefix truncation is not an authorized most-recent checkpoint.
   if _,err:=f13Load(state[:len(state)-15],expectedSHA);err==nil{
    t.Fatal("truncated checkpoint accepted")
   }
  }
 }
}
func TestF13DevelopmentEvidenceCannotForgeScienceOrOwner(t *testing.T){
 base,err:=F13Development();if err!=nil{t.Fatal(err)}
 clone:=func()F13Report{
  data,err:=json.Marshal(base);if err!=nil{t.Fatal(err)}
  var v F13Report
  if err:=json.Unmarshal(data,&v);err!=nil{t.Fatal(err)}
  return v
 }
 cases:=[]struct{name string;fn func(*F13Report)}{
  {"source",func(v *F13Report){v.F12SourceDigestSHA256="forged"}},
  {"prior no-go",func(v *F13Report){v.EarlierNegativePreserved=false}},
  {"schema",func(v *F13Report){v.Schema="forged"}},
  {"seed",func(v *F13Report){v.Seeds[1]=59}},
  {"budget",func(v *F13Report){v.TotalActions=600}},
  {"delay",func(v *F13Report){v.Delay=0}},
  {"strong threshold",func(v *F13Report){v.MinStrongGain=0}},
  {"ablation threshold",func(v *F13Report){v.MinAblationGain=0}},
  {"missing loser",func(v *F13Report){v.Arms=v.Arms[:3]}},
  {"reorder",func(v *F13Report){v.Arms[0],v.Arms[1]=v.Arms[1],v.Arms[0]}},
  {"pending",func(v *F13Report){v.Arms[0].Rounds[0].PendingConsequences=0}},
  {"future outcome",func(v *F13Report){v.Arms[0].Rounds[1].CreditedConsequences=60}},
  {"fake score",func(v *F13Report){v.Arms[0].Rounds[1].ChangedCorrect[0]=64}},
  {"false science",func(v *F13Report){v.ScientificAccepted=true}},
  {"heldout",func(v *F13Report){v.IndependentHoldoutConsumed=true}},
  {"efficiency",func(v *F13Report){v.FullProcessEfficiencyProven=true}},
  {"owner",func(v *F13Report){v.OwnerEligible=true}},
  {"dispatch",func(v *F13Report){v.DispatchAuthorized=true}},
  {"live research",func(v *F13Report){v.LiveFORGEResearchChanged=true}},
  {"agent",func(v *F13Report){v.AgentCalls=1}},
  {"paid",func(v *F13Report){v.PaidAPICalls=1}},
  {"false signal",func(v *F13Report){v.Classification=F13Signal}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   v:=clone();tc.fn(&v);v.DigestSHA256=f13Digest(v)
   if F13Validate(v)==nil{t.Fatal("self-hashed fake result or unauthorized science accepted")}
  })
 }
}
func returnEarlyF13(t *testing.T,s string){t.Fatal(s)}

// Independently reconstructed from the frozen F12 hidden-state transition law,
// deterministic action stream, and F13's prespecified 16-rule competitors.
// The table is a verification witness, NOT an input to learner selection.
func TestF13IndependentFourArmGolden(t *testing.T){
 out,err:=F13Development()
 if err!=nil||F13Validate(out)!=nil{t.Fatal("F13 source report invalid",err)}
 type row struct{
  seed uint32
  policy string
  originalG1 [7]int
  changedG1 [7]int
  originalG2 [7]int
  changedG2 [7]int
  alarmG1,alarmG2 bool
  retainsOriginal bool
 }
 expected:=[]row{
  {17,"fixed",
   [7]int{64,64,64,64,64,20,20},
   [7]int{20,20,20,20,20,64,64},
   [7]int{64,64,20,20,58,20,20},
   [7]int{20,20,64,64,25,64,64},
   false,false,true},
  {17,"random",
   [7]int{64,64,64,64,64,20,8},
   [7]int{20,20,20,20,20,64,19},
   [7]int{20,64,20,20,50,20,20},
   [7]int{64,20,64,64,28,64,64},
   false,true,false},
  {31,"fixed",
   [7]int{12,64,12,12,64,21,21},
   [7]int{64,12,64,64,12,10,10},
   [7]int{12,64,12,12,64,9,64},
   [7]int{64,12,64,64,12,22,12},
   true,true,true},
  {31,"random",
   [7]int{12,64,12,12,64,9,0},
   [7]int{64,12,64,64,12,22,20},
   [7]int{12,64,12,12,64,9,10},
   [7]int{64,12,64,64,12,22,21},
   true,true,true},
 }
 if len(out.Arms)!=len(expected){t.Fatal("F13 dropped an unfavorable arm")}
 for i,w:=range expected{
  a:=out.Arms[i];g1,g2:=a.Rounds[0],a.Rounds[1]
  if a.Seed!=w.seed||a.Policy!=w.policy||
   g1.OriginalCorrect!=w.originalG1||
   g1.ChangedCorrect!=w.changedG1||
   g2.OriginalCorrect!=w.originalG2||
   g2.ChangedCorrect!=w.changedG2||
   g1.SurpriseAlarm!=w.alarmG1||
   g2.SurpriseAlarm!=w.alarmG2||
   a.RetainedOriginal!=w.retainsOriginal||
   a.PassesThreshold{
   t.Fatalf("F13_FROZEN_GOLDEN_DRIFT seed=%d policy=%s got=%+v expected=%+v",a.Seed,a.Policy,a,w)
  }
  t.Logf("F13_INDEPENDENT_GOLDEN seed=%d policy=%s changedG1=%v changedG2=%v originalG1=%v originalG2=%v surprise=%t/%t",
   a.Seed,a.Policy,g1.ChangedCorrect,g2.ChangedCorrect,g1.OriginalCorrect,
   g2.OriginalCorrect,g1.SurpriseAlarm,g2.SurpriseAlarm)
 }
 if out.Classification!=F13NO_GO||out.PassingArms!=0||
  out.ScientificAccepted||out.OwnerEligible||out.DispatchAuthorized||
  !out.EarlierNegativePreserved{
  t.Fatalf("F13 false scientific gain or owner authority class=%s passing=%d",
   out.Classification,out.PassingArms)
 }
 t.Log("F13_INDEPENDENT_GOLDEN_VERDICT=F13_DEV_NO_GO; strongest_rolling_MLE_not_beaten; scientific_accepted=false")
}
