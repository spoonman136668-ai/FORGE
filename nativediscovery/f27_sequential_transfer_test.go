package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF27DevelopmentFrozenFourTransferWorlds(t *testing.T) {
	r, err := F27Development()
	if err != nil || F27Validate(r) != nil {
		t.Fatal("frozen experiment cannot reproduce", err)
	}
	if r.Schema != F27Schema || r.Parent != F27Parent || r.TrainingWorlds != [2]uint32{211, 223} || r.TransferWorlds != [4]uint32{227, 229, 233, 239} || r.TrainingTransitions != 128 || r.TransferTransitions != 48 || r.MinimumGain != 3 || r.MinimumAblationGain != 5 || r.MinimumEarlyGain != 1 || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven {
		t.Fatal("frozen source or scientific authority drift")
	}
	passing := 0
	for i, a := range r.Arms {
		w := f27TransferWorlds()[i]
		if a.Seed != w.Seed || a.Schedule != w.Schedule {
			t.Fatal("world identity drift")
		}
		strong, strongEarly := -1, -1
		for j, x := range a.Trials {
			if x.Kind != f27Kinds()[j] || x.Seen != 48 || x.TrainingSeen != 128 || x.Score < 0 || x.Score > 48 || x.Work <= 0 || !x.ColdMatches || x.First16+x.Middle16+x.Last16 != x.Score || x.InterventionScore+x.PassiveScore != x.Score || x.UniqueCues < 1 || x.UniqueCues > 4 || len(x.ActionsSHA256) != 64 || len(x.PredictionsSHA256) != 64 || len(x.CheckpointSHA256) != 64 || len(x.TerminalSHA256) != 64 {
				t.Fatalf("invalid trial provenance: world=%d kind=%s", i, x.Kind)
			}
			if x.ActionsSHA256 != a.Trials[0].ActionsSHA256 {
				t.Fatal("different interaction trace")
			}
			if j >= 1 && j <= 3 {
				if x.Score > strong {
					strong = x.Score
				}
				if x.First16 > strongEarly {
					strongEarly = x.First16
				}
			}
		}
		passes := a.Trials[0].Score >= strong+3 && a.Trials[0].Score >= a.Trials[4].Score+5 && a.Trials[0].Score >= a.Trials[5].Score+5 && a.Trials[0].First16 >= strongEarly+1
		if a.BestConventional != strong || a.BestConventionalEarly != strongEarly || a.GainStrong != a.Trials[0].Score-strong || a.GainActionBlind != a.Trials[0].Score-a.Trials[4].Score || a.GainColdZero != a.Trials[0].Score-a.Trials[5].Score || a.Passes != passes {
			t.Fatal("hindsight relabel")
		}
		if passes {
			passing++
		}
		t.Logf("F27_DEV seed=%d schedule=%s causal=%d/48 markov=%d delta=%d softmax=%d blind=%d coldzero=%d gain=%+d early=%d/%d work=%d pass=%t", a.Seed, a.Schedule, a.Trials[0].Score, a.Trials[1].Score, a.Trials[2].Score, a.Trials[3].Score, a.Trials[4].Score, a.Trials[5].Score, a.GainStrong, a.Trials[0].First16, strongEarly, a.Trials[0].Work, passes)
	}
	expected := F27NoGo
	if passing == 4 {
		expected = F27Signal
	}
	if r.Passing != passing || r.Classification != expected {
		t.Fatal("classification altered")
	}
	t.Logf("F27_FROZEN_DEV=%s passing=%d/4; SCIENTIFIC_PASS=false", r.Classification, passing)
}
func TestF27ActualActionChangesPersistentState(t *testing.T) {
	left, e := f27NewWorld(227, "balanced")
	if e != nil {
		t.Fatal(e)
	}
	right := left
	cue, e := f27Cue(227, "balanced", 0)
	if e != nil {
		t.Fatal(e)
	}
	if _, _, e = left.step(0, cue, 0); e != nil {
		t.Fatal(e)
	}
	if _, _, e = right.step(0, cue, 1); e != nil {
		t.Fatal(e)
	}
	if left.S == right.S || left.clean() == right.clean() {
		t.Fatal("action has no consequence")
	}
	// The consequence persists through the next passive transition.
	nextCue, _ := f27Cue(227, "balanced", 1)
	if _, _, e = left.step(1, nextCue, 0); e != nil {
		t.Fatal(e)
	}
	if _, _, e = right.step(1, nextCue, 0); e != nil {
		t.Fatal(e)
	}
	if left.S == right.S {
		t.Fatal("causal action effect did not persist")
	}
}
func TestF27NoHiddenStateFirstUseOrFuturePeeking(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 193, 197, 210, 212, 224, 226, 228, 230, 232, 234, 238, 240} {
		if _, e := f27NewWorld(seed, "balanced"); e == nil {
			t.Fatal("unregistered world")
		}
		if _, e := f27Cue(seed, "balanced", 0); e == nil {
			t.Fatal("unregistered cue")
		}
		if _, e := f27Sensor(seed, 0, 0, 0); e == nil {
			t.Fatal("unregistered sensor")
		}
	}
	if _, e := f27Cue(227, "balanced", 64); e == nil {
		t.Fatal("future cue")
	}
	if _, e := f27Cue(227, "unknown", 0); e == nil {
		t.Fatal("unknown schedule")
	}
	if _, e := f27Sensor(227, 0, 0, 2); e == nil {
		t.Fatal("unknown sensor")
	}
	if _, e := f27Sensor(227, -1, 0, 0); e == nil {
		t.Fatal("negative time")
	}
	if _, e := f27New("oracle"); e == nil {
		t.Fatal("oracle learner admitted")
	}
	for _, k := range f27Kinds() {
		m, _ := f27New(k)
		if _, e := m.forecast(0, 1); e == nil {
			t.Fatal("forecast before observation admitted")
		}
	}
}
func TestF27StrongBayesianNormalizationAndDeterminism(t *testing.T) {
	for _, ob := range [][2]int{{0, 0}, {0, 1}, {0, 2}, {2, 0}, {3, 3}} {
		p, e := f27Posterior(ob)
		if e != nil {
			t.Fatal(e)
		}
		total := 0.0
		for _, x := range p {
			if math.IsNaN(x) || math.IsInf(x, 0) || x < 0 {
				t.Fatal("bad belief")
			}
			total += x
		}
		if math.Abs(total-1) > 1e-12 {
			t.Fatal("unnormalized belief")
		}
	}
	for _, kind := range f27Kinds() {
		trained, e := f27Training(kind)
		if e != nil {
			t.Fatal(e)
		}
		if trained.TrainingSeen != 128 || trained.TransferSeen != 0 {
			t.Fatal("training inadequate")
		}
		data, e := f27Save(trained)
		if e != nil {
			t.Fatal(e)
		}
		restored, e := f27Load(data)
		if e != nil || !reflect.DeepEqual(trained, restored) {
			t.Fatal("cold restored wrong model")
		}
		for _, w := range f27TransferWorlds() {
			cold, cb, e := f27TrialRun(restored, w.Seed, w.Schedule, true)
			warm, wb, e2 := f27TrialRun(trained, w.Seed, w.Schedule, false)
			if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				t.Fatal("cold/warm predictions diverged", kind, w)
			}
			if cold.TrainingSeen != 128 || cold.Seen != 48 {
				t.Fatal("replayed training or lost transfer")
			}
		}
		corrupted := append([]byte(nil), data...)
		corrupted[0] = '['
		if _, e := f27Load(corrupted); e == nil {
			t.Fatal("corrupt checkpoint")
		}
		nonCanonical := append([]byte{' '}, data...)
		if _, e := f27Load(nonCanonical); e == nil {
			t.Fatal("noncanonical checkpoint")
		}
		var changed f27Model
		if json.Unmarshal(data, &changed) != nil {
			t.Fatal("invalid JSON")
		}
		changed.TrainingSeen = 129
		b, _ := json.Marshal(changed)
		if _, e := f27Load(b); e == nil {
			t.Fatal("replayed training accepted")
		}
	}
}
func TestF27NoScientificRehashOrDevelopmentRelabel(t *testing.T) {
	r, e := F27Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		change func(*F27Report)
	}{
		{"science", func(r *F27Report) { r.ScientificAccepted = true }},
		{"first-use", func(r *F27Report) { r.FirstUseConsumed = true }},
		{"owner", func(r *F27Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F27Report) { r.DispatchAuthorized = true }},
		{"whole-cost", func(r *F27Report) { r.WholeProcessCostProven = true }},
		{"compute", func(r *F27Report) { r.MatchedComputeProven = true }},
		{"seed", func(r *F27Report) { r.TransferWorlds[0] = 59 }},
		{"threshold", func(r *F27Report) { r.MinimumGain = 0 }},
		{"negative", func(r *F27Report) { r.EarlierNegativesPreserved = false }},
		{"candidate-score", func(r *F27Report) { r.Arms[0].Trials[0].Score = 48 }},
		{"baseline-score", func(r *F27Report) { r.Arms[0].Trials[1].Score = 0 }},
		{"relabel", func(r *F27Report) { r.Classification = F27Signal }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b, _ := json.Marshal(r)
			var mutated F27Report
			if json.Unmarshal(b, &mutated) != nil {
				t.Fatal("copy")
			}
			tc.change(&mutated)
			mutated.DigestSHA256 = f27Digest(mutated)
			if F27Validate(mutated) == nil {
				t.Fatal("rehash forged scientific admission")
			}
		})
	}
}
