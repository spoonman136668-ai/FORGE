package sandboxworker
import(
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func TestRealWorkerProcessBoundaryNoRetry(t *testing.T){
 seed:=sha256.Sum256([]byte("sandbox worker test"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 expected:=workerreconcile.Expected{Lane:"Wingless",ExperimentID:"synthetic1",FrozenSHA256:strings.Repeat("a",64),
 IntentSHA256:strings.Repeat("b",64),OriginalRunID:"syntheticrun",WorkerID:"sandboxworker",OwnerEpoch:1,
 WorkerPublicKey:key.Public().(ed25519.PublicKey)}
 task:=Task{Expected:expected,OwnerID:"SYNTHETIC_TEST_OWNER",Epoch:1}
 dir:=t.TempDir()
 if err:=ExecuteOnce(context.Background(),dir,task,key);err!=nil{t.Fatal(err)}
 if err:=ExecuteOnce(context.Background(),dir,task,key);err==nil{t.Fatal("replayed original computation")}
 task.Expected.OriginalRunID="alternate"
 if err:=ExecuteOnce(context.Background(),dir,task,key);err==nil{t.Fatal("changed original ID replayed")}
}
func TestSandboxWorkerRejectsRealOwnership(t *testing.T){
 seed:=sha256.Sum256([]byte("sandbox worker deny"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 task:=Task{OwnerID:"CKB",Epoch:1,Expected:workerreconcile.Expected{Lane:"Wingless",ExperimentID:"x",OwnerEpoch:1,WorkerPublicKey:key.Public().(ed25519.PublicKey)}}
 if err:=ExecuteOnce(context.Background(),t.TempDir(),task,key);err==nil{t.Fatal("live owner permitted")}
}
