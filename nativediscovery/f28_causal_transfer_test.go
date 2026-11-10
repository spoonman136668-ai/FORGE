package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF28FrozenDevelopment(t *testing.T) {
	r, e := F28Development()
	if e != nil || F28Validate(r) != nil {
		t.Fatal("frozen trial error", e)
	}
	if r.Schema != F28Schema || r.Parent != F28Parent || r.TrainingWorlds != [2]uint32{241, 243} || r.TransferWorlds != [4]uint32{251, 257, 263, 269} || r.TrainingTransitions != 128 || r.TransferTransitions != 48 || r.MinNLLGain != .05 || r.MinAblationNLLGain != .10 || r.MinSegmentGain != 1 || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		t.Fatal("protocol drift")
	}
	passed := 0
	for i, a := range r.Arms {
		if a.Seed != r.TransferWorlds[i] || a.Schedule != f28SeedWorlds()[i].Schedule {
			t.Fatal("arm order")
		}
		best := math.Inf(1)
		br, bn := 0, 0
		for j, v := range a.Trials {
			if v.Kind != f28Kinds()[j] || v.TransferSeen != 48 || v.TrainingSeen != 128 || v.Work <= 0 || len(v.ActionsSHA256) != 64 || len(v.SensorsSHA256) != 64 || len(v.PredictionsSHA256) != 64 || len(v.CheckpointSHA256) != 64 || len(v.TerminalSHA256) != 64 || !v.ColdMatches || math.IsNaN(v.MeanNLL) || math.IsInf(v.MeanNLL, 0) {
				t.Fatal("incomplete trial", i, j)
			}
			total := 0
			for _, x := range v.PhaseAccuracy {
				total += x
			}
			if total != v.Accuracy {
				t.Fatal("accuracy trace")
			}
			if j >= 1 && j <= 5 {
				if v.MeanNLL < best {
					best = v.MeanNLL
				}
				if v.PhaseAccuracy[2] > br {
					br = v.PhaseAccuracy[2]
				}
				if v.PhaseAccuracy[3] > bn {
					bn = v.PhaseAccuracy[3]
				}
			}
			if v.ActionsSHA256 != a.Trials[0].ActionsSHA256 || v.SensorsSHA256 != a.Trials[0].SensorsSHA256 {
				t.Fatal("unequal actions/sensors")
			}
		}
		pass := best-a.Trials[0].MeanNLL >= .05 && a.Trials[6].MeanNLL-a.Trials[0].MeanNLL >= .10 && a.Trials[7].MeanNLL-a.Trials[0].MeanNLL >= .10 && a.Trials[0].PhaseAccuracy[2] >= br+1 && a.Trials[0].PhaseAccuracy[3] >= bn+1
		if pass != a.Passes || math.Abs(best-a.BestConventionalNLL) > 1e-12 || br != a.BestConventionalReturn || bn != a.BestConventionalNovel {
			t.Fatal("score reclassification")
		}
		if pass {
			passed++
		}
		t.Logf("F28_DEV seed=%d schedule=%s candidate=%.4f strongest=%.4f delta=%.4f accuracy=%d return=%d/%d novel=%d/%d ablations=%.4f/%.4f pass=%t", a.Seed, a.Schedule, a.Trials[0].MeanNLL, a.BestConventionalNLL, a.CandidateGainNLL, a.Trials[0].Accuracy, a.Trials[0].PhaseAccuracy[2], br, a.Trials[0].PhaseAccuracy[3], bn, a.GainOverwriteNLL, a.GainWrongActionNLL, a.Passes)
	}
	class := F28NoGo
	if passed == 4 {
		class = F28Signal
	}
	if r.Passing != passed || r.Classification != class {
		t.Fatal("frozen status changed")
	}
	t.Logf("F28_FROZEN_DEV=%s arms=%d/4 first_use=false science=false", r.Classification, passed)
}
func TestF28ActualWorldChangesAndUnseenCausalLaw(t *testing.T) {
	for c := 0; c < 4; c++ {
		ba, ea, e := f28Law('A', c)
		if e != nil {
			t.Fatal(e)
		}
		bb, eb, e := f28Law('B', c)
		if e != nil {
			t.Fatal(e)
		}
		bc, ec, e := f28Law('C', c)
		if e != nil {
			t.Fatal(e)
		}
		bd, ed, e := f28Law('D', c)
		if e != nil {
			t.Fatal(e)
		}
		if c%2 == 0 && (bc != ba || ec != eb || bd != bb || ed != ea) {
			t.Fatal("recombination")
		}
		if c%2 == 1 && (bc != bb || ec != ea || bd != ba || ed != eb) {
			t.Fatal("recombination")
		}
	}
	for _, id := range f28SeedWorlds() {
		w, e := f28NewWorld(id.Seed, id.Schedule)
		if e != nil {
			t.Fatal(e)
		}
		for k := 0; k < 48; k++ {
			c, e := f28Cue(id.Seed, id.Schedule, k)
			if e != nil {
				t.Fatal(e)
			}
			a, e := f28Action(id.Seed, k)
			if e != nil {
				t.Fatal(e)
			}
			phase, e := f28Phase(id.Seed, k)
			if e != nil {
				t.Fatal(e)
			}
			b, x, e := f28Law(phase, c)
			if e != nil {
				t.Fatal(e)
			}
			prev := w.S
			truth, _, e := w.step(k, c, a)
			if e != nil || w.S != (prev+b+a*x)%4 || truth != w.clean() {
				t.Fatal("action not causally changing persistent state")
			}
		}
		if w.Seen != 48 {
			t.Fatal("world not finished")
		}
	}
}
func TestF28NoFirstUseNoOracle(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 211, 223, 227, 229, 233, 239, 240, 242, 244, 250, 252, 256, 258, 262, 264, 268, 270} {
		if _, e := f28Cue(seed, "balanced", 0); e == nil {
			t.Fatal("unknown cue")
		}
		if _, e := f28Action(seed, 0); e == nil {
			t.Fatal("unknown action")
		}
		if _, e := f28NewWorld(seed, "balanced"); e == nil {
			t.Fatal("hidden world")
		}
		if _, e := f28Phase(seed, 0); e == nil {
			t.Fatal("unknown law")
		}
	}
	for _, s := range []string{"oracle", "hidden-state", "", "SCIENCE_PASS"} {
		if _, e := f28New(s); e == nil {
			t.Fatal("unknown policy")
		}
	}
	if _, e := f28Cue(251, "bad", 0); e == nil {
		t.Fatal("bad schedule")
	}
	if _, e := f28Cue(251, "balanced", 48); e == nil {
		t.Fatal("future cue")
	}
	if _, e := f28Action(251, 48); e == nil {
		t.Fatal("future action")
	}
}
func TestF28ColdCheckpointAndTampering(t *testing.T) {
	for _, kind := range f28Kinds() {
		trained, e := f28Train(kind)
		if e != nil || trained.TrainingSeen != 128 {
			t.Fatal("training", e)
		}
		serialized, e := f28Save(trained)
		if e != nil {
			t.Fatal("checkpoint", e)
		}
		cloned, e := f28Load(serialized)
		if e != nil || !reflect.DeepEqual(trained, cloned) {
			t.Fatal("cold learning loss", e)
		}
		corrupt := append([]byte(nil), serialized...)
		corrupt[0] = '['
		if _, e := f28Load(corrupt); e == nil {
			t.Fatal("corrupt admitted")
		}
		if _, e := f28Load(append([]byte(" "), serialized...)); e == nil {
			t.Fatal("noncanonical checkpoint")
		}
		for _, w := range f28SeedWorlds() {
			cold, cbytes, e := f28Trial(trained, w.Seed, w.Schedule, true)
			warm, wbytes, e2 := f28Trial(trained, w.Seed, w.Schedule, false)
			if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cbytes, wbytes) {
				t.Fatal("cold warm divergence", kind, w, e, e2)
			}
		}
	}
}
func TestF28CannotRehashScientificClaimsOrThresholds(t *testing.T) {
	r, e := F28Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		mutate func(*F28Report)
	}{
		{"scientific", func(x *F28Report) { x.ScientificAccepted = true }},
		{"firstuse", func(x *F28Report) { x.FirstUseConsumed = true }},
		{"owner", func(x *F28Report) { x.OwnerEligible = true }},
		{"dispatch", func(x *F28Report) { x.DispatchAuthorized = true }},
		{"cost", func(x *F28Report) { x.WholeProcessCostProven = true }},
		{"compute", func(x *F28Report) { x.MatchedComputeProven = true }},
		{"negative", func(x *F28Report) { x.EarlierNegativesPreserved = false }},
		{"threshold", func(x *F28Report) { x.MinNLLGain = 0 }},
		{"seed", func(x *F28Report) { x.TransferWorlds[0] = 59 }},
		{"baseline", func(x *F28Report) { x.Arms[0].Trials[1].MeanNLL = 100 }},
		{"candidate", func(x *F28Report) { x.Arms[0].Trials[0].MeanNLL = 0 }},
		{"relabel", func(x *F28Report) { x.Classification = F28Signal }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b, _ := json.Marshal(r)
			var copy F28Report
			if json.Unmarshal(b, &copy) != nil {
				t.Fatal("copy")
			}
			tc.mutate(&copy)
			copy.DigestSHA256 = f28Digest(copy)
			if F28Validate(copy) == nil {
				t.Fatal("forgery admitted")
			}
		})
	}
}
