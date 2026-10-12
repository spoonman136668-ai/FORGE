package subprocesssupervisor
import(
 "context"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "testing"
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
