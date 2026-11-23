package optimizerstages

// F90 is a STRICTLY NON-AUTHORIZING source/crypto consistency audit of F89
// prospective policy-arm assignments. A valid signature or timestamp string
// does NOT prove independent pre-outcome custody, true randomness, original
// first-use, completeness of a real research population, or scientific gain.
import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math/big"
)

const F90WitnessSchema="forge.optimizer.f90.source-only-owner-predecision.v1"
const F90AuditSchema="forge.optimizer.f90.signed-policy-outcome-source-audit.v1"
const F90SignatureDomain="FORGE-F90-SOURCE-ONLY-WITNESS-V1\n"
var ErrF90=errors.New("FORGE_F90_AUTHENTIC_INDEPENDENT_PROSPECTIVE_OWNER_WITNESS_REQUIRED")

type F90Predecision struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 AssignmentSHA256 string `json:"assignment_sha256"`
 OwnerSourceSHA string `json:"owner_source_sha"`
 PreregistrationSHA256 string `json:"preregistration_sha256"`
 CandidateSlateSHA256 string `json:"candidate_slate_sha256"`
 OriginalReceiptSHA256 string `json:"original_receipt_sha256"`
 Sequence uint64 `json:"sequence"`
 ClaimedPredecisionUnix int64 `json:"claimed_predecision_unix"`
}
type F90SignedPredecision struct{
 Record F90Predecision `json:"record"`
 SignatureHex string `json:"signature_hex"`
}
// Pin origins must be authenticated OUTSIDE this library; caller-supplied
// matching hexes cannot establish scientific trust.
type F90Pin struct{
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 SignedRecordSHA256 string `json:"signed_record_sha256"`
}
type F90Observation struct{
 Assignment F89PreparedAssignment `json:"assignment"`
 Witness F90SignedPredecision `json:"witness"`
 Pin F90Pin `json:"pin"`
 Classification string `json:"classification"`
 Score int64 `json:"score"`
 ComputeUnits int64 `json:"compute_units"`
 ClaimedOutcomeUnix int64 `json:"claimed_outcome_unix"`
}
type F90ArmPreview struct{
 ArmName string `json:"arm_name"`
 PolicySHA256 string `json:"policy_sha256"`
 Assigned int `json:"assigned"`
 Observed int `json:"observed"`
 Missing int `json:"missing"`
 ScoreIPS string `json:"score_ips,omitempty"`
 ComputeIPS string `json:"compute_ips,omitempty"`
}
type F90LaneAudit struct{
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 SignedWitnessClaimsConsistent bool `json:"signed_witness_claims_consistent"`
 ReportedTimeSequenceConsistent bool `json:"reported_time_sequence_consistent"`
 SourceOnlyAssignmentCount int `json:"source_only_assignment_count"`
 MissingOutcomes int `json:"missing_outcomes"`
 Arms []F90ArmPreview `json:"arms"`
}
type F90ReadOnlyAudit struct{
 Schema string `json:"schema"`
 Lanes []F90LaneAudit `json:"lanes"`
 SourceCryptographyConsistent bool `json:"source_cryptography_consistent"`
 ExactPolicyArmProbabilityNumerator int `json:"exact_policy_arm_probability_numerator"`
 ExactPolicyArmProbabilityDenominator int `json:"exact_policy_arm_probability_denominator"`
 RealPreOutcomeCustodyIndependentlyProven bool `json:"real_pre_outcome_custody_independently_proven"`
 AuthenticRandomnessIndependentlyProven bool `json:"authentic_randomness_independently_proven"`
 CompleteOwnerLeaseHistoryVerified bool `json:"complete_owner_lease_history_verified"`
 FirstUseOriginalIndependentlyVerified bool `json:"first_use_original_independently_verified"`
 CausalGainScientificallyEstablished bool `json:"causal_gain_scientifically_established"`
 DreamParetoActivationAuthorized bool `json:"dream_pareto_activation_authorized"`
 ThetaEvolveAcceptedTrainingEnabled bool `json:"theta_evolve_accepted_training_enabled"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedReferenceMutation bool `json:"accepted_reference_mutation"`
 Status string `json:"status"`
}
func f90Hash(raw []byte)string{
 sum:=sha256.Sum256(raw);return hex.EncodeToString(sum[:])
}
func f90ClassAllowed(s string)bool{
 switch s{
 case "SUPPORTED","NEGATIVE","MIXED","INVALID","CONSUMED_INDETERMINATE","MISSING":return true
 default:return false
 }
}
// f90VerifyWitness verifies only cryptographic agreement with a SUPPLIED pin.
// Neither the source of the pin nor the recorded times is authenticated here.
func f90VerifyWitness(f FrozenSixPolicyTrial,o F90Observation)error{
 w:=o.Witness.Record
 if ValidateF89Prepared(f,o.Assignment)!=nil||
  w.Schema!=F90WitnessSchema||w.Lane!=f.Lane||
  w.FrozenDesignSHA256!=F89FreezeDigest(f)||
  w.AssignmentSHA256!=o.Assignment.AssignmentSHA256||
  w.OwnerSourceSHA!=f.OwnerSourceSHA||
  w.PreregistrationSHA256!=f.PreregistrationSHA256||
  w.CandidateSlateSHA256!=f.CandidateSlateSHA256||
  !exactHex(w.OriginalReceiptSHA256,64)||
  !exactHex(o.Pin.WitnessPublicKeyHex,64)||
  !exactHex(o.Pin.SignedRecordSHA256,64)||
  !exactHex(o.Witness.SignatureHex,128)||
  w.Sequence==0||w.ClaimedPredecisionUnix<=0||
  o.ClaimedOutcomeUnix<=w.ClaimedPredecisionUnix||
  !f90ClassAllowed(o.Classification){return ErrF90}
 if o.Classification=="MISSING"{
  if o.Score!=0||o.ComputeUnits!=0{return ErrF90}
 }else{
  if o.Score<0||o.Score>100||o.ComputeUnits<1||o.ComputeUnits>1000000{return ErrF90}
  if (o.Classification=="INVALID"||o.Classification=="CONSUMED_INDETERMINATE")&&o.Score!=0{return ErrF90}
 }
 raw,err:=json.Marshal(w)
 if err!=nil||f90Hash(raw)!=o.Pin.SignedRecordSHA256{return ErrF90}
 key,err:=hex.DecodeString(o.Pin.WitnessPublicKeyHex)
 if err!=nil||len(key)!=ed25519.PublicKeySize{return ErrF90}
 sig,err:=hex.DecodeString(o.Witness.SignatureHex)
 if err!=nil||len(sig)!=ed25519.SignatureSize||
  !ed25519.Verify(ed25519.PublicKey(key),append([]byte(F90SignatureDomain),raw...),sig){
  return ErrF90
 }
 return nil
}
func f90AuditLane(f FrozenSixPolicyTrial,rows []F90Observation)(F90LaneAudit,error){
 var empty F90LaneAudit
 // Bounded higher-cardinality prospective cohorts are necessary for any
 // meaningful six-arm familywise error control; a 128-row cap would make
 // virtually every nontrivial confidence interval inconclusive.
 if ValidateF89Freeze(f)!=nil||len(rows)<1||len(rows)>16384{return empty,ErrF90}
 names,policies:=f89Arms(f)
 out:=F90LaneAudit{Lane:f.Lane,FrozenDesignSHA256:F89FreezeDigest(f),
  SourceOnlyAssignmentCount:len(rows),SignedWitnessClaimsConsistent:true,
  ReportedTimeSequenceConsistent:true,Arms:make([]F90ArmPreview,6)}
 for i:=range out.Arms{
  out.Arms[i]=F90ArmPreview{ArmName:names[i],PolicySHA256:policies[i]}
 }
 usedAssignment:=map[string]bool{}
 usedDraw:=map[string]bool{}
 usedReceipt:=map[string]bool{}
 usedWitness:=map[string]bool{}
 var prevSeq uint64
 var prevClaimedUnix int64
 var score [6]int64
 var compute [6]int64
 for idx,o:=range rows{
  if f90VerifyWitness(f,o)!=nil{return empty,ErrF90}
  w:=o.Witness.Record
  if usedAssignment[o.Assignment.AssignmentSHA256]||
   usedDraw[o.Assignment.RandomDrawHex]||
   usedReceipt[w.OriginalReceiptSHA256]||
   usedWitness[o.Pin.SignedRecordSHA256]||
   w.Sequence<=prevSeq||w.ClaimedPredecisionUnix<prevClaimedUnix{return empty,ErrF90}
  if idx==0{out.WitnessPublicKeyHex=o.Pin.WitnessPublicKeyHex}
  if out.WitnessPublicKeyHex!=o.Pin.WitnessPublicKeyHex{return empty,ErrF90}
  prevSeq=w.Sequence;prevClaimedUnix=w.ClaimedPredecisionUnix
  usedAssignment[o.Assignment.AssignmentSHA256]=true
  usedDraw[o.Assignment.RandomDrawHex]=true
  usedReceipt[w.OriginalReceiptSHA256]=true
  usedWitness[o.Pin.SignedRecordSHA256]=true
  a:=&out.Arms[o.Assignment.ArmIndex];a.Assigned++
  if o.Classification=="MISSING"{a.Missing++;out.MissingOutcomes++;continue}
  a.Observed++;score[o.Assignment.ArmIndex]+=o.Score
  compute[o.Assignment.ArmIndex]+=o.ComputeUnits
 }
 // If any outcome is missing, DO NOT silently score it as failure or
 // publish a partial propensity-weighted comparison.
 if out.MissingOutcomes==0{
  for i:=range out.Arms{
   out.Arms[i].ScoreIPS=new(big.Rat).SetFrac(
    big.NewInt(score[i]*6),big.NewInt(int64(len(rows)))).RatString()
   out.Arms[i].ComputeIPS=new(big.Rat).SetFrac(
    big.NewInt(compute[i]*6),big.NewInt(int64(len(rows)))).RatString()
  }
 }
 return out,nil
}

// AuditF90PreparedOutcomes verifies TWO separate F89 source-only populations.
// A successful audit reports CRYPTOGRAPHIC CONSISTENCY, NOT an independently
// authentic witnessed experiment or a causal proof. No operational authority
// interface or external network credential is accepted.
func AuditF90PreparedOutcomes(w FrozenSixPolicyTrial,wr []F90Observation,
 y FrozenSixPolicyTrial,yr []F90Observation)(F90ReadOnlyAudit,error){
 var zero F90ReadOnlyAudit
 if len(wr)==0||len(yr)==0||ValidateF89Pair(w,wr[0].Assignment,y,yr[0].Assignment)!=nil{
  return zero,ErrF90
 }
 wa,err:=f90AuditLane(w,wr);if err!=nil{return zero,ErrF90}
 ya,err:=f90AuditLane(y,yr);if err!=nil{return zero,ErrF90}
 if wa.WitnessPublicKeyHex==ya.WitnessPublicKeyHex{return zero,ErrF90}
 // Forbid source reuse between lanes even when each separately parses.
 seen:=map[string]bool{}
 for _,cohort:=range [][]F90Observation{wr,yr}{
  for _,o:=range cohort{
   fields:=[]string{o.Assignment.AssignmentSHA256,
    o.Witness.Record.OriginalReceiptSHA256,o.Pin.SignedRecordSHA256,
    o.Assignment.RandomDrawHex}
   for _,field:=range fields{if seen[field]{return zero,ErrF90};seen[field]=true}
  }
 }
 return F90ReadOnlyAudit{Schema:F90AuditSchema,Lanes:[]F90LaneAudit{wa,ya},
  SourceCryptographyConsistent:true,
  ExactPolicyArmProbabilityNumerator:1,ExactPolicyArmProbabilityDenominator:6,
  Status:"SOURCE_ONLY_SIGNED_CLAIMS_NOT_INDEPENDENTLY_WITNESSED_NO_SCIENCE_AUTHORITY"},nil
}
