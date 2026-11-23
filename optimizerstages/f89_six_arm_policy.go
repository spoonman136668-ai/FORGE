// Package optimizerstages contains non-executing FORGE-native research-policy
// preparation. F89 fixes the design of a six-arm randomized selection trial;
// a prepared assignment is never a research original or an owner witness.
package optimizerstages

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
)

const F89FreezeSchema = "forge.optimizer.f89.frozen-six-policy-trial.v1"
const F89PreparedSchema = "forge.optimizer.f89.unwitnessed-predecision.v1"
const F89Status = "PREPARED_UNWITNESSED_NOT_FIRSTUSE_OR_PROSPECTIVE_EVIDENCE"
var ErrF89 = errors.New("FORGE_F89_PROSPECTIVE_TRIAL_FREEZE_OR_OWNER_WITNESS_REQUIRED")

// FrozenSixPolicyTrial is fixed BEFORE the candidate slate or outcomes are
// evaluated. The four control policies have distinct exact source identities.
// This object is a source-only trial design, not an approved preregistration.
type FrozenSixPolicyTrial struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 OwnerSourceSHA string `json:"owner_source_sha"`
 PreregistrationSHA256 string `json:"preregistration_sha256"`
 CandidateSlateSHA256 string `json:"candidate_slate_sha256"`
 SourceFamilySHA256 string `json:"source_family_sha256"`
 BudgetSHA256 string `json:"budget_sha256"`
 Controls [4]string `json:"controls"`
 DreamPolicySHA256 string `json:"dream_policy_sha256"`
 ParetoPolicySHA256 string `json:"pareto_policy_sha256"`
}

