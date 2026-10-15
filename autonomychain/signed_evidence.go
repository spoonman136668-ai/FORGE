// Package autonomychain composes existing signed-science evidence checks
// without providing an original execution, admission or acceptance path.
package autonomychain

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/executionbridge"
 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

// SignedEvidence is a snapshot supplied by an existing owner/custody reader.
// This type does not fetch, provision, or authenticate the origin of the keys.
type SignedEvidence struct {
 ClaimRoot string
 Claim originalclaim.Claim
 Worker workerreconcile.Expected
 Start workerreconcile.Signed
 Terminal workerreconcile.Signed
 Science executionbridge.AttestedTerminalWitness
 PinnedSourceHeadSHA256 string
}

// EvidenceSet is exactly two consecutive originals from EACH existing lane.
type EvidenceSet struct {
 Wingless [2]SignedEvidence
 Yggdrasil [2]SignedEvidence
}

// EvidenceReport deliberately distinguishes verified cryptographic syntax
// against supplied keys from genuine independent first-use and owner custody.
type EvidenceReport struct {
 Structure Report `json:"structure"`
 LocalFirstUseClaimsMatched bool `json:"local_first_use_claims_matched"`
 SuppliedKeyWorkerSignaturesValid bool `json:"supplied_key_worker_signatures_valid"`
 SuppliedKeyScienceSignaturesValid bool `json:"supplied_key_science_signatures_valid"`
 IndependentOwnerHighWaterVerified bool `json:"independent_owner_high_water_verified"`
 DistributedFirstUseCASVerified bool `json:"distributed_first_use_cas_verified"`
 AuthenticFirstUseVerified bool `json:"authentic_first_use_verified"`
 NewOriginalsExecuted bool `json:"new_originals_executed"`
 IndependentScientificAcceptance bool `json:"independent_scientific_acceptance"`
 AutonomousDispatchAuthorized bool `json:"autonomous_dispatch_authorized"`
 OwnerCutoverAuthorized bool `json:"owner_cutover_authorized"`
}

