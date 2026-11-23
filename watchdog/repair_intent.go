package watchdog

// RepairIntent is a deterministic, non-executing plan. Nothing in this
// package launches an agent, edits code, extends scientific budgets, or
// exercises CKB scientific authority.
type RepairIntent struct{
 IncidentKey string
 Lane string
 ExperimentID string
 FrozenHeadSHA256 string
 OwnerEpoch uint64
 Failure FailureKind
 Scope string
 RequiresIndependentRequalification bool
}
func PlanRepair(a RecoveryAssessment, scope string)(RepairIntent,error){
 d,err:=ClassifyFailure(a)
 if err!=nil||!d.AutonomousRepairEligible||d.OriginalReplayPermitted||
  !a.ReversiblePreFirstUseProven||!a.IndependentEvidenceAuthenticated||
  scope==""||len(scope)>128 {
  return RepairIntent{},ErrUnsafe
 }
 for _,c:=range scope{
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'||c=='.'){
   return RepairIntent{},ErrUnsafe
  }
 }
 i:=a.Incident
 return RepairIntent{IncidentKey:IncidentKey(i),Lane:i.Lane,
  ExperimentID:i.OriginalExperimentID,FrozenHeadSHA256:i.JournalHeadSHA256,
  OwnerEpoch:i.OwnerEpoch,Failure:a.Failure,Scope:scope,
  RequiresIndependentRequalification:true},nil
}
