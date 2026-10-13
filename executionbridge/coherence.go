package executionbridge

import (
 "context"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
// EvaluateBoundOriginal links an independently signed terminal scientific
// witness to the exact authenticated terminal worker receipt, not merely to
// caller-supplied matching strings or a green workflow status.
func EvaluateBoundOriginal(ctx context.Context,receipts ReceiptWitness,science AttestedTerminalWitness,expected workerreconcile.Expected,evidence TerminalEvidence)(NextAction,error){
 if ctx==nil||ctx.Err()!=nil||receipts==nil||
  evidence.Lane!=expected.Lane||evidence.OriginalRunID!=expected.OriginalRunID||
  science.Expected.Lane!=expected.Lane||science.Expected.OriginalRunID!=expected.OriginalRunID||
  science.Expected.OwnerEpoch!=expected.OwnerEpoch{
  return WaitForReconciliation,ErrBlocked
 }
 terminal,err:=receipts.LoadTerminal(ctx,expected.OriginalRunID)
 if err!=nil||terminal==nil{return WaitForReconciliation,ErrBlocked}
 if err:=workerreconcile.Verify(*terminal,expected);err!=nil||terminal.Receipt.Stage!="TERMINAL"||
  terminal.Receipt.EvidenceSHA256!=evidence.EvidenceSHA256||
  science.Signed.WorkerEvidenceSHA256!=terminal.Receipt.EvidenceSHA256{
  return WaitForReconciliation,ErrBlocked
 }
 return EvaluateOriginal(ctx,receipts,science,expected,&evidence)
}
