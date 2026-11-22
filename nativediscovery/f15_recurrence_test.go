package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF15RecurrentMechanismAgainstStrongSwitchingControl(t *testing.T) {
	report, err := F15Development()
	if err != nil {
		t.Fatal(err)
	}
	if F15Validate(report) != nil {
		t.Fatal("F15 source-bound review rejected")
	}
	prior, err := F13Development()
	if err != nil || F13Validate(prior) != nil || prior.Classification != F13NO_GO ||
		report.ParentF13DigestSHA256 != prior.DigestSHA256 || !report.F13NegativePreserved {
		t.Fatal("F13 negative evidence lost")
	}
	if report.Schema != F15Schema || len(report.Arms) != 4 ||
		report.Seeds != [2]uint32{17, 31} ||
		report.Policies != [2]string{"fixed", "random"} ||
		report.FirstSwitchStep != 33 || report.ReturnStep != 49 ||
		report.ActionsPerArm != 60 || report.DelaySteps != 2 ||
		report.MinimumStrongGain != 4 || report.MinimumAblationGain != 8 ||
		report.TotalRuleWorkChecks <= 0 || report.IndependentFirstUseConsumed ||
		report.ScientificAccepted || report.OwnerEligible || report.DispatchAuthorized ||
		report.FullProcessEfficiencyProven || report.ActiveResearchChanged ||
		report.AgentCalls != 0 || report.PaidAPICalls != 0 || !report.DevelopmentOnly {
		t.Fatal("F15 experiment budgets, science or authority changed")
	}
	passed := 0
	for i, arm := range report.Arms {
		if arm.Seed != report.Seeds[i/2] || arm.Policy != report.Policies[i%2] {
			t.Fatal("duplicate or missing development arm")
		}
		events, err := f15Generate(arm.Seed, arm.Policy)
		if err != nil || arm.TraceSHA256 != f8Digest("FORGE-EUREKA-F15-OBSERVATIONS-V1\n", events) {
			t.Fatal("changed training source")
		}
		for gen, round := range arm.Rounds {
			cut := 54 + gen*6
			if round.Generation != gen+1 || round.ActionsSeen != cut ||
				round.CreditedConsequences != cut-2 || round.PendingConsequences != 2 ||
				!round.ColdStateMatches || len(round.SnapshotSHA256) != 64 ||
				round.RuleWorkChecks <= 0 || round.StrongestName == "" {
				t.Fatal("unresolved credit, checkpoint or strong control omitted")
			}
			trained := f13New()
			for _, e := range events[:cut] {
				if trained.Observe(e) != nil {
					t.Fatal("failed to credit delayed outcome")
				}
			}
			raw, err := trained.Snapshot()
			if err != nil || f3Hash(raw) != round.SnapshotSHA256 {
				t.Fatal("cold source mismatch")
			}
			sourceBefore := append([]byte(nil), raw...)
			strongest := 0
			for k, kind := range f15Kinds() {
				got, _, err := f15Score(kind, trained, arm.Seed, false)
				if err != nil || got != round.ReturnCorrect[k] {
					t.Fatalf("returned-world score mismatch %s", kind)
				}
				got, _, err = f15Score(kind, trained, arm.Seed, true)
				if err != nil || got != round.MiddleCorrect[k] {
					t.Fatalf("middle-world score mismatch %s", kind)
				}
				if k >= 1 && k <= 6 && round.ReturnCorrect[k] > strongest {
					strongest = round.ReturnCorrect[k]
				}
				if round.ReturnCorrect[k] < 0 || round.ReturnCorrect[k] > 64 ||
					round.MiddleCorrect[k] < 0 || round.MiddleCorrect[k] > 64 {
					t.Fatal("score out of bounds")
				}
			}
			if strongest != round.StrongestCorrect ||
				round.AdvantageOverStrongest != round.ReturnCorrect[0]-strongest ||
				round.AdvantageOverNoBank != round.ReturnCorrect[0]-round.ReturnCorrect[7] ||
				round.AdvantageOverWrongCredit != round.ReturnCorrect[0]-round.ReturnCorrect[8] {
				t.Fatal("strongest fully trained control or negative controls ignored")
			}
			sourceAfter, err := trained.Snapshot()
			if err != nil || !bytes.Equal(sourceBefore, sourceAfter) {
				t.Fatal("evaluation leaked labels into training")
			}
		}
		final := arm.Rounds[1]
		expected := final.ReturnCorrect[0] >= arm.Rounds[0].ReturnCorrect[0]
		meets := expected && final.AdvantageOverStrongest >= 4 &&
			final.AdvantageOverNoBank >= 8 && final.AdvantageOverWrongCredit >= 8
		if arm.ReturningLawRetained != expected || arm.PassesFrozenThreshold != meets {
			t.Fatal("post-result threshold or retention changed")
		}
		if meets {
			passed++
		}
		t.Logf("F15_DEV seed=%d policy=%s original_G1=%v original_G2=%v "+
			"middle_G2=%v strongest=%s/%d adv_strong=%+d adv_no_bank=%+d "+
			"adv_wrong=%+d passing=%t", arm.Seed, arm.Policy,
			arm.Rounds[0].ReturnCorrect, final.ReturnCorrect, final.MiddleCorrect,
			final.StrongestName, final.StrongestCorrect, final.AdvantageOverStrongest,
			final.AdvantageOverNoBank, final.AdvantageOverWrongCredit, meets)
	}
	want := F15NoGo
	if passed == 4 {
		want = F15Signal
	}
	if passed != report.PassingArms || report.Classification != want {
		t.Fatal("negative/tied results relabeled as science")
	}
	t.Logf("F15_FROZEN_DEV=%s passing=%d/4 owner_eligible=false", want, passed)
}

