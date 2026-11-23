package watchdog

import("strings";"testing")
func TestRepairPlanOnlyForProvenReversibleFailures(t *testing.T){
 inc:=Incident{Lane:"Wingless",OriginalExperimentID:"existing_1",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:7,Action:DiagnoseOrchestration}
 a:=RecoveryAssessment{Incident:inc,Failure:FailureInfrastructure,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true}
 p,err:=PlanRepair(a,"bounded_worker_config")
 if err!=nil||p.IncidentKey!=IncidentKey(inc)||!p.RequiresIndependentRequalification{t.Fatal(p,err)}
 a.Incident.FirstUseRisk=true
 if _,err:=PlanRepair(a,"bounded_worker_config");err==nil{t.Fatal("first-use plan accepted")}
 a.Incident.FirstUseRisk=false;a.ReversiblePreFirstUseProven=false
 if _,err:=PlanRepair(a,"bounded_worker_config");err==nil{t.Fatal("unproven preflight accepted")}
 a.ReversiblePreFirstUseProven=true
 if _,err:=PlanRepair(a,"../unsafe");err==nil{t.Fatal("unsafe scope accepted")}
 a.Failure=FailureScientificNegative
 if _,err:=PlanRepair(a,"bounded_worker_config");err==nil{t.Fatal("scientific negative became engineering repair")}
}
