package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF18PredeclaredCompositionVersusStrongEqualInformation(t *testing.T) {
	report, err := F18Development()
	if err != nil {
		t.Fatal(err)
	}
	if err := F18Validate(report); err != nil {
		t.Fatal("source-bound development report denied", err)
	}
	prior, err := F17Development()
	if err != nil || F17Validate(prior) != nil || prior.Classification != F17NO_GO ||
		report.ParentF17DigestSHA256 != prior.DigestSHA256 || !report.EarlierNegativesPreserved {
		t.Fatal("original F17 and earlier negatives not retained")
	}
	if report.Schema != F18Schema || report.Seeds != [2]uint32{101, 103} ||
		report.Policies != [2]string{"fixed", "random"} ||
		report.SourceContexts != [3]int{0, 1, 2} || report.TargetContext != 3 ||
		report.SourceActions != 18 || report.TargetActions != 12 || report.ScoredPredictions != 8 ||
		report.MinimumStrongGain != 2 || report.MinimumAblationGain != 2 ||
		len(report.Arms) != 4 || report.TotalRuleWork <= 0 || !report.DevelopmentOnly ||
		report.IndependentFirstUseConsumed || report.ScientificAccepted ||
		report.WholeProcessCostMeasured || report.OwnerEligible || report.DispatchAuthorized ||
		report.LiveResearchChanged || report.AgentCalls != 0 || report.PaidAPICalls != 0 {
		t.Fatal("F18 preregistration, source or authority drift")
	}
	passed, totalWork := 0, 0
	for i, arm := range report.Arms {
		if arm.Seed != report.Seeds[i/2] || arm.Policy != report.Policies[i%2] || !arm.ColdMatches ||
			arm.SourceCredited != [3]int{16, 16, 16} || arm.SourcePending != [3]int{2, 2, 2} ||
			arm.TargetCredited != 10 || arm.TargetPending != 2 {
			t.Fatal("missing independent DEV arm or delayed credit/cold source")
		}
		var sources [3][]f13Credit
		for context := 0; context < 3; context++ {
			events, e := f18Generate(arm.Seed, arm.Policy, context)
			if e != nil || len(events) != 18 || arm.SourceTraceSHA256[context] != f8Digest(
				"FORGE-EUREKA-F18-SOURCE-OBSERVATIONS-V1\n", events) {
				t.Fatal("source provenance differs")
			}
			m := f13New()
			for _, v := range events {
				if m.Observe(v) != nil {
					t.Fatal("source credit failed")
				}
			}
			raw, e := m.Snapshot()
			if e != nil || f3Hash(raw) != arm.SourceStateSHA256[context] {
				t.Fatal("source checkpoint changed")
			}
			cold, e := f13Load(raw, arm.SourceStateSHA256[context])
			if e != nil || !reflect.DeepEqual(cold, m) {
				t.Fatal("cold learned source did not survive")
			}
			sources[context] = append([]f13Credit(nil), cold.Credits...)
			_, hits := f13Best(sources[context], false, false)
			if hits != arm.SourceCorrect[context] {
				t.Fatal("source fit relabeled")
			}
		}
		stream, e := f18Generate(arm.Seed, arm.Policy, 3)
		if e != nil || len(stream) != 12 || arm.TargetTraceSHA256 != f8Digest(
			"FORGE-EUREKA-F18-TARGET-OBSERVATIONS-V1\n", stream) {
			t.Fatal("target source drift")
		}
		m := f13New()
		var scores [9]int
		var works [9]int
		var bits [9]string
		for step, event := range stream {
			if m.Observe(event) != nil {
				t.Fatal("target delayed ingest failed")
			}
			if step < 2 || step > 9 {
				continue
			}
			before, e := m.Snapshot()
			if e != nil {
				t.Fatal(e)
			}
			for k, kind := range f18Kinds() {
				guess, work, e := f18Forecast(kind, sources, m.Credits, stream[step-1], event)
				if e != nil || work <= 0 {
					t.Fatalf("bad %s forecast: %v", kind, e)
				}
				// Future target is available to the test scorer *only*.
				if guess == stream[step+2].DelayedState {
					scores[k]++
					bits[k] += "1"
				} else {
					bits[k] += "0"
				}
				works[k] += work
			}
			after, e := m.Snapshot()
			if e != nil || !bytes.Equal(before, after) {
				t.Fatal("future label mutated learned state")
			}
		}
		if scores != arm.Score || works != arm.RuleWork || bits != arm.CorrectTrace {
			t.Fatal("one or more matched controls omitted/mismatched")
		}
		raw, e := m.Snapshot()
		if e != nil || f3Hash(raw) != arm.TargetStateSHA256 {
			t.Fatal("target cold source mismatch")
		}
		cold, e := f13Load(raw, arm.TargetStateSHA256)
		if e != nil || !reflect.DeepEqual(cold, m) {
			t.Fatal("target cold checkpoint changed")
		}
		for _, v := range works {
			totalWork += v
		}
		strongest, name, fastest := -1, "", 8
		for k := 1; k <= 6; k++ {
			if scores[k] > strongest {
				strongest, name = scores[k], f18Kinds()[k]
			}
			if v := f18Recovery(bits[k]); v < fastest {
				fastest = v
			}
		}
		ret := f18Recovery(bits[0])
		pass := scores[0]-strongest >= F18MinStrongGain && scores[0]-scores[7] >= F18MinAblationGain &&
			scores[0]-scores[8] >= F18MinAblationGain && ret <= fastest && arm.ColdMatches
		for _, n := range arm.SourceCorrect {
			if n < 14 {
				pass = false
			}
		}
		if arm.StrongestScore != strongest || arm.StrongestName != name ||
			arm.FastestControlOffset != fastest || arm.RecoveryOffset != ret ||
			arm.AdvantageStrongest != scores[0]-strongest ||
			arm.AdvantageNoAction != scores[0]-scores[7] ||
			arm.AdvantageWrongCredit != scores[0]-scores[8] || arm.PassesThreshold != pass {
			t.Fatal("frozen strongest comparator/ablation/threshold changed")
		}
		if pass {
			passed++
		}
		t.Logf("F18_DEV seed=%d policy=%s score=%v trace=%v strongest=%s/%d advantage=%+d sources=%v return=%d fastest=%d passing=%v",
			arm.Seed, arm.Policy, scores, bits, name, strongest, arm.AdvantageStrongest, arm.SourceCorrect, ret, fastest, pass)
	}
	classification := F18NO_GO
	if passed == 4 {
		classification = F18Signal
	}
	if report.PassingArms != passed || report.TotalRuleWork != totalWork || report.Classification != classification {
		t.Fatal("loser excluded, total work omitted or negative relabeled")
	}
	t.Logf("F18_FROZEN_DEV=%s passing=%d/4 science_unverified=true owner_eligible=false", classification, passed)
}

