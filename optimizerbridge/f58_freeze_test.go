package optimizerbridge

import (
 "errors"
 "encoding/json"
 "reflect"
 "strings"
 "testing"
)

func TestF58ConcreteBaselineIdentityAndProspectiveSourceFreeze(t *testing.T){
 f,err:=FreezeF58()
 if err!=nil{t.Fatal(err)}
 if err:=ValidateF58(f);err!=nil{t.Fatal(err)}
 if len(f.Lanes)!=2||f.Lanes[0].Lane!="Wingless"||f.Lanes[1].Lane!="Yggdrasil"{t.Fatal("not both frozen lanes")}
 seen:=map[string]bool{}
 for _,lane:=range f.Lanes{
  for _,control:=range lane.Controls{
   if control.SHA256!=control.Policy.ID()||seen[control.SHA256]{t.Fatalf("invalid or reused policy ID %+v",control)}
   seen[control.SHA256]=true
  }
  for _,candidate:=range lane.Challengers{
   if candidate.ExternallyAcceptedPolicySHA256!=""||candidate.IndependentCustodianReceiptSHA256!=""{
    t.Fatal("synthetic challenger identity promoted")
   }
  }
 }
 if len(seen)!=8{t.Fatal("not all eight unique real control policy identities")}
 data,_:=json.Marshal(f)
 var rec F58Freeze
 if err:=json.Unmarshal(data,&rec);err!=nil{t.Fatal(err)}
 if err:=ValidateF58(rec);err!=nil{t.Fatalf("serialized immutable policy changed: %v",err)}
 r,err:=ReadinessF58(rec)
 if err!=nil{t.Fatal(err)}
 if r.FrozenControlPolicies!=8||r.ReservedProspectiveChallengers!=4||
  len(r.FrozenControlRegistrySHA256)!=64||
  !strings.Contains(r.Status,"NOT_YET_RECEIVED")||
  r.OwnerPublishedChallengerPolicies||
  r.IndependentFirstUseAndRandomizationQualified||
  r.FutureProspectiveCausalOutcomesQualified||
  r.DreamParetoPromotionAuthorized||r.ThetaWeightPromotionAuthorized||
  r.SelectionTrialExecutionAuthorized{t.Fatalf("unqualified promotion: %+v",r)}
 f2,err:=FreezeF58()
 if err!=nil||!reflect.DeepEqual(f,f2){t.Fatal("nondeterministic control policy freeze")}
}
func TestF58AdversarialProspectiveIdentityMutationsFailClosed(t *testing.T){
 fresh:=func()F58Freeze {f,err:=FreezeF58();if err!=nil{t.Fatal(err)};return f}
 cases:=map[string]func(*F58Freeze){
  "change_parent_commit":func(f *F58Freeze){f.ParentSourceCommit=strings.Repeat("a",40)},
  "change_dream_source":func(f *F58Freeze){f.Lanes[0].Challengers[0].ImplementationGitBlob=strings.Repeat("a",40)},
  "change_pareto_source":func(f *F58Freeze){f.Lanes[1].Challengers[1].ImplementationGitBlob=strings.Repeat("b",40)},
  "supply_untrusted_dream_identity":func(f *F58Freeze){f.Lanes[0].Challengers[0].ExternallyAcceptedPolicySHA256=strings.Repeat("f",64)},
  "supply_self_attested_custodian":func(f *F58Freeze){f.Lanes[0].Challengers[0].IndependentCustodianReceiptSHA256=strings.Repeat("a",64)},
  "weaken_confirmatory_sample":func(f *F58Freeze){f.ConfirmatoryMinIndependentSelectionsPerLane=12},
  "lower_ess":func(f *F58Freeze){f.ConfirmatoryMinEffectiveSampleSizePerPolicy=1},
  "remove_baseline":func(f *F58Freeze){f.Lanes[0].Controls=f.Lanes[0].Controls[:3]},
  "mutate_control_weights":func(f *F58Freeze){f.Lanes[0].Controls[0].Policy.Weights[0]++},
  "reuse_control_identity":func(f *F58Freeze){f.Lanes[1].Controls[2].SHA256=f.Lanes[1].Controls[1].SHA256},
  "soften_fair_budget":func(f *F58Freeze){f.BudgetMatchedCandidatesAndCompute=false},
  "permit_post_outcome_freeze":func(f *F58Freeze){f.FrozenBeforeFutureOutcomes=false},
  "change_logging_rule":func(f *F58Freeze){f.RandomizationRule="deterministic_auto_evidence"},
  "promote_trial":func(f *F58Freeze){f.ControllerOrFirstUseDispatchAuthorized=true},
  "promote_scientific_gain":func(f *F58Freeze){f.DreamParetoProspectiveGainEstablished=true},
  "promote_theta":func(f *F58Freeze){f.ThetaEvolveWeightUpdateAuthorized=true},
  "drop_lane":func(f *F58Freeze){f.Lanes=f.Lanes[:1]},
 }
 for name,change:=range cases{
  t.Run(name,func(t *testing.T){
   f:=fresh();change(&f)
   if err:=ValidateF58(f);!errors.Is(err,ErrF58){t.Fatalf("unsafe F58 registration accepted %v",err)}
   if r,err:=ReadinessF58(f);!errors.Is(err,ErrF58)||r!= (F58Readiness{}){t.Fatalf("invalid readiness accepted %+v %v",r,err)}
  })
 }
}
