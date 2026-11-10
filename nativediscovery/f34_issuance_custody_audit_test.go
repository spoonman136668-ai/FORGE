package nativediscovery

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"testing"
)

// F34 is a source-bound forensic test, not a model, admission gate, or new policy.
// Its prospectively frozen protocol is docs/NATIVE-DISCOVERY-F34-ISSUANCE-CUSTODY-AUDIT.md.
const (
	f34Schema      = "forge.native-discovery.issuance-custody-audit.dev.v1"
	f34Parent      = "63cc1764fe1a11acd2d752a033f33eff0d9ebc1b"
	f34Invalid     = "F34_AUDIT_INVALID"
	f34Confirmed   = "F34_PENDING_EVENT_REINTERPRETATION_CONFIRMED"
	f34NotObserved = "F34_PENDING_EVENT_REINTERPRETATION_NOT_OBSERVED"
)

type f34Witness struct {
	Seed         uint32 `json:"seed"`
	Boundary     int    `json:"boundary"`
	IssueTime    int    `json:"issue_time"`
	Cue          int    `json:"cue"`
	Tick         int    `json:"tick"`
	IssuingLaw   string `json:"issuing_law"`
	CurrentLaw   string `json:"current_law"`
	OriginalMask int    `json:"original_mask"`
	OriginalLag  int    `json:"original_lag"`
	OriginalDue  int    `json:"original_due"`
	PhysicalMask int    `json:"physical_mask"`
	ReplayedMask int    `json:"replayed_mask"`
}
type f34Scenario struct {
	Seed         uint32 `json:"seed"`
	Boundary     int    `json:"boundary"`
	IssueTime    int    `json:"issue_time"`
	Cue          int    `json:"cue"`
	IssuingLaw   string `json:"issuing_law"`
	OriginalMask int    `json:"original_mask"`
	OriginalLag  int    `json:"original_lag"`
	OriginalDue  int    `json:"original_due"`
	Mismatches   int    `json:"mismatches"`
	Heldover     bool   `json:"heldover"`
}
type f34Report struct {
	Schema                      string        `json:"schema"`
	Parent                      string        `json:"parent"`
	Classification              string        `json:"classification"`
	Seeds                       [4]uint32     `json:"seeds"`
	Boundaries                  [3]int        `json:"boundaries"`
	Scenarios                   int           `json:"scenarios"`
	TickComparisons             int           `json:"tick_comparisons"`
	PhysicalMismatches          int           `json:"physical_mismatches"`
	IssuanceReferenceMismatches int           `json:"issuance_reference_mismatches"`
	CurrentLawReplayMismatches  int           `json:"current_law_replay_mismatches"`
	HeldoverEvents              int           `json:"heldover_events"`
	MismatchesByWorldBoundary   [4][3]int     `json:"mismatches_by_world_boundary"`
	HeldoversByWorldBoundary    [4][3]int     `json:"heldovers_by_world_boundary"`
	ScenariosDetail             []f34Scenario `json:"scenario_details"`
	FirstWitness                *f34Witness   `json:"first_witness"`
	ScenariosSHA256             string        `json:"scenarios_sha256"`
	DevelopmentOnly             bool          `json:"development_only"`
	EarlierNegativesPreserved   bool          `json:"earlier_negatives_preserved"`
	FirstUseConsumed            bool          `json:"first_use_consumed"`
	ScientificAccepted          bool          `json:"scientific_accepted"`
}

