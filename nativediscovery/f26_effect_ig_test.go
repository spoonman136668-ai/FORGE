package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF26FourFrozenDevelopmentArms(t *testing.T) {
	r, e := F26Development()
	if e != nil || F26Validate(r) != nil {
		t.Fatal("frozen comparison/custody invalid", e)
	}
	if r.Schema != F26Schema || r.Parent != F26Parent || r.Seeds != [2]uint32{193, 197} || r.Schedules != [2]string{"balanced", "skewed"} || r.Actions != 48 || r.Budget != 8 || r.Checkpoints != [4]int{10, 18, 26, 34} || r.MinimumGain != 2 || r.MinimumAblationGain != 3 || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.ScientificAccepted || r.FirstUseConsumed || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven {
		t.Fatal("frozen protocol changed")
	}
	count := 0
	for i, a := range r.Arms {
		if a.Seed != r.Seeds[i/2] || a.Schedule != r.Schedules[i%2] {
			t.Fatal("arm identity")
		}
		for j, x := range a.Trials {
			if x.Kind != f26Kinds()[j] || x.Credits != 46 || x.Pending != 2 || x.Spent < 0 || x.Spent > 8 || x.Work <= 0 || !x.ColdMatches || len(x.Trace) != 32 || len(x.ActionsSHA256) != 64 || len(x.CheckpointSHA256) != 64 || len(x.FinalSHA256) != 64 {
				t.Fatal("trial lineage", i, j)
			}
			score, bits := 0, 0
			for _, v := range x.Checkpoints {
				score += v
			}
			for _, v := range x.Trace {
				if v == '1' {
					bits++
				} else if v != '0' {
					t.Fatal("score binary")
				}
			}
			if score != x.Score || bits != score {
				t.Fatal("scorer drift")
			}
		}
		best := -1
		for j := 1; j <= 6; j++ {
			if a.Trials[j].Score > best {
				best = a.Trials[j].Score
			}
		}
		pass := a.Trials[0].Score >= best+2 && a.Trials[0].Score >= a.Trials[7].Score+3 && a.Trials[0].Score >= a.Trials[8].Score+3 && a.Trials[0].Spent >= 2 && a.Trials[0].Spent <= 8
		if pass != a.Passes || best != a.BestConventional {
			t.Fatal("classification mismatch")
		}
		if pass {
			count++
		}
		t.Logf("F26_DEV seed=%d schedule=%s candidate=%d/32 control=%v best=%d gain=%+d no=%d wrong=%d spent=%d pass=%v", a.Seed, a.Schedule, a.Trials[0].Score, [6]int{a.Trials[1].Score, a.Trials[2].Score, a.Trials[3].Score, a.Trials[4].Score, a.Trials[5].Score, a.Trials[6].Score}, best, a.GainStrong, a.Trials[7].Score, a.Trials[8].Score, a.Trials[0].Spent, pass)
	}
	expected := F26NoGo
	if count == 4 {
		expected = F26Signal
	}
	if count != r.Passing || expected != r.Classification {
		t.Fatal("frozen signal altered")
	}
	t.Logf("F26_FROZEN_DEV=%s passing=%d/4", r.Classification, count)
}
func TestF26EffectInformationIsActionSpecific(t *testing.T) {
	// Under a uniform independent B/E prior, do(0) cannot identify E, while do(1) alone also cannot.
	var f [4]float64
	for i := range f {
		f[i] = .25
	}
	if math.Abs(f26EffectIG(f, 0)) > 1e-10 || math.Abs(f26EffectIG(f, 1)) > 1e-10 {
		t.Fatal("unidentifiable bit given uniform latent baseline")
	}
	// Once passive outcomes identify the baseline B, an intervention can identify causal E.
	f = [4]float64{.48, .02, .48, .02}
	if f26EffectIG(f, 1) <= f26EffectIG(f, 0)+.05 {
		t.Fatal("effect-specific intervention not identified")
	}
}
func TestF26NoUnknownSeedOrOracle(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 151, 157, 163, 167, 173, 179, 192, 194, 196, 198} {
		if _, e := f26Law(seed); e == nil {
			t.Fatal("seed law leak")
		}
		if _, e := f26Cue(seed, "balanced", 0); e == nil {
			t.Fatal("seed cue leak")
		}
		if _, e := f26Outcome(seed, 0, 0, 0); e == nil {
			t.Fatal("seed outcome leak")
		}
		if _, _, e := f26Select(nil, nil, 0, 0, 0, seed, "effect-ig"); e == nil {
			t.Fatal("seed action leak")
		}
	}
	for _, kind := range []string{"oracle", "", "first-use", "hidden-law"} {
		if _, _, e := f26Select(nil, nil, 0, 0, 0, 193, kind); e == nil {
			t.Fatal("unregistered strategy")
		}
	}
	if _, _, e := f26Select(nil, nil, 4, 0, 0, 193, "effect-ig"); e == nil {
		t.Fatal("invalid cue")
	}
	if _, _, e := f26Select(nil, nil, 0, 48, 0, 193, "effect-ig"); e == nil {
		t.Fatal("out-of-window step")
	}
	if _, _, e := f26Select(nil, nil, 0, 3, 9, 193, "effect-ig"); e == nil {
		t.Fatal("budget bypass")
	}
	if _, e := f26Cue(193, "unknown", 0); e == nil {
		t.Fatal("bad schedule")
	}
}
func TestF26ColdRestartAndCredits(t *testing.T) {
	for _, seed := range f26Seeds() {
		for _, sched := range f26Schedules() {
			for _, kind := range f26Kinds() {
				cold, ck, raw, e := f26Run(seed, sched, kind, true)
				warm, wck, wraw, e2 := f26Run(seed, sched, kind, false)
				if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(ck, wck) || !bytes.Equal(raw, wraw) {
					t.Fatal("cold mismatch")
				}
				s, e := f26Load(ck)
				if e != nil || s.Seen != 24 || len(s.Credits) != 22 || len(s.Pending) != 2 || s.Pending[0].Step != 22 || s.Pending[1].Step != 23 {
					t.Fatal("checkpoint credit")
				}
				s, e = f26Load(raw)
				if e != nil || s.Seen != 48 || len(s.Credits) != 46 || len(s.Pending) != 2 || s.Pending[0].Step != 46 || s.Pending[1].Step != 47 {
					t.Fatal("final credit")
				}
				corrupt := append([]byte(nil), ck...)
				corrupt[0] = '['
				if _, e := f26Load(corrupt); e == nil {
					t.Fatal("invalid checkpoint")
				}
				noncanon := append([]byte(" "), ck...)
				if _, e := f26Load(noncanon); e == nil {
					t.Fatal("noncanonical checkpoint")
				}
				s.Credits[0], s.Credits[1] = s.Credits[1], s.Credits[0]
				if _, e := f26Save(s); e == nil {
					t.Fatal("reordered records")
				}
			}
		}
	}
}
func TestF26RehashCannotForgeScienceOrNegative(t *testing.T) {
	r, e := F26Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		update func(*F26Report)
	}{
		{"science", func(r *F26Report) { r.ScientificAccepted = true }},
		{"first-use", func(r *F26Report) { r.FirstUseConsumed = true }},
		{"owner", func(r *F26Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F26Report) { r.DispatchAuthorized = true }},
		{"cost", func(r *F26Report) { r.WholeProcessCostProven = true }},
		{"threshold", func(r *F26Report) { r.MinimumGain = 0 }},
		{"seed", func(r *F26Report) { r.Seeds[0] = 59 }},
		{"negative", func(r *F26Report) { r.EarlierNegativesPreserved = false }},
		{"score", func(r *F26Report) { r.Arms[0].Trials[0].Score = 32 }},
		{"bestcontrol", func(r *F26Report) { r.Arms[0].Trials[1].Score = 0 }},
		{"relabel", func(r *F26Report) { r.Classification = F26Signal }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b, _ := json.Marshal(r)
			var copy F26Report
			if json.Unmarshal(b, &copy) != nil {
				t.Fatal("clone")
			}
			tc.update(&copy)
			copy.DigestSHA256 = f26Digest(copy)
			if F26Validate(copy) == nil {
				t.Fatal("forgery admitted")
			}
		})
	}
}
