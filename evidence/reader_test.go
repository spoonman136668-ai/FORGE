package evidence

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/spoonman136668-ai/forge/contracts"
)

type fixtureSource struct {
	docs map[contracts.Lane][]byte
	fail error
}

func (s *fixtureSource) ReadReceipt(ctx context.Context, lane contracts.Lane) ([]byte, error) {
	if s.fail != nil {
		return nil, s.fail
	}
	return append([]byte(nil), s.docs[lane]...), nil
}

type fixtureAuth struct {
	calls int
	fail  error
}

func (a *fixtureAuth) Authenticate(ctx context.Context, lane contracts.Lane, b []byte, w Witness) error {
	a.calls++
	return a.fail
}
func hex64(ch string) string { return strings.Repeat(ch, 64) }
func fixture(t *testing.T) (*fixtureSource, *fixtureAuth, map[contracts.Lane]Witness) {
	t.Helper()
	src := &fixtureSource{docs: map[contracts.Lane][]byte{}}
	pins := map[contracts.Lane]Witness{}
	for _, lane := range []contracts.Lane{contracts.Wingless, contracts.Yggdrasil} {
		o := contracts.Observation{Schema: contracts.ObservationSchema, Lane: lane, AuthorityEpoch: 12, SourceWitnessSHA256: hex64("a"), LedgerWitnessSHA256: hex64("b"), LatestOutcome: "MIXED"}
		receipt := Receipt{Schema: ReceiptSchema, Observation: o, SourceClass: contracts.Synthetic, OriginalStartedSHA256: hex64("c"), OriginalTerminalSHA256: hex64("d"), OriginalArchiveSHA256: hex64("e"), OriginalRawEvidenceSHA256: hex64("f"), OriginalRunConsumed: true}
		b, e := json.Marshal(receipt)
		if e != nil {
			t.Fatal(e)
		}
		src.docs[lane] = b
		h := sha256.Sum256(b)
		pins[lane] = Witness{AuthorityEpoch: 12, SourceWitnessSHA256: o.SourceWitnessSHA256, LedgerWitnessSHA256: o.LedgerWitnessSHA256, ReceiptSHA256: hex.EncodeToString(h[:])}
	}
	return src, &fixtureAuth{}, pins
}
func TestReadOnlyDualLaneWithIndependentAuthentication(t *testing.T) {
	src, auth, pins := fixture(t)
	r, e := NewReader(src, auth, pins)
	if e != nil {
		t.Fatal(e)
	}
	pins[contracts.Wingless] = Witness{} // Must not change the reader's copied immutable witness.
	for _, lane := range []contracts.Lane{contracts.Wingless, contracts.Yggdrasil} {
		o, e := r.ReadLatest(context.Background(), lane)
		if e != nil {
			t.Fatal(e)
		}
		if o.Lane != lane || o.LatestOutcome != "MIXED" || o.ScientificAuthority || o.AcceptedRefMutation {
			t.Fatalf("authority escalation: %+v", o)
		}
	}
	if auth.calls != 2 {
		t.Fatalf("auth calls=%d", auth.calls)
	}
}
func TestUnsafeOrUnauthenticatedSourcesFailClosed(t *testing.T) {
	for _, tc := range []struct {
		name string
		f    func(*fixtureSource, *fixtureAuth, map[contracts.Lane]Witness)
	}{
		{"read_failed", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			s.fail = errors.New("unavailable")
		}},
		{"auth_failed", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			a.fail = errors.New("bad signature")
		}},
		{"tamper_bytes", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			s.docs[contracts.Wingless] = append(s.docs[contracts.Wingless], byte('x'))
		}},
		{"wrong_epoch", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			w := p[contracts.Wingless]
			w.AuthorityEpoch++
			p[contracts.Wingless] = w
		}},
		{"wrong_source", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			w := p[contracts.Wingless]
			w.SourceWitnessSHA256 = hex64("0")
			p[contracts.Wingless] = w
		}},
		{"wrong_ledger", func(s *fixtureSource, a *fixtureAuth, p map[contracts.Lane]Witness) {
			w := p[contracts.Wingless]
			w.LedgerWitnessSHA256 = hex64("0")
			p[contracts.Wingless] = w
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s, a, p := fixture(t)
			tc.f(s, a, p)
			r, e := NewReader(s, a, p)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = r.ReadLatest(context.Background(), contracts.Wingless); e == nil {
				t.Fatal("unsupported evidence accepted")
			}
		})
	}
	src, a, pins := fixture(t)
	if _, e := NewReader(src, nil, pins); e == nil {
		t.Fatal("nil authenticator accepted")
	}
	delete(pins, contracts.Yggdrasil)
	if _, e := NewReader(src, a, pins); e == nil {
		t.Fatal("missing lane pin accepted")
	}
}
func TestCanonicalAndPrivilegeEscalationNegatives(t *testing.T) {
	src, _, _ := fixture(t)
	good := src.docs[contracts.Wingless]
	for _, tc := range []struct {
		name  string
		bytes []byte
	}{
		{"unknown_key", bytes.Replace(good, []byte(`"schema":`), []byte(`"unexpected":true,"schema":`), 1)},
		{"duplicate_key", bytes.Replace(good, []byte(`"schema":`), []byte(`"schema":"FORGED","schema":`), 1)},
		{"trailing", append(append([]byte(nil), good...), []byte(`{}`)...)},
		{"noncanonical_space", bytes.Replace(good, []byte(`,"observation":`), []byte(`, "observation":`), 1)},
		{"privileged", bytes.Replace(good, []byte(`"scientific_accepted":false`), []byte(`"scientific_accepted":true`), 1)},
		{"replay", bytes.Replace(good, []byte(`"replay_authorized":false`), []byte(`"replay_authorized":true`), 1)},
		{"not_consumed", bytes.Replace(good, []byte(`"original_run_consumed":true`), []byte(`"original_run_consumed":false`), 1)},
		{"oversize", bytes.Repeat([]byte("x"), MaxReceiptBytes+1)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, e := DecodeCanonical(tc.bytes); e == nil {
				t.Fatal("invalid receipt accepted")
			}
		})
	}
	if _, e := DecodeCanonical(good); e != nil {
		t.Fatalf("good receipt refused: %s", e)
	}
}
func TestCancellationAndUnknownLanes(t *testing.T) {
	src, auth, pins := fixture(t)
	r, e := NewReader(src, auth, pins)
	if e != nil {
		t.Fatal(e)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, e := r.ReadLatest(ctx, contracts.Wingless); !errors.Is(e, context.Canceled) {
		t.Fatalf("cancel: %v", e)
	}
	if _, e := r.ReadLatest(context.Background(), contracts.Lane("not-a-lane")); e == nil {
		t.Fatal("unknown lane accepted")
	}
	if auth.calls != 0 {
		t.Fatalf("unexpected auth calls: %d", auth.calls)
	}
}
