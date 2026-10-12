package repairregistry
import(
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func sample(t *testing.T)Incident{
 t.Helper()
 r:=Incident{Schema:Schema,ID:"RFIX-LINUX-ISOLATION-1",Repository:"spoonman136668-ai/FORGE",
 Component:"public-isolation",FailureSignature:"CI_PUBLIC_ISOLATION_EXEC_COMMAND",
 Cause:"Allowlisted synthetic process test changed without policy count update",
 RepairCommit:strings.Repeat("a",40),FailedRun:"38309699707",QualifiedRun:"38310139710",
 Scope:"FORGE qualify.yml public isolation synthetic subprocess tests",
 Preconditions:[]string{"Exact subprocess file inventory independently reviewed","No live execution or CKB authority"},
 Prohibited:[]string{"Do not allow arbitrary process execution","Never waive scientific or final regression controls"},
 Status:"QUALIFIED_REPAIR",EvidenceSHA256:strings.Repeat("b",64)}
 var err error;r.RecordSHA256,err=Digest(r);if err!=nil{t.Fatal(err)};return r
}
func TestRegistryExactBoundedMatchAndTamper(t *testing.T){
 r:=sample(t)
 if err:=Verify(r);err!=nil{t.Fatal(err)}
 if !Match(r,r.Repository,r.Component,r.FailureSignature,r.Scope,r.Preconditions){t.Fatal("valid exact match missed")}
 if Match(r,r.Repository,r.Component,r.FailureSignature,r.Scope,[]string{"weaker"}){t.Fatal("precondition drift allowed")}
 r.Status="FAILED_REPAIR"
 if Verify(r)==nil{t.Fatal("post-hoc mutation accepted")}
}
func TestWriteOnceCanonicalAndFailClosed(t *testing.T){
 r:=sample(t);dir:=t.TempDir()
 if err:=RecordOnce(dir,r);err!=nil{t.Fatal(err)}
 path:=filepath.Join(dir,r.RecordSHA256+".json")
 got,err:=ReadFile(path);if err!=nil||!rEqual(got,r){t.Fatal("round trip",err)}
 if err:=RecordOnce(dir,r);err==nil{t.Fatal("duplicate immutable record overwritten")}
 if err:=os.WriteFile(path,[]byte("{\"schema\":\"forged\"}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=ReadFile(path);err==nil{t.Fatal("tampered evidence accepted")}
}
func rEqual(a,b Incident)bool{return a.RecordSHA256==b.RecordSHA256&&a.ID==b.ID}
