package ckbhistory

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strconv"
)

const WakeSchema="forge.ckb.s14-issuer-wake.v1"
const wakeDomain="FORGE-CKB-S14-ISSUER-WAKE-V1\n"

type WakeEvidence struct{
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Workflow string `json:"workflow"`
 WakeRunID int64 `json:"wake_run_id"`
 WakeMainSHA string `json:"wake_main_sha"`
 Event string `json:"event"`
 RunAttempt int `json:"run_attempt"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 Classification string `json:"classification"`
 FirstUseReplayAuthorized bool `json:"first_use_replay_authorized"`
 EvidenceSHA256 string `json:"evidence_sha256"`
}

func permittedConclusion(x string)bool{
 switch x{
 case "success","failure","cancelled","timed_out","neutral",
  "skipped","action_required","startup_failure","stale":
  return true
 }
 return false
}

func sameWakeFields(w WakeEvidence)bool{
 if w.Schema!=WakeSchema||w.Repository!="spoonman136668-ai/ckb-plane"||
  w.Workflow!=WakeWorkflowPath||w.WakeRunID<=0||
  !validHash(w.WakeMainSHA,40)||w.RunAttempt!=1||
  w.Status!="completed"||!permittedConclusion(w.Conclusion)||
  w.FirstUseReplayAuthorized{return false}
 if w.Event!="workflow_dispatch"&&w.Event!="schedule"{return false}
 expected:="COMPLETED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"
 if w.Conclusion=="failure"{
  expected="FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"
 }
 return w.Classification==expected
}

func wakeDigest(w WakeEvidence)(string,error){
 w.EvidenceSHA256=""
 raw,err:=json.Marshal(w);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte(wakeDomain),raw...))
 return hex.EncodeToString(h[:]),nil
}

// VerifyWakeEvidence verifies exact source fields and a deterministic digest.
// A digest is not a signature: its transport authentication comes from the
// fixed CKB GitHub API TLS connection, and the expected ID/SHA from a separately
// pinned permanent private CKB first-use ledger.
func VerifyWakeEvidence(w WakeEvidence)error{
 if !sameWakeFields(w)||!validHash(w.EvidenceSHA256,64){return ErrBlocked}
 h,err:=wakeDigest(w)
 if err!=nil||h!=w.EvidenceSHA256{return ErrBlocked}
 return nil
}

// InspectWake queries exactly one existing CKB wake-run by independently
// pinned ledger ID and source commit. No arbitrary URL or other GitHub
// workflow is accepted. A failed wake is NOT permission to reuse S14.
func (c *Client) InspectWake(ctx context.Context,wakeID int64,sourceCommit string)(WakeEvidence,error){
 if wakeID<=0||!validHash(sourceCommit,40){return WakeEvidence{},ErrBlocked}
 var r run
 if err:=c.get(ctx,"/actions/runs/"+strconv.FormatInt(wakeID,10),&r);err!=nil{
  return WakeEvidence{},ErrBlocked
 }
 if r.ID!=wakeID||r.HeadSHA!=sourceCommit||
  r.Path!=WakeWorkflowPath||r.HeadBranch!="main"||
  (r.Event!="workflow_dispatch"&&r.Event!="schedule")||
  r.RunAttempt!=1||r.Status!="completed"||
  r.Conclusion==nil||!permittedConclusion(*r.Conclusion){
  return WakeEvidence{},ErrBlocked
 }
 class:="COMPLETED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"
 if *r.Conclusion=="failure"{
  class="FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"
 }
 w:=WakeEvidence{Schema:WakeSchema,Repository:"spoonman136668-ai/ckb-plane",
  Workflow:WakeWorkflowPath,WakeRunID:wakeID,WakeMainSHA:sourceCommit,
  Event:r.Event,RunAttempt:r.RunAttempt,Status:r.Status,
  Conclusion:*r.Conclusion,Classification:class,FirstUseReplayAuthorized:false}
 var err error
 w.EvidenceSHA256,err=wakeDigest(w)
 if err!=nil||VerifyWakeEvidence(w)!=nil{return WakeEvidence{},ErrBlocked}
 return w,nil
}
