// Package durableauthority implements a fail-closed durable shadow first-use
// ledger for the two EXISTING research lanes. It is not a deployed controller,
// a grant issuer, a queue consumer, or a scientific worker launcher.
package durableauthority

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
)

const Schema = "forge.original-custody-ledger.v1"
const GrantSchema = "forge.original-reservation-grant.v1"
const zeroSHA = "0000000000000000000000000000000000000000000000000000000000000000"
const grantDomain = "FORGE-ORIGINAL-RESERVATION-GRANT-V1\n"
const recordDomain = "FORGE-ORIGINAL-CUSTODY-RECORD-V1\n"

var (
	ErrBlocked       = errors.New("FORGE_ORIGINAL_CUSTODY_BLOCKED")
	ErrConsumed      = errors.New("FORGE_ORIGINAL_FIRST_USE_ALREADY_RESERVED")
	ErrIndeterminate = errors.New("FORGE_ORIGINAL_CUSTODY_WRITE_INDETERMINATE")
)

type Stage string

const (
	OriginalReserved Stage = "ORIGINAL_RESERVED_NO_REPLAY"
)

// Grant must be authenticated by a pinned independent signer. The runtime
// signing capability is deliberately NOT implemented in this repository.
// A signature is not an authority transfer and never launches a worker.
type Grant struct {
	Schema             string `json:"schema"`
	Lane               string `json:"lane"`
	OriginalID         string `json:"original_id"`
	FrozenSHA256       string `json:"frozen_sha256"`
	IntentSHA256       string `json:"intent_sha256"`
	OwnerID            string `json:"owner_id"`
	OwnerEpoch         uint64 `json:"owner_epoch"`
	ExpectedHeadSHA256 string `json:"expected_head_sha256"`
	SignatureHex       string `json:"signature_hex"`
}

type Record struct {
	Schema            string `json:"schema"`
	Sequence          uint64 `json:"sequence"`
	PreviousSHA256    string `json:"previous_sha256"`
	Lane              string `json:"lane"`
	OriginalID        string `json:"original_id"`
	FrozenSHA256      string `json:"frozen_sha256"`
	IntentSHA256      string `json:"intent_sha256"`
	OwnerID           string `json:"owner_id"`
	OwnerEpoch        uint64 `json:"owner_epoch"`
	Stage             Stage  `json:"stage"`
	GrantSignatureHex string `json:"grant_signature_hex"`
	RecordSHA256      string `json:"record_sha256"`
}

type Snapshot struct {
	HeadSHA256 string
	Entries    []Record
	// Reservations are treated as consumed, including when a worker never
	// returned a start or terminal receipt.
	ReservedOriginals map[string]bool
	HighWaterEpoch    map[string]uint64
}

type Store struct {
	mu        sync.Mutex
	root      string
	guard     *os.File
	publicKey ed25519.PublicKey
	closed    bool
	poisoned  bool
}

