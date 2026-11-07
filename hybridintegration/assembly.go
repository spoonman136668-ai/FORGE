// Package hybridintegration composes independently staged Hybrid read-only
// research checks. It has no network, worker, scheduler, lease, credential,
// scientific classification, first-use authority, or dispatch API.
package hybridintegration

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"

 "github.com/spoonman136668-ai/forge/hybridcustody"
 "github.com/spoonman136668-ai/forge/hybridresearch"
 "github.com/spoonman136668-ai/forge/hybridrunnerpreview"
 "github.com/spoonman136668-ai/forge/researchobserver"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/researchstatepreview"
)

const (
 Schema = "forge.hybrid.inactive-research-assembly.v1"
 Mode = "INACTIVE_OFFLINE_CONSISTENCY_NO_TRAINING_OR_SCIENCE"
)
var ErrBlocked = errors.New("FORGE_HYBRID_INACTIVE_ASSEMBLY_BLOCKED")

type Input struct {
 WinglessWorkflowRaw []byte
 YggdrasilWorkflowRaw []byte
 HybridWorkflowRaw []byte
 CandidateSnapshotRaw []byte
 SelectedExperimentID string
 ProtocolRaw []byte
 ArtifactRaw []byte
 StatementRaw []byte
 Signature []byte
 Expected hybridcustody.Expected
 LegacyJournal researchstate.Journal
 ExpectedLegacyHeadSHA256 string
 HybridShadowEvents []researchstatepreview.Event
 RunnerRequest hybridrunnerpreview.Request
 Host hybridrunnerpreview.HostObservation
 Attempts []hybridrunnerpreview.Attempt
 NowUnix uint64
 // This is a caller claim, NOT the FORGE two-lane journal head.
 // An actual Hybrid first-use witness must authenticate it separately.
 ClaimedHybridFirstUseLedgerHeadSHA256 string
}
type Result struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Repository string `json:"repository"`
 ExperimentID string `json:"experiment_id"`
 SourceSHA string `json:"source_sha"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 WorkflowRunID uint64 `json:"workflow_run_id"`
 WorkflowAttempt uint64 `json:"workflow_attempt"`
 CandidateSnapshotSHA256 string `json:"candidate_snapshot_sha256"`
 WorkflowSnapshotSHA256 string `json:"workflow_snapshot_sha256"`
 LegacyTwoLaneJournalSHA256 string `json:"legacy_two_lane_journal_sha256"`
 EvidenceAttestationSHA256 string `json:"evidence_attestation_sha256"`
 Handoff hybridrunnerpreview.Handoff `json:"handoff"`
 IndependentGitHubSourceAuthenticated bool `json:"independent_github_source_authenticated"`
 IndependentHybridFirstUseAuthenticated bool `json:"independent_hybrid_first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ResearchDispatched bool `json:"research_dispatched"`
}
func hash(b []byte)string {
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:])
}
// Assemble runs the actual source parsers and signature consistency verifier
// on supplied bytes. No result is a claim of genuine independent custody.
func Assemble(in Input)(Result,error){
 var zero Result
 observed,err:=researchobserver.BuildWithHybrid(in.WinglessWorkflowRaw,
  in.YggdrasilWorkflowRaw,in.HybridWorkflowRaw)
 if err!=nil||observed.Hybrid==nil||observed.ScientificAccepted||
  observed.ExecutionAuthorized||observed.AcceptedRefMutation||
  observed.ResearchOriginalsExecuted!=0{return zero,ErrBlocked}
 candidates,err:=hybridresearch.Inspect(in.CandidateSnapshotRaw)
 if err!=nil||candidates.ScientificAccepted||candidates.ExecutionAuthorized||
  candidates.TrainingExecuted||candidates.OriginalFirstUseAuthenticated{
  return zero,ErrBlocked
 }
 if hybridresearch.VerifyOutput(candidates)!=nil{return zero,ErrBlocked}
 attested,err:=hybridcustody.Verify(in.ProtocolRaw,in.ArtifactRaw,
  in.StatementRaw,in.Signature,in.Expected)
 if err!=nil||attested.EvidenceKind!="ENGINEERING_RECEIPT"||
  !attested.SignatureVerified||!attested.PayloadDigestsMatch||
  attested.GitHubSourceAuthenticated||attested.FirstUseAuthenticated||
  attested.ExecutionAuthorized||attested.ScientificAccepted{return zero,ErrBlocked}
 req:=in.RunnerRequest
 if in.SelectedExperimentID==""||req.Repository!=hybridcustody.Project||
  req.SourceSHA!=attested.SourceSHA||req.PullRequest!=attested.PullRequest||
  req.ProtocolSHA256!=attested.ProtocolSHA256{return zero,ErrBlocked}
 foundCandidate:=false
 for _,candidate:=range candidates.Candidates{
  if candidate.ExperimentID!=in.SelectedExperimentID{continue}
  if foundCandidate||candidate.SourceAuthenticated||
   candidate.OriginalFirstUseAuthenticated||candidate.ScientificAccepted||
   candidate.HeadSHA!=req.SourceSHA||
   candidate.PullRequest!=req.PullRequest||
   candidate.PullRequestURL!=req.PullRequestURL||
   candidate.ProtocolSHA256!=req.ProtocolSHA256{return zero,ErrBlocked}
  foundCandidate=true
 }
 if !foundCandidate{return zero,ErrBlocked}
 foundRun:=false
 for _,run:=range observed.Hybrid.Runs{
  if run.RunID!=attested.WorkflowRunID||run.RunAttempt!=attested.WorkflowAttempt{continue}
  if foundRun||run.HeadSHA!=req.SourceSHA||
   run.Status!="completed"||run.Conclusion!="success"||
   run.ScientificClassification!="UNVERIFIED_NOT_A_SCIENTIFIC_RESULT"||
   run.ScientificAccepted||run.OriginalFirstUseReconciled{return zero,ErrBlocked}
  foundRun=true
 }
 if !foundRun{return zero,ErrBlocked}
 shadow,err:=researchstatepreview.Build(in.LegacyJournal,
  in.ExpectedLegacyHeadSHA256,in.HybridShadowEvents)
 if err!=nil||shadow.ExecutionAuthorized||shadow.FirstUseAuthenticated||
  shadow.ScientificAccepted{return zero,ErrBlocked}
 latest:=researchstatepreview.Phase("")
 for _,event:=range shadow.Hybrid{
  if event.ExperimentID!=in.SelectedExperimentID{continue}
  if event.ProtocolSHA256!=req.ProtocolSHA256{return zero,ErrBlocked}
  latest=event.To
 }
 if latest!=researchstatepreview.ProtocolFrozen&&
  latest!=researchstatepreview.EngineeringChecked{return zero,ErrBlocked}
 review,err:=hybridrunnerpreview.Evaluate(req,in.Host,in.Attempts,in.NowUnix)
 if err!=nil||hybridrunnerpreview.AssertNonAuthorizing(review)!=nil{return zero,ErrBlocked}
 refs:=hybridrunnerpreview.CustodyReferences{
  Repository:req.Repository,SourceSHA:req.SourceSHA,
  ProtocolSHA256:req.ProtocolSHA256,
  SignedAttestationSHA256:attested.AttestationSHA256,
  ArtifactSHA256:attested.ArtifactSHA256,
  ClaimedSignerKeySHA256:attested.PublicKeySHA256,
  ClaimedOriginalLedgerHeadSHA256:in.ClaimedHybridFirstUseLedgerHeadSHA256,
 }
 handoff,err:=hybridrunnerpreview.BuildDisabledHandoff(req,review,refs)
 if err!=nil||hybridrunnerpreview.VerifyDisabledHandoff(handoff)!=nil{return zero,ErrBlocked}
 result:=Result{
  Schema:Schema,Mode:Mode,Repository:req.Repository,
  ExperimentID:in.SelectedExperimentID,SourceSHA:req.SourceSHA,
  ProtocolSHA256:req.ProtocolSHA256,WorkflowRunID:attested.WorkflowRunID,
  WorkflowAttempt:attested.WorkflowAttempt,
  CandidateSnapshotSHA256:candidates.SnapshotSHA256,
  WorkflowSnapshotSHA256:observed.Hybrid.InputRawSHA256,
  LegacyTwoLaneJournalSHA256:shadow.LegacyJournalSHA256,
  EvidenceAttestationSHA256:attested.AttestationSHA256,
  Handoff:handoff,
 }
 if Validate(result)!=nil{return zero,ErrBlocked}
 return result,nil
}
func Validate(r Result)error {
 if r.Schema!=Schema||r.Mode!=Mode||
  r.Repository!=hybridcustody.Project||r.ExperimentID==""||
  r.IndependentGitHubSourceAuthenticated||
  r.IndependentHybridFirstUseAuthenticated||r.ScientificAccepted||
  r.ExecutionAuthorized||r.ResearchDispatched||
  r.Handoff.ExecutionAuthorized||r.Handoff.FirstUseAuthenticated||
  r.Handoff.SourceAuthenticated||r.Handoff.GPUReserved||
  r.Handoff.Repository!=r.Repository||
  r.Handoff.Mode!=hybridrunnerpreview.HandoffMode||
  r.EvidenceAttestationSHA256==""||
  r.Handoff.HandoffSHA256==""||
  r.Handoff.RequiresIndependentSourceAndFirstUseWitness==false||
  !validHex(r.SourceSHA,40)||!validHex(r.ProtocolSHA256,64)||
  !validHex(r.CandidateSnapshotSHA256,64)||
  !validHex(r.WorkflowSnapshotSHA256,64)||
  !validHex(r.LegacyTwoLaneJournalSHA256,64)||
  !validHex(r.EvidenceAttestationSHA256,64)||
  hybridrunnerpreview.VerifyDisabledHandoff(r.Handoff)!=nil{return ErrBlocked}
 return nil
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
