package fsaeligibility

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/spoonman136668-ai/forge/dreamrsi"
	"github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
	"github.com/spoonman136668-ai/forge/dreamrsi/prospective"
	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaissuance"
	"github.com/spoonman136668-ai/forge/fsaissuer"
	"github.com/spoonman136668-ai/forge/fsatrust"
	"github.com/spoonman136668-ai/forge/privatearchive"
	"github.com/spoonman136668-ai/forge/researchlog"
)

func digest(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}
func hashJSON(x any) string {
	b, _ := json.Marshal(x)
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

type fixtureFloor struct {
	mu sync.Mutex
	anchor fsahead.Anchor
	offline bool
	cas int
}
func (f *fixtureFloor) ReadAnchor(context.Context) (fsahead.Anchor, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.offline { return fsahead.Anchor{}, errors.New("synthetic outage") }
	a := f.anchor
	a.PublicKey = append(ed25519.PublicKey(nil), a.PublicKey...)
	return a, nil
}
func (f *fixtureFloor) ConfirmArchiveBinding(_ context.Context, id string) (bool, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.offline { return false, errors.New("synthetic outage") }
	return id == f.anchor.ArchiveID, nil
}
func (f *fixtureFloor) CompareAndSwap(_ context.Context, prior, next fsahead.Anchor) (bool, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.cas++
	if f.offline { return false, errors.New("synthetic outage") }
	if prior.Sequence != f.anchor.Sequence || prior.HeadSHA256 != f.anchor.HeadSHA256 {
		return false, nil
	}
	f.anchor = next
	return true, nil
}

type fixture struct {
	archive *privatearchive.Store
	floor *fixtureFloor
	identity fsatrust.Identity
	evidence Snapshot
	plan fsagate.FirstUsePlan
	pin string
	signer *fsaissuer.Issuer
	root string
	approvalKey ed25519.PublicKey
}

func setup(t *testing.T, lane string) *fixture {
	t.Helper()
	ctx := context.Background()
	archive, err := privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName))
	if err != nil { t.Fatal(err) }
	fsaPrivate := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{71},32))
	approverPrivate := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{37},32))
	predecisionPrivate := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{27},32))
	fsaPublic := fsaPrivate.Public().(ed25519.PublicKey)
	identity := fsatrust.Identity{
		ArchiveID:digest("protected-archive-"+lane),
		KeyID:"FORGE_FSA_R14",
		PublicKey:fsaPublic,AuthorityEpoch:12,
	}
	cohort:=digest(lane+"-cohort")
	prereg:=digest(lane+"-prereg")
	witness:=digest(lane+"-source-qualified")
	source:=strings.Repeat("a",40)
	hyp:=strings.Repeat("b",40)
	preregCommit:=strings.Repeat("c",40)
	var row researchlog.Record
	for _,event:=range []researchlog.Event{
		{Lane:lane,Generation:11,ExperimentID:"EXPERIMENT_11",Kind:researchlog.Hypothesis,SourceCommitSHA:hyp},
		{Lane:lane,Generation:11,ExperimentID:"EXPERIMENT_11",Kind:researchlog.Preregister,SourceCommitSHA:preregCommit,PreregSHA256:prereg,CohortSHA256:cohort},
		{Lane:lane,Generation:11,ExperimentID:"EXPERIMENT_11",Kind:researchlog.SourceQualified,SourceCommitSHA:source,PreregSHA256:prereg,CohortSHA256:cohort,WitnessSHA256:witness},
	} {
		row,err=archive.AppendEvent(event)
		if err!=nil { t.Fatal(err) }
	}
	floor:=&fixtureFloor{anchor:fsahead.Anchor{
		ArchiveID:identity.ArchiveID, KeyID:identity.KeyID,
		PublicKey:append(ed25519.PublicKey(nil),fsaPublic...),
		AuthorityEpoch:identity.AuthorityEpoch,
		Sequence:row.Sequence,HeadSHA256:row.RecordSHA256,
	}}
	policy:=dreamrsi.BasePolicies(lane,50)[0]
	opts:=[]dreamrsi.Option{
		{ID:"first",CohortSHA256:cohort,Family:"novel",
		 Impact:89,Novelty:90,Robustness:90,Diversity:70,EstimatedCost:60,Risk:1},
		{ID:"second",CohortSHA256:digest(lane+"-other"),Family:"control",
		 Impact:20,Novelty:10,Robustness:20,Diversity:20,EstimatedCost:20,Risk:5},
	}
	chosen,err:=dreamrsi.Select(policy,dreamrsi.Decision{
		ContextSHA256:digest("context-"+lane),Options:opts,
	})
	if err!=nil||chosen!="first" { t.Fatalf("unexpected test policy choice %s: %v",chosen,err) }
	scope:=fsagate.Scope{
		Schema:fsagate.ScopeSchema,Lane:lane,Generation:11,
		ExperimentID:"EXPERIMENT_11",HypothesisCommitSHA:hyp,
		PreregCommitSHA:preregCommit,SourceCommitSHA:source,
		PreregSHA256:prereg,CandidateCohortSHA256:cohort,
		SourceQualificationWitnessSHA256:witness,
		EligibleHistoricalSourceSHA256:digest("history-"+lane),
		PolicySHA256:policy.ID(),
		PolicyLineageHeadSHA256:digest("policy-lineage-"+lane),
		FrozenOptimizerSpecSHA256:digest("optimizer-"+lane),
		MaxComputeUnits:100,AuthorityEpoch:identity.AuthorityEpoch,
	}
	selection:=prospective.Selection{
		Schema:prospective.DecisionSchema,Lane:lane,
		Epoch:identity.AuthorityEpoch,Tick:33,
		SourceCommitSHA:source,FrozenPreregSHA256:prereg,
		PolicySHA256:policy.ID(),
		PolicyLineageSHA256:scope.PolicyLineageHeadSHA256,
		ContextSHA256:digest("context-"+lane),Options:opts,
		ChosenID:"first",ChosenCohortSHA256:cohort,
		MaxComputeUnits:scope.MaxComputeUnits,
		LoggingMode:prospective.Observational,
	}
	selectionBytes,_:=json.Marshal(selection)
	selectionSig:=ed25519.Sign(predecisionPrivate,append([]byte(prospective.DecisionDomain),selectionBytes...))
	evidence:=Snapshot{
		Selection:prospective.SignedSelection{Selection:selection,
		 SignatureHex:hex.EncodeToString(selectionSig)},
		SelectionPin:prospective.IndependentPin{
			ExpectedSHA256:hashJSON(selection),
			PublicKeyHex:hex.EncodeToString(predecisionPrivate.Public().(ed25519.PublicKey)),
		}, Policy:policy,
		SelectionRequest:dreamrsi.FSASelectionRequest{
			Schema:dreamrsi.ContractSchema,Mode:"UNPRIVILEGED_FSA_REVIEW_REQUEST",
			Lane:lane,SourceHistorySHA256:scope.EligibleHistoricalSourceSHA256,
			FrozenSpecSHA256:scope.FrozenOptimizerSpecSHA256,
			OptimizerLineageHeadSHA256:scope.PolicyLineageHeadSHA256,
			PolicySHA256:scope.PolicySHA256,CandidateID:"first",
			CandidateCohortSHA256:cohort,
		},
		Scope:scope,ScopeSHA256:hashJSON(scope),
		StartWitnessSHA256:digest("fsa-start-"+lane),RunID:330033,
	}
	plan,err:=fsagate.PrepareFirstUse(ctx,floor,archive,identity,
		evidence.Selection,evidence.SelectionPin,evidence.Policy,
		evidence.SelectionRequest,evidence.Scope,evidence.ScopeSHA256,
		evidence.StartWitnessSHA256,evidence.RunID)
	if err!=nil { t.Fatal(err) }
	pin,err:=fsagate.PlanSHA(plan)
	if err!=nil { t.Fatal(err) }
	req:=fsaissuance.IssuanceRequest{
		PlanSHA256:pin, ArchiveID:plan.ArchiveID,
		AuthorityEpoch:plan.AuthorityEpoch,PreviousSequence:plan.PreviousSequence,
		PreviousHeadSHA256:plan.PreviousHeadSHA256,
		ProposedSequence:plan.PlannedSequence,
		ProposedHeadSHA256:plan.PlannedStartedRecordSHA256,
		Lane:lane,ExperimentID:plan.ExperimentID,CohortSHA256:cohort,
		SourceQualificationWitnessSHA256:witness,
	}
	grant:=fsaissuer.Grant{
		Schema:fsaissuer.GrantSchema,Mode:fsaissuer.GrantMode,
		KeyID:identity.KeyID,FSAPublicKeyHex:hex.EncodeToString(fsaPublic),
		Request:req,
	}
	grantBytes,_:=json.Marshal(grant)
	grantSignature:=ed25519.Sign(approverPrivate,
		append([]byte("FORGE-FSA-INDEPENDENT-APPROVAL-V1\n"),grantBytes...))
	root:=filepath.Join(t.TempDir(),fsaissuer.FolderName)
	if err=os.Mkdir(root,0700);err!=nil {t.Fatal(err)}
	underlying,err:=fsaissuer.New(approverPrivate.Public().(ed25519.PublicKey),
		fsaPublic,fsaissuer.Approval{
			Grant:grant,SignatureHex:hex.EncodeToString(grantSignature),
		},root,func(_ context.Context, msg []byte)([]byte,error){
			return ed25519.Sign(fsaPrivate,msg),nil
		})
	if err!=nil {t.Fatal(err)}
	return &fixture{
		archive:archive,floor:floor,identity:identity,evidence:evidence,
		plan:plan,pin:pin,signer:underlying,root:root,
		approvalKey:approverPrivate.Public().(ed25519.PublicKey),
	}
}

