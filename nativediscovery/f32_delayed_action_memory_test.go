package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF32FrozenDevelopmentAndEqualActions(t *testing.T) {
	r, e := F32Development()
	if e != nil || F32Validate(r) != nil {
		t.Fatal("frozen F32 invalid", e)
	}
	if r.Schema != F32Schema || r.Parent != F32Parent || r.TrainSeeds != [2]uint32{331, 337} || r.TransferSeeds != [4]uint32{347, 349, 353, 359} || r.TrainTransitions != 256 || r.TransferTransitions != 96 || r.MinGain != .05 || r.MinAblationGain != .10 || r.MinNovelGain != 2 || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven {
		t.Fatal("frozen source or authority drift")
	}
	for bank, row := range r.Coverage {
		for cue, got := range row {
			if got != 4 {
				t.Fatalf("bank %d cue %d training pulses %d", bank, cue, got)
			}
		}
	}
	passing := 0
	for i, arm := range r.Arms {
		if arm.Seed != r.TransferSeeds[i] || arm.Schedule != f32Worlds()[i].Schedule {
			t.Fatal("wrong transfer world")
		}
		best := math.Inf(1)
		bestReturn, bestNovel := 0, 0
		for j, x := range arm.Trials {
			if x.Kind != f32Kinds()[j] || x.TrainingSeen != 256 || x.TransferSeen != 96 || x.Work <= 0 || x.Parameters <= 0 || x.Accuracy < 0 || x.Accuracy > 96 || math.IsNaN(x.MeanNLL) || math.IsInf(x.MeanNLL, 0) || x.MeanNLL < 0 || !x.ColdMatches || len(x.ActionsSHA256) != 64 || len(x.SensorsSHA256) != 64 || len(x.PredictionsSHA256) != 64 || len(x.CheckpointSHA256) != 64 || len(x.TerminalSHA256) != 64 {
				t.Fatalf("invalid world=%d model=%d", i, j)
			}
			score := 0
			for _, n := range x.PhaseAccuracy {
				if n < 0 || n > 24 {
					t.Fatal("phase count invalid")
				}
				score += n
			}
			if score != x.Accuracy {
				t.Fatal("inconsistent phase scores")
			}
			for _, n := range x.FirstAfterSwitch {
				if n < 0 || n > 8 {
					t.Fatal("early count")
				}
			}
			if x.ActionsSHA256 != arm.Trials[0].ActionsSHA256 || x.SensorsSHA256 != arm.Trials[0].SensorsSHA256 {
				t.Fatal("mismatched real action and observation exposure")
			}
			if j > 0 && j <= 3 {
				if x.MeanNLL < best {
					best = x.MeanNLL
				}
				if x.PhaseAccuracy[2] > bestReturn {
					bestReturn = x.PhaseAccuracy[2]
				}
				if x.PhaseAccuracy[3] > bestNovel {
					bestNovel = x.PhaseAccuracy[3]
				}
			}
		}
		pass := best-arm.Trials[0].MeanNLL >= .05 && arm.Trials[4].MeanNLL-arm.Trials[0].MeanNLL >= .10 && arm.Trials[5].MeanNLL-arm.Trials[0].MeanNLL >= .10 && arm.Trials[0].PhaseAccuracy[2] >= bestReturn && arm.Trials[0].PhaseAccuracy[3] >= bestNovel+2
		if pass != arm.Passes || math.Abs(best-arm.BestConventionalNLL) > 1e-9 {
			t.Fatal("frozen result mismatch")
		}
		if pass {
			passing++
		}
		t.Logf("F32_DEV seed=%d schedule=%s candidate=%.6f best=%.6f gain=%+.6f return=%d/%d novel=%d/%d blind=%.6f coldzero=%.6f pass=%v", arm.Seed, arm.Schedule, arm.Trials[0].MeanNLL, best, arm.GainStrong, arm.Trials[0].PhaseAccuracy[2], bestReturn, arm.Trials[0].PhaseAccuracy[3], bestNovel, arm.GainHistoryBlind, arm.GainColdZero, pass)
	}
	class := F32NoGo
	if passing == 4 {
		class = F32Signal
	}
	if passing != r.Passing || class != r.Classification {
		t.Fatal("false DEV promotion")
	}
	t.Logf("F32_FROZEN_DEV=%s passing=%d/4 first_use=false science=false", class, passing)
}
func TestF32GenuineDelayedPersistentEffects(t *testing.T) {
	// Verify schedule, no earlier effect, and persistence, including events spanning phases.
	for _, seed := range []uint32{331, 337, 347, 349, 353, 359} {
		w, e := f32NewWorld(seed)
		if e != nil {
			t.Fatal(e)
		}
		length := 96
		sched := "balanced"
		if f32Training(seed) {
			length = 128
			sched = "isolated"
		}
		if seed == 349 || seed == 359 {
			sched = "skewed"
		}
		pending := map[int]int{}
		expected := w.State
		for step := 0; step < length; step++ {
			cue, action, e := f32Schedule(seed, sched, step)
			if e != nil {
				t.Fatal(e)
			}
			phase, e := f32Phase(seed, step)
			if e != nil {
				t.Fatal(e)
			}
			if action == 1 {
				spec, e := f32Law(phase, cue)
				if e != nil {
					t.Fatal(e)
				}
				pending[step+spec.Lag-1] ^= spec.Mask
			}
			expected ^= pending[step]
			got, _, e := w.step(step, cue, action)
			if e != nil || got != expected {
				t.Fatalf("missing persistent delayed consequence seed=%d t=%d actual=%d expected=%d", seed, step, got, expected)
			}
		}
	}
	// Isolated impulse 3-step lag must leave state unchanged on the first two transitions.
	w, e := f32NewWorld(331)
	if e != nil {
		t.Fatal(e)
	}
	before := w.State
	_, _, e = w.step(0, 0, 1)
	if e != nil {
		t.Fatal(e)
	}
	if w.State == before {
		t.Fatal("lag-1 learned world cue0 did not change")
	}
	for _, bad := range []uint32{59, 83, 0, 211, 223, 241, 243, 301, 303, 307, 311, 313, 317, 330, 332, 336, 338, 345, 357} {
		if _, e := f32NewWorld(bad); e == nil {
			t.Fatal("unknown or first-use seed allowed")
		}
	}
	if _, _, e := f32Schedule(347, "balanced", 96); e == nil {
		t.Fatal("future transfer access")
	}
	if _, _, e := f32Schedule(331, "isolated", 128); e == nil {
		t.Fatal("future training access")
	}
	if _, e := f32Sensor(347, 0, 4, 0); e == nil {
		t.Fatal("invalid state")
	}
	if _, e := f32Law('Z', 0); e == nil {
		t.Fatal("hidden unknown law")
	}
}
func TestF32PosteriorUsesNoCleanState(t *testing.T) {
	train, e := f32MakeTrace(331, "isolated")
	if e != nil {
		t.Fatal(e)
	}
	logs, coverage, e := f32TrainLog(train)
	if e != nil {
		t.Fatal(e)
	}
	for _, n := range coverage {
		if n != 4 {
			t.Fatal("insufficient real training pulses")
		}
	}
	for cue := 0; cue < 4; cue++ {
		got := f32MAP(logs[cue])
		if got.Mask < 1 || got.Mask > 3 || got.Lag < 1 || got.Lag > 3 {
			t.Fatal("model hypothesis invalid")
		}
		for _, v := range logs[cue] {
			if math.IsNaN(v) || math.IsInf(v, 0) {
				t.Fatal("posterior invalid")
			}
		}
	}
	// Removing the simulator-only clean target must not change bank training.
	mod := train
	mod.Clean = nil
	other, _, e := f32TrainLog(mod)
	if e != nil || !reflect.DeepEqual(logs, other) {
		t.Fatal("hidden clean target leaked into training")
	}
}
func TestF32ColdWarmExactAndCheckpointNegatives(t *testing.T) {
	a, e := f32MakeTrace(331, "isolated")
	if e != nil {
		t.Fatal(e)
	}
	b, e := f32MakeTrace(337, "isolated")
	if e != nil {
		t.Fatal(e)
	}
	for _, kind := range f32Kinds() {
		m, e := f32Train(kind, [2]f32Trace{a, b})
		if e != nil {
			t.Fatal(e)
		}
		raw, e := f32Save(m)
		if e != nil {
			t.Fatal(e)
		}
		loaded, e := f32Load(raw)
		if e != nil || !reflect.DeepEqual(m, loaded) {
			t.Fatal("training cold checkpoint lost", kind)
		}
		bad := append([]byte("\n"), raw...)
		if _, e := f32Load(bad); e == nil {
			t.Fatal("noncanonical checkpoint allowed")
		}
		malformed := append([]byte(nil), raw...)
		malformed[0] = '['
		if _, e := f32Load(malformed); e == nil {
			t.Fatal("corrupted checkpoint allowed")
		}
		for _, world := range f32Worlds() {
			trace, e := f32MakeTrace(world.Seed, world.Schedule)
			if e != nil {
				t.Fatal(e)
			}
			cold, cb, e := f32Trial(m, trace, true)
			if e != nil {
				t.Fatal(e)
			}
			warm, wb, e := f32Trial(m, trace, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				t.Fatal("warm/cold loss", kind, world.Seed, e)
			}
		}
	}
}
func TestF32ScientificClaimsCannotBeForged(t *testing.T) {
	orig, e := F32Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name string
		fn   func(*F32Report)
	}{
		{"first-use", func(r *F32Report) { r.FirstUseConsumed = true }},
		{"science", func(r *F32Report) { r.ScientificAccepted = true }},
		{"owner", func(r *F32Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F32Report) { r.DispatchAuthorized = true }},
		{"compute", func(r *F32Report) { r.MatchedComputeProven = true }},
		{"cost", func(r *F32Report) { r.WholeProcessCostProven = true }},
		{"negative", func(r *F32Report) { r.EarlierNegativesPreserved = false }},
		{"seed", func(r *F32Report) { r.TransferSeeds[0] = 59 }},
		{"threshold", func(r *F32Report) { r.MinGain = 0 }},
		{"result", func(r *F32Report) { r.Classification = F32Signal }},
		{"score", func(r *F32Report) { r.Arms[0].Trials[0].MeanNLL = 0 }},
		{"control", func(r *F32Report) { r.Arms[0].Trials[1].MeanNLL = 999 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			raw, _ := json.Marshal(orig)
			var r F32Report
			if json.Unmarshal(raw, &r) != nil {
				t.Fatal("copy")
			}
			tc.fn(&r)
			r.DigestSHA256 = f32Digest(r)
			if F32Validate(r) == nil {
				t.Fatal("forged science accepted")
			}
		})
	}
}
