package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF22LongHorizonFrozenStrongControls(t *testing.T) {
	report, e := F22Development()
	if e != nil {
		t.Fatal(e)
	}
	if F22Validate(report) != nil {
		t.Fatal("exact-source F22 verification failed")
	}
	prior, e := F20Development()
	if e != nil || F20Validate(prior) != nil || prior.Classification != F20NoGo ||
		report.ParentF20SHA256 != prior.DigestSHA256 || !report.EarlierNegativesPreserved {
		t.Fatal("previous science negatives erased")
	}
	if report.Schema != F22Schema || report.Seeds != [2]uint32{131, 137} ||
		report.Policies != [2]string{"balanced", "skewed"} || report.Actions != 96 ||
		report.FeedbackDelay != 2 || report.Middle != [2]int{50, 61} || report.Return != [2]int{64, 75} ||
		report.MinimumGain != 2 || len(report.Arms) != 4 || report.TotalWork <= 0 || !report.DevelopmentOnly ||
		report.FirstUseConsumed || report.ScientificAccepted || report.WholeProcessCostProven ||
		report.OwnerEligible || report.DispatchAuthorized || report.ActiveResearchChanged ||
		report.AgentCalls != 0 || report.PaidAPICalls != 0 {
		t.Fatal("preregistered contract changed")
	}
	passing, cost := 0, 0
	for i, arm := range report.Arms {
		seed, policy := report.Seeds[i/2], report.Policies[i%2]
		a, raw, e := f22Run(seed, policy, true)
		b, original, e2 := f22Run(seed, policy, false)
		if e != nil || e2 != nil || !reflect.DeepEqual(a, b) || !bytes.Equal(raw, original) ||
			!reflect.DeepEqual(a, arm) || !arm.ColdMatches || arm.G1Credited != 62 ||
			arm.G2Credited != 94 || arm.Pending != 2 || len(arm.G1SHA256) != 64 || len(arm.G2SHA256) != 64 ||
			len(arm.TraceSHA256) != 64 {
			t.Fatal("source/cold attribution changed", e, e2)
		}
		loaded, e := f22Load(raw, arm.G2SHA256)
		if e != nil || len(loaded.Credits) != 94 || len(loaded.Pending) != 2 ||
			loaded.Pending[0].Step != 94 || loaded.Pending[1].Step != 95 {
			t.Fatal("pending effect lost")
		}
		for wi, w := range arm.Windows {
			if wi == 0 && (w.Name != "middle-B" || w.Start != 50 || w.End != 61) ||
				wi == 1 && (w.Name != "returned-A" || w.Start != 64 || w.End != 75) {
				t.Fatal("scoring window drift")
			}
			for k, kind := range f22Kinds() {
				if len(w.Trace[k]) != 12 || w.Correct[k] < 0 || w.Correct[k] > 12 || w.Work[k] < 1 {
					t.Fatalf("missing control %s score", kind)
				}
				bits := 0
				for _, ch := range w.Trace[k] {
					if ch == '1' {
						bits++
					} else if ch != '0' {
						t.Fatal("invalid trace")
					}
				}
				if bits != w.Correct[k] {
					t.Fatal("score and trace disagree")
				}
				cost += w.Work[k]
			}
		}
		middle, ret := arm.Windows[0], arm.Windows[1]
		midBest, _, _ := f22Strongest(middle)
		best, name, fastest := f22Strongest(ret)
		recover := f22Recovery(ret.Trace[0])
		success := arm.ColdMatches && arm.ArchiveReady && middle.Correct[0] >= midBest-2 &&
			ret.Correct[0]-best >= 2 && fastest-recover >= 1 &&
			ret.Correct[0]-ret.Correct[8] >= 2 && ret.Correct[0]-ret.Correct[10] >= 2 &&
			ret.Correct[0]-ret.Correct[9] >= 1
		if arm.StrongestReturnScore != best || arm.StrongestReturnName != name ||
			arm.FastestReturnOffset != fastest || arm.CandidateReturnOffset != recover ||
			arm.GainStrongest != ret.Correct[0]-best || arm.GainNoArchive != ret.Correct[0]-ret.Correct[8] ||
			arm.GainWrongCredit != ret.Correct[0]-ret.Correct[10] ||
			arm.GainAlwaysArchive != ret.Correct[0]-ret.Correct[9] ||
			arm.RetainedMiddle != (middle.Correct[0] >= midBest-2) || arm.Passes != success {
			t.Fatal("strongest baseline or frozen criteria changed")
		}
		if success {
			passing++
		}
		t.Logf("F22_DEV seed=%d policy=%s middle=%v return=%v strongest=%s/%d gain=%+d recovery=%d fastest=%d ablations=%+d/%+d/%+d retained=%v passing=%v",
			seed, policy, middle.Correct, ret.Correct, name, best, arm.GainStrongest,
			recover, fastest, arm.GainNoArchive, arm.GainWrongCredit, arm.GainAlwaysArchive, arm.RetainedMiddle, success)
	}
	class := F22NoGo
	if passing == 4 {
		class = F22Signal
	}
	if report.PassingArms != passing || report.TotalWork != cost || report.Classification != class {
		t.Fatal("losing arm or costly control erased")
	}
	t.Logf("F22_FROZEN_DEV=%s passing=%d/4 science_unverified=true rule_work=%d", class, passing, cost)
}
func TestF22DelayedWorldAndNoOracle(t *testing.T) {
	for _, bad := range []uint32{0, 17, 31, 59, 83, 101, 113, 127, 130, 136, 138} {
		if _, _, e := f22Laws(bad); e == nil {
			t.Fatal("first-use or unknown seed admitted")
		}
	}
	for _, policy := range []string{"", "oracle", "fixed", "random"} {
		if _, _, e := f22ActionCue(131, policy, 0); e == nil {
			t.Fatal("unapproved policy admitted")
		}
	}
	for _, seed := range f22Seeds() {
		for _, policy := range f22Policies() {
			a, b, _ := f22Laws(seed)
			for step := 0; step < F22Actions; step++ {
				cue, action, e := f22ActionCue(seed, policy, step)
				if e != nil || cue < 0 || cue > 3 || action < 0 || action > 1 {
					t.Fatal("invalid policy action")
				}
				law := a
				if step >= 32 && step < 64 {
					law = b
				}
				truth, e := f22Truth(seed, step, cue, action)
				if e != nil || truth != f20Truth(law, cue, action) {
					t.Fatal("hidden phase law drift")
				}
				obs, e := f22Observation(seed, step, cue, action)
				if e != nil || obs < -1 || obs > 1 {
					t.Fatal("invalid actual delayed outcome")
				}
			}
		}
	}
	if _, _, e := f22Forecast("oracle", nil, 0, 0); e == nil {
		t.Fatal("oracle predictor admitted")
	}
	if _, _, e := f22Forecast("full-bayes", nil, 4, 0); e == nil {
		t.Fatal("invalid cue admitted")
	}
	if _, _, e := f22Forecast("full-bayes", nil, 0, 2); e == nil {
		t.Fatal("invalid action admitted")
	}
	if _, _, e := f22MAP([]f20Credit{{Step: 0, Cue: 0, Action: 2}}, false); e == nil {
		t.Fatal("bad credit admitted")
	}
}
func TestF22RehashedForgeryAndAuthorityDenial(t *testing.T) {
	good, e := F22Development()
	if e != nil {
		t.Fatal(e)
	}
	clone := func() F22Report {
		b, e := json.Marshal(good)
		if e != nil {
			t.Fatal(e)
		}
		var x F22Report
		if json.Unmarshal(b, &x) != nil {
			t.Fatal("copy failed")
		}
		return x
	}
	cases := []struct {
		name   string
		mutate func(*F22Report)
	}{
		{"parent", func(x *F22Report) { x.ParentF20SHA256 = "missing" }},
		{"historical negative", func(x *F22Report) { x.EarlierNegativesPreserved = false }},
		{"first use seed", func(x *F22Report) { x.Seeds[0] = 59 }},
		{"world", func(x *F22Report) { x.Seeds[0] = 132 }},
		{"policy", func(x *F22Report) { x.Policies[0] = "oracle" }},
		{"action budget", func(x *F22Report) { x.Actions = 97 }},
		{"credit delay", func(x *F22Report) { x.FeedbackDelay = 0 }},
		{"cut", func(x *F22Report) { x.Return[0] = 63 }},
		{"gain", func(x *F22Report) { x.MinimumGain = 0 }},
		{"missing baseline", func(x *F22Report) { x.Arms[0].Windows[1].Correct[1] = 0 }},
		{"false score", func(x *F22Report) { x.Arms[0].Windows[1].Correct[0] = 13 }},
		{"loser omitted", func(x *F22Report) { x.Arms = x.Arms[:3] }},
		{"reordered", func(x *F22Report) { x.Arms[0], x.Arms[1] = x.Arms[1], x.Arms[0] }},
		{"credit", func(x *F22Report) { x.Arms[0].G1Credited = 64 }},
		{"cold", func(x *F22Report) { x.Arms[0].G2SHA256 = "fake" }},
		{"science", func(x *F22Report) { x.ScientificAccepted = true }},
		{"first use", func(x *F22Report) { x.FirstUseConsumed = true }},
		{"cost", func(x *F22Report) { x.WholeProcessCostProven = true }},
		{"owner", func(x *F22Report) { x.OwnerEligible = true }},
		{"dispatch", func(x *F22Report) { x.DispatchAuthorized = true }},
		{"active", func(x *F22Report) { x.ActiveResearchChanged = true }},
		{"paid", func(x *F22Report) { x.PaidAPICalls = 1 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			x := clone()
			tc.mutate(&x)
			x.DigestSHA256 = f22Digest(x)
			if F22Validate(x) == nil {
				t.Fatal("rehashed forged report/authority accepted")
			}
		})
	}
}
