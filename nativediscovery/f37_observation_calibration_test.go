package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF37FrozenCalibration(t *testing.T) {
	r, e := F37Development()
	if e != nil || F37Validate(r) != nil {
		t.Fatal("frozen audit failed", e)
	}
	if r.Schema != F37Schema || r.Parent != F37Parent || r.TrainingSteps != 384 || r.Epsilon != .025 || r.MinSensorNLLGain != .05 || r.TrainingSHA256 == "" {
		t.Fatal("protocol drift")
	}
	passing := 0
	for i, world := range r.Worlds {
		if world.Seed != f36Worlds()[i].Seed || world.Schedule != f36Worlds()[i].Schedule {
			t.Fatal("world drift")
		}
		for j, c := range world.Comparisons {
			want := "compositional-issued-memory"
			if j == 1 {
				want = "two-bank-issued-bayes"
			}
			if c.Model != want || c.Legacy.Model != want || c.Calibrated.Model != want || c.CalibratedOnPolicy.Model != want {
				t.Fatal("wrong control")
			}
			a, b := c.Legacy, c.Calibrated
			if a.Epsilon != 0 || b.Epsilon != F37Epsilon || a.ActionsSHA256 != b.ActionsSHA256 || a.SensorsSHA256 != b.SensorsSHA256 || a.GoalsSHA256 != b.GoalsSHA256 {
				t.Fatal("mismatched physical exposure")
			}
			if a.GoalHits != b.GoalHits || a.GoalHits != c.OriginalF36Goals || a.NonzeroActions != b.NonzeroActions || a.NonzeroActions > 36 || c.CalibratedOnPolicy.NonzeroActions > 36 {
				t.Fatal("action cap or trace drift")
			}
			if len(a.TerminalSHA256) != 64 || len(b.TerminalSHA256) != 64 || len(c.CalibratedOnPolicy.TerminalSHA256) != 64 || len(a.MidCheckpointSHA256) != 64 || len(b.MidCheckpointSHA256) != 64 {
				t.Fatal("missing custody")
			}
			for _, trial := range []F37Trial{a, b, c.CalibratedOnPolicy} {
				if math.IsNaN(trial.MeanSensorNLL) || math.IsInf(trial.MeanSensorNLL, 0) || trial.MeanSensorNLL < 0 || !trial.ColdMatches {
					t.Fatal("invalid NLL or cold")
				}
			}
			good := a.MeanSensorNLL-b.MeanSensorNLL >= .05 && b.ZeroProbabilityUpdates == 0 && a.LegacyFallbacks > 0
			if good != c.Passes || math.Abs(c.SensorNLLGain-(a.MeanSensorNLL-b.MeanSensorNLL)) > 1e-10 {
				t.Fatal("false pass")
			}
			if good {
				passing++
			}
			t.Logf("F37_DEV seed=%d policy=%s legacy_nll=%.6f calibrated_nll=%.6f gain=%+.6f legacy_fallbacks=%d calibrated_zero=%d on_policy_hits=%d original_hits=%d pass=%v", world.Seed, want, a.MeanSensorNLL, b.MeanSensorNLL, c.SensorNLLGain, a.LegacyFallbacks, b.ZeroProbabilityUpdates, c.CalibratedOnPolicy.GoalHits, c.OriginalF36Goals, good)
		}
	}
	classification := F37CalNoGo
	if passing == 8 {
		classification = F37CalSignal
	}
	if r.Classification != classification || r.PassingPairs != passing {
		t.Fatal("wrong classification")
	}
	t.Logf("F37_FROZEN_DEV=%s passing=%d/8 digest=%s", classification, passing, r.DigestSHA256)
}
func TestF37ProperBeliefAndLikelihood(t *testing.T) {
	archive, e := f36Train()
	if e != nil {
		t.Fatal(e)
	}
	for _, w := range f36Worlds() {
		world, e := f36NewWorld(w.Seed)
		if e != nil {
			t.Fatal(e)
		}
		m, e := f36Init(archive, "compositional-issued-memory", world.Sensors)
		if e != nil {
			t.Fatal(e)
		}
		for i := 0; i < 96; i++ {
			cue, e := f36Cue(w.Seed, w.Schedule, i)
			if e != nil {
				t.Fatal(e)
			}
			action := 0
			if i%4 == 0 {
				action = 1
			} else if i%4 == 1 {
				action = 2
			}
			_, obs, e := world.step(i, cue, action)
			if e != nil {
				t.Fatal(e)
			}
			_, z, p, e := f37Evidence(m, i, cue, action, obs, F37Epsilon)
			if e != nil || p <= 0 || p > 1 {
				t.Fatal("nonpositive sensor evidence")
			}
			for _, v := range z {
				if v <= 0 {
					t.Fatal("nonpositive hypothesis evidence")
				}
			}
			if e := f37CalibratedObserve(&m, i, cue, action, obs); e != nil {
				t.Fatal(e)
			}
			weights := 0.0
			for k, x := range m.Weights {
				if x < 0 || x > 1 {
					t.Fatal("weight invalid")
				}
				weights += x
				s := 0.0
				for _, v := range m.Beliefs[k] {
					if v < 0 || v > 1 {
						t.Fatal("belief invalid")
					}
					s += v
				}
				if math.Abs(s-1) > 1e-9 {
					t.Fatal("posterior not normalized")
				}
				for _, evt := range m.Events[k] {
					if evt.Due <= i || evt.Mask < 1 || evt.Mask > 15 {
						t.Fatal("event not preserved")
					}
				}
			}
			if math.Abs(weights-1) > 1e-9 || m.FloorHits != 0 {
				t.Fatal("weights wrong or fallback invented")
			}
		}
	}
}
func TestF37ColdRestorationAndFirstUse(t *testing.T) {
	a, e := f36Train()
	if e != nil {
		t.Fatal(e)
	}
	for _, seed := range []uint32{0, 59, 83, 431, 433, 441, 459} {
		if _, _, _, e := f37Trial(a, "compositional-issued-memory", seed, "balanced", F37Epsilon, nil, true); e == nil {
			t.Fatal("unauthorized seed", seed)
		}
	}
	if _, _, _, e := f37Trial(a, "untrained-oracle", 439, "balanced", F37Epsilon, nil, true); e == nil {
		t.Fatal("unauthorized model")
	}
	if _, _, _, e := f37Trial(a, "compositional-issued-memory", 439, "skewed", F37Epsilon, nil, true); e == nil {
		t.Fatal("wrong schedule")
	}
	if _, _, _, e := f37Trial(a, "compositional-issued-memory", 439, "balanced", .026, nil, true); e == nil {
		t.Fatal("epsilon retuned")
	}
	for _, world := range f36Worlds() {
		for _, kind := range []string{"compositional-issued-memory", "two-bank-issued-bayes"} {
			warm, actions, buf, e := f37Trial(a, kind, world.Seed, world.Schedule, F37Epsilon, nil, false)
			if e != nil {
				t.Fatal(e)
			}
			cold, _, cbuf, e := f37Trial(a, kind, world.Seed, world.Schedule, F37Epsilon, nil, true)
			if e != nil || !reflect.DeepEqual(warm, cold) || !bytes.Equal(buf, cbuf) {
				t.Fatal("midworld cold mismatch")
			}
			if len(actions) != 96 || len(warm.ActionsSHA256) != 64 {
				t.Fatal("trace missing")
			}
		}
	}
}
func TestF37RejectScientificAndScoreForgery(t *testing.T) {
	r, e := F37Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []func(*F37Report){
		func(p *F37Report) { p.ScientificAccepted = true }, func(p *F37Report) { p.FirstUseConsumed = true }, func(p *F37Report) { p.OwnerEligible = true }, func(p *F37Report) { p.DispatchAuthorized = true }, func(p *F37Report) { p.MatchedComputeProven = true },
		func(p *F37Report) { p.Epsilon = .03 }, func(p *F37Report) { p.MinSensorNLLGain = 0 }, func(p *F37Report) { p.Seeds[0] = 59 }, func(p *F37Report) { p.Worlds[0].Comparisons[0].Calibrated.MeanSensorNLL = 0 }, func(p *F37Report) { p.Worlds[0].Comparisons[0].CalibratedOnPolicy.GoalHits = 24 }, func(p *F37Report) { p.PreviousNegativesPreserved = false }, func(p *F37Report) { p.Classification = F37CalSignal },
	}
	for i, change := range cases {
		b, _ := json.Marshal(r)
		var c F37Report
		if json.Unmarshal(b, &c) != nil {
			t.Fatal("copy")
		}
		change(&c)
		c.DigestSHA256 = f37Digest(c)
		if F37Validate(c) == nil {
			t.Fatal("forged report accepted", i)
		}
	}
}
