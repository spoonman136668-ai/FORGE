package executionbridge

import (
 "context"
 "errors"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

// ReceiptWitness must be independently provisioned. This interface only
// checks original attempt evidence; it never grants an original-start retry.
type ReceiptWitness interface{
 LoadStarted(context.Context,string)(*workerreconcile.Signed,error)
 LoadTerminal(context.Context,string)(*workerreconcile.Signed,error)
}

// ReconcileOriginal follows durable original-attempt identity, not worker
// process status or green CI. A missing or ambiguous receipt is never proof
// that first-use is available. There is no dispatch API in this package.
func ReconcileOriginal(ctx context.Context,w ReceiptWitness,id string,expected workerreconcile.Expected)(workerreconcile.Disposition,error){
 if ctx==nil||ctx.Err()!=nil||w==nil||id==""||
  id!=expected.OriginalRunID||expected.OwnerEpoch==0||
  (expected.Lane!="Wingless"&&expected.Lane!="Yggdrasil"){
  return workerreconcile.Unknown,ErrBlocked
 }
 started,err:=w.LoadStarted(ctx,id)
 if err!=nil{return workerreconcile.Unknown,errors.Join(ErrBlocked,err)}
 terminal,err:=w.LoadTerminal(ctx,id)
 if err!=nil{return workerreconcile.Unknown,errors.Join(ErrBlocked,err)}
 disposition,err:=workerreconcile.Reconcile(expected,started,terminal)
 if err!=nil{return workerreconcile.Unknown,errors.Join(ErrBlocked,err)}
 return disposition,nil
}
