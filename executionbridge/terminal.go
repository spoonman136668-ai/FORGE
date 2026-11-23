package executionbridge

import (
 "context"
 "errors"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

// TerminalEvidence is independently authenticated scientific custody, not
// an inference from GitHub workflow status or a worker's exit code.
type TerminalEvidence struct {
 Lane string
 OriginalRunID string
 EvidenceSHA256 string
 ClassificationSHA256 string
 SourceHeadSHA256 string
 IndependentlyAuthenticated bool
}
type TerminalWitness interface {
 VerifyTerminal(context.Context,TerminalEvidence)(bool,error)
}
type NextAction string
const(
 WaitForReconciliation NextAction="QUARANTINE_ORIGINAL_NO_REPLAY"
 AuthenticateEvidence NextAction="AUTHENTICATE_TERMINAL_EVIDENCE"
 IndependentSuccessor NextAction="INDEPENDENT_SUCCESSOR_QUALIFICATION"
)
// EvaluateOriginal refuses to advance an original based only on an
// authenticated terminal worker receipt. Evidence/classification must be
// independently witnessed before successor qualification is even considered.
func EvaluateOriginal(ctx context.Context,receipts ReceiptWitness,science TerminalWitness,expected workerreconcile.Expected,terminal *TerminalEvidence)(NextAction,error){
 if ctx==nil||ctx.Err()!=nil||receipts==nil||science==nil||
 expected.OriginalRunID==""||expected.OwnerEpoch==0{return WaitForReconciliation,ErrBlocked}
 state,err:=ReconcileOriginal(ctx,receipts,expected.OriginalRunID,expected)
 if err!=nil{return WaitForReconciliation,err}
 if state!=workerreconcile.Terminal{return WaitForReconciliation,nil}
 if terminal==nil{return AuthenticateEvidence,nil}
 if terminal.Lane!=expected.Lane||terminal.OriginalRunID!=expected.OriginalRunID||
 !terminal.IndependentlyAuthenticated||!validDigest(terminal.EvidenceSHA256)||
 !validDigest(terminal.ClassificationSHA256)||!validDigest(terminal.SourceHeadSHA256){
 return WaitForReconciliation,ErrBlocked
 }
 ok,err:=science.VerifyTerminal(ctx,*terminal)
 if err!=nil||!ok{return WaitForReconciliation,errors.Join(ErrBlocked,err)}
 // Qualification of a separate immutable successor remains outside this
 // function. In particular this never retries or executes the original.
 return IndependentSuccessor,nil
}
