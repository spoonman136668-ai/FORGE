// Package custodyreconcile requires a durable original-attempt record
// before accepting signed worker evidence. It never starts workers.
package custodyreconcile

import (
 "errors"

 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/workerboundary"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

var ErrUntrusted = errors.New("FORGE_CUSTODY_WORKER_RECONCILIATION_BLOCKED")

// Inspect requires the exact local write-once STARTED receipt fingerprint,
// the authenticated original owner epoch, and the worker's signed terminal.
// A missing or corrupt custody record cannot be repaired by a fresh run ID.
func Inspect(root string, x workerboundary.Input, custody attemptjournal.Record)(workerboundary.Disposition,error){
 if x.Started==nil{return workerboundary.NoLaunch,ErrUntrusted}
 if custody.State!="ORIGINAL_RISK_RECORDED" ||
 custody.Schema!=attemptjournal.Schema ||
 custody.Lane!=x.Lane ||
 custody.ExperimentID!=x.ExperimentID ||
 custody.OriginalRunID!=x.ExpectedWorker.OriginalRunID ||
 custody.FrozenSHA256!=x.ExpectedWorker.FrozenSHA256 ||
 custody.IntentSHA256!=x.ExpectedWorker.IntentSHA256 ||
 custody.OwnerEpoch!=x.OwnerEpoch ||
 custody.WorkerID!=x.ExpectedWorker.WorkerID{
  return workerboundary.NoLaunch,ErrUntrusted
 }
 fingerprint,err:=workerreconcile.Fingerprint(*x.Started)
 if err!=nil||fingerprint!=custody.ReceiptSHA256{
  return workerboundary.NoLaunch,ErrUntrusted
 }
 if _,err=attemptjournal.Read(root,custody);err!=nil{
  return workerboundary.NoLaunch,ErrUntrusted
 }
 outcome,err:=workerboundary.Inspect(x)
 if err!=nil{return workerboundary.NoLaunch,err}
 return outcome,nil
}
