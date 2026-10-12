package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "testing"

 "github.com/spoonman136668-ai/forge/subprocesssupervisor"
)

// Tests the actual supervisor CLI -> two real OS worker processes -> signed
// custody/recovery path on native Linux and Windows, not just a package mock.
func TestSupervisorStandaloneEndToEnd(t *testing.T){
 if testing.Short(){t.Skip("requires separate executable builds")}
 goExe,err:=exec.LookPath("go");if err!=nil{t.Skip("Go compiler unavailable")}
 root,err:=filepath.Abs("../..");if err!=nil{t.Fatal(err)}
 dir:=t.TempDir();suffix:="";if runtime.GOOS=="windows"{suffix=".exe"}
 worker:=filepath.Join(dir,"worker"+suffix)
 supervisor:=filepath.Join(dir,"supervisor"+suffix)
 for _,build:=range []struct{path,target string}{{worker,"./cmd/forge-sandbox-worker"},{supervisor,"./cmd/forge-synthetic-supervisor"}}{
  cmd:=exec.Command(goExe,"build","-o",build.path,build.target);cmd.Dir=root
  if out,err:=cmd.CombinedOutput();err!=nil{t.Fatalf("build %s: %v %s",build.target,err,out)}
 }
 raw,err:=os.ReadFile(worker);if err!=nil{t.Fatal(err)}
 h:=sha256.Sum256(raw)
 destination:=filepath.Join(dir,"forge-synthetic-processes")
 args:=[]string{"--synthetic-only","--worker-executable",worker,"--worker-sha256",hex.EncodeToString(h[:]),"--new-dir",destination}
 command:=exec.Command(supervisor,args...)
 result,err:=command.Output();if err!=nil{t.Fatalf("standalone worker process failed: %v",err)}
 var report subprocesssupervisor.Result
 if err:=json.Unmarshal(result,&report);err!=nil{t.Fatal(err)}
 if !report.WinglessVerified||!report.YggdrasilVerified||report.RealScientificCycles!=0{t.Fatalf("unverified execution: %+v",report)}
 // Restart after consumed originals must not retry even with same executable.
 if err:=exec.Command(supervisor,args...).Run();err==nil{t.Fatal("standalone supervisor replayed consumed originals")}
 // An incorrect executable digest must be rejected without touching the new root.
 wrong:=filepath.Join(t.TempDir(),"forge-synthetic-processes")
 args[len(args)-3]=hex.EncodeToString(make([]byte,32))
 args[len(args)-1]=wrong
 if err:=exec.Command(supervisor,args...).Run();err==nil{t.Fatal("standalone supervisor accepted bad binary hash")}
 if _,err:=os.Stat(wrong);!os.IsNotExist(err){t.Fatal("bad hash created state directory")}
}