func f34Audit() (f34Report, error) {
	report := f34Report{
		Schema: f34Schema, Parent: f34Parent,
		Seeds:           [4]uint32{367, 373, 379, 383},
		Boundaries:      [3]int{24, 48, 72},
		DevelopmentOnly: true, EarlierNegativesPreserved: true,
	}
	for si, seed := range report.Seeds {
		for bi, boundary := range report.Boundaries {
			for _, issue := range [2]int{boundary - 2, boundary - 1} {
				for cue := 0; cue < 4; cue++ {
					w, e := f33NewWorld(seed)
					if e != nil {
						return report, e
					}
					priorLaw, e := f33Phase(seed, issue)
					if e != nil {
						return report, e
					}
					original, e := f32Law(priorLaw, cue)
					if e != nil {
						return report, e
					}
					due := issue + original.Lag - 1
					sc := f34Scenario{
						Seed: seed, Boundary: boundary, IssueTime: issue, Cue: cue,
						IssuingLaw: string(priorLaw), OriginalMask: original.Mask,
						OriginalLag: original.Lag, OriginalDue: due, Heldover: due >= boundary,
					}
					if sc.Heldover {
						report.HeldoverEvents++
						report.HeldoversByWorldBoundary[si][bi]++
					}
					history := make([]f32Issued, 0, boundary+3)
					for t := 0; t <= boundary+2; t++ {
						currentLaw, e := f33Phase(seed, t)
						if e != nil {
							return report, e
						}
						action := 0
						currentCue := 0
						if t == issue {
							action = 1
							currentCue = cue
						}
						realBefore := w.State
						observed, _, e := w.step(t, currentCue, action)
						if e != nil {
							return report, e
						}
						physical := realBefore ^ observed
						expected := 0
						if due == t {
							expected = original.Mask
						}
						// Verify oracle issuance custody against the *actual* simulator, every tick.
						if physical != expected {
							report.PhysicalMismatches++
							if t >= boundary {
								report.IssuanceReferenceMismatches++
							}
						}
						if t >= boundary {
							// Deliberately privileged CURRENT-law template: audit-only.
							// This proves whether the historical replay helper can even be
							// correct when the current regime's law is perfectly known.
							var current [4]f32Spec
							for c := 0; c < 4; c++ {
								current[c], e = f32Law(currentLaw, c)
								if e != nil {
									return report, e
								}
							}
							replay := f32Due(history, f32Issued{Cue: currentCue, Action: action}, t, current, false)
							report.TickComparisons++
							if replay != physical {
								report.CurrentLawReplayMismatches++
								report.MismatchesByWorldBoundary[si][bi]++
								sc.Mismatches++
								if report.FirstWitness == nil {
									report.FirstWitness = &f34Witness{
										Seed: seed, Boundary: boundary, IssueTime: issue, Cue: cue,
										Tick: t, IssuingLaw: string(priorLaw), CurrentLaw: string(currentLaw),
										OriginalMask: original.Mask, OriginalLag: original.Lag,
										OriginalDue: due, PhysicalMask: physical, ReplayedMask: replay,
									}
								}
							}
						}
						history = append(history, f32Issued{Cue: currentCue, Action: action})
					}
					report.Scenarios++
					report.ScenariosDetail = append(report.ScenariosDetail, sc)
				}
			}
		}
	}
	details, _ := json.Marshal(report.ScenariosDetail)
	digest := sha256.Sum256(details)
	report.ScenariosSHA256 = hex.EncodeToString(digest[:])
	report.Classification = f34NotObserved
	if report.PhysicalMismatches > 0 || report.IssuanceReferenceMismatches > 0 {
		report.Classification = f34Invalid
	} else if report.CurrentLawReplayMismatches > 0 {
		report.Classification = f34Confirmed
	}
	if report.Scenarios != 96 || report.TickComparisons != 288 || len(report.ScenariosDetail) != 96 || report.HeldoverEvents < 1 {
		return report, errors.New("F34_CUSTODY_TOTALS_INVALID")
	}
	if report.Classification == f34Invalid {
		return report, errors.New("F34_ISSUANCE_REFERENCE_INVALID")
	}
	return report, nil
}
func TestF34FrozenIssuanceCustodyAudit(t *testing.T) {
	a, e := f34Audit()
	if e != nil {
		t.Fatal(e)
	}
	b, e := f34Audit()
	if e != nil || !reflect.DeepEqual(a, b) {
		t.Fatal("non-deterministic F34 audit", e)
	}
	if a.Schema != f34Schema || a.Parent != f34Parent ||
		a.Seeds != [4]uint32{367, 373, 379, 383} || a.Boundaries != [3]int{24, 48, 72} ||
		a.Scenarios != 96 || a.TickComparisons != 288 || a.PhysicalMismatches != 0 ||
		a.IssuanceReferenceMismatches != 0 || a.DevelopmentOnly != true ||
		!a.EarlierNegativesPreserved || a.FirstUseConsumed || a.ScientificAccepted {
		t.Fatal("frozen audit qualification invalid")
	}
	details, _ := json.Marshal(a.ScenariosDetail)
	sum := sha256.Sum256(details)
	if a.ScenariosSHA256 != hex.EncodeToString(sum[:]) {
		t.Fatal("scenario checksum invalid")
	}
	if (a.CurrentLawReplayMismatches > 0) != (a.Classification == f34Confirmed) ||
		(a.CurrentLawReplayMismatches == 0) != (a.Classification == f34NotObserved) {
		t.Fatal("classification does not follow preregistration")
	}
	raw, _ := json.Marshal(a)
	var copy f34Report
	if json.Unmarshal(raw, &copy) != nil || !reflect.DeepEqual(copy, a) {
		t.Fatal("canonical report lost data")
	}
	if a.FirstWitness != nil {
		t.Logf("F34_WITNESS seed=%d boundary=%d issue=%d cue=%d due=%d tick=%d old=%s new=%s physical=%d replay=%d",
			a.FirstWitness.Seed, a.FirstWitness.Boundary, a.FirstWitness.IssueTime,
			a.FirstWitness.Cue, a.FirstWitness.OriginalDue, a.FirstWitness.Tick,
			a.FirstWitness.IssuingLaw, a.FirstWitness.CurrentLaw,
			a.FirstWitness.PhysicalMask, a.FirstWitness.ReplayedMask)
	}
	t.Logf("F34_RESULT=%s scenarios=%d ticks=%d heldovers=%d mismatches=%d checksum=%s",
		a.Classification, a.Scenarios, a.TickComparisons, a.HeldoverEvents,
		a.CurrentLawReplayMismatches, a.ScenariosSHA256)
	t.Logf("F34_JSON=%s", raw)
}
func TestF34NoFirstUseOrUnscopedAudit(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 331, 337, 347, 349, 353, 359, 366, 368, 372, 374, 378, 380, 382, 384} {
		if _, e := f33NewWorld(seed); e == nil {
			t.Fatal("forbidden development world", seed)
		}
	}
	for _, tt := range []int{-1, 96, 97} {
		if _, e := f33Phase(367, tt); e == nil {
			t.Fatal("invalid time accepted", tt)
		}
	}
	for _, cue := range []int{-1, 4, 99} {
		if _, e := f32Law('A', cue); e == nil {
			t.Fatal("invalid cue accepted", cue)
		}
	}
	// The exact F33 learned-world result is untouched; no experiment selector is updated.
	r, e := F33Development()
	if e != nil || F33Validate(r) != nil || r.Classification != F33NoGo || r.Passing != 1 || r.ScientificAccepted || r.FirstUseConsumed {
		t.Fatal(fmt.Sprintf("previous scientific negatives modified: %v", e))
	}
}
