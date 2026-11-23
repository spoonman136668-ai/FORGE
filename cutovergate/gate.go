// Package cutovergate composes OLD CKB original custody with independently
// attested pre-existing lane release and NEW FORGE authority evidence. The
// result is an audit candidate, NEVER a cutover, original grant or dispatch.
package cutovergate

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"

 "github.com/spoonman136668-ai/forge/ckbcustody"
 "github.com/spoonman136668-ai/forge/durableauthority"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/lanetakeover"
)
const Schema="forge.existing-lane.custody-join.v1"
const domain="FORGE-EXISTING-LANE-CUSTODY-JOIN-V1\n"
const Status="INACTIVE_CUSTODY_CANDIDATE_NOT_AUTHORIZED"
const MaxAgeSeconds uint64=300
var ErrBlocked=errors.New("FORGE_CKB_TO_FSA_CUTOVER_BLOCKED_NO_REPLAY")

// The collector must sign the *joint* inventory and BOTH legacy lane
// releases. Merely comparing two unrelated snapshots is not atomic custody.
type JointObservation struct{
 Schema string `json:"schema"`
 InventorySHA256 string `json:"inventory_sha256"`
 S14LedgerSHA256 string `json:"s14_ledger_sha256"`
 WinglessCustodySHA256 string `json:"wingless_custody_sha256"`
 YggdrasilCustodySHA256 string `json:"yggdrasil_custody_sha256"`
 ObservedAtUnix uint64 `json:"observed_at_unix"`
 LegacyAuthorityID string `json:"legacy_authority_id"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
}
type SignedJoint struct{
 Observation JointObservation `json:"observation"`
 SignatureHex string `json:"signature_hex"`
}
type Input struct{
 LegacyStateDirectory string
 LegacySHA256Pins map[string]string
 LegacyPlan lanetakeover.Plan
 LegacyLaneCustody []lanetakeover.SignedCustody
 LegacyJoin SignedJoint
 NowUnix uint64
 FSAAnchor fsahead.Anchor
 FSAPin fsaremote.Pin
 FSAWitness fsaremote.SignedWitness
 ForgeOriginalLedgerDirectory string
 ForgeOriginalGrantPublicKey ed25519.PublicKey
}
type Report struct{
 Mode string `json:"mode"`
 LegacyInventorySHA256 string `json:"legacy_inventory_sha256"`
 CKBFirstUseS14SHA256 string `json:"ckb_firstuse_s14_sha256"`
 LegacyJoinSHA256 string `json:"legacy_join_sha256"`
 WinglessCustodySHA256 string `json:"wingless_custody_sha256"`
 YggdrasilCustodySHA256 string `json:"yggdrasil_custody_sha256"`
 FSAArchiveID string `json:"fsa_archive_id"`
 FSAHeadSHA256 string `json:"fsa_head_sha256"`
 FSAWitnessRevision uint64 `json:"fsa_witness_revision"`
 ForgeOriginalReservationCount int `json:"forge_original_reservation_count"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
 ScienceActivated bool `json:"science_activated"`
 CutoverAuthorized bool `json:"cutover_authorized"`
 Pending []string `json:"pending"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func allowedNewLedger(path string)bool{
 if path==""||!filepath.IsAbs(path){return false}
 for _,part:=range strings.FieldsFunc(strings.ToLower(filepath.Clean(path)),func(r rune)bool{return r=='/'||r=='\\'}){
  switch part{case "ckbr","ckb-plane","ktrade","ktrade-external","research","state","forge-fsa-trust":return false}
 }
 for p:=filepath.Clean(path);;p=filepath.Dir(p){
  info,err:=os.Lstat(p)
  if err!=nil||!info.IsDir()||info.Mode()&os.ModeSymlink!=0{return false}
  if filepath.Dir(p)==p{break}
 }
 return true
}
func verifyJoint(j SignedJoint,key ed25519.PublicKey,now uint64)(string,error){
 v:=j.Observation
 if len(key)!=ed25519.PublicKeySize||now==0||v.Schema!=Schema||
  v.LegacyAuthorityID==""||v.OriginalReplayAuthorized||
  v.ObservedAtUnix==0||v.ObservedAtUnix>now||now-v.ObservedAtUnix>MaxAgeSeconds||
  !validHex(v.InventorySHA256,64)||!validHex(v.S14LedgerSHA256,64)||
  !validHex(v.WinglessCustodySHA256,64)||!validHex(v.YggdrasilCustodySHA256,64)||
  !validHex(j.SignatureHex,ed25519.SignatureSize*2){return "",ErrBlocked}
 raw,err:=json.Marshal(v)
 if err!=nil{return "",ErrBlocked}
 sig,err:=hex.DecodeString(j.SignatureHex)
 if err!=nil||!ed25519.Verify(key,append([]byte(domain),raw...),sig){return "",ErrBlocked}
 sum:=sha256.Sum256(append([]byte(domain),raw...))
 return hex.EncodeToString(sum[:]),nil
}
// Assess is fully read-only. The returned report intentionally can *never*
// indicate an authorized cutover; its evidentiary assertions must be repeated
// online against live CKB owner fencing before a separate future authority
// service can even consider promotion.
func Assess(in Input)(Report,error){
 if in.NowUnix==0||in.LegacyPlan.Wingless.LegacyAuthorityID==""||
  in.LegacyPlan.Wingless.LegacyAuthorityID!=in.LegacyPlan.Yggdrasil.LegacyAuthorityID||
  !allowedNewLedger(in.ForgeOriginalLedgerDirectory){return Report{},ErrBlocked}
 history,err:=ckbcustody.Inspect(in.LegacyStateDirectory)
 if err!=nil||ckbcustody.VerifyPins(history,in.LegacySHA256Pins)!=nil||
  len(history.Generations)!=6||
  history.S14Disposition!="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"{
  return Report{},ErrBlocked
 }
 old,err:=lanetakeover.Preflight(in.LegacyPlan,in.LegacyLaneCustody)
 if err!=nil{return Report{},ErrBlocked}
 j:=in.LegacyJoin.Observation
 jointSHA,err:=verifyJoint(in.LegacyJoin,in.LegacyPlan.TrustedCollectorKey,in.NowUnix)
 if err!=nil||j.InventorySHA256!=history.InventorySHA256||
  j.S14LedgerSHA256!=history.Generations[5].SHA256||
  j.WinglessCustodySHA256!=old.WinglessCustodySHA256||
  j.YggdrasilCustodySHA256!=old.YggdrasilCustodySHA256||
  j.LegacyAuthorityID!=in.LegacyPlan.Wingless.LegacyAuthorityID{
  return Report{},ErrBlocked
 }
 // Release proof MUST not be an all-zero placeholder and must be distinct
 // in each original lane. This is still a signed observation, not a fence.
 releases:=map[string]bool{}
 for _,record:=range in.LegacyLaneCustody {
  h:=record.Custody.LastLegacyOwnerReleaseSHA256
  if !validHex(h,64)||h==strings.Repeat("0",64)||releases[h]{
   return Report{},ErrBlocked
  }
  releases[h]=true
 }
 // Three unrelated trust roots: legacy collector, independent FSA witness,
 // and FORGE original-grant signer. A shared key is NOT independence.
 if len(in.FSAPin.WitnessPublicKey)!=ed25519.PublicKeySize||
  len(in.FSAPin.PublicKey)!=ed25519.PublicKeySize||
  len(in.ForgeOriginalGrantPublicKey)!=ed25519.PublicKeySize||
  bytes.Equal(in.LegacyPlan.TrustedCollectorKey,in.FSAPin.WitnessPublicKey)||
  bytes.Equal(in.LegacyPlan.TrustedCollectorKey,in.FSAPin.PublicKey)||
  bytes.Equal(in.LegacyPlan.TrustedCollectorKey,in.ForgeOriginalGrantPublicKey)||
  bytes.Equal(in.FSAPin.WitnessPublicKey,in.ForgeOriginalGrantPublicKey)||
  bytes.Equal(in.FSAPin.PublicKey,in.ForgeOriginalGrantPublicKey)||
  fsaremote.VerifyWitness(in.FSAPin,in.FSAWitness,in.FSAAnchor)!=nil||
  in.FSAAnchor.Sequence==0{
  return Report{},ErrBlocked
 }
 local,err:=durableauthority.Load(in.ForgeOriginalLedgerDirectory,in.ForgeOriginalGrantPublicKey)
 if err!=nil||len(local.Entries)!=0||len(local.ReservedOriginals)!=0||
  local.HeadSHA256!=strings.Repeat("0",64){
  return Report{},ErrBlocked
 }
 return Report{
  Mode:Status,LegacyInventorySHA256:history.InventorySHA256,
  CKBFirstUseS14SHA256:history.Generations[5].SHA256,
  LegacyJoinSHA256:jointSHA,WinglessCustodySHA256:old.WinglessCustodySHA256,
  YggdrasilCustodySHA256:old.YggdrasilCustodySHA256,
  FSAArchiveID:in.FSAAnchor.ArchiveID,FSAHeadSHA256:in.FSAAnchor.HeadSHA256,
  FSAWitnessRevision:in.FSAWitness.Head.Revision,
  ForgeOriginalReservationCount:0,OriginalReplayAuthorized:false,
  ScienceActivated:false,CutoverAuthorized:false,
  Pending:[]string{"LIVE_CKB_OWNER_REVOCATION_AND_WORKER_FENCING",
   "GITHUB_FIRST_USE_AND_ISSUER_ATTEMPT_RECONCILIATION",
   "OFF_HOST_LINEARIZABLE_FSA_AND_HIGHWATER",
   "AUTHENTICATED_SOURCE_AND_EXACT_TREE_REGRESSION",
   "GENUINE_INDEPENDENT_UNATTENDED_SCIENCE_CYCLES",
   "EXPLICIT_QUALIFIED_OPERATOR_CUTOVER"},
 },nil
}
