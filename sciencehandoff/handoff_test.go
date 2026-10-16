package sciencehandoff

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/workerlease"
)
func hashed(label string)string{
 h:=sha256.Sum256([]byte("F69_SYNTHETIC_NOT_OWNER_CUSTODY_"+label))
 return hex.EncodeToString(h[:])
}
func fixture(t *testing.T)Input{
 t.Helper()
 c:=originalclaim.Claim{
  Schema:originalclaim.Schema,Lane:"Wingless",ExperimentID:"NEW_F69_PROSPECTIVE",
  FrozenSHA256:hashed("frozen"),IntentSHA256:hashed("intent"),
  SourceCommitSHA:strings.Repeat("a",40),OriginalRunID:"F69_NEW_RUN",
  OwnerEpoch:7,WorkerID:"f69_worker",FirstUseConsumed:true,
 }
 decision:=originalclaim.Predecision{
  Schema:originalclaim.PredecisionSchema,
  Lane:c.Lane,ExperimentID:c.ExperimentID,
  FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,
  SourceCommitSHA:c.SourceCommitSHA,OriginalRunID:c.OriginalRunID,
  OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,
  PolicySHA256:hashed("policy"),CandidateSetSHA256:hashed("candidates"),
  SelectedCandidateSHA256:hashed("selected"),
  BaselinePolicySHA256:[4]string{
   hashed("baseline1"),hashed("baseline2"),hashed("baseline3"),hashed("baseline4")},
  LoggedActionProbabilityBP:2000,RandomizationProofSHA256:hashed("randomness"),
  DecisionSequence:47,BeforeOutcomeDeclared:true,
 }
 owner:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{18},ed25519.SeedSize))
 witness:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{19},ed25519.SeedSize))
 raw,err:=json.Marshal(decision);if err!=nil{t.Fatal(err)}
 msg:=append([]byte(originalclaim.PredecisionDomain),raw...)
 digest,err:=originalclaim.PredecisionHash(decision);if err!=nil{t.Fatal(err)}
 signed:=originalclaim.SignedPredecision{Event:decision,
  OwnerSignatureHex:hex.EncodeToString(ed25519.Sign(owner,msg)),
  WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(witness,msg))}
 trust:=originalclaim.PinnedTrust{
  OwnerPublicKeyHex:hex.EncodeToString(owner.Public().(ed25519.PublicKey)),
  WitnessPublicKeyHex:hex.EncodeToString(witness.Public().(ed25519.PublicKey)),
  ExpectedPredecisionSHA256:digest,ExpectedPolicySHA256:decision.PolicySHA256,
  ExpectedBaselinePolicySHA256:decision.BaselinePolicySHA256,
 }
 cohorts:=[2]Cohort{
  {Schema:CohortSchema,Lane:"Wingless",OwnerEpoch:7,SequenceHighwater:45,
   Records:[]Original{{ExperimentID:"W_OLD",IntentSHA256:hashed("w-old"),
     State:"CONSUMED",OwnerEpoch:7,DecisionSequence:41}}},
  {Schema:CohortSchema,Lane:"Yggdrasil",OwnerEpoch:7,SequenceHighwater:46,
   Records:[]Original{{ExperimentID:"Y_UNCERTAIN",IntentSHA256:hashed("y-uncertain"),
     State:"UNCERTAIN",OwnerEpoch:7,DecisionSequence:42}}},
 }
 a,err:=SnapshotHash(cohorts[0]);if err!=nil{t.Fatal(err)}
 b,err:=SnapshotHash(cohorts[1]);if err!=nil{t.Fatal(err)}
 return Input{
  Claim:c,Signed:signed,Trust:trust,Cohorts:cohorts,
  Pins:Pins{WinglessSnapshotSHA256:a,YggdrasilSnapshotSHA256:b,
   OwnerID:"existing-ckb-owner",OwnerEpoch:7},
  Lease:workerlease.Lease{Lane:c.Lane,ExperimentID:c.ExperimentID,
   IntentSHA256:c.IntentSHA256,OwnerID:"existing-ckb-owner",OwnerEpoch:7,
   WorkerID:c.WorkerID,LeaseSequence:3,ExpiresAtUnix:1000,FirstUseRisk:false},
  NowUnix:900,
 }
}
func TestF69BothLaneSourceAndExistingOwnerLeaseProjectOneInertR41Candidate(t *testing.T){
 x:=fixture(t)
 result,err:=Assess(x)
 if err!=nil{t.Fatal(err)}
 if result.Schema!=Schema||!result.SignedPredecisionSourceVerified||
  !result.PinnedTwoLaneSnapshotCorrespondenceVerified||
  !result.SameOwnerLeaseHeldAtObservation||
  result.CanonicalR41D1Candidate.Lane!="Wingless"||
  result.CanonicalR41D1Candidate.OwnerEpoch!=7||
  result.CanonicalR41D1Candidate.ClaimedSequence!=47||
  result.CanonicalR41D1Candidate.ScientificAuthorized||
  result.CurrentOwnerIndependentlyAttested||
  result.CompleteTwoLaneFirstUseExternallyWitnessed||
  result.LiveD1AtomicFirstUseConsumed||
  result.WorkerExecutionPermitIssued||
  result.OriginalScienceAuthorized||result.OriginalDispatched||
  result.OwnerCutoverAuthorized{
  t.Fatalf("synthetic source projection escalated to science authority: %+v",result)
 }
}
func TestF69UncertainOrConsumedOriginalsNeverReEnterLeaseHandoff(t *testing.T){
 for _,state:=range []string{"CONSUMED","ACTIVE","UNCERTAIN"}{
  t.Run(state,func(t *testing.T){
   x:=fixture(t)
   x.Cohorts[1].Records[0].ExperimentID=x.Claim.ExperimentID
   x.Cohorts[1].Records[0].State=state
   digest,err:=SnapshotHash(x.Cohorts[1]);if err!=nil{t.Fatal(err)}
   x.Pins.YggdrasilSnapshotSHA256=digest
   if report,err:=Assess(x);err==nil||report!=(Report{}){
    t.Fatalf("reused original in %s state accepted",state)
   }
  })
 }
}
func TestF69SourceAndCohortPinDriftFailClosed(t *testing.T){
 cases:=[]struct{name string;mutate func(*Input)}{
  {"snapshot_pin",func(x *Input){x.Pins.WinglessSnapshotSHA256=hashed("wrong")}},
  {"single_lane",func(x *Input){x.Cohorts[1]=x.Cohorts[0]}},
  {"uncertain_evidence_removed",func(x *Input){x.Cohorts[1].Records=[]Original{}}},
  {"cohort_epoch",func(x *Input){x.Cohorts[0].OwnerEpoch=8}},
  {"cohort_missing_records",func(x *Input){x.Cohorts[1].Records=nil}},
  {"source_drift",func(x *Input){x.Claim.SourceCommitSHA=strings.Repeat("b",40)}},
  {"signed_event",func(x *Input){x.Signed.Event.DecisionSequence=45}},
  {"forged_owner",func(x *Input){x.Signed.OwnerSignatureHex=strings.Repeat("f",128)}},
  {"forged_witness",func(x *Input){x.Signed.WitnessSignatureHex=strings.Repeat("f",128)}},
  {"reused_keys",func(x *Input){x.Trust.WitnessPublicKeyHex=x.Trust.OwnerPublicKeyHex}},
  {"external_source_pin",func(x *Input){x.Trust.ExpectedPredecisionSHA256=hashed("forged")}},
  {"current_owner_changed",func(x *Input){x.Pins.OwnerID="new-owner"}},
  {"current_epoch_changed",func(x *Input){x.Pins.OwnerEpoch=8}},
  {"claim_epoch_changed",func(x *Input){x.Claim.OwnerEpoch=8}},
  {"worker_id_changed",func(x *Input){x.Lease.WorkerID="other"}},
  {"lease_intent_changed",func(x *Input){x.Lease.IntentSHA256=hashed("lease")}},
  {"firstuse_risk",func(x *Input){x.Lease.FirstUseRisk=true}},
  {"expired_lease",func(x *Input){x.NowUnix=1001}},
  {"missing_lease_clock",func(x *Input){x.NowUnix=0}},
  {"sequence_highwater_reaches_new",func(x *Input){
   x.Cohorts[0].SequenceHighwater=47
   h,_:=SnapshotHash(x.Cohorts[0]);x.Pins.WinglessSnapshotSHA256=h
  }},
  {"crosslane_sequence_overlap",func(x *Input){
   x.Cohorts[1].Records[0].DecisionSequence=41
   h,_:=SnapshotHash(x.Cohorts[1]);x.Pins.YggdrasilSnapshotSHA256=h
  }},
  {"intent_reuse_from_other_lane",func(x *Input){
   x.Cohorts[1].Records[0].IntentSHA256=x.Claim.IntentSHA256
   h,_:=SnapshotHash(x.Cohorts[1]);x.Pins.YggdrasilSnapshotSHA256=h
  }},
  {"policy_drift",func(x *Input){x.Trust.ExpectedPolicySHA256=hashed("unexpected-policy")}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   x:=fixture(t);tc.mutate(&x)
   result,err:=Assess(x)
   if err==nil||result!=(Report{}){t.Fatalf("untrusted admission: %+v %v",result,err)}
  })
 }
}
func TestF69SnapshotDuplicateSequenceMalformedOrUnknownOutcomeFails(t *testing.T){
 for _,edit:=range []struct{name string;mutate func(*Cohort)}{
  {"unsorted",func(c *Cohort){c.Records=append(c.Records,Original{
   ExperimentID:"OLDER",IntentSHA256:hashed("older"),State:"ACTIVE",
   OwnerEpoch:7,DecisionSequence:40})}},
  {"duplicate_experiment",func(c *Cohort){c.Records=append(c.Records,Original{
   ExperimentID:"W_OLD",IntentSHA256:hashed("different"),State:"ACTIVE",
   OwnerEpoch:7,DecisionSequence:44})}},
  {"unknown_outcome",func(c *Cohort){c.Records[0].State="SAFE_UNUSED"}},
  {"future_epoch",func(c *Cohort){c.Records[0].OwnerEpoch=8}},
  {"highwater_below_used",func(c *Cohort){c.SequenceHighwater=40}},
  {"missing_schema",func(c *Cohort){c.Schema=""}},
 }{
  t.Run(edit.name,func(t *testing.T){
   x:=fixture(t);c:=x.Cohorts[0];edit.mutate(&c)
   if _,err:=SnapshotHash(c);err==nil{t.Fatal("source snapshot drift accepted")}
  })
 }
}
