// Package nativefirstuse prepares a FORGE-native two-lane science first-use
// identity. This is an INERT admission contract, not an execution permit.
// It reuses FORGE's existing originalclaim and workerlease safeguards instead
// of resurrecting the retired CKB-plane research controller.
package nativefirstuse

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "unicode/utf8"

 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/workerlease"
)

const Schema = "forge.f74.native-two-lane-firstuse-source-bound.v1"
// Domain-separated v2: hash the entire accepted proposal, not a subset of
// fields. The previous digest omitted lease and both cohort source/high-water
// details, allowing distinct snapshots to share one candidate identity.
// This remains source-only and never grants original first-use authority.
const CandidateDigestDomain = "FORGE-F74-NATIVE-FIRSTUSE-CANDIDATE-V2\n"
var ErrNoScienceAuthority = errors.New("F74_NO_INDEPENDENT_CURRENT_OWNER_AND_TWO_LANE_FIRST_USE_CUSTODY")

type LaneSnapshot struct {
 Lane string
 SourceCommitSHA string
 LedgerSHA256 string
 OwnerEpoch uint64
 SequenceHighwater uint64
 // Counts of all prior first-use dispositions MUST be supplied from
 // independently proven complete lane custody, not the caller alone.
 ConsumedCount uint64
 ActiveCount uint64
 UncertainCount uint64
}
type Proposal struct {
 Claim originalclaim.Claim
 Lease workerlease.Lease
 OwnerID string
 OwnerEpoch uint64
 AtUnix uint64
 FrozenDecisionSHA256 string
 PolicySHA256 string
 BudgetSHA256 string
 ActionNumerator uint64
 ActionDenominator uint64
 Snapshots [2]LaneSnapshot
}
type Review struct {
 Schema string `json:"schema"`
 CandidateDigest string `json:"candidate_digest"`
 Lane string `json:"lane"`
 SourceAndLeaseCorrespondenceVerified bool `json:"source_and_lease_correspondence_verified"`
 TwoLaneSnapshotShapeVerified bool `json:"two_lane_snapshot_shape_verified"`
 ExternallyAuthenticatedFullOriginalHistory bool `json:"externally_authenticated_full_original_history"`
 IndependentlyAcceptedCurrentOwner bool `json:"independently_accepted_current_owner"`
 PrivateRestorableBackupVerified bool `json:"private_restorable_backup_verified"`
 AtomicD1FirstUseConsumed bool `json:"atomic_d1_firstuse_consumed"`
 LiveWorkerPermitIssued bool `json:"live_worker_permit_issued"`
 OriginalDispatched bool `json:"original_dispatched"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
 Disposition string `json:"disposition"`
}
func hexN(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{
  if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}
 }
 return true
}
func validName(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{
  if !(c>='A'&&c<='Z'||c>='a'&&c<='z'||c>='0'&&c<='9'||c=='_'||c=='-'){
   return false
  }
 }
 return true
}
func validSnapshot(s LaneSnapshot)bool{
 return(s.Lane=="Wingless"||s.Lane=="Yggdrasil")&&
  hexN(s.SourceCommitSHA,40)&&hexN(s.LedgerSHA256,64)&&
  s.OwnerEpoch>0&&s.SequenceHighwater>0
}
// JSON replaces malformed UTF-8 with U+FFFD. Reject it in *every* proposal
// string before encoding so distinct owner/worker/original bytes cannot alias.
// Other validators currently restrict most fields to ASCII, but enumerate all
// strings here to keep the digest boundary safe if that policy later changes.
func validProposalUTF8(p Proposal)bool{
 c,l:=p.Claim,p.Lease
 fields:=[]string{
  c.Schema,c.Lane,c.ExperimentID,c.FrozenSHA256,c.IntentSHA256,
  c.SourceCommitSHA,c.OriginalRunID,c.WorkerID,
  l.Lane,l.ExperimentID,l.IntentSHA256,l.OwnerID,l.WorkerID,
  p.OwnerID,p.FrozenDecisionSHA256,p.PolicySHA256,p.BudgetSHA256,
 }
 for _,snapshot:=range p.Snapshots{
  fields=append(fields,snapshot.Lane,snapshot.SourceCommitSHA,snapshot.LedgerSHA256)
 }
 for _,value:=range fields{
  if !utf8.ValidString(value){return false}
 }
 return true
}
// Pure source-level interlock. The inputs are NOT treated as independent
// evidence; they may be caller-provided. Never allow this function's
// synthetic success to become a live Cloudflare or worker authorization.
func Prepare(p Proposal)(Review,error){
 var zero Review
 c,l:=p.Claim,p.Lease
 if !validProposalUTF8(p)||c.Schema!=originalclaim.Schema||!c.FirstUseConsumed||
  (c.Lane!="Wingless"&&c.Lane!="Yggdrasil")||
  !validName(c.ExperimentID)||!hexN(c.SourceCommitSHA,40)||
  !hexN(c.FrozenSHA256,64)||!hexN(c.IntentSHA256,64)||
  !hexN(p.FrozenDecisionSHA256,64)||!hexN(p.PolicySHA256,64)||
  !hexN(p.BudgetSHA256,64)||
  p.FrozenDecisionSHA256==p.PolicySHA256||
  p.OwnerID==""||p.OwnerEpoch==0||p.AtUnix==0||
  p.ActionNumerator==0||p.ActionDenominator==0||
  p.ActionNumerator>p.ActionDenominator||
  p.ActionDenominator>1_000_000_000||
  c.OwnerEpoch!=p.OwnerEpoch||
  l.OwnerEpoch!=p.OwnerEpoch||l.OwnerID!=p.OwnerID||
  l.Lane!=c.Lane||l.ExperimentID!=c.ExperimentID||
  l.IntentSHA256!=c.IntentSHA256||l.WorkerID!=c.WorkerID||
  l.FirstUseRisk||
  !validSnapshot(p.Snapshots[0])||!validSnapshot(p.Snapshots[1])||
  p.Snapshots[0].Lane!="Wingless"||p.Snapshots[1].Lane!="Yggdrasil"||
  p.Snapshots[0].LedgerSHA256==p.Snapshots[1].LedgerSHA256||
  p.Snapshots[0].SourceCommitSHA==p.Snapshots[1].SourceCommitSHA||
  p.Snapshots[0].OwnerEpoch!=p.OwnerEpoch||
  p.Snapshots[1].OwnerEpoch!=p.OwnerEpoch{
  return zero,ErrNoScienceAuthority
 }
 state,err:=workerlease.Inspect(l,p.AtUnix,p.OwnerID,p.OwnerEpoch)
 if err!=nil||state!=workerlease.Held{return zero,ErrNoScienceAuthority}
 if gcd(p.ActionNumerator,p.ActionDenominator)!=1{
  return zero,ErrNoScienceAuthority
 }
 // Forbid accidentally identifying a frozen prospect as the same original
 // as any ledger root or as one of the owner-approved current source hashes.
 for _,s:=range p.Snapshots{
  if s.LedgerSHA256==c.IntentSHA256||s.LedgerSHA256==p.FrozenDecisionSHA256{
   return zero,ErrNoScienceAuthority
  }
 }
 // JSON encodes every scalar, both ordered snapshots, and each nested
 // claim/lease field unambiguously. Go's struct-field order is stable, unlike
 // an ad hoc delimiter stream or a selectively hashed field list.
 canonical,err:=json.Marshal(p)
 if err!=nil{return zero,ErrNoScienceAuthority}
 digest:=sha256.Sum256(append([]byte(CandidateDigestDomain),canonical...))
 return Review{
  Schema:Schema,CandidateDigest:hex.EncodeToString(digest[:]),Lane:c.Lane,
  SourceAndLeaseCorrespondenceVerified:true,
  TwoLaneSnapshotShapeVerified:true,
  Disposition:"SOURCE_CORRESPONDENCE_ONLY_OWNER_CUSTODY_TIME_TRAVEL_AND_D1_PERMIT_UNQUALIFIED",
 },nil
}
func gcd(a,b uint64)uint64{for b!=0{a,b=b,a%b};return a}
// Production admission remains denied without REAL independently sourced
// owner/lease/first-use and serving-worker custody. Even a positive source
// review grants no D1 or worker operation.
func AuthorizeLiveOriginal(Review)error{return ErrNoScienceAuthority}
