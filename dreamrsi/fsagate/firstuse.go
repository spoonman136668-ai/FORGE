package fsagate

// R5 binds a signed FSA first-use commitment to an existing, fully verified
// FORGE scientific archive. This module does NOT append, CAS, sign, start or
// dispatch. Only the independently controlled FSA may commit first use.
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/dreamrsi/prospective"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 FirstUsePlanSchema="forge.dreamrsi.fsa-first-use-intent.v1"
 FirstUseProofSchema="forge.dreamrsi.fsa-first-use-observed.v1"
)
var ErrFirstUse=errors.New("FORGE_DREAMRSI_FSA_FIRST_USE_NOT_PROVEN")
var ErrFirstUseUncertain=errors.New("FORGE_DREAMRSI_FSA_FIRST_USE_UNCERTAIN_NO_REPLAY")

type FirstUsePlan struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 Generation uint64 `json:"generation"`
 ExperimentID string `json:"experiment_id"`
 CandidateID string `json:"candidate_id"`
 CohortSHA256 string `json:"cohort_sha256"`
 SourceCommitSHA string `json:"source_commit_sha"`
 PreregSHA256 string `json:"prereg_sha256"`
 SourceQualificationWitnessSHA256 string `json:"source_qualification_witness_sha256"`
 StartWitnessSHA256 string `json:"start_witness_sha256"`
 RunID uint64 `json:"run_id"`
 FSAReviewSHA256 string `json:"fsa_review_sha256"`
 FrozenScopeSHA256 string `json:"frozen_scope_sha256"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 PreviousSequence uint64 `json:"previous_sequence"`
 PreviousHeadSHA256 string `json:"previous_head_sha256"`
 PlannedSequence uint64 `json:"planned_sequence"`
 PlannedStartedRecordSHA256 string `json:"planned_started_record_sha256"`
 FSAFirstUseCommitted bool `json:"fsa_first_use_committed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
