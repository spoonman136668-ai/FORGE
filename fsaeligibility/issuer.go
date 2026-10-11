// Package fsaeligibility binds the R13 checkpoint issuer to a fresh,
// independently pinned, read-only FORGE scientific eligibility review.
// No run is dispatched, accepted, promoted, or scheduled by this package.
package fsaeligibility

import (
	"context"
	"errors"

	"github.com/spoonman136668-ai/forge/dreamrsi"
	"github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
	"github.com/spoonman136668-ai/forge/dreamrsi/prospective"
	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaissuance"
	"github.com/spoonman136668-ai/forge/fsatrust"
	"github.com/spoonman136668-ai/forge/privatearchive"
)

var ErrDenied = errors.New("FORGE_FSA_R14_LIVE_ELIGIBILITY_REVIEW_DENIED")

// Snapshot is independently supplied frozen input, NOT a worker-issued
// authorization. Its scope hash and selection key/hash must have been
// pinned by the FSA outside the optimizer and hosted compute worker.
type Snapshot struct {
	Selection prospective.SignedSelection
	SelectionPin prospective.IndependentPin
	Policy dreamrsi.Policy
	SelectionRequest dreamrsi.FSASelectionRequest
	Scope fsagate.Scope
	ScopeSHA256 string
	StartWitnessSHA256 string
	RunID uint64
}

// Issuer is an adapter for the existing FSA first-use interface. The R13
// downstream signer and existing archive/CAS boundary remain independently
// responsible for signing and consuming first use; there is no new authority.
type Issuer struct {
	backend fsatrust.Authority
	archive *privatearchive.Store
	identity fsatrust.Identity
	evidence Snapshot
	expectedPlanSHA256 string
	downstream fsaissuance.Issuer
}

// New never performs or permits irreversible work. Inputs must originate
// from FSA-controlled custody and never be provided by the optimizer alone.
func New(backend fsatrust.Authority, archive *privatearchive.Store,
	identity fsatrust.Identity, evidence Snapshot, expectedPlanSHA256 string,
	downstream fsaissuance.Issuer) (*Issuer, error) {
	if backend == nil || archive == nil || downstream == nil ||
		len(identity.PublicKey) != 32 || identity.AuthorityEpoch == 0 ||
		len(expectedPlanSHA256) != 64 || len(evidence.ScopeSHA256) != 64 ||
		len(evidence.StartWitnessSHA256) != 64 || evidence.RunID == 0 {
		return nil, ErrDenied
	}
	for _, c := range expectedPlanSHA256 + evidence.ScopeSHA256 + evidence.StartWitnessSHA256 {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {
			return nil, ErrDenied
		}
	}
	return &Issuer{
		backend: backend, archive: archive, identity: identity,
		evidence: evidence, expectedPlanSHA256: expectedPlanSHA256,
		downstream: downstream,
	}, nil
}

// IssueFirstUse recomputes the entire frozen FSA eligibility decision
// against a fresh independently authenticated high-water and complete
// FORGE research archive immediately before invoking the R13 signer.
// A stale grant, altered cohort, changed source, changed compute ceiling,
// forged selection, started cohort, outage or unknown archive state denies
// WITHOUT attempting a signer call, appending STARTED or performing CAS.
func (i *Issuer) IssueFirstUse(ctx context.Context,
	req fsaissuance.IssuanceRequest) (fsahead.SignedHead, error) {
	var zero fsahead.SignedHead
	if i == nil || ctx == nil || ctx.Err() != nil ||
		req.PlanSHA256 != i.expectedPlanSHA256 {
		return zero, ErrDenied
	}
	e := i.evidence
	p, err := fsagate.PrepareFirstUse(ctx, i.backend, i.archive, i.identity,
		e.Selection, e.SelectionPin, e.Policy, e.SelectionRequest,
		e.Scope, e.ScopeSHA256, e.StartWitnessSHA256, e.RunID)
	if err != nil {
		return zero, ErrDenied
	}
	sha, err := fsagate.PlanSHA(p)
	if err != nil || sha != i.expectedPlanSHA256 {
		return zero, ErrDenied
	}
	expected := fsaissuance.IssuanceRequest{
		PlanSHA256: sha,
		ArchiveID: p.ArchiveID, AuthorityEpoch: p.AuthorityEpoch,
		PreviousSequence: p.PreviousSequence,
		PreviousHeadSHA256: p.PreviousHeadSHA256,
		ProposedSequence: p.PlannedSequence,
		ProposedHeadSHA256: p.PlannedStartedRecordSHA256,
		Lane: p.Lane, ExperimentID: p.ExperimentID,
		CohortSHA256: p.CohortSHA256,
		SourceQualificationWitnessSHA256: p.SourceQualificationWitnessSHA256,
	}
	if req != expected || ctx.Err() != nil {
		return zero, ErrDenied
	}
	return i.downstream.IssueFirstUse(ctx, req)
}

var _ fsaissuance.Issuer = (*Issuer)(nil)
