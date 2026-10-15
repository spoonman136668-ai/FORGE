package dreamrsi

// R25 is a read-only owner-evidence adapter. Source bytes are authenticated
// against separately supplied immutable pins before the existing R24 verifier
// is invoked. Matching SHA256 and signatures cannot by themselves establish
// physical trust custody, first-use, or unbiased randomization.
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
)

const (
 OwnerBundleSchema = "forge.dreamrsi.r25-prospective-owner-evidence.v1"
 IndependentPinsSchema = "forge.dreamrsi.r25-independent-source-pins.v1"
 MaxOwnerEvidenceBytes=8*1024*1024
 MaxIndependentPinsBytes=256*1024
)
var ErrProspectiveIntake=errors.New("FORGE_R25_GENUINE_PROSPECTIVE_OWNER_EVIDENCE_NOT_QUALIFIED")

type OwnerLaneEvidence struct {
 Lane string `json:"lane"`
 Optimizer Optimization `json:"optimizer"`
 Train Envelope `json:"train"`
 Validation Envelope `json:"validation"`
 Heldout Envelope `json:"heldout"`
 FrozenHoldout HoldoutSpec `json:"frozen_holdout"`
 SignedAudit SignedProspectiveAudit `json:"signed_audit"`
}
type ProspectiveOwnerBundle struct {
 Schema string `json:"schema"`
 Lanes [2]OwnerLaneEvidence `json:"lanes"`
}
type IndependentLanePins struct {
 Lane string `json:"lane"`
 FrozenOptimizerHeadSHA256 string `json:"frozen_optimizer_head_sha256"`
 Train TrustPin `json:"train"`
 Validation TrustPin `json:"validation"`
 Heldout TrustPin `json:"heldout"`
 HoldoutSpecSHA256 string `json:"holdout_spec_sha256"`
 Audit ProspectiveAuditPins `json:"audit"`
}
type ProspectiveIndependentPins struct {
 Schema string `json:"schema"`
 OwnerBundleSHA256 string `json:"owner_bundle_sha256"`
 Lanes [2]IndependentLanePins `json:"lanes"`
}

// Strict byte identity deliberately rejects alternate encodings, unknown
// fields, trailing JSON, and duplicate-key ambiguity. An independent owner
// pins the exact source bytes outside the owner-generated evidence bundle.
func decodeIntake[T any](raw []byte,max int)(T,error){
 var zero T
 if len(raw)==0||len(raw)>max{return zero,ErrProspectiveIntake}
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 if d.Decode(&zero)!=nil||d.Decode(new(any))!=io.EOF{
  var empty T
  return empty,ErrProspectiveIntake
 }
 normalized,err:=json.Marshal(zero)
 if err!=nil||!bytes.Equal(bytes.TrimSuffix(raw,[]byte("\n")),normalized){
  var empty T
  return empty,ErrProspectiveIntake
 }
 return zero,nil
}

// ReviewOwnerEvidence requires one signed, immutable pair from the existing
// scientific owner plus separately provided pins. It will NOT invent missing
// records. It is *not* the execution service and cannot grant admission.
func ReviewOwnerEvidence(ownerRaw,pinsRaw []byte)(ProspectivePairReview,error){
 var zero ProspectivePairReview
 bundle,err:=decodeIntake[ProspectiveOwnerBundle](ownerRaw,MaxOwnerEvidenceBytes)
 if err!=nil{return zero,ErrProspectiveIntake}
 pins,err:=decodeIntake[ProspectiveIndependentPins](pinsRaw,MaxIndependentPinsBytes)
 if err!=nil{return zero,ErrProspectiveIntake}
 sha:=sha256.Sum256(ownerRaw)
 if bundle.Schema!=OwnerBundleSchema||pins.Schema!=IndependentPinsSchema||
  !validHex(pins.OwnerBundleSHA256,64)||
  hex.EncodeToString(sha[:])!=pins.OwnerBundleSHA256{
  return zero,ErrProspectiveIntake
 }
 var inputs [2]ProspectiveLaneInput
 for i,lane:=range []string{"Wingless","Yggdrasil"} {
  e,p:=bundle.Lanes[i],pins.Lanes[i]
  if e.Lane!=lane||p.Lane!=lane||
   !validHex(p.FrozenOptimizerHeadSHA256,64)||
   e.Optimizer.LineageHeadSHA256!=p.FrozenOptimizerHeadSHA256||
   e.Optimizer.Lane!=lane||e.FrozenHoldout.Lane!=lane||
   p.Train.ExpectedHistorySHA256==p.Validation.ExpectedHistorySHA256||
   p.Train.ExpectedHistorySHA256==p.Heldout.ExpectedHistorySHA256||
   p.Validation.ExpectedHistorySHA256==p.Heldout.ExpectedHistorySHA256{
   return zero,ErrProspectiveIntake
  }
  inputs[i]=ProspectiveLaneInput{
   Lane:lane,Optimizer:e.Optimizer,Train:e.Train,
   Validation:e.Validation,Heldout:e.Heldout,
   TrainPin:p.Train,ValidationPin:p.Validation,HeldoutPin:p.Heldout,
   FrozenHoldout:e.FrozenHoldout,
   IndependentlyPinnedHoldoutSpecSHA256:p.HoldoutSpecSHA256,
   SignedAudit:e.SignedAudit,AuditPins:p.Audit,
  }
 }
 result,err:=AssessProspectivePair(inputs)
 if err!=nil || result.ScientificAccepted || result.OptimizerDispatchAuthorized ||
  result.ScientificImprovementEstablished||result.NewOriginalsExecuted!=0||
  result.IndependentFirstUseAndSourceBirthProven||result.IndependentRandomizationOperationallyProven{
  return zero,ErrProspectiveIntake
 }
 return result,nil
}
