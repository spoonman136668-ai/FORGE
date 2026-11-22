// Eureka F33: goal-directed action choice in a delayed consequence environment.
// Frozen synthetic development evidence only: not scientific first-use or owner authority.
package nativediscovery

import (
	"bytes"
	"encoding/json"
	"errors"
	"math"
	"reflect"
	"sync"
)

const (
	F33Schema    = "forge.native-discovery.delayed-goal-control.dev.v1"
	F33Parent    = "91600fe51adb429ed53c75cdb8abf45df74c87ef"
	F33NoGo      = "F33_DEV_NO_GO"
	F33Signal    = "F33_DEV_SIGNAL_UNVERIFIED"
	F33Steps     = 96
	F33Decisions = 48
	F33Budget    = 24
)

var errF33 = errors.New("FORGE_EUREKA_F33_SOURCE_OR_AUTHORITY_INVALID")

type f33World struct {
	Seed        uint32
	State, Seen int
	Sensors     [2]int
	Due         []f32Event
}
type f33Decision struct {
	Goal   int     `json:"goal"`
	Action int     `json:"action"`
	P0     float64 `json:"p0"`
	P1     float64 `json:"p1"`
}

func f33Worlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{
		{367, "balanced"}, {373, "skewed"}, {379, "balanced"}, {383, "skewed"},
	}
}
func f33Known(seed uint32) bool {
	for _, w := range f33Worlds() {
		if seed == w.Seed {
			return true
		}
	}
	return false
}
func f33Phase(seed uint32, t int) (byte, error) {
	if !f33Known(seed) || t < 0 || t >= F33Steps {
		return 0, errF33
	}
	firstA := seed == 367 || seed == 379
	switch t / 24 {
	case 0, 2:
		if firstA {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if firstA {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if seed == 367 || seed == 383 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF33
}
func f33Cue(seed uint32, sched string, t int) (int, error) {
	if !f33Known(seed) || t < 0 || t >= F33Steps {
		return 0, errF33
	}
	even := t - (t % 2)
	switch sched {
	case "balanced":
		return (even/2 + int(seed%4)) % 4, nil
	case "skewed":
		if even%8 == 6 {
			return (even/4 + int(seed%4)) % 4, nil
		}
		return (even/4 + int(seed%2)) % 2, nil
	}
	return 0, errF33
}
func f33Goal(seed uint32, t int) (int, error) {
	if !f33Known(seed) || t < 0 || t >= F33Steps || t%2 != 0 {
		return 0, errF33
	}
	return int(f27Mix(seed^uint32(t/2+1)*0x7f4a7c15^0x52dce729) & 3), nil
}
func f33Sensor(seed uint32, t, clean, which int) (int, error) {
	if !f33Known(seed) || t < 0 || t > F33Steps || clean < 0 || clean > 3 || which < 0 || which > 1 {
		return 0, errF33
	}
	u := f27Mix(seed^uint32(t+1)*0x9e3779b9^uint32(which+1)*0x85ebca6b^0x6a09e667) % 100
	if which == 0 {
		if u < 90 {
			return clean, nil
		}
		if u < 96 {
			return (clean + 1) % 4, nil
		}
		return (clean + 3) % 4, nil
	}
	if u < 80 {
		return clean, nil
	}
	if u < 90 {
		return (clean + 1) % 4, nil
	}
	return (clean + 3) % 4, nil
}
func f33NewWorld(seed uint32) (f33World, error) {
	if !f33Known(seed) {
		return f33World{}, errF33
	}
	w := f33World{Seed: seed, State: int(f27Mix(seed^0x4cf5ad43) & 3)}
	for i := 0; i < 2; i++ {
		s, e := f33Sensor(seed, 0, w.State, i)
		if e != nil {
			return f33World{}, e
		}
		w.Sensors[i] = s
	}
	return w, nil
}
func (w *f33World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || t < 0 || t >= F33Steps || c < 0 || c > 3 || a < 0 || a > 1 || !f33Known(w.Seed) {
		return 0, [2]int{}, errF33
	}
	if a == 1 {
		law, e := f33Phase(w.Seed, t)
		if e != nil {
			return 0, [2]int{}, e
		}
		spec, e := f32Law(law, c)
		if e != nil {
			return 0, [2]int{}, e
		}
		w.Due = append(w.Due, f32Event{Due: t + spec.Lag - 1, Mask: spec.Mask})
	}
	var pending []f32Event
	for _, event := range w.Due {
		if event.Due == t {
			w.State ^= event.Mask
		} else if event.Due > t {
			pending = append(pending, event)
		} else {
			return 0, [2]int{}, errF33
		}
	}
	w.Due = pending
	w.Seen++
	var next [2]int
	for i := 0; i < 2; i++ {
		v, e := f33Sensor(w.Seed, w.Seen, w.State, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = v
	}
	w.Sensors = next
	return w.State, next, nil
}
func f33Kinds() [8]string {
	return [8]string{
		"delayed-event-memory", "two-bank-event-bayes", "pooled-event-bayes", "history-logistic",
		"history-blind", "cold-zero", "random-budget", "always-zero",
	}
}
func f33Learned(kind string) bool { return kind != "random-budget" && kind != "always-zero" }
func f33Train() ([6]f32Model, error) {
	var out [6]f32Model
	aa, e := f32MakeTrace(331, "isolated")
	if e != nil {
		return out, e
	}
	bb, e := f32MakeTrace(337, "isolated")
	if e != nil {
		return out, e
	}
	for _, tr := range [2]f32Trace{aa, bb} {
		_, cov, e := f32TrainLog(tr)
		if e != nil {
			return out, e
		}
		for _, v := range cov {
			if v != 4 {
				return out, errF33
			}
		}
	}
	for i := 0; i < 6; i++ {
		m, e := f32Train(f33Kinds()[i], [2]f32Trace{aa, bb})
		if e != nil || m.TrainingSeen != 256 {
			return out, errF33
		}
		out[i] = m
	}
	return out, nil
}

// Forward-project the next two real transitions without inventing sensor feedback.
// Four regime hypotheses use only the stored learned event templates and actual action history.
func f33EventPlan(m f32Model, c, oddCue, a, goal int) (float64, int, error) {
	if !m.HasWorld || len(m.History)%2 != 0 || goal < 0 || goal > 3 {
		return 0, 0, errF33
	}
	state, e := f27Posterior(m.Last)
	if e != nil {
		return 0, 0, e
	}
	n := 4
	if m.Kind == "two-bank-event-bayes" {
		n = 2
	}
	if m.Kind == "pooled-event-bayes" {
		n = 1
	}
	now := f32Issued{Cue: c, Action: a}
	next := f32Issued{Cue: oddCue, Action: 0}
	history := append(append([]f32Issued(nil), m.History...), now)
	t := len(m.History)
	chance := 0.0
	for k := 0; k < n; k++ {
		template := m.SourceTemplates[k]
		if m.Kind == "pooled-event-bayes" {
			template = m.Pool
		}
		if m.Kind == "cold-zero" {
			for idx := range template {
				template[idx] = f32Spec{Mask: 1, Lag: 1}
			}
		}
		blind := m.Kind == "history-blind"
		d0 := f32Due(m.History, now, t, template, blind)
		d1 := f32Due(history, next, t+1, template, blind)
		chance += m.Weights[k] * state[goal^(d0^d1)]
	}
	if math.IsNaN(chance) || chance < 0 || chance > 1+1e-10 {
		return 0, 0, errF33
	}
	return chance, 2*n*4*3 + 16, nil
}

// Autoregressive conventional model: sum over all 16 possible intermediate sensor pairs,
// with probabilities from its own learned first-step prediction; no fabricated training.
func f33LogisticPlan(m f32Model, c, oddCue, a, goal int) (float64, int, error) {
	if !m.HasWorld || m.Kind != "history-logistic" || goal < 0 || goal > 3 {
		return 0, 0, errF33
	}
	first := m
	p, e := func() ([4]float64, error) { p, _, e := first.nextPred(c, a); return p, e }()
	if e != nil {
		return 0, 0, e
	}
	value := 0.0
	for s0 := 0; s0 < 4; s0++ {
		for s1 := 0; s1 < 4; s1++ {
			obs := [2]int{s0, s1}
			likelihood := 0.0
			for state := 0; state < 4; state++ {
				likelihood += p[state] * f27Likelihood(obs, state)
			}
			fictive := m
			fictive.Last = obs
			fictive.History = append(append([]f32Issued(nil), m.History...), f32Issued{Cue: c, Action: a})
			second, _, e := fictive.nextPred(oddCue, 0)
			if e != nil {
				return 0, 0, e
			}
			value += likelihood * second[goal]
		}
	}
	if math.IsNaN(value) || value < 0 || value > 1+1e-10 {
		return 0, 0, errF33
	}
	return value, (1+16)*68 + 4*16*4, nil
}
func f33Plan(m f32Model, c, oddCue, a, goal int) (float64, int, error) {
	if m.Kind == "history-logistic" {
		return f33LogisticPlan(m, c, oddCue, a, goal)
	}
	return f33EventPlan(m, c, oddCue, a, goal)
}

type F33Trial struct {
	Kind                                                                                         string `json:"kind"`
	GoalsHit, Interventions, Opportunities, ObservedTransitions, TrainingSeen                    int
	PhaseHits                                                                                    [4]int  `json:"phase_hits"`
	EarlySwitchHits                                                                              [3]int  `json:"early_switch_hits"`
	NetReward                                                                                    float64 `json:"net_reward"`
	ModelParameters, TrainingWork, OnlineWork, PlannerWork                                       int
	GoalsSHA256, ActionsSHA256, SensorsSHA256, DecisionsSHA256, CheckpointSHA256, TerminalSHA256 string
	ColdMatches                                                                                  bool `json:"cold_matches"`
}

func f33Trial(trained [6]f32Model, kind string, seed uint32, sched string, cold bool) (F33Trial, []byte, error) {
	if !f33Known(seed) {
		return F33Trial{}, nil, errF33
	}
	idx := -1
	for i, k := range f33Kinds() {
		if k == kind {
			idx = i
		}
	}
	if idx < 0 {
		return F33Trial{}, nil, errF33
	}
	world, e := f33NewWorld(seed)
	if e != nil {
		return F33Trial{}, nil, e
	}
	result := F33Trial{Kind: kind, Opportunities: F33Decisions, ColdMatches: true}
	var model f32Model
	var ck []byte
	if f33Learned(kind) {
		model = trained[idx]
		ck, e = f32Save(model)
		if e != nil {
			return F33Trial{}, nil, e
		}
		if cold {
			model, e = f32Load(ck)
			if e != nil {
				return F33Trial{}, nil, e
			}
		}
		result.TrainingSeen = model.TrainingSeen
		result.ModelParameters = f32Params(kind)
		result.TrainingWork = model.Work
		if e = model.beginWorld(world.Sensors); e != nil {
			return F33Trial{}, nil, e
		}
	} else {
		ck, _ = json.Marshal(struct {
			Kind       string
			TrainSeeds [2]uint32
		}{kind, [2]uint32{331, 337}})
	}
	result.CheckpointSHA256 = f27Hash(ck)
	initialWork := model.Work
	var goals []int
	var acts []int
	var obs [][2]int
	var decisions []f33Decision
	obs = append(obs, world.Sensors)
	for t := 0; t < F33Steps; t += 2 {
		cue, e := f33Cue(seed, sched, t)
		if e != nil {
			return F33Trial{}, nil, e
		}
		oddCue, e := f33Cue(seed, sched, t+1)
		if e != nil {
			return F33Trial{}, nil, e
		}
		goal, e := f33Goal(seed, t)
		if e != nil {
			return F33Trial{}, nil, e
		}
		goals = append(goals, goal)
		choice := 0
		p0, p1 := 0.0, 0.0
		if f33Learned(kind) {
			var work0, work1 int
			p0, work0, e = f33Plan(model, cue, oddCue, 0, goal)
			if e != nil {
				return F33Trial{}, nil, e
			}
			p1, work1, e = f33Plan(model, cue, oddCue, 1, goal)
			if e != nil {
				return F33Trial{}, nil, e
			}
			result.PlannerWork += work0 + work1
			if p1-p0 > 0.05 && result.Interventions < F33Budget {
				choice = 1
			}
		} else if kind == "random-budget" && (f27Mix(seed^uint32(t/2+1)*0x4c11db7)&1) == 1 && result.Interventions < F33Budget {
			choice = 1
		}
		if choice == 1 {
			result.Interventions++
		}
		decisions = append(decisions, f33Decision{Goal: goal, Action: choice, P0: p0, P1: p1})
		for sub := 0; sub < 2; sub++ {
			action := 0
			currentCue := oddCue
			if sub == 0 {
				action = choice
				currentCue = cue
			}
			acts = append(acts, action)
			if f33Learned(kind) {
				if _, _, e = model.nextPred(currentCue, action); e != nil {
					return F33Trial{}, nil, e
				}
			}
			_, next, e := world.step(t+sub, currentCue, action)
			if e != nil {
				return F33Trial{}, nil, e
			}
			obs = append(obs, next)
			if f33Learned(kind) {
				if e = model.observe(currentCue, action, next, false); e != nil {
					return F33Trial{}, nil, e
				}
			}
		}
		if world.State == goal {
			result.GoalsHit++
			result.PhaseHits[t/24]++
			if t >= 24 && t < 28 {
				result.EarlySwitchHits[0]++
			}
			if t >= 48 && t < 52 {
				result.EarlySwitchHits[1]++
			}
			if t >= 72 && t < 76 {
				result.EarlySwitchHits[2]++
			}
		}
	}
	result.ObservedTransitions = world.Seen
	if result.Interventions > F33Budget || world.Seen != F33Steps || len(decisions) != F33Decisions || len(obs) != F33Steps+1 {
		return F33Trial{}, nil, errF33
	}
	result.NetReward = float64(result.GoalsHit) - 0.05*float64(result.Interventions)
	if f33Learned(kind) {
		result.OnlineWork = model.Work - initialWork
	}
	bg, _ := json.Marshal(goals)
	result.GoalsSHA256 = f27Hash(bg)
	ba, _ := json.Marshal(acts)
	result.ActionsSHA256 = f27Hash(ba)
	bo, _ := json.Marshal(obs)
	result.SensorsSHA256 = f27Hash(bo)
	bd, _ := json.Marshal(decisions)
	result.DecisionsSHA256 = f27Hash(bd)
	var terminal []byte
	if f33Learned(kind) {
		terminal, e = f32Save(model)
	} else {
		terminal, _ = json.Marshal(struct {
			Kind                    string
			Seed                    uint32
			GoalsHit, Interventions int
		}{kind, seed, result.GoalsHit, result.Interventions})
	}
	if e != nil {
		return F33Trial{}, nil, e
	}
	result.TerminalSHA256 = f27Hash(terminal)
	return result, terminal, nil
}

type F33Arm struct {
	Seed                 uint32      `json:"seed"`
	Schedule             string      `json:"schedule"`
	Trials               [8]F33Trial `json:"trials"`
	BestConventionalHits int         `json:"best_conventional_hits"`
	BestConventionalNet  float64     `json:"best_conventional_net"`
	GainGoals            int         `json:"gain_goals"`
	GainBlind            int         `json:"gain_blind"`
	GainCold             int         `json:"gain_cold"`
	GainNet              float64     `json:"gain_net"`
	Passes               bool        `json:"passes"`
}
type F33Report struct {
	Schema, Parent, Classification                                                                                        string
	TrainSeeds                                                                                                            [2]uint32
	DevSeeds                                                                                                              [4]uint32
	TrainingTransitions, TransferTransitions, Decisions, Budget                                                           int
	MinGoalsGain, MinAblationGain                                                                                         int
	MinNetGain                                                                                                            float64
	Arms                                                                                                                  [4]F33Arm
	Passing                                                                                                               int
	DevelopmentOnly, EarlierNegativesPreserved                                                                            bool
	FirstUseConsumed, ScientificAccepted, OwnerEligible, DispatchAuthorized, WholeProcessCostProven, MatchedComputeProven bool
	DigestSHA256                                                                                                          string
}

func f33Digest(r F33Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func f33Calculate() (F33Report, error) {
	r := F33Report{Schema: F33Schema, Parent: F33Parent, TrainSeeds: [2]uint32{331, 337}, DevSeeds: [4]uint32{367, 373, 379, 383}, TrainingTransitions: 256, TransferTransitions: 96, Decisions: 48, Budget: 24, MinGoalsGain: 3, MinAblationGain: 4, MinNetGain: 2.5, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	trained, e := f33Train()
	if e != nil {
		return r, e
	}
	for i, w := range f33Worlds() {
		arm := F33Arm{Seed: w.Seed, Schedule: w.Schedule}
		for j, k := range f33Kinds() {
			cold, cb, e := f33Trial(trained, k, w.Seed, w.Schedule, true)
			if e != nil {
				return r, e
			}
			warm, wb, e := f33Trial(trained, k, w.Seed, w.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return r, errF33
			}
			arm.Trials[j] = cold
		}
		for j, v := range arm.Trials {
			if v.Kind != f33Kinds()[j] || v.Opportunities != 48 || v.ObservedTransitions != 96 || v.Interventions > 24 || v.Interventions < 0 || v.GoalsHit < 0 || v.GoalsHit > 48 || v.GoalsSHA256 != arm.Trials[0].GoalsSHA256 || !v.ColdMatches {
				return r, errF33
			}
			if j >= 1 && j <= 3 {
				if v.GoalsHit > arm.BestConventionalHits {
					arm.BestConventionalHits = v.GoalsHit
				}
				if v.NetReward > arm.BestConventionalNet {
					arm.BestConventionalNet = v.NetReward
				}
			}
		}
		arm.GainGoals = arm.Trials[0].GoalsHit - arm.BestConventionalHits
		arm.GainNet = arm.Trials[0].NetReward - arm.BestConventionalNet
		arm.GainBlind = arm.Trials[0].GoalsHit - arm.Trials[4].GoalsHit
		arm.GainCold = arm.Trials[0].GoalsHit - arm.Trials[5].GoalsHit
		arm.Passes = arm.GainGoals >= 3 && arm.GainNet >= 2.5 && arm.GainBlind >= 4 && arm.GainCold >= 4
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F33NoGo
	if r.Passing == 4 {
		r.Classification = F33Signal
	}
	r.DigestSHA256 = f33Digest(r)
	return r, nil
}

var f33Once sync.Once
var f33Cached F33Report
var f33CacheErr error

func F33Development() (F33Report, error) {
	f33Once.Do(func() { f33Cached, f33CacheErr = f33Calculate() })
	return f33Cached, f33CacheErr
}
func F33Validate(r F33Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f33Digest(r) || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven {
		return errF33
	}
	expected, e := F33Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF33
	}
	return nil
}
