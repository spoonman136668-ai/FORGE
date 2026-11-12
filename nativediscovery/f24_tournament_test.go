package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF24FrozenFourArmDevelopment(t *testing.T) {
	r, err := F24Development()
	if err != nil || F24Validate(r) != nil {
		t.Fatal("frozen source-bound development failed", err)
	}
	if r.Schema != F24Schema || r.Parent != F24F23Parent || r.Seeds != [2]uint32{163, 167} ||
		r.Schedules != [2]string{"balanced", "skewed"} || r.Actions != 128 || r.Budget != 12 ||
		r.Checkpoints != [4]int{96, 104, 112, 120} || r.MinimumGain != 2 || r.MinimumAblationGain != 3 ||
		!r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven {
		t.Fatal("protocol/authority drift")
	}
	passed := 0
	for i, arm := range r.Arms {
		if arm.Seed != r.Seeds[i/2] || arm.Schedule != r.Schedules[i%2] {
			t.Fatal("seed/schedule drift")
		}
		if arm.Trials[0].Score > 32 || arm.Trials[0].Score < 0 || arm.Trials[0].Spent > 12 {
			t.Fatal("scoring/budget invalid")
		}
		for j, trial := range arm.Trials {
			if trial.Kind != f24Kinds()[j] || trial.Credits != 126 || trial.Pending != 2 || trial.Spent < 0 || trial.Spent > 12 ||
				!trial.ColdMatches || trial.Work < 1 || len(trial.Trace) != 32 || len(trial.FinalSHA256) != 64 ||
				len(trial.CheckpointSHA256) != 64 || len(trial.ActionsSHA256) != 64 {
				t.Fatal("trial provenance invalid")
			}
			score := 0
			for _, v := range trial.Checkpoints {
				score += v
			}
			bits := 0
			for _, v := range trial.Trace {
				if v == '1' {
					bits++
				} else if v != '0' {
					t.Fatal("nonbinary score trace")
				}
			}
			if score != trial.Score || bits != score {
				t.Fatal("scorer incongruent")
			}
		}
		best := 0
		for j := 1; j <= 6; j++ {
			if arm.Trials[j].Score > best {
				best = arm.Trials[j].Score
			}
		}
		valid := arm.Trials[0].Score >= best+2 && arm.Trials[0].Score >= arm.Trials[7].Score+3 &&
			arm.Trials[0].Score >= arm.Trials[8].Score+3 && arm.Trials[0].Spent >= 2 && arm.Trials[0].Spent <= 12
		if arm.Passes != valid {
			t.Fatal("hindsight or loss relabeled")
		}
		if valid {
			passed++
		}
		t.Logf("F24_DEV seed=%d schedule=%s candidate=%d/32 controls=%v best=%d gain=%+d ablations(no/wrong)=%d/%d spent=%d PASS=%v",
			arm.Seed, arm.Schedule, arm.Trials[0].Score,
			[6]int{arm.Trials[1].Score, arm.Trials[2].Score, arm.Trials[3].Score, arm.Trials[4].Score, arm.Trials[5].Score, arm.Trials[6].Score},
			best, arm.GainStrong, arm.Trials[7].Score, arm.Trials[8].Score, arm.Trials[0].Spent, valid)
	}
	classify := F24NoGo
	if passed == 4 {
		classify = F24Signal
	}
	if classify != r.Classification || passed != r.Passing {
		t.Fatal("frozen classification mismatch")
	}
	t.Logf("F24_FROZEN_DEV=%s passing=%d/4 first_use=false science_accepted=false", r.Classification, r.Passing)
}
func TestF24NoOracleAndSealedSeedRejection(t *testing.T) {
	for _, seed := range []uint32{0, 17, 31, 59, 83, 151, 157, 162, 164, 166, 168} {
		if _, e := f24Laws(seed); e == nil {
			t.Fatal("unknown/first-use world accepted")
		}
		if _, e := f24Cue(seed, "balanced", 0); e == nil {
			t.Fatal("seed oracle accepted")
		}
		if _, e := f24Observation(seed, 0, 0, 0); e == nil {
			t.Fatal("outcome oracle accepted")
		}
		if _, _, e := f24Select(nil, 0, 0, 0, seed, "tournament"); e == nil {
			t.Fatal("source invalid")
		}
	}
	for _, bad := range []string{"oracle", "random-policy", "", "phase"} {
		if _, e := f24Cue(163, bad, 0); e == nil {
			t.Fatal("policy admitted")
		}
	}
	for _, bad := range []string{"oracle", "regime-belief", "", "full-bayes"} {
		if _, _, e := f24Select(nil, 0, 0, 0, 163, bad); e == nil {
			t.Fatal("nonpolicy admitted")
		}
	}
	if _, _, e := f24Select(nil, 4, 0, 0, 163, "tournament"); e == nil {
		t.Fatal("bad cue")
	}
	if _, _, e := f24Select(nil, 0, 128, 0, 163, "tournament"); e == nil {
		t.Fatal("future step")
	}
	if _, _, e := f24Select(nil, 0, 1, 13, 163, "tournament"); e == nil {
		t.Fatal("budget bypass")
	}
	bad := []f20Credit{{Step: 0, Cue: 0, Action: 2, WrongAction: 0, Value: 1}}
	if _, _, e := f24Fit(bad, false); e == nil {
		t.Fatal("forged action admitted")
	}
}
func TestF24ColdRestartAndCreditedOnly(t *testing.T) {
	for _, seed := range f24Seeds() {
		for _, schedule := range f24Schedules() {
			for _, kind := range f24Kinds() {
				cold, checkpoint, coldFinal, e := f24Run(seed, schedule, kind, true)
				warm, warmCheckpoint, warmFinal, e2 := f24Run(seed, schedule, kind, false)
				if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(checkpoint, warmCheckpoint) || !bytes.Equal(coldFinal, warmFinal) {
					t.Fatal("cold/warm divergence")
				}
				s, e := f24Load(checkpoint)
				if e != nil || s.Seen != 96 || len(s.Credits) != 94 || len(s.Pending) != 2 || s.Pending[0].Step != 94 || s.Pending[1].Step != 95 {
					t.Fatal("delayed checkpoint")
				}
				s, e = f24Load(coldFinal)
				if e != nil || s.Seen != 128 || len(s.Credits) != 126 || len(s.Pending) != 2 || s.Pending[0].Step != 126 || s.Pending[1].Step != 127 {
					t.Fatal("final pending invalid")
				}
				if s.Work != cold.Work || len(s.ScoreTrace) != 32 {
					t.Fatal("work or score dropped")
				}
				// Reordered, rehashed and noncanonical checkpoints are never admitted.
				corrupted := append([]byte(nil), checkpoint...)
				corrupted[0] = '['
				if _, e := f24Load(corrupted); e == nil {
					t.Fatal("corrupted checkpoint")
				}
				compact := append([]byte(" "), checkpoint...)
				if _, e := f24Load(compact); e == nil {
					t.Fatal("noncanonical checkpoint")
				}
				if len(s.Credits) > 4 {
					s.Credits[0], s.Credits[1] = s.Credits[1], s.Credits[0]
					if _, e := f24Save(s); e == nil {
						t.Fatal("reordered credits")
					}
				}
			}
		}
	}
}
func TestF24ReportRehashCannotForgeScienceOrNegatives(t *testing.T) {
	base, e := F24Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name   string
		mutate func(*F24Report)
	}{
		{"science", func(r *F24Report) { r.ScientificAccepted = true }},
		{"first_use", func(r *F24Report) { r.FirstUseConsumed = true }},
		{"owner", func(r *F24Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F24Report) { r.DispatchAuthorized = true }},
		{"cost", func(r *F24Report) { r.WholeProcessCostProven = true }},
		{"seeds", func(r *F24Report) { r.Seeds[0] = 59 }},
		{"frozen_threshold", func(r *F24Report) { r.MinimumGain = 0 }},
		{"scorer", func(r *F24Report) { r.Arms[0].Trials[0].Score = 32 }},
		{"baseline_erasure", func(r *F24Report) { r.Arms[0].Trials[1].Score = 0 }},
		{"reorder", func(r *F24Report) { r.Arms[0], r.Arms[1] = r.Arms[1], r.Arms[0] }},
		{"relabel", func(r *F24Report) { r.Classification = F24Signal }},
		{"negative_erasure", func(r *F24Report) { r.EarlierNegativesPreserved = false }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b, _ := json.Marshal(base)
			var r F24Report
			if json.Unmarshal(b, &r) != nil {
				t.Fatal("copy failed")
			}
			tc.mutate(&r)
			r.DigestSHA256 = f24Digest(r)
			if F24Validate(r) == nil {
				t.Fatal("mutated report accepted")
			}
		})
	}
}
