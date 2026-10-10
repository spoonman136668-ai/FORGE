package fsaremote

// Source-only end-to-end network fixtures: real TLS 1.3, two independent
// certificate authorities and client identities, and real HTTP framing.
// The servers are ephemeral httptest instances; this is NOT proof of
// off-host durability, independently provisioned identities, or live FSA.

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/hex"
	"encoding/json"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/researchlog"
)

type realMTLSPeer struct {
	peer Peer
	served *atomic.Int32
	close func()
}

func newRealMTLSPeer(t *testing.T, label string, handler http.HandlerFunc) realMTLSPeer {
	t.Helper()
	now := time.Now()
	expiry := now.Add(time.Hour)
	caKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil { t.Fatal(err) }
	ca := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{CommonName: "FORGE test-only "+label+" root"},
		NotBefore: now.Add(-time.Hour), NotAfter: expiry,
		IsCA: true, BasicConstraintsValid: true,
		KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature,
	}
	caDER, err := x509.CreateCertificate(rand.Reader, ca, ca, &caKey.PublicKey, caKey)
	if err != nil { t.Fatal(err) }
	caParsed, err := x509.ParseCertificate(caDER)
	if err != nil { t.Fatal(err) }
	roots := x509.NewCertPool()
	roots.AddCert(caParsed)

	issue := func(serial int64, usage x509.ExtKeyUsage) (tls.Certificate, []byte) {
		t.Helper()
		key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if err != nil { t.Fatal(err) }
		leaf := &x509.Certificate{
			SerialNumber: big.NewInt(serial),
			Subject: pkix.Name{CommonName: "FORGE test-only "+label},
			NotBefore: now.Add(-time.Hour), NotAfter: expiry,
			KeyUsage: x509.KeyUsageDigitalSignature,
			ExtKeyUsage: []x509.ExtKeyUsage{usage},
			DNSNames: []string{"localhost"},
			IPAddresses: []net.IP{net.ParseIP("127.0.0.1")},
		}
		der, err := x509.CreateCertificate(rand.Reader, leaf, caParsed, &key.PublicKey, caKey)
		if err != nil { t.Fatal(err) }
		return tls.Certificate{Certificate: [][]byte{der, caDER}, PrivateKey: key}, der
	}
	serverCertificate, serverDER := issue(2, x509.ExtKeyUsageServerAuth)
	clientCertificate, clientDER := issue(3, x509.ExtKeyUsageClientAuth)
	parsedServer, err := x509.ParseCertificate(serverDER)
	if err != nil { t.Fatal(err) }
	spki := sha256.Sum256(parsedServer.RawSubjectPublicKeyInfo)

	p := realMTLSPeer{served: &atomic.Int32{}}
	server := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Requiring a verified, exact expected client identity is mandatory
		// for the synthetic servers; TLS alone is insufficient for ownership.
		if r.TLS == nil || len(r.TLS.VerifiedChains) == 0 ||
			len(r.TLS.PeerCertificates) == 0 ||
			!bytes.Equal(r.TLS.PeerCertificates[0].Raw, clientDER) {
			http.Error(w, "untrusted client identity", http.StatusForbidden)
			return
		}
		p.served.Add(1)
		handler(w, r)
	}))
	server.TLS = &tls.Config{
		MinVersion: tls.VersionTLS13,
		Certificates: []tls.Certificate{serverCertificate},
		ClientAuth: tls.RequireAndVerifyClientCert,
		ClientCAs: roots,
	}
	server.StartTLS()
	t.Cleanup(server.Close)
	p.peer = Peer{
		BaseURL: server.URL,
		Roots: roots,
		Certificate: clientCertificate,
		ServerSPKISHA256: hex.EncodeToString(spki[:]),
	}
	p.close = server.Close
	return p
}

