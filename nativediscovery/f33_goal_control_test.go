package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF33FrozenDevelopmentFourInteractiveWorlds(t *testing.T) {
	r, e := F33Development()
	if e != nil || F33Validate(r) != nil {
		t.Fatal("invalid frozen F33 development", e)
	}
	if r.Schema != F33Schema || r.Parent != F33Parent || r.TrainSeeds != [2]uint32{331, 337} ||
		r.DevSeeds != [4]uint32{367, 373, 379, 383} || r.TrainingTransitions != 256 ||
		r.TransferTransitions != 96 || r.Decisions != 48 || r.Budget != 24 ||
		r.MinGoalsGain != 3 || r.MinAblationGain != 4 || r.MinNetGain != 2.5 ||
		!r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed ||
		r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized ||
		r.WholeProcessCostProven || r.MatchedComputeProven {
		t.Fatal("frozen protocol or scientific authority drift")
	}
	passing := 0
	for i, arm := range r.Arms {
		if arm.Seed != r.DevSeeds[i] || arm.Schedule != f33Worlds()[i].Schedule {
			t.Fatal("world identity")
		}
		bestHits, bestNet := 0, 0.0
		for j, tr := range arm.Trials {
			if tr.Kind != f33Kinds()[j] || tr.Opportunities != 48 || tr.ObservedTransitions != 96 ||
				tr.Interventions < 0 || tr.Interventions > 24 || tr.GoalsHit < 0 || tr.GoalsHit > 48 ||
				math.Abs(tr.NetReward-(float64(tr.GoalsHit)-.05*float64(tr.Interventions))) > 1e-10 ||
				len(tr.CheckpointSHA256) != 64 || len(tr.TerminalSHA256) != 64 ||
				len(tr.GoalsSHA256) != 64 || len(tr.ActionsSHA256) != 64 || len(tr.SensorsSHA256) != 64 ||
				len(tr.DecisionsSHA256) != 64 || !tr.ColdMatches ||
				tr.GoalsSHA256 != arm.Trials[0].GoalsSHA256 {
				t.Fatalf("invalid goal trace model %s seed %d", tr.Kind, arm.Seed)
			}
			sum := 0
			for _, v := range tr.PhaseHits {
				if v < 0 || v > 12 {
					t.Fatal("bad phase count")
				}
				sum += v
			}
			if sum != tr.GoalsHit {
				t.Fatal("phase counts not equal to total")
			}
			if j < 6 && (tr.TrainingSeen != 256 || tr.ModelParameters <= 0 || tr.OnlineWork <= 0 || tr.PlannerWork <= 0) {
				t.Fatal("untrained conventional planner or missing work")
			}
			if j >= 6 && (tr.Interventions > 24 || tr.ModelParameters != 0) {
				t.Fatal("unqualified negative policy")
			}
			if j >= 1 && j <= 3 {
				if tr.GoalsHit > bestHits {
					bestHits = tr.GoalsHit
				}
				if tr.NetReward > bestNet {
					bestNet = tr.NetReward
				}
			}
		}
		expect := arm.Trials[0].GoalsHit >= bestHits+3 &&
			arm.Trials[0].NetReward >= bestNet+2.5 &&
			arm.Trials[0].GoalsHit >= arm.Trials[4].GoalsHit+4 &&
			arm.Trials[0].GoalsHit >= arm.Trials[5].GoalsHit+4
		if expect != arm.Passes || bestHits != arm.BestConventionalHits || math.Abs(bestNet-arm.BestConventionalNet) > 1e-9 {
			t.Fatal("posthoc score classification")
		}
		if expect {
			passing++
		}
		t.Logf("F33_DEV seed=%d schedule=%s candidate=%d/48 interventions=%d net=%.2f best_trained=%d net=%.2f blind=%d cold_zero=%d random=%d always_zero=%d return=%d novel=%d PASS=%t",
			arm.Seed, arm.Schedule, arm.Trials[0].GoalsHit, arm.Trials[0].Interventions, arm.Trials[0].NetReward,
			bestHits, bestNet, arm.Trials[4].GoalsHit, arm.Trials[5].GoalsHit, arm.Trials[6].GoalsHit, arm.Trials[7].GoalsHit,
			arm.Trials[0].PhaseHits[2], arm.Trials[0].PhaseHits[3], expect)
	}
	expected := F33NoGo
	if passing == 4 {
		expected = F33Signal
	}
	if r.Classification != expected || r.Passing != passing {
		t.Fatal("incorrect frozen classification")
	}
	t.Logf("F33_FROZEN_DEV=%s passed=%d/4 SCIENTIFIC_PASS=false", r.Classification, passing)
}
func TestF33TrueDelayedConsequencesAndOverlap(t *testing.T) {
	w, e := f33NewWorld(367)
	if e != nil {
		t.Fatal(e)
	}
	start := w.State
	// In law A, cue2 has mask3 and lag3: the effect arrives at transition t2.
	for tstep := 0; tstep < 3; tstep++ {
		action := 0
		if tstep == 0 {
			action = 1
		}
		actual, _, e := w.step(tstep, 2, action)
		if e != nil {
			t.Fatal(e)
		}
		if tstep < 2 && actual != start {
			t.Fatal("consequence was not delayed")
		}
		if tstep == 2 && actual != start^3 {
			t.Fatal("credited delayed mask not applied")
		}
	}
	// Two separately issued events can mature on the same transition and XOR.
	other, e := f33NewWorld(367)
	if e != nil {
		t.Fatal(e)
	}
	original := other.State
	if _, _, e = other.step(0, 1, 1); e != nil {
		t.Fatal(e)
	} // cue1 mask2, lag2.
	both, _, e := other.step(1, 0, 1)
	if e != nil {
		t.Fatal(e)
	} // cue0 mask1, lag1.
	if both != original^2^1 {
		t.Fatal("overlapping causal events did not combine")
	}
	// Events emitted before a regime switch retain their source law's mask and lag.
	third, e := f33NewWorld(367)
	if e != nil {
		t.Fatal(e)
	}
	s := third.State
	for step := 0; step <= 25; step++ {
		a := 0
		if step == 23 {
			a = 1
		}
		got, _, e := third.step(step, 2, a)
		if e != nil {
			t.Fatal(e)
		}
		if step < 25 && got != s {
			t.Fatal("premature cross-regime event")
		}
		if step == 25 && got != s^3 {
			t.Fatal("previous-regime event lost or reinterpreted")
		}
	}
}
func TestF33PlannerNormalizedAndNoOracle(t *testing.T) {
	trained, e := f33Train()
	if e != nil {
		t.Fatal(e)
	}
	for i, m := range trained {
		w, e := f33NewWorld(367)
		if e != nil {
			t.Fatal(e)
		}
		if e = m.beginWorld(w.Sensors); e != nil {
			t.Fatal(e)
		}
		for a := 0; a <= 1; a++ {
			sum := 0.0
			for goal := 0; goal < 4; goal++ {
				prob, work, e := f33Plan(m, 1, 1, a, goal)
				if e != nil || math.IsNaN(prob) || math.IsInf(prob, 0) || prob < 0 || prob > 1+1e-9 || work <= 0 {
					t.Fatalf("model %d bad planner", i)
				}
				sum += prob
			}
			if math.Abs(sum-1) > 1e-8 {
				t.Fatalf("model %s improper next-target distribution %.9f", m.Kind, sum)
			}
		}
	}
	for _, seed := range []uint32{0, 59, 83, 301, 303, 331, 337, 347, 349, 353, 359, 364, 365, 369, 371, 3731, 385} {
		if _, e := f33NewWorld(seed); e == nil {
			t.Fatal("unknown or first-use seed admitted", seed)
		}
		if _, e := f33Goal(seed, 0); e == nil {
			t.Fatal("unknown goal seed admitted", seed)
		}
	}
	if _, e := f33Goal(367, 1); e == nil {
		t.Fatal("odd-step goal")
	}
	if _, e := f33Cue(367, "future", 0); e == nil {
		t.Fatal("unknown schedule")
	}
	if _, e := f33Phase(367, 96); e == nil {
		t.Fatal("future phase")
	}
	if _, e := f33Sensor(367, 0, 4, 0); e == nil {
		t.Fatal("invalid sensor target")
	}
}
func TestF33ColdWarmAndInvalidCheckpoint(t *testing.T) {
	tr, e := f33Train()
	if e != nil {
		t.Fatal(e)
	}
	for _, w := range f33Worlds() {
		for _, kind := range f33Kinds() {
			a, ar, e := f33Trial(tr, kind, w.Seed, w.Schedule, true)
			b, br, e2 := f33Trial(tr, kind, w.Seed, w.Schedule, false)
			if e != nil || e2 != nil || !reflect.DeepEqual(a, b) || !bytes.Equal(ar, br) {
				t.Fatalf("cold/warm different seed=%d kind=%s %v %v", w.Seed, kind, e, e2)
			}
		}
	}
	m := tr[0]
	raw, e := f32Save(m)
	if e != nil {
		t.Fatal(e)
	}
	corrupted := append([]byte(" "), raw...)
	if _, e = f32Load(corrupted); e == nil {
		t.Fatal("noncanonical model checkpoint accepted")
	}
}
func TestF33NegativeScienceAndScoreRelabeling(t *testing.T) {
	original, e := F33Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name string
		f    func(*F33Report)
	}{
		{"first-use", func(r *F33Report) { r.FirstUseConsumed = true }},
		{"science", func(r *F33Report) { r.ScientificAccepted = true }},
		{"owner", func(r *F33Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F33Report) { r.DispatchAuthorized = true }},
		{"matched-compute", func(r *F33Report) { r.MatchedComputeProven = true }},
		{"whole-cost", func(r *F33Report) { r.WholeProcessCostProven = true }},
		{"seed", func(r *F33Report) { r.DevSeeds[0] = 59 }},
		{"threshold", func(r *F33Report) { r.MinGoalsGain = 0 }},
		{"negative-custody", func(r *F33Report) { r.EarlierNegativesPreserved = false }},
		{"candidate-score", func(r *F33Report) { r.Arms[0].Trials[0].GoalsHit = 48 }},
		{"conventional-score", func(r *F33Report) { r.Arms[0].Trials[1].GoalsHit = 0 }},
		{"relabel", func(r *F33Report) { r.Classification = F33Signal }},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			raw, _ := json.Marshal(original)
			var cloned F33Report
			if json.Unmarshal(raw, &cloned) != nil {
				t.Fatal("copy")
			}
			c.f(&cloned)
			cloned.DigestSHA256 = f33Digest(cloned)
			if F33Validate(cloned) == nil {
				t.Fatal("tampered evidence accepted")
			}
		})
	}
}
