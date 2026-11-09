package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF25FrozenDevelopment(t *testing.T) {
	r, e := F25Development()
	if e != nil || F25Validate(r) != nil {
		t.Fatal("cannot reproduce F25 frozen development", e)
	}
	if r.Schema != F25Schema || r.Parent != F25Parent || r.Seeds != [2]uint32{173, 179} || r.Schedules != [2]string{"balanced", "skewed"} || r.Actions != 96 || r.Budget != 12 || r.Checkpoints != [4]int{24, 40, 56, 72} || r.MinimumGain != 2 || r.MinimumAblationGain != 3 || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven {
		t.Fatal("protocol or authority drift")
	}
	passed := 0
	for i, a := range r.Arms {
		if a.Seed != r.Seeds[i/2] || a.Schedule != r.Schedules[i%2] {
			t.Fatal("world mismatch")
		}
		for j, tr := range a.Trials {
			if tr.Kind != f25Kinds()[j] || tr.Credits != 94 || tr.Pending != 2 || tr.Spent < 0 || tr.Spent > 12 || !tr.ColdMatches || tr.Work < 1 || len(tr.Trace) != 32 || len(tr.ActionsSHA256) != 64 || len(tr.FinalSHA256) != 64 || len(tr.CheckpointSHA256) != 64 {
				t.Fatal("trial custody")
			}
			score, trace := 0, 0
			for _, v := range tr.Checkpoints {
				score += v
			}
			for _, v := range tr.Trace {
				if v == '1' {
					trace++
				} else if v != '0' {
					t.Fatal("non-binary score trace")
				}
			}
			if score != tr.Score || trace != score {
				t.Fatal("score mismatch")
			}
		}
		best := -1
		for j := 1; j <= 5; j++ {
			if a.Trials[j].Score > best {
				best = a.Trials[j].Score
			}
		}
		pass := a.Trials[0].Score >= best+2 && a.Trials[0].Score >= a.Trials[6].Score+3 && a.Trials[0].Score >= a.Trials[7].Score+3 && a.Trials[0].Spent >= 2 && a.Trials[0].Spent <= 12
		if pass != a.Passes || best != a.BestConventional {
			t.Fatal("post-result label drift")
		}
		if pass {
			passed++
		}
		t.Logf("F25_DEV seed=%d schedule=%s candidate=%d/32 controls=%v strongest=%d gain=%+d ablations(no/wrong)=%d/%d spent=%d pass=%v", a.Seed, a.Schedule, a.Trials[0].Score, [5]int{a.Trials[1].Score, a.Trials[2].Score, a.Trials[3].Score, a.Trials[4].Score, a.Trials[5].Score}, best, a.GainStrong, a.Trials[6].Score, a.Trials[7].Score, a.Trials[0].Spent, pass)
	}
	expectedClass := F25NoGo
	if passed == 4 {
		expectedClass = F25Signal
	}
	if r.Classification != expectedClass || r.Passing != passed {
		t.Fatal("incorrect classification")
	}
	t.Logf("F25_FROZEN_DEV=%s passing=%d/4 first_use=false science=false", r.Classification, r.Passing)
}
func TestF25NoOracleFirstUseOrUnknownPolicy(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 151, 157, 163, 167, 172, 174, 178, 180} {
		if _, e := f25World(seed); e == nil {
			t.Fatal("unregistered law accepted")
		}
		if _, e := f25Cue(seed, "balanced", 0); e == nil {
			t.Fatal("unregistered seed accepted")
		}
		if _, e := f25Observed(seed, 0, 0, 0); e == nil {
			t.Fatal("unregistered outcome accepted")
		}
		if _, _, e := f25Select(nil, nil, 0, 0, 0, seed, "causal-pair"); e == nil {
			t.Fatal("unregistered selector accepted")
		}
	}
	for _, kind := range []string{"", "oracle", "hidden-law", "full-bayes"} {
		if _, _, e := f25Select(nil, nil, 0, 0, 0, 173, kind); e == nil {
			t.Fatal("invalid policy admitted")
		}
	}
	if _, _, e := f25Select(nil, nil, 4, 0, 0, 173, "causal-pair"); e == nil {
		t.Fatal("bad cue")
	}
	if _, _, e := f25Select(nil, nil, 0, 96, 0, 173, "causal-pair"); e == nil {
		t.Fatal("future")
	}
	if _, _, e := f25Select(nil, nil, 0, 12, 13, 173, "causal-pair"); e == nil {
		t.Fatal("budget bypass")
	}
	if _, e := f25Cue(173, "unknown", 0); e == nil {
		t.Fatal("unknown schedule")
	}
	if _, _, e := f25Predict(nil, 4, 0, false); e == nil {
		t.Fatal("invalid scorer input")
	}
}
func TestF25CheckpointColdCreditIntegrity(t *testing.T) {
	for _, seed := range f25Seeds() {
		for _, sched := range f25Schedules() {
			for _, kind := range f25Kinds() {
				cold, ck, raw, e := f25Run(seed, sched, kind, true)
				warm, wck, wraw, e2 := f25Run(seed, sched, kind, false)
				if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(ck, wck) || !bytes.Equal(raw, wraw) {
					t.Fatal("cold continuity", kind)
				}
				s, e := f25Load(ck)
				if e != nil || s.Seen != 48 || len(s.Credits) != 46 || len(s.Pending) != 2 || s.Pending[0].Step != 46 || s.Pending[1].Step != 47 {
					t.Fatal("checkpoint lineage")
				}
				s, e = f25Load(raw)
				if e != nil || s.Seen != 96 || len(s.Credits) != 94 || len(s.Pending) != 2 || s.Pending[0].Step != 94 || s.Pending[1].Step != 95 {
					t.Fatal("terminal lineage")
				}
				corrupt := append([]byte(nil), ck...)
				corrupt[0] = '['
				if _, e := f25Load(corrupt); e == nil {
					t.Fatal("bad checkpoint accepted")
				}
				nonCanonical := append([]byte(" "), ck...)
				if _, e := f25Load(nonCanonical); e == nil {
					t.Fatal("noncanonical checkpoint accepted")
				}
				s.Credits[0], s.Credits[1] = s.Credits[1], s.Credits[0]
				if _, e := f25Save(s); e == nil {
					t.Fatal("reordered credits accepted")
				}
			}
		}
	}
}
func TestF25ReportRehashCannotForgeScience(t *testing.T) {
	orig, e := F25Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		change func(*F25Report)
	}{
		{"scientific", func(r *F25Report) { r.ScientificAccepted = true }},
		{"first-use", func(r *F25Report) { r.FirstUseConsumed = true }},
		{"owner", func(r *F25Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F25Report) { r.DispatchAuthorized = true }},
		{"cost", func(r *F25Report) { r.WholeProcessCostProven = true }},
		{"seed", func(r *F25Report) { r.Seeds[0] = 59 }},
		{"gain", func(r *F25Report) { r.MinimumGain = 0 }},
		{"candidate", func(r *F25Report) { r.Arms[0].Trials[0].Score = 32 }},
		{"baseline", func(r *F25Report) { r.Arms[0].Trials[1].Score = 0 }},
		{"negative", func(r *F25Report) { r.EarlierNegativesPreserved = false }},
		{"classification", func(r *F25Report) { r.Classification = F25Signal }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b, _ := json.Marshal(orig)
			var copy F25Report
			if json.Unmarshal(b, &copy) != nil {
				t.Fatal("copy")
			}
			tc.change(&copy)
			copy.DigestSHA256 = f25Digest(copy)
			if F25Validate(copy) == nil {
				t.Fatal("tampered report rehashed and admitted")
			}
		})
	}
}
