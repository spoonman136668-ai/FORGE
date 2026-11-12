// Package autonomychain audits the structural shape of two-lane scientific
// succession evidence. It never grants first-use, dispatch, or acceptance.
package autonomychain

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
)

const Schema = "forge.autonomy.original-succession-candidate.v1"
const ReportSchema = "forge.autonomy.non-authorizing-structural-audit.v1"
var ErrBlocked = errors.New("FORGE_AUTONOMY_CHAIN_INCOMPLETE_OR_UNTRUSTED")

type Original struct {
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 OriginalRunID string `json:"original_run_id"`
 SourceCommitSHA string `json:"source_commit_sha"`
 FrozenPlanSHA256 string `json:"frozen_plan_sha256"`
 StartReceiptSHA256 string `json:"start_receipt_sha256"`
 TerminalReceiptSHA256 string `json:"terminal_receipt_sha256"`
 IndependentReviewSHA256 string `json:"independent_review_sha256"`
 SuccessorExperimentID string `json:"successor_experiment_id"`
 // A locally asserted classification is explicitly NOT a source of authority.
 Classification string `json:"classification"`
}
type Candidate struct {
 Schema string `json:"schema"`
 Wingless []Original `json:"wingless"`
 Yggdrasil []Original `json:"yggdrasil"`
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 CandidateSHA256 string `json:"candidate_sha256"`
 ConnectedOriginalsPerLane int `json:"connected_originals_per_lane"`
 StructuralContinuity bool `json:"structural_continuity"`
 AuthenticFirstUseVerified bool `json:"authentic_first_use_verified"`
 IndependentScientificAcceptance bool `json:"independent_scientific_acceptance"`
 AutonomousDispatchAuthorized bool `json:"autonomous_dispatch_authorized"`
 OwnerCutoverAuthorized bool `json:"owner_cutover_authorized"`
 NextGate string `json:"next_gate"`
}
func hexLower(s string,n int) bool {
 if len(s)!=n{return false}
 for _,c:=range s {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// Audit requires two consecutively linked, unique original identities per
// independent lane and exact structural evidence placeholders. All hashes
// are caller supplied: structural success NEVER authenticates a receipt.
func Audit(c Candidate)(Report,error){
 var empty Report
 if c.Schema!=Schema||len(c.Wingless)!=2||len(c.Yggdrasil)!=2{return empty,ErrBlocked}
 seenOriginal:=map[string]bool{}
 seenExperiments:=map[string]bool{}
 seenReceipts:=map[string]bool{}
 check:=func(lane string,rows []Original)error{
  for i,r:=range rows {
   if r.Lane!=lane||r.ExperimentID==""||r.OriginalRunID==""||
    r.SuccessorExperimentID==""||r.SuccessorExperimentID==r.ExperimentID||
    !hexLower(r.SourceCommitSHA,40)||!hexLower(r.FrozenPlanSHA256,64)||
    !hexLower(r.StartReceiptSHA256,64)||!hexLower(r.TerminalReceiptSHA256,64)||
    !hexLower(r.IndependentReviewSHA256,64)||
    (r.Classification!="NEGATIVE"&&r.Classification!="POSITIVE"&&r.Classification!="MIXED"){
    return fmt.Errorf("%w: invalid %s record %d",ErrBlocked,lane,i)
   }
   if seenOriginal[r.OriginalRunID]||seenExperiments[r.ExperimentID]||
    seenReceipts[r.StartReceiptSHA256]||seenReceipts[r.TerminalReceiptSHA256]||
    seenReceipts[r.IndependentReviewSHA256]||
    r.StartReceiptSHA256==r.TerminalReceiptSHA256||
    r.StartReceiptSHA256==r.IndependentReviewSHA256||
    r.TerminalReceiptSHA256==r.IndependentReviewSHA256{return ErrBlocked}
   seenOriginal[r.OriginalRunID]=true;seenExperiments[r.ExperimentID]=true
   seenReceipts[r.StartReceiptSHA256]=true
   seenReceipts[r.TerminalReceiptSHA256]=true
   seenReceipts[r.IndependentReviewSHA256]=true
   if i>0&&rows[i-1].SuccessorExperimentID!=r.ExperimentID{return ErrBlocked}
  }
  return nil
 }
 if err:=check("Wingless",c.Wingless);err!=nil{return empty,err}
 if err:=check("Yggdrasil",c.Yggdrasil);err!=nil{return empty,err}
 for _,rows:=range [][]Original{c.Wingless,c.Yggdrasil}{
  last:=rows[len(rows)-1].SuccessorExperimentID
  if seenExperiments[last]{return empty,ErrBlocked}
  seenExperiments[last]=true
 }
 raw,err:=json.Marshal(c);if err!=nil{return empty,ErrBlocked}
 sum:=sha256.Sum256(raw)
 return Report{Schema:ReportSchema,Mode:"READ_ONLY_STRUCTURE_NOT_AUTHENTICATED_SCIENCE",
  CandidateSHA256:hex.EncodeToString(sum[:]),ConnectedOriginalsPerLane:2,
  StructuralContinuity:true,
  NextGate:"AUTHENTICATE_RECEIPTS_WITH_EXISTING_INDEPENDENT_AUTHORITY_AND_PROVE_UNATTENDED_FIRST_USE"},nil
}
