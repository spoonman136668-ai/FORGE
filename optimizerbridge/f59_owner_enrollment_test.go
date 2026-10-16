package optimizerbridge

import (
 "errors"
 "fmt"
 "strings"
 "testing"
)

func f59TestNomination(f F58Freeze,index int)F59PolicyNomination {
 n,_:=ReadinessF58(f)
 // Distinct 64-character test-only hashes across BOTH lanes.
 // They never represent independently accepted policies or receipts.
 digits:=make([]string,9)
 for i:=range digits {digits[i]=fmt.Sprintf("%064x",index*20+i+1)}
 source:="a"
 if index==1 {source="b"}
 return F59PolicyNomination{
  Lane:f.Lanes[index].Lane,
  FrozenControlRegistrySHA256:n.FrozenControlRegistrySHA256,
  DreamPolicySHA256:digits[0],
  DreamOptimizerLineageSHA256:digits[1],
  DreamTrainingHistorySHA256:digits[2],
  DreamValidationHistorySHA256:digits[3],
  ParetoPolicySHA256:digits[4],
  ParetoFrozenPortfolioSHA256:digits[5],
  ParetoLineageSHA256:digits[6],
  OwnerPreregistrationSHA256:digits[7],
  PredecisionOwnerSourceSHA:strings.Repeat(source,40),
  IndependentExternalTrustReceiptSHA256:digits[8],
 }
}
func TestF59EnrollmentIsNeverAutomaticScientificAdmission(t *testing.T){
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 for _,nominations:=range [][]F59PolicyNomination{
  nil,
  {f59TestNomination(f,0)},
  {f59TestNomination(f,0),f59TestNomination(f,1)},
 }{
  got,err:=PreviewEnrollment(f,nominations)
  if err!=nil{t.Fatal(err)}
  if got.FrozenControlPolicies!=8||
   got.SourceNominatedLanes!=len(nominations)||
   got.OwnerAuthenticatedLanes!=0||
   got.DistinctNewScientificFirstUseAssignments!=0||
   got.FirstProspectiveSelectionExecuted||
   got.DreamParetoPolicySelectionActivated||
   got.ThetaEvolvePromotionAuthorized||got.TrialDispatchAuthorized{
   t.Fatalf("SHA pointer became science authority %+v",got)
  }
 }
}
func TestF59RejectUntrustedEnrollmentAndCrossLaneReuse(t *testing.T){
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 changes:=map[string]func(*F59PolicyNomination,*F59PolicyNomination){
 "wrong_lane":func(w,y *F59PolicyNomination){w.Lane="FORGE"},
 "repeat_lane":func(w,y *F59PolicyNomination){y.Lane=w.Lane},
 "alternate_frozen_controls":func(w,y *F59PolicyNomination){w.FrozenControlRegistrySHA256=strings.Repeat("0",64)},
 "missing_owner_prereg":func(w,y *F59PolicyNomination){w.OwnerPreregistrationSHA256=""},
 "missing_real_custody":func(w,y *F59PolicyNomination){y.IndependentExternalTrustReceiptSHA256=""},
 "same_train_and_validation":func(w,y *F59PolicyNomination){w.DreamValidationHistorySHA256=w.DreamTrainingHistorySHA256},
 "same_challenger_policy":func(w,y *F59PolicyNomination){w.ParetoPolicySHA256=w.DreamPolicySHA256},
 "candidate_matches_frozen_control":func(w,y *F59PolicyNomination){w.DreamPolicySHA256=f.Lanes[0].Controls[0].SHA256},
 "crosslane_reused_source":func(w,y *F59PolicyNomination){y.PredecisionOwnerSourceSHA=w.PredecisionOwnerSourceSHA},
 "crosslane_reused_early_assignment":func(w,y *F59PolicyNomination){y.IndependentExternalTrustReceiptSHA256=w.IndependentExternalTrustReceiptSHA256},
 "misuse_frozen_parent":func(w,y *F59PolicyNomination){w.PredecisionOwnerSourceSHA=F58ParentSource},
 "no_pareto_portfolio_identity":func(w,y *F59PolicyNomination){w.ParetoFrozenPortfolioSHA256=""},
 "bad_dream_optimizer_lineage":func(w,y *F59PolicyNomination){w.DreamOptimizerLineageSHA256="x"},
 }
 for label,mutate:=range changes{
  t.Run(label,func(t *testing.T){
   w,y:=f59TestNomination(f,0),f59TestNomination(f,1)
   mutate(&w,&y)
   r,err:=PreviewEnrollment(f,[]F59PolicyNomination{w,y})
   if !errors.Is(err,ErrF59Enrollment)||r!=(F59EnrollmentReadiness{}){
    t.Fatalf("failed-open external nomination %+v %v",r,err)
   }
  })
 }
}
