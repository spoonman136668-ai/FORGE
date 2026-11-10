package nativediscovery

import (
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF38FrozenDevelopment(t *testing.T) {
	r, e := F38Development()
	if e != nil || F38Validate(r) != nil {
		t.Fatal("development invalid", e)
	}
	if r.Schema != F38Schema || r.Parent != F38Parent || r.TrainingSteps != 384 || r.Epsilon != F37Epsilon || r.MinSensorGain != .05 || r.MinGoalGain != 2 || r.MinNetGain != 1.5 || r.Seeds != [4]uint32{461, 463, 467, 479} {
		t.Fatal("frozen dev setup drift")
	}
	cal, control := 0, 0
	for i, w := range r.Worlds {
		if w.Seed != r.Seeds[i] || w.Schedule != f38Worlds()[i].Schedule {
			t.Fatal("seed drift")
		}
		for j, comp := range w.Matched {
			if comp.Family != f38Kinds()[j] || comp.Legacy.Model != comp.Calibrated.Model || comp.Legacy.ActionsSHA256 != comp.Calibrated.ActionsSHA256 || comp.Legacy.SensorsSHA256 != comp.Calibrated.SensorsSHA256 || comp.Legacy.GoalsSHA256 != comp.Calibrated.GoalsSHA256 {
				t.Fatalf("paired mismatch %d %d", i, j)
			}
			if comp.Legacy.TrainingTransitions != 384 || comp.Calibrated.TrainingTransitions != 384 || comp.Calibrated.Unsupported != 0 {
				t.Fatal("training/support drift")
			}
			if comp.SensorNLLGain != comp.Legacy.MeanSensorNLL-comp.Calibrated.MeanSensorNLL || math.IsNaN(comp.SensorNLLGain) {
				t.Fatal("arithmetic invalid")
			}
			pass := comp.SensorNLLGain >= .05 && comp.Calibrated.Unsupported == 0 && comp.Legacy.LegacyFallbacks > 0
			if comp.Passes != pass {
				t.Fatal("pass forged")
			}
			if pass {
				cal++
			}
		}
		bestHits, bestNet := 0, 0.0
		for j, tr := range w.OnPolicy {
			if tr.Model != f38Kinds()[j] || tr.Actions > 36 || tr.GoalHits > 24 || tr.TrainingTransitions != 384 || tr.GoalHits < 0 || tr.Actions < 0 || len(tr.GoalsSHA256) != 64 || len(tr.ActionsSHA256) != 64 || len(tr.SensorsSHA256) != 64 || len(tr.TerminalSHA256) != 64 || len(tr.CheckpointSHA256) != 64 || len(tr.MidCheckpointSHA256) != 64 {
				t.Fatalf("trial invalid %d %s", i, tr.Model)
			}
			if j >= 1 && j <= 3 {
				if tr.GoalHits > bestHits {
					bestHits = tr.GoalHits
				}
				if tr.NetReward > bestNet {
					bestNet = tr.NetReward
				}
			}
			if tr.GoalsSHA256 != w.OnPolicy[0].GoalsSHA256 {
				t.Fatal("goal drift")
			}
			if tr.NetReward != float64(tr.GoalHits)-.03*float64(tr.Actions) {
				t.Fatal("incorrect reward")
			}
		}
		if bestHits != w.BestConventionalHits || bestNet != w.BestConventionalNet {
			t.Fatal("strongest control incorrect")
		}
		ca, two := w.OnPolicy[0], w.OnPolicy[1]
		ok := ca.GoalHits >= bestHits+2 && ca.NetReward >= bestNet+1.5 && float64(ca.Work) <= float64(two.Work)*1.10
		if ok != w.CandidateGoalPass {
			t.Fatal("goal result mislabeled")
		}
		if ok {
			control++
		}
		t.Logf("F38_DEV seed=%d cal_four=%.5f cal_two=%.5f four_goals=%d two_goals=%d best=%d four_work=%d two_work=%d goal_pass=%v", w.Seed, w.Matched[0].SensorNLLGain, w.Matched[1].SensorNLLGain, ca.GoalHits, two.GoalHits, bestHits, ca.Work, two.Work, ok)
	}
	if r.PassingCalibration != cal || r.PassingControl != control || r.CalibrationPass != (cal == 8) || r.ControlPass != (control == 4) {
		t.Fatal("classification drift")
	}
	expected := F38NoGo
	if cal == 8 && control == 4 {
		expected = F38Signal
	}
	if r.Classification != expected {
		t.Fatal("classification forged")
	}
	t.Logf("F38_FROZEN_DEV=%s calibrated=%d/8 goal_control=%d/4", expected, cal, control)
}
func TestF38DistinctWorldsGenuineDelayedEffects(t *testing.T) {
	for _, spec := range f38Worlds() {
		w, e := f38NewWorld(spec.Seed, spec.Schedule)
		if e != nil {
			t.Fatal(e)
		}
		pendingProof := 0
		for i := 0; i < 96; i++ {
			c, e := f38Cue(spec, i)
			if e != nil {
				t.Fatal(e)
			}
			a := 0
			if i%3 == 0 {
				a = i%2 + 1
			}
			before := w.State
			// Independently compute physical register difference from original issued and due action records.
			original := append([]f36Event(nil), w.Pending...)
			law, e := f38Phase(spec, i)
			if e != nil {
				t.Fatal(e)
			}
			if a > 0 {
				tbl, e := f36Law(law)
				if e != nil {
					t.Fatal(e)
				}
				sp := tbl[c][a-1]
				original = append(original, f36Event{Due: i + sp.Lag - 1, Mask: sp.Mask})
			}
			expected := before
			for _, ev := range original {
				if ev.Due == i {
					expected ^= ev.Mask
				}
				if ev.Due > i {
					pendingProof++
				}
			}
			clean, next, e := w.step(i, c, a)
			if e != nil || clean != expected || clean != w.State || next != w.Sensors {
				t.Fatal("physical action-consequence contradiction")
			}
		}
		if pendingProof == 0 {
			t.Fatal("no delayed actions tested")
		}
		// Hidden source laws should differ from at least one unseen combination.
		a, _ := f36Law('A')
		b, _ := f36Law('B')
		c, _ := f36Law('C')
		d, _ := f36Law('D')
		if reflect.DeepEqual(a, c) || reflect.DeepEqual(b, d) {
			t.Fatal("novel law not distinct")
		}
	}
}
func TestF38RejectFirstUseAndForgedEvidence(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 431, 433, 439, 443, 449, 457, 460, 462, 466, 478, 480} {
		if _, e := f38NewWorld(seed, "balanced"); e == nil {
			t.Fatal("unknown or prior seed admitted", seed)
		}
	}
	if _, e := f38NewWorld(461, "skewed"); e == nil {
		t.Fatal("wrong schedule admitted")
	}
	valid, e := F38Development()
	if e != nil {
		t.Fatal(e)
	}
	mutations := []struct {
		name   string
		modify func(*F38Report)
	}{
		{"science", func(v *F38Report) { v.ScientificAccepted = true }},
		{"first_use", func(v *F38Report) { v.FirstUseConsumed = true }},
		{"owner", func(v *F38Report) { v.OwnerEligible = true }},
		{"dispatch", func(v *F38Report) { v.DispatchAuthorized = true }},
		{"matched_compute", func(v *F38Report) { v.MatchedComputeProven = true }},
		{"seeds", func(v *F38Report) { v.Seeds[0] = 59 }},
		{"threshold", func(v *F38Report) { v.MinSensorGain = 0 }},
		{"scores", func(v *F38Report) { v.Worlds[0].OnPolicy[0].GoalHits = 24 }},
		{"goal", func(v *F38Report) { v.Worlds[0].OnPolicy[0].Actions = 0 }},
		{"result", func(v *F38Report) { v.Classification = F38Signal }},
		{"negatives", func(v *F38Report) { v.PreviousNegativesPreserved = false }},
	}
	for _, tc := range mutations {
		t.Run(tc.name, func(t *testing.T) {
			raw, _ := json.Marshal(valid)
			var copy F38Report
			if e := json.Unmarshal(raw, &copy); e != nil {
				t.Fatal(e)
			}
			tc.modify(&copy)
			copy.DigestSHA256 = f38Digest(copy)
			if F38Validate(copy) == nil {
				t.Fatal("forged claim admitted")
			}
		})
	}
}
func TestF38ColdRestoreAndUnsupportedAction(t *testing.T) {
	archive, e := f36Train()
	if e != nil {
		t.Fatal(e)
	}
	logistic, e := f36TrainLogistic()
	if e != nil {
		t.Fatal(e)
	}
	for _, kind := range []string{"compositional-issued-memory", "two-bank-issued-bayes", "pooled-issued-bayes", "history-logistic", "always-zero"} {
		eps := F37Epsilon
		if kind == "history-logistic" || kind == "always-zero" {
			eps = 0
		}
		warm, _, wt, e := f38Trial(archive, logistic, kind, 461, "balanced", eps, nil, false)
		cold, _, ct, e2 := f38Trial(archive, logistic, kind, 461, "balanced", eps, nil, true)
		if e != nil || e2 != nil || !reflect.DeepEqual(warm, cold) || !reflect.DeepEqual(wt, ct) {
			t.Fatal("cold replay drift", kind, e, e2)
		}
	}
	if _, _, _, e := f38Trial(archive, logistic, "two-bank-issued-bayes", 59, "balanced", F37Epsilon, nil, false); e == nil {
		t.Fatal("first use admitted")
	}
	if _, _, _, e := f38Trial(archive, logistic, "two-bank-issued-bayes", 461, "balanced", .1, nil, false); e == nil {
		t.Fatal("unfrozen epsilon admitted")
	}
}