func TestF18UnseenContextRuleAndDelayAreWorldOnly(t *testing.T) {
	for _, bad := range []uint32{0, 17, 31, 59, 71, 83, 97, 102} {
		if _, e := f18Generate(bad, "fixed", 0); e == nil {
			t.Fatal("unapproved or first-use seed admitted")
		}
	}
	for _, policy := range []string{"", "oracle", "independent", "disagreement"} {
		if _, e := f18Generate(101, policy, 3); e == nil {
			t.Fatal("unapproved action policy admitted")
		}
	}
	for _, context := range []int{-1, 4, 99} {
		if _, e := f18Generate(101, "fixed", context); e == nil {
			t.Fatal("unknown context admitted")
		}
	}
	for _, seed := range f18Seeds() {
		for _, policy := range f18Policies() {
			base, a, b, _ := f18World(seed)
			for context := 0; context < 4; context++ {
				law := base
				if context&1 != 0 {
					law ^= a
				}
				if context&2 != 0 {
					law ^= b
				}
				stream, e := f18Generate(seed, policy, context)
				if e != nil {
					t.Fatal(e)
				}
				state := int(f12Mix(seed^uint32(context+1)*0x7f4a7c15^0x125ecafe) & 3)
				initial := state
				past := make([]int, 0, len(stream))
				m := f13New()
				for step, event := range stream {
					expected := -1
					if step == 1 {
						expected = initial
					}
					if step >= 2 {
						expected = past[step-2]
					}
					action, e := f18Action(seed, policy, context, step)
					if e != nil || event.Step != step || event.Phase != 0 || event.Action != action ||
						event.Cue != f12Cue(seed, step, context) || event.Sensor != state&1 || event.DelayedState != expected {
						t.Fatal("future-state leak, incorrectly reported context or credit latency")
					}
					state = f12Next(law, state, 0, event.Cue, event.Action)
					past = append(past, state)
					if m.Observe(event) != nil || len(m.Credits) != max(0, step+1-2) {
						t.Fatal("credited unobserved effect")
					}
				}
				if m.Seen-len(m.Credits) != 2 || m.Pending[0].Step != len(stream)-2 || m.Pending[1].Step != len(stream)-1 {
					t.Fatal("pending consequence identities lost")
				}
			}
		}
	}
}

