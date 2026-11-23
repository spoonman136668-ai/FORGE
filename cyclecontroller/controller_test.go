package cyclecontroller

import (
 "context"
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "strings"
 "sync"
 "testing"
)

var buildOnce sync.Once
var buildPath,buildSHA string
var buildError error
func testBinary(t *testing.T)(string,string){
 t.Helper()
 buildOnce.Do(func(){
  folder,err:=os.MkdirTemp("","forge-cycle-worker-bin-")
  if err!=nil{buildError=err;return}
  binary:="forge-sandbox-worker"
  if runtime.GOOS=="windows"{binary+=".exe"}
  buildPath=filepath.Join(folder,binary)
  cmd:=exec.Command("go","build","-o",buildPath,"./cmd/forge-sandbox-worker")
  cmd.Dir=".."
  out,err:=cmd.CombinedOutput()
  if err!=nil{buildError=errors.New(string(out)+": "+err.Error());return}
  buildSHA,buildError=digestBinary(buildPath)
 })
 if buildError!=nil{t.Fatal(buildError)}
 return buildPath,buildSHA
}
func runTwo(t *testing.T,root string)(Report,string,string){
 t.Helper()
 worker,digest:=testBinary(t)
 plan:=strings.Repeat("e",64)
 report,err:=Run(context.Background(),worker,digest,plan,root,2,0)
 if err!=nil{t.Fatal("two verified consecutive parallel lane generations",err)}
 if report.Schema!=Schema||report.Mode!="DURABLE_PARALLEL_SYNTHETIC_NO_SCIENCE"||
  report.Completed!=2||report.WinglessCycles!=2||report.YggdrasilCycles!=2||
  report.OriginalScientificRuns!=0||report.ScientificExecutionAuthorized||
  report.AcceptedRefMutation||!hex64(report.LastTerminalSHA256){
  t.Fatalf("operational synthetic proof lost important safety: %+v",report)
 }
 return report,worker,digest
}
func TestParallelTwoLaneDurableSuccessionAndIdempotentRestart(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 first,worker,digest:=runTwo(t,root)
 snapshot,err:=Run(context.Background(),worker,digest,strings.Repeat("e",64),root,2,2)
 if err!=nil||snapshot!=first{t.Fatalf("completed originals were replayed or lost: %v %+v",err,snapshot)}
 items,err:=os.ReadDir(root)
 if err!=nil||len(items)!=7{t.Fatalf("unexpected checkpoint content %d %v",len(items),err)}
 for _,lane:=range []string{"wingless","yggdrasil"}{
  for gen:=uint64(1);gen<=2;gen++{
   p:=filepath.Join(root,cycleName(gen),"forge-synthetic-processes",lane,"forge-synthetic-worker")
   entries,err:=os.ReadDir(p)
   if err!=nil||len(entries)!=3{t.Fatalf("missing signed synthetic start/terminal lane %s: %v",lane,err)}
  }
 }
}
func TestControllerRefusesChangedFrozenInputsAndWorkerIdentity(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 _,worker,digest:=runTwo(t,root)
 if _,err:=Run(context.Background(),worker,digest,strings.Repeat("d",64),root,2,2);
  !errors.Is(err,ErrQuarantine){t.Fatal("postfreeze plan change admitted",err)}
 // An externally unrelated worker SHA must reject without any original.
 if _,err:=Run(context.Background(),worker,strings.Repeat("f",64),strings.Repeat("e",64),root,2,2);
  !errors.Is(err,ErrBlocked){t.Fatal("changed executable admitted",err)}
}
func TestCrashAfterDurableIntentIsQuarantinedWithoutNewWorker(t *testing.T){
 worker,digest:=testBinary(t)
 root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 plan:=strings.Repeat("e",64)
 first,err:=Run(context.Background(),worker,digest,plan,root,1,0)
 if err!=nil{t.Fatal(err)}
 seq:=uint64(2)
 id:=Identity{Schema:IdentitySchema,WorkerSHA256:digest,FrozenPlanSHA256:plan,
  LaneNames:[2]string{"Wingless","Yggdrasil"}}
 encoded,_:=canonical(id)
 if err:=os.Mkdir(filepath.Join(root,cycleName(seq)),0700);err!=nil{t.Fatal(err)}
 intent:=Intent{Schema:IntentSchema,Sequence:seq,
  PriorTerminalSHA256:first.LastTerminalSHA256,IdentitySHA256:hash(encoded)}
 if err:=writeOnce(filepath.Join(root,cycleName(seq)+".intent.json"),intent);err!=nil{t.Fatal(err)}
 if _,err:=Run(context.Background(),worker,digest,plan,root,2,1);
  !errors.Is(err,ErrQuarantine){t.Fatal("missing terminal treated as retryable",err)}
 if _,err:=os.Lstat(filepath.Join(root,"controller.active"));err!=nil{
  t.Fatal("interrupted original did not retain sticky lock",err)
 }
 if _,err:=Run(context.Background(),worker,digest,plan,root,2,1);
  !errors.Is(err,ErrQuarantine){t.Fatal("repeat attempt bypassed sticky quarantine",err)}
 if _,err:=os.Lstat(filepath.Join(root,cycleName(seq),"forge-synthetic-processes"));!os.IsNotExist(err){
  t.Fatal("worker ran after uncommitted intent",err)
 }
}
func TestControllerDetectsTamperedEvidenceAndIndependentFloor(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 _,worker,digest:=runTwo(t,root)
 p:=filepath.Join(root,"generation-0002.terminal.json")
 if err:=os.WriteFile(p,[]byte("{}\n"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Run(context.Background(),worker,digest,strings.Repeat("e",64),root,2,2);
  !errors.Is(err,ErrQuarantine){t.Fatal("local terminal tampering recovered as success",err)}
}
func TestControllerNeverExecutesWithoutValidBoundedSyntheticParameters(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 for _,p:=range []struct{name string;root string;cycles,floor uint64;plan string}{
  {"zero generations",root,0,0,strings.Repeat("e",64)},
  {"capacity widened",root,5,0,strings.Repeat("e",64)},
  {"nonmatching floor",root,1,2,strings.Repeat("e",64)},
  {"unknown plan",root,1,0,""},
  {"foreign root",filepath.Join(t.TempDir(),"CKB-plane"),1,0,strings.Repeat("e",64)},
 }{
  t.Run(p.name,func(t *testing.T){
   if _,err:=Run(context.Background(),"/missing/binary",strings.Repeat("f",64),p.plan,p.root,p.cycles,p.floor);err==nil{
    t.Fatal("unqualified cycle request launched")
   }
  })
 }
 if _,err:=os.Stat(root);!os.IsNotExist(err){t.Fatal("invalid request changed state",err)}
}
