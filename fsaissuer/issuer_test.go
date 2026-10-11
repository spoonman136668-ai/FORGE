package fsaissuer

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"testing"

	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaissuance"
	"github.com/spoonman136668-ai/forge/researchlog"
)

func testDigest(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

type testFixture struct {
	approver ed25519.PublicKey
	fsa ed25519.PublicKey
	approval Approval
	root string
	sign SignFunc
}

func newFixture(t *testing.T) testFixture {
	t.Helper()
	operatorPrivate := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{37}, 32))
	fsaPrivate := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{73}, 32))
	operatorPublic := operatorPrivate.Public().(ed25519.PublicKey)
	fsaPublic := fsaPrivate.Public().(ed25519.PublicKey)
	root := filepath.Join(t.TempDir(), FolderName)
	if err := os.Mkdir(root, 0700); err != nil {
		t.Fatal(err)
	}
	request := fsaissuance.IssuanceRequest{
		PlanSHA256: testDigest("frozen-plan"),
		ArchiveID: testDigest("separate-archive"),
		AuthorityEpoch: 7,
		PreviousSequence: 3,
		PreviousHeadSHA256: testDigest("previous-record"),
		ProposedSequence: 4,
		ProposedHeadSHA256: testDigest("started-record"),
		Lane: "Wingless", ExperimentID: "EXPERIMENT_7",
		CohortSHA256: testDigest("frozen-cohort"),
		SourceQualificationWitnessSHA256: testDigest("source-witness"),
	}
	grant := Grant{
		Schema: GrantSchema, Mode: GrantMode, KeyID: "FORGE_FSA_R13",
		FSAPublicKeyHex: hex.EncodeToString(fsaPublic),
		Request: request,
	}
	raw, err := grantBytes(grant)
	if err != nil {
		t.Fatal(err)
	}
	approval := Approval{
		Grant: grant,
		SignatureHex: hex.EncodeToString(ed25519.Sign(operatorPrivate, raw)),
	}
	sign := func(_ context.Context, msg []byte) ([]byte, error) {
		return ed25519.Sign(fsaPrivate, msg), nil
	}
	return testFixture{operatorPublic, fsaPublic, approval, root, sign}
}

func (f testFixture) issuer(t *testing.T) *Issuer {
	t.Helper()
	i, err := New(f.approver, f.fsa, f.approval, f.root, f.sign)
	if err != nil {
		t.Fatal(err)
	}
	return i
}

func TestFSAIndependentFirstUseCertificateAndRestartNoReplay(t *testing.T) {
	f := newFixture(t)
	first, err := f.issuer(t).IssueFirstUse(context.Background(), f.approval.Grant.Request)
	if err != nil {
		t.Fatal(err)
	}
	req := f.approval.Grant.Request
	prior := fsahead.Anchor{
		ArchiveID: req.ArchiveID, KeyID: f.approval.Grant.KeyID,
		PublicKey: f.fsa, AuthorityEpoch: req.AuthorityEpoch,
		Sequence: req.PreviousSequence, HeadSHA256: req.PreviousHeadSHA256,
	}
	verified, err := fsahead.VerifySignature(prior, first)
	if err != nil || verified.Sequence != req.ProposedSequence ||
		verified.HeadSHA256 != req.ProposedHeadSHA256 {
		t.Fatalf("FSA signed-head verification failed: %v", err)
	}
	if _, err := f.issuer(t).IssueFirstUse(context.Background(), req); !errors.Is(err, ErrConsumed) {
		t.Fatalf("restart minted second certificate: %v", err)
	}
	if first.Payload.Domain != fsahead.Domain {
		t.Fatal("wrong signing domain")
	}
}

