// Package nativefirstuse defines FORGE's non-executing, fail-closed
// scientific first-use admission boundary. It has no CKB-plane dependency.
// Existing Cloudflare/owner custody must independently verify all records.
// A passing source test or structurally valid receipt cannot issue a permit.
package nativefirstuse

import (
 "errors"
 "strings"
)

var ErrUnverified = errors.New("FORGE_NATIVE_FIRSTUSE_INDEPENDENT_CUSTODY_NOT_QUALIFIED")

const Schema = "forge.native-firstuse.owner-admission.v1"

type Receipt struct {
 Lane string
 SourceSHA string
 FrozenDecisionSHA256 string
 OwnerEpoch uint64
 FirstUseSequence uint64
 GlobalClaimSHA256 string
 FirstUseLedgerHeadSHA256 string
 CloudflareClaimSHA256 string
 PublicSlateSHA256 string
 BudgetSHA256 string
 PolicySHA256 string
 PolicyArmNumerator uint64
 PolicyArmDenominator uint64
 // Existing externally authenticated source, never caller-derived.
 WitnessIdentitySHA256 string
}

type Custody interface {
 // VerifyExternalPredecision must verify externally pinned *pre-outcome*
 // registration, owner epoch, source birth and witness custody.
 VerifyExternalPredecision(Receipt) error
 // VerifyDurableFirstUse must verify once-only atomic Cloudflare state
 // against complete active, consumed and uncertain owner histories.
 VerifyDurableFirstUse(Receipt) error
}

type Review struct {
 Schema string
 Lane string
 ExternalAdmissionEvidenceVerified bool
 ExactPolicyProbabilityNumerator uint64
 ExactPolicyProbabilityDenominator uint64
 SeparateOperationalApprovalRequired bool
 AuthorizedOriginalStart bool
 AuthorizedControllerCutover bool
 AcceptedScientificOutcome bool
 Status string
}

func hex(s string, n int) bool {
 if len(s)!=n{return false}
 for _,r:=range s{if !strings.ContainsRune("0123456789abcdef",r){return false}}
 return true
}

func valid(r Receipt) bool {
 return (r.Lane=="Wingless"||r.Lane=="Yggdrasil") &&
  hex(r.SourceSHA,40)&&r.OwnerEpoch>0&&r.FirstUseSequence>0&&
  hex(r.FrozenDecisionSHA256,64)&&hex(r.GlobalClaimSHA256,64)&&
  hex(r.FirstUseLedgerHeadSHA256,64)&&hex(r.CloudflareClaimSHA256,64)&&
  hex(r.PublicSlateSHA256,64)&&hex(r.BudgetSHA256,64)&&
  hex(r.PolicySHA256,64)&&hex(r.WitnessIdentitySHA256,64)&&
  r.PolicyArmNumerator==1&&r.PolicyArmDenominator==6&&
  r.GlobalClaimSHA256!=r.CloudflareClaimSHA256&&
  r.FrozenDecisionSHA256!=r.PolicySHA256
}

// ReviewNativeFirstUse checks externally verified first-use at the FORGE
// boundary. It never creates/consumes claims or issues dispatch permits.
// A test-only Custody implementation cannot authenticate a live system.
func ReviewNativeFirstUse(r Receipt, custody Custody)(Review,error){
 if !valid(r)||custody==nil{return Review{},ErrUnverified}
 if custody.VerifyExternalPredecision(r)!=nil||
  custody.VerifyDurableFirstUse(r)!=nil{return Review{},ErrUnverified}
 return Review{
  Schema:Schema,Lane:r.Lane,
  ExternalAdmissionEvidenceVerified:true,
  ExactPolicyProbabilityNumerator:1,
  ExactPolicyProbabilityDenominator:6,
  SeparateOperationalApprovalRequired:true,
  Status:"EXTERNAL_CUSTODY_INTERFACE_ACCEPTED_SEPARATE_OWNER_PERMIT_REQUIRED",
 },nil
}

// ReviewNativePair rejects identity reuse or partial research-lane custody.
// There is deliberately no path from this result to running an experiment.
func ReviewNativePair(w,y Receipt,custody Custody)([2]Review,error){
 var empty [2]Review
 if w.Lane!="Wingless"||y.Lane!="Yggdrasil"||
  w.GlobalClaimSHA256==y.GlobalClaimSHA256||
  w.CloudflareClaimSHA256==y.CloudflareClaimSHA256||
  w.WitnessIdentitySHA256==y.WitnessIdentitySHA256||
  w.FirstUseLedgerHeadSHA256==y.FirstUseLedgerHeadSHA256||
  w.SourceSHA==y.SourceSHA||
  w.FrozenDecisionSHA256==y.FrozenDecisionSHA256||
  w.PolicySHA256==y.PolicySHA256{return empty,ErrUnverified}
 a,err:=ReviewNativeFirstUse(w,custody)
 if err!=nil{return empty,ErrUnverified}
 b,err:=ReviewNativeFirstUse(y,custody)
 if err!=nil{return empty,ErrUnverified}
 return [2]Review{a,b},nil
}
