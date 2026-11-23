package historycoverage
import (
 "encoding/json"
 "fmt"
 "strings"
 "testing"
)
func mkRun(lane string,id int)([]byte){
 return []byte(fmt.Sprintf(`{"id":%d,"run_attempt":1,"head_sha":"%s","status":"completed","conclusion":"success","path":".github/workflows/qualify-test.yml","repository":{"full_name":"spoonman136668-ai/%s"}}`+"\n",id,strings.Repeat("a",40),lane))
}
func mkArtifact(id,run int,name string,expired bool,digest string)([]byte){
 return []byte(fmt.Sprintf(`{"id":%d,"name":%q,"expired":%v,"digest":%q,"size_in_bytes":100,"workflow_run":{"id":%d,"head_sha":"%s"}}`+"\n",id,name,expired,digest,run,strings.Repeat("a",40)))
}
func TestVisibleMetadataAndFalseAuthority(t *testing.T){
 digest:="sha256:"+strings.Repeat("b",64)
 a:=Source{Lane:"Wingless",Runs:mkRun("Wingless",9),Artifacts:mkArtifact(99,9,"W-original-negative",false,digest),DeclaredRuns:1,DeclaredArtifacts:1}
 b:=Source{Lane:"Yggdrasil",Runs:mkRun("Yggdrasil",8),Artifacts:mkArtifact(98,8,"Y-original",true,digest),DeclaredRuns:1,DeclaredArtifacts:1}
 report,err:=Build(a,b);if err!=nil{t.Fatal(err)}
 if !report.GithubAccessibleSnapshotReconciled||report.FullHistoricalScientificCoverageVerified||report.LongTermOriginalBytesRetained||report.IndependentScientificCustodyQualified||report.NewScientificExecution||report.AcceptedRefMutation{t.Fatal("unauthorized custody claims")}
 if len(report.OriginalObservations)!=2||report.Wingless.OriginalUnverifiedAvailableCount!=1||report.Yggdrasil.OriginalExpiredCount!=1{t.Fatalf("%+v",report)}
 raw,_:=json.Marshal(report);if strings.Contains(string(raw),"SCIENTIFIC_ACCEPTED"){t.Fatal("science accepted")}
}
func TestCountsAndDrift(t *testing.T){
 digest:="sha256:"+strings.Repeat("b",64)
 a:=Source{Lane:"Wingless",Runs:mkRun("Wingless",9),Artifacts:mkArtifact(99,9,"original",false,digest),DeclaredRuns:2,DeclaredArtifacts:1}
 b:=Source{Lane:"Yggdrasil",Runs:mkRun("Yggdrasil",8),Artifacts:mkArtifact(98,8,"original",false,digest),DeclaredRuns:1,DeclaredArtifacts:1}
 r,err:=Build(a,b);if err!=nil||r.GithubAccessibleSnapshotReconciled{t.Fatal("pagination failure not exposed")}
 a.DeclaredRuns=1
 a.Artifacts=mkArtifact(99,777,"original",false,digest)
 r,err=Build(a,b);if err!=nil||r.GithubAccessibleSnapshotReconciled||r.Wingless.ArtifactOrphanCount!=1{t.Fatal("orphan not exposed")}
 a.Artifacts=mkArtifact(99,9,"original",false,"")
 r,err=Build(a,b);if err!=nil||r.Wingless.OriginalMissingDigestCount!=1{t.Fatal("missing digest not exposed")}
 a.Artifacts=append(a.Artifacts,a.Artifacts...)
 if _,err=Build(a,b);err==nil{t.Fatal("duplicate artifact not rejected")}
 a.Artifacts=mkArtifact(99,9,"original",false,digest)
 a.Runs=[]byte(`{"id":9,"run_attempt":1,"head_sha":"INVALID","repository":{"full_name":"spoonman136668-ai/Wingless"}}`+"\n")
 if _,err=Build(a,b);err==nil{t.Fatal("invalid source accepted")}
}

func TestConcurrentPaginationDuplicatesFailClosedWithoutCrashing(t *testing.T){
 digest:="sha256:"+strings.Repeat("b",64)
 a:=Source{Lane:"Wingless",Runs:append(mkRun("Wingless",9),mkRun("Wingless",9)...),Artifacts:mkArtifact(99,9,"W-original",false,digest),DeclaredRuns:1,DeclaredArtifacts:1}
 b:=Source{Lane:"Yggdrasil",Runs:mkRun("Yggdrasil",8),Artifacts:mkArtifact(98,8,"Y-original",false,digest),DeclaredRuns:1,DeclaredArtifacts:1}
 report,err:=Build(a,b)
 if err!=nil{t.Fatal(err)}
 if report.GithubAccessibleSnapshotReconciled||report.Wingless.RunPaginationDuplicateCount!=1||report.Wingless.ObservedRunCount!=1||report.FullHistoricalScientificCoverageVerified{t.Fatal("duplicate incorrectly accepted as complete")}
 a.Runs=append(mkRun("Wingless",9),[]byte(`{"id":9,"run_attempt":2,"head_sha":"`+strings.Repeat("a",40)+`","repository":{"full_name":"spoonman136668-ai/Wingless"}}`+"\n")...)
 if _,err=Build(a,b);err==nil{t.Fatal("conflicting duplicate accepted")}
}
