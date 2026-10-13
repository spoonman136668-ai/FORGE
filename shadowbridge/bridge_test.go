package shadowbridge
import(
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/watchdog"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
)
func TestEndToEndShadowRepairIntakeAndNoOriginalDispatch(t *testing.T){
 dir:=t.TempDir()
 inc:=watchdog.Incident{Lane:"Wingless",OriginalExperimentID:"existing_w",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:9,Action:watchdog.DiagnoseOrchestration}
 chain,err:=watchdog.AppendIncidentChain(nil,inc,strings.Repeat("0",64));if err!=nil{t.Fatal(err)}
 if err=watchdog.ExportIncidentChain(dir,chain);err!=nil{t.Fatal(err)}
 item:=watchdog.AssessedIncident{Assessment:watchdog.RecoveryAssessment{Incident:inc,Failure:watchdog.FailureInfrastructure,ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true},RepairScope:"bounded_config"}
 manifest,err:=watchdog.SealRecoveryManifest(dir,chain,[]watchdog.AssessedIncident{item});if err!=nil{t.Fatal(err)}
 manifestPath:=filepath.Join(dir,"shadow-recovery-"+manifest.ManifestSHA256+".json")
 outboxDir:=filepath.Join(t.TempDir(),"inactive-outbox")
 first,err:=Stage(manifestPath,outboxDir,manifest,chain)
 if err!=nil||len(first)!=1{t.Fatal(first,err)}
 second,err:=Stage(manifestPath,outboxDir,manifest,chain)
 if err!=nil||len(second)!=1||second[0]!=first[0]{t.Fatal(second,err)}
 rows,err:=shadowoutbox.Load(outboxDir);if err!=nil||len(rows)!=1||rows[0].Lane!="Wingless"{t.Fatal(rows,err)}
 manifest.Repairs[0].Scope="unqualified"
 if _,err:=Stage(manifestPath,outboxDir,manifest,chain);err==nil{t.Fatal("tampered plan admitted")}
}
func TestRejectsFakeSealedEvidence(t *testing.T){
 m:=watchdog.RecoveryManifest{Schema:"forge.shadow.recovery-manifest.v1",ManifestSHA256:strings.Repeat("f",64),IncidentChainHeadSHA256:strings.Repeat("0",64)}
 if _,err:=Prepare(m,nil);err==nil{t.Fatal("fake manifest accepted")}
 _=json.Valid([]byte("{}"));_ = os.ErrNotExist
}
