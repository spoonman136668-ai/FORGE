package watchdog

// RecoveryClass separates safe pre-original repair planning from scientific
// first-use ambiguity. None of these classes authorizes an automatic worker.
type RecoveryClass string
const (
 RecoverInfrastructure RecoveryClass="RECOVERABLE_PRE_FIRST_USE_INFRASTRUCTURE"
 RecoverQualification RecoveryClass="RECOVERABLE_PRE_FIRST_USE_QUALIFICATION"
 RecoverScientific RecoveryClass="SCIENTIFIC_RESULT_REQUIRES_SUCCESSOR"
 RecoverOriginalUnknown RecoveryClass="CONSUMED_OR_UNKNOWN_ORIGINAL_RECONCILE"
 RecoverIntegrity RecoveryClass="AUTHORITY_OR_PROVENANCE_FAIL_CLOSED"
)
type FailureKind string
const(
 FailureInfrastructure FailureKind="INFRASTRUCTURE"
 FailureQualification FailureKind="QUALIFICATION"
 FailureScientificNegative FailureKind="SCIENTIFIC_NEGATIVE"
 FailureScientificInconclusive FailureKind="SCIENTIFIC_INCONCLUSIVE"
 FailureOriginalUnknown FailureKind="ORIGINAL_EXECUTION_UNKNOWN"
 FailureAuthority FailureKind="AUTHORITY"
 FailureProvenance FailureKind="PROVENANCE"
)
type RecoveryAssessment struct {
 Incident Incident
 Failure FailureKind
 ReversiblePreFirstUseProven bool
 IndependentEvidenceAuthenticated bool
}
type RecoveryDecision struct{
 Class RecoveryClass
 OriginalReplayPermitted bool
 AutonomousRepairEligible bool
 IndependentSuccessorReviewRequired bool
}
func ClassifyFailure(a RecoveryAssessment)(RecoveryDecision,error){
 i:=a.Incident
 if (i.Lane!="Wingless"&&i.Lane!="Yggdrasil")||
 i.OriginalExperimentID==""||!validHash(i.JournalHeadSHA256)||i.OwnerEpoch==0{
  return RecoveryDecision{},ErrUnsafe
 }
 fail:=func()RecoveryDecision{return RecoveryDecision{Class:RecoverIntegrity}}
 if i.FirstUseRisk||a.Failure==FailureOriginalUnknown{
  return RecoveryDecision{Class:RecoverOriginalUnknown},nil
 }
 switch a.Failure {
 case FailureInfrastructure,FailureQualification:
  if !a.ReversiblePreFirstUseProven||!a.IndependentEvidenceAuthenticated{return fail(),nil}
  kind:=RecoverInfrastructure
  if a.Failure==FailureQualification{kind=RecoverQualification}
  return RecoveryDecision{Class:kind,AutonomousRepairEligible:true},nil
 case FailureScientificNegative,FailureScientificInconclusive:
  if !a.IndependentEvidenceAuthenticated{return fail(),nil}
  return RecoveryDecision{Class:RecoverScientific,IndependentSuccessorReviewRequired:true},nil
 case FailureAuthority,FailureProvenance:
  return fail(),nil
 default:
  return RecoveryDecision{},ErrUnsafe
 }
}
