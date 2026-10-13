// Package ckbreconcile checks two independent observations of the existing
// CKB S14 original: permanent local S09-S14 first-use state and GitHub's
// original workflow/intent histories. This is a read-only diagnosis, NEVER a
// grant to replay, restart, transfer CKB ownership or execute FORGE science.
package ckbreconcile

import(
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/ckbcustody"
 "github.com/spoonman136668-ai/forge/ckbhistory"
)
const Schema="forge.ckb.s14-dual-source-reconciliation.v1"
const Mode="READ_ONLY_CKB_S14_CONSUMED_NO_REPLAY"
var ErrBlocked=errors.New("FORGE_CKB_S14_DUAL_SOURCE_INDETERMINATE_NO_RETRY")
type HistoryReader interface{InspectS14(context.Context)(ckbhistory.Report,error)}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 LegacyInventorySHA256 string `json:"legacy_inventory_sha256"`
 LocalS14PermanentFirstUseSHA256 string `json:"local_s14_first_use_sha256"`
 GitHubHistorySHA256 string `json:"github_history_sha256"`
 GitHubOriginalRunIDs []int64 `json:"github_original_run_ids"`
 GitHubIssuerArtifactIDs []int64 `json:"github_issuer_artifact_ids"`
 OriginalStatus string `json:"original_status"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
 CutoverAuthorized bool `json:"cutover_authorized"`
 ScientificCyclesVerified int `json:"scientific_cycles_verified"`
 Outstanding []string `json:"outstanding"`
}
func validHash(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func verifiedRemote(r ckbhistory.Report)bool{
 if r.Schema!=ckbhistory.Schema||r.Repository!="spoonman136668-ai/ckb-plane"||
  r.OriginalWorkflow!=ckbhistory.OriginalPath||r.FirstUseReplayAuthorized||
  r.ScientificExecutionActivated||r.OriginalAttemptCount!=len(r.OriginalRunIDs)||
  r.IntentArtifactCount!=len(r.IntentArtifactIDs)||!validHash(r.EvidenceSHA256){
  return false
 }
 // Validate the exact content-addressed report produced by GitHub reader.
 digest:=r.EvidenceSHA256
 r.EvidenceSHA256=""
 raw,err:=json.Marshal(r)
 if err!=nil{return false}
 hash:=sha256.Sum256(append([]byte("FORGE-CKB-S14-HISTORY-V1\n"),raw...))
 return hex.EncodeToString(hash[:])==digest
}
// Reconcile requires independent historical SHA pins and COMPLETE consumed
// S09-S14 local custody. The GitHub read is sandwiched between authenticated
// local snapshots: mutation, absent S14, unavailable GitHub, or unknown
// source identity abort without a false unconsumed-first-use conclusion.
func Reconcile(ctx context.Context,reader HistoryReader,stateDirectory string,pins map[string]string)(Report,error){
 if ctx==nil||ctx.Err()!=nil||reader==nil||len(pins)!=6{return Report{},ErrBlocked}
 before,err:=ckbcustody.Inspect(stateDirectory)
 if err!=nil||ckbcustody.VerifyPins(before,pins)!=nil||
  len(before.Generations)!=6||
  before.S14Disposition!="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"{
  return Report{},ErrBlocked
 }
 gh,err:=reader.InspectS14(ctx)
 if err!=nil||ctx.Err()!=nil||!verifiedRemote(gh){return Report{},ErrBlocked}
 after,err:=ckbcustody.Inspect(stateDirectory)
 if err!=nil||ckbcustody.VerifyPins(after,pins)!=nil||
  after.InventorySHA256!=before.InventorySHA256||
  after.Generations[5].SHA256!=before.Generations[5].SHA256{
  return Report{},ErrBlocked
 }
 state:="GITHUB_ABSENCE_DOES_NOT_CLEAR_PERMANENT_S14_FIRST_USE"
 if gh.OriginalAttemptCount>1||gh.IntentArtifactCount>1{
  state="MULTIPLE_GITHUB_ATTEMPTS_QUARANTINE_NO_REPLAY"
 }else if gh.OriginalAttemptCount==1{
  state="ORIGINAL_ATTEMPT_REQUIRES_SIGNED_RAW_EVIDENCE_NO_REPLAY"
 }else if gh.IntentArtifactCount==1{
  state="ISSUER_INTENT_ARCHIVED_ORIGINAL_UNKNOWN_NO_REPLAY"
 }
 return Report{Schema:Schema,Mode:Mode,
  LegacyInventorySHA256:before.InventorySHA256,
  LocalS14PermanentFirstUseSHA256:before.Generations[5].SHA256,
  GitHubHistorySHA256:gh.EvidenceSHA256,
  GitHubOriginalRunIDs:append([]int64{},gh.OriginalRunIDs...),
  GitHubIssuerArtifactIDs:append([]int64{},gh.IntentArtifactIDs...),
  OriginalStatus:state,FirstUseConsumed:true,
  OriginalReplayAuthorized:false,CutoverAuthorized:false,
  ScientificCyclesVerified:0,
  Outstanding:[]string{
   "S14_SOLE_CKB_WAKE_ISSUER_RUN_AND_EXACT_FAILURE_RECONCILIATION",
   "INDEPENDENT_ORIGINAL_WORKER_RECEIPTS_AND_ARCHIVED_RAW_DISPOSITION",
   "SIGNED_LIVE_CKB_OWNER_REVOCATION",
   "OFF_HOST_FSA_WORKER_EPOCH_FENCING",
   "GENUINE_SCIENTIFIC_CYCLES_AND_EXPLICIT_APPROVED_CUTOVER",
  },
 },nil
}
