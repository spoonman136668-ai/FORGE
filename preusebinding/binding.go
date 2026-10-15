package preusebinding

// R36 bridges externally pinned signed predecision bytes to the R35 D1
// candidate identity. It does not operate D1, grant science, or mint keys.
import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)
const Domain="FORGE-R36-INDEPENDENT-OWNER-WITNESS-PREUSE-V1\x00"
var ErrUnqualified=errors.New("R36_INDEPENDENT_OWNER_FIRST_USE_NOT_QUALIFIED")

type Decision struct{
 Lane string `json:"lane"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OriginalKeySHA256 string `json:"original_key_sha256"`
 FrozenPolicySHA256 string `json:"frozen_policy_sha256"`
 CandidateSetSHA256 string `json:"candidate_set_sha256"`
 ChosenCandidateSHA256 string `json:"chosen_candidate_sha256"`
 LoggedProbabilityBP uint32 `json:"logged_probability_bp"`
 RandomizationProofSHA256 string `json:"randomization_proof_sha256"`
 Sequence uint64 `json:"sequence"`
}
type Signed struct{
 Decision Decision `json:"decision"`
 OwnerSignatureHex string `json:"owner_signature_hex"`
 WitnessSignatureHex string `json:"witness_signature_hex"`
}
type IndependentPins struct{
 OwnerPublicKeyHex string `json:"owner_public_key_hex"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 ExactDecisionSHA256 string `json:"exact_decision_sha256"`
}
type Claim struct{
 OriginalKeySHA256 string `json:"original_key_sha256"`
 Lane string `json:"lane"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 SourceCommitSHA string `json:"source_commit_sha"`
 FrozenPredecisionSHA256 string `json:"frozen_predecision_sha256"`
 ExternalOwnerWitnessPinSHA256 string `json:"external_owner_witness_pin_sha256"`
 ClaimedSequence uint64 `json:"claimed_sequence"`
 ScientificAuthorized bool `json:"scientific_authorized"`
}
func validHex(v string,n int)bool{
 if len(v)!=n{return false}
 for _,r:=range v {if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func Verify(s Signed,p IndependentPins)(Claim,error){
 d:=s.Decision
 var zero Claim
 if (d.Lane!="Wingless"&&d.Lane!="Yggdrasil")||d.OwnerEpoch==0||d.Sequence==0||
  !validHex(d.SourceCommitSHA,40)||!validHex(d.OriginalKeySHA256,64)||
  !validHex(d.FrozenPolicySHA256,64)||!validHex(d.CandidateSetSHA256,64)||
  !validHex(d.ChosenCandidateSHA256,64)||!validHex(d.RandomizationProofSHA256,64)||
  d.LoggedProbabilityBP==0||d.LoggedProbabilityBP>10000||
  !validHex(p.OwnerPublicKeyHex,64)||!validHex(p.WitnessPublicKeyHex,64)||
  p.OwnerPublicKeyHex==p.WitnessPublicKeyHex||!validHex(p.ExactDecisionSHA256,64)||
  !validHex(s.OwnerSignatureHex,128)||!validHex(s.WitnessSignatureHex,128){
  return zero,ErrUnqualified
 }
 body,err:=json.Marshal(d)
 if err!=nil{return zero,ErrUnqualified}
 message:=append([]byte(Domain),body...)
 digest:=sha256.Sum256(message)
 if hex.EncodeToString(digest[:])!=p.ExactDecisionSHA256{return zero,ErrUnqualified}
 owner,_:=hex.DecodeString(p.OwnerPublicKeyHex)
 witness,_:=hex.DecodeString(p.WitnessPublicKeyHex)
 a,_:=hex.DecodeString(s.OwnerSignatureHex)
 b,_:=hex.DecodeString(s.WitnessSignatureHex)
 if !ed25519.Verify(owner,message,a)||!ed25519.Verify(witness,message,b){
  return zero,ErrUnqualified
 }
 // This hash cryptographically binds the *two pinned public keys* to the
 // frozen event. Pin authenticity and physical independence remain external.
 pinHash:=sha256.Sum256([]byte(p.OwnerPublicKeyHex+"\x00"+p.WitnessPublicKeyHex))
 return Claim{OriginalKeySHA256:d.OriginalKeySHA256,Lane:d.Lane,
  OwnerEpoch:d.OwnerEpoch,SourceCommitSHA:d.SourceCommitSHA,
  FrozenPredecisionSHA256:p.ExactDecisionSHA256,
  ExternalOwnerWitnessPinSHA256:hex.EncodeToString(pinHash[:]),
  ClaimedSequence:d.Sequence,ScientificAuthorized:false},nil
}