func TestFSARejectsForgedApprovalKeyDriftAndRequestMutation(t *testing.T) {
	f := newFixture(t)
	tampered := f.approval
	tampered.Grant.Request.CohortSHA256 = testDigest("swapped")
	if _, err := New(f.approver, f.fsa, tampered, f.root, f.sign); !errors.Is(err, ErrDenied) {
		t.Fatal("changed grant accepted")
	}
	falseApprover := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{8}, 32)).Public().(ed25519.PublicKey)
	if _, err := New(falseApprover, f.fsa, f.approval, f.root, f.sign); !errors.Is(err, ErrDenied) {
		t.Fatal("unknown approval principal accepted")
	}
	if _, err := New(f.approver, f.approver, f.approval, f.root, f.sign); !errors.Is(err, ErrDenied) {
		t.Fatal("same approver and signer accepted")
	}
	req := f.approval.Grant.Request
	req.ProposedHeadSHA256 = testDigest("different-head")
	if _, err := f.issuer(t).IssueFirstUse(context.Background(), req); !errors.Is(err, ErrDenied) {
		t.Fatal("request not exactly approved")
	}
	if names, err := os.ReadDir(f.root); err != nil || len(names) != 0 {
		t.Fatal("denied request consumed first use")
	}
}

func TestFSAConcurrentIssuersCompeteForOneDurableAttempt(t *testing.T) {
	f := newFixture(t)
	var wg sync.WaitGroup
	start := make(chan struct{})
	errs := make(chan error, 12)
	for n := 0; n < 12; n++ {
		i := f.issuer(t)
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			_, err := i.IssueFirstUse(context.Background(), f.approval.Grant.Request)
			errs <- err
		}()
	}
	close(start)
	wg.Wait()
	close(errs)
	success := 0
	for err := range errs {
		if err == nil {
			success++
		} else if !errors.Is(err, ErrConsumed) {
			t.Fatalf("unexpected concurrent issuer result: %v", err)
		}
	}
	if success != 1 {
		t.Fatalf("first-use certificates=%d want 1", success)
	}
}

func TestFSASignerFailureAndCancelledContextNeverAutoRetry(t *testing.T) {
	f := newFixture(t)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := f.issuer(t).IssueFirstUse(ctx, f.approval.Grant.Request); !errors.Is(err, ErrDenied) {
		t.Fatal("cancelled request accepted")
	}
	f.sign = func(context.Context, []byte) ([]byte, error) {
		return nil, errors.New("signer interrupted after first-use tombstone")
	}
	if _, err := f.issuer(t).IssueFirstUse(context.Background(), f.approval.Grant.Request); !errors.Is(err, ErrUncertain) {
		t.Fatalf("signer failure not classified as uncertain: %v", err)
	}
	if _, err := f.issuer(t).IssueFirstUse(context.Background(), f.approval.Grant.Request); !errors.Is(err, ErrConsumed) {
		t.Fatalf("signer replay allowed after uncertainty: %v", err)
	}
}

func TestFSARejectsUnsafeDirectoryAndInvalidGrant(t *testing.T) {
	f := newFixture(t)
	wrong := filepath.Join(t.TempDir(), "not-fsa")
	if err := os.Mkdir(wrong, 0700); err != nil {
		t.Fatal(err)
	}
	if _, err := New(f.approver, f.fsa, f.approval, wrong, f.sign); !errors.Is(err, ErrDenied) {
		t.Fatal("foreign directory permitted")
	}
	if err := os.Chmod(f.root, 0777); err != nil {
		t.Fatal(err)
	}
	// Windows os.Chmod does not model the directory DACL. The real FSA
	// must independently enforce Windows ACL custody before deployment.
	if runtime.GOOS != "windows" {
		if _, err := New(f.approver, f.fsa, f.approval, f.root, f.sign); !errors.Is(err, ErrDenied) {
			t.Fatal("world-writable FSA attempts permitted")
		}
	}
	if err := os.Chmod(f.root, 0700); err != nil {
		t.Fatal(err)
	}
	invalid := f.approval
	invalid.Grant.Request.PreviousSequence = researchlog.MaxEntries
	if _, err := New(f.approver, f.fsa, invalid, f.root, f.sign); !errors.Is(err, ErrDenied) {
		t.Fatal("invalid sequence accepted")
	}
}
