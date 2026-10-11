package fsaremote

// Source-only fault-injection tests over real TLS 1.3/mTLS, using two
// separately identified ephemeral endpoints and synthetic signer keys.
// A closed local HTTP connection models transport loss, not real off-host
// failure-domain separation or physical power-loss durability.
import (
	"context"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"sync/atomic"
	"testing"

	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/researchlog"
)

type partitionFixture struct {
	client *Client
	genesis fsahead.Anchor
	next fsahead.Anchor
	witnessDown atomic.Bool
	bindingDown atomic.Bool
	witnessDownAfterCommit atomic.Bool
	posts atomic.Int32
}

func cutTestTLSConnection(w http.ResponseWriter) {
	if hijacker, ok := w.(http.Hijacker); ok {
		conn, _, err := hijacker.Hijack()
		if err == nil {
			_ = conn.Close()
			return
		}
	}
	http.Error(w, "synthetic transport interruption", http.StatusServiceUnavailable)
}

func newPartitionFixture(t *testing.T) *partitionFixture {
	t.Helper()
	pub, _ := kpair("FSA")
	witnessPub, witnessSecret := kpair("independent-witness")
	pin := Pin{
		ArchiveID: hx("a", 64), KeyID: "FORGE_TEST_ONLY",
		PublicKey: pub, AuthorityEpoch: 4,
		BindingSHA256: hx("b", 64),
		WitnessPublicKey: witnessPub, MinimumRevision: 1,
	}
	genesis := fsahead.Anchor{
		ArchiveID: pin.ArchiveID, KeyID: pin.KeyID,
		PublicKey: pin.PublicKey, AuthorityEpoch: pin.AuthorityEpoch,
		HeadSHA256: researchlog.Genesis,
	}
	next := genesis
	next.Sequence = 1
	next.HeadSHA256 = hx("d", 64)
	f := &partitionFixture{genesis:genesis, next:next}
	var current atomic.Pointer[fsahead.Anchor]
	current.Store(&f.genesis)
	var revision atomic.Uint64
	revision.Store(1)

	authority := newRealMTLSPeer(t, "partition-authority", func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/anchor":
			_ = json.NewEncoder(w).Encode(anchorResponse{
				Schema: WireSchema, Anchor: makeWire(*current.Load()),
			})
		case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/binding" &&
			r.URL.Query().Get("archive_id") == pin.ArchiveID:
			if f.bindingDown.Load() {
				cutTestTLSConnection(w)
				return
			}
			_ = json.NewEncoder(w).Encode(bindingResponse{
				Schema: WireSchema, ArchiveID: pin.ArchiveID,
				BindingSHA256: pin.BindingSHA256, Bound: true,
			})
		case r.Method == http.MethodPost && r.URL.Path == "/v1/fsa/cas":
			f.posts.Add(1)
			var req casRequest
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Schema != WireSchema {
				http.Error(w, "invalid CAS", http.StatusBadRequest)
				return
			}
			prior, errPrior := parseAnchor(req.Previous)
			proposed, errNext := parseAnchor(req.Next)
			if errPrior != nil || errNext != nil ||
				!sameAnchor(*current.Load(), prior) ||
				!sameAnchor(prior, f.genesis) || !sameAnchor(proposed, f.next) {
				http.Error(w, "conflicting CAS", http.StatusConflict)
				return
			}
			current.Store(&f.next)
			revision.Store(2)
			if f.witnessDownAfterCommit.Load() {
				f.witnessDown.Store(true)
			}
			_ = json.NewEncoder(w).Encode(casResponse{Schema: WireSchema, Committed: true})
		default:
			http.Error(w, "forbidden method", http.StatusMethodNotAllowed)
		}
	})
	witness := newRealMTLSPeer(t, "partition-witness", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || r.URL.Path != "/v1/fsa/highwater" ||
			r.URL.Query().Get("archive_id") != pin.ArchiveID {
			http.Error(w, "forbidden method", http.StatusMethodNotAllowed)
			return
		}
		if f.witnessDown.Load() {
			cutTestTLSConnection(w)
			return
		}
		a := current.Load()
		head := WitnessHead{
			Schema: WitnessSchema, Domain: WitnessDomain,
			ArchiveID: pin.ArchiveID, KeyID: pin.KeyID,
			AuthorityEpoch: pin.AuthorityEpoch,
			BindingSHA256: pin.BindingSHA256,
			Sequence: a.Sequence, HeadSHA256: a.HeadSHA256,
			Revision: revision.Load(),
		}
		body, err := json.Marshal(head)
		if err != nil { http.Error(w, "signing fixture unavailable", 503); return }
		signed := SignedWitness{
			Head: head, SignatureHex: hex.EncodeToString(ed25519.Sign(
				witnessSecret, append([]byte(domainPrefix), body...))),
		}
		_ = json.NewEncoder(w).Encode(witnessResponse{Schema: WireSchema, Witness: signed})
	})
	client, err := NewClient(authority.peer, witness.peer, pin)
	if err != nil { t.Fatal(err) }
	f.client = client
	return f
}

