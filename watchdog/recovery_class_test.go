package watchdog
import("strings";"testing")
func TestRecoveryClassificationSeparatesRepairFromConsumedOriginal(t *testing.T){
 incident:=Incident{Lane:"Wingless",OriginalExperimentID:"existing",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:4,Action:DiagnoseOrchestration}
 for _,f:=range []FailureKind{FailureInfrastructure,FailureQualification}{
  d,e:=ClassifyFailure(RecoveryAssessment{Incident:incident,Failure:f,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true})
  if e!=nil||!d.AutonomousRepairEligible||d.OriginalReplayPermitted{t.Fatal(d,e)}
 }
 incident.FirstUseRisk=true
 d,e:=ClassifyFailure(RecoveryAssessment{Incident:incident,Failure:FailureInfrastructure,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true})
 if e!=nil||d.Class!=RecoverOriginalUnknown||d.AutonomousRepairEligible{t.Fatal(d,e)}
 incident.FirstUseRisk=false
 d,e=ClassifyFailure(RecoveryAssessment{Incident:incident,Failure:FailureScientificNegative,IndependentEvidenceAuthenticated:true})
 if e!=nil||!d.IndependentSuccessorReviewRequired||d.OriginalReplayPermitted{t.Fatal(d,e)}
 d,e=ClassifyFailure(RecoveryAssessment{Incident:incident,Failure:FailureInfrastructure})
 if e!=nil||d.Class!=RecoverIntegrity{t.Fatal(d,e)}
}
