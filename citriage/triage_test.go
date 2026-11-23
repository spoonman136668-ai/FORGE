package citriage
import(
 "strings"
 "testing"
)
func known()Failure{return Failure{
 Repository:"spoonman136668-ai/FORGE",RunID:38309699707,
 CommitSHA:strings.Repeat("a",40),JobName:"linux",
 FailedStep:"Public isolation",WorkflowName:"FORGE public Linux and Windows qualification",
}}
func TestFrozenFailureClassOnly(t *testing.T){
 base:=known()
 q,err:=QueryFor(base);if err!=nil||q.FailureSignature!="CI_PUBLIC_ISOLATION_EXEC_COMMAND"{t.Fatal(q,err)}
 for _,mutate:=range []func(*Failure){
  func(f *Failure){f.JobName="windows"},
  func(f *Failure){f.FailedStep="Tests, race, vet and build"},
  func(f *Failure){f.FailedStep="Public isolation (similar)"},
  func(f *Failure){f.CommitSHA="wrong"},
  func(f *Failure){f.RunID=0},
  func(f *Failure){f.Repository="untrusted/FORGE"},
 }{
  f:=base;mutate(&f)
  if _,err:=QueryFor(f);err==nil{t.Fatalf("untrusted failure accepted %+v",f)}
 }
}
func TestMissingHistoricalRegistryNeverInventsRepair(t *testing.T){
 if _,err:=Diagnose(t.TempDir(),known());err!=nil{t.Fatal(err)}
 if _,err:=Diagnose("/nonexistent/forge-repair-registry",known());err==nil{
  t.Fatal("unavailable history treated as a matching repair")
 }
}
