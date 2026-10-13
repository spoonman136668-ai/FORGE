// Package qualreuse makes qualified focused-test evidence reusable only for
// its exact, immutable, externally attested scientific source identity.
// It never reuses a full-system regression or grants execution authority.
package qualreuse

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

const (
 Schema="forge.qualification.focused-reuse.v1"
 PlanSchema="forge.qualification.delta-plan.v1"
)
var ErrInvalid=errors.New("FORGE_QUALIFICATION_IDENTITY_OR_PROVENANCE_INVALID")

// Identity is a compositional scientific qualification fingerprint.
// Independent changes to any interface, budget, cohort or preregistration
// invalidate cached focused tests even if the implementation tree is the same.
type Identity struct{
 Lane string `json:"lane"`
 BaselineCommitSHA string `json:"baseline_commit_sha"`
 SourceTreeSHA string `json:"source_tree_sha"`
 PreregistrationBlobSHA string `json:"preregistration_blob_sha"`
 DependenciesTreeSHA string `json:"dependencies_tree_sha"`
 InterfacesTreeSHA string `json:"interfaces_tree_sha"`
 HarnessTreeSHA string `json:"harness_tree_sha"`
 ToolchainSHA256 string `json:"toolchain_sha256"`
 BudgetSHA256 string `json:"budget_sha256"`
 CohortSHA256 string `json:"cohort_sha256"`
 FocusedCommandSHA256 string `json:"focused_command_sha256"`
}

// FocusedReceipt must be authenticated by a separately trusted verifier.
// The bool is a fact supplied by that verifier, NOT cryptographic evidence:
// a caller cannot self-issue accepted cache receipts based on this package.
// Its exact immutable manifest/source identity must be verified externally.
type FocusedReceipt struct{
 Schema string `json:"schema"`
 Identity Identity `json:"identity"`
 QualificationSourceCommitSHA string `json:"qualification_source_commit_sha"`
 IndependentEvidenceSHA256 string `json:"independent_evidence_sha256"`
 SourceBirthProvenanceSHA256 string `json:"source_birth_provenance_sha256"`
 IndependentVerifierAuthenticated bool `json:"independent_verifier_authenticated"`
 FocusedPassed bool `json:"focused_passed"`
 NegativeControlsPassed bool `json:"negative_controls_passed"`
 OriginalFirstUseConsumed bool `json:"original_first_use_consumed"`
 SealedOutcomesRead bool `json:"sealed_outcomes_read"`
 BudgetWidened bool `json:"budget_widened"`
}
type Plan struct{
 Schema string `json:"schema"`
 IdentitySHA256 string `json:"identity_sha256"`
 FocusedTestsReused bool `json:"focused_tests_reused"`
 FocusedTestsRequired bool `json:"focused_tests_required"`
 FullRegressionRequired bool `json:"full_regression_required"`
 BuildRequired bool `json:"build_required"`
 IndependentScientificAdmissionRequired bool `json:"independent_scientific_admission_required"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,x:=range s{
  if !(x>='0'&&x<='9'||x>='a'&&x<='f'){return false}
 }
 return true
}
func Valid(i Identity)bool{
 return (i.Lane=="Wingless"||i.Lane=="Yggdrasil")&&
  validHex(i.BaselineCommitSHA,40)&&validHex(i.SourceTreeSHA,40)&&
  validHex(i.PreregistrationBlobSHA,40)&&validHex(i.DependenciesTreeSHA,40)&&
  validHex(i.InterfacesTreeSHA,40)&&validHex(i.HarnessTreeSHA,40)&&
  validHex(i.ToolchainSHA256,64)&&validHex(i.BudgetSHA256,64)&&
  validHex(i.CohortSHA256,64)&&validHex(i.FocusedCommandSHA256,64)
}
func Digest(i Identity)(string,error){
 if !Valid(i){return "",ErrInvalid}
 b,err:=json.Marshal(i);if err!=nil{return "",ErrInvalid}
 d:=sha256.Sum256(append([]byte("FORGE-QUALIFICATION-COMPOSITION-V1\n"),b...))
 return hex.EncodeToString(d[:]),nil
}
// PlanFocusedReuse only decides whether a bounded FOCUSED qualification can
// be skipped. Full regression and build remain compulsory for EVERY new
// integration or promotion, including an exact focused reuse hit.
//
// nil previously qualified receipt means run focused tests; it never means
// automatically trust a local cache or infer that science may execute.
func PlanFocusedReuse(want Identity, previous *FocusedReceipt)(Plan,error){
 id,err:=Digest(want)
 if err!=nil{return Plan{},err}
 p:=Plan{Schema:PlanSchema,IdentitySHA256:id,
  FocusedTestsRequired:true,FullRegressionRequired:true,BuildRequired:true,
  IndependentScientificAdmissionRequired:true}
 if previous==nil{return p,nil}
 if previous.Schema!=Schema||!Valid(previous.Identity)||
  !validHex(previous.QualificationSourceCommitSHA,40)||
  !validHex(previous.IndependentEvidenceSHA256,64)||
  !validHex(previous.SourceBirthProvenanceSHA256,64)||
  previous.OriginalFirstUseConsumed||previous.SealedOutcomesRead||
  previous.BudgetWidened{return Plan{},ErrInvalid}
 if previous.Identity!=want{return p,nil} // Never reuse on scope drift.
 if previous.IndependentVerifierAuthenticated&&previous.FocusedPassed&&
  previous.NegativeControlsPassed{
  p.FocusedTestsReused=true
  p.FocusedTestsRequired=false
 }
 return p,nil
}
