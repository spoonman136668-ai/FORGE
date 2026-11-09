package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF16ProspectiveOnlineRecoveryAgainstSixStrongControls(t *testing.T) {
	report, err := F16Development()
	if err != nil {
		t.Fatal(err)
	}
	second, err := F16Development()
	if err != nil || !reflect.DeepEqual(report, second) {
		t.Fatal("non-deterministic F16 DEV evidence", err)
	}
	if F16Validate(report) != nil {
		t.Fatal("source-bound F16 report not verified")
	}
	previous, err := F15Development()
	if err != nil || F15Validate(previous) != nil || previous.Classification != F15NoGo ||
		report.ParentF15DigestSHA256 != previous.DigestSHA256 || !report.EarlierNegativesPreserved {
		t.Fatal("frozen F15/F13 negative not preserved")
	}
	if report.Schema != F16Schema || report.MiddleStep != 18 || report.ReturnStep != 47 ||
		report.ActionsPerArm != 60 || report.Delay != 2 || report.ReturnPredictionCount != 11 ||
		report.Seeds != [2]uint32{17, 31} || report.Policies != [2]string{"fixed", "random"} ||
		report.MinimumStrongGain != 2 || report.MinimumLatencyGain != 2 || report.MinimumAblationGain != 2 ||
		len(report.Arms) != 4 || report.TotalRuleWork <= 0 || !report.DevelopmentOnly ||
		report.IndependentFirstUseConsumed || report.ScientificAccepted ||
		report.WholeProcessCostMeasured || report.OwnerEligible || report.DispatchAuthorized ||
		report.ActiveResearchChanged || report.AgentCalls != 0 || report.PaidAPICalls != 0 {
		t.Fatal("F16 preregistration/authority fence altered")
	}
	passing, cost := 0, 0
	for i, arm := range report.Arms {
		if arm.Seed != report.Seeds[i/2] || arm.Policy != report.Policies[i%2] ||
			arm.G1Credited != 52 || arm.G2Credited != 58 || arm.G1Pending != 2 || arm.G2Pending != 2 ||
			!arm.ColdContinuationMatches || len(arm.G1SnapshotSHA256) != 64 || len(arm.G2SnapshotSHA256) != 64 {
			t.Fatal("F16 missing arm, delay credit or cold continuation")
		}
		trace, err := f16Generate(arm.Seed, arm.Policy)
		if err != nil || arm.TraceSHA256 != f8Digest("FORGE-EUREKA-F16-PREQUENTIAL-OBSERVATIONS-V1\n", trace) {
			t.Fatal("F16 source trace changed")
		}
		cut := f13New()
		for _, e := range trace[:54] {
			if cut.Observe(e) != nil {
				t.Fatal("bad G1 credit")
			}
		}
		state, err := cut.Snapshot()
		if err != nil || arm.G1SnapshotSHA256 != f3Hash(state) {
			t.Fatal("G1 source mismatch")
		}
		saved, err := f13Load(state, arm.G1SnapshotSHA256)
		if err != nil {
			t.Fatal(err)
		}
		for _, e := range trace[54:] {
			if saved.Observe(e) != nil {
				t.Fatal("bad cold G2 credit")
			}
		}
		final, err := saved.Snapshot()
		if err != nil || arm.G2SnapshotSHA256 != f3Hash(final) {
			t.Fatal("G2 cold source mismatch")
		}
		for wi, win := range arm.Windows {
			frozen := f16Windows()[wi]
			if win.Name != frozen.Name || win.FirstAction != frozen.FirstAction ||
				win.LastAction != frozen.LastAction || win.Trials != frozen.Trials {
				t.Fatal("experiment window moved")
			}
			for k, kind := range f15Kinds() {
				m := f13New()
				for _, e := range trace[:win.FirstAction] {
					if m.Observe(e) != nil {
						t.Fatal("source fail")
					}
				}
				hits, work, bits := 0, 0, ""
				for step := win.FirstAction; step <= win.LastAction; step++ {
					if m.Observe(trace[step]) != nil {
						t.Fatal("causal source failed")
					}
					before, err := m.Snapshot()
					if err != nil {
						t.Fatal(err)
					}
					got, units, err := f16Forecast(kind, m, trace[step-1], trace[step])
					if err != nil || units < 1 {
						t.Fatal("online forecast failed")
					}
					// Entire future is available *only here*, never in f16Forecast's API.
					target := trace[step+2].DelayedState
					if got == target {
						hits++
						bits += "1"
					} else {
						bits += "0"
					}
					after, err := m.Snapshot()
					if err != nil || !bytes.Equal(before, after) {
						t.Fatal("future label changed model state")
					}
					work += units
				}
				if hits != win.Correct[k] || work != win.RuleWork[k] || bits != win.CorrectTrace[k] || len(bits) != win.Trials {
					t.Fatalf("online source drift window=%s kind=%s", win.Name, kind)
				}
				cost += win.RuleWork[k]
			}
		}
		original, mid, ret := arm.Windows[0], arm.Windows[1], arm.Windows[2]
		origBest, _, _ := f16Strongest(original)
		midBest, _, _ := f16Strongest(mid)
		strongest, name, fastest := f16Strongest(ret)
		offset := f16RecoveryOffset(ret.CorrectTrace[0])
		retained := original.Correct[0] >= origBest-1 && mid.Correct[0] >= midBest-1
		pass := retained && arm.ColdContinuationMatches && ret.Correct[0]-strongest >= 2 &&
			fastest-offset >= 2 && ret.Correct[0]-ret.Correct[7] >= 2 && ret.Correct[0]-ret.Correct[8] >= 2
		if arm.StrongestReturnScore != strongest || arm.StrongestReturnName != name ||
			arm.FastestControlRecoveryOffset != fastest || arm.CandidateRecoveryOffset != offset ||
			arm.AdvantageOverStrongest != ret.Correct[0]-strongest ||
			arm.RecoveryOffsetAdvantage != fastest-offset ||
			arm.AdvantageOverNoBank != ret.Correct[0]-ret.Correct[7] ||
			arm.AdvantageOverWrongCredit != ret.Correct[0]-ret.Correct[8] ||
			arm.OriginalAndMiddleRetained != retained || arm.PassesThreshold != pass {
			t.Fatal("F16 stronger-than-control/threshold data omitted")
		}
		if pass {
			passing++
		}
		t.Logf("F16_DEV seed=%d policy=%s return_correct=%v return_trace=%v "+
			"strongest=%s/%d gain=%+d/11 recovery=%d fastest_control=%d "+
			"retained=%t passing=%t", arm.Seed, arm.Policy, ret.Correct, ret.CorrectTrace,
			name, strongest, arm.AdvantageOverStrongest, offset, fastest, retained, pass)
	}
	if cost != report.TotalRuleWork || passing != report.PassingArms {
		t.Fatal("work or losing arms were dropped")
	}
	expected := F16NO_GO
	if passing == 4 {
		expected = F16Signal
	}
	if report.Classification != expected {
		t.Fatal("negative F16 relabeled after outcomes")
	}
	t.Logf("F16_FROZEN_DEV=%s passing=%d/4 science_unverified=true owner_eligible=false work=%d",
		report.Classification, passing, cost)
}
func TestF16OnlyCreditedConsequencesAndHiddenRecurrentWorld(t *testing.T) {
	for _, seed := range f13Seeds() {
		a, b, err := f13Rules(seed)
		if err != nil || a == b {
			t.Fatal("world laws not distinct")
		}
		for _, policy := range f13Policies() {
			events, err := f16Generate(seed, policy)
			if err != nil || len(events) != 60 {
				t.Fatal("bad generation")
			}
			state := int(f12Mix(seed^0x125ecafe) & 3)
			initial := state
			var after [60]int
			m := f13New()
			for i, event := range events {
				expected := -1
				if i == 1 {
					expected = initial
				}
				if i >= 2 {
					expected = after[i-2]
				}
				action, err := f13Action(seed, policy, i)
				if err != nil || event.Phase != 0 || event.Step != i || event.Action != action ||
					event.Cue != f12Cue(seed, i, 0) || event.Sensor != state&1 || event.DelayedState != expected {
					t.Fatal("future outcome/switch leaked or data changed")
				}
				rule := a
				if i >= 18 && i < 47 {
					rule = b
				}
				state = f12Next(rule, state, 0, event.Cue, event.Action)
				after[i] = state
				if m.Observe(event) != nil || len(m.Credits) != max(0, i+1-2) {
					t.Fatal("unobserved action consequence credited")
				}
			}
			if m.Seen != 60 || len(m.Credits) != 58 || m.Pending[0].Step != 58 || m.Pending[1].Step != 59 {
				t.Fatal("pending two causal IDs not retained")
			}
		}
	}
	for _, seed := range []uint32{0, 18, 59, 83} {
		if _, err := f16Generate(seed, "fixed"); err == nil {
			t.Fatal("unapproved/first-use world accessed")
		}
	}
	for _, policy := range []string{"oracle", "", "disagreement"} {
		if _, err := f16Generate(17, policy); err == nil {
			t.Fatal("unapproved action policy")
		}
	}
}
func TestF16FrozenDevelopmentNotScientificOrOwnerAuthority(t *testing.T) {
	base, err := F16Development()
	if err != nil {
		t.Fatal(err)
	}
	clone := func() F16Report {
		b, _ := json.Marshal(base)
		var out F16Report
		if err := json.Unmarshal(b, &out); err != nil {
			t.Fatal(err)
		}
		return out
	}
	negatives := []struct {
		name   string
		change func(*F16Report)
	}{
		{"missing older no-go", func(x *F16Report) { x.EarlierNegativesPreserved = false }},
		{"parent", func(x *F16Report) { x.ParentF15DigestSHA256 = "forged" }},
		{"world", func(x *F16Report) { x.MiddleStep = 33 }},
		{"holdout seed", func(x *F16Report) { x.Seeds[0] = 59 }},
		{"threshold", func(x *F16Report) { x.MinimumStrongGain = 0 }},
		{"future", func(x *F16Report) { x.Arms[0].Windows[2].Correct[0] = 11 }},
		{"negative control", func(x *F16Report) { x.Arms[0].Windows[2].RuleWork[8] = 0 }},
		{"omitted loss", func(x *F16Report) { x.Arms = x.Arms[:3] }},
		{"reordered arms", func(x *F16Report) { x.Arms[0], x.Arms[1] = x.Arms[1], x.Arms[0] }},
		{"credited", func(x *F16Report) { x.Arms[0].G1Credited = 54 }},
		{"tamper", func(x *F16Report) { x.Arms[0].G1SnapshotSHA256 = "tampered" }},
		{"false first use", func(x *F16Report) { x.IndependentFirstUseConsumed = true }},
		{"science", func(x *F16Report) { x.ScientificAccepted = true }},
		{"owner", func(x *F16Report) { x.OwnerEligible = true }},
		{"dispatch", func(x *F16Report) { x.DispatchAuthorized = true }},
		{"live", func(x *F16Report) { x.ActiveResearchChanged = true }},
		{"paid", func(x *F16Report) { x.PaidAPICalls = 1 }},
	}
	for _, tc := range negatives {
		t.Run(tc.name, func(t *testing.T) {
			bad := clone()
			tc.change(&bad)
			bad.DigestSHA256 = f16Digest(bad)
			if F16Validate(bad) == nil {
				t.Fatal("forged authority or source accepted")
			}
		})
	}
}