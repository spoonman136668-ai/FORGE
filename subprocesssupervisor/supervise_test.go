package subprocesssupervisor
import(
 "context"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "testing"
 "os/exec"
 "runtime"
)
func TestSubprocessSupervisorRejectsUntrustedBinaryAndReplay(t *testing.T){
 dir:=t.TempDir()
 exe:=filepath.Join(dir,"worker")
 if err:=os.WriteFile(exe,[]byte("not an executable"),0700);err!=nil{t.Fatal(err)}
 wrong:=hex.EncodeToString(make([]byte,32))
 root:=filepath.Join(dir,"forge-synthetic-processes")
 if _,err:=Run(context.Background(),exe,wrong,root);err==nil{t.Fatal("untrusted executable accepted")}
 if _,err:=os.Stat(root);!os.IsNotExist(err){t.Fatal("invalid binary created directory")}
 bytes,err:=os.ReadFile(exe);if err!=nil{t.Fatal(err)}
 sum:=sha256.Sum256(bytes)
 if _,err:=Run(context.Background(),exe,hex.EncodeToString(sum[:]),root);err==nil{t.Fatal("bad worker accepted")}
 if _,err:=Run(context.Background(),exe,hex.EncodeToString(sum[:]),root);err==nil{t.Fatal("uncertain lane retried")}
}
func TestInvalidSupervisorRootFailsClosed(t *testing.T){
 if _,err:=Run(context.Background(),"/bad/file","",t.TempDir());err==nil{t.Fatal("invalid trust admitted")}
}

func TestEndToEndSeparateWorkerProcesses(t *testing.T){
 if testing.Short(){t.Skip("requires building a separate pinned synthetic worker")}
 goBinary,err:=exec.LookPath("go");if err!=nil{t.Skip("Go compiler missing")}
 repoRoot,err:=filepath.Abs("..");if err!=nil{t.Fatal(err)}
 binary:=filepath.Join(t.TempDir(),"forge-synthetic-worker")
 if runtime.GOOS=="windows"{binary+=".exe"}
 build:=exec.Command(goBinary,"build","-o",binary,"./cmd/forge-sandbox-worker")
 build.Dir=repoRoot
 if raw,err:=build.CombinedOutput();err!=nil{t.Fatalf("worker build: %v %s",err,raw)}
 data,err:=os.ReadFile(binary);if err!=nil{t.Fatal(err)}
 digest:=sha256.Sum256(data)
 root:=filepath.Join(t.TempDir(),"forge-synthetic-processes")
 outcome,err:=Run(context.Background(),binary,hex.EncodeToString(digest[:]),root)
 if err!=nil{t.Fatal(err)}
 if !outcome.WinglessVerified||!outcome.YggdrasilVerified||
 outcome.RealScientificCycles!=0{t.Fatalf("false real execution: %+v",outcome)}
 if _,err:=Run(context.Background(),binary,hex.EncodeToString(digest[:]),root);err==nil{
  t.Fatal("completed original replayed after restart")
 }
}
