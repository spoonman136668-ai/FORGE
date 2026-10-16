// Package sciencehandoff binds the existing worker lease and two-lane
// original-science first-use inventory to the existing R41 canonical owner
// predecision/R35-D1 claim shape. It is pure, WITHOUT ANY DISPATCH OR D1 WRITE.
//
// The supplied cohort pins and signed owner keys MUST be independently sourced:
// matching self-declared hashes does not establish independent owner custody.
package sciencehandoff

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"

 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/preusebinding"
 "github.com/spoonman136668-ai/forge/workerlease"
)

const (
 Schema = "forge.f69.prospective-owner-lease-firstuse-handoff.v1"
 CohortSchema = "forge.f69.lane-firstuse-snapshot.v1"
 domain = "FORGE-F69-LANE-FIRSTUSE-SNAPSHOT-V1\n"
)
var ErrBlocked=errors.New("F69_EXISTING_OWNER_AND_FIRST_USE_LEASE_NOT_AUTHENTICATED")

type Original struct {
 ExperimentID string `json:"experiment_id"`
 IntentSHA256 string `json:"intent_sha256"`
 State string `json:"state"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 DecisionSequence uint64 `json:"decision_sequence"`
}
type Cohort struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 SequenceHighwater uint64 `json:"sequence_highwater"`
 Records []Original `json:"records"`
}
type Pins struct {
 // Pin hashes must come from outside the proposed original and its worker.
 WinglessSnapshotSHA256 string
 YggdrasilSnapshotSHA256 string
 OwnerID string
 OwnerEpoch uint64
}
type Input struct {
 Claim originalclaim.Claim
 Signed originalclaim.SignedPredecision
 Trust originalclaim.PinnedTrust
 Lease workerlease.Lease
 Cohorts [2]Cohort
 Pins Pins
 NowUnix uint64
}
type Report struct {
 Schema string `json:"schema"`
 Disposition string `json:"disposition"`
 SignedPredecisionSourceVerified bool `json:"signed_predecision_source_verified"`
 PinnedTwoLaneSnapshotCorrespondenceVerified bool `json:"pinned_two_lane_snapshot_correspondence_verified"`
 SameOwnerLeaseHeldAtObservation bool `json:"same_owner_lease_held_at_observation"`
 CanonicalR41D1Candidate preusebinding.Claim `json:"canonical_r41_d1_candidate"`
 CurrentOwnerIndependentlyAttested bool `json:"current_owner_independently_attested"`
 CompleteTwoLaneFirstUseExternallyWitnessed bool `json:"complete_two_lane_firstuse_externally_witnessed"`
 LiveD1AtomicFirstUseConsumed bool `json:"live_d1_atomic_firstuse_consumed"`
 WorkerExecutionPermitIssued bool `json:"worker_execution_permit_issued"`
 OriginalScienceAuthorized bool `json:"original_science_authorized"`
 OriginalDispatched bool `json:"original_dispatched"`
 OwnerCutoverAuthorized bool `json:"owner_cutover_authorized"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validName(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'){return false}
 }
 return true
}
func validLane(s string)bool{return s=="Wingless"||s=="Yggdrasil"}
func allowedState(s string)bool{
 return s=="CONSUMED"||s=="ACTIVE"||s=="UNCERTAIN"
}
// SnapshotHash binds an *exact source representation* to externally supplied
// pins; it does not prove these records exhaust the installed owner ledger.
func SnapshotHash(c Cohort)(string,error){
 if c.Schema!=CohortSchema||!validLane(c.Lane)||
  c.OwnerEpoch==0||c.OwnerEpoch>math.MaxInt64||
  c.SequenceHighwater>math.MaxInt64||c.Records==nil||len(c.Records)>10000{
  return "",ErrBlocked
 }
 seen:=map[string]bool{}
 prev:=uint64(0)
 for _,r:=range c.Records{
  if !validName(r.ExperimentID)||!validHex(r.IntentSHA256,64)||
   !allowedState(r.State)||r.OwnerEpoch==0||r.OwnerEpoch>c.OwnerEpoch||
   r.DecisionSequence==0||r.DecisionSequence<=prev||
   r.DecisionSequence>c.SequenceHighwater||seen[r.ExperimentID]{
   return "",ErrBlocked
  }
  prev=r.DecisionSequence
  seen[r.ExperimentID]=true
 }
 raw,err:=json.Marshal(c)
 if err!=nil{return "",ErrBlocked}
 sum:=sha256.Sum256(append([]byte(domain),raw...))
 return hex.EncodeToString(sum[:]),nil
}
// Assess checks BOTH frozen lane snapshots, signed canonical prospective
// owner choice, same-owner work lease and shared monotonically higher sequence.
// A positive result only produces an INERT candidate for further authority
// review. It can neither write the installed Cloudflare D1 nor issue a permit.
func Assess(x Input)(Report,error){
 zero:=Report{}
 c:=x.Claim
 if x.Pins.OwnerID==""||x.Pins.OwnerEpoch==0||
  x.Pins.OwnerEpoch>math.MaxInt64||x.NowUnix==0||
  !validHex(x.Pins.WinglessSnapshotSHA256,64)||
  !validHex(x.Pins.YggdrasilSnapshotSHA256,64)||
  !validLane(c.Lane)||!validName(c.ExperimentID)||
  c.OwnerEpoch!=x.Pins.OwnerEpoch||!c.FirstUseConsumed||
  x.Lease.OwnerID!=x.Pins.OwnerID||x.Lease.OwnerEpoch!=x.Pins.OwnerEpoch||
  x.Lease.ExperimentID!=c.ExperimentID||x.Lease.Lane!=c.Lane||
  x.Lease.IntentSHA256!=c.IntentSHA256||
  x.Lease.WorkerID!=c.WorkerID||x.Lease.FirstUseRisk{
  return zero,ErrBlocked
 }
 // A time-valid lease is necessary for a snapshot binding, NEVER sufficient
 // for a scientific execution permit.
 state,err:=workerlease.Inspect(x.Lease,x.NowUnix,x.Pins.OwnerID,x.Pins.OwnerEpoch)
 if err!=nil||state!=workerlease.Held{return zero,ErrBlocked}
 if originalclaim.VerifyPredecision(x.Signed,c,x.Trust)!=nil{return zero,ErrBlocked}
 projected,err:=preusebinding.FromOwnerPredecision(x.Signed,c,x.Trust)
 if err!=nil||projected.ScientificAuthorized{return zero,ErrBlocked}
 if x.Signed.Event.DecisionSequence==0||x.Signed.Event.DecisionSequence>math.MaxInt64{
  return zero,ErrBlocked
 }
 maxSeq:=uint64(0)
 seenLanes:=map[string]bool{}
 seenIntent:=map[string]bool{}
 seenSequences:=map[uint64]bool{}
 for _,cohort:=range x.Cohorts{
  h,err:=SnapshotHash(cohort)
  if err!=nil||cohort.OwnerEpoch!=x.Pins.OwnerEpoch||seenLanes[cohort.Lane]{
   return zero,ErrBlocked
  }
  expected:=x.Pins.WinglessSnapshotSHA256
  if cohort.Lane=="Yggdrasil"{expected=x.Pins.YggdrasilSnapshotSHA256}
  if h!=expected{return zero,ErrBlocked}
  seenLanes[cohort.Lane]=true
  if cohort.SequenceHighwater>maxSeq{maxSeq=cohort.SequenceHighwater}
  for _,r:=range cohort.Records{
   // Never interpret an absence as an unused original. Reject any exact
   // experiment replay and repeated intent across projects conservatively.
   if r.ExperimentID==c.ExperimentID||r.IntentSHA256==c.IntentSHA256||
    seenIntent[r.IntentSHA256]||seenSequences[r.DecisionSequence]{
    return zero,ErrBlocked
   }
   seenIntent[r.IntentSHA256]=true
   seenSequences[r.DecisionSequence]=true
  }
 }
 if len(seenLanes)!=2||!seenLanes["Wingless"]||!seenLanes["Yggdrasil"]||
  projected.ClaimedSequence<=maxSeq||
  projected.OwnerEpoch!=x.Pins.OwnerEpoch||
  projected.SourceCommitSHA!=c.SourceCommitSHA||
  projected.Lane!=c.Lane{
  return zero,ErrBlocked
 }
 return Report{
  Schema:Schema,Disposition:"SOURCE_BOUND_CANDIDATE_ONLY_EXTERNAL_OWNER_D1_PERMIT_BLOCKED",
  SignedPredecisionSourceVerified:true,
  PinnedTwoLaneSnapshotCorrespondenceVerified:true,
  SameOwnerLeaseHeldAtObservation:true,
  CanonicalR41D1Candidate:projected,
  // These are ALWAYS false. No source-controlled attestations may override.
 },nil
}
