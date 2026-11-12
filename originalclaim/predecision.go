package originalclaim

// R30 introduces a SOURCE-BOUND OWNER PREDECISION hook immediately before
// this package's existing write-once first-use claim. It cannot mint an
// external witness, authorize science, or prove unbiased randomization.
import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
)

const (
 PredecisionSchema="forge.original.owner-predecision.v1"
 PredecisionDomain="FORGE-ORIGINAL-OWNER-PREDECISION-V1\n"
)
var ErrPredecision=errors.New("FORGE_ORIGINAL_PREDECISION_NOT_OWNER_AUTHENTICATED_OR_ALREADY_CONSUMED")

// Predecision is frozen BEFORE an original can start. A signed declaration of
// pre-outcome timing alone never proves clock order; independent first-use
// authority must check its own durable sequence and current owner epoch.
type Predecision struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 IntentSHA256 string `json:"intent_sha256"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OriginalRunID string `json:"original_run_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 WorkerID string `json:"worker_id"`
 PolicySHA256 string `json:"policy_sha256"`
 CandidateSetSHA256 string `json:"candidate_set_sha256"`
 SelectedCandidateSHA256 string `json:"selected_candidate_sha256"`
 BaselinePolicySHA256 [4]string `json:"baseline_policy_sha256"`
 LoggedActionProbabilityBP int `json:"logged_action_probability_bp"`
 RandomizationProofSHA256 string `json:"randomization_proof_sha256"`
 DecisionSequence uint64 `json:"decision_sequence"`
 BeforeOutcomeDeclared bool `json:"before_outcome_declared"`
}
type SignedPredecision struct {
 Event Predecision `json:"event"`
 OwnerSignatureHex string `json:"owner_signature_hex"`
 WitnessSignatureHex string `json:"witness_signature_hex"`
}
// PinnedTrust MUST originate outside both the proposed original and its
// worker. Key inequality detects key reuse, not physical independence.
type PinnedTrust struct {
 OwnerPublicKeyHex string `json:"owner_public_key_hex"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 ExpectedPredecisionSHA256 string `json:"expected_predecision_sha256"`
 ExpectedPolicySHA256 string `json:"expected_policy_sha256"`
 ExpectedBaselinePolicySHA256 [4]string `json:"expected_baseline_policy_sha256"`
}
type PredecisionAssessment struct {
 ClaimVerified bool `json:"claim_verified"`
 PredecisionSigned bool `json:"predecision_signed"`
 ActualPreOutcomeTimingIndependentlyVerified bool `json:"actual_pre_outcome_timing_independently_verified"`
 IndependentExternalFirstUseVerified bool `json:"independent_external_first_use_verified"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
}

