package optimizerbridge

// The operational shadow admission step requires BOTH already-authenticated
// Cloudflare export receipts and separately signed, source-linked assignment
// audits. Neither is an execution or independent scientific authority.
import "errors"

var ErrShadowAuditIncomplete = errors.New("FORGE_OPTIMIZER_SHADOW_AUDIT_NOT_QUALIFIED")

// HistoricalComparison is descriptive only: both selectors use the SAME
// frozen historical screens. Score differences are not future task gains.
type HistoricalComparison struct {
 Lane string `json:"lane"`
 BaselineFinalists []string `json:"baseline_finalists"`
 ParetoFinalists []string `json:"pareto_finalists"`
 SharedFinalists int `json:"shared_finalists"`
 BaselineHistoricalScreenScore int64 `json:"baseline_historical_screen_score"`
 ParetoHistoricalScreenScore int64 `json:"pareto_historical_screen_score"`
 BaselineReservedSealedCompute int64 `json:"baseline_reserved_sealed_compute"`
 ParetoReservedSealedCompute int64 `json:"pareto_reserved_sealed_compute"`
 OutcomeEvidenceFullyPreserved bool `json:"outcome_evidence_fully_preserved"`
 ProspectiveGeneralizationEstablished bool `json:"prospective_generalization_established"`
 CausalImprovementEstablished bool `json:"causal_improvement_established"`
}

func historicalComparison(e LaneEvidence, report LaneResult)(HistoricalComparison,error) {
 var zero HistoricalComparison
 if e.Lane!=report.Lane || len(report.BaselineFinalists)==0 ||
  len(report.ParetoFinalists)==0 || report.HistoricalArchiveCount!=len(e.Portfolio.Candidates) ||
  report.BaselineSealedComputeReserved>e.Portfolio.MaxSealedCompute ||
  report.ParetoSealedComputeReserved>e.Portfolio.MaxSealedCompute {
  return zero,ErrShadowAuditIncomplete
 }
 scores:=map[string]int64{}
 for _,c:=range e.Portfolio.Candidates {
  if _,exists:=scores[c.ID];exists{return zero,ErrShadowAuditIncomplete}
  scores[c.ID]=c.Score
 }
 chosen:=map[string]bool{}
 out:=HistoricalComparison{Lane:e.Lane,
  BaselineFinalists:append([]string(nil),report.BaselineFinalists...),
  ParetoFinalists:append([]string(nil),report.ParetoFinalists...),
  BaselineReservedSealedCompute:report.BaselineSealedComputeReserved,
  ParetoReservedSealedCompute:report.ParetoSealedComputeReserved,
  OutcomeEvidenceFullyPreserved:true,
 }
 for _,id:=range report.BaselineFinalists{
  score,ok:=scores[id];if !ok||chosen[id]{return zero,ErrShadowAuditIncomplete}
  out.BaselineHistoricalScreenScore+=score
  chosen[id]=true
 }
 paretoSeen:=map[string]bool{}
 for _,id:=range report.ParetoFinalists{
  score,ok:=scores[id];if !ok||paretoSeen[id]{return zero,ErrShadowAuditIncomplete}
  out.ParetoHistoricalScreenScore+=score
  if chosen[id]{out.SharedFinalists++}
  paretoSeen[id]=true
 }
 return out,nil
}

// EvaluatePinnedExportWithAudits is the REQUIRED path for cloud-export CLI
// shadow admission. An unsigned/missing audit, a reused auditor trust identity,
// cross-lane duplicated assignment, or any evidence drift fails ATOMICALLY.
// Only the preexisting read-only selection code executes; no worker launch.
func EvaluatePinnedExportWithAudits(
 signed SignedExport,trust ExternalTrust,raw [2][]byte,pins []LanePins,
 audits [2]SignedSelectionAudit,auditPins [2]SelectionAuditPin,
)(ExportReview,error){
 var zero ExportReview
 evidence,err:=verifyPinnedExportInputs(signed,trust,raw,pins)
 if err!=nil{return zero,err}
 if len(pins)!=2 ||
  auditPins[0].IndependentAuditorPublicKeyHex==auditPins[1].IndependentAuditorPublicKeyHex ||
  auditPins[0].IndependentAuditorPublicKeyHex==pins[1].IndependentEd25519PublicKeyHex ||
  auditPins[1].IndependentAuditorPublicKeyHex==pins[0].IndependentEd25519PublicKeyHex ||
  pins[0].IndependentEd25519PublicKeyHex==pins[1].IndependentEd25519PublicKeyHex {
  return zero,ErrShadowAuditIncomplete
 }
 // Separate every observed assignment across the two original research lanes.
 assignments:=map[string]bool{}
 receipts:=map[string]bool{}
 var reviews [2]SelectionAuditReview
 for i,lane:=range []string{"Wingless","Yggdrasil"} {
  review,auditErr:=VerifySelectionAudit(evidence[i],pins[i],audits[i],auditPins[i],
   trust.CustodianEd25519PublicKeyHex)
  if auditErr!=nil||review.Lane!=lane||review.EntriesCrossChecked==0||
   !review.SignedClaimsConsistent||review.ActualRandomizationIndependentlyDemonstrated||
   review.ProspectiveScienceAuthorized||review.ScientificImprovementEstablished {
   return zero,ErrShadowAuditIncomplete
  }
  for _,entry:=range audits[i].Audit.Entries {
   if assignments[entry.AssignmentEventSHA256]||receipts[entry.ReceiptSHA256]{
    return zero,ErrShadowAuditIncomplete
   }
   assignments[entry.AssignmentEventSHA256]=true
   receipts[entry.ReceiptSHA256]=true
  }
  reviews[i]=review
 }
 // No adaptive/expensive optimizer work before both signed audits pass.
 report,err:=EvaluatePair(evidence[:],pins)
 if err!=nil{return zero,ErrShadowAuditIncomplete}
 if report.ScientificAccepted||report.DispatchAuthorized||report.ScientificImprovementEstablished||
  report.FirstUseConsumed||report.ScienceOriginalsExecuted!=0||len(report.Lanes)!=2{
  return zero,ErrShadowAuditIncomplete
 }
 verified:=ExportReview{
  Schema:"forge.optimizer.cloud-export-review.v1",
  Mode:"EXTERNAL_EXPORT_AND_SIGNED_ASSIGNMENT_CLAIMS_SHADOW_ONLY",
  ManifestSHA256:trust.ManifestSHA256,
  SourceDigestAndCustodySignatureVerified:true,
  Shadow:report,
 }
 for i:=range evidence {
  comparison,compareErr:=historicalComparison(evidence[i],report.Lanes[i])
  if compareErr!=nil{return zero,ErrShadowAuditIncomplete}
  verified.SelectionAudits=append(verified.SelectionAudits,reviews[i])
  verified.HistoricalComparisons=append(verified.HistoricalComparisons,comparison)
 }
 return verified,nil
}