func realMTLSPair(t *testing.T) (*Client, realMTLSPeer, realMTLSPeer) {
	t.Helper()
	pub, _ := kpair("FSA")
	witnessPublic, witnessSecret := kpair("independent-witness")
	pin := Pin{
		ArchiveID: hx("a", 64),
		KeyID: "FORGE_TEST_ONLY", PublicKey: pub, AuthorityEpoch: 4,
		BindingSHA256: hx("b", 64),
		WitnessPublicKey: witnessPublic, MinimumRevision: 1,
	}
	anchor := fsahead.Anchor{
		ArchiveID: pin.ArchiveID, KeyID: pin.KeyID, PublicKey: pin.PublicKey,
		AuthorityEpoch: pin.AuthorityEpoch, Sequence: 0,
		HeadSHA256: researchlog.Genesis,
	}
	head := WitnessHead{
		Schema: WitnessSchema, Domain: WitnessDomain,
		ArchiveID: pin.ArchiveID, KeyID: pin.KeyID,
		AuthorityEpoch: pin.AuthorityEpoch,
		BindingSHA256: pin.BindingSHA256,
		Sequence: 0, HeadSHA256: anchor.HeadSHA256, Revision: 1,
	}
	b, err := json.Marshal(head)
	if err != nil { t.Fatal(err) }
	signed := SignedWitness{
		Head: head,
		SignatureHex: hex.EncodeToString(ed25519.Sign(
			witnessSecret, append([]byte(domainPrefix), b...))),
	}
	authority := newRealMTLSPeer(t, "authority", func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/anchor":
			_ = json.NewEncoder(w).Encode(anchorResponse{Schema: WireSchema, Anchor: makeWire(anchor)})
		case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/binding" &&
			r.URL.Query().Get("archive_id") == pin.ArchiveID:
			_ = json.NewEncoder(w).Encode(bindingResponse{
				Schema: WireSchema, ArchiveID: pin.ArchiveID,
				BindingSHA256: pin.BindingSHA256, Bound: true,
			})
		default:
			http.Error(w, "not permitted", http.StatusMethodNotAllowed)
		}
	})
	witness := newRealMTLSPeer(t, "witness", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || r.URL.Path != "/v1/fsa/highwater" ||
			r.URL.Query().Get("archive_id") != pin.ArchiveID {
			http.Error(w, "not permitted", http.StatusMethodNotAllowed)
			return
		}
		_ = json.NewEncoder(w).Encode(witnessResponse{Schema: WireSchema, Witness: signed})
	})
	client, err := NewClient(authority.peer, witness.peer, pin)
	if err != nil { t.Fatal(err) }
	return client, authority, witness
}

func TestRealMutualTLSSeparateAuthorities(t *testing.T) {
	client, authority, witness := realMTLSPair(t)
	if authority.peer.BaseURL == witness.peer.BaseURL ||
		authority.peer.ServerSPKISHA256 == witness.peer.ServerSPKISHA256 ||
		bytes.Equal(authority.peer.Certificate.Certificate[0],
			witness.peer.Certificate.Certificate[0]) {
		t.Fatal("two nominally independent TLS identity domains collapsed")
	}
	got, err := client.ReadAnchor(context.Background())
	if err != nil || got.Sequence != 0 || got.HeadSHA256 != researchlog.Genesis {
		t.Fatalf("real TLS signed witness read: %+v %v", got, err)
	}
	bound, err := client.ConfirmArchiveBinding(context.Background(), got.ArchiveID)
	if err != nil || !bound { t.Fatalf("real TLS bound authority: %v %v", bound, err) }
	if authority.served.Load() < 3 || witness.served.Load() < 2 {
		t.Fatal("both independent mutual-TLS services were not contacted")
	}
}

func TestRealMutualTLSRejectsWrongTrustAndClientIdentity(t *testing.T) {
	_, authority, witness := realMTLSPair(t)
	pub, _ := kpair("FSA")
	witnessPublic, _ := kpair("independent-witness")
	pin := Pin{
		ArchiveID: hx("a", 64), KeyID: "FORGE_TEST_ONLY",
		PublicKey: pub, AuthorityEpoch: 4, BindingSHA256: hx("b", 64),
		WitnessPublicKey: witnessPublic, MinimumRevision: 1,
	}
	cases := []struct {
		name string
		change func(*Peer, *Peer)
	}{
		{"authority_client_identity_crossed", func(a, w *Peer) { a.Certificate = w.Certificate }},
		{"authority_trust_root_crossed", func(a, w *Peer) { a.Roots = w.Roots }},
		{"witness_client_identity_crossed", func(a, w *Peer) { w.Certificate = a.Certificate }},
		{"witness_trust_root_crossed", func(a, w *Peer) { w.Roots = a.Roots }},
		{"authority_spki_tampered", func(a, w *Peer) { a.ServerSPKISHA256 = hx("f", 64) }},
		{"witness_spki_tampered", func(a, w *Peer) { w.ServerSPKISHA256 = hx("f", 64) }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			a, w := authority.peer, witness.peer
			tc.change(&a, &w)
			bad, err := NewClient(a, w, pin)
			if err == nil {
				_, err = bad.ReadAnchor(context.Background())
			}
			if err == nil { t.Fatal("identity or SPKI substitution succeeded over real TLS") }
		})
	}
}


