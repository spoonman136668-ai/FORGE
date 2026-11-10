package nativediscovery

import (
	"bytes"
	"encoding/json"
	"math"
	"reflect"
	"testing"
)

func TestF35FrozenFourWorldDevelopment(t *testing.T) {
	report, err := F35Development()
	if err != nil {
		t.Fatal("F35 complete DEV evaluation errored", err)
	}
	if err = F35Validate(report); err != nil {
		t.Fatal("F35 evidence hash/source failed", err)
	}
	if report.Parent != F35Parent || report.Schema != F35Schema || report.TrainingWorlds != [2]uint32{331, 337} || report.TransferWorlds != [4]uint32{389, 397, 401, 409} || report.TrainingTransitions != 256 || report.TransferTransitions != 96 || report.Decisions != 48 || report.Budget != 24 || report.MinGoalsGain != 3 || report.MinAblationGain != 4 || report.MinNetGain != 2.5 || !report.DevelopmentOnly || !report.EarlierNegativesPreserved || report.FirstUseConsumed || report.ScientificAccepted || report.OwnerEligible || report.DispatchAuthorized || report.WholeProcessCostProven || report.MatchedComputeProven {
		t.Fatal("frozen protocol or authority drift")
	}
	passing := 0
	for i, arm := range report.Arms {
		if arm.Seed != report.TransferWorlds[i] || arm.Schedule != f35Worlds()[i].Schedule {
			t.Fatal("world changed")
		}
		best, bestNet := 0, 0.0
		for j, v := range arm.Trials {
			if v.Kind != f35Kinds()[j] || v.GoalsHit < 0 || v.GoalsHit > 48 || v.Interventions < 0 || v.Interventions > 24 || v.Opportunities != 48 || v.ObservedTransitions != 96 || !v.ColdMatches || len(v.GoalsSHA256) != 64 || len(v.ActionsSHA256) != 64 || len(v.SensorsSHA256) != 64 || len(v.DecisionsSHA256) != 64 || len(v.CheckpointSHA256) != 64 || len(v.TerminalSHA256) != 64 {
				t.Fatalf("bad trial custody: world=%d model=%s", arm.Seed, v.Kind)
			}
			total := 0
			for _, h := range v.PhaseHits {
				if h < 0 || h > 12 {
					t.Fatal("phase score invalid")
				}
				total += h
			}
			if total != v.GoalsHit {
				t.Fatal("phase score mismatch")
			}
			if math.Abs(v.NetReward-(float64(v.GoalsHit)-.05*float64(v.Interventions))) > 1e-9 {
				t.Fatal("unmatched action cost")
			}
			if v.GoalsSHA256 != arm.Trials[0].GoalsSHA256 {
				t.Fatal("unequal external goals")
			}
			if j < 7 && (v.TrainingSeen != 256 || v.ModelParameters <= 0 || v.TrainingWork <= 0) {
				t.Fatal("baseline not fully trained", v.Kind)
			}
			if j >= 1 && j <= 3 {
				if v.GoalsHit > best {
					best = v.GoalsHit
				}
				if v.NetReward > bestNet {
					bestNet = v.NetReward
				}
			}
		}
		candidate := arm.Trials[0]
		hits := candidate.GoalsHit - best
		net := candidate.NetReward - bestNet
		gReplay := candidate.GoalsHit - arm.Trials[4].GoalsHit
		gZero := candidate.GoalsHit - arm.Trials[5].GoalsHit
		gCold := candidate.GoalsHit - arm.Trials[6].GoalsHit
		passes := hits >= 3 && net >= 2.5 && gReplay >= 4 && gZero >= 4 && gCold >= 4
		if arm.Passes != passes || arm.GainGoals != hits || arm.GainNet != net || arm.GainReplay != gReplay || arm.GainZeroMemory != gZero || arm.GainCold != gCold || arm.BestConventionalHits != best || arm.BestConventionalNet != bestNet {
			t.Fatal("reclassified frozen evidence", arm.Seed)
		}
		if passes {
			passing++
		}
		t.Logf("F35_DEV seed=%d %s candidate=%d/48 best_trained=%d replay=%d zero_pending=%d coldzero=%d interventions=%d particles_peak=%d work=%d gain=%+d pass=%v", arm.Seed, arm.Schedule, candidate.GoalsHit, best, arm.Trials[4].GoalsHit, arm.Trials[5].GoalsHit, arm.Trials[6].GoalsHit, candidate.Interventions, candidate.PeakParticles, candidate.Propagations, hits, passes)
	}
	want := F35NoGo
	if passing == 4 {
		want = F35Signal
	}
	if report.Classification != want || report.Passing != passing {
		t.Fatal("classification incorrect")
	}
	t.Logf("F35_FROZEN_DEV=%s passing=%d/4 science=false", report.Classification, passing)
}
func TestF35IssuedEventNeverRewrittenByNewRegimeWeights(t *testing.T) {
	trained, e := f33Train()
	if e != nil {
		t.Fatal(e)
	}
	m, e := f35Begin("four-bank-issued-memory", trained[0], [2]int{0, 0})
	if e != nil {
		t.Fatal(e)
	}
	// Construct valid, learned-representation hypotheses with an action1 event issued now.
	for k := 0; k < 4; k++ {
		m.Source.SourceTemplates[k][0] = f32Spec{Mask: 1, Lag: 3}
	}
	m.Source.Weights = [4]float64{1, 0, 0, 0}
	issued, n, e := f35Advance(m.Particles, m, 0, 0, 1, nil)
	if e != nil || n < 1 {
		t.Fatal("issue", e)
	}
	for _, p := range issued {
		if len(p.Pending) != 1 || p.Pending[0] != (f32Event{Due: 2, Mask: 1}) {
			t.Fatal("issuance receipt changed", p.Pending)
		}
	}
	old := m
	old.Source.Weights = [4]float64{1, 0, 0, 0}
	newHyp := m
	newHyp.Source.Weights = [4]float64{0, 1, 0, 0}
	newHyp.Source.SourceTemplates[1][0] = f32Spec{Mask: 2, Lag: 1}
	pOld, _, e := f35Advance(issued, old, 1, 0, 0, nil)
	if e != nil {
		t.Fatal(e)
	}
	pNew, _, e := f35Advance(issued, newHyp, 1, 0, 0, nil)
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(pOld, pNew) {
		t.Fatal("new regime hypothesis rewrote already issued action")
	}
	delivered, _, e := f35Advance(pNew, newHyp, 2, 0, 0, nil)
	if e != nil {
		t.Fatal(e)
	}
	for _, p := range delivered {
		if len(p.Pending) != 0 {
			t.Fatal("event not delivered")
		}
	}
	once, _, e := f35Advance(delivered, newHyp, 3, 0, 0, nil)
	if e != nil || !reflect.DeepEqual(delivered, once) {
		t.Fatal("event replayed after delivery", e)
	}
}
func TestF35RealWorldDelayedAndOverlappingActions(t *testing.T) {
	for _, w := range f35Worlds() {
		world, e := f35NewWorld(w.Seed)
		if e != nil {
			t.Fatal(e)
		}
		seenLags := [4]bool{}
		for t0 := 0; t0 < 96; t0++ {
			cue, e := f35Cue(w.Seed, w.Schedule, t0)
			if e != nil {
				t.Fatal(e)
			}
			action := 0
			if t0%2 == 0 {
				action = 1
			}
			pre := world.State
			phase, e := f35Phase(w.Seed, t0)
			if e != nil {
				t.Fatal(e)
			}
			if action == 1 {
				spec, e := f32Law(phase, cue)
				if e != nil {
					t.Fatal(e)
				}
				seenLags[spec.Lag] = true
			}
			var due []f32Event
			due = append(due, world.Due...)
			if action == 1 {
				spec, _ := f32Law(phase, cue)
				due = append(due, f32Event{Due: t0 + spec.Lag - 1, Mask: spec.Mask})
			}
			wantMask := 0
			for _, ev := range due {
				if ev.Due == t0 {
					wantMask ^= ev.Mask
				}
			}
			actual, _, e := world.step(t0, cue, action)
			if e != nil {
				t.Fatal(e)
			}
			if pre^actual != wantMask {
				t.Fatal("physical world altered issuance-time events")
			}
		}
		if !seenLags[1] || !seenLags[2] || !seenLags[3] {
			t.Fatal("missing real delayed-event lag in transfer", w.Seed, seenLags)
		}
	}
}
func TestF35ColdRestoreAndTamper(t *testing.T) {
	trained, e := f33Train()
	if e != nil {
		t.Fatal(e)
	}
	for _, w := range f35Worlds() {
		for _, kind := range f35Kinds() {
			cold, cb, e := f35Trial(trained, kind, w.Seed, w.Schedule, true)
			warm, wb, e2 := f35Trial(trained, kind, w.Seed, w.Schedule, false)
			if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				t.Fatal("cold/continuation drift", w.Seed, kind, e, e2)
			}
		}
	}
	m, e := f35Begin("four-bank-issued-memory", trained[0], [2]int{1, 1})
	if e != nil {
		t.Fatal(e)
	}
	raw, e := f35Save(m)
	if e != nil {
		t.Fatal(e)
	}
	clone, e := f35Load(raw)
	if e != nil || !reflect.DeepEqual(clone, m) {
		t.Fatal("exact cold state lost", e)
	}
	// Probe an in-flight event checkpoint, not merely an empty model.
	m.Particles, _, e = f35Advance(m.Particles, m, 0, 0, 1, nil)
	if e != nil {
		t.Fatal(e)
	}
	m.Clock = 1
	m.Source.TransferSeen = 1
	m.Source.History = []f32Issued{{Cue: 0, Action: 1}}
	raw, e = f35Save(m)
	if e != nil {
		t.Fatal(e)
	}
	clone, e = f35Load(raw)
	if e != nil || !reflect.DeepEqual(clone, m) {
		t.Fatal("pending issued event not persisted", e)
	}
	if _, e = f35Load(append([]byte(" "), raw...)); e == nil {
		t.Fatal("noncanonical checkpoint admitted")
	}
	corrupt := append([]byte(nil), raw...)
	corrupt[0] = '['
	if _, e = f35Load(corrupt); e == nil {
		t.Fatal("corrupt checkpoint admitted")
	}
}
func TestF35FirstUseAndAuthorityFailClosed(t *testing.T) {
	for _, seed := range []uint32{0, 59, 83, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 388, 390, 396, 398, 400, 402, 408, 410} {
		if _, e := f35NewWorld(seed); e == nil {
			t.Fatal("outside F35 heldout admitted", seed)
		}
		if _, e := f35Goal(seed, 0); e == nil {
			t.Fatal("goal seed admitted", seed)
		}
		if _, e := f35Phase(seed, 0); e == nil {
			t.Fatal("phase seed admitted", seed)
		}
	}
	if _, e := f35Goal(389, 1); e == nil {
		t.Fatal("odd-step goal admitted")
	}
	if _, e := f35Cue(389, "invalid", 0); e == nil {
		t.Fatal("bad schedule admitted")
	}
	if _, e := f35Sensor(389, 0, 4, 0); e == nil {
		t.Fatal("bad hidden state admitted")
	}
	orig, e := F35Development()
	if e != nil {
		t.Fatal(e)
	}
	tamper := []struct {
		name string
		fn   func(*F35Report)
	}{
		{"science", func(r *F35Report) { r.ScientificAccepted = true }},
		{"firstuse", func(r *F35Report) { r.FirstUseConsumed = true }},
		{"owner", func(r *F35Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F35Report) { r.DispatchAuthorized = true }},
		{"wholecost", func(r *F35Report) { r.WholeProcessCostProven = true }},
		{"matchedcompute", func(r *F35Report) { r.MatchedComputeProven = true }},
		{"threshold", func(r *F35Report) { r.MinGoalsGain = 0 }},
		{"seed", func(r *F35Report) { r.TransferWorlds[0] = 59 }},
		{"negative", func(r *F35Report) { r.EarlierNegativesPreserved = false }},
		{"candidate", func(r *F35Report) { r.Arms[0].Trials[0].GoalsHit = 48 }},
		{"baseline", func(r *F35Report) { r.Arms[0].Trials[1].GoalsHit = 0 }},
		{"relabel", func(r *F35Report) { r.Classification = F35Signal }},
	}
	for _, c := range tamper {
		t.Run(c.name, func(t *testing.T) {
			raw, _ := json.Marshal(orig)
			var copy F35Report
			if json.Unmarshal(raw, &copy) != nil {
				t.Fatal("copy")
			}
			c.fn(&copy)
			copy.DigestSHA256 = f35Digest(copy)
			if F35Validate(copy) == nil {
				t.Fatal("forged evidence accepted")
			}
		})
	}
}