func TestF15HiddenRecurrentLawAndPendingConsequence(t *testing.T) {
	for _, seed := range f13Seeds() {
		a, b, err := f13Rules(seed)
		if err != nil || a == b {
			t.Fatal("invalid distinct causal laws")
		}
		for _, policy := range f13Policies() {
			events, err := f15Generate(seed, policy)
			if err != nil || len(events) != 60 {
				t.Fatal("invalid action schedule")
			}
			state := int(f12Mix(seed^0x125ecafe) & 3)
			initial := state
			var history [F15Actions]int
			m := f13New()
			for step, e := range events {
				expected := -1
				if step == 1 {
					expected = initial
				}
				if step >= 2 {
					expected = history[step-2]
				}
				action, _ := f13Action(seed, policy, step)
				if e.Step != step || e.Phase != 0 || e.DelayedState != expected ||
					e.Sensor != state&1 || e.Action != action || e.Cue != f12Cue(seed, step, 0) {
					t.Fatal("world leaked hidden switch or early consequence")
				}
				rule := a
				if step >= 33 && step < 49 {
					rule = b
				}
				state = f12Next(rule, state, 0, e.Cue, e.Action)
				history[step] = state
				if m.Observe(e) != nil || len(m.Credits) != max(0, step+1-2) {
					t.Fatal("wrong action credited before its delayed consequence")
				}
			}
			if m.Pending[0].Step != 58 || m.Pending[1].Step != 59 {
				t.Fatal("pending causal IDs lost")
			}
			g1 := f13New()
			for _, e := range events[:54] {
				if g1.Observe(e) != nil {
					t.Fatal("G1 training failed")
				}
			}
			original, err := g1.Snapshot()
			if err != nil {
				t.Fatal(err)
			}
			cold, err := f13Load(original, f3Hash(original))
			if err != nil {
				t.Fatal(err)
			}
			for _, e := range events[54:] {
				if cold.Observe(e) != nil {
					t.Fatal("cold continuation failed")
				}
			}
			got, err := cold.Snapshot()
			if err != nil {
				t.Fatal(err)
			}
			want, err := m.Snapshot()
			if err != nil || !bytes.Equal(got, want) {
				t.Fatal("cold G1->G2 differs from full replay")
			}
			if cold.Observe(events[0]) == nil {
				t.Fatal("old action replay accepted")
			}
			if _, err := f13Load(original, ""); err == nil {
				t.Fatal("external digest missing")
			}
			broken := append([]byte(nil), original...)
			broken[20] ^= 1
			if _, err := f13Load(broken, f3Hash(original)); err == nil {
				t.Fatal("tampered snapshot accepted")
			}
		}
	}
	for _, seed := range []uint32{59, 83, 0} {
		if _, err := f15Generate(seed, "fixed"); err == nil {
			t.Fatal("independent first-use seed consumed")
		}
	}
}

func TestF15CanonicalEvidenceCannotPromoteScience(t *testing.T) {
	base, err := F15Development()
	if err != nil {
		t.Fatal(err)
	}
	makeCopy := func() F15Report {
		raw, _ := json.Marshal(base)
		var out F15Report
		if json.Unmarshal(raw, &out) != nil {
			t.Fatal("roundtrip failed")
		}
		return out
	}
	cases := []struct {
		name   string
		change func(*F15Report)
	}{
		{"parent", func(v *F15Report) { v.ParentF13DigestSHA256 = "stale" }},
		{"negative", func(v *F15Report) { v.F13NegativePreserved = false }},
		{"seed", func(v *F15Report) { v.Seeds[0] = 59 }},
		{"score", func(v *F15Report) { v.Arms[0].Rounds[1].ReturnCorrect[0] = -1 }},
		{"loser", func(v *F15Report) { v.Arms = v.Arms[:3] }},
		{"threshold", func(v *F15Report) { v.MinimumStrongGain = 0 }},
		{"pending", func(v *F15Report) { v.Arms[0].Rounds[1].PendingConsequences = 0 }},
		{"false acceptance", func(v *F15Report) { v.ScientificAccepted = true }},
		{"first use", func(v *F15Report) { v.IndependentFirstUseConsumed = true }},
		{"owner", func(v *F15Report) { v.OwnerEligible = true }},
		{"dispatch", func(v *F15Report) { v.DispatchAuthorized = true }},
		{"live", func(v *F15Report) { v.ActiveResearchChanged = true }},
		{"paid", func(v *F15Report) { v.PaidAPICalls = 1 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := makeCopy()
			tc.change(&bad)
			bad.DigestSHA256 = f15Digest(bad)
			if reflect.DeepEqual(bad, base) || F15Validate(bad) == nil {
				t.Fatal("forged evidence accepted")
			}
		})
	}
}