// VerifySignedEvidence performs read-only, deterministic composition of
// F55 structure + locally consumed claims + signed worker START/TERMINAL +
// a DIFFERENT signer for an independent terminal-science observation.
// It never claims provenance of the supplied public keys or atomicity of the
// underlying claim store. Real owner custody, independent trust pins and a
// durable distributed once-only fence remain mandatory future gates.
func VerifySignedEvidence(ctx context.Context,c Candidate,e EvidenceSet)(EvidenceReport,error){
 var blocked EvidenceReport
 if ctx==nil||ctx.Err()!=nil{return blocked,ErrBlocked}
 shape,err:=Audit(c)
 if err!=nil{return blocked,err}
 seenWorkerKeys:=map[string]string{}
 seenScienceKeys:=map[string]string{}
 check:=func(original Original,s SignedEvidence)error{
  if ctx.Err()!=nil{return ErrBlocked}
  w:=s.Worker
  if w.Lane!=original.Lane||w.ExperimentID!=original.ExperimentID||
   w.OriginalRunID!=original.OriginalRunID||w.FrozenSHA256!=original.FrozenPlanSHA256||
   w.OwnerEpoch==0||w.WorkerID==""||w.IntentSHA256==""||
   s.Claim.Lane!=w.Lane||s.Claim.ExperimentID!=w.ExperimentID||
   s.Claim.OriginalRunID!=w.OriginalRunID||s.Claim.FrozenSHA256!=w.FrozenSHA256||
   s.Claim.IntentSHA256!=w.IntentSHA256||s.Claim.OwnerEpoch!=w.OwnerEpoch||
   s.Claim.WorkerID!=w.WorkerID||s.Claim.SourceCommitSHA!=original.SourceCommitSHA||
   !s.Claim.FirstUseConsumed||
   len(w.WorkerPublicKey)!=ed25519.PublicKeySize||
   len(s.Science.PublicKey)!=ed25519.PublicKeySize||
   bytes.Equal(w.WorkerPublicKey,s.Science.PublicKey)||
   s.Science.Expected.Lane!=w.Lane||
   s.Science.Expected.ExperimentID!=w.ExperimentID||
   s.Science.Expected.OriginalRunID!=w.OriginalRunID||
   s.Science.Expected.OwnerEpoch!=w.OwnerEpoch||
   s.Science.Expected.WorkerID!=w.WorkerID||
   s.Science.Expected.FrozenSHA256!=w.FrozenSHA256||
   s.Science.Expected.IntentSHA256!=w.IntentSHA256||
   !bytes.Equal(s.Science.Expected.WorkerPublicKey,w.WorkerPublicKey)||
   !hexLower(s.PinnedSourceHeadSHA256,64)||
   s.Science.Signed.Evidence.SourceHeadSHA256!=s.PinnedSourceHeadSHA256 {
   return ErrBlocked
  }
  // Independent signing domains for different lanes, while allowing key
  // rotation or deliberate re-use within the same lane.
  wk:=string(w.WorkerPublicKey);sk:=string(s.Science.PublicKey)
  if prev,ok:=seenWorkerKeys[wk];ok&&prev!=w.Lane{return ErrBlocked}
  if prev,ok:=seenScienceKeys[sk];ok&&prev!=w.Lane{return ErrBlocked}
  if _,ok:=seenScienceKeys[wk];ok{return ErrBlocked}
  if _,ok:=seenWorkerKeys[sk];ok{return ErrBlocked}
  seenWorkerKeys[wk]=w.Lane;seenScienceKeys[sk]=w.Lane

  if _,err:=originalclaim.Read(s.ClaimRoot,s.Claim);err!=nil{return fmt.Errorf("%w: local first-use claim: %v",ErrBlocked,err)}
  state,err:=workerreconcile.Reconcile(w,&s.Start,&s.Terminal)
  if err!=nil||state!=workerreconcile.Terminal||
   s.Start.Receipt.Stage!="STARTED"||s.Terminal.Receipt.Stage!="TERMINAL"{
   return fmt.Errorf("%w: worker receipts",ErrBlocked)
  }
  startHash,err:=workerreconcile.Fingerprint(s.Start)
  if err!=nil||startHash!=original.StartReceiptSHA256{return ErrBlocked}
  endHash,err:=workerreconcile.Fingerprint(s.Terminal)
  if err!=nil||endHash!=original.TerminalReceiptSHA256{return ErrBlocked}
  if s.Science.Signed.Evidence.EvidenceSHA256!=s.Terminal.Receipt.EvidenceSHA256||
   s.Science.Signed.WorkerEvidenceSHA256!=s.Terminal.Receipt.EvidenceSHA256{return ErrBlocked}
  verified,err:=s.Science.VerifyTerminal(ctx,s.Science.Signed.Evidence)
  if err!=nil||!verified{return fmt.Errorf("%w: independent terminal witness",ErrBlocked)}
  reviewHash,err:=executionbridge.TerminalWitnessFingerprint(s.Science.Signed)
  if err!=nil||reviewHash!=original.IndependentReviewSHA256{return ErrBlocked}
  return nil
 }
 for i:=0;i<2;i++{
  if err:=check(c.Wingless[i],e.Wingless[i]);err!=nil{return blocked,fmt.Errorf("%w: Wingless stage %d: %v",ErrBlocked,i,err)}
  if err:=check(c.Yggdrasil[i],e.Yggdrasil[i]);err!=nil{return blocked,fmt.Errorf("%w: Yggdrasil stage %d: %v",ErrBlocked,i,err)}
 }
 if ctx.Err()!=nil{return blocked,errors.Join(ErrBlocked,ctx.Err())}
 return EvidenceReport{
  Structure:shape,LocalFirstUseClaimsMatched:true,
  SuppliedKeyWorkerSignaturesValid:true,
  SuppliedKeyScienceSignaturesValid:true,
  // These are NOT inferred from signed strings or a locally present file.
  IndependentOwnerHighWaterVerified:false,
  DistributedFirstUseCASVerified:false,AuthenticFirstUseVerified:false,
  NewOriginalsExecuted:false,IndependentScientificAcceptance:false,
  AutonomousDispatchAuthorized:false,OwnerCutoverAuthorized:false,
 },nil
}
