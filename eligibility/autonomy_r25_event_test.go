package eligibility

import (
    "errors"
    "strings"
    "testing"
)

// TestR25AutonomousSourceEvidenceChecks is a source-only, non-executing
// qualification probe. It never consumes an experiment or grants authority.
func TestR25AutonomousSourceEvidenceChecks(t *testing.T) {
    cases := []struct{
        name string
        edit func(*Frozen, *Witness)
    }{
        {"cross-lane-seed", func(p *Frozen, _ *Witness) {
            p.SeedIDs = []string{"Yggdrasil:seed_02"}
        }},
        {"source-changed-after-freeze", func(p *Frozen, _ *Witness) {
            p.SourceSHA = strings.Repeat("b", 40)
        }},
        {"no-independent-ledger", func(_ *Frozen, w *Witness) {
            w.LedgerAuthenticated = false
        }},
        {"uncertain-start", func(_ *Frozen, w *Witness) {
            w.StartReconciled = false
        }},
        {"cohort-already-consumed", func(p *Frozen, w *Witness) {
            w.ConsumedCohorts[p.CohortSHA256] = true
        }},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            frozen, witness := fixture()
            tc.edit(&frozen, &witness)
            if err := Check(frozen, witness); !errors.Is(err, ErrBlocked) {
                t.Fatalf("unqualified source cleared a scientific boundary: %v", err)
            }
        })
    }
}
