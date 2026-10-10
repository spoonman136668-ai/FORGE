package fsaremote

// Synthetic source qualification only: a disk-backed checkpoint, separately
// persisted signed high-water records and real mutual-TLS servers. Both
// directories and servers are local test fixtures, NOT independent protected
// failure domains, deployed FSA services, or proof of physical durability.
import (
	"context"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"

	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaanchorstore"
	"github.com/spoonman136668-ai/forge/researchlog"
)

// TestDiskBackedRealTLSRestartAndRollbackFencing covers the interface
// between the already-qualified write-once local authority and real mTLS.
// A lost HTTP acknowledgment, lagging witness, restarted services and
// truncated source store must never imply permission to replay a CAS.
func TestDiskBackedRealTLSRestartAndRollbackFencing(t *testing.T) {
	ctx := context.Background()
	public, _ := kpair("FSA")
	witnessPublic, witnessSecret := kpair("independent-witness")
	pin := Pin{
		ArchiveID: hx("a", 64), KeyID: "FORGE_TEST_ONLY",
		PublicKey: public, AuthorityEpoch: 4,
		BindingSHA256: hx("b", 64),
		WitnessPublicKey: witnessPublic, MinimumRevision: 1,
	}
	genesis := fsahead.Anchor{
		ArchiveID: pin.ArchiveID, KeyID: pin.KeyID, PublicKey: pin.PublicKey,
		AuthorityEpoch: pin.AuthorityEpoch, HeadSHA256: researchlog.Genesis,
	}
	authorityParent := filepath.Join(t.TempDir(), "authority")
	if err := os.MkdirAll(authorityParent, 0700); err != nil { t.Fatal(err) }
	authorityRoot := filepath.Join(authorityParent, fsaanchorstore.FolderName)
	store, err := fsaanchorstore.Provision(authorityRoot, genesis)
	if err != nil { t.Fatal(err) }
	witnessRoot := filepath.Join(t.TempDir(), "witness")
	if err := os.MkdirAll(witnessRoot, 0700); err != nil { t.Fatal(err) }

	// The test harness signs only synthetic witnesses. A real deployment
	// requires separately governed signing custody and immutable storage.
	writeWitness := func(revision uint64, a fsahead.Anchor) error {
		h := WitnessHead{
			Schema: WitnessSchema, Domain: WitnessDomain,
			ArchiveID: pin.ArchiveID, KeyID: pin.KeyID,
			AuthorityEpoch: pin.AuthorityEpoch,
			BindingSHA256: pin.BindingSHA256,
			Sequence: a.Sequence, HeadSHA256: a.HeadSHA256, Revision: revision,
		}
		body, err := json.Marshal(h)
		if err != nil { return err }
		signed := SignedWitness{
			Head: h,
			SignatureHex: hex.EncodeToString(ed25519.Sign(
				witnessSecret, append([]byte(domainPrefix), body...))),
		}
		raw, err := json.Marshal(signed)
		if err != nil { return err }
		name := filepath.Join(witnessRoot, fmt.Sprintf("%08d.json", revision))
		f, err := os.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if err != nil { return err }
		_, err = f.Write(raw)
		if err == nil { err = f.Sync() }
		if closeErr := f.Close(); err == nil { err = closeErr }
		return err
	}
	readWitness := func() (SignedWitness, error) {
		var empty SignedWitness
		rows, err := os.ReadDir(witnessRoot)
		if err != nil || len(rows) == 0 { return empty, errors.New("witness ledger missing") }
		for i, row := range rows {
			if row.IsDir() || row.Name() != fmt.Sprintf("%08d.json", i+1) {
				return empty, errors.New("witness ledger gap or drift")
			}
		}
		data, err := os.ReadFile(filepath.Join(witnessRoot, rows[len(rows)-1].Name()))
		if err != nil || len(data) > MaxResponseBytes { return empty, errors.New("witness ledger unavailable") }
		var signed SignedWitness
		if err := json.Unmarshal(data, &signed); err != nil { return empty, err }
		if signed.Head.Revision != uint64(len(rows)) { return empty, errors.New("witness revision mismatch") }
		return signed, nil
	}
	if err := writeWitness(1, genesis); err != nil { t.Fatal(err) }

	var posts atomic.Int32
	// A new server and its store instance are created on each simulated
	// service restart; neither transport retains an in-memory trusted head.
	startPeers := func(authorityStore *fsaanchorstore.Store) (realMTLSPeer, realMTLSPeer) {
		authority := newRealMTLSPeer(t, "disk-authority", func(w http.ResponseWriter, r *http.Request) {
			switch {
			case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/anchor":
				a, err := authorityStore.ReadAnchor(r.Context())
				if err != nil { http.Error(w, "anchor unavailable", 503); return }
				_ = json.NewEncoder(w).Encode(anchorResponse{Schema: WireSchema, Anchor: makeWire(a)})
			case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/binding" &&
				r.URL.Query().Get("archive_id") == pin.ArchiveID:
				bound, err := authorityStore.ConfirmArchiveBinding(r.Context(), pin.ArchiveID)
				if err != nil { http.Error(w, "archive binding unavailable", 503); return }
				_ = json.NewEncoder(w).Encode(bindingResponse{
					Schema: WireSchema, ArchiveID: pin.ArchiveID,
					BindingSHA256: pin.BindingSHA256, Bound: bound,
				})
			case r.Method == http.MethodPost && r.URL.Path == "/v1/fsa/cas":
				var request casRequest
				if err := json.NewDecoder(r.Body).Decode(&request); err != nil || request.Schema != WireSchema {
					http.Error(w, "invalid request", 400); return
				}
				previous, e1 := parseAnchor(request.Previous)
				next, e2 := parseAnchor(request.Next)
				if e1 != nil || e2 != nil {
					http.Error(w, "invalid anchor", 400); return
				}
				committed, err := authorityStore.CompareAndSwap(r.Context(), previous, next)
				if err != nil { http.Error(w, "indeterminate", 503); return }
				if !committed { http.Error(w, "conflict", http.StatusConflict); return }
				posts.Add(1)
				// Commit is durable in the *test* store BEFORE dropping HTTP.
				hijacker, ok := w.(http.Hijacker)
				if !ok { http.Error(w, "ack unavailable", 503); return }
				connection, _, err := hijacker.Hijack()
				if err != nil { http.Error(w, "ack unavailable", 503); return }
				_ = connection.Close()
			default:
				http.Error(w, "method forbidden", http.StatusMethodNotAllowed)
			}
		})
		witness := newRealMTLSPeer(t, "disk-witness", func(w http.ResponseWriter, r *http.Request) {
			if r.Method != http.MethodGet || r.URL.Path != "/v1/fsa/highwater" ||
				r.URL.Query().Get("archive_id") != pin.ArchiveID {
				http.Error(w, "method forbidden", http.StatusMethodNotAllowed); return
			}
			signed, err := readWitness()
			if err != nil { http.Error(w, "witness unavailable", 503); return }
			_ = json.NewEncoder(w).Encode(witnessResponse{Schema: WireSchema, Witness: signed})
		})
		return authority, witness
	}

	authority, witness := startPeers(store)
	client, err := NewClient(authority.peer, witness.peer, pin)
	if err != nil { t.Fatal(err) }
	before, err := client.ReadAnchor(ctx)
	if err != nil || !sameAnchor(before, genesis) { t.Fatalf("initial witnessed anchor: %v", err) }
	target := genesis
	target.Sequence = 1
	target.HeadSHA256 = hx("d", 64)
	ok, err := client.CompareAndSwap(ctx, genesis, target)
	if ok || !errors.Is(err, ErrRemote) {
		t.Fatalf("lost CAS acknowledgement was trusted: committed=%v error=%v", ok, err)
	}
	if posts.Load() != 1 { t.Fatalf("CAS executed %d times", posts.Load()) }
	// The signer has not yet observed the accepted CAS. A lagging witness
	// MUST block scientific continuation instead of trusting the anchor.
	if _, err := client.ReadAnchor(ctx); !errors.Is(err, ErrWitness) {
		t.Fatalf("lagging independent witness accepted: %v", err)
	}
	onDisk, err := store.ReadAnchor(ctx)
	if err != nil || !sameAnchor(onDisk, target) { t.Fatalf("disk receipt missing after lost response: %v", err) }
	// Explicit test-harness publication models independent observation,
	// not an auto-retry or real witness synchronization implementation.
	if err := writeWitness(2, onDisk); err != nil { t.Fatal(err) }
	observed, err := client.ReadAnchor(ctx)
	if err != nil || !sameAnchor(observed, target) { t.Fatalf("witness reconciliation: %v", err) }

	authority.close()
	witness.close()
	// Every restart requires the independently supplied genesis and the
	// externally retained high-water revision. They are not read from FORGE.
	reopened, err := fsaanchorstore.Open(authorityRoot, genesis)
	if err != nil { t.Fatal(err) }
	authority2, witness2 := startPeers(reopened)
	restartPin := pin
	restartPin.MinimumRevision = 2
	restarted, err := NewClient(authority2.peer, witness2.peer, restartPin)
	if err != nil { t.Fatal(err) }
	fromRestart, err := restarted.ReadAnchor(ctx)
	if err != nil || !sameAnchor(fromRestart, target) { t.Fatalf("independent service restart: %v", err) }
	replayed, err := restarted.CompareAndSwap(ctx, genesis, target)
	if err != nil || replayed || posts.Load() != 1 {
		t.Fatalf("stale intent replayed after restart: %v %v %d", replayed, err, posts.Load())
	}

	// A locally valid truncated authority log must not defeat the signed
	// independent high-water statement, even after TLS server restart.
	if err := os.Remove(filepath.Join(authorityRoot, "receipts", "00000001.json")); err != nil { t.Fatal(err) }
	if _, err := restarted.ReadAnchor(ctx); !errors.Is(err, ErrWitness) {
		t.Fatalf("complete-tail rollback passed independent witness: %v", err)
	}
	// A simultaneous rollback of *test* witness files still fails when the
	// operator has independently preserved the accepted revision floor.
	if err := os.Remove(filepath.Join(witnessRoot, "00000002.json")); err != nil { t.Fatal(err) }
	if _, err := restarted.ReadAnchor(ctx); !errors.Is(err, ErrWitness) {
		t.Fatalf("witness rollback passed externally retained floor: %v", err)
	}
	if posts.Load() != 1 { t.Fatalf("rollback dispatched an extra CAS: %d", posts.Load()) }
}
