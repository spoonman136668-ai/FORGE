// Package fsaservice contains source-only FSA HTTP boundaries.
// This endpoint is NOT registered, deployed, or an execution permit.
package fsaservice

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "io"
 "net/http"

 "github.com/spoonman136668-ai/forge/fsaepochstore"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/workerfence"
 "github.com/spoonman136668-ai/forge/workerlease"
)

const (
 StepRequestSchema="forge.fsa.step-consumption-request.v1"
 MaxStepRequestBytes=4096
)
var ErrStepServiceUnprovisioned=errors.New("FORGE_FSA_STEP_SERVICE_UNPROVISIONED")
// OriginalCustody is an independently authenticated all-lane consumed/active
// and immutable STARTED ledger attestor. This code DOES NOT implement one.
// It MUST NOT be backed by an untrusted worker or unauthenticated local map.
type OriginalCustody interface {
 ConfirmEligible(context.Context,workerfence.StepClaim)(bool,error)
}
type stepRequest struct {
 Schema string `json:"schema"`
 Claim workerfence.StepClaim `json:"claim"`
}
// StepConsumptionHandler is a negative-only synthetic HTTP boundary. The
// caller MUST separately provision mTLS with verified client certificates,
// independent archive/witness service, trusted clock, original custody and
// a qualified FSA authority; this source module launches NONE of them.
//
// A returned signed consumption receipt is NOT a permit to execute science,
// start an original, or perform an external side effect. Read/consume/read
// cannot atomically authorize a subsequent action.
func StepConsumptionHandler(pin fsaremote.Pin,
 readerSPKI,checkpointWriterSPKI,stepWorkerSPKI string,
 remote *fsaremote.Client,store *fsaepochstore.Store,
 custody OriginalCustody,clock fsaepochstore.TrustedClock,
 receiptPub ed25519.PublicKey)(http.Handler,error){
 scope,err:=newBound(pin,stepWorkerSPKI)
 if err!=nil||remote==nil||store==nil||custody==nil||clock==nil||
  !validHex(readerSPKI,64)||!validHex(checkpointWriterSPKI,64)||
  stepWorkerSPKI==readerSPKI||stepWorkerSPKI==checkpointWriterSPKI||
  readerSPKI==checkpointWriterSPKI||
  len(receiptPub)!=ed25519.PublicKeySize||
  bytes.Equal(receiptPub,pin.PublicKey)||bytes.Equal(receiptPub,pin.WitnessPublicKey){
  return nil,ErrStepServiceUnprovisioned
 }
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !scope.authenticated(r){deny(w,http.StatusUnauthorized);return}
  if r.URL==nil||r.URL.Path!="/v1/fsa/consume-step"{
   deny(w,http.StatusNotFound);return
  }
  if r.Method!=http.MethodPost{deny(w,http.StatusMethodNotAllowed);return}
  if r.URL.RawQuery!=""||r.URL.Fragment!=""||r.Header.Get("Content-Type")!="application/json"||
   r.ContentLength>MaxStepRequestBytes||r.Body==nil{
   deny(w,http.StatusBadRequest);return
  }
  raw,err:=io.ReadAll(io.LimitReader(r.Body,MaxStepRequestBytes+1))
  if err!=nil||len(raw)==0||len(raw)>MaxStepRequestBytes{
   deny(w,http.StatusBadRequest);return
  }
  var request stepRequest
  decoder:=json.NewDecoder(bytes.NewReader(raw))
  decoder.DisallowUnknownFields()
  if decoder.Decode(&request)!=nil||decoder.Decode(new(any))!=io.EOF{
   deny(w,http.StatusBadRequest);return
  }
  canonical,err:=json.Marshal(request)
  if err!=nil||!bytes.Equal(raw,canonical)||request.Schema!=StepRequestSchema{
   deny(w,http.StatusBadRequest);return
  }
  c:=request.Claim
  if c.Schema!=workerfence.StepSchema||c.ArchiveID!=pin.ArchiveID||
   c.OwnerEpoch!=pin.AuthorityEpoch{
   deny(w,http.StatusForbidden);return
  }
  anchor:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
   PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
   Sequence:c.AuthoritySequence,HeadSHA256:c.AuthorityHeadSHA256}
  lease:=workerlease.Lease{Lane:c.Lane,ExperimentID:c.OriginalID,
   IntentSHA256:c.IntentSHA256,OwnerID:c.OwnerID,OwnerEpoch:c.OwnerEpoch,
   WorkerID:c.WorkerID,LeaseSequence:c.LeaseSequence,ExpiresAtUnix:c.ExpiresAtUnix}
  ctx:=r.Context()
  now,err:=clock.NowUnix(ctx)
  if err!=nil||now==0||ctx.Err()!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  allowed,err:=custody.ConfirmEligible(ctx,c)
  if err!=nil||!allowed||ctx.Err()!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  if _,err:=workerfence.Observe(ctx,remote,anchor,lease,now);err!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  before,err:=store.Read(ctx)
  if err!=nil||before.OwnerID!=c.OwnerID||before.OwnerEpoch!=c.OwnerEpoch{
   deny(w,http.StatusServiceUnavailable);return
  }
  // The single append-only store checks current epoch and clock under its
  // own atomic in-process lock, and never grants execution.
  signed,err:=store.ConsumeOnce(ctx,c)
  if err!=nil{
   if errors.Is(err,fsaepochstore.ErrConsumed){deny(w,http.StatusConflict)
   }else{deny(w,http.StatusServiceUnavailable)}
   return
  }
  if !workerfence.VerifyStepReceipt(signed,c,receiptPub){
   deny(w,http.StatusServiceUnavailable);return
  }
  allowed,err=custody.ConfirmEligible(ctx,c)
  if err!=nil||!allowed||ctx.Err()!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  after,err:=store.Read(ctx)
  if err!=nil||after.OwnerID!=c.OwnerID||after.OwnerEpoch!=c.OwnerEpoch{
   deny(w,http.StatusServiceUnavailable);return
  }
  if _,err=workerfence.Observe(ctx,remote,anchor,lease,now);err!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  respond(w,struct{
   Schema string `json:"schema"`
   Receipt workerfence.SignedStepReceipt `json:"receipt"`
   ExecutionAuthorized bool `json:"execution_authorized"`
  }{Schema:StepRequestSchema,Receipt:signed,ExecutionAuthorized:false})
 }),nil
}
