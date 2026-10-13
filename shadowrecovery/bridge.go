// Package shadowrecovery connects authenticated watchdog classification to
// the existing immutable shadow outbox. It never dispatches science or repairs.
package shadowrecovery
import(
 "errors"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
 "github.com/spoonman136668-ai/forge/watchdog"
)
var ErrUnsafe=errors.New("FORGE_SHADOW_RECOVERY_NOT_ELIGIBLE")
type Request struct {
 Assessment watchdog.RecoveryAssessment
 IncidentSHA256 string
 RecoveryManifestSHA256 string
 Scope string
}
func Candidate(r Request)(shadowoutbox.Entry,error){
 i:=r.Assessment.Incident
 d,err:=watchdog.ClassifyFailure(r.Assessment)
 if err!=nil||!d.AutonomousRepairEligible||
  d.OriginalReplayPermitted||i.FirstUseRisk||
  (d.Class!=watchdog.RecoverInfrastructure&&d.Class!=watchdog.RecoverQualification){
  return shadowoutbox.Entry{},ErrUnsafe
 }
 return shadowoutbox.Entry{
  Schema:shadowoutbox.Schema,Lane:i.Lane,OriginalID:i.OriginalExperimentID,
  IncidentSHA256:r.IncidentSHA256,RecoveryManifestSHA256:r.RecoveryManifestSHA256,
  Scope:r.Scope,FirstUseRisk:false,RequiresRequalification:true,
 },nil
}
// EnqueueCandidate only writes a content-addressed inactive recommendation.
// Duplicate content is idempotent. No worker or repair actions are invoked.
func EnqueueCandidate(dir string,r Request)(string,error){
 e,err:=Candidate(r);if err!=nil{return "",err}
 return shadowoutbox.Enqueue(dir,e)
}
