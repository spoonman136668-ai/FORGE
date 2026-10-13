package watchdog

import "errors"

// RecoveryBatch binds a fresh incident batch to bounded, non-executing repair
// intents. It preserves every nonrepair incident for original reconciliation
// or independent scientific successor qualification.
type RecoveryBatch struct {
 Repairs []RepairIntent
 Reconcile []Incident
 Scientific []Incident
 Blocked []Incident
}
var ErrBatchUnsafe=errors.New("FORGE_RECOVERY_BATCH_NOT_QUALIFIED")
type AssessedIncident struct {
 Assessment RecoveryAssessment
 RepairScope string
}
// PrepareRecoveryBatch fails atomically on duplicate incidents, untrusted
// observations and unauthorized scopes. It cannot silently drop a blocked or
// scientifically negative incident.
func PrepareRecoveryBatch(items []AssessedIncident)(RecoveryBatch,error){
 out:=RecoveryBatch{Repairs:[]RepairIntent{},Reconcile:[]Incident{},Scientific:[]Incident{},Blocked:[]Incident{}}
 seen:=map[string]bool{}
 if len(items)>1024{return RecoveryBatch{},ErrBatchUnsafe}
 for _,item:=range items{
  incident:=item.Assessment.Incident
  key:=IncidentKey(incident)
  if seen[key]{return RecoveryBatch{},ErrBatchUnsafe}
  seen[key]=true
  decision,err:=ClassifyFailure(item.Assessment)
  if err!=nil{return RecoveryBatch{},errors.Join(ErrBatchUnsafe,err)}
  switch decision.Class{
  case RecoverInfrastructure,RecoverQualification:
   intent,err:=PlanRepair(item.Assessment,item.RepairScope)
   if err!=nil{return RecoveryBatch{},errors.Join(ErrBatchUnsafe,err)}
   out.Repairs=append(out.Repairs,intent)
  case RecoverOriginalUnknown:
   out.Reconcile=append(out.Reconcile,incident)
  case RecoverScientific:
   out.Scientific=append(out.Scientific,incident)
  case RecoverIntegrity:
   out.Blocked=append(out.Blocked,incident)
  default:return RecoveryBatch{},ErrBatchUnsafe
  }
 }
 return out,nil
}
