package infogain

import (
 "reflect"
 "strings"
 "testing"
)

func observedHybridDevFinding()HybridFinding{
 return HybridFinding{
  Schema:HybridFindingSchema,
  // These are bounded, caller-transcribed development run identities, not
  // independent scientific custody or candidate-source birth.
  OriginalSourceSHA:"108808f7b685107a76fae1ce5605b7ff9e2bac27",
  ReserveSourceSHA:"3c91165dab7878e09c7c8646e245811c0a66adf5",
  OriginalRunID:42424890385,ReserveRunID:42425936640,
  CallerEvidenceSHA256:"30823b55e54821b518f5ede6ac8df73c54e3909cbe589b3bb0f198fdcdaa2706",
  MatchedWorlds:12,SignFlipWorlds:9,UpdatesPerWorld:32,
  OriginalPostSwitchUpdates:0,
  ReservePreSwitchUpdates:288,ReservePostSwitchUpdates:96,
  ReserveDetectorSelected:312,ReserveForcedUpdates:72,
  SignFlipForcedUpdates:72,SignFlipPostSwitchNonforcedSelected:0,
  RandomPostSwitchUpdates:156,PeriodicPostSwitchUpdates:144,
  SameObservationsAndCheckpoints:true,ScientificTrainingRun:false,
 }
}
func TestRealUntrainedDevelopmentEvidenceGeneratesFalsifiableProposal(t *testing.T){
 f:=observedHybridDevFinding();copyInput:=f
 got,err:=SuggestHybridFinding(f)
 if err!=nil||VerifyHybridFindingProposal(f,got)!=nil{t.Fatal("invalid native proposal",err)}
 if got.Diagnostic!="RESERVE_WORKS_CHANGE_DETECTOR_NOT_DEMONSTRATED"||
  got.ProposedExperiment!="freeze_calibrated_contradiction_trigger_vs_matched_controls"||
  got.UpdatesPerWorld!=32||got.PostSwitchDifferenceVersusRandom!=-60||
  len(got.Controls)!=5||!got.DevelopmentOnly||
  got.ScientificThresholdFrozen||got.NewOriginalSourceAuthenticated||
  got.OriginalEvidenceIndependentlyAuthenticated||got.ResearchExecuted||
  got.ScientificAccepted||got.DispatchAuthorized{
  t.Fatalf("wrong or overclaimed proposal: %+v",got)
 }
 cold,err:=SuggestHybridFinding(f)
 if err!=nil||!reflect.DeepEqual(cold,got)||!reflect.DeepEqual(copyInput,f){
  t.Fatal("replay drift or mutated original",err)
 }
}
func TestObservedProposalDeniedWithoutActualDetectorBlindSpot(t *testing.T){
 f:=observedHybridDevFinding()
 f.SignFlipPostSwitchNonforcedSelected=8
 got,err:=SuggestHybridFinding(f)
 if err!=nil||got.ProposedExperiment!=""||
  got.Diagnostic!="NO_TRIGGER_SPECIFIC_PROPOSAL_FROM_THESE_OBSERVATIONS"{
  t.Fatalf("invented blind spot: %v %+v",err,got)
 }
}
func TestDevelopmentInputFailsClosedOnMismatchedCountsAndDrift(t *testing.T){
 base:=observedHybridDevFinding()
 cases:=[]func(*HybridFinding){
  func(x *HybridFinding){x.OriginalSourceSHA=x.ReserveSourceSHA},
  func(x *HybridFinding){x.ReserveRunID=x.OriginalRunID},
  func(x *HybridFinding){x.CallerEvidenceSHA256="untrusted"},
  func(x *HybridFinding){x.ReserveForcedUpdates=73},
  func(x *HybridFinding){x.ReservePostSwitchUpdates=97},
  func(x *HybridFinding){x.SignFlipForcedUpdates=400},
  func(x *HybridFinding){x.SignFlipPostSwitchNonforcedSelected=97},
  func(x *HybridFinding){x.MatchedWorlds=0},
  func(x *HybridFinding){x.SameObservationsAndCheckpoints=false},
  func(x *HybridFinding){x.ScientificTrainingRun=true},
 }
 for i,fn:=range cases{
  f:=base;fn(&f)
  if _,err:=SuggestHybridFinding(f);err==nil{t.Fatalf("invalid observation %d admitted",i)}
 }
}
func TestCallerCannotPromoteProposalIntoAcceptedScienceOrDispatch(t *testing.T){
 f:=observedHybridDevFinding()
 good,err:=SuggestHybridFinding(f);if err!=nil{t.Fatal(err)}
 modifications:=[]func(*HybridFindingProposal){
  func(x *HybridFindingProposal){x.DispatchAuthorized=true},
  func(x *HybridFindingProposal){x.ScientificAccepted=true},
  func(x *HybridFindingProposal){x.ResearchExecuted=true},
  func(x *HybridFindingProposal){x.ScientificThresholdFrozen=true},
  func(x *HybridFindingProposal){x.NewOriginalSourceAuthenticated=true},
  func(x *HybridFindingProposal){x.OriginalEvidenceIndependentlyAuthenticated=true},
  func(x *HybridFindingProposal){x.PostSwitchDifferenceVersusRandom++},
  func(x *HybridFindingProposal){x.ReceiptSHA256=strings.Repeat("a",64)},
 }
 for i,fn:=range modifications{
  changed:=good;changed.Controls=append([]string(nil),good.Controls...);fn(&changed)
  if VerifyHybridFindingProposal(f,changed)==nil{t.Fatalf("forged promotion %d passed",i)}
 }
}
