package optimizerstages

import (
 "errors"
 "math"
 "testing"
)

func TestF92QuantifiesF91UnderpoweredSmallEffects(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 cases:=[]struct{target,wantN int;feasible bool}{
  {5,166128,false},
  {10,41532,false},
  {20,10383,true},
 }
 for _,tc:=range cases{
  t.Run("strict_margin_"+string(rune('A'+tc.target)),func(t *testing.T){
   p,err:=PlanF92Precision(w,y,tc.target,16384)
   if err!=nil{t.Fatal(err)}
   if p.MinimumObservationsForStrictHalfWidth!=tc.wantN||
    p.MathematicalPrecisionFeasibleWithinPlan!=tc.feasible||
    p.RequiresLargerQualifiedReaderOrPreregisteredEstimator==tc.feasible||
    p.ConditionalHalfWidthAtReaderMaximum<15.9||
    p.ConditionalHalfWidthAtReaderMaximum>16.0||
    p.FrozenComparisonCount!=16||p.FamilywiseAlpha!=0.05{
    t.Fatalf("incorrect precision feasibility %+v",p)
   }
   if err:=ValidateF92FrozenPlan(w,y,p);err!=nil{t.Fatal(err)}
   if f91ConditionalRadius(tc.wantN)>=float64(tc.target){
    t.Fatalf("computed minimum is not strict target %d",tc.target)
   }
   if f91ConditionalRadius(tc.wantN-1)<float64(tc.target){
    t.Fatalf("smaller N already meets target %d",tc.target)
   }
  })
 }
}
func TestF92DefaultHasNoAuthorityAndStableSourceIdentity(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 p,err:=PlanF92Precision(w,y,5,16384)
 if err!=nil{t.Fatal(err)}
 again,err:=PlanF92Precision(w,y,5,16384)
 if err!=nil||again!=p{t.Fatalf("plan not deterministic %v",err)}
 if !exactHex(p.PlanSHA256,64)||p.Status!=F92Status||
  p.CompleteIndependentOriginalsObserved||
  p.IndependentlyVerifiedPreOutcomeWitness||
  p.AuthenticatedRandomizationAndOwnerFirstUse||
  p.ScientificImprovementClaimed||
  p.DreamRSIOrParetoActivationAuthorized||
  p.ThetaEvolveAcceptedTrainingAllowed||
  p.ScientificDispatchAuthorized||p.CloudflareWriteAuthorized{
  t.Fatalf("source-only plan claimed science %+v",p)
 }
}
func TestF92MalformedOrReusedPredecisionDesignRejected(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 cases:=map[string]func(*FrozenSixPolicyTrial){
  "same owner source":func(q *FrozenSixPolicyTrial){q.OwnerSourceSHA=w.OwnerSourceSHA},
  "same prereg":func(q *FrozenSixPolicyTrial){q.PreregistrationSHA256=w.PreregistrationSHA256},
  "same candidate slate":func(q *FrozenSixPolicyTrial){q.CandidateSlateSHA256=w.CandidateSlateSHA256},
  "same source family":func(q *FrozenSixPolicyTrial){q.SourceFamilySHA256=w.SourceFamilySHA256},
  "invalid frozen control":func(q *FrozenSixPolicyTrial){q.Controls[0]=q.DreamPolicySHA256},
  "no owner source":func(q *FrozenSixPolicyTrial){q.OwnerSourceSHA=""},
 }
 for name,fn:=range cases{
  t.Run(name,func(t *testing.T){
   altered:=y;fn(&altered)
   if _,err:=PlanF92Precision(w,altered,20,16384);!errors.Is(err,ErrF92){
    t.Fatalf("unfrozen same-owner design entered: %v",err)
   }
  })
 }
 if _,err:=PlanF92Precision(y,w,20,16384);!errors.Is(err,ErrF92){t.Fatal("swapped lanes allowed")}
 for _,args:=range [][2]int{{0,16384},{101,16384},{5,0},{5,5},{5,16385},{5,-1},{-1,16384}}{
  if _,err:=PlanF92Precision(w,y,args[0],args[1]);!errors.Is(err,ErrF92){
   t.Fatalf("invalid design params %+v passed %v",args,err)
  }
 }
}
func TestF92ConditionalPrecisionCannotBeRetroactivelyRewritten(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 original,err:=PlanF92Precision(w,y,20,16384)
 if err!=nil{t.Fatal(err)}
 tests:=map[string]func(*F92PrecisionPlan){
  "threshold changed":func(p *F92PrecisionPlan){p.DesiredHalfWidthScorePoints=5},
  "sample cap changed":func(p *F92PrecisionPlan){p.PlannedMaximumObservationsPerLane=14000},
  "score range changed":func(p *F92PrecisionPlan){p.ScoreScaleMaximum=10},
  "familywise alpha inflated":func(p *F92PrecisionPlan){p.FamilywiseAlpha=0.5},
  "control comparisons dropped":func(p *F92PrecisionPlan){p.FrozenComparisonCount=1},
  "lowered sample requirement":func(p *F92PrecisionPlan){p.MinimumObservationsForStrictHalfWidth=200},
  "fake feasibility":func(p *F92PrecisionPlan){p.MathematicalPrecisionFeasibleWithinPlan=false},
  "fake original":func(p *F92PrecisionPlan){p.CompleteIndependentOriginalsObserved=true},
  "fake witness":func(p *F92PrecisionPlan){p.IndependentlyVerifiedPreOutcomeWitness=true},
  "fake score gain":func(p *F92PrecisionPlan){p.ScientificImprovementClaimed=true},
  "fake dream activation":func(p *F92PrecisionPlan){p.DreamRSIOrParetoActivationAuthorized=true},
  "fake theta":func(p *F92PrecisionPlan){p.ThetaEvolveAcceptedTrainingAllowed=true},
  "fake execution":func(p *F92PrecisionPlan){p.ScientificDispatchAuthorized=true},
  "fake cloudflare":func(p *F92PrecisionPlan){p.CloudflareWriteAuthorized=true},
 }
 for name,fn:=range tests{
  t.Run(name,func(t *testing.T){
   p:=original;fn(&p)
   if err:=ValidateF92FrozenPlan(w,y,p);!errors.Is(err,ErrF92){
    t.Fatalf("tampered preregistered design passed: %v",err)
   }
   // Re-hashing a fabricated output must not make it authoritative.
   p.PlanSHA256=f92PlanHash(p)
   if err:=ValidateF92FrozenPlan(w,y,p);!errors.Is(err,ErrF92){
    t.Fatalf("rehash laundered tampered design %s",name)
   }
  })
 }
 // A corrupted digest must fail. Recomputing the unchanged content's
 // correct digest is not a forgery and must continue to verify.
 wrongDigest:=original
 wrongDigest.PlanSHA256="0"
 if err:=ValidateF92FrozenPlan(w,y,wrongDigest);!errors.Is(err,ErrF92){
  t.Fatal("corrupted digest admitted")
 }
 wrongDigest.PlanSHA256=f92PlanHash(wrongDigest)
 if err:=ValidateF92FrozenPlan(w,y,wrongDigest);err!=nil{
  t.Fatalf("unchanged plan with its actual digest was rejected: %v",err)
 }
 changed:=y;changed.Epoch=2
 if err:=ValidateF92FrozenPlan(w,changed,original);!errors.Is(err,ErrF92){t.Fatal("source epoch drift allowed")}
}
func TestF92PowerDoesNotFollowFromSmallConditionalRadius(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 smallBudget,err:=PlanF92Precision(w,y,20,6)
 if err!=nil{t.Fatal(err)}
 if smallBudget.MathematicalPrecisionFeasibleWithinPlan||
  smallBudget.ConditionalHalfWidthAtPlannedMaximum<300{
  t.Fatalf("tiny design incorrectly qualified %+v",smallBudget)
 }
 if math.IsNaN(f91ConditionalRadius(16384))||math.IsInf(f91ConditionalRadius(16384),0){
  t.Fatal("precision NaN or infinity")
 }
}
