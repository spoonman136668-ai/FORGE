// Package fsaissuer is the FORGE-native, fail-closed first-use checkpoint
// signer, not an active FORGE Scientific Authority service. An independently
// authenticated, pre-frozen approval and a separately held signing capability
// are prerequisites. It cannot dispatch, schedule, accept, or promote science.
package fsaissuer

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sync"

	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaissuance"
)

const (
	GrantSchema = "forge.fsa.first-use-grant.v1"
	GrantMode = "PINNED_FIRST_USE_CHECKPOINT_ONLY_NO_DISPATCH"
	FolderName = "forge-fsa-authorizations"
	approvalDomain = "FORGE-FSA-INDEPENDENT-APPROVAL-V1\n"
	checkpointDomain = "FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"
)

var (
	ErrDenied = errors.New("FORGE_FSA_ISSUER_UNAUTHORIZED")
	ErrConsumed = errors.New("FORGE_FSA_ISSUER_ONE_USE_ALREADY_ATTEMPTED")
	ErrUncertain = errors.New("FORGE_FSA_ISSUER_ATTEMPT_UNCERTAIN_NO_RETRY")
)

// Grant is created and signed by an independent FSA approval principal.
// Neither a worker-selected policy nor a public GitHub job can approve it.
type Grant struct {
	Schema string `json:"schema"`
	Mode string `json:"mode"`
	KeyID string `json:"key_id"`
	FSAPublicKeyHex string `json:"fsa_public_key_hex"`
	Request fsaissuance.IssuanceRequest `json:"request"`
}

type Approval struct {
	Grant Grant `json:"grant"`
	SignatureHex string `json:"signature_hex"`
}

// SignFunc is supplied by a separate FSA key-custody implementation. This
// package never generates or loads a private key, including from environment
// variables, repository secrets, CKB or a research worker.
type SignFunc func(context.Context, []byte) ([]byte, error)

type Issuer struct {
	approval Approval
	pinnedFSA ed25519.PublicKey
	root string
	sign SignFunc
	mu sync.Mutex
}

func lowerHex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	for _, c := range s {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {
			return false
		}
	}
	return true
}

func validID(s string) bool {
	if len(s) < 1 || len(s) > 96 {
		return false
	}
	for _, c := range s {
		if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' ||
			c >= '0' && c <= '9' || c == '_' || c == '-') {
			return false
		}
	}
	return true
}

func validGrant(g Grant) bool {
	r := g.Request
	return g.Schema == GrantSchema && g.Mode == GrantMode &&
		validID(g.KeyID) && lowerHex(g.FSAPublicKeyHex, 64) &&
		lowerHex(r.PlanSHA256, 64) && lowerHex(r.ArchiveID, 64) &&
		r.AuthorityEpoch != 0 && r.PreviousSequence < 2048 &&
		r.ProposedSequence == r.PreviousSequence+1 &&
		lowerHex(r.PreviousHeadSHA256, 64) &&
		lowerHex(r.ProposedHeadSHA256, 64) &&
		(r.Lane == "Wingless" || r.Lane == "Yggdrasil") &&
		validID(r.ExperimentID) && lowerHex(r.CohortSHA256, 64) &&
		lowerHex(r.SourceQualificationWitnessSHA256, 64)
}

func grantBytes(g Grant) ([]byte, error) {
	raw, err := json.Marshal(g)
	if err != nil {
		return nil, err
	}
	return append([]byte(approvalDomain), raw...), nil
}

func secureDirectory(root string) bool {
	if !filepath.IsAbs(root) || filepath.Base(filepath.Clean(root)) != FolderName {
		return false
	}
	st, err := os.Lstat(root)
	return err == nil && st.IsDir() && st.Mode()&os.ModeSymlink == 0 &&
		st.Mode().Perm()&0022 == 0
}

