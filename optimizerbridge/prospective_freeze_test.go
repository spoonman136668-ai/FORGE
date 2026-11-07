package optimizerbridge
import ("strings";"testing")
func TestProspectiveFrozenAndNonauthorizing(t *testing.T){
 plan:=PriorityPlan{Schema:"forge.optimizer.priority-plan.v1",Phase:"DREAM_PARETO_FROZEN_CONTROL_PROSPECTIVE_PREREGISTRATION",Lane:"Wingless",DreamPolicySHA256:strings.Repeat("a",64),FrozenControlsRequired:true,ProspectiveRandomizationRequired:true,IndependentOutcomeReviewRequired:true}
 p:=ProspectiveFreeze{Schema:"forge.optimizer.prospective-freeze.v1",Lane:"Wingless",SourceCommitSHA:strings.Repeat("b",40),DreamPolicySHA256:strings.Repeat("a",64),FrozenControlSHA256:strings.Repeat("c",64),ParetoPoolSHA256:strings.Repeat("d",64),EligibilityAndExclusionSHA256:strings.Repeat("e",64),OutcomeMetricSHA256:strings.Repeat("f",64),RandomizationProtocolSHA256:strings.Repeat("1",64),ComputeBudget:100,ExperimentCount:4,HoldoutSealed:true}
 rec,err:=FreezeProspective(plan,p)
 if err!=nil||rec.DispatchAuthorized||rec.ScientificImprovementEstablished||rec.OriginalsExecuted!=0||len(rec.PreregisteredSHA256)!=64{t.Fatal(rec,err)}
 p.ExperimentCount=5
 altered,err:=FreezeProspective(plan,p);if err!=nil||altered.PreregisteredSHA256==rec.PreregisteredSHA256{t.Fatal("freeze failed to bind count",err)}
 tests:=[]struct{name string;change func(*ProspectiveFreeze)}{
 {"unsealed",func(p *ProspectiveFreeze){p.HoldoutSealed=false}},
 {"wrong_lane",func(p *ProspectiveFreeze){p.Lane="Yggdrasil"}},
 {"unknown_metric",func(p *ProspectiveFreeze){p.OutcomeMetricSHA256=""}},
 {"zero_budget",func(p *ProspectiveFreeze){p.ComputeBudget=0}},
 {"single_original",func(p *ProspectiveFreeze){p.ExperimentCount=1}},
 {"no_randomization",func(p *ProspectiveFreeze){p.RandomizationProtocolSHA256=""}},
 {"policy_drift",func(p *ProspectiveFreeze){p.DreamPolicySHA256=strings.Repeat("f",64)}},
 }
 for _,tc:=range tests {t.Run(tc.name,func(t *testing.T){
  x:=p;tc.change(&x);z,err:=FreezeProspective(plan,x)
  if err==nil||z!=(ProspectiveRecord{}){t.Fatal("admitted bad freeze")}
 })}
}
