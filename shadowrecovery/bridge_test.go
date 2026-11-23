package shadowrecovery
import(
 "path/filepath"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
 "github.com/spoonman136668-ai/forge/watchdog"
)
func example()Request{return Request{
 Assessment:watchdog.RecoveryAssessment{
  Incident:watchdog.Incident{Lane:"Wingless",OriginalExperimentID:"existing_w",
   JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:3,
   Action:watchdog.DiagnoseOrchestration},
  Failure:watchdog.FailureInfrastructure,
  ReversiblePreFirstUseProven:true,IndependentEvidenceAuthenticated:true},
 IncidentSHA256:strings.Repeat("b",64),RecoveryManifestSHA256:strings.Repeat("c",64),Scope:"bounded_repair",
}}
func TestQualifiedShadowRecoveryEnqueueIsIdempotent(t *testing.T){
 r:=example();dir:=filepath.Join(t.TempDir(),"outbox")
 a,e:=EnqueueCandidate(dir,r);if e!=nil{t.Fatal(e)}
 b,e:=EnqueueCandidate(dir,r);if e!=nil||a!=b{t.Fatal(b,e)}
 entries,e:=shadowoutbox.Load(dir)
 if e!=nil||len(entries)!=1||entries[0].FirstUseRisk||!entries[0].RequiresRequalification{t.Fatal(entries,e)}
}
func TestFirstUseAndScienceNeverBecomeRepairActions(t *testing.T){
 r:=example();r.Assessment.Incident.FirstUseRisk=true
 if _,e:=Candidate(r);e==nil{t.Fatal("consumed original enqueued")}
 r=example();r.Assessment.Failure=watchdog.FailureScientificNegative
 if _,e:=Candidate(r);e==nil{t.Fatal("science negative enqueued as engineering repair")}
 r=example();r.Assessment.IndependentEvidenceAuthenticated=false
 if _,e:=Candidate(r);e==nil{t.Fatal("unverified evidence enqueued")}
 r=example();r.Assessment.ReversiblePreFirstUseProven=false
 if _,e:=Candidate(r);e==nil{t.Fatal("original not proven reversible")}
}
