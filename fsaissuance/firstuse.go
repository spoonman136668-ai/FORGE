// Package fsaissuance is the FORGE Scientific Authority-side first-use
// transaction boundary. It has no production issuer, signer, scheduler,
// credential source or scientific execution endpoint.
package fsaissuance

import (
 "context"
 "crypto/ed25519"
 "errors"

 "github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

var (
 ErrDenied=errors.New("FORGE_FSA_ISSUANCE_NOT_INDEPENDENTLY_AUTHORIZED")
 ErrUncertain=errors.New("FORGE_FSA_FIRST_USE_CONSUMED_OR_UNKNOWN_NO_RETRY")
)

// IssuanceRequest is the exact immutable FSA-owned proposal to authorize,
// not a request from an optimizer with write permissions. Independent FSA
// eligibility, source and key custody verification MUST occur inside the
// issuer implementation; this repository supplies no live implementation.
type IssuanceRequest struct {
 PlanSHA256 string
 ArchiveID string
 AuthorityEpoch uint64
 PreviousSequence uint64
 PreviousHeadSHA256 string
 ProposedSequence uint64
 ProposedHeadSHA256 string
 Lane string
 ExperimentID string
 CohortSHA256 string
 SourceQualificationWitnessSHA256 string
}

// Issuer is a capability whose implementation must exist OUTSIDE the
// optimizer's trust boundary, with independently pinned signing authority.
// A fake in tests is not acceptable evidence of off-host custody.
type Issuer interface {
 IssueFirstUse(context.Context,IssuanceRequest)(fsahead.SignedHead,error)
}

func expectedPrior(identity fsatrust.Identity,p fsagate.FirstUsePlan)fsahead.Anchor{
 return fsahead.Anchor{
  ArchiveID:identity.ArchiveID,
  KeyID:identity.KeyID,
  PublicKey:append(ed25519.PublicKey(nil),identity.PublicKey...),
  AuthorityEpoch:identity.AuthorityEpoch,
  Sequence:p.PreviousSequence,HeadSHA256:p.PreviousHeadSHA256,
 }
}

func matchingAnchor(a fsahead.Anchor, p fsagate.FirstUsePlan)bool{
 return a.ArchiveID==p.ArchiveID&&a.AuthorityEpoch==p.AuthorityEpoch&&
  a.Sequence==p.PreviousSequence&&a.HeadSHA256==p.PreviousHeadSHA256
}

// CommitFirstUse makes AT MOST ONE local exclusive STARTED append and AT MOST
// ONE external atomic CAS. Prior to that irreversible operation it requires
// a stable independently authenticated high-water and a fresh FSA-signed
// checkpoint for the exact projected STARTED record.
// All failures following attempted archival mutation are CONSUMED_OR_UNKNOWN.
// Neither an error nor a successful proof is authorization to dispatch science.
func CommitFirstUse(ctx context.Context, backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 issuer Issuer,p fsagate.FirstUsePlan,pinnedPlanSHA string)(fsagate.FirstUseProof,error){
 var empty fsagate.FirstUseProof
 if ctx==nil||ctx.Err()!=nil||backend==nil||archive==nil||issuer==nil||
  len(identity.PublicKey)!=ed25519.PublicKeySize{return empty,ErrDenied}
 actual,err:=fsagate.PlanSHA(p)
 if err!=nil||actual!=pinnedPlanSHA||p.ArchiveID!=identity.ArchiveID||
  p.AuthorityEpoch!=identity.AuthorityEpoch{return empty,ErrDenied}
 // Failure or uncertainty here prohibits issuer, writer AND CAS.
 anchor,err:=fsatrust.Recover(ctx,backend,archive,identity)
 if err!=nil||!matchingAnchor(anchor,p){return empty,ErrDenied}
 journal,err:=archive.Load()
 if err!=nil||uint64(len(journal.Entries))!=p.PreviousSequence{
  return empty,ErrDenied
 }
 projected,err:=researchlog.Append(journal,fsagate.EventForPlan(p))
 if err!=nil||len(projected.Entries)==0{return empty,ErrDenied}
 proposed:=projected.Entries[len(projected.Entries)-1]
 if proposed.Sequence!=p.PlannedSequence||
  proposed.RecordSHA256!=p.PlannedStartedRecordSHA256||
  proposed.PreviousSHA256!=p.PreviousHeadSHA256{return empty,ErrDenied}
 req:=IssuanceRequest{
  PlanSHA256:pinnedPlanSHA,
  ArchiveID:p.ArchiveID,AuthorityEpoch:p.AuthorityEpoch,
  PreviousSequence:p.PreviousSequence,
  PreviousHeadSHA256:p.PreviousHeadSHA256,
  ProposedSequence:p.PlannedSequence,
  ProposedHeadSHA256:p.PlannedStartedRecordSHA256,
  Lane:p.Lane,ExperimentID:p.ExperimentID,
  CohortSHA256:p.CohortSHA256,
  SourceQualificationWitnessSHA256:p.SourceQualificationWitnessSHA256,
 }
 // The FSA issuer must independently authenticate and authorize this scope,
 // not merely sign a caller-chosen digest. The capability is NOT implemented
 // in FORGE's optimizer. A denied/unknown issuance never appends.
 certificate,err:=issuer.IssueFirstUse(ctx,req)
 if err!=nil{return empty,ErrDenied}
 next,err:=fsahead.VerifySignature(expectedPrior(identity,p),certificate)
 if err!=nil||next.Sequence!=p.PlannedSequence||
  next.HeadSHA256!=p.PlannedStartedRecordSHA256{return empty,ErrDenied}
 if ctx.Err()!=nil{return empty,ErrDenied}
 // After this point an interrupted write is NOT retried, even if its caller
 // sees an error and the external FSA high-water has not yet advanced.
 actualRow,err:=archive.AppendEvent(fsagate.EventForPlan(p))
 if err!=nil{return empty,ErrUncertain}
 if actualRow.Sequence!=p.PlannedSequence||
  actualRow.RecordSHA256!=p.PlannedStartedRecordSHA256{return empty,ErrUncertain}
 // fsatrust.Advance independently reads, validates complete private archive,
 // performs ONE remote CAS, and readbacks. No retry on timeout or conflict.
 if _,err=fsatrust.Advance(ctx,backend,archive,identity,certificate);err!=nil{
  return empty,ErrUncertain
 }
 proof,err:=fsagate.ProveFSAFirstUse(ctx,backend,archive,identity,p,pinnedPlanSHA,certificate)
 if err!=nil{return empty,ErrUncertain}
 if !proof.FSAFirstUseCommitted||!proof.FirstUseConsumed||
  proof.DispatchAuthorized||proof.ScientificAccepted||
  proof.PhysicalIndependenceDemonstrated||proof.AcceptedRefMutation{
  return empty,ErrUncertain
 }
 return proof,nil
}

// ReconcileCommittedFirstUse may be invoked after an uncertain CAS, but is
// READ-ONLY and may never issue a checkpoint, append or retry a scientific run.
// Even a valid consumption proof grants no permission to start science.
func ReconcileCommittedFirstUse(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 p fsagate.FirstUsePlan,pinnedPlanSHA string,
 independentlyIssuedCertificate fsahead.SignedHead)(fsagate.FirstUseProof,error){
 proof,err:=fsagate.ProveFSAFirstUse(ctx,backend,archive,identity,
  p,pinnedPlanSHA,independentlyIssuedCertificate)
 if err!=nil{return fsagate.FirstUseProof{},ErrUncertain}
 return proof,nil
}
