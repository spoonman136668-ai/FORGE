// Package lanetakeover verifies read-only custody snapshots for the TWO
// existing research lanes. It cannot dispatch work, transfer authority or
// create a new scientific lane.
package lanetakeover

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "sort"
)

const Schema = "forge.existing-lane-custody.v1"
const domain = "FORGE_EXISTING_LANE_CUSTODY_V1\n"
var ErrBlocked = errors.New("FORGE_EXISTING_LANE_TAKEOVER_BLOCKED")

// Custody is a signed observation from an independently provisioned evidence
// collector, not a grant of execution authority. One signed record per lane.
type Custody struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceRepo string `json:"source_repo"`
 SourceCommitSHA string `json:"source_commit_sha"`
 ExistingQueueID string `json:"existing_queue_id"`
 ExistingLaneID string `json:"existing_lane_id"`
 LegacyAuthorityID string `json:"legacy_authority_id"`
 LegacyJournalHeadSHA256 string `json:"legacy_journal_head_sha256"`
 LegacyConsumedLedgerSHA256 string `json:"legacy_consumed_ledger_sha256"`
 LegacyFrozenWorkSHA256 string `json:"legacy_frozen_work_sha256"`
 ActiveLeaseCount uint64 `json:"active_lease_count"`
 UncertainDispatchCount uint64 `json:"uncertain_dispatch_count"`
 LastLegacyOwnerReleaseSHA256 string `json:"last_legacy_owner_release_sha256"`
 ObservationSequence uint64 `json:"observation_sequence"`
}
type SignedCustody struct {
 Custody Custody `json:"custody"`
 SignatureHex string `json:"signature_hex"`
}
type ExpectedLane struct {
 Lane string
 SourceRepo string
 SourceCommitSHA string
 ExistingQueueID string
 ExistingLaneID string
 LegacyAuthorityID string
}
type Plan struct {
 TrustedCollectorKey ed25519.PublicKey
 Wingless ExpectedLane
 Yggdrasil ExpectedLane
 MinimumObservationSequence uint64
}
// Result is a qualified handoff *candidate* only. It has no activation,
// admission, deployment, signing, orchestration, queue or migration powers.
type Result struct {
 WinglessCustodySHA256 string
 YggdrasilCustodySHA256 string
}
func isHex(s string,n int) bool {
 if len(s)!=n {return false}
 for _,r:=range s {if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func VerifySigned(s SignedCustody,key ed25519.PublicKey)(string,error) {
 if len(key)!=ed25519.PublicKeySize{return "",ErrBlocked}
 c:=s.Custody
 if c.Schema!=Schema || (c.Lane!="Wingless"&&c.Lane!="Yggdrasil") ||
  c.SourceRepo=="" || c.ExistingLaneID=="" || c.ExistingQueueID=="" ||
  c.LegacyAuthorityID=="" || c.ObservationSequence==0 ||
  !isHex(c.SourceCommitSHA,40) ||
  !isHex(c.LegacyJournalHeadSHA256,64) ||
  !isHex(c.LegacyConsumedLedgerSHA256,64) ||
  !isHex(c.LegacyFrozenWorkSHA256,64) ||
  !isHex(c.LastLegacyOwnerReleaseSHA256,64) ||
  !isHex(s.SignatureHex,ed25519.SignatureSize*2) {return "",ErrBlocked}
 b,err:=json.Marshal(c);if err!=nil{return "",ErrBlocked}
 sig,err:=hex.DecodeString(s.SignatureHex)
 if err!=nil||!ed25519.Verify(key,append([]byte(domain),b...),sig){return "",ErrBlocked}
 h:=sha256.Sum256(append([]byte(domain),b...))
 return hex.EncodeToString(h[:]),nil
}
func exact(s SignedCustody,e ExpectedLane,p Plan)(string,error){
 if e.Lane!=s.Custody.Lane || e.SourceRepo!=s.Custody.SourceRepo ||
  e.SourceCommitSHA!=s.Custody.SourceCommitSHA ||
  e.ExistingLaneID!=s.Custody.ExistingLaneID ||
  e.ExistingQueueID!=s.Custody.ExistingQueueID ||
  e.LegacyAuthorityID!=s.Custody.LegacyAuthorityID ||
  !isHex(e.SourceCommitSHA,40) ||
  s.Custody.ObservationSequence<p.MinimumObservationSequence ||
  s.Custody.ActiveLeaseCount!=0 || s.Custody.UncertainDispatchCount!=0 {
  return "",ErrBlocked
 }
 return VerifySigned(s,p.TrustedCollectorKey)
}
// Preflight evaluates exactly the two pre-existing lanes in input-order
// independent fashion. It deliberately NEVER writes a queue or starts science.
func Preflight(p Plan,records []SignedCustody)(Result,error){
 if len(records)!=2||p.MinimumObservationSequence==0 ||
  len(p.TrustedCollectorKey)!=ed25519.PublicKeySize ||
  p.Wingless.Lane!="Wingless"||p.Yggdrasil.Lane!="Yggdrasil" ||
  p.Wingless.ExistingLaneID==p.Yggdrasil.ExistingLaneID ||
  p.Wingless.ExistingQueueID==p.Yggdrasil.ExistingQueueID ||
  p.Wingless.LegacyAuthorityID==""||p.Yggdrasil.LegacyAuthorityID==""{
  return Result{},ErrBlocked
 }
 seen:=map[string]SignedCustody{}
 for _,s:=range records{
  if _,ok:=seen[s.Custody.Lane];ok{return Result{},ErrBlocked}
  seen[s.Custody.Lane]=s
 }
 w,okW:=seen["Wingless"];y,okY:=seen["Yggdrasil"]
 if !okW||!okY{return Result{},ErrBlocked}
 wh,err:=exact(w,p.Wingless,p);if err!=nil{return Result{},fmt.Errorf("Wingless: %w",err)}
 yh,err:=exact(y,p.Yggdrasil,p);if err!=nil{return Result{},fmt.Errorf("Yggdrasil: %w",err)}
 // Cross-lane queue and custody identities must be different; never clone
 // an existing lane into a fresh FORGE identity.
 if w.Custody.LegacyJournalHeadSHA256==y.Custody.LegacyJournalHeadSHA256 ||
  w.Custody.LegacyConsumedLedgerSHA256==y.Custody.LegacyConsumedLedgerSHA256 ||
  w.Custody.LegacyFrozenWorkSHA256==y.Custody.LegacyFrozenWorkSHA256 ||
  w.Custody.ExistingQueueID==y.Custody.ExistingQueueID ||
  w.Custody.ExistingLaneID==y.Custody.ExistingLaneID {
  return Result{},ErrBlocked
 }
 return Result{WinglessCustodySHA256:wh,YggdrasilCustodySHA256:yh},nil
}
// IdentityKeys returns the stable original lane names, never a replacement
// identifier or a newly generated queue name.
func IdentityKeys()[]string{
 v:=[]string{"Wingless","Yggdrasil"}
 sort.Strings(v)
 return v
}
