package subprocesssupervisor
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "testing"
)
// When one existing lane's original execution is already indeterminate, the
// supervisor must stop before launching a different lane or replaying the
// first. A new process cannot reset local custody ambiguity.
func TestPartialLaneCrashNeverDispatchesOtherLane(t *testing.T){
 goBin,err:=exec.LookPath("go");if err!=nil{t.Skip("Go compiler unavailable")}
 root,err:=filepath.Abs("..");if err!=nil{t.Fatal(err)}
 binary:=filepath.Join(t.TempDir(),"synthetic-worker")
 if runtime.GOOS=="windows"{binary+=".exe"}
 cmd:=exec.Command(goBin,"build","-o",binary,"./cmd/forge-sandbox-worker")
 cmd.Dir=root
 if out,err:=cmd.CombinedOutput();err!=nil{t.Fatalf("worker build: %v %s",err,out)}
 data,err:=os.ReadFile(binary);if err!=nil{t.Fatal(err)}
 sum:=sha256.Sum256(data)
 dir:=filepath.Join(t.TempDir(),"forge-synthetic-processes")
 lane:=filepath.Join(dir,"wingless")
 if err:=os.MkdirAll(filepath.Join(lane,"forge-synthetic-worker"),0700);err!=nil{t.Fatal(err)}
 if _,err:=Run(context.Background(),binary,hex.EncodeToString(sum[:]),dir);err==nil{
  t.Fatal("pre-existing uncertain Wingless lane allowed new execution")
 }
 if _,err:=os.Stat(filepath.Join(dir,"yggdrasil"));!os.IsNotExist(err){
  t.Fatal("Yggdrasil execution attempted after Wingless uncertainty")
 }
 if _,err:=Run(context.Background(),binary,hex.EncodeToString(sum[:]),dir);err==nil{
  t.Fatal("process restart retried indeterminate original")
 }
}
