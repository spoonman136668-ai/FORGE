package eligibility

import (
    "errors"
    "testing"
)

// TestR27AtomicAuditSourceOnly is a benign qualification probe: it cannot
// dispatch or consume any experiment, apply a patch, or grant merge authority.
func TestR27AtomicAuditSourceOnly(t *testing.T) {
    cases := []struct {
        name string
        edit func(*Frozen, *Witness)
    }{
        {"unknown-lane", func(p *Frozen, _ *Witness) { p.Lane = "UNAUTHORIZED" }},
        {"ledger-untrusted", func(_ *Frozen, w *Witness) { w.LedgerAuthenticated = false }},
        {"start-uncertain", func(_ *Frozen, w *Witness) { w.StartReconciled = false }},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            frozen, witness := fixture()
            tc.edit(&frozen, &witness)
            if err := Check(frozen, witness); !errors.Is(err, ErrBlocked) {
                t.Fatalf("unqualified evidence accepted: %v", err)
            }
        })
    }
}