// TestRealMutualTLSLostCommitAcknowledgment checks the actual TLS/HTTP
// uncertain-commit boundary, rather than an in-memory RoundTripper mock.
// All peers, keys and state are test-only. No service is deployed.
func TestRealMutualTLSLostCommitAcknowledgment(t *testing.T) {
	ctx := context.Background()
	pub, _ := kpair("FSA")
	witnessPub, witnessSecret := kpair("independent-witness")
	pin := Pin{
		ArchiveID: hx("a", 64), KeyID: "FORGE_TEST_ONLY",
		PublicKey: pub, AuthorityEpoch: 4, BindingSHA256: hx("b", 64),
		WitnessPublicKey: witnessPub, MinimumRevision: 1,
	}
	original := fsahead.Anchor{
		ArchiveID: pin.ArchiveID, KeyID: pin.KeyID, PublicKey: pin.PublicKey,
		AuthorityEpoch: pin.AuthorityEpoch, HeadSHA256: researchlog.Genesis,
	}
	var current atomic.Pointer[fsahead.Anchor]
	current.Store(&original)
	var revision atomic.Uint64
	revision.Store(1)
	var postCount atomic.Int32

	authority := newRealMTLSPeer(t, "cas-authority", func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/v1/fsa/anchor":
			_ = json.NewEncoder(w).Encode(anchorResponse{
				Schema: WireSchema, Anchor: makeWire(*current.Load()),
			})
		case r.Method == http.MethodPost && r.URL.Path == "/v1/fsa/cas":
			var request casRequest
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil || request.Schema != WireSchema {
				http.Error(w, "invalid test CAS", http.StatusBadRequest)
				return
			}
			prior, priorErr := parseAnchor(request.Previous)
			next, nextErr := parseAnchor(request.Next)
			if priorErr != nil || nextErr != nil ||
				!sameAnchor(prior, *current.Load()) ||
				!pin.accepts(next) || next.Sequence <= prior.Sequence {
				http.Error(w, "conflicting test CAS", http.StatusConflict)
				return
			}
			current.Store(&next)
			revision.Store(2)
			postCount.Add(1)
			// The new value was committed before the HTTP connection broke.
			// A lost response must NEVER trigger a blind retry.
			if hijacker, ok := w.(http.Hijacker); ok {
				if conn, _, err := hijacker.Hijack(); err == nil {
					_ = conn.Close()
					return
				}
			}
			// Fallback: a truncated acknowledgment remains indeterminate.
			w.WriteHeader(http.StatusOK)
		default:
			http.Error(w, "not permitted", http.StatusMethodNotAllowed)
		}
	})
	witness := newRealMTLSPeer(t, "cas-witness", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || r.URL.Path != "/v1/fsa/highwater" ||
			r.URL.Query().Get("archive_id") != pin.ArchiveID {
			http.Error(w, "not permitted", http.StatusMethodNotAllowed)
			return
		}
		a := current.Load()
		head := WitnessHead{
			Schema: WitnessSchema, Domain: WitnessDomain,
			ArchiveID: pin.ArchiveID, KeyID: pin.KeyID,
			AuthorityEpoch: pin.AuthorityEpoch, BindingSHA256: pin.BindingSHA256,
			Sequence: a.Sequence, HeadSHA256: a.HeadSHA256, Revision: revision.Load(),
		}
		body, err := json.Marshal(head)
		if err != nil {
			http.Error(w, "test encoding failed", http.StatusInternalServerError)
			return
		}
		signed := SignedWitness{
			Head: head,
			SignatureHex: hex.EncodeToString(ed25519.Sign(
				witnessSecret, append([]byte(domainPrefix), body...))),
		}
		_ = json.NewEncoder(w).Encode(witnessResponse{Schema: WireSchema, Witness: signed})
	})
	client, err := NewClient(authority.peer, witness.peer, pin)
	if err != nil { t.Fatal(err) }
	before, err := client.ReadAnchor(ctx)
	if err != nil || !sameAnchor(before, original) { t.Fatalf("genesis: %v", err) }

	next := original
	next.Sequence = 1
	next.HeadSHA256 = hx("d", 64)
	ok, err := client.CompareAndSwap(ctx, original, next)
	if ok || err != ErrRemote {
		t.Fatalf("lost reply falsely accepted: accepted=%v error=%v", ok, err)
	}
	if postCount.Load() != 1 || !sameAnchor(*current.Load(), next) {
		t.Fatalf("ambiguous response did not follow exactly one actual commit: %d", postCount.Load())
	}
	readback, err := client.ReadAnchor(ctx)
	if err != nil || !sameAnchor(readback, next) { t.Fatalf("signed reconciliation: %v", err) }
	replayed, err := client.CompareAndSwap(ctx, original, next)
	if err != nil || replayed || postCount.Load() != 1 {
		t.Fatalf("original intent replayed: replay=%v err=%v posts=%d", replayed, err, postCount.Load())
	}
	// A newly constructed client must carry an independently preserved
	// high-water revision pin; otherwise process restart loses that defense.
	restartPin := pin
	restartPin.MinimumRevision = 2
	restarted, err := NewClient(authority.peer, witness.peer, restartPin)
	if err != nil { t.Fatal(err) }
	if _, err := restarted.ReadAnchor(ctx); err != nil { t.Fatalf("restarted pinned read: %v", err) }
	current.Store(&original)
	revision.Store(1)
	if _, err := restarted.ReadAnchor(ctx); err != ErrWitness {
		t.Fatalf("witness rollback passed restart pin: %v", err)
	}
}
