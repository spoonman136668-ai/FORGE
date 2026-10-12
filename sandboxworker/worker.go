// Package sandboxworker exercises a real supervised worker execution boundary
// using a fixed synthetic computation. It has no live research dispatch route.
package sandboxworker

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "time"

 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

var ErrUnsafe=errors.New("FORGE_SANDBOX_WORKER_UNSAFE")
type Task struct{
 Expected workerreconcile.Expected
 OwnerID string
 Epoch uint64
}
// ExecuteOnce persists signed STARTED custody BEFORE any computation, then
// runs a bounded, deterministic test workload and persists TERMINAL. A crash,
// cancellation or ambiguous write never permits the same experiment to run again.
func ExecuteOnce(ctx context.Context,root string,task Task,key ed25519.PrivateKey)error{
 if ctx==nil||ctx.Err()!=nil||len(key)!=ed25519.PrivateKeySize||
 task.Expected.Lane!="Wingless"&&task.Expected.Lane!="Yggdrasil"||
 task.OwnerID!="SYNTHETIC_TEST_OWNER"||task.Epoch==0||
 task.Epoch!=task.Expected.OwnerEpoch||
 task.Expected.OriginalRunID==""||task.Expected.WorkerID==""||
 !task.Expected.WorkerPublicKey.Equal(key.Public()) {return ErrUnsafe}
 e:=task.Expected
 receipt:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:e.Lane,
  ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,
  IntentSHA256:e.IntentSHA256,OriginalRunID:e.OriginalRunID,
  WorkerID:e.WorkerID,OwnerEpoch:e.OwnerEpoch,Stage:"STARTED"}
 signedStart,err:=sign(receipt,key);if err!=nil{return err}
 fp,err:=workerreconcile.Fingerprint(signedStart);if err!=nil{return err}
 custody:=attemptjournal.Record{Schema:attemptjournal.Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,
  OriginalRunID:e.OriginalRunID,FrozenSHA256:e.FrozenSHA256,
  IntentSHA256:e.IntentSHA256,OwnerEpoch:e.OwnerEpoch,WorkerID:e.WorkerID,
  ReceiptSHA256:fp,State:"ORIGINAL_RISK_RECORDED"}
 if err:=attemptjournal.WriteOnce(root,custody);err!=nil{return err}
 if err:=writeExclusive(root,"start-"+fp+".json",signedStart);err!=nil{return ErrUnsafe}
 select{
 case <-ctx.Done():return ErrUnsafe
 default:
 }
 // Fixed synthetic computation is intentionally not an experiment plugin.
 // This is a process-level handshake, not autonomous scientific progression.
 evidence:=sha256.Sum256([]byte("FORGE-INACTIVE-SYNTHETIC-WORKER\n"+fp))
 receipt.Stage="TERMINAL";receipt.EvidenceSHA256=hex.EncodeToString(evidence[:])
 signedEnd,err:=sign(receipt,key);if err!=nil{return err}
 if err:=writeExclusive(root,"terminal-"+fp+".json",signedEnd);err!=nil{return ErrUnsafe}
 return nil
}
func sign(r workerreconcile.Receipt,key ed25519.PrivateKey)(workerreconcile.Signed,error){
 raw,err:=json.Marshal(r);if err!=nil{return workerreconcile.Signed{},err}
 sig:=ed25519.Sign(key,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...))
 return workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(sig)},nil
}
func writeExclusive(root,name string,record workerreconcile.Signed)error{
 b,err:=json.Marshal(record);if err!=nil{return err}
 f,err:=os.OpenFile(filepath.Join(root,name),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return err}
 b=append(b,'\n')
 n,err:=f.Write(b)
 if err==nil&&n!=len(b){err=ErrUnsafe}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil{return err}
 if closeErr!=nil{return closeErr}
 return nil
}
// BoundedContext is used by the standalone synthetic worker supervisor.
func BoundedContext(ctx context.Context)(context.Context,context.CancelFunc){
 return context.WithTimeout(ctx,5*time.Second)
}