func validHash(s string) bool {
	if len(s) != 64 {return false}
	for _, c := range s {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {return false}
	}
	return true
}
func validID(s string) bool {
	if len(s) == 0 || len(s) > 96 {return false}
	for _, c := range s {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c == '_' || c == '-') {return false}
	}
	return true
}
func validLane(s string) bool  { return s == "Wingless" || s == "Yggdrasil" }
func fileName(n uint64) string { return fmt.Sprintf("%020d.json", n) }
func recordHash(r Record) (string, error) {
	r.RecordSHA256 = ""
	b, err := json.Marshal(r)
	if err != nil {return "", err}
	d := sha256.Sum256(append([]byte(recordDomain), b...))
	return hex.EncodeToString(d[:]), nil
}
func grantPayload(g Grant) ([]byte, error) {
	g.SignatureHex = ""
	return json.Marshal(g)
}
func verifyGrant(g Grant, key ed25519.PublicKey) error {
	if g.Schema != GrantSchema || !validLane(g.Lane) || !validID(g.OriginalID) ||
		!validHash(g.FrozenSHA256) || !validHash(g.IntentSHA256) ||
		!validID(g.OwnerID) || g.OwnerEpoch == 0 || !validHash(g.ExpectedHeadSHA256) ||
		len(key) != ed25519.PublicKeySize {return ErrBlocked}
	b, err := grantPayload(g)
	if err != nil {return ErrBlocked}
	sig, err := hex.DecodeString(g.SignatureHex)
	if err != nil || len(sig) != ed25519.SignatureSize || !ed25519.Verify(key, append([]byte(grantDomain), b...), sig) {return ErrBlocked}
	return nil
}
func validateRecord(r Record, key ed25519.PublicKey) bool {
	if r.Schema != Schema || r.Stage != OriginalReserved || !validLane(r.Lane) ||
		!validID(r.OriginalID) || !validHash(r.FrozenSHA256) ||
		!validHash(r.IntentSHA256) || !validID(r.OwnerID) ||
		r.OwnerEpoch == 0 || !validHash(r.PreviousSHA256) || !validHash(r.RecordSHA256) {return false}
	return verifyGrant(Grant{Schema: GrantSchema, Lane: r.Lane, OriginalID: r.OriginalID,
		FrozenSHA256: r.FrozenSHA256, IntentSHA256: r.IntentSHA256,
		OwnerID: r.OwnerID, OwnerEpoch: r.OwnerEpoch,
		ExpectedHeadSHA256: r.PreviousSHA256, SignatureHex: r.GrantSignatureHex}, key) == nil
}

// Load is a read-only recovery inspection, safe even when an old writer lock
// exists. It never removes a stale lock or infers a missing record as unused.
func Load(root string, pinnedKey ed25519.PublicKey) (Snapshot, error) {
	out := Snapshot{HeadSHA256: zeroSHA, Entries: []Record{}, ReservedOriginals: map[string]bool{}, HighWaterEpoch: map[string]uint64{}}
	if !filepath.IsAbs(root) || len(pinnedKey) != ed25519.PublicKeySize {return Snapshot{}, ErrBlocked}
	dir, err := os.ReadDir(root)
	if err != nil {return Snapshot{}, err}
	count := 0
	for _, d := range dir {
		if d.Name() == ".writer.lock" {continue}
		if !d.Type().IsRegular() || len(d.Name()) != 25 || d.Name()[20:] != ".json" {return Snapshot{}, ErrBlocked}
		for _, c := range d.Name()[:20] {
			if c < '0' || c > '9' {return Snapshot{}, ErrBlocked}
		}
		count++
	}
	if count > 100000 {return Snapshot{}, ErrBlocked}
	latest := map[string]Record{}
	for i := 1; i <= count; i++ {
		raw, err := os.ReadFile(filepath.Join(root, fileName(uint64(i))))
		if err != nil || len(raw) == 0 || len(raw) > 8192 {return Snapshot{}, ErrBlocked}
		dec := json.NewDecoder(bytes.NewReader(raw))
		dec.DisallowUnknownFields()
		var r Record
		if err := dec.Decode(&r); err != nil {return Snapshot{}, ErrBlocked}
		var trailing any
		if err := dec.Decode(&trailing); !errors.Is(err, io.EOF) {return Snapshot{}, ErrBlocked}
		normalized, err := json.Marshal(r)
		if err != nil || !bytes.Equal(raw, append(normalized, '\n')) ||
			r.Sequence != uint64(i) || r.PreviousSHA256 != out.HeadSHA256 {return Snapshot{}, ErrBlocked}
		k := r.Lane + ":" + r.OriginalID
		if _, known := latest[k]; known || !validateRecord(r, pinnedKey) {return Snapshot{}, ErrBlocked}
		if r.OwnerEpoch < out.HighWaterEpoch[r.Lane] {return Snapshot{}, ErrBlocked}
		calc, err := recordHash(r)
		if err != nil || calc != r.RecordSHA256 {return Snapshot{}, ErrBlocked}
		out.ReservedOriginals[k] = true
		out.HighWaterEpoch[r.Lane] = r.OwnerEpoch
		latest[k] = r
		out.HeadSHA256 = calc
		out.Entries = append(out.Entries, r)
	}
	return out, nil
}