func TestF18ControlsAndReportCannotForgeScientificAcceptance(t *testing.T) {
	baseline, e := F18Development()
	if e != nil {
		t.Fatal(e)
	}
	clone := func() F18Report {
		raw, e := json.Marshal(baseline)
		if e != nil {
			t.Fatal(e)
		}
		var x F18Report
		if json.Unmarshal(raw, &x) != nil {
			t.Fatal("cannot copy report")
		}
		return x
	}
	cases := []struct {
		name   string
		mutate func(*F18Report)
	}{
		{"parent", func(x *F18Report) { x.ParentF17DigestSHA256 = "missing" }},
		{"source negative", func(x *F18Report) { x.EarlierNegativesPreserved = false }},
		{"seed first-use", func(x *F18Report) { x.Seeds[0] = 59 }},
		{"unseen target changed", func(x *F18Report) { x.TargetContext = 1 }},
		{"missing control", func(x *F18Report) { x.Arms[0].Score[1] = 0 }},
		{"altered threshold", func(x *F18Report) { x.MinimumStrongGain = 0 }},
		{"score", func(x *F18Report) { x.Arms[0].Score[0] = -1 }},
		{"missing loser", func(x *F18Report) { x.Arms = x.Arms[:3] }},
		{"reordered arms", func(x *F18Report) { x.Arms[0], x.Arms[1] = x.Arms[1], x.Arms[0] }},
		{"pending credit", func(x *F18Report) { x.Arms[0].TargetPending = 0 }},
		{"fake science", func(x *F18Report) { x.ScientificAccepted = true }},
		{"first use", func(x *F18Report) { x.IndependentFirstUseConsumed = true }},
		{"owner", func(x *F18Report) { x.OwnerEligible = true }},
		{"dispatch", func(x *F18Report) { x.DispatchAuthorized = true }},
		{"active", func(x *F18Report) { x.LiveResearchChanged = true }},
		{"paid", func(x *F18Report) { x.PaidAPICalls = 1 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := clone()
			tc.mutate(&bad)
			bad.DigestSHA256 = f18Digest(bad)
			if F18Validate(bad) == nil {
				t.Fatal("forged development result/authority was accepted")
			}
		})
	}
	var source [3][]f13Credit
	_, _, e = f18Forecast("oracle", source, nil, f12Event{}, f12Event{})
	if e == nil {
		t.Fatal("unauthorized fit kind admitted")
	}
}
