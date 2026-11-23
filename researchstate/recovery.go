package researchstate

// Recovery is a non-executing assessment of an authenticated lifecycle
// snapshot. The caller must independently verify durable writer ownership,
// high-water witness, original-start receipts and complete evidence before
// undertaking any next action. These dispositions never confer authority.
type Recovery string
const (
 RecoverReversible Recovery="REQUALIFY_REVERSIBLE_ONLY"
 RecoverReconcileFirstUse Recovery="RECONCILE_FIRST_USE_NO_REPLAY"
 RecoverEvidence Recovery="VERIFY_AND_CLASSIFY_SEALED_EVIDENCE"
 RecoverSuccessor Recovery="QUALIFY_NEW_SUCCESSOR_ONLY"
 RecoverTerminal Recovery="TERMINAL_NO_REPLAY"
 RecoverBlocked Recovery="BLOCKED_PROVENANCE_OR_AUTHORITY"
)
func ClassifyRecovery(j Journal,lane,id string)(Recovery,error){
 phase,ok,err:=Status(j,lane,id)
 if err!=nil{return "",err}
 if !ok{return RecoverBlocked,nil}
 switch phase{
 case Proposed,Preregistered,Qualifying,Qualified,Blocked:
  return RecoverReversible,nil
 case Authorized,Executing,Quarantined:
  // Even AUTHORIZED may have attempted irreversible dispatch before a
  // crash. Never automatically replay it or infer unused first-use.
  return RecoverReconcileFirstUse,nil
 case EvidenceSealed:
  return RecoverEvidence,nil
 case Classified,SuccessorReady:
  return RecoverSuccessor,nil
 case Failed:
  return RecoverTerminal,nil
 default:
  return RecoverBlocked,nil
 }
}
