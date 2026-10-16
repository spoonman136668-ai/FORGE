package optimizerbridge

import (
 "errors"
 "strings"
 "testing"
)

func f60SyntheticShadowForTest(t *testing.T)(F58Freeze,[]LanePins,ExportReview){
 t.Helper()
 f,err:=FreezeF58()
 if err!=nil{t.Fatal(err)}
 pins:=[]LanePins{
  {Lane:"Wingless",ParetoPolicySHA256:strings.Repeat("a",64),DreamTrainSHA256:strings.Repeat("b",64),DreamValidationSHA256:strings.Repeat("c",64)},
  {Lane:"Yggdrasil",ParetoPolicySHA256:strings.Repeat("d",64),DreamTrainSHA256:strings.Repeat("e",64),DreamValidationSHA256:strings.Repeat("f",64)},
 }
 result:=ExportReview{
  Schema:"forge.optimizer.cloud-export-review.v1",
  Mode:"EXTERNAL_EXPORT_AND_SIGNED_ASSIGNMENT_CLAIMS_SHADOW_ONLY",
  ManifestSHA256:strings.Repeat("7",64),
  SourceDigestAndCustodySignatureVerified:true,
 }
 for i,p:=range pins{
  result.Shadow.Lanes=append(result.Shadow.Lanes,LaneResult{
   Lane:p.Lane,
   DreamPolicySHA256:strings.Repeat([]string{"1","2"}[i],64),
   DreamTrainingSHA256:p.DreamTrainSHA256,
   DreamValidationSHA256:p.DreamValidationSHA256,
   DreamProspectiveComparisonEligible:true,
   CapabilityModes:map[string]string{
    "dream_rsi":"SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN",
    "shinka_pareto":"HISTORICAL_DIVERSITY_ADVISORY",
   },
  })
  result.SelectionAudits=append(result.SelectionAudits,SelectionAuditReview{
   Lane:p.Lane,SignedClaimsConsistent:true,EntriesCrossChecked:128,
  })
 }
 return f,pins,result
}
func TestF60SourceConsistentShadowNeverEarnsProspectiveAuthority(t *testing.T){
 f,pins,r:=f60SyntheticShadowForTest(t)
 got,err:=previewF60Review(f,pins,r)
 if err!=nil{t.Fatal(err)}
 if len(got.Lanes)!=2||got.FrozenControlRegistrySHA256==""||
  !got.PinnedSourceAndSignerClaimConsistent||
  got.IndependentlyProvenRandomizedResearchSelections!=0||
  got.ProspectivelyQualifiedOwnerPolicies!=0||
  got.AcceptedScientificOriginals!=0||
  got.DreamParetoLiveActivationAuthorized||
  got.ThetaEvolveWeightUpdatesAuthorized||
  got.ControllerCutoverOrScientificDispatchAuthorized{
  t.Fatalf("historical evidence falsely promoted: %+v",got)
 }
 for _,lane:=range got.Lanes {
  if len(lane.FrozenBaselinePolicySHA256)!=4||lane.SignedAssignmentClaimCount!=128||
   lane.OwnerApprovedProspectiveChallengers||
   lane.ActualPredecisionRandomizationProven||
   lane.FirstNewProspectiveSelectionExecuted||
   lane.IndependentlyAcceptedResearchOutcome{
   t.Fatalf("signed claims treated as real science %+v",lane)
  }
 }
 if actual,err:=ObserveF60FromSignedExport(f,SignedExport{},ExternalTrust{},
  [2][]byte{},pins,[2]SignedSelectionAudit{},[2]SelectionAuditPin{});
  !errors.Is(err,ErrF60)||actual!=(F60ShadowCandidateObservation{}) {
  t.Fatalf("missing source credentials accepted %+v %v",actual,err)
 }
}
func TestF60SpoofedSignedHistoricalInputsRejected(t *testing.T){
 f,pins,original:=f60SyntheticShadowForTest(t)
 cases:=map[string]func(*ExportReview,*[]LanePins){
  "missing_signed_export":func(r *ExportReview,p *[]LanePins){r.SourceDigestAndCustodySignatureVerified=false},
  "not_verified_mode":func(r *ExportReview,p *[]LanePins){r.Mode="synthetic-ok"},
  "signed_only_not_history":func(r *ExportReview,p *[]LanePins){r.SelectionAudits[0].SignedClaimsConsistent=false},
  "fake_independent_random":func(r *ExportReview,p *[]LanePins){r.SelectionAudits[1].ActualRandomizationIndependentlyDemonstrated=true},
  "fake_improvement":func(r *ExportReview,p *[]LanePins){r.Shadow.ScientificImprovementEstablished=true},
  "fake_first_use":func(r *ExportReview,p *[]LanePins){r.Shadow.FirstUseConsumed=true},
  "wrong_dream_history":func(r *ExportReview,p *[]LanePins){r.Shadow.Lanes[0].DreamTrainingSHA256=strings.Repeat("9",64)},
  "duplicate_train_validation":func(r *ExportReview,p *[]LanePins){(*p)[0].DreamValidationSHA256=(*p)[0].DreamTrainSHA256;r.Shadow.Lanes[0].DreamValidationSHA256=(*p)[0].DreamTrainSHA256},
  "crosslane_train_reuse":func(r *ExportReview,p *[]LanePins){(*p)[1].DreamTrainSHA256=(*p)[0].DreamTrainSHA256;r.Shadow.Lanes[1].DreamTrainingSHA256=(*p)[0].DreamTrainSHA256},
  "crosslane_pareto_reuse":func(r *ExportReview,p *[]LanePins){(*p)[1].ParetoPolicySHA256=(*p)[0].ParetoPolicySHA256},
  "wrong_claim_count":func(r *ExportReview,p *[]LanePins){r.SelectionAudits[1].EntriesCrossChecked=0},
  "historical_gain_not_eligible":func(r *ExportReview,p *[]LanePins){r.Shadow.Lanes[0].DreamProspectiveComparisonEligible=false},
  "other_lane_name":func(r *ExportReview,p *[]LanePins){r.Shadow.Lanes[1].Lane="Wingless"},
  "missing_pareto":func(r *ExportReview,p *[]LanePins){(*p)[0].ParetoPolicySHA256=""},
 }
 for name,change:=range cases{
  t.Run(name,func(t *testing.T){
   // Produce a new bounded, TEST-ONLY structure each time.
   _,p,r:=f60SyntheticShadowForTest(t)
   change(&r,&p)
   out,err:=previewF60Review(f,p,r)
   if !errors.Is(err,ErrF60)||out!=(F60ShadowCandidateObservation{}){
    t.Fatalf("admitted forged source claims: %+v %v",out,err)
   }
  })
 }
 _=pins;_=original
}
