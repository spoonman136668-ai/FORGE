package fsawitnessguard

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/spoonman136668-ai/forge/fsaremote"
)

func inspect(t *testing.T, g *Guard, before, after fsaremote.SignedWitness) RecoveryObservation {
	t.Helper()
	r, err := g.InspectRecovery(context.Background(), g.pin.ArchiveID, before, after)
	if err != nil {
		t.Fatal(err)
	}
	return r
}

func TestInspectRecoveryUnchangedAndConvergedWithoutWrites(t *testing.T) {
	g, l, f, before, after, _ := setup(t)
	r := inspect(t, g, before, after)
	if r.State != RecoveryPreviousObserved || r.LedgerRevision != before.Head.Revision ||
		r.FloorRevision != before.Head.Revision {
		t.Fatalf("wrong original observation %+v", r)
	}
	if l.calls != 0 || f.calls != 0 {
		t.Fatal("read-only inspection performed a write")
	}
	ok, err := g.Advance(context.Background(), before, after)
	if err != nil || !ok {
		t.Fatalf("advance failed %v %v", ok, err)
	}
	r = inspect(t, g, before, after)
	if r.State != RecoveryNextObserved || r.LedgerRevision != after.Head.Revision ||
		r.FloorRevision != after.Head.Revision {
		t.Fatalf("wrong converged observation %+v", r)
	}
	if l.calls != 1 || f.calls != 1 {
		t.Fatalf("inspection replayed a write: ledger %d floor %d", l.calls, f.calls)
	}
	// A new guard instance must use the separately injected stores and pin.
	reopened, err := New(g.pin, l, f)
	if err != nil {
		t.Fatal(err)
	}
	if r := inspect(t, reopened, before, after); r.State != RecoveryNextObserved {
		t.Fatalf("restart lost exact observation %+v", r)
	}
}

func TestInspectRecoveryInterruptedLedgerWriteNeverReplays(t *testing.T) {
	g, l, f, before, after, _ := setup(t)
	l.ambiguous = true
	ok, err := g.Advance(context.Background(), before, after)
	if ok || !errors.Is(err, ErrUntrusted) {
		t.Fatalf("uncertain ledger write accepted %v %v", ok, err)
	}
	r := inspect(t, g, before, after)
	if r.State != RecoveryLedgerAhead || r.LedgerRevision != after.Head.Revision ||
		r.FloorRevision != before.Head.Revision {
		t.Fatalf("interrupted write misclassified %+v", r)
	}
	if l.calls != 1 || f.calls != 0 {
		t.Fatalf("diagnostics retried writes %d %d", l.calls, f.calls)
	}
	if _, err := g.ReadHighWater(context.Background(), g.pin.ArchiveID); !errors.Is(err, ErrUntrusted) {
		t.Fatalf("half committed ledger became trusted %v", err)
	}
}

func TestInspectRecoveryFloorAheadQuarantined(t *testing.T) {
	g, l, f, before, after, _ := setup(t)
	hash, err := digest(after)
	if err != nil {
		t.Fatal(err)
	}
	f.mu.Lock()
	f.current = Commitment{Revision: after.Head.Revision, WitnessSHA256: hash}
	f.mu.Unlock()
	r := inspect(t, g, before, after)
	if r.State != RecoveryFloorAhead {
		t.Fatalf("unexpected floor advance not quarantined %+v", r)
	}
	if l.calls != 0 || f.calls != 0 {
		t.Fatal("inspection mutated state")
	}
	if _, err := g.ReadHighWater(context.Background(), g.pin.ArchiveID); !errors.Is(err, ErrUntrusted) {
		t.Fatalf("floor ahead became trusted %v", err)
	}
}

func TestInspectRecoveryRejectsForgedUnexpectedOrUnavailableEvidence(t *testing.T) {
	t.Run("bad caller inputs", func(t *testing.T) {
		g, l, f, before, after, _ := setup(t)
		forged := after
		forged.SignatureHex = strings.Repeat("0", 128)
		cases := []struct {
			name string
			ctx context.Context
			id string
			prev fsaremote.SignedWitness
			next fsaremote.SignedWitness
		}{
			{"nil_context", nil, g.pin.ArchiveID, before, after},
			{"cancelled_context", cancelledContext(), g.pin.ArchiveID, before, after},
			{"foreign_archive", context.Background(), strings.Repeat("f", 64), before, after},
			{"forged_successor", context.Background(), g.pin.ArchiveID, before, forged},
			{"forged_predecessor", context.Background(), g.pin.ArchiveID, forged, after},
			{"replayed_successor", context.Background(), g.pin.ArchiveID, before, before},
		}
		for _, c := range cases {
			t.Run(c.name, func(t *testing.T) {
				if _, err := g.InspectRecovery(c.ctx, c.id, c.prev, c.next); !errors.Is(err, ErrUntrusted) {
					t.Fatalf("invalid inputs accepted: %v", err)
				}
			})
		}
		if l.calls != 0 || f.calls != 0 {
			t.Fatal("invalid input wrote to stores")
		}
	})
	t.Run("floor outage", func(t *testing.T) {
		g, _, f, before, after, _ := setup(t)
		f.outage = true
		if _, err := g.InspectRecovery(context.Background(), g.pin.ArchiveID, before, after); !errors.Is(err, ErrUntrusted) {
			t.Fatalf("outage accepted %v", err)
		}
	})
	t.Run("unexpected digest", func(t *testing.T) {
		g, _, f, before, after, _ := setup(t)
		f.mu.Lock()
		f.current.WitnessSHA256 = strings.Repeat("f", 64)
		f.mu.Unlock()
		if _, err := g.InspectRecovery(context.Background(), g.pin.ArchiveID, before, after); !errors.Is(err, ErrUntrusted) {
			t.Fatalf("unwitnessed floor accepted %v", err)
		}
	})
	t.Run("forged ledger", func(t *testing.T) {
		g, l, _, before, after, _ := setup(t)
		l.mu.Lock()
		l.current.SignatureHex = strings.Repeat("0", 128)
		l.mu.Unlock()
		if _, err := g.InspectRecovery(context.Background(), g.pin.ArchiveID, before, after); !errors.Is(err, ErrUntrusted) {
			t.Fatalf("forged ledger accepted %v", err)
		}
	})
}

func cancelledContext() context.Context {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	return ctx
}

type changingLedger struct {
	one fsaremote.SignedWitness
	two fsaremote.SignedWitness
	reads int
}
func (c *changingLedger) Read(context.Context) (fsaremote.SignedWitness, error) {
	c.reads++
	if c.reads == 1 {
		return c.one, nil
	}
	return c.two, nil
}
func (c *changingLedger) CompareAndSwap(context.Context, string, fsaremote.SignedWitness) (bool, error) {
	panic("read-only recovery attempted CAS")
}

func TestInspectRecoveryRejectsMovingSnapshots(t *testing.T) {
	g, l, f, before, after, _ := setup(t)
	moving := &changingLedger{one: before, two: after}
	g.ledger = moving
	if _, err := g.InspectRecovery(context.Background(), g.pin.ArchiveID, before, after); !errors.Is(err, ErrUntrusted) {
		t.Fatalf("mixed snapshots accepted %v", err)
	}
	if moving.reads != 2 || l.calls != 0 || f.calls != 0 {
		t.Fatalf("read-only snapshot contract violated: %d %d %d", moving.reads, l.calls, f.calls)
	}
}
