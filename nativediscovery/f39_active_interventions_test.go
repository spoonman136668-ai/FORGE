package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF39TrainingAndTrueInterventions(t *testing.T) {
	for _, seed := range []uint32{491, 499} {
		w, e := f39NewWorld(seed, "training")
		if e != nil {
			t.Fatal(e)
		}
		var cov [4][3]int
		for step := 0; step < 192; step++ {
			cue, e := f39Cue(seed, "training", step)
			if e != nil {
				t.Fatal(e)
			}
			action := f39TrainingAction(step)
			cov[cue][action]++
			phase, e := f39Phase(seed, step)
			if e != nil {
				t.Fatal(e)
			}
			base, ef1, ef2, e := f39Law(phase, cue)
			if e != nil {
				t.Fatal(e)
			}
			prior := w.S
			actual, _, e := w.step(step, cue, action)
			if e != nil {
				t.Fatal(e)
			}
			expected := base
			if action&1 != 0 {
				expected += ef1
			}
			if action&2 != 0 {
				expected += ef2
			}
			if actual != (prior+expected)%8 {
				t.Fatal("bad physical action consequence")
			}
		}
		for c := 0; c < 4; c++ {
			for a := 0; a < 3; a++ {
				if cov[c][a] != 16 {
					t.Fatal("incomplete real intervention coverage")
				}
			}
		}
	}
	// Untrained joint intervention must have different effects than each single intervention in some cue.
	found := false
	for c := 0; c < 4; c++ {
		b, a1, a2, _ := f39Law('A', c)
		if (b+a1+a2)%8 != (b+a1)%8 && (b+a1+a2)%8 != (b+a2)%8 {
			found = true
		}
	}
	if !found {
		t.Fatal("no genuine combined intervention")
	}
}
func TestF39NoOracleOrReservedFirstUse(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 251, 439, 501, 502, 504, 508, 510, 520, 522, 524} {
		if _, e := f39NewWorld(seed, "balanced"); e == nil {
			t.Fatal("unknown or first-use world accepted", seed)
		}
		if _, e := f39Goal(seed, 0); e == nil {
			t.Fatal("unknown or first-use goal accepted", seed)
		}
	}
	if _, e := f39Cue(503, "balanced", 96); e == nil {
		t.Fatal("future step accepted")
	}
	if _, e := f39Cue(491, "balanced", 0); e == nil {
		t.Fatal("wrong training schedule")
	}
	if _, e := f39Cue(503, "training", 0); e == nil {
		t.Fatal("wrong transfer schedule")
	}
	if _, e := f39Sensor(503, 0, 8, 0); e == nil {
		t.Fatal("unknown state")
	}
	if _, e := f39Posterior([2]int{8, 0}); e == nil {
		t.Fatal("bad sensor accepted")
	}
	if _, e := f39New("oracle"); e == nil {
		t.Fatal("invalid controller accepted")
	}
}
func TestF39ColdCheckpointsAndActionExposure(t *testing.T) {
	m, e := f39Train("uncertainty-directed")
	if e != nil {
		t.Fatal(e)
	}
	raw, e := f39Save(m)
	if e != nil {
		t.Fatal(e)
	}
	restored, e := f39Load(raw)
	if e != nil || !reflect.DeepEqual(m, restored) {
		t.Fatal("source cold restore drift")
	}
	corrupted := append([]byte(nil), raw...)
	corrupted[0] = '['
	if _, e := f39Load(corrupted); e == nil {
		t.Fatal("bad checkpoint accepted")
	}
	if _, e := f39Load(append([]byte(" "), raw...)); e == nil {
		t.Fatal("noncanonical checkpoint accepted")
	}
	for _, world := range f39Worlds() {
		c, cb, e := f39Trial(m, world.Seed, world.Schedule, true)
		if e != nil {
			t.Fatal(e)
		}
		warm, wb, e := f39Trial(m, world.Seed, world.Schedule, false)
		if e != nil || !reflect.DeepEqual(c, warm) || !bytes.Equal(cb, wb) {
			t.Fatal("cold/warm mismatch", world.Seed)
		}
		if c.TransferSeen != 96 || c.Interventions > 48 || c.CheckpointSHA256 != f39SHA256(raw) || len(c.SensorsSHA256) != 64 || len(c.ActionsSHA256) != 64 {
			t.Fatal("custody mismatch")
		}
	}
}
func TestF39FrozenDevelopmentAndSourceControls(t *testing.T) {
	r, e := F39Development()
	if e != nil {
		t.Fatal(e)
	}
	if F39Validate(r) != nil {
		t.Fatal("development not revalidated")
	}
	if r.Schema != F39Schema || r.Parent != F39Parent || r.TrainingStepsPerWorld != 192 || r.TransferSteps != 96 || r.MinGoalGain != 4 || r.MinNovelGain != 3 || r.MinAblationGain != 4 || r.MaxInterventions != 48 || r.Bonus != .08 || r.Hazard != .03 || r.MaxWorkRatio != 1.25 || !r.EarlierNegativesPreserved || !r.DevelopmentOnly || len(r.SourceTraceSHA256) != 64 {
		t.Fatal("frozen protocol drift")
	}
	passed := 0
	for i, world := range r.Worlds {
		if world.Seed != f39Worlds()[i].Seed || world.Schedule != f39Worlds()[i].Schedule {
			t.Fatal("seed or schedule drift")
		}
		sumScore := 0
		for j, tr := range world.Trials {
			if tr.Kind != f39Kinds()[j] || tr.Interventions > 48 || tr.TransferSeen != 96 || tr.TrainingSeen != 384 || tr.Parameters != 412 || tr.Work <= 0 || len(tr.ActionsSHA256) != 64 || len(tr.SensorsSHA256) != 64 || len(tr.CheckpointSHA256) != 64 || len(tr.TerminalSHA256) != 64 || !tr.ColdMatches {
				t.Fatal("trial invalid", tr.Kind)
			}
			phaseTotal := 0
			for _, n := range tr.PhaseGoals {
				if n < 0 || n > 24 {
					t.Fatal("bad phase goal count")
				}
				phaseTotal += n
			}
			if phaseTotal != tr.Goals {
				t.Fatal("phase mismatch")
			}
			if j == 0 {
				sumScore = tr.Goals
			}
		}
		bestIndex := 1
		maxReturn, maxNovel := 0, 0
		for j := 1; j <= 3; j++ {
			if world.Trials[j].Goals > world.Trials[bestIndex].Goals {
				bestIndex = j
			}
			maxReturn = int(math.Max(float64(maxReturn), float64(world.Trials[j].PhaseGoals[2])))
			maxNovel = int(math.Max(float64(maxNovel), float64(world.Trials[j].PhaseGoals[3])))
		}
		valid := world.Trials[0].Goals >= world.Trials[bestIndex].Goals+4 && world.Trials[0].PhaseGoals[2] >= maxReturn && world.Trials[0].PhaseGoals[3] >= maxNovel+3 && world.Trials[0].Goals >= world.Trials[4].Goals+4 && world.Trials[0].Goals >= world.Trials[5].Goals+4 && float64(world.Trials[0].Work) <= 1.25*float64(world.Trials[bestIndex].Work)
		if valid != world.Passes || world.GainGoals != sumScore-world.BestConventionalGoals {
			t.Fatal("incorrect classification")
		}
		if valid {
			passed++
		}
		t.Logf("F39_DEV world=%d %s candidate=%d strongest=%d gain=%+d return=%d/%d novel=%d/%d wrong_action=%d cold_zero=%d work=%d/%d pass=%v", world.Seed, world.Schedule, world.Trials[0].Goals, world.BestConventionalGoals, world.GainGoals, world.Trials[0].PhaseGoals[2], maxReturn, world.Trials[0].PhaseGoals[3], maxNovel, world.Trials[4].Goals, world.Trials[5].Goals, world.Trials[0].Work, world.Trials[bestIndex].Work, valid)
	}
	status := F39NoGo
	if passed == 4 {
		status = F39Signal
	}
	if r.Passing != passed || r.Classification != status {
		t.Fatal("result label tampered")
	}
	t.Logf("F39_FROZEN_DEV=%s passing=%d/4 first_use=false science=false", status, passed)
}
func TestF39RejectFalseScientificClaims(t *testing.T) {
	original, e := F39Development()
	if e != nil {
		t.Fatal(e)
	}
	tests := []struct {
		Name  string
		Apply func(*F39Report)
	}{
		{"first-use", func(r *F39Report) { r.FirstUseConsumed = true }},
		{"science", func(r *F39Report) { r.ScientificAccepted = true }},
		{"owner", func(r *F39Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F39Report) { r.DispatchAuthorized = true }},
		{"compute", func(r *F39Report) { r.MatchedWholeProcessComputeProven = true }},
		{"fake-gain", func(r *F39Report) { r.Worlds[0].Trials[0].Goals = 96 }},
		{"fake-source", func(r *F39Report) { r.SourceTraceSHA256 = "faked" }},
		{"fake-label", func(r *F39Report) { r.Classification = F39Signal }},
		{"fake-threshold", func(r *F39Report) { r.MinGoalGain = 0 }},
		{"fake-seed", func(r *F39Report) { r.TransferSeeds[0] = 59 }},
		{"erase-negatives", func(r *F39Report) { r.EarlierNegativesPreserved = false }},
	}
	for _, tc := range tests {
		t.Run(tc.Name, func(t *testing.T) {
			b, _ := json.Marshal(original)
			var v F39Report
			if json.Unmarshal(b, &v) != nil {
				t.Fatal("report copy failed")
			}
			tc.Apply(&v)
			v.DigestSHA256 = f39Digest(v)
			if F39Validate(v) == nil {
				t.Fatal("forged report admitted")
			}
		})
	}
}