// OpenShadow acquires exclusive process custody using a create-only guard.
// After a crash the lock is intentionally retained: recovery requires a
// separate, independently authenticated owner-fencing procedure.
func OpenShadow(root string, pinnedKey ed25519.PublicKey) (*Store, error) {
	if !filepath.IsAbs(root) || len(pinnedKey) != ed25519.PublicKeySize {return nil, ErrBlocked}
	if err := os.MkdirAll(root, 0700); err != nil {return nil, err}
	guard, err := os.OpenFile(filepath.Join(root, ".writer.lock"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {return nil, ErrBlocked}
	s := &Store{root: root, guard: guard, publicKey: append(ed25519.PublicKey(nil), pinnedKey...)}
	if _, err := Load(root, pinnedKey); err != nil {
		_ = guard.Close()
		// Never release a guard after an integrity failure.
		return nil, err
	}
	return s, nil
}

// Reserve persists the irreversible first-use hazard BEFORE any external
// original attempt. Neither the signature nor a successful return permits
// executing the original; the actual independent authority and worker-side
// epoch fence must separately attest the cutover. This is shadow-only.
func (s *Store) Reserve(g Grant) (string, error) {
	if s == nil {return "", ErrBlocked}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed || s.poisoned || s.guard == nil {return "", ErrBlocked}
	if err := verifyGrant(g, s.publicKey); err != nil {return "", err}
	old, err := Load(s.root, s.publicKey)
	if err != nil {s.poisoned = true;return "", ErrIndeterminate}
	if old.ReservedOriginals[g.Lane+":"+g.OriginalID] {return "", ErrConsumed}
	if old.HeadSHA256 != g.ExpectedHeadSHA256 || g.OwnerEpoch < old.HighWaterEpoch[g.Lane] {return "", ErrBlocked}
	r := Record{Schema: Schema, Sequence: uint64(len(old.Entries) + 1), PreviousSHA256: old.HeadSHA256,
		Lane: g.Lane, OriginalID: g.OriginalID, FrozenSHA256: g.FrozenSHA256,
		IntentSHA256: g.IntentSHA256, OwnerID: g.OwnerID, OwnerEpoch: g.OwnerEpoch, Stage: OriginalReserved, GrantSignatureHex: g.SignatureHex}
	r.RecordSHA256, err = recordHash(r)
	if err != nil {return "", ErrBlocked}
	if err := s.write(r); err != nil {return "", err}
	// Must observe the precise committed record before returning success.
	after, err := Load(s.root, s.publicKey)
	if err != nil || after.HeadSHA256 != r.RecordSHA256 {s.poisoned = true;return "", ErrIndeterminate}
	return r.RecordSHA256, nil
}
func (s *Store) write(r Record) error {
	b, err := json.Marshal(r)
	if err != nil {return ErrBlocked}
	path := filepath.Join(s.root, fileName(r.Sequence))
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {s.poisoned = true;return ErrIndeterminate}
	_, writeErr := f.Write(append(b, '\n'))
	if writeErr == nil {writeErr = f.Sync()}
	closeErr := f.Close()
	if writeErr != nil || closeErr != nil {s.poisoned = true;return ErrIndeterminate}
	return nil
}

// Close releases ONLY a normal, reconciled shadow process's local guard.
// Never invoke after unknown durability or on a crashed owner.
func (s *Store) Close() error {
	if s == nil {return ErrBlocked}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed || s.poisoned || s.guard == nil {return ErrBlocked}
	s.closed = true
	if err := s.guard.Close(); err != nil {return err}
	return os.Remove(filepath.Join(s.root, ".writer.lock"))
}