func PredecisionHash(e Predecision)(string,error){
 if e.Schema!=PredecisionSchema{return "",ErrPredecision}
 raw,err:=json.Marshal(e)
 if err!=nil{return "",ErrPredecision}
 sum:=sha256.Sum256(append([]byte(PredecisionDomain),raw...))
 return hex.EncodeToString(sum[:]),nil
}
func validPredecision(e Predecision,c Claim,p PinnedTrust)bool{
 if !validate(c)||e.Schema!=PredecisionSchema||
  e.Lane!=c.Lane||e.ExperimentID!=c.ExperimentID||
  e.FrozenSHA256!=c.FrozenSHA256||e.IntentSHA256!=c.IntentSHA256||
  e.SourceCommitSHA!=c.SourceCommitSHA||e.OriginalRunID!=c.OriginalRunID||
  e.OwnerEpoch!=c.OwnerEpoch||e.WorkerID!=c.WorkerID||
  !hexN(e.PolicySHA256,64)||e.PolicySHA256!=p.ExpectedPolicySHA256||
  !hexN(e.CandidateSetSHA256,64)||!hexN(e.SelectedCandidateSHA256,64)||
  e.SelectedCandidateSHA256==e.CandidateSetSHA256||
  !hexN(e.RandomizationProofSHA256,64)||
  e.DecisionSequence==0||!e.BeforeOutcomeDeclared||
  e.LoggedActionProbabilityBP<1||e.LoggedActionProbabilityBP>10000{
  return false
 }
 seen:=map[string]bool{e.PolicySHA256:true}
 for i,b:=range e.BaselinePolicySHA256{
  if !hexN(b,64)||b!=p.ExpectedBaselinePolicySHA256[i]||seen[b]{
   return false
  }
  seen[b]=true
 }
 return true
}
// VerifyPredecision only validates cryptographic correspondence against
// independently provided pins. A signed counterfeit using newly invented
// local keys is NEVER independent authority.
func VerifyPredecision(s SignedPredecision,c Claim,p PinnedTrust)error{
 if !validPredecision(s.Event,c,p)||
  !hexN(p.ExpectedPredecisionSHA256,64)||
  !hexN(p.OwnerPublicKeyHex,64)||!hexN(p.WitnessPublicKeyHex,64)||
  p.OwnerPublicKeyHex==p.WitnessPublicKeyHex||
  !hexN(s.OwnerSignatureHex,128)||!hexN(s.WitnessSignatureHex,128){
  return ErrPredecision
 }
 digest,err:=PredecisionHash(s.Event)
 if err!=nil||digest!=p.ExpectedPredecisionSHA256{return ErrPredecision}
 raw,err:=json.Marshal(s.Event)
 if err!=nil{return ErrPredecision}
 message:=append([]byte(PredecisionDomain),raw...)
 owner,_:=hex.DecodeString(p.OwnerPublicKeyHex)
 witness,_:=hex.DecodeString(p.WitnessPublicKeyHex)
 ownerSig,_:=hex.DecodeString(s.OwnerSignatureHex)
 witnessSig,_:=hex.DecodeString(s.WitnessSignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(owner),message,ownerSig)||
  !ed25519.Verify(ed25519.PublicKey(witness),message,witnessSig){
  return ErrPredecision
 }
 return nil
}
func predecisionPath(root string,c Claim)string{
 h:=sha256.Sum256([]byte(c.Lane+"\x00"+c.ExperimentID))
 return filepath.Join(root,hex.EncodeToString(h[:])+"-predecision.json")
}
func signedCanonical(s SignedPredecision)([]byte,error){
 b,err:=json.Marshal(s)
 if err!=nil||len(b)>4095{return nil,ErrPredecision}
 return append(b,'\n'),nil
}
// ConsumeWithPredecision is a prospective OWNER CALL SITE hook. It saves a
// durable, write-once PREDECISION BEFORE calling Consume. Any uncertainty,
// interruption or duplicate leaves original eligibility denied; it never
// deletes its partial evidence or retries the original.
// This LOCAL transaction is not a distributed CAS and must still be fenced
// by the existing independently controlled scientific owner.
func ConsumeWithPredecision(root string,c Claim,s SignedPredecision,p PinnedTrust)error{
 if directory(root)!=nil||VerifyPredecision(s,c,p)!=nil{return ErrPredecision}
 // A pre-existing original claim may NEVER gain a post-hoc "predecision".
 // A concurrent direct Consume remains an uncertain race and is denied below.
 if _,err:=os.Lstat(path(root,c));err==nil||!os.IsNotExist(err){return ErrPredecision}
 raw,err:=signedCanonical(s)
 if err!=nil{return ErrPredecision}
 f,err:=os.OpenFile(predecisionPath(root,c),os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return ErrPredecision}
 n,err:=f.Write(raw)
 if err==nil&&n!=len(raw){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil||closeErr!=nil||syncDir(root)!=nil{return ErrPredecision}
 if err=Consume(root,c);err!=nil{return ErrPredecision}
 return nil
}
func ReadPredecision(root string,c Claim,p PinnedTrust)(SignedPredecision,PredecisionAssessment,error){
 var zero SignedPredecision
 var result PredecisionAssessment
 if directory(root)!=nil||!validate(c){return zero,result,ErrPredecision}
 info,err:=os.Lstat(predecisionPath(root,c))
 if err!=nil||!info.Mode().IsRegular()||info.Size()<1||info.Size()>4096{return zero,result,ErrPredecision}
 raw,err:=os.ReadFile(predecisionPath(root,c))
 if err!=nil{return zero,result,ErrPredecision}
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 var signed SignedPredecision
 if decoder.Decode(&signed)!=nil||decoder.Decode(new(any))!=io.EOF{return zero,result,ErrPredecision}
 canon,err:=signedCanonical(signed)
 if err!=nil||!bytes.Equal(canon,raw)||VerifyPredecision(signed,c,p)!=nil{
  return zero,result,ErrPredecision
 }
 if _,err=Read(root,c);err!=nil{return zero,result,ErrPredecision}
 result.ClaimVerified=true
 result.PredecisionSigned=true
 return signed,result,nil
}
