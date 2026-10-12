// Package syntheticsupervisor inspects crash recovery of a synthetic
// worker without redispatch. No production experiment authority is present.
package syntheticsupervisor

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
var ErrUnsafe=errors.New("FORGE_SYNTHETIC_SUPERVISOR_UNSAFE")
type State string
const(
 Unknown State="QUARANTINED_NO_REPLAY"
 Started State="STARTED_NO_REPLAY"
 Terminal State="TERMINAL_REVIEW_REQUIRED"
)
// Recover reads the exact write-once custody and verifies signed receipts.
// It cannot infer that first-use is unused even if every file is absent.
// A signed terminal is evidence for review, never authorization to rerun.
func Recover(root string,expected attemptjournal.Record,worker workerreconcile.Expected)(State,error){
 if expected.Schema!=attemptjournal.Schema||
 expected.Lane!=worker.Lane||expected.ExperimentID!=worker.ExperimentID||
 expected.OriginalRunID!=worker.OriginalRunID||expected.FrozenSHA256!=worker.FrozenSHA256||
 expected.IntentSHA256!=worker.IntentSHA256||expected.OwnerEpoch!=worker.OwnerEpoch||
 expected.WorkerID!=worker.WorkerID||expected.State!="ORIGINAL_RISK_RECORDED"{
  return Unknown,ErrUnsafe
 }
 if _,err:=attemptjournal.Read(root,expected);err!=nil{return Unknown,fmt.Errorf("%w: original attempt indeterminate",ErrUnsafe)}
 start,err:=readSigned(root,"start-"+expected.ReceiptSHA256+".json")
 if err!=nil{return Unknown,ErrUnsafe}
 if err:=workerreconcile.Verify(start,worker);err!=nil||start.Receipt.Stage!="STARTED"{
  return Unknown,ErrUnsafe
 }
 fingerprint,err:=workerreconcile.Fingerprint(start)
 if err!=nil||fingerprint!=expected.ReceiptSHA256{return Unknown,ErrUnsafe}
 end,err:=readSigned(root,"terminal-"+expected.ReceiptSHA256+".json")
 if errors.Is(err,os.ErrNotExist){return Started,nil}
 if err!=nil{return Unknown,ErrUnsafe}
 outcome,err:=workerreconcile.Reconcile(worker,&start,&end)
 if err!=nil||outcome!=workerreconcile.Terminal{return Unknown,ErrUnsafe}
 return Terminal,nil
}
func readSigned(root,name string)(workerreconcile.Signed,error){
 path:=filepath.Join(root,name)
 info,err:=os.Lstat(path)
 if err!=nil{return workerreconcile.Signed{},err}
 if !info.Mode().IsRegular()||info.Size()>8192||info.Size()<2{return workerreconcile.Signed{},ErrUnsafe}
 raw,err:=os.ReadFile(path)
 if err!=nil{return workerreconcile.Signed{},err}
 var signed workerreconcile.Signed
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&signed);err!=nil{return workerreconcile.Signed{},ErrUnsafe}
 canonical,err:=json.Marshal(signed)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n')){return workerreconcile.Signed{},ErrUnsafe}
 return signed,nil
}
