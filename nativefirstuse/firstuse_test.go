package nativefirstuse

import (
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/workerlease"
)
func rep(c string,n int)string{return strings.Repeat(c,n)}
func fixture()Proposal{
 claim:=originalclaim.Claim{
  Schema:originalclaim.Schema,Lane:"Wingless",
  ExperimentID:"F74_NEW_SCIENTIFIC_PROSPECT",FrozenSHA256:rep("a",64),
  IntentSHA256:rep("b",64),SourceCommitSHA:rep("c",40),
  OriginalRunID:"FORGE_F74_FRESH",OwnerEpoch:7,WorkerID:"native-shadow-worker",
  FirstUseConsumed:true,
 }
 return Proposal{
  Claim:claim,OwnerID:"FORGE-native-current-owner",OwnerEpoch:7,AtUnix:1000,
  Lease:workerlease.Lease{Lane:claim.Lane,ExperimentID:claim.ExperimentID,
   IntentSHA256:claim.IntentSHA256,OwnerID:"FORGE-native-current-owner",
   OwnerEpoch:7,WorkerID:claim.WorkerID,LeaseSequence:12,
   ExpiresAtUnix:1010,FirstUseRisk:false},
  FrozenDecisionSHA256:rep("d",64),PolicySHA256:rep("e",64),
  BudgetSHA256:rep("f",64),
  ActionNumerator:1,ActionDenominator:6,
  Snapshots:[2]LaneSnapshot{
   {Lane:"Wingless",SourceCommitSHA:rep("1",40),LedgerSHA256:rep("2",64),
    OwnerEpoch:7,SequenceHighwater:40,ConsumedCount:29,ActiveCount:0,UncertainCount:3},
   {Lane:"Yggdrasil",SourceCommitSHA:rep("3",40),LedgerSHA256:rep("4",64),
    OwnerEpoch:7,SequenceHighwater:40,ConsumedCount:19,ActiveCount:1,UncertainCount:4},
  },
 }
}
func TestNativeSourceReusesOriginalClaimLeaseAndPreservesUncertainBothLanes(t *testing.T){
 p:=fixture()
 r,err:=Prepare(p)
 if err!=nil{t.Fatal(err)}
 if !r.SourceAndLeaseCorrespondenceVerified||!r.TwoLaneSnapshotShapeVerified||
  r.ExternallyAuthenticatedFullOriginalHistory||r.IndependentlyAcceptedCurrentOwner||
  r.PrivateRestorableBackupVerified||r.AtomicD1FirstUseConsumed||
  r.LiveWorkerPermitIssued||r.OriginalDispatched||r.OriginalReplayAuthorized||
  len(r.CandidateDigest)!=64||r.Lane!="Wingless"{t.Fatalf("unearned authority %+v",r)}
 if !errors.Is(AuthorizeLiveOriginal(r),ErrNoScienceAuthority){t.Fatal("unsafe promotion")}
 a,err:=Prepare(p)
 if err!=nil||a.CandidateDigest!=r.CandidateDigest{t.Fatal("not deterministic")}
 p.ActionNumerator=1;p.ActionDenominator=7
 c,e:=Prepare(p)
 if e!=nil||c.CandidateDigest==r.CandidateDigest{t.Fatal("non-unique rational arm")}
 if !errors.Is(AuthorizeLiveOriginal(c),ErrNoScienceAuthority){t.Fatal("propensity promoted")}
}
func TestNativeFirstUseSourceDeniesDriftAndReplay(t *testing.T){
 cases:=[]struct{name string;mutate func(*Proposal)}{
  {"old_original_state",func(p *Proposal){p.Claim.FirstUseConsumed=false}},
  {"wrong_lane",func(p *Proposal){p.Claim.Lane="CKB"}},
  {"wrong_worker",func(p *Proposal){p.Lease.WorkerID="shadow"} },
  {"wrong_intent",func(p *Proposal){p.Lease.IntentSHA256=rep("9",64)}},
  {"wrong_epoch",func(p *Proposal){p.Lease.OwnerEpoch=8}},
  {"wrong_owner",func(p *Proposal){p.Lease.OwnerID="new-controller"}},
  {"lease_risk",func(p *Proposal){p.Lease.FirstUseRisk=true}},
  {"expired_lease",func(p *Proposal){p.AtUnix=1010}},
  {"invalid_source",func(p *Proposal){p.Claim.SourceCommitSHA="untrusted"}},
  {"missing_wingless",func(p *Proposal){p.Snapshots[0]=LaneSnapshot{}}},
  {"duplicate_lanes",func(p *Proposal){p.Snapshots[1].Lane="Wingless"}},
  {"reused_ledger",func(p *Proposal){p.Snapshots[1].LedgerSHA256=p.Snapshots[0].LedgerSHA256}},
  {"missing_ledger",func(p *Proposal){p.Snapshots[1].LedgerSHA256=""}},
  {"other_epoch",func(p *Proposal){p.Snapshots[1].OwnerEpoch=6}},
  {"foreign_source",func(p *Proposal){p.Snapshots[1].SourceCommitSHA=p.Snapshots[0].SourceCommitSHA}},
  {"source_replays_intent",func(p *Proposal){p.Snapshots[1].LedgerSHA256=p.Claim.IntentSHA256}},
  {"zero_action_probability",func(p *Proposal){p.ActionNumerator=0}},
  {"nonreduced_probability",func(p *Proposal){p.ActionNumerator=2;p.ActionDenominator=6}},
  {"rounded_probability",func(p *Proposal){p.ActionNumerator=1;p.ActionDenominator=1000000001}},
  {"invalid_policy",func(p *Proposal){p.PolicySHA256="FUTURE"}},
  {"self_policy",func(p *Proposal){p.FrozenDecisionSHA256=p.PolicySHA256}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   p:=fixture();tc.mutate(&p)
   got,err:=Prepare(p)
   if !errors.Is(err,ErrNoScienceAuthority)||got!=(Review{}){
    t.Fatalf("should deny, got %+v, %v",got,err)
   }
  })
 }
}
func TestNativeFirstUsePublicExecutionAlwaysDenied(t *testing.T){
 for _,r:=range []Review{
  {},{Schema:Schema,SourceAndLeaseCorrespondenceVerified:true,
   TwoLaneSnapshotShapeVerified:true},
  {Schema:Schema,ExternallyAuthenticatedFullOriginalHistory:true,
   IndependentlyAcceptedCurrentOwner:true,PrivateRestorableBackupVerified:true,
   AtomicD1FirstUseConsumed:true,LiveWorkerPermitIssued:true},
 }{
  if !errors.Is(AuthorizeLiveOriginal(r),ErrNoScienceAuthority){
   t.Fatal("caller-provided authority flags bypassed")
  }
 }
}