func (f *fixture) guard(t *testing.T, e Snapshot) *Issuer {
	t.Helper()
	guard,err:=New(f.floor,f.archive,f.identity,e,f.pin,f.signer)
	if err!=nil {t.Fatal(err)}
	return guard
}
func (f *fixture) req() fsaissuance.IssuanceRequest {
	p:=f.plan
	return fsaissuance.IssuanceRequest{
		PlanSHA256:f.pin,ArchiveID:p.ArchiveID,
		AuthorityEpoch:p.AuthorityEpoch,PreviousSequence:p.PreviousSequence,
		PreviousHeadSHA256:p.PreviousHeadSHA256,
		ProposedSequence:p.PlannedSequence,
		ProposedHeadSHA256:p.PlannedStartedRecordSHA256,
		Lane:p.Lane,ExperimentID:p.ExperimentID,CohortSHA256:p.CohortSHA256,
		SourceQualificationWitnessSHA256:p.SourceQualificationWitnessSHA256,
	}
}
func (f *fixture) unchanged(t *testing.T) {
	t.Helper()
	rows,err:=os.ReadDir(f.root)
	if err!=nil||len(rows)!=0 {t.Fatal("denied preflight reached signer tombstone")}
	j,err:=f.archive.Load()
	if err!=nil||len(j.Entries)!=3||f.floor.cas!=0 {
		t.Fatal("denied preflight changed archive or CAS")
	}
}

