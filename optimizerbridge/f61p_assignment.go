package optimizerbridge

// F61P is an exact six-arm, pre-outcome assignment PREPARATION utility for the
// already-authorized scientific owner. It cannot independently validate the
// random source, register first-use, authorize an original or promote a policy.
// An external owner must durably publish and independently witness the record
// BEFORE the corresponding research-selection outcome exists.
import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
)

const F61PilotSchema="forge.optimizer.f61p.six-arm-owner-predecision-preparation.v1"
const F61PilotDomain="FORGE-F61P-SIX-ARM-PREDECISION-V1\x00"
var ErrF61Pilot=errors.New("FORGE_F61P_OWNER_PREDECISION_REGISTRATION_NOT_QUALIFIED")

type F61PilotArm struct {
 Name string `json:"name"`
 PolicySHA256 string `json:"policy_sha256"`
}
type F61PilotAssignment struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenControlRegistrySHA256 string `json:"frozen_control_registry_sha256"`
 OwnerPreregistrationSHA256 string `json:"owner_preregistration_sha256"`
 OwnerSourceSHA string `json:"owner_source_sha"`
 PublicCandidateSlateSHA256 string `json:"public_candidate_slate_sha256"`
 PublicSourceFamilySHA256 string `json:"public_source_family_sha256"`
 BudgetCommitmentSHA256 string `json:"budget_commitment_sha256"`
 SixPolicyArms []F61PilotArm `json:"six_policy_arms"`
 ChoiceIndex int `json:"choice_index"`
 ChosenArm F61PilotArm `json:"chosen_arm"`
 RandomDrawHex string `json:"random_draw_hex"`
 RandomizationAlgorithm string `json:"randomization_algorithm"`
 LoggedPropensityNumerator int `json:"logged_propensity_numerator"`
 LoggedPropensityDenominator int `json:"logged_propensity_denominator"`
 AssignmentSHA256 string `json:"assignment_sha256"`
 ExternalRandomnessAndTimeAudited bool `json:"external_randomness_and_time_audited"`
 ExternallyWitnessedPredecisionRegistration bool `json:"externally_witnessed_predecision_registration"`
 AtomicFirstUseClaimConsumed bool `json:"atomic_firstuse_claim_consumed"`
 GenuineScientificOriginalAuthorized bool `json:"genuine_scientific_original_authorized"`
 PolicyAcceptedOrPromoted bool `json:"policy_accepted_or_promoted"`
 Status string `json:"status"`
}
func f61Digest(a F61PilotAssignment)string {
 a.AssignmentSHA256=""
 raw,_:=json.Marshal(a)
 s:=sha256.Sum256(append([]byte(F61PilotDomain),raw...))
 return hex.EncodeToString(s[:])
}

// Exactly unbiased integer sampling from [0,6) on an 8-byte raw draw.
// 2^64 leaves remainder 4 on division by 6. Excluding the last four
// uint64 values prevents modulo bias; all six arms have probability 1/6.
// Do not round this exact propensity into 1666/1667 basis points.
func f61Draw(random io.Reader)(int,string,error) {
 if random==nil{return 0,"",ErrF61Pilot}
 var raw [8]byte
 for i:=0;i<16;i++ {
  if _,err:=io.ReadFull(random,raw[:]);err!=nil{return 0,"",ErrF61Pilot}
  v:=binary.BigEndian.Uint64(raw[:])
  if v>=(^uint64(0))-3{continue}
  return int(v%6),hex.EncodeToString(raw[:]),nil
 }
 return 0,"",ErrF61Pilot
}
func f61Arms(f F58Freeze,n F59PolicyNomination)([]F61PilotArm,error) {
 ready,err:=PreviewEnrollment(f,[]F59PolicyNomination{n})
 if err!=nil||ready.SourceNominatedLanes!=1{return nil,ErrF61Pilot}
 for _,l:=range f.Lanes {
  if l.Lane!=n.Lane{continue}
  arms:=make([]F61PilotArm,0,6)
  for _,c:=range l.Controls{
   arms=append(arms,F61PilotArm{Name:c.Name,PolicySHA256:c.SHA256})
  }
  arms=append(arms,F61PilotArm{Name:"dream_rsi_selected",PolicySHA256:n.DreamPolicySHA256})
  arms=append(arms,F61PilotArm{Name:"shinka_pareto_diverse",PolicySHA256:n.ParetoPolicySHA256})
  return arms,nil
 }
 return nil,ErrF61Pilot
}