// F89PreparedAssignment contains the exact probability 1/6 of a POLICY ARM,
// not the research-ACTION propensity consumed by Dream-RSI's existing replay.
// No timing, randomness independence, owner or once-only permission is implied.
type F89PreparedAssignment struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenDesignSHA256 string `json:"frozen_design_sha256"`
 ArmIndex int `json:"arm_index"`
 ArmName string `json:"arm_name"`
 PolicySHA256 string `json:"policy_sha256"`
 RandomDrawHex string `json:"random_draw_hex"`
 ExactArmPropensityNumerator int `json:"exact_arm_propensity_numerator"`
 ExactArmPropensityDenominator int `json:"exact_arm_propensity_denominator"`
 AssignmentSHA256 string `json:"assignment_sha256"`
 IndependentRandomnessVerified bool `json:"independent_randomness_verified"`
 ExternallyWitnessedBeforeOutcome bool `json:"externally_witnessed_before_outcome"`
 OwnerFirstUseAuthenticated bool `json:"owner_firstuse_authenticated"`
 CausalGainEstablished bool `json:"causal_gain_established"`
 PolicyPromotionAuthorized bool `json:"policy_promotion_authorized"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 Status string `json:"status"`
}

func f89Digest(domain string, v any)string{
 b,_:=json.Marshal(v)
 d:=sha256.Sum256(append([]byte(domain+"\n"),b...))
 return hex.EncodeToString(d[:])
}
func F89FreezeDigest(f FrozenSixPolicyTrial)string{return f89Digest("FORGE-F89-SIX-POLICY-DESIGN-V1",f)}
func f89AssignmentDigest(a F89PreparedAssignment)string{
 a.AssignmentSHA256=""
 return f89Digest("FORGE-F89-UNWITNESSED-ASSIGNMENT-V1",a)
}
func f89Arms(f FrozenSixPolicyTrial)([6]string,[6]string){
 return [6]string{"control_1","control_2","control_3","control_4","dream_rsi","shinka_pareto"},
 [6]string{f.Controls[0],f.Controls[1],f.Controls[2],f.Controls[3],f.DreamPolicySHA256,f.ParetoPolicySHA256}
}
func ValidateF89Freeze(f FrozenSixPolicyTrial)error{
 if f.Schema!=F89FreezeSchema||!checkLane(f.Lane)||f.Epoch==0||
  !exactHex(f.OwnerSourceSHA,40)||!exactHex(f.PreregistrationSHA256,64)||
  !exactHex(f.CandidateSlateSHA256,64)||!exactHex(f.SourceFamilySHA256,64)||
  !exactHex(f.BudgetSHA256,64){return ErrF89}
 identities:=map[string]bool{}
 for _,s:=range []string{f.PreregistrationSHA256,f.CandidateSlateSHA256,f.SourceFamilySHA256,f.BudgetSHA256}{
  if identities[s]{return ErrF89};identities[s]=true
 }
 _,arms:=f89Arms(f)
 seen:=map[string]bool{}
 for _,s:=range arms{
  if !exactHex(s,64)||seen[s]||identities[s]{return ErrF89}
  seen[s]=true
 }
 return nil
}

// f89Draw uses unbiased integer rejection sampling. 2^64 modulo 6 leaves
// remainder four: exclude precisely 2^64-4 through 2^64-1. No rounded
// 1666/1667-basis-point substitute is permitted.
func f89Draw(random io.Reader)(int,string,error){
 if random==nil{return 0,"",ErrF89}
 var bytes [8]byte
 for attempt:=0;attempt<16;attempt++{
  if _,err:=io.ReadFull(random,bytes[:]);err!=nil{return 0,"",ErrF89}
  v:=binary.BigEndian.Uint64(bytes[:])
  if v>=^uint64(0)-3{continue}
  return int(v%6),hex.EncodeToString(bytes[:]),nil
 }
 return 0,"",ErrF89
}

// PrepareF89Selection consumes caller-provided draw bytes but DOES NOT
// independently certify entropy, timestamp, registered owner or first-use.
// The returned record is always UNWITNESSED and has no execution privileges.
func PrepareF89Selection(f FrozenSixPolicyTrial,random io.Reader)(F89PreparedAssignment,error){
 var zero F89PreparedAssignment
 if err:=ValidateF89Freeze(f);err!=nil{return zero,err}
 choice,draw,err:=f89Draw(random)
 if err!=nil{return zero,err}
 names,arms:=f89Arms(f)
 a:=F89PreparedAssignment{
  Schema:F89PreparedSchema,Lane:f.Lane,FrozenDesignSHA256:F89FreezeDigest(f),
  ArmIndex:choice,ArmName:names[choice],PolicySHA256:arms[choice],
  RandomDrawHex:draw,ExactArmPropensityNumerator:1,ExactArmPropensityDenominator:6,
  Status:F89Status,
 }
 a.AssignmentSHA256=f89AssignmentDigest(a)
 if err:=ValidateF89Prepared(f,a);err!=nil{return zero,err}
 return a,nil
}
func ValidateF89Prepared(f FrozenSixPolicyTrial,a F89PreparedAssignment)error{
 if ValidateF89Freeze(f)!=nil||a.Schema!=F89PreparedSchema||a.Lane!=f.Lane||
  a.FrozenDesignSHA256!=F89FreezeDigest(f)||
  a.ArmIndex<0||a.ArmIndex>=6||
  a.ExactArmPropensityNumerator!=1||a.ExactArmPropensityDenominator!=6||
  a.Status!=F89Status||a.IndependentRandomnessVerified||
  a.ExternallyWitnessedBeforeOutcome||a.OwnerFirstUseAuthenticated||
  a.CausalGainEstablished||a.PolicyPromotionAuthorized||
  a.ScientificOriginalDispatchAuthorized{return ErrF89}
 names,arms:=f89Arms(f)
 if a.ArmName!=names[a.ArmIndex]||a.PolicySHA256!=arms[a.ArmIndex]||
  len(a.RandomDrawHex)!=16||!exactHex(a.AssignmentSHA256,64)||
  a.AssignmentSHA256!=f89AssignmentDigest(a){return ErrF89}
 raw,err:=hex.DecodeString(a.RandomDrawHex)
 if err!=nil||len(raw)!=8{return ErrF89}
 v:=binary.BigEndian.Uint64(raw)
 if v>=^uint64(0)-3||int(v%6)!=a.ArmIndex{return ErrF89}
 return nil
}

// ValidateF89Pair ensures a future two-lane trial would not reuse a frozen
// slate, source family, preregistration, assignment or random draw. Even a
// valid pair remains mere source-only preparation.
func ValidateF89Pair(w FrozenSixPolicyTrial,wa F89PreparedAssignment,
 y FrozenSixPolicyTrial,ya F89PreparedAssignment)error{
 if w.Lane!="Wingless"||y.Lane!="Yggdrasil"||
  ValidateF89Prepared(w,wa)!=nil||ValidateF89Prepared(y,ya)!=nil||
  w.OwnerSourceSHA==y.OwnerSourceSHA||
  w.PreregistrationSHA256==y.PreregistrationSHA256||
  w.CandidateSlateSHA256==y.CandidateSlateSHA256||
  w.SourceFamilySHA256==y.SourceFamilySHA256||
  wa.FrozenDesignSHA256==ya.FrozenDesignSHA256||
  wa.AssignmentSHA256==ya.AssignmentSHA256||
  wa.RandomDrawHex==ya.RandomDrawHex{return ErrF89}
 return nil
}
