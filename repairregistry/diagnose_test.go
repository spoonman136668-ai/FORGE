package repairregistry
import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestExactDiagnosticReferenceOnly(t *testing.T){
 dir:=t.TempDir()
 r:=sample(t)
 if err:=RecordOnce(dir,r);err!=nil{t.Fatal(err)}
 q:=Query{Repository:r.Repository,Component:r.Component,FailureSignature:r.FailureSignature,Scope:r.Scope,Preconditions:r.Preconditions}
 matches,err:=Diagnose(dir,q)
 if err!=nil||len(matches)!=1||matches[0].Disposition!=AdvisoryOnly{t.Fatalf("matching evidence: %v %+v",err,matches)}
 q.Preconditions=[]string{"weaker conditions"}
 matches,err=Diagnose(dir,q)
 if err!=nil||len(matches)!=0{t.Fatalf("scope drift: %v %+v",err,matches)}
 q.Preconditions=r.Preconditions
 if err:=os.WriteFile(filepath.Join(dir,strings.Repeat("f",64)+".json"),[]byte("{corrupted"),0600);err!=nil{t.Fatal(err)}
 if matches,err=Diagnose(dir,q);err==nil||matches!=nil{t.Fatal("corrupt registry silently ignored")}
}
func TestUnresolvedCannotMatch(t *testing.T){
 r:=sample(t)
 r.Status="UNRESOLVED"
 var err error;r.RecordSHA256,err=Digest(r);if err!=nil{t.Fatal(err)}
 dir:=t.TempDir();if err:=RecordOnce(dir,r);err!=nil{t.Fatal(err)}
 m,err:=Diagnose(dir,Query{Repository:r.Repository,Component:r.Component,FailureSignature:r.FailureSignature,Scope:r.Scope,Preconditions:r.Preconditions})
 if err!=nil||len(m)!=0{t.Fatal("unresolved repair offered",err,m)}
}
