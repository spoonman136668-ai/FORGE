package sourcebirth

// External readback validation is an additional source-only cryptographic
// consistency gate, NOT a real remote D1 request, persistent global CAS,
// independent physical key custody or permission to run an original.
import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
)

const (
 RemoteReadbackSchema="forge.sourcebirth.external-readback-claim.v1"
 RemoteReadbackDomain="FORGE-SOURCE-FIRSTUSE-REMOTE-READBACK-V1\n"
)

var ErrUntrustedRemoteReadback=errors.New("FORGE_SOURCEBIRTH_REMOTE_FIRSTUSE_NOT_INDEPENDENTLY_ATTESTED")

type RemoteReadbackClaim struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 BirthSHA256 string `json:"birth_sha256"`
 StoreID string `json:"store_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BirthSequence uint64 `json:"birth_sequence"`
 PriorHeadSHA256 string `json:"prior_head_sha256"`
 CommittedHeadSHA256 string `json:"committed_head_sha256"`
 CommittedRevision uint64 `json:"committed_revision"`
 ReadbackHeadSHA256 string `json:"readback_head_sha256"`
 ReadbackRevision uint64 `json:"readback_revision"`
}
type SignedRemoteReadback struct {
 Claim RemoteReadbackClaim `json:"claim"`
 SignatureHex string `json:"signature_hex"`
}
type IndependentReadbackPins struct {
 StoreID string
 AuthorityEpoch uint64
 PriorHeadSHA256 string
 MinimumCommittedRevision uint64
 MinimumReadbackRevision uint64
 RemoteWitnessPublicKey ed25519.PublicKey
}
type ReadbackReview struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 SourceBirthSHA256 string `json:"source_birth_sha256"`
 SourceSignaturesVerified bool `json:"source_signatures_verified"`
 RemoteReceiptSignatureVerified bool `json:"remote_receipt_signature_verified"`
 ImmutableSourceAndClaimPinned bool `json:"immutable_source_and_claim_pinned"`
 ClaimedReadbackMatchesCommit bool `json:"claimed_readback_matches_commit"`
 LiveRemoteReadbackWitnessed bool `json:"live_remote_readback_witnessed"`
 OperationalSignerIndependenceVerified bool `json:"operational_signer_independence_verified"`
 GlobalLinearizableFirstUseProven bool `json:"global_linearizable_first_use_proven"`
 OriginalExecutionAuthorized bool `json:"original_execution_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}

// ReviewRemoteReadback validates signatures and caller-independent pins.
// Passing this check NEVER turns self-reported remote commitment into a
// trustworthy remote readback: the operational live witness still must be
// supplied by an independently provisioned authority OUTSIDE this API.
func ReviewRemoteReadback(
 birth Signed, sourcePins Pins, receipt SignedRemoteReadback, pins IndependentReadbackPins,
)(ReadbackReview,error){
 var zero ReadbackReview
 observed,err:=Verify(birth,sourcePins)
 if err!=nil{return zero,ErrUntrustedRemoteReadback}
 b:=birth.Statement
 r:=receipt.Claim
 if r.Schema!=RemoteReadbackSchema||
  r.Lane!=b.Lane||r.OriginalID!=b.OriginalID||
  r.BirthSHA256!=observed.BirthSHA256||
  len(r.StoreID)<4||len(r.StoreID)>128||r.StoreID!=pins.StoreID||
  r.AuthorityEpoch==0||r.AuthorityEpoch!=b.AuthorityEpoch||r.AuthorityEpoch!=pins.AuthorityEpoch||
  r.BirthSequence==0||r.BirthSequence!=b.BirthSequence||
  !validHex(r.PriorHeadSHA256,64)||r.PriorHeadSHA256!=pins.PriorHeadSHA256||
  !validHex(r.CommittedHeadSHA256,64)||r.CommittedHeadSHA256==r.PriorHeadSHA256||
  !validHex(r.ReadbackHeadSHA256,64)||r.ReadbackHeadSHA256!=r.CommittedHeadSHA256||
  pins.MinimumCommittedRevision==0||pins.MinimumReadbackRevision==0||
  r.CommittedRevision<pins.MinimumCommittedRevision||
  r.ReadbackRevision<pins.MinimumReadbackRevision||
  r.ReadbackRevision<r.CommittedRevision||
  len(pins.RemoteWitnessPublicKey)!=ed25519.PublicKeySize||
  bytes.Equal(pins.RemoteWitnessPublicKey,sourcePins.IssuerPublicKey)||
  bytes.Equal(pins.RemoteWitnessPublicKey,sourcePins.WitnessPublicKey)||
  !validHex(receipt.SignatureHex,128){
  return zero,ErrUntrustedRemoteReadback
 }
 raw,err:=json.Marshal(r)
 if err!=nil{return zero,ErrUntrustedRemoteReadback}
 sig,err:=hex.DecodeString(receipt.SignatureHex)
 if err!=nil||!ed25519.Verify(pins.RemoteWitnessPublicKey,
      append([]byte(RemoteReadbackDomain),raw...),sig){
  return zero,ErrUntrustedRemoteReadback
 }
 return ReadbackReview{
  Schema:"forge.sourcebirth.readonly-remote-claim-review.v1",
  Lane:b.Lane,OriginalID:b.OriginalID,SourceBirthSHA256:observed.BirthSHA256,
  SourceSignaturesVerified:true,RemoteReceiptSignatureVerified:true,
  ImmutableSourceAndClaimPinned:true,ClaimedReadbackMatchesCommit:true,
  // Never promote synthetic signatures or caller-supplied metadata into
  // physical independence, actual D1 linearizability or execution permits.
 },nil
}
