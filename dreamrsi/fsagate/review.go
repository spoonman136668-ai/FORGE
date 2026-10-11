// Package fsagate connects Dream-RSI candidate recommendations with
// FORGE's existing independently anchored, read-only FSA archive verifier.
// It cannot issue admission, claim custody, reserve a cohort or dispatch.
package fsagate

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
 ScopeSchema = "forge.dreamrsi.fsa-review-scope.v1"
 ReviewSchema = "forge.dreamrsi.fsa-review-snapshot.v1"
)
var ErrBlocked=errors.New("FORGE_DREAMRSI_FSA_REVIEW_BLOCKED")
var ErrConsumed=errors.New("FORGE_DREAMRSI_FSA_COHORT_ALREADY_STARTED_OR_REUSED")

// Scope is an EXTERNALLY pinned, frozen FSA review scope. A caller may
// provide it only from independent FSA eligibility records. It must never be
// constructed by the optimizer itself and is not a signing authority.
type Scope struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Generation uint64 `json:"generation"`
 ExperimentID string `json:"experiment_id"`
 HypothesisCommitSHA string `json:"hypothesis_commit_sha"`
 PreregCommitSHA string `json:"prereg_commit_sha"`
 SourceCommitSHA string `json:"source_commit_sha"`
 PreregSHA256 string `json:"prereg_sha256"`
 CandidateCohortSHA256 string `json:"candidate_cohort_sha256"`
 SourceQualificationWitnessSHA256 string `json:"source_qualification_witness_sha256"`
 EligibleHistoricalSourceSHA256 string `json:"eligible_historical_source_sha256"`
 PolicySHA256 string `json:"policy_sha256"`
 PolicyLineageHeadSHA256 string `json:"policy_lineage_head_sha256"`
 FrozenOptimizerSpecSHA256 string `json:"frozen_optimizer_spec_sha256"`
 MaxComputeUnits int `json:"max_compute_units"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
}
type Review struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 Generation uint64 `json:"generation"`
 ExperimentID string `json:"experiment_id"`
 CandidateID string `json:"candidate_id"`
 CandidateCohortSHA256 string `json:"candidate_cohort_sha256"`
 FrozenScopeSHA256 string `json:"frozen_scope_sha256"`
 SignedPredecisionSHA256 string `json:"signed_predecision_sha256"`
 FSAArchiveID string `json:"fsa_archive_id"`
 FSAAuthorityEpoch uint64 `json:"fsa_authority_epoch"`
 FSAHighwaterSequence uint64 `json:"fsa_highwater_sequence"`
 FSAHighwaterHeadSHA256 string `json:"fsa_highwater_head_sha256"`
 SourceQualifiedInAuthenticatedArchive bool `json:"source_qualified_in_authenticated_archive"`
 CohortUnstartedAtObservedHead bool `json:"cohort_unstarted_at_observed_head"`
 EligibilityForFSAReviewOnly bool `json:"eligibility_for_fsa_review_only"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 CohortReserved bool `json:"cohort_reserved"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 ProtectedPhysicalIndependenceProven bool `json:"protected_physical_independence_proven"`
 OriginalEvidenceAudited bool `json:"original_evidence_audited"`
 RandomizationAudited bool `json:"randomization_audited"`
}
func hexValid(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func idValid(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'){return false}
 }
 return true
}
func (s Scope) valid()bool{
 if s.Schema!=ScopeSchema||s.Lane!="Wingless"&&s.Lane!="Yggdrasil"||
  s.Generation<1||s.Generation>1000000000||!idValid(s.ExperimentID)||
  !hexValid(s.HypothesisCommitSHA,40)||!hexValid(s.PreregCommitSHA,40)||
  !hexValid(s.SourceCommitSHA,40)||!hexValid(s.PreregSHA256,64)||
  !hexValid(s.CandidateCohortSHA256,64)||
  !hexValid(s.SourceQualificationWitnessSHA256,64)||
  !hexValid(s.EligibleHistoricalSourceSHA256,64)||
  !hexValid(s.PolicySHA256,64)||!hexValid(s.PolicyLineageHeadSHA256,64)||
  !hexValid(s.FrozenOptimizerSpecSHA256,64)||
  s.MaxComputeUnits<1||s.MaxComputeUnits>1000000||s.AuthorityEpoch==0{return false}
 return true
}
func scopeHash(scope Scope)string{
 b,_:=json.Marshal(scope)
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:])
}
func exactlyArchived(j researchlog.Journal,scope Scope)error{
 // The journal's complete phase and cohort consistency is checked by
 // researchlog.Verify before reviewing *every* competing experiment.
 if err:=researchlog.Verify(j);err!=nil{return ErrBlocked}
 seenHyp,seenPrereg,seenSource:=false,false,false
 for _,record:=range j.Entries{
  e:=record.Event
  if e.CohortSHA256==scope.CandidateCohortSHA256&&
   (e.Lane!=scope.Lane||e.ExperimentID!=scope.ExperimentID){
   return ErrConsumed
  }
  if e.Lane!=scope.Lane||e.ExperimentID!=scope.ExperimentID{continue}
  if e.Generation!=scope.Generation{return ErrBlocked}
  switch e.Kind{
  case researchlog.Hypothesis:
   if seenHyp||e.SourceCommitSHA!=scope.HypothesisCommitSHA{return ErrBlocked}
   seenHyp=true
  case researchlog.Preregister:
   if e.SourceCommitSHA!=scope.PreregCommitSHA||!seenHyp||seenPrereg||e.PreregSHA256!=scope.PreregSHA256||
    e.CohortSHA256!=scope.CandidateCohortSHA256{return ErrBlocked}
   seenPrereg=true
  case researchlog.SourceQualified:
   if e.SourceCommitSHA!=scope.SourceCommitSHA||!seenPrereg||seenSource||e.WitnessSHA256!=scope.SourceQualificationWitnessSHA256||
    e.PreregSHA256!=scope.PreregSHA256||
    e.CohortSHA256!=scope.CandidateCohortSHA256{return ErrBlocked}
   seenSource=true
  case researchlog.SourceRepair:
   // A repaired source must enter a fresh review with a fresh FSA snapshot.
   return ErrBlocked
  case researchlog.PrimaryStarted,researchlog.PrimaryTerminal,
   researchlog.IndependentReview,researchlog.FinalArchive:
   return ErrConsumed
  default:return ErrBlocked
  }
 }
 if !seenHyp||!seenPrereg||!seenSource{return ErrBlocked}
 return nil
}
// ReviewAtAuthenticatedHead uses the existing fsatrust.Recover boundary,
// which checks independent anchor identity, archive binding, complete local
// journal consistency and a stable second external read. This is a READ
// operation. It never consumes first-use or writes any archive entry.
func ReviewAtAuthenticatedHead(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 signed prospective.SignedSelection,signaturePin prospective.IndependentPin,
 policy dreamrsi.Policy,request dreamrsi.FSASelectionRequest,
 scope Scope,externalScopeSHA256 string)(Review,error){
 var empty Review
 if ctx==nil||ctx.Err()!=nil||!scope.valid()||
  !hexValid(externalScopeSHA256,64)||scopeHash(scope)!=externalScopeSHA256||
  dreamrsi.ValidateFSARequest(request)!=nil||
  request.Lane!=scope.Lane||request.SourceHistorySHA256!=scope.EligibleHistoricalSourceSHA256||
  request.PolicySHA256!=scope.PolicySHA256||
  request.OptimizerLineageHeadSHA256!=scope.PolicyLineageHeadSHA256||
  request.FrozenSpecSHA256!=scope.FrozenOptimizerSpecSHA256||
  request.CandidateCohortSHA256!=scope.CandidateCohortSHA256||
  identity.AuthorityEpoch!=scope.AuthorityEpoch{return empty,ErrBlocked}
 verified,err:=prospective.VerifySelection(signed,signaturePin,policy)
 if err!=nil{return empty,ErrBlocked}
 d:=verified.Selection
 if d.Lane!=scope.Lane||d.Epoch!=scope.AuthorityEpoch||
  d.SourceCommitSHA!=scope.SourceCommitSHA||
  d.FrozenPreregSHA256!=scope.PreregSHA256||
  d.PolicySHA256!=scope.PolicySHA256||
  d.PolicyLineageSHA256!=scope.PolicyLineageHeadSHA256||
  d.ChosenID!=request.CandidateID||
  d.ChosenCohortSHA256!=request.CandidateCohortSHA256||
  d.MaxComputeUnits!=scope.MaxComputeUnits{return empty,ErrBlocked}
 // No "approval" is inferred from the selected policy or signed envelope.
 // FSA controls the independent archive high-water read and consistency.
 anchored,err:=fsatrust.Recover(ctx,backend,archive,identity)
 if err!=nil{return empty,ErrBlocked}
 if !sameEpoch(anchored,scope){return empty,ErrBlocked}
 journal,err:=archive.Load();if err!=nil{return empty,ErrBlocked}
 if err=exactlyArchived(journal,scope);err!=nil{return empty,err}
 if err=archive.VerifyTrustedHead(anchored.Sequence,anchored.HeadSHA256);err!=nil{return empty,ErrBlocked}
 return Review{
  Schema:ReviewSchema,Mode:"FSA_REVIEW_ONLY_NO_CONSUMPTION",
  Lane:scope.Lane,Generation:scope.Generation,ExperimentID:scope.ExperimentID,
  CandidateID:d.ChosenID,CandidateCohortSHA256:d.ChosenCohortSHA256,
  FrozenScopeSHA256:externalScopeSHA256,
  SignedPredecisionSHA256:verified.SHA256,
  FSAArchiveID:anchored.ArchiveID,FSAAuthorityEpoch:anchored.AuthorityEpoch,
  FSAHighwaterSequence:anchored.Sequence,
  FSAHighwaterHeadSHA256:anchored.HeadSHA256,
  SourceQualifiedInAuthenticatedArchive:true,
  CohortUnstartedAtObservedHead:true,
  EligibilityForFSAReviewOnly:true,
 },nil
}
func sameEpoch(anchor fsahead.Anchor,scope Scope)bool{
 return anchor.AuthorityEpoch==scope.AuthorityEpoch&&anchor.Sequence>=3&&
  hexValid(anchor.ArchiveID,64)&&hexValid(anchor.HeadSHA256,64)
}
// The only interface offered to FSA is a read-only review snapshot. There
// is no Run, Admit, Dispatch, Sign, Commit or CompareAndSwap operation here.
