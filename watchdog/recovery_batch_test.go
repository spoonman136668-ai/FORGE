package watchdog
import("strings";"testing")
func TestRecoveryBatchPreservesAllIncidentCategories(t *testing.T){
 makeI:=func(lane,id string)Incident{return Incident{Lane:lane,OriginalExperimentID:id,JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:8,Action:DiagnoseOrchestration}}
 a:=AssessedIncident{Assessment:RecoveryAssessment{Incident:makeI("Wingless","w1"),Failure:FailureInfrastructure,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true},RepairScope:"worker_config"}
 b:=AssessedIncident{Assessment:RecoveryAssessment{Incident:makeI("Yggdrasil","y1"),Failure:FailureScientificNegative,IndependentEvidenceAuthenticated:true}}
 c:=AssessedIncident{Assessment:RecoveryAssessment{Incident:makeI("Wingless","w2"),Failure:FailureOriginalUnknown}}
 d:=AssessedIncident{Assessment:RecoveryAssessment{Incident:makeI("Yggdrasil","y2"),Failure:FailureProvenance}}
 r,err:=PrepareRecoveryBatch([]AssessedIncident{a,b,c,d})
 if err!=nil||len(r.Repairs)!=1||len(r.Scientific)!=1||len(r.Reconcile)!=1||len(r.Blocked)!=1{t.Fatal(r,err)}
 if _,err:=PrepareRecoveryBatch([]AssessedIncident{a,a});err==nil{t.Fatal("duplicate repair entered batch")}
 a.RepairScope="../escape"
 if _,err:=PrepareRecoveryBatch([]AssessedIncident{a,b});err==nil{t.Fatal("unbounded repair accepted")}
}
