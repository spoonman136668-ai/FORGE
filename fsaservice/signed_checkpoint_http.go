package fsaservice

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "net/http"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsatrust"
)

// SignedCheckpointSchema is distinct from the legacy unsigned anchor-only
// CAS wire format. It is not a worker dispatch or scientific admission grant.
const SignedCheckpointSchema="forge.fsa.signed-checkpoint-request.v1"
const maxSignedCheckpointRequestBytes=4096

type signedCheckpointRequest struct {
 Schema string `json:"schema"`
 SignedCheckpoint fsahead.SignedHead `json:"signed_checkpoint"`
}

// SignedCheckpointHandler is a source-only writer handler. It is NOT
// registered by the existing read-only handlers, and this package does
// not provision a listener, signer, writer credentials or durable authority.
//
// Before use it requires a distinct operator-pinned *writer* client SPKI,
// independently authenticated and provisioned backing stores and a qualified
// CheckpointGate. For now only synthetic qualification fixtures exist.
// The SignedHead alone never authorizes new science or first-use execution.
func SignedCheckpointHandler(pin fsaremote.Pin,readerClientSPKI,writerClientSPKI string,
 gate *CheckpointGate)(http.Handler,error){
 boundWriter,err:=newBound(pin,writerClientSPKI)
 if err!=nil||gate==nil||!validHex(readerClientSPKI,64)||
  writerClientSPKI==readerClientSPKI||
  gate.identity.ArchiveID!=pin.ArchiveID||
  gate.identity.KeyID!=pin.KeyID||
  gate.identity.AuthorityEpoch!=pin.AuthorityEpoch||
  !bytes.Equal(gate.identity.PublicKey,pin.PublicKey)||
  gate.bindingSHA256!=pin.BindingSHA256{
  return nil,ErrUnprovisioned
 }
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !boundWriter.authenticated(r){deny(w,http.StatusUnauthorized);return}
  if r.URL==nil||r.URL.Path!="/v1/fsa/signed-checkpoint"{
   deny(w,http.StatusNotFound);return
  }
  if r.Method!=http.MethodPost{deny(w,http.StatusMethodNotAllowed);return}
  if r.URL.RawQuery!=""||r.URL.Fragment!=""||
   r.Header.Get("Content-Type")!="application/json"||
   r.ContentLength>maxSignedCheckpointRequestBytes||r.Body==nil{
   deny(w,http.StatusBadRequest);return
  }
  raw,err:=io.ReadAll(io.LimitReader(r.Body,maxSignedCheckpointRequestBytes+1))
  if err!=nil||len(raw)==0||len(raw)>maxSignedCheckpointRequestBytes{
   deny(w,http.StatusBadRequest);return
  }
  decoder:=json.NewDecoder(bytes.NewReader(raw))
  decoder.DisallowUnknownFields()
  var request signedCheckpointRequest
  if decoder.Decode(&request)!=nil||decoder.Decode(new(any))!=io.EOF{
   deny(w,http.StatusBadRequest);return
  }
  canonical,err:=json.Marshal(request)
  if err!=nil||!bytes.Equal(raw,canonical)||request.Schema!=SignedCheckpointSchema{
   deny(w,http.StatusBadRequest);return
  }
  committed,err:=gate.AdvanceSignedCheckpoint(r.Context(),request.SignedCheckpoint)
  if err!=nil{
   if errors.Is(err,fsatrust.ErrConflict){
    deny(w,http.StatusConflict)
   }else{
    // May have committed. Never invite an automatic retry.
    deny(w,http.StatusServiceUnavailable)
   }
   return
  }
  respond(w,struct{
   Schema string `json:"schema"`
   WitnessedSequence uint64 `json:"witnessed_sequence"`
   WitnessedHeadSHA256 string `json:"witnessed_head_sha256"`
   ExecutionAuthorized bool `json:"execution_authorized"`
  }{Schema:SignedCheckpointSchema,WitnessedSequence:committed.Sequence,
   WitnessedHeadSHA256:committed.HeadSHA256,ExecutionAuthorized:false})
 }),nil
}

// No legacy unsigned /v1/fsa/cas route is registered by this handler.
