package optimizerbridge
import ("reflect";"strings";"testing")
func TestFirstPhaseIsFrozenAdvisoryOnly(t *testing.T){
 r:=LaneResult{Lane:"Wingless",DreamPolicySHA256:strings.Repeat("a",64),
  DreamPoliciesEvaluated:3,BaselineFinalists:[]string{"baseline-1"},
  ParetoFinalists:[]string{"diverse-1","diverse-2"},
  CapabilityModes:map[string]string{"dream_rsi":"SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN",
   "shinka_pareto":"HISTORICAL_DIVERSITY_ADVISORY"}}
 p,err:=PlanFirstPhase(r)
 if err!=nil{t.Fatal(err)}
 if p.ExperimentDispatchAuthorized||p.ScientificImprovementEstablished||
  p.ThetaCanLearnFromAcceptedOutcomes||p.PromptAndGenenvCanProposeNovelty||
  !p.FrozenControlsRequired||!p.ProspectiveRandomizationRequired||
  !p.IndependentOutcomeReviewRequired{t.Fatalf("premature authority/promotion %+v",p)}
 r.BaselineFinalists[0]="mutated"
 if p.BaselineFinalists[0]=="mutated"{t.Fatal("mutable alias")}
}
func TestFirstPhaseRejectsWeakControls(t *testing.T){
 base:=LaneResult{Lane:"Yggdrasil",DreamPolicySHA256:strings.Repeat("f",64),
 DreamPoliciesEvaluated:1,BaselineFinalists:[]string{"b"},ParetoFinalists:[]string{"p"},
 CapabilityModes:map[string]string{"dream_rsi":"SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN",
 "shinka_pareto":"HISTORICAL_DIVERSITY_ADVISORY"}}
 cases:=[]struct{name string;mut func(*LaneResult)}{
 {"wrong_lane",func(r *LaneResult){r.Lane="Wingless/Yggdrasil"}},
 {"missing_baseline",func(r *LaneResult){r.BaselineFinalists=nil}},
 {"missing_diversity",func(r *LaneResult){r.ParetoFinalists=nil}},
 {"duplicate_finalists",func(r *LaneResult){r.ParetoFinalists=[]string{"p","p"}}},
 {"missing_policy",func(r *LaneResult){r.DreamPolicySHA256=""}},
 {"zero_policy_evaluations",func(r *LaneResult){r.DreamPoliciesEvaluated=0}},
 {"false_prospective_gain",func(r *LaneResult){r.CapabilityModes["dream_rsi"]="PROSPECTIVE_GAIN"}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  r:=base;r.CapabilityModes=map[string]string{"dream_rsi":base.CapabilityModes["dream_rsi"],"shinka_pareto":base.CapabilityModes["shinka_pareto"]}
  tc.mut(&r);p,err:=PlanFirstPhase(r)
  if err==nil||!reflect.DeepEqual(p,PriorityPlan{}){t.Fatal("unsafe promotion allowed",err)}
 })}
}
