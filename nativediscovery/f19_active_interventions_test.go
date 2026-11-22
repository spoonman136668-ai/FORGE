package nativediscovery

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestF19FrozenActiveInterventionsAgainstStrongPlanners(t *testing.T) {
	report, err := F19Development()
	if err != nil {
		t.Fatal(err)
	}
	second, err := F19Development()
	if err != nil || !reflect.DeepEqual(report, second) {
		t.Fatal("nondeterministic experimental results", err)
	}
	if F19Validate(report) != nil {
		t.Fatal("source-bound report invalid")
	}
	prev, err := F18Development()
	if err != nil || F18Validate(prev) != nil || prev.Classification != F18NO_GO ||
		report.ParentF18DigestSHA256 != prev.DigestSHA256 || !report.EarlierNegativesPreserved {
		t.Fatal("F18 and earlier NO_GO evidence not preserved")
	}
	if report.Schema != F19Schema || report.Seeds != [2]uint32{107, 109} ||
		report.Schedules != [2]string{"confounded", "varied"} || report.TotalActions != 18 ||
		report.FeedbackDelay != 2 || report.Milestones != [4]int{4, 6, 8, 12} ||
		report.MaximumScore != 128 || report.MinimumStrongGain != 4 || report.MinimumAblationGain != 8 ||
		!report.DevelopmentOnly || report.IndependentFirstUseConsumed || report.ScientificAccepted ||
		report.WholeProcessCostMeasured || report.OwnerEligible || report.DispatchAuthorized ||
		report.ActiveResearchChanged || report.AgentCalls != 0 || report.PaidAPICalls != 0 || len(report.Arms) != 4 {
		t.Fatal("F19 frozen source, hypothesis or authority modified")
	}
	passed, totalWork := 0, 0
	for armIndex, arm := range report.Arms {
		if arm.Seed != report.Seeds[armIndex/2] || arm.Schedule != report.Schedules[armIndex%2] {
			t.Fatal("expected development arm omitted")
		}
		best, bestName := -1, ""
		for i, kind := range f19Kinds() {
			original := arm.Policies[i]
			fresh, e := f19PolicyRun(arm.Seed, arm.Schedule, kind)
			if e != nil || !reflect.DeepEqual(fresh, original) || original.Name != kind ||
				!original.ColdMatches || original.G1Credited != 8 || original.G1Pending != 2 ||
				original.G2Credited != 16 || original.G2Pending != 2 ||
				len(original.G1StateSHA256) != 64 || len(original.G2StateSHA256) != 64 ||
				len(original.ObservationSHA256) != 64 || original.RuleWork < 1 ||
				len(original.ActionBits) != 18 {
				t.Fatalf("policy %s mismatched exact delayed-source and cold replay: %v", kind, e)
			}
			sum := 0
			for _, count := range original.Correct {
				if count < 0 || count > 32 {
					t.Fatal("invalid oracle-isolated causal score")
				}
				sum += count
			}
			if sum != original.TotalCorrect || sum > 128 {
				t.Fatal("inconsistent multi-window causal score")
			}
			for step, ch := range original.ActionBits {
				if ch != '0' && ch != '1' {
					t.Fatal("invalid intervention trace")
				}
				if kind == "no-intervention" && ch != '0' {
					t.Fatal("no-intervention ablation intervened")
				}
				if kind == "passive" {
					cue, e := f19Cue(arm.Seed, arm.Schedule, step)
					if e != nil || int(ch-'0') != cue&1 {
						t.Fatal("passive comparator used a counterfactual action")
					}
				}
			}
			if i >= 1 && i <= 6 && original.TotalCorrect > best {
				best, bestName = original.TotalCorrect, kind
			}
			totalWork += original.RuleWork
		}
		changed := 0
		for step, ch := range arm.Policies[0].ActionBits {
			cue, e := f19Cue(arm.Seed, arm.Schedule, step)
			if e != nil {
				t.Fatal(e)
			}
			if int(ch-'0') != cue&1 {
				changed++
			}
		}
		gain := arm.Policies[0].TotalCorrect - best
		gainNo := arm.Policies[0].TotalCorrect - arm.Policies[7].TotalCorrect
		gainWrong := arm.Policies[0].TotalCorrect - arm.Policies[8].TotalCorrect
		pass := gain >= 4 && gainNo >= 8 && gainWrong >= 8 && changed >= 2
		if arm.StrongestControlCorrect != best || arm.StrongestControlName != bestName ||
			arm.CandidateNonPassiveActions != changed || arm.GainOverStrongest != gain ||
			arm.GainOverNoIntervention != gainNo || arm.GainOverWrongCredit != gainWrong ||
			arm.PassesThreshold != pass {
			t.Fatal("strongest of six conventional planners or frozen thresholds changed")
		}
		if pass {
			passed++
		}
		t.Logf("F19_DEV seed=%d schedule=%s totals=%v candidate=%d strongest=%s/%d gain=%+d no-intervention=%+d wrong-credit=%+d nonpassive=%d pass=%v",
			arm.Seed, arm.Schedule, func() [9]int {
				var x [9]int
				for i, p := range arm.Policies {
					x[i] = p.TotalCorrect
				}
				return x
			}(),
			arm.Policies[0].TotalCorrect, bestName, best, gain, gainNo, gainWrong, changed, pass)
	}
	want := F19NO_GO
	if passed == 4 {
		want = F19Signal
	}
	if report.Classification != want || report.PassingArms != passed || report.TotalRuleWork != totalWork {
		t.Fatal("earlier experiment losses or operation-cost evidence altered")
	}
	t.Logf("F19_FROZEN_DEV=%s passing=%d/4 total_rule_work=%d scientific_pass=false owner_eligible=false", want, passed, totalWork)
}