// PrepareF61OwnerSelection is called only by an authorized owner with its own
// genuine nomination and future public slate. The returned UNWITNESSED record
// is *not* an owner-executable policy assignment. Owner-side registration,
// independence, atomic once-only claim and authorization remain separate.
func PrepareF61OwnerSelection(f F58Freeze,n F59PolicyNomination,
 slateSHA256,familySHA256,budgetSHA256 string,random io.Reader)(F61PilotAssignment,error){
 var zero F61PilotAssignment
 if !f59Hex(slateSHA256,64)||!f59Hex(familySHA256,64)||
  !f59Hex(budgetSHA256,64)||
  slateSHA256==budgetSHA256||slateSHA256==familySHA256||
  budgetSHA256==familySHA256{return zero,ErrF61Pilot}
 arms,err:=f61Arms(f,n)
 if err!=nil{return zero,ErrF61Pilot}
 seen:=map[string]bool{}
 for _,a:=range arms {
  if seen[a.PolicySHA256]{return zero,ErrF61Pilot}
  seen[a.PolicySHA256]=true
 }
 idx,draw,err:=f61Draw(random)
 if err!=nil{return zero,ErrF61Pilot}
 out:=F61PilotAssignment{
  Schema:F61PilotSchema,Lane:n.Lane,
  FrozenControlRegistrySHA256:n.FrozenControlRegistrySHA256,
  OwnerPreregistrationSHA256:n.OwnerPreregistrationSHA256,
  OwnerSourceSHA:n.PredecisionOwnerSourceSHA,
  PublicCandidateSlateSHA256:slateSHA256,
  PublicSourceFamilySHA256:familySHA256,
  BudgetCommitmentSHA256:budgetSHA256,
  SixPolicyArms:arms,ChoiceIndex:idx,ChosenArm:arms[idx],
  RandomDrawHex:draw,RandomizationAlgorithm:"UINT64_BE_REJECTION_THRESHOLD_18446744073709551612",
  LoggedPropensityNumerator:1,LoggedPropensityDenominator:6,
  Status:"UNWITNESSED_PREDECISION_PREPARATION_NOT_OWNER_FIRSTUSE_PERMISSION",
 }
 out.AssignmentSHA256=f61Digest(out)
 if err:=ValidateF61Prepared(f,n,out);err!=nil{return zero,err}
 return out,nil
}
func ValidateF61Prepared(f F58Freeze,n F59PolicyNomination,a F61PilotAssignment)error {
 arms,err:=f61Arms(f,n)
 if err!=nil||a.Schema!=F61PilotSchema||a.Lane!=n.Lane||
  a.FrozenControlRegistrySHA256!=n.FrozenControlRegistrySHA256||
  a.OwnerPreregistrationSHA256!=n.OwnerPreregistrationSHA256||
  a.OwnerSourceSHA!=n.PredecisionOwnerSourceSHA||
  !f59Hex(a.PublicCandidateSlateSHA256,64)||
  !f59Hex(a.PublicSourceFamilySHA256,64)||
  !f59Hex(a.BudgetCommitmentSHA256,64)||
  a.PublicCandidateSlateSHA256==a.PublicSourceFamilySHA256||
  a.PublicCandidateSlateSHA256==a.BudgetCommitmentSHA256||
  a.PublicSourceFamilySHA256==a.BudgetCommitmentSHA256||
  len(a.SixPolicyArms)!=6||a.ChoiceIndex<0||a.ChoiceIndex>=6||
  a.RandomizationAlgorithm!="UINT64_BE_REJECTION_THRESHOLD_18446744073709551612"||
  a.LoggedPropensityNumerator!=1||a.LoggedPropensityDenominator!=6||
  a.ExternalRandomnessAndTimeAudited||
  a.ExternallyWitnessedPredecisionRegistration||
  a.AtomicFirstUseClaimConsumed||a.GenuineScientificOriginalAuthorized||
  a.PolicyAcceptedOrPromoted||
  a.Status!="UNWITNESSED_PREDECISION_PREPARATION_NOT_OWNER_FIRSTUSE_PERMISSION"{
  return ErrF61Pilot
 }
 for i:=range arms {
  if arms[i]!=a.SixPolicyArms[i]{return ErrF61Pilot}
 }
 if a.ChosenArm!=arms[a.ChoiceIndex]||len(a.RandomDrawHex)!=16{return ErrF61Pilot}
 b,err:=hex.DecodeString(a.RandomDrawHex)
 if err!=nil||len(b)!=8{return ErrF61Pilot}
 v:=binary.BigEndian.Uint64(b)
 if v>=(^uint64(0))-3||int(v%6)!=a.ChoiceIndex||
  !f59Hex(a.AssignmentSHA256,64)||a.AssignmentSHA256!=f61Digest(a){
  return ErrF61Pilot
 }
 return nil
}