func TestR14GuardedIssuerFullR13FirstUseIntegration(t *testing.T){
	for _,lane:=range []string{"Wingless","Yggdrasil"}{
		t.Run(lane,func(t *testing.T){
			f:=setup(t,lane)
			g:=f.guard(t,f.evidence)
			proof,err:=fsaissuance.CommitFirstUse(context.Background(),
				f.floor,f.archive,f.identity,g,f.plan,f.pin)
			if err!=nil||!proof.FirstUseConsumed||!proof.FSAFirstUseCommitted||
				proof.DispatchAuthorized||proof.ScientificAccepted||
				proof.PhysicalIndependenceDemonstrated||f.floor.cas!=1{
				t.Fatalf("R14 independent review+R13 sign+R6 CAS integration: %+v %v",proof,err)
			}
			if _,err=g.IssueFirstUse(context.Background(),f.req());!errors.Is(err,ErrDenied){
				t.Fatalf("consumed cohort got second first-use authorization: %v",err)
			}
			if f.floor.cas!=1 {t.Fatal("duplicate CAS on consumed cohort")}
		})
	}
}

func TestR14ReviewChangesFailBeforeSigning(t *testing.T){
	mutators:=map[string]func(*Snapshot){
		"frozen-budget":func(e *Snapshot){e.Scope.MaxComputeUnits++},
		"source-change":func(e *Snapshot){e.Scope.SourceCommitSHA=strings.Repeat("d",40)},
		"prereg-change":func(e *Snapshot){e.Scope.PreregSHA256=digest("changed-prereg")},
		"cohort-change":func(e *Snapshot){e.Scope.CandidateCohortSHA256=digest("stolen-cohort")},
		"history-change":func(e *Snapshot){e.Scope.EligibleHistoricalSourceSHA256=digest("unwitnessed-history")},
		"scope-pin-change":func(e *Snapshot){e.ScopeSHA256=digest("wrong-scope")},
		"start-witness-change":func(e *Snapshot){e.StartWitnessSHA256=digest("unknown-start")},
		"run-change":func(e *Snapshot){e.RunID++},
		"unsigned-policy":func(e *Snapshot){e.Selection.Selection.ChosenID="second"},
		"source-witness-change":func(e *Snapshot){e.Scope.SourceQualificationWitnessSHA256=digest("wrong-source-witness")},
	}
	for name,mutate:=range mutators{
		t.Run(name,func(t *testing.T){
			f:=setup(t,"Wingless")
			e:=f.evidence
			mutate(&e)
			g:=f.guard(t,e)
			if _,err:=g.IssueFirstUse(context.Background(),f.req());!errors.Is(err,ErrDenied){
				t.Fatalf("%s reached signer without live eligibility: %v",name,err)
			}
			f.unchanged(t)
		})
	}
}

func TestR14MissingFloorAndUnknownPlanNeverSign(t *testing.T){
	f:=setup(t,"Yggdrasil")
	g:=f.guard(t,f.evidence)
	f.floor.offline=true
	if _,err:=g.IssueFirstUse(context.Background(),f.req());!errors.Is(err,ErrDenied){
		t.Fatal("missing authority floor allowed signer")
	}
	f.floor.offline=false
	bad:=f.req()
	bad.ProposedHeadSHA256=digest("unapproved-head")
	if _,err:=g.IssueFirstUse(context.Background(),bad);!errors.Is(err,ErrDenied){
		t.Fatal("changed FIRST_USE request allowed")
	}
	ctx,cancel:=context.WithCancel(context.Background())
	cancel()
	if _,err:=g.IssueFirstUse(ctx,f.req());!errors.Is(err,ErrDenied){
		t.Fatal("cancelled eligibility gate used signer")
	}
	f.unchanged(t)
}