func TestRealMutualTLSConnectivityPartitionOneShotFencing(t *testing.T) {
	for _, scenario := range []struct{
		name string
		partition func(*partitionFixture)
	}{
		{"independent_witness_unreachable_before_CAS", func(f *partitionFixture){
			f.witnessDown.Store(true)
		}},
		{"archive_binding_unreachable_before_CAS", func(f *partitionFixture){
			f.bindingDown.Store(true)
		}},
	}{
		t.Run(scenario.name, func(t *testing.T){
			f := newPartitionFixture(t)
			ctx := context.Background()
			original, err := f.client.ReadAnchor(ctx)
			if err != nil || !sameAnchor(original, f.genesis) {
				t.Fatalf("initial witnessed genesis unavailable: %v", err)
			}
			scenario.partition(f)
			accepted, err := f.client.CompareAndSwap(ctx, f.genesis, f.next)
			if accepted || err == nil {
				t.Fatalf("partition falsely accepted CAS: accepted=%v error=%v", accepted, err)
			}
			if f.posts.Load() != 0 {
				t.Fatalf("partition permitted CAS POST count=%d", f.posts.Load())
			}
			// Restore only test connectivity; the *same* original intent may
			// now submit once because no previous POST took place.
			f.bindingDown.Store(false)
			f.witnessDown.Store(false)
			accepted, err = f.client.CompareAndSwap(ctx, f.genesis, f.next)
			if !accepted || err != nil || f.posts.Load() != 1 {
				t.Fatalf("restored first CAS: accepted=%v err=%v posts=%d",
					accepted, err, f.posts.Load())
			}
		})
	}
}

func TestRealMutualTLSWitnessPartitionImmediatelyAfterCAS(t *testing.T) {
	f := newPartitionFixture(t)
	ctx := context.Background()
	f.witnessDownAfterCommit.Store(true)
	accepted, err := f.client.CompareAndSwap(ctx, f.genesis, f.next)
	if accepted || !errors.Is(err, ErrRemote) {
		t.Fatalf("CAS with lost witness acknowledgment accepted: %v %v", accepted, err)
	}
	if f.posts.Load() != 1 {
		t.Fatalf("uncertain commit posts=%d want 1", f.posts.Load())
	}
	// The authority advanced but connectivity failure must not permit
	// duplicate work. Only read-only observation follows the partition.
	f.witnessDown.Store(false)
	got, err := f.client.ReadAnchor(ctx)
	if err != nil || !sameAnchor(got, f.next) {
		t.Fatalf("cannot reconcile trusted committed head: %v", err)
	}
	again, err := f.client.CompareAndSwap(ctx, f.genesis, f.next)
	if again || err != nil || f.posts.Load() != 1 {
		t.Fatalf("original CAS was replayed: accepted=%v err=%v posts=%d",
			again, err, f.posts.Load())
	}
}
