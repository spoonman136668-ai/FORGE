package ckbreconcile

import (
 "context"

 "github.com/spoonman136668-ai/forge/ckbcustody"
 "github.com/spoonman136668-ai/forge/ckbhistory"
)

const WakeSchema="forge.ckb.s14-three-source-reconciliation.v1"
const WakeMode="READ_ONLY_CKB_S14_WAKE_AND_FIRST_USE_NO_REPLAY"

type WakeReader interface {
 HistoryReader
 InspectWake(context.Context,int64,string)(ckbhistory.WakeEvidence,error)
}
type WakeReport struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Reconciled Report `json:"reconciled"`
 PinnedWakeRunID int64 `json:"pinned_wake_run_id"`
 PinnedWakeSourceSHA string `json:"pinned_wake_source_sha"`
 PinnedControllerSHA string `json:"pinned_controller_sha"`
 WakeConclusion string `json:"wake_conclusion"`
 WakeEvidenceSHA256 string `json:"wake_evidence_sha256"`
 WakeClassification string `json:"wake_classification"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
 FORGEAuthorityTransferred bool `json:"forge_authority_transferred"`
 ScienceActivated bool `json:"science_activated"`
 Outstanding []string `json:"outstanding"`
}

// ReconcileWake joins the exact original CKB owner wake (as recorded in the
// separately pinned private S14 ledger) with complete six-generation first-use
// and GitHub original/issuer inventories. It never treats a failed CKB wake
// or absent GitHub artifact as evidence the consumed S14 is safe to retry.
func ReconcileWake(ctx context.Context,source WakeReader,state string,pins map[string]string)(WakeReport,error){
 if ctx==nil||ctx.Err()!=nil||source==nil{return WakeReport{},ErrBlocked}
 before,err:=ckbcustody.ReadS14WakeBinding(state,pins)
 if err!=nil{return WakeReport{},ErrBlocked}
 joined,err:=Reconcile(ctx,source,state,pins)
 if err!=nil{return WakeReport{},ErrBlocked}
 wake,err:=source.InspectWake(ctx,before.WakeRunID,before.WakeMainSHA)
 if err!=nil||ctx.Err()!=nil||ckbhistory.VerifyWakeEvidence(wake)!=nil||
  wake.WakeRunID!=before.WakeRunID||wake.WakeMainSHA!=before.WakeMainSHA{
  return WakeReport{},ErrBlocked
 }
 after,err:=ckbcustody.ReadS14WakeBinding(state,pins)
 if err!=nil||after!=before||after.PermanentLedgerSHA256!=joined.LocalS14PermanentFirstUseSHA256{
  return WakeReport{},ErrBlocked
 }
 return WakeReport{Schema:WakeSchema,Mode:WakeMode,Reconciled:joined,
  PinnedWakeRunID:before.WakeRunID,PinnedWakeSourceSHA:before.WakeMainSHA,
  PinnedControllerSHA:before.ControllerSHA,WakeConclusion:wake.Conclusion,
  WakeEvidenceSHA256:wake.EvidenceSHA256,WakeClassification:wake.Classification,
  FirstUseConsumed:true,OriginalReplayAuthorized:false,
  FORGEAuthorityTransferred:false,ScienceActivated:false,
  Outstanding:[]string{
   "S14_PRIVATE_ISSUER_AND_WORKER_FIRST_USE_RECEIPTS",
   "ORIGINAL_WINGLESS_YGGDRASIL_RAW_DISPOSITION_AND_SCIENTIFIC_HISTORY",
   "LIVE_CKB_OWNER_REVOCATION_WITH_WORKER_EPOCH_FENCES",
   "OFF_HOST_INDEPENDENT_FSA_MONOTONIC_STORAGE",
   "GENUINE_UNATTENDED_SCIENTIFIC_CYCLE_QUALIFICATION",
   "EXPLICIT_QUALIFIED_CUTOVER_APPROVAL",
  },
 },nil
}
