package syntheticsupervisor
import(
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/sandboxworker"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func setup(t *testing.T)(string,attemptjournal.Record,workerreconcile.Expected,ed25519.PrivateKey){
 t.Helper()
 sum:=sha256.Sum256([]byte("supervisor recovery test"))
 key:=ed25519.NewKeyFromSeed(sum[:])
 expected:=workerreconcile.Expected{Lane:"Wingless",ExperimentID:"synthetic1",OriginalRunID:"original1",
 FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),WorkerID:"sandboxworker",OwnerEpoch:2,
 WorkerPublicKey:key.Public().(ed25519.PublicKey)}
 dir:=t.TempDir()
 task:=sandboxworker.Task{Expected:expected,OwnerID:"SYNTHETIC_TEST_OWNER",Epoch:2}
 if err:=sandboxworker.ExecuteOnce(context.Background(),dir,task,key);err!=nil{t.Fatal(err)}
 entries,err:=os.ReadDir(dir);if err!=nil{t.Fatal(err)}
 var custody attemptjournal.Record
 for _,e:=range entries{
  if strings.HasPrefix(e.Name(),"start-")||strings.HasPrefix(e.Name(),"terminal-"){continue}
  raw,err:=os.ReadFile(filepath.Join(dir,e.Name()));if err!=nil{t.Fatal(err)}
  if err:=json.Unmarshal(raw,&custody);err!=nil{t.Fatal(err)}
 }
 return dir,custody,expected,key
}
func TestRecoveryCompletesWithoutRedispatch(t *testing.T){
 root,custody,expected,_:=setup(t)
 if got,err:=Recover(root,custody,expected);err!=nil||got!=Terminal{t.Fatal(got,err)}
 if err:=os.Remove(filepath.Join(root,"terminal-"+custody.ReceiptSHA256+".json"));err!=nil{t.Fatal(err)}
 if got,err:=Recover(root,custody,expected);err!=nil||got!=Started{t.Fatal("silent terminal must remain consumed",got,err)}
 if err:=os.Remove(filepath.Join(root,"start-"+custody.ReceiptSHA256+".json"));err!=nil{t.Fatal(err)}
 if got,err:=Recover(root,custody,expected);err==nil||got!=Unknown{t.Fatal("missing start must quarantine",got,err)}
}
func TestRecoveryDoesNotTrustMissingOrDriftedOriginal(t *testing.T){
 root,custody,expected,_:=setup(t)
 changed:=expected;changed.OwnerEpoch++
 if got,err:=Recover(root,custody,changed);err==nil||got!=Unknown{t.Fatal("stale epoch accepted",got,err)}
 changed=expected;changed.Lane="Yggdrasil"
 if got,err:=Recover(root,custody,changed);err==nil||got!=Unknown{t.Fatal("cross-lane accepted",got,err)}
 if got,err:=Recover(t.TempDir(),custody,expected);err==nil||got!=Unknown{t.Fatal("missing custody treated as unused",got,err)}
}
