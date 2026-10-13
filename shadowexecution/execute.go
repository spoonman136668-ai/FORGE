// Package shadowexecution combines durable original custody with FORGE's
// FIXED SYNTHETIC worker. No real science, task plugin or authority transfer.
package shadowexecution

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "errors"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/durableauthority"
 "github.com/spoonman136668-ai/forge/sandboxworker"
)
var ErrUnsafe=errors.New("FORGE_SHADOW_EXECUTION_BLOCKED")
var ErrOriginalRisk=errors.New("FORGE_SHADOW_ORIGINAL_ALREADY_RESERVED_NO_REPLAY")

type Task struct {
 Grant durableauthority.Grant
 Worker sandboxworker.Task
 Root string
}
// RunOnce seals irreversible original custody BEFORE creating the worker
// directory. An interrupted or failed synthetic worker can never reissue this
// original. The fixed sandboxworker cannot execute real research.
func RunOnce(ctx context.Context,store *durableauthority.Store,task Task,workerKey ed25519.PrivateKey)(string,error){
 if ctx==nil||ctx.Err()!=nil||store==nil||len(workerKey)!=ed25519.PrivateKeySize||
  !filepath.IsAbs(task.Root)||filepath.Base(filepath.Clean(task.Root))!="forge-synthetic-worker"||
  task.Grant.OwnerID!="SYNTHETIC_TEST_OWNER"||
  task.Worker.OwnerID!="SYNTHETIC_TEST_OWNER"||
  (task.Grant.Lane!="Wingless"&&task.Grant.Lane!="Yggdrasil")||
  task.Worker.Expected.Lane!=task.Grant.Lane||
  task.Worker.Expected.ExperimentID!=task.Grant.OriginalID||
  task.Worker.Expected.OriginalRunID!=task.Grant.OriginalID||
  task.Worker.Expected.FrozenSHA256!=task.Grant.FrozenSHA256||
  task.Worker.Expected.IntentSHA256!=task.Grant.IntentSHA256||
  task.Worker.Expected.OwnerEpoch!=task.Grant.OwnerEpoch||
  task.Worker.Expected.WorkerID==""||
  !bytes.Equal(task.Worker.Expected.WorkerPublicKey,workerKey.Public().(ed25519.PublicKey))||
  task.Worker.Epoch!=task.Grant.OwnerEpoch{return "",ErrUnsafe}
 // This is an actual durable file write with signed provenance and no-replay
 // protection. A successful write remains only a synthetic-work permit.
 custody,err:=store.Reserve(task.Grant)
 if err!=nil{return "",err}
 if err:=os.Mkdir(task.Root,0700);err!=nil{return custody,errors.Join(ErrOriginalRisk,err)}
 if err:=sandboxworker.ExecuteOnce(ctx,task.Root,task.Worker,workerKey);err!=nil{
  return custody,errors.Join(ErrOriginalRisk,err)
 }
 return custody,nil
}
