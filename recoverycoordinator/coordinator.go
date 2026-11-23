// Package recoverycoordinator links verified originals to bounded decisions.
// It is an inactive deterministic seam, not a scientific worker launcher.
package recoverycoordinator

import (
 "context"
 "errors"
 "github.com/spoonman136668-ai/forge/executionbridge"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
var ErrBlocked=errors.New("FORGE_RECOVERY_COORDINATOR_BLOCKED")
type Decision string
const (
 Quarantine Decision="QUARANTINE_NO_REPLAY"
 ReviewEvidence Decision="REVIEW_INDEPENDENT_EVIDENCE"
 QualifySuccessor Decision="QUALIFY_NEW_SUCCESSOR"
)
type Dependencies struct{
 Receipts executionbridge.ReceiptWitness
 Science executionbridge.AttestedTerminalWitness
}
type Request struct{
 Expected workerreconcile.Expected
 Evidence *executionbridge.TerminalEvidence
}
// Evaluate reconciles the exact original worker receipt and independent
// science witness before even proposing a new successor qualification.
func Evaluate(ctx context.Context,deps Dependencies,req Request)(Decision,error){
 if ctx==nil||ctx.Err()!=nil||deps.Receipts==nil||
 req.Expected.OriginalRunID==""||
 (req.Expected.Lane!="Wingless"&&req.Expected.Lane!="Yggdrasil")||
 req.Expected.OwnerEpoch==0{return Quarantine,ErrBlocked}
 if req.Evidence==nil{
  state,err:=executionbridge.ReconcileOriginal(ctx,deps.Receipts,req.Expected.OriginalRunID,req.Expected)
  if err!=nil{return Quarantine,err}
  if state==workerreconcile.Terminal{return ReviewEvidence,nil}
  return Quarantine,nil
 }
 state,err:=executionbridge.EvaluateBoundOriginal(ctx,deps.Receipts,deps.Science,req.Expected,*req.Evidence)
 if err!=nil{return Quarantine,err}
 if state!=executionbridge.IndependentSuccessor{return Quarantine,nil}
 return QualifySuccessor,nil
}
