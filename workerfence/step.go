// Package workerfence provides source-only, negative-only worker boundaries.
package workerfence

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/workerlease"
)

const (
 StepSchema = "forge.worker.step-consumption.v1"
 StepReceiptSchema = "forge.worker.step-receipt.v1"
 StepReceiptDomain = "FORGE-WORKER-STEP-FENCE-RECEIPT-V1\n"
 Consumed = "CONSUMED_NO_EXECUTION_AUTHORITY"
)

var (
 ErrStepBlocked = errors.New("FORGE_WORKER_STEP_FENCE_BLOCKED")
 ErrStepIndeterminate = errors.New("FORGE_WORKER_STEP_FENCE_INDETERMINATE_NO_RETRY")
)

// StepClaim binds a specific original, immutable worker binary and logical
// step to an observed authority head. It is not itself a worker permit.
type StepClaim struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 AuthoritySequence uint64 `json:"authority_sequence"`
 AuthorityHeadSHA256 string `json:"authority_head_sha256"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 IntentSHA256 string `json:"intent_sha256"`
 OwnerID string `json:"owner_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 WorkerID string `json:"worker_id"`
 WorkerBinarySHA256 string `json:"worker_binary_sha256"`
 LeaseSequence uint64 `json:"lease_sequence"`
 ExpiresAtUnix uint64 `json:"expires_at_unix"`
 StepSHA256 string `json:"step_sha256"`
}

// SignedStepReceipt must originate from a SEPARATELY provisioned signer,
// not from a worker. A signature without a durable one-shot store is unsafe.
type SignedStepReceipt struct {
 Schema string `json:"schema"`
 Claim StepClaim `json:"claim"`
 Status string `json:"status"`
 SignatureHex string `json:"signature_hex"`
}

// StepAuthority must atomically fence owner+epoch+lease+step against an
// independently durable consumed-step ledger. Each exact step is immutable.
// On ANY ambiguous outcome the caller must not retry or perform the step.
// This interface is not a production backend and creates no scheduler.
type StepAuthority interface {
 ConsumeOnce(context.Context, StepClaim)(SignedStepReceipt,error)
}

type StepObservation struct {
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 StepSHA256 string `json:"step_sha256"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 ConsumptionObserved bool `json:"consumption_observed"`
 WorkerDispatchAuthorized bool `json:"worker_dispatch_authorized"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 FirstUseReplayAuthorized bool `json:"first_use_replay_authorized"`
}

func receiptVerified(r SignedStepReceipt,claim StepClaim,pin ed25519.PublicKey)bool{
 if r.Schema!=StepReceiptSchema||r.Claim!=claim||r.Status!=Consumed||
  len(pin)!=ed25519.PublicKeySize{return false}
 signature,err:=hex.DecodeString(r.SignatureHex)
 if err!=nil||len(signature)!=ed25519.SignatureSize{return false}
 r.SignatureHex=""
 encoded,err:=json.Marshal(r)
 if err!=nil{return false}
 return ed25519.Verify(pin,append([]byte(StepReceiptDomain),encoded...),signature)
}

// InspectStep consumes exactly one hypothetical step identity after the
// existing real dual-mTLS remote epoch/binding/witness observation.
// Even on success this is a source-only, NON-AUTHORIZING diagnostic receipt:
// a read/CAS/read sequence cannot atomically protect a subsequent external
// side effect. Actual worker executors must be integrated with a protected
// synchronous authority gate at the irreversible step boundary.
func InspectStep(ctx context.Context,remote *fsaremote.Client,anchor fsahead.Anchor,
 lease workerlease.Lease,now uint64,stepSHA256,binarySHA256 string,
 authority StepAuthority,receiptKey ed25519.PublicKey)(StepObservation,error){
 var none StepObservation
 if ctx==nil||ctx.Err()!=nil||remote==nil||authority==nil||
  !pinned(anchor)||!digest(stepSHA256,64)||!digest(binarySHA256,64)||
  len(receiptKey)!=ed25519.PublicKeySize||
  bytes.Equal(receiptKey,anchor.PublicKey)||
  lease.FirstUseRisk||lease.Lane!="Wingless"&&lease.Lane!="Yggdrasil"||
  lease.OwnerEpoch!=anchor.AuthorityEpoch{return none,ErrStepBlocked}
 before,err:=Observe(ctx,remote,anchor,lease,now)
 if err!=nil{return none,ErrStepBlocked}
 claim:=StepClaim{Schema:StepSchema,ArchiveID:anchor.ArchiveID,
  AuthoritySequence:anchor.Sequence,AuthorityHeadSHA256:anchor.HeadSHA256,
  Lane:lease.Lane,OriginalID:lease.ExperimentID,IntentSHA256:lease.IntentSHA256,
  OwnerID:lease.OwnerID,OwnerEpoch:lease.OwnerEpoch,WorkerID:lease.WorkerID,
  WorkerBinarySHA256:binarySHA256,LeaseSequence:lease.LeaseSequence,
  ExpiresAtUnix:lease.ExpiresAtUnix,StepSHA256:stepSHA256}
 if before.LeaseSequence!=claim.LeaseSequence||ctx.Err()!=nil{
  return none,ErrStepBlocked
 }
 // A network error may mean the irreversible one-shot claim was committed.
 // There is deliberately no retry or local fallback.
 consumed,err:=authority.ConsumeOnce(ctx,claim)
 if err!=nil||ctx.Err()!=nil{return none,ErrStepIndeterminate}
 if !receiptVerified(consumed,claim,receiptKey){
  return none,ErrStepIndeterminate
 }
 after,err:=Observe(ctx,remote,anchor,lease,now)
 if err!=nil||after.LeaseSequence!=claim.LeaseSequence||ctx.Err()!=nil{
  return none,ErrStepIndeterminate
 }
 return StepObservation{Mode:"SOURCE_ONLY_STEP_CONSUMED_NO_EXECUTION_AUTHORITY",
  Lane:claim.Lane,OriginalID:claim.OriginalID,StepSHA256:claim.StepSHA256,
  AuthorityEpoch:claim.OwnerEpoch,ConsumptionObserved:true,
  WorkerDispatchAuthorized:false,ScientificExecutionAuthorized:false,
  FirstUseReplayAuthorized:false},nil
}