// New verifies the operator-pinned approval public key and the separately
// pinned FSA signing key before accepting any request. The directory must
// already exist under an isolated, access-controlled FORGE principal.
// Filesystem protection does not establish off-host rollback resistance.
func New(approver, fsa ed25519.PublicKey, approval Approval,
	root string, signer SignFunc) (*Issuer, error) {
	if len(approver) != ed25519.PublicKeySize ||
		len(fsa) != ed25519.PublicKeySize ||
		bytes.Equal(approver, fsa) || signer == nil ||
		!validGrant(approval.Grant) || !secureDirectory(root) {
		return nil, ErrDenied
	}
	if approval.Grant.FSAPublicKeyHex != hex.EncodeToString(fsa) ||
		!lowerHex(approval.SignatureHex, ed25519.SignatureSize*2) {
		return nil, ErrDenied
	}
	msg, err := grantBytes(approval.Grant)
	if err != nil {
		return nil, ErrDenied
	}
	sig, err := hex.DecodeString(approval.SignatureHex)
	if err != nil || !ed25519.Verify(approver, msg, sig) {
		return nil, ErrDenied
	}
	return &Issuer{
		approval: approval,
		pinnedFSA: append(ed25519.PublicKey(nil), fsa...),
		root: filepath.Clean(root),
		sign: signer,
	}, nil
}

// claim creates a durable no-retry tombstone BEFORE calling the signer.
// It is exclusive across concurrent processes and survives normal restart.
// Privileged deletion/rollback of the entire directory is NOT prevented.
func (i *Issuer) claim() error {
	if !secureDirectory(i.root) {
		return ErrUncertain
	}
	g := i.approval.Grant
	path := filepath.Join(i.root, g.Request.PlanSHA256+".attempt")
	f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if os.IsExist(err) {
		return ErrConsumed
	}
	if err != nil {
		return ErrUncertain
	}
	raw, err := json.Marshal(g)
	if err != nil {
		_ = f.Close()
		return ErrUncertain
	}
	sum := sha256.Sum256(raw)
	line := []byte(hex.EncodeToString(sum[:]) + "
")
	n, err := f.Write(line)
	if err == nil && n != len(line) {
		err = io.ErrShortWrite
	}
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err != nil || closeErr != nil {
		return ErrUncertain
	}
	dir, err := os.Open(i.root)
	if err != nil {
		return ErrUncertain
	}
	err = dir.Sync()
	closeErr = dir.Close()
	if (err != nil && runtime.GOOS != "windows") || closeErr != nil {
		return ErrUncertain
	}
	return nil
}

// IssueFirstUse fulfills only the fsaissuance.Issuer checkpoint-signing
// interface. The independent FSA must separately authenticate high-water,
// immutable source, preregistration, cohort and grant custody before New;
// the existing CommitFirstUse must still recover and commit exactly once.
// A returned signed checkpoint is NEVER worker dispatch authorization.
func (i *Issuer) IssueFirstUse(ctx context.Context,
	request fsaissuance.IssuanceRequest) (fsahead.SignedHead, error) {
	var empty fsahead.SignedHead
	if ctx == nil || ctx.Err() != nil || i == nil ||
		request != i.approval.Grant.Request {
		return empty, ErrDenied
	}
	i.mu.Lock()
	defer i.mu.Unlock()
	if ctx.Err() != nil {
		return empty, ErrDenied
	}
	if err := i.claim(); err != nil {
		return empty, err
	}
	g := i.approval.Grant
	p := fsahead.Payload{
		Schema: fsahead.Schema, Domain: fsahead.Domain,
		ArchiveID: request.ArchiveID, KeyID: g.KeyID,
		AuthorityEpoch: request.AuthorityEpoch,
		ParentSequence: request.PreviousSequence,
		ParentHeadSHA256: request.PreviousHeadSHA256,
		Sequence: request.ProposedSequence,
		HeadSHA256: request.ProposedHeadSHA256,
	}
	raw, err := json.Marshal(p)
	if err != nil {
		return empty, ErrUncertain
	}
	signature, err := i.sign(ctx, append([]byte(checkpointDomain), raw...))
	if err != nil || len(signature) != ed25519.SignatureSize ||
		!ed25519.Verify(i.pinnedFSA, append([]byte(checkpointDomain), raw...), signature) {
		return empty, ErrUncertain
	}
	if ctx.Err() != nil {
		return empty, ErrUncertain
	}
	return fsahead.SignedHead{
		Payload: p, SignatureHex: hex.EncodeToString(signature),
	}, nil
}

var _ fsaissuance.Issuer = (*Issuer)(nil)