type FirstUseProof struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 PlanSHA256 string `json:"plan_sha256"`
 Lane string `json:"lane"`
 CandidateID string `json:"candidate_id"`
 CohortSHA256 string `json:"cohort_sha256"`
 StartedRecordSHA256 string `json:"started_record_sha256"`
 ObservedTrustedSequence uint64 `json:"observed_trusted_sequence"`
 ObservedTrustedHeadSHA256 string `json:"observed_trusted_head_sha256"`
 FSAFirstUseCommitted bool `json:"fsa_first_use_committed"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 PhysicalIndependenceDemonstrated bool `json:"physical_independence_demonstrated"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func canonicalSHA(v any)(string,error){
 b,err:=json.Marshal(v)
 if err!=nil||len(b)==0||len(b)>32768{return "",ErrFirstUse}
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:]),nil
}
func PlanSHA(p FirstUsePlan)(string,error){
 if p.Schema!=FirstUsePlanSchema||p.Mode!="EXTERNAL_FSA_ISSUER_REVIEW_REQUIRED"||
  p.RunID==0||p.AuthorityEpoch==0||p.PlannedSequence!=p.PreviousSequence+1||
  !hexValid(p.PlannedStartedRecordSHA256,64)||!hexValid(p.PreviousHeadSHA256,64)||
  !hexValid(p.ArchiveID,64)||!hexValid(p.StartWitnessSHA256,64)||
  !hexValid(p.FSAReviewSHA256,64)||!hexValid(p.FrozenScopeSHA256,64)||
  p.FSAFirstUseCommitted||p.ScientificAccepted||p.DispatchAuthorized{
  return "",ErrFirstUse
 }
 return canonicalSHA(p)
}
func EventForPlan(p FirstUsePlan) researchlog.Event {
 return researchlog.Event{
  Lane:p.Lane,Generation:p.Generation,ExperimentID:p.ExperimentID,
  Kind:researchlog.PrimaryStarted,SourceCommitSHA:p.SourceCommitSHA,
  PreregSHA256:p.PreregSHA256,CohortSHA256:p.CohortSHA256,
  WitnessSHA256:p.StartWitnessSHA256,RunID:p.RunID,
 }
}
// PrepareFirstUse obtains a NEW authenticated high-water snapshot from R4,
// then projects the exact next STARTED hash through the existing journal.
// It cannot consume a first use, send work or issue a checkpoint signature.
func PrepareFirstUse(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 signed prospective.SignedSelection,pin prospective.IndependentPin,
 policy dreamrsi.Policy,request dreamrsi.FSASelectionRequest,
 scope Scope,scopeSHA,startWitnessSHA string,runID uint64)(FirstUsePlan,error){
 var empty FirstUsePlan
 if ctx==nil||ctx.Err()!=nil||runID==0||!hexValid(startWitnessSHA,64){
  return empty,ErrFirstUse
 }
 review,err:=ReviewAtAuthenticatedHead(ctx,backend,archive,identity,
  signed,pin,policy,request,scope,scopeSHA)
 if err!=nil{return empty,ErrFirstUse}
 j,err:=archive.Load();if err!=nil{return empty,ErrFirstUse}
 if uint64(len(j.Entries))!=review.FSAHighwaterSequence{return empty,ErrFirstUseUncertain}
 reviewSHA,err:=canonicalSHA(review);if err!=nil{return empty,err}
 p:=FirstUsePlan{
  Schema:FirstUsePlanSchema,Mode:"EXTERNAL_FSA_ISSUER_REVIEW_REQUIRED",
  Lane:scope.Lane,Generation:scope.Generation,ExperimentID:scope.ExperimentID,
  CandidateID:review.CandidateID,CohortSHA256:scope.CandidateCohortSHA256,
  SourceCommitSHA:scope.SourceCommitSHA,PreregSHA256:scope.PreregSHA256,
  SourceQualificationWitnessSHA256:scope.SourceQualificationWitnessSHA256,
  StartWitnessSHA256:startWitnessSHA,RunID:runID,
  FSAReviewSHA256:reviewSHA,FrozenScopeSHA256:scopeSHA,
  ArchiveID:review.FSAArchiveID,AuthorityEpoch:review.FSAAuthorityEpoch,
  PreviousSequence:review.FSAHighwaterSequence,
  PreviousHeadSHA256:review.FSAHighwaterHeadSHA256,
 }
 next,err:=researchlog.Append(j,EventForPlan(p))
 if err!=nil{return empty,ErrFirstUse}
 row:=next.Entries[len(next.Entries)-1]
 p.PlannedSequence=row.Sequence
 p.PlannedStartedRecordSHA256=row.RecordSHA256
 if _,err=PlanSHA(p);err!=nil{return empty,err}
 // The FSA must compare this prediction to an independently issued,
 // signed and atomically checkpointed STARTED record in its OWN transaction.
 // No code here writes STARTED evidence or authorizes a worker.
 return p,nil
}
// ProveFSAFirstUse verifies an external FSA checkpoint signature against the
// prior pinned head, the exact STARTED record and an independently read-back
// stable high-water. If a commit is unknown, always fail closed; NEVER repeat.
func ProveFSAFirstUse(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 p FirstUsePlan,externallyPinnedPlanSHA string,
 signedHead fsahead.SignedHead)(FirstUseProof,error){
 var empty FirstUseProof
 claimed,err:=PlanSHA(p)
 if err!=nil||claimed!=externallyPinnedPlanSHA||
  !hexValid(externallyPinnedPlanSHA,64)||
  p.ArchiveID!=identity.ArchiveID||p.AuthorityEpoch!=identity.AuthorityEpoch||
  len(identity.PublicKey)!=32{return empty,ErrFirstUse}
 prior:=fsahead.Anchor{
  ArchiveID:identity.ArchiveID,KeyID:identity.KeyID,
  PublicKey:append([]byte(nil),identity.PublicKey...),
  AuthorityEpoch:identity.AuthorityEpoch,
  Sequence:p.PreviousSequence,HeadSHA256:p.PreviousHeadSHA256,
 }
 after,err:=fsahead.VerifySignature(prior,signedHead)
 if err!=nil||after.Sequence!=p.PlannedSequence||
  after.HeadSHA256!=p.PlannedStartedRecordSHA256{return empty,ErrFirstUse}
 // fsatrust.Recover authenticates the real independently pinned FSA archive
 // and separate readback; no local-only hash can replace it.
 observed,err:=fsatrust.Recover(ctx,backend,archive,identity)
 if err!=nil{return empty,ErrFirstUseUncertain}
 if observed.Sequence!=p.PlannedSequence||
  observed.HeadSHA256!=p.PlannedStartedRecordSHA256||
  observed.ArchiveID!=p.ArchiveID||observed.AuthorityEpoch!=p.AuthorityEpoch{
  return empty,ErrFirstUseUncertain
 }
 journal,err:=archive.Load()
 if err!=nil||uint64(len(journal.Entries))!=p.PlannedSequence{return empty,ErrFirstUseUncertain}
 row:=journal.Entries[len(journal.Entries)-1]
 if row.RecordSHA256!=p.PlannedStartedRecordSHA256||
  row.PreviousSHA256!=p.PreviousHeadSHA256||
  row.Event!=EventForPlan(p){return empty,ErrFirstUseUncertain}
 return FirstUseProof{
  Schema:FirstUseProofSchema,Mode:"EXTERNAL_FSA_FIRST_USE_OBSERVED_NO_DISPATCH",
  PlanSHA256:externallyPinnedPlanSHA,
  Lane:p.Lane,CandidateID:p.CandidateID,CohortSHA256:p.CohortSHA256,
  StartedRecordSHA256:row.RecordSHA256,
  ObservedTrustedSequence:observed.Sequence,
  ObservedTrustedHeadSHA256:observed.HeadSHA256,
  FSAFirstUseCommitted:true,FirstUseConsumed:true,
  PhysicalIndependenceDemonstrated:false,
  ScientificAccepted:false,DispatchAuthorized:false,
  AcceptedRefMutation:false,
 },nil
}
