package watchdog
import("strings";"testing")
func TestSealedRecoveryRequiresPersistedIncidentIdentity(t *testing.T){
 dir:=t.TempDir()
 i:=Incident{Lane:"Wingless",OriginalExperimentID:"existing_1",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:12,Action:DiagnoseOrchestration}
 chain,err:=AppendIncidentChain(nil,i,zeroHead);if err!=nil{t.Fatal(err)}
 if err=ExportIncidentChain(dir,chain);err!=nil{t.Fatal(err)}
 item:=AssessedIncident{Assessment:RecoveryAssessment{Incident:i,Failure:FailureInfrastructure,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true},RepairScope:"bounded_fix"}
 m,err:=SealRecoveryManifest(dir,chain,[]AssessedIncident{item})
 if err!=nil||len(m.Repairs)!=1||m.ManifestSHA256==""{t.Fatal(m,err)}
 if _,err=SealRecoveryManifest(dir,chain,[]AssessedIncident{item});err==nil{t.Fatal("sealed manifest overwritten")}
 unknown:=i;unknown.OriginalExperimentID="never_observed"
 item.Assessment.Incident=unknown
 if _,err=SealRecoveryManifest(dir,chain,[]AssessedIncident{item});err==nil{t.Fatal("unrecorded incident promoted")}
}
