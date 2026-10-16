package optimizerbridge

// F57StructuralInputs are non-authorizing, externally observed FIT evidence.
// They are NOT signed research-selection trials, independently accepted
// originals or evidence of a Dream/Pareto policy improvement. The existing
// independent science provider must separately verify source custody before
// any proposed mechanism enters future owner research.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

var ErrF57Novelty = errors.New("FORGE_F57_NOVEL_MECHANISM_PROVENANCE_OR_STRUCTURE_BLOCKED")

type F57StructuralInput struct {
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 OriginalFITRun uint64 `json:"original_fit_run"`
 FITResultSHA256 string `json:"fit_result_sha256"`
 IndependentAuditSHA256 string `json:"independent_audit_sha256"`
 FITCases int `json:"fit_cases"`
 CandidateCorrect int `json:"candidate_correct"`
 StrongestFairCorrect int `json:"strongest_fair_correct"`
 DiagnosticExecuted bool `json:"diagnostic_executed"`
 ScientificAccepted bool `json:"scientific_accepted"`
}

type F57NoveltyReview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 SourceInputs []F57StructuralInput `json:"source_inputs"`
 Proposals []StructuralMechanismProposal `json:"proposals"`
 DreamParetoProspectivelyQualified bool `json:"dream_pareto_prospectively_qualified"`
 ThetaEvolveIndependentAcceptanceEligible bool `json:"theta_evolve_independent_acceptance_eligible"`
 NovelProposalsAreOnlyUntested bool `json:"novel_proposals_are_only_untested"`
 ScientificOriginalsExecuted int `json:"scientific_originals_executed"`
 ControllerDispatchAuthorized bool `json:"controller_dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func f57hash(domain string,v any)string{
 bytes,_:=json.Marshal(v)
 d:=sha256.Sum256(append([]byte(domain+"\n"),bytes...))
 return hex.EncodeToString(d[:])
}
func f57InputValid(e F57StructuralInput)bool{
 return checkLane(e.Lane)&&exactHex(e.SourceSHA,40)&&
   exactHex(e.FITResultSHA256,64)&&exactHex(e.IndependentAuditSHA256,64)&&
   e.FITResultSHA256!=e.IndependentAuditSHA256&&e.OriginalFITRun>0&&
   e.FITCases==64&&e.CandidateCorrect>=0&&e.CandidateCorrect<=e.FITCases&&
   e.StrongestFairCorrect>=0&&e.StrongestFairCorrect<=e.FITCases&&
   !e.DiagnosticExecuted&&!e.ScientificAccepted
}
func makeF57StructuralProposal(e F57StructuralInput)(StructuralMechanismProposal,error){
 var p StructuralMechanismProposal
 if !f57InputValid(e){return p,ErrF57Novelty}
 p.Lane=e.Lane
 p.SourceSHA=e.SourceSHA
 p.Status="UNTESTED"
 if e.Lane=="Wingless" {
  p.Generator="Promptbreeder"
  p.ParentRepresentation="independent-seven-state-role-posterior"
  p.NewRepresentation="persistent-role-conditioned-joint-binding-belief"
  p.ParentConsumer="independent-role-marginal-transition"
  p.NewConsumer="trained-reused-role-binding-composer"
  p.ParentTestEnvironment="within-fit-noisy-affine-role-order"
  p.NewTestEnvironment="new-reused-role-inverse-binding-grammar"
 } else {
  p.Generator="DGM/GenEnv"
  p.ParentRepresentation="greedy-lossless-pairwise-chunks"
  p.NewRepresentation="incremental-component-boundary-forest"
  p.ParentConsumer="fixed-online-greedy-component-merge"
  p.NewConsumer="learned-retention-and-boundary-completion"
  p.ParentTestEnvironment="within-fit-segmented-chain-arrivals"
  p.NewTestEnvironment="new-cyclic-and-partial-component-arrivals"
 }
 // Frozen-control identifiers refer to the existing source with exact
 // named baselines, NOT fictitious accepted policies or scientific scores.
 for _,control:=range []string{"source-frozen-reference","source-frozen-equal-budget-control"}{
  p.FrozenControlSHA256=append(p.FrozenControlSHA256,
   f57hash("FORGE-F57-PROPOSAL-CONTROL-V1",struct{
    Lane string `json:"lane"`
    SourceSHA string `json:"source_sha"`
    Control string `json:"control"`
   }{e.Lane,e.SourceSHA,control}))
 }
 // Completely content-addressed: source, observed FIT evidence, changed
 // representation/consumer/environment and control identities.
 p.CandidateSHA256=f57hash("FORGE-F57-NOVEL-PROPOSAL-V1",struct{
  FIT F57StructuralInput `json:"fit"`
  Generator string `json:"generator"`
  ParentRepresentation string `json:"parent_representation"`
  NewRepresentation string `json:"new_representation"`
  ParentConsumer string `json:"parent_consumer"`
  NewConsumer string `json:"new_consumer"`
  ParentTestEnvironment string `json:"parent_test_environment"`
  NewTestEnvironment string `json:"new_test_environment"`
  FrozenControls []string `json:"frozen_controls"`
 }{e,p.Generator,p.ParentRepresentation,p.NewRepresentation,p.ParentConsumer,
  p.NewConsumer,p.ParentTestEnvironment,p.NewTestEnvironment,p.FrozenControlSHA256})
 if !validMechanism(p){return StructuralMechanismProposal{},ErrF57Novelty}
 return p,nil
}

// PrepareF57Novelty routes known FIT results to two structurally different
// untested *proposals*. No policy optimizer, model service, experiment worker,
// accepted-ref writer, FSA, signing authority, or runtime API is invoked.
func PrepareF57Novelty(inputs []F57StructuralInput)(F57NoveltyReview,error){
 var zero F57NoveltyReview
 if len(inputs)!=2||inputs[0].Lane!="Wingless"||inputs[1].Lane!="Yggdrasil"||
  !f57InputValid(inputs[0])||!f57InputValid(inputs[1])||
  inputs[0].SourceSHA==inputs[1].SourceSHA||
  inputs[0].FITResultSHA256==inputs[1].FITResultSHA256||
  inputs[0].IndependentAuditSHA256==inputs[1].IndependentAuditSHA256||
  inputs[0].OriginalFITRun==inputs[1].OriginalFITRun{
  return zero,ErrF57Novelty
 }
 // Concrete observations from the source-free F57 FIT archives: Wingless
 // 49/64 vs frozen 44/64; Yggdrasil causal reference 29/64 vs fixed 29/64.
 // FIT does not establish prospective policy or scientific task gains.
 if inputs[0].CandidateCorrect!=49||inputs[0].StrongestFairCorrect!=44||
  inputs[1].CandidateCorrect!=29||inputs[1].StrongestFairCorrect!=29{
  return zero,ErrF57Novelty
 }
 w,err:=makeF57StructuralProposal(inputs[0])
 if err!=nil{return zero,err}
 y,err:=makeF57StructuralProposal(inputs[1])
 if err!=nil||w.CandidateSHA256==y.CandidateSHA256{return zero,ErrF57Novelty}
 out:=F57NoveltyReview{
  Schema:"forge.f57.authentic-fit-novelty-advisory.v1",
  Mode:"BOUNDED_PROMPTBREEDER_AND_GENENV_STRUCTURAL_PROPOSALS_ONLY",
  SourceInputs:append([]F57StructuralInput(nil),inputs...),
  Proposals:[]StructuralMechanismProposal{w,y},
  NovelProposalsAreOnlyUntested:true}
 return out,nil
}
