// Package cutovergate composes verified original CKB custody and FORGE's
// independently signed FSA shadow checkpoint. It never enables execution.
package cutovergate

import(
 "context"
 "reflect"

 "github.com/spoonman136668-ai/forge/ckbreconcile"
)

const CompleteSchema="forge.existing-lane.full-source-custody-audit.v1"
const CompleteStatus="INACTIVE_FULL_CUSTODY_AUDIT_NO_EXECUTION_AUTHORITY"
type CompleteReport struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 LegacyAndFSA Report `json:"legacy_and_fsa"`
 S14WakeAndFirstUse ckbreconcile.WakeReport `json:"s14_wake_and_first_use"`
 OriginalReplayAuthorized bool `json:"original_replay_authorized"`
 CutoverAuthorized bool `json:"cutover_authorized"`
 ScientificExecutionActivated bool `json:"scientific_execution_activated"`
}

// AssessWithWake is the composite, read-only CKB→FORGE cutover audit.
// Existing-lane custody, six immutable consumed first-use ledgers,
// GitHub S14 issuer/original history, exact original CKB wake and separately
// signed FSA high-water must ALL agree. Signed owner and FSA evidence are
// checked again after network reads to detect drift. A passing report never
// grants the original first use or creates an independent research owner.
func AssessWithWake(ctx context.Context,source ckbreconcile.WakeReader,in Input)(CompleteReport,error){
 if ctx==nil||ctx.Err()!=nil||source==nil{return CompleteReport{},ErrBlocked}
 first,err:=Assess(in)
 if err!=nil{return CompleteReport{},ErrBlocked}
 history,err:=ckbreconcile.ReconcileWake(ctx,source,in.LegacyStateDirectory,in.LegacySHA256Pins)
 if err!=nil||ctx.Err()!=nil{return CompleteReport{},ErrBlocked}
 if first.LegacyInventorySHA256!=history.Reconciled.LegacyInventorySHA256||
  first.CKBFirstUseS14SHA256!=history.Reconciled.LocalS14PermanentFirstUseSHA256{
  return CompleteReport{},ErrBlocked
 }
 second,err:=Assess(in)
 if err!=nil||ctx.Err()!=nil||!reflect.DeepEqual(first,second){
  return CompleteReport{},ErrBlocked
 }
 if history.OriginalReplayAuthorized||history.FORGEAuthorityTransferred||
  history.ScienceActivated||!history.FirstUseConsumed||
  history.Reconciled.CutoverAuthorized||first.CutoverAuthorized||
  first.ScienceActivated{return CompleteReport{},ErrBlocked}
 return CompleteReport{Schema:CompleteSchema,Mode:CompleteStatus,
  LegacyAndFSA:first,S14WakeAndFirstUse:history,
  OriginalReplayAuthorized:false,CutoverAuthorized:false,
  ScientificExecutionActivated:false},nil
}
