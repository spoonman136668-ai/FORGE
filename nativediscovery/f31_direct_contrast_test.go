package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF31FrozenFourWorldDevelopment(t *testing.T) {
	r, e := F31Development()
	if e != nil || F31Validate(r) != nil {
		t.Fatal("frozen development invalid", e)
	}
	if r.Schema != F31Schema || r.Parent != F31Parent || r.TrainingWorlds != [2]uint32{301, 303} || r.TransferWorlds != [4]uint32{307, 311, 313, 317} || r.TrainingTransitions != 128 || r.TransferTransitions != 48 || r.MinimumGain != .05 || r.MinimumAblationGain != .10 || r.MinimumNovelGain != 1 || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.MatchedComputeProven || r.WholeProcessCostProven {
		t.Fatal("frozen protocol or science boundary altered")
	}
	count := 0
	for i, world := range r.Coverage {
		for cue, acts := range world {
			for a, n := range acts {
				if n != 8 {
					t.Fatalf("missing coverage bank=%d cue=%d action=%d got=%d", i, cue, a, n)
				}
			}
		}
	}
	for i, arm := range r.Arms {
		if arm.Seed != r.TransferWorlds[i] || arm.Schedule != f31Worlds()[i].Schedule {
			t.Fatal("world identity mismatch")
		}
		best := math.Inf(1)
		bestReturn, bestNovel := 0, 0
		for j, x := range arm.Trials {
			if x.Kind != f31Kinds()[j] || x.TrainingSeen != 128 || x.TransferSeen != 48 || x.Accuracy < 0 || x.Accuracy > 48 || x.TrainingWork <= 0 || x.TransferWork <= 0 || x.Parameters <= 0 || !x.ColdMatches || math.IsNaN(x.MeanNLL) || math.IsInf(x.MeanNLL, 0) || x.MeanNLL < 0 || len(x.ActionsSHA256) != 64 || len(x.SensorsSHA256) != 64 || len(x.PredictionsSHA256) != 64 || len(x.CheckpointSHA256) != 64 || len(x.TerminalSHA256) != 64 {
				t.Fatalf("trial invalid world=%d model=%d", i, j)
			}
			correct := 0
			for _, n := range x.PhaseAccuracy {
				if n < 0 || n > 12 {
					t.Fatal("invalid phase count")
				}
				correct += n
			}
			if correct != x.Accuracy {
				t.Fatal("phase totals inconsistent")
			}
			if x.ActionsSHA256 != arm.Trials[0].ActionsSHA256 || x.SensorsSHA256 != arm.Trials[0].SensorsSHA256 {
				t.Fatal("unmatched observations/actions")
			}
			if j >= 1 && j <= 5 {
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
		pass := best-arm.Trials[0].MeanNLL >= .05 && arm.Trials[6].MeanNLL-arm.Trials[0].MeanNLL >= .10 && arm.Trials[7].MeanNLL-arm.Trials[0].MeanNLL >= .10 && arm.Trials[0].PhaseAccuracy[2] >= bestReturn && arm.Trials[0].PhaseAccuracy[3] >= bestNovel+1
		if pass != arm.Passes || math.Abs(best-arm.BestControlNLL) > 1e-10 {
			t.Fatal("frozen outcome mismatch")
		}
		if pass {
			count++
		}
		t.Logf("F31 seed=%d %s candidate_nll=%.7f best_control_nll=%.7f gain=%+.7f return=%d/%d novel=%d/%d no_cross_delta=%.7f wrong_action_delta=%.7f dev_pass=%v", arm.Seed, arm.Schedule, arm.Trials[0].MeanNLL, best, arm.GainStrong, arm.Trials[0].PhaseAccuracy[2], bestReturn, arm.Trials[0].PhaseAccuracy[3], bestNovel, arm.GainNoCross, arm.GainWrongAction, pass)
	}
	class := F31NoGo
	if count == 4 {
		class = F31Signal
	}
	if r.Passing != count || r.Classification != class {
		t.Fatal("scientific label mismatch")
	}
	t.Logf("F31_FROZEN_DEV=%s passing=%d/4", class, count)
}
func TestF31CoverageAndDirectObservationPreservation(t *testing.T) {
	actual, e := f31Coverage()
	if e != nil {
		t.Fatal(e)
	}
	for _, bank := range actual {
		for _, actions := range bank {
			for _, n := range actions {
				if n != 8 {
					t.Fatal("coverage schedule changed")
				}
			}
		}
	}
	m, e := f31Train("direct-contrast")
	if e != nil {
		t.Fatal(e)
	}
	for c := 0; c < 4; c++ {
		pairs, e := m.Direct.pairDeltas(c, 1)
		if e != nil {
			t.Fatal(e)
		}
		qa := f28DeltaProb(m.Direct.Bank[0], c, 1)
		qb := f28DeltaProb(m.Direct.Bank[1], c, 1)
		for d := 0; d < 4; d++ {
			if math.Abs(pairs[0][d]-qa[d]) > 1e-12 || math.Abs(pairs[3][d]-qb[d]) > 1e-12 {
				t.Fatal("same-bank action1 observations were blurred")
			}
		}
		for k := 0; k < 4; k++ {
			sum := 0.0
			for _, x := range pairs[k] {
				if x < 0 || x > 1 || math.IsNaN(x) {
					t.Fatal("invalid posterior")
				}
				sum += x
			}
			if math.Abs(sum-1) > 1e-9 {
				t.Fatal("pair probability not normalized")
			}
		}
	}
}
func TestF31RealPersistentIntervention(t *testing.T) {
	for _, seed := range []uint32{301, 303, 307, 311, 313, 317} {
		sched := "balanced"
		if seed == 311 || seed == 317 {
			sched = "skewed"
		}
		for c := 0; c < 4; c++ {
			w, e := f31NewWorld(seed, sched)
			if e != nil {
				t.Fatal(e)
			}
			first, second := w, w
			p, _, e := first.step(0, c, 0)
			if e != nil {
				t.Fatal(e)
			}
			q, _, e := second.step(0, c, 1)
			if e != nil {
				t.Fatal(e)
			}
			phase, e := f31Phase(seed, 0)
			if e != nil {
				t.Fatal(e)
			}
			_, eff, e := f28Law(phase, c)
			if e != nil {
				t.Fatal(e)
			}
			if (q-p+4)%4 != eff || second.S != (w.S+((first.S-w.S+4)%4)+eff)%4 {
				t.Fatal("actual action did not change persistent state")
			}
		}
	}
}
func TestF31ColdRestorationAndForgery(t *testing.T) {
	for _, kind := range f31Kinds() {
		model, e := f31Train(kind)
		if e != nil {
			t.Fatal(e)
		}
		ck, e := f31Save(model)
		if e != nil {
			t.Fatal(e)
		}
		copy, e := f31Load(ck)
		if e != nil || !reflect.DeepEqual(copy, model) {
			t.Fatal("cold trained state mismatch")
		}
		if _, e := f31Load(append([]byte(" "), ck...)); e == nil {
			t.Fatal("noncanonical checkpoint accepted")
		}
		altered := append([]byte(nil), ck...)
		altered[0] = '['
		if _, e := f31Load(altered); e == nil {
			t.Fatal("forged checkpoint accepted")
		}
		for _, w := range f31Worlds() {
			c, cb, e := f31Trial(model, w.Seed, w.Schedule, true)
			warm, wb, e2 := f31Trial(model, w.Seed, w.Schedule, false)
			if e != nil || e2 != nil || !reflect.DeepEqual(c, warm) || !bytes.Equal(cb, wb) {
				t.Fatal("cold/warm deviation", kind, w.Seed, e, e2)
			}
		}
	}
}
func TestF31FirstUseAndInvalidSourceFence(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 211, 223, 241, 243, 251, 257, 263, 269, 271, 277, 281, 283, 300, 302, 304, 306, 308, 310, 312, 314, 316, 318} {
		if _, e := f31NewWorld(seed, "balanced"); e == nil {
			t.Fatal("unknown/first-use world accepted")
		}
		if _, e := f31Cue(seed, "balanced", 0); e == nil {
			t.Fatal("unknown cue accepted")
		}
		if _, e := f31Action(seed, 0); e == nil {
			t.Fatal("unknown action accepted")
		}
		if _, e := f31Phase(seed, 0); e == nil {
			t.Fatal("unknown phase accepted")
		}
	}
	if _, e := f31Cue(307, "balanced", 48); e == nil {
		t.Fatal("future step accepted")
	}
	if _, e := f31Action(307, -1); e == nil {
		t.Fatal("negative time accepted")
	}
	if _, e := f31Sensor(307, 0, 4, 0); e == nil {
		t.Fatal("invalid sensor state accepted")
	}
	if _, e := f31Train("oracle"); e == nil {
		t.Fatal("unregistered method accepted")
	}
	if _, e := f31NewWorld(307, "oracle"); e == nil {
		t.Fatal("unregistered cue schedule")
	}
}
func TestF31ReportCannotBeForgedByRehash(t *testing.T) {
	r, e := F31Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		mutate func(*F31Report)
	}{
		{"first-use", func(r *F31Report) { r.FirstUseConsumed = true }},
		{"science", func(r *F31Report) { r.ScientificAccepted = true }},
		{"owner", func(r *F31Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F31Report) { r.DispatchAuthorized = true }},
		{"compute", func(r *F31Report) { r.MatchedComputeProven = true }},
		{"cost", func(r *F31Report) { r.WholeProcessCostProven = true }},
		{"threshold", func(r *F31Report) { r.MinimumGain = 0 }},
		{"seeds", func(r *F31Report) { r.TransferWorlds[0] = 59 }},
		{"coverage", func(r *F31Report) { r.Coverage[1][2][1] = 0 }},
		{"prior-negative", func(r *F31Report) { r.EarlierNegativesPreserved = false }},
		{"candidate-score", func(r *F31Report) { r.Arms[0].Trials[0].MeanNLL = 0 }},
		{"strong-control-score", func(r *F31Report) { r.Arms[0].Trials[1].MeanNLL = 999 }},
		{"relabel", func(r *F31Report) { r.Classification = F31Signal }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			raw, _ := json.Marshal(r)
			var changed F31Report
			if json.Unmarshal(raw, &changed) != nil {
				t.Fatal("copy failed")
			}
			tc.mutate(&changed)
			changed.DigestSHA256 = f31Digest(changed)
			if F31Validate(changed) == nil {
				t.Fatal("forged research evidence accepted")
			}
		})
	}
}
