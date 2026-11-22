package nativediscovery

import (
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF36FrozenDevelopment(t *testing.T) {
	r, e := F36Development()
	if e != nil {
		t.Fatal(e)
	}
	if F36Validate(r) != nil {
		t.Fatal("frozen score invalid")
	}
	if r.TrainingSeeds != [2]uint32{431, 433} || r.TransferSeeds != [4]uint32{439, 443, 449, 457} || !r.DevelopmentOnly || !r.PriorNegativesPreserved {
		t.Fatal("frozen custody")
	}
	passing := 0
	for _, a := range r.Arms {
		for bi := 0; bi < 2; bi++ {
			for c := 0; c < 4; c++ {
				for ai := 0; ai < 2; ai++ {
					if r.Coverage[bi][c][ai] != 4 {
						t.Fatal("not covered")
					}
				}
			}
		}
		bestHits := 0
		bestNet := math.Inf(-1)
		for j, x := range a.Trials {
			if x.Kind != f36Kinds()[j] || x.Hits < 0 || x.Hits > 24 || x.Actions < 0 || x.Actions > 36 || x.GoalsSHA256 != a.Trials[0].GoalsSHA256 || len(x.TerminalSHA256) != 64 || !x.ColdMatches {
				t.Fatal("trial custody", a.Seed, x.Kind)
			}
			if j >= 1 && j <= 3 {
				if x.Hits > bestHits {
					bestHits = x.Hits
				}
				if x.NetReward > bestNet {
					bestNet = x.NetReward
				}
			}
		}
		yes := a.Trials[0].Hits >= bestHits+2 && a.Trials[0].NetReward >= bestNet+1.5 && a.Trials[0].Hits >= a.Trials[4].Hits+2 && a.Trials[0].Hits >= a.Trials[5].Hits+2
		if a.Passes != yes || a.BestConventionalHits != bestHits || a.BestConventionalNet != bestNet {
			t.Fatal("false winner")
		}
		if yes {
			passing++
		}
		t.Logf("F36_DEV seed=%d candidate=%d best_conventional=%d drop=%d coldzero=%d gain=%+d pass=%v", a.Seed, a.Trials[0].Hits, bestHits, a.Trials[4].Hits, a.Trials[5].Hits, a.Trials[0].Hits-bestHits, yes)
	}
	if passing != r.Passing {
		t.Fatal("false passing")
	}
	want := F36NoGo
	if passing == 4 {
		want = F36Signal
	}
	if r.Classification != want {
		t.Fatal("false classification")
	}
	t.Log("F36_FROZEN", r.Classification, "passing", passing, "/4 digest", r.DigestSHA256)
}
func TestF36PhysicalActionCustodyAndSimultaneity(t *testing.T) {
	for _, seed := range []uint32{431, 433, 439, 443, 449, 457} {
		w, e := f36NewWorld(seed)
		if e != nil {
			t.Fatal(e)
		}
		limit := 96
		if seed == 431 || seed == 433 {
			limit = 192
		}
		for t0 := 0; t0 < limit; t0++ {
			c, a := t0%4, 0
			if t0%4 == 0 {
				a = 1
			} else if t0%4 == 1 {
				a = 2
			}
			old := w.State
			dueXor := 0
			for _, q := range w.Pending {
				if q.Due == t0 {
					dueXor ^= q.Mask
				}
			}
			phase, e := f36Phase(seed, t0)
			if e != nil {
				t.Fatal(e)
			}
			law, e := f36Law(phase)
			if e != nil {
				t.Fatal(e)
			}
			if a > 0 && law[c][a-1].Lag == 1 {
				dueXor ^= law[c][a-1].Mask
			}
			next, _, e := w.step(t0, c, a)
			if e != nil {
				t.Fatal(e)
			}
			if next != old^dueXor {
				t.Fatalf("simulator event mismatch seed=%d t=%d", seed, t0)
			}
			for _, q := range w.Pending {
				if q.Due < t0 || q.Mask < 1 || q.Mask > 15 {
					t.Fatal("pending event corrupted")
				}
			}
		}
	}
}
func TestF36CleanScorerNotInTraining(t *testing.T) {
	a, e := f36Train()
	if e != nil || !f36ValidParams(a) {
		t.Fatal("source not trained", e)
	}
	for _, tab := range []f36LawTable{a.A, a.B, a.Pooled} {
		for c := 0; c < 4; c++ {
			for i := 0; i < 2; i++ {
				if tab[c][i].Mask == 0 || tab[c][i].Lag == 0 {
					t.Fatal("empty trained law")
				}
			}
		}
	}
	for _, seed := range []uint32{0, 59, 83, 389, 397, 401, 409, 4311, 4391} {
		if _, e := f36NewWorld(seed); e == nil {
			t.Fatal("unknown seed", seed)
		}
	}
	if _, e := f36Cue(439, "invalid", 0); e == nil {
		t.Fatal("unknown schedule")
	}
	if _, e := f36Goal(439, 96); e == nil {
		t.Fatal("future goal")
	}
	if _, e := f36Phase(439, -1); e == nil {
		t.Fatal("negative time")
	}
}
func TestF36FrozenReportForgery(t *testing.T) {
	r, e := F36Development()
	if e != nil {
		t.Fatal(e)
	}
	cases := []func(*F36Report){func(x *F36Report) { x.ScientificAccepted = true }, func(x *F36Report) { x.FirstUseConsumed = true }, func(x *F36Report) { x.OwnerEligible = true }, func(x *F36Report) { x.MatchedComputeProven = true }, func(x *F36Report) { x.TransferSeeds[0] = 59 }, func(x *F36Report) { x.Arms[0].Trials[0].Hits = 24 }, func(x *F36Report) { x.Classification = F36Signal }, func(x *F36Report) { x.PriorNegativesPreserved = false }}
	for i, f := range cases {
		b, _ := json.Marshal(r)
		var copy F36Report
		if json.Unmarshal(b, &copy) != nil {
			t.Fatal("copy")
		}
		f(&copy)
		copy.DigestSHA256 = f36Digest(copy)
		if F36Validate(copy) == nil {
			t.Fatal("forged report accepted", i)
		}
	}
}
func TestF36CheckpointCanonicality(t *testing.T) {
	a, e := f36Train()
	if e != nil {
		t.Fatal(e)
	}
	raw, _ := json.Marshal(a)
	b, e := f36LoadArchive(raw)
	if e != nil || !reflect.DeepEqual(a, b) {
		t.Fatal("cold archive failed")
	}
	if _, e := f36LoadArchive(append([]byte(" "), raw...)); e == nil {
		t.Fatal("noncanonical accepted")
	}
	m, e := f36Init(a, "compositional-issued-memory", [2]int{0, 0})
	if e != nil {
		t.Fatal(e)
	}
	raw, _ = json.Marshal(m)
	n, e := f36LoadModel(raw)
	if e != nil || !reflect.DeepEqual(m, n) {
		t.Fatal("cold model failed")
	}
	if _, e := f36LoadModel(append([]byte(" "), raw...)); e == nil {
		t.Fatal("tampered model accepted")
	}
}

// An already-issued event must retain its original (due,mask) across a cold
// serialization and across subsequent observations. This tests midworld memory,
// not merely restoration of the initial trained archive.
func TestF36MidEpisodePendingColdRetention(t *testing.T) {
	archive, err := f36Train()
	if err != nil {
		t.Fatal(err)
	}
	seed := uint32(439)
	world, err := f36NewWorld(seed)
	if err != nil {
		t.Fatal(err)
	}
	control, err := f36Init(archive, "compositional-issued-memory", world.Sensors)
	if err != nil {
		t.Fatal(err)
	}
	// At t=0 force a real actuator1 pulse; due times differ across hypotheses.
	cue, err := f36Cue(seed, "balanced", 0)
	if err != nil {
		t.Fatal(err)
	}
	_, sensed, err := world.step(0, cue, 1)
	if err != nil {
		t.Fatal(err)
	}
	if err := control.observe(0, cue, 1, sensed); err != nil {
		t.Fatal(err)
	}
	anyPending := false
	for _, events := range control.Events {
		for _, e := range events {
			if e.Due > 0 {
				anyPending = true
			}
		}
	}
	if !anyPending {
		t.Fatal("no pending causal event to cold restore")
	}
	checkpoint, err := json.Marshal(control)
	if err != nil {
		t.Fatal(err)
	}
	restored, err := f36LoadModel(checkpoint)
	if err != nil || !reflect.DeepEqual(control, restored) {
		t.Fatal("pending receipt lost during cold restart", err)
	}
	for step := 1; step <= 7; step++ {
		c, e := f36Cue(seed, "balanced", step)
		if e != nil {
			t.Fatal(e)
		}
		a := 0
		if step == 3 {
			a = 2
		}
		goal, e := f36Goal(seed, step)
		if e != nil {
			t.Fatal(e)
		}
		for action := 0; action <= 2; action++ {
			x, e := control.scoreGoal(step, c, action, goal)
			if e != nil {
				t.Fatal(e)
			}
			y, e := restored.scoreGoal(step, c, action, goal)
			if e != nil || x != y {
				t.Fatal("cold planning mismatch", e)
			}
		}
		_, next, e := world.step(step, c, a)
		if e != nil {
			t.Fatal(e)
		}
		if e = control.observe(step, c, a, next); e != nil {
			t.Fatal(e)
		}
		if e = restored.observe(step, c, a, next); e != nil {
			t.Fatal(e)
		}
		b, _ := json.Marshal(control)
		d, _ := json.Marshal(restored)
		if !reflect.DeepEqual(b, d) {
			t.Fatalf("cold continuation drift at step %d", step)
		}
	}
}