func TestF19ActualInterventionsNeverReceiveOracleSeedOrFutureFeedback(t *testing.T) {
	for _, seed := range []uint32{0, 17, 31, 59, 71, 83, 97, 101, 103, 108, 111, 127} {
		if _, e := f19WorldRule(seed); e == nil {
			t.Fatal("unknown or first-use world admitted")
		}
		if _, e := f19Cue(seed, "varied", 0); e == nil {
			t.Fatal("future world escaped seed gate")
		}
	}
	for _, schedule := range []string{"oracle", "", "future", "fixed"} {
		if _, e := f19Cue(107, schedule, 1); e == nil {
			t.Fatal("unapproved cue schedule admitted")
		}
	}
	for _, step := range []int{-1, 19, 20} {
		if _, e := f19Cue(107, "confounded", step); e == nil {
			t.Fatal("out-of-budget cue leaked")
		}
	}
	if len(f18Masks()) != 8 {
		t.Fatal("hypothesis class drift")
	}
	for _, kind := range f19Kinds() {
		if _, _, e := f19Select(kind, nil, nil, 0, 1, 2); e == nil {
			t.Fatalf("uncredited future labels were accepted: %s", kind)
		}
		if _, _, e := f19Select(kind, nil, nil, 0, 1, 0); e != nil {
			t.Fatalf("source-free first action rejected: %s %v", kind, e)
		}
	}
	if _, _, e := f19Select("oracle", nil, nil, 0, 1, 0); e == nil {
		t.Fatal("world oracle accepted as policy")
	}
	if _, _, e := f19Select("queue-lookahead", nil, nil, 0, 1, 17); e == nil {
		t.Fatal("forged 17-action history accepted")
	}
	if _, _, e := f19Select("pending-aware", nil, nil, 0, 1, 18); e == nil {
		t.Fatal("extra 19th action accepted")
	}
	if _, _, e := f19Select("pending-aware", nil, nil, 4, 1, 0); e == nil {
		t.Fatal("out-of-range cue accepted")
	}
	bad := f13Credit{Step: 0, Before: 0, After: 0, Cue: 0, Action: 4}
	if _, _, e := f19Select("pending-aware", []f13Credit{bad}, []f19Probe{{0, 0}, {0, 0}}, 0, 1, 3); e == nil {
		t.Fatal("invalid causal credit admitted")
	}
}

func TestF19RehashedForgeryCannotGrantScienceOrChangeResult(t *testing.T) {
	expected, err := F19Development()
	if err != nil {
		t.Fatal(err)
	}
	clone := func() F19Report {
		raw, e := json.Marshal(expected)
		if e != nil {
			t.Fatal(e)
		}
		var copy F19Report
		if json.Unmarshal(raw, &copy) != nil {
			t.Fatal("unable to clone evidence")
		}
		return copy
	}
	cases := []struct {
		name   string
		mutate func(*F19Report)
	}{
		{"parent-loss", func(x *F19Report) { x.ParentF18DigestSHA256 = "fake" }},
		{"forgot-prior-negatives", func(x *F19Report) { x.EarlierNegativesPreserved = false }},
		{"first-use-seed", func(x *F19Report) { x.Seeds[0] = 59 }},
		{"altered-cue", func(x *F19Report) { x.Schedules[0] = "oracle" }},
		{"altered-cut", func(x *F19Report) { x.Milestones[0] = 1 }},
		{"altered-threshold", func(x *F19Report) { x.MinimumStrongGain = 0 }},
		{"elided-losing-arm", func(x *F19Report) { x.Arms = x.Arms[:3] }},
		{"forged-positive", func(x *F19Report) { x.Classification = F19Signal }},
		{"forged-baseline", func(x *F19Report) { x.Arms[0].StrongestControlCorrect = 0 }},
		{"forged-first-use", func(x *F19Report) { x.IndependentFirstUseConsumed = true }},
		{"forged-accepted", func(x *F19Report) { x.ScientificAccepted = true }},
		{"forged-owner", func(x *F19Report) { x.OwnerEligible = true }},
		{"forged-dispatch", func(x *F19Report) { x.DispatchAuthorized = true }},
		{"forged-live", func(x *F19Report) { x.ActiveResearchChanged = true }},
		{"forged-paid-api", func(x *F19Report) { x.PaidAPICalls = 1 }},
		{"forged-cost", func(x *F19Report) { x.WholeProcessCostMeasured = true }},
		{"forged-snapshot", func(x *F19Report) { x.Arms[0].Policies[0].G1StateSHA256 = "fake" }},
		{"forged-intervention", func(x *F19Report) { x.Arms[0].Policies[0].ActionBits = "000000000000000000" }},
		{"forged-score", func(x *F19Report) { x.Arms[0].Policies[0].Correct[0] = -1 }},
		{"forged-work", func(x *F19Report) { x.TotalRuleWork = 0 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			x := clone()
			tc.mutate(&x)
			x.DigestSHA256 = f19Digest(x)
			if F19Validate(x) == nil {
				t.Fatal("rehashed forged report accepted")
			}
		})
	}
}
