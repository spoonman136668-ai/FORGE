// Eureka F35: issuance-frozen, cold-restorable belief over pending delayed events.
// Synthetic development only. No owner, dispatch, first-use or deployment hooks.
package nativediscovery

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"reflect"
	"sort"
	"sync"
)

const (
	F35Schema = "forge.native-discovery.issuance-frozen-goal.dev.v1"
	F35Parent = "9f04db87a01701b458bd4aa6b1c4428b06a3c17e"
	F35NoGo   = "F35_DEV_NO_GO"
	F35Signal = "F35_DEV_SIGNAL_UNVERIFIED"
)

var errF35 = errors.New("FORGE_EUREKA_F35_SOURCE_OR_AUTHORITY_INVALID")

func f35Worlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{{389, "balanced"}, {397, "skewed"}, {401, "balanced"}, {409, "skewed"}}
}
func f35Known(seed uint32) bool {
	for _, w := range f35Worlds() {
		if w.Seed == seed {
			return true
		}
	}
	return false
}
func f35Phase(seed uint32, t int) (byte, error) {
	if !f35Known(seed) || t < 0 || t >= 96 {
		return 0, errF35
	}
	a := seed == 389 || seed == 401
	switch t / 24 {
	case 0, 2:
		if a {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if a {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if seed == 389 || seed == 409 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF35
}
func f35Cue(seed uint32, schedule string, t int) (int, error) {
	if !f35Known(seed) || t < 0 || t >= 96 {
		return 0, errF35
	}
	even := t - t%2
	switch schedule {
	case "balanced":
		return (even/2 + int(seed%4)) % 4, nil
	case "skewed":
		if even%8 == 6 {
			return (even/4 + int(seed%4)) % 4, nil
		}
		return (even/4 + int(seed%2)) % 2, nil
	}
	return 0, errF35
}
func f35Goal(seed uint32, t int) (int, error) {
	if !f35Known(seed) || t < 0 || t >= 96 || t%2 != 0 {
		return 0, errF35
	}
	return int(f27Mix(seed^uint32(t/2+1)*0x7f4a7c15^0x52dce729) & 3), nil
}
func f35Sensor(seed uint32, t, clean, which int) (int, error) {
	if !f35Known(seed) || t < 0 || t > 96 || clean < 0 || clean > 3 || which < 0 || which > 1 {
		return 0, errF35
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

type f35World struct {
	Seed        uint32
	State, Seen int
	Sensors     [2]int
	Due         []f32Event
}

func f35NewWorld(seed uint32) (f35World, error) {
	if !f35Known(seed) {
		return f35World{}, errF35
	}
	w := f35World{Seed: seed, State: int(f27Mix(seed^0x4cf5ad43) & 3)}
	for i := 0; i < 2; i++ {
		s, e := f35Sensor(seed, 0, w.State, i)
		if e != nil {
			return f35World{}, e
		}
		w.Sensors[i] = s
	}
	return w, nil
}

// Only the scorer and simulator call the hidden world law.
func (w *f35World) step(t, c, a int) (int, [2]int, error) {
	if !f35Known(w.Seed) || t != w.Seen || t < 0 || t >= 96 || c < 0 || c > 3 || a < 0 || a > 1 {
		return 0, [2]int{}, errF35
	}
	if a == 1 {
		phase, e := f35Phase(w.Seed, t)
		if e != nil {
			return 0, [2]int{}, e
		}
		spec, e := f32Law(phase, c)
		if e != nil {
			return 0, [2]int{}, e
		}
		w.Due = append(w.Due, f32Event{Due: t + spec.Lag - 1, Mask: spec.Mask})
	}
	var rest []f32Event
	for _, ev := range w.Due {
		if ev.Due == t {
			w.State ^= ev.Mask
		} else if ev.Due > t {
			rest = append(rest, ev)
		} else {
			return 0, [2]int{}, errF35
		}
	}
	w.Due = rest
	w.Seen++
	var next [2]int
	for i := 0; i < 2; i++ {
		s, e := f35Sensor(w.Seed, w.Seen, w.State, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = s
	}
	w.Sensors = next
	return w.State, next, nil
}
func f35Kinds() [8]string {
	return [8]string{
		"four-bank-issued-memory", "two-bank-issued-bayes", "pooled-issued-bayes", "history-logistic",
		"four-bank-replay-history", "four-bank-zero-memory", "cold-zero", "always-zero"}
}
func f35Underlying(kind string) string {
	switch kind {
	case "four-bank-issued-memory", "four-bank-replay-history", "four-bank-zero-memory":
		return "delayed-event-memory"
	case "two-bank-issued-bayes":
		return "two-bank-event-bayes"
	case "pooled-issued-bayes":
		return "pooled-event-bayes"
	case "history-logistic":
		return "history-logistic"
	case "cold-zero":
		return "cold-zero"
	}
	return ""
}

type f35Particle struct {
	State       int        `json:"state"`
	Probability float64    `json:"probability"`
	Pending     []f32Event `json:"pending"`
}
type f35Controller struct {
	Kind             string        `json:"kind"`
	Source           f32Model      `json:"source"`
	Particles        []f35Particle `json:"particles"`
	Clock            int           `json:"clock"`
	Propagations     int           `json:"propagations"`
	PeakParticles    int           `json:"peak_particles"`
	LikelihoodFloors int           `json:"likelihood_floors"`
}

func f35Template(m f35Controller, k int, c int) f32Spec {
	if m.Kind == "cold-zero" {
		return f32Spec{Mask: 1, Lag: 1}
	}
	if m.Kind == "pooled-issued-bayes" {
		return m.Source.Pool[c]
	}
	return m.Source.SourceTemplates[k][c]
}
func f35Number(m f35Controller) int {
	switch m.Kind {
	case "two-bank-issued-bayes":
		return 2
	case "pooled-issued-bayes":
		return 1
	default:
		return 4
	}
}
func f35Key(p f35Particle) string {
	key := fmt.Sprintf("%d", p.State)
	for _, ev := range p.Pending {
		key += fmt.Sprintf("|%d:%d", ev.Due, ev.Mask)
	}
	return key
}
func f35Merge(parts []f35Particle) ([]f35Particle, error) {
	buckets := make(map[string]f35Particle, len(parts))
	for _, p := range parts {
		if p.State < 0 || p.State >= 4 || math.IsNaN(p.Probability) || math.IsInf(p.Probability, 0) || p.Probability < 0 {
			return nil, errF35
		}
		for _, ev := range p.Pending {
			if ev.Mask < 1 || ev.Mask > 3 || ev.Due < 0 {
				return nil, errF35
			}
		}
		key := f35Key(p)
		if exist, ok := buckets[key]; ok {
			exist.Probability += p.Probability
			buckets[key] = exist
		} else {
			buckets[key] = p
		}
	}
	keys := make([]string, 0, len(buckets))
	for k := range buckets {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	merged := make([]f35Particle, 0, len(keys))
	total := 0.0
	for _, k := range keys {
		p := buckets[k]
		if p.Probability > 0 {
			merged = append(merged, p)
			total += p.Probability
		}
	}
	if total <= 0 || math.IsNaN(total) || math.IsInf(total, 0) {
		return nil, errF35
	}
	for i := range merged {
		merged[i].Probability /= total
	}
	return merged, nil
}
func f35Begin(kind string, trained f32Model, initial [2]int) (f35Controller, error) {
	if f35Underlying(kind) == "" || trained.Kind != f35Underlying(kind) || trained.TrainingSeen != 256 {
		return f35Controller{}, errF35
	}
	m := f35Controller{Kind: kind, Source: trained, Clock: 0}
	if err := m.Source.beginWorld(initial); err != nil {
		return f35Controller{}, err
	}
	posterior, e := f27Posterior(initial)
	if e != nil {
		return f35Controller{}, e
	}
	for s, prob := range posterior {
		if prob > 0 {
			m.Particles = append(m.Particles, f35Particle{State: s, Probability: prob})
		}
	}
	m.PeakParticles = len(m.Particles)
	return m, nil
}

// Each issue permanently binds its mask/due hypothesis. Future regime weights never rewrite it.
func f35AdvanceDetailed(parts []f35Particle, m f35Controller, t, c, a int, ob *[2]int) ([]f35Particle, int, int, error) {
	if t < 0 || t >= 96 || c < 0 || c > 3 || a < 0 || a > 1 {
		return nil, 0, 0, errF35
	}
	n := f35Number(m)
	raw := make([]f35Particle, 0, len(parts)*n)
	floors := 0
	for _, particle := range parts {
		for k := 0; k < n; k++ {
			weight := 1.0
			if a == 1 {
				weight = m.Source.Weights[k]
			}
			if weight <= 0 {
				continue
			}
			copyP := f35Particle{State: particle.State, Probability: particle.Probability * weight, Pending: append([]f32Event(nil), particle.Pending...)}
			if a == 1 {
				spec := f35Template(m, k, c)
				if spec.Lag < 1 || spec.Lag > 3 || spec.Mask < 1 || spec.Mask > 3 {
					return nil, 0, 0, errF35
				}
				copyP.Pending = append(copyP.Pending, f32Event{Due: t + spec.Lag - 1, Mask: spec.Mask})
			}
			outstanding := make([]f32Event, 0, len(copyP.Pending))
			for _, ev := range copyP.Pending {
				if ev.Due == t {
					copyP.State ^= ev.Mask
				} else if ev.Due > t {
					outstanding = append(outstanding, ev)
				} else {
					return nil, 0, 0, errF35
				}
			}
			copyP.Pending = outstanding
			if ob != nil {
				likelihood := f27Likelihood(*ob, copyP.State)
				if likelihood == 0 {
					likelihood = 1e-9
					floors++
				}
				copyP.Probability *= likelihood
			}
			raw = append(raw, copyP)
			if a == 0 {
				break
			}
		}
	}
	merged, e := f35Merge(raw)
	if e != nil {
		return nil, 0, 0, e
	}
	return merged, len(raw), floors, nil
}

// Forecasts need no sensor conditioning; the detailed path counts numerical emission floors.
func f35Advance(parts []f35Particle, m f35Controller, t, c, a int, ob *[2]int) ([]f35Particle, int, error) {
	next, work, _, err := f35AdvanceDetailed(parts, m, t, c, a, ob)
	return next, work, err
}
func f35Plan(m f35Controller, t, c, oddCue, a, goal int) (float64, int, error) {
	if t%2 != 0 || t != m.Clock || goal < 0 || goal > 3 {
		return 0, 0, errF35
	}
	if m.Kind == "four-bank-replay-history" || m.Kind == "history-logistic" {
		return f33Plan(m.Source, c, oddCue, a, goal)
	}
	step1, w1, e := f35Advance(m.Particles, m, t, c, a, nil)
	if e != nil {
		return 0, 0, e
	}
	step2, w2, e := f35Advance(step1, m, t+1, oddCue, 0, nil)
	if e != nil {
		return 0, 0, e
	}
	probability := 0.0
	for _, part := range step2 {
		if part.State == goal {
			probability += part.Probability
		}
	}
	return probability, w1 + w2, e
}
func (m *f35Controller) forgetAtDecision() error {
	if m.Kind != "four-bank-zero-memory" {
		return nil
	}
	p, e := f27Posterior(m.Source.Last)
	if e != nil {
		return e
	}
	m.Particles = nil
	for s, w := range p {
		if w > 0 {
			m.Particles = append(m.Particles, f35Particle{State: s, Probability: w})
		}
	}
	return nil
}
func (m *f35Controller) observe(t, c, a int, next [2]int) error {
	if t != m.Clock {
		return errF35
	}
	if m.Kind != "four-bank-replay-history" && m.Kind != "history-logistic" {
		nextParticles, w, floors, e := f35AdvanceDetailed(m.Particles, *m, t, c, a, &next)
		if e != nil {
			return e
		}
		m.Particles = nextParticles
		m.Propagations += w
		m.LikelihoodFloors += floors
		if len(nextParticles) > m.PeakParticles {
			m.PeakParticles = len(nextParticles)
		}
	}
	if _, _, e := m.Source.nextPred(c, a); e != nil {
		return e
	}
	if e := m.Source.observe(c, a, next, false); e != nil {
		return e
	}
	m.Clock++
	return nil
}
func f35Valid(m f35Controller) bool {
	if f35Underlying(m.Kind) == "" || m.Source.Kind != f35Underlying(m.Kind) || !f32Valid(m.Source) || m.Clock < 0 || m.Clock > 96 || m.Propagations < 0 || m.PeakParticles < 0 || m.LikelihoodFloors < 0 {
		return false
	}
	if m.Source.TransferSeen != m.Clock {
		return false
	}
	if len(m.Particles) > 4096 {
		return false
	}
	if m.Kind == "four-bank-replay-history" || m.Kind == "history-logistic" {
		return len(m.Particles) > 0
	}
	total := 0.0
	for _, p := range m.Particles {
		if p.State < 0 || p.State > 3 || p.Probability < 0 || p.Probability > 1 || math.IsNaN(p.Probability) || math.IsInf(p.Probability, 0) {
			return false
		}
		total += p.Probability
		for _, v := range p.Pending {
			if v.Mask < 1 || v.Mask > 3 || v.Due < m.Clock || v.Due > m.Clock+2 {
				return false
			}
		}
	}
	return len(m.Particles) > 0 && math.Abs(total-1) < 1e-8
}
func f35Save(m f35Controller) ([]byte, error) {
	if !f35Valid(m) {
		return nil, errF35
	}
	return json.Marshal(m)
}
func f35Load(raw []byte) (f35Controller, error) {
	var m f35Controller
	if json.Unmarshal(raw, &m) != nil || !f35Valid(m) {
		return f35Controller{}, errF35
	}
	exact, _ := json.Marshal(m)
	if !bytes.Equal(exact, raw) {
		return f35Controller{}, errF35
	}
	return m, nil
}

type F35Trial struct {
	Kind                                                                                                  string `json:"kind"`
	GoalsHit, Interventions, Opportunities, ObservedTransitions, TrainingSeen                             int
	PhaseHits                                                                                             [4]int  `json:"phase_hits"`
	EarlySwitchHits                                                                                       [3]int  `json:"early_switch_hits"`
	NetReward                                                                                             float64 `json:"net_reward"`
	ModelParameters, TrainingWork, OnlineWork, PlannerWork, Propagations, PeakParticles, LikelihoodFloors int
	GoalsSHA256, ActionsSHA256, SensorsSHA256, DecisionsSHA256, CheckpointSHA256, TerminalSHA256          string
	ColdMatches                                                                                           bool `json:"cold_matches"`
}

func f35Params(kind string) int {
	if kind == "always-zero" {
		return 0
	}
	src := f35Underlying(kind)
	return f32Params(src)
}
func f35Trial(trained [6]f32Model, kind string, seed uint32, sched string, cold bool) (F35Trial, []byte, error) {
	if !f35Known(seed) {
		return F35Trial{}, nil, errF35
	}
	idx := -1
	for j, k := range f35Kinds() {
		if k == kind {
			idx = j
		}
	}
	if idx < 0 {
		return F35Trial{}, nil, errF35
	}
	world, e := f35NewWorld(seed)
	if e != nil {
		return F35Trial{}, nil, e
	}
	trial := F35Trial{Kind: kind, Opportunities: 48, ColdMatches: true}
	var model f35Controller
	var initial []byte
	if kind != "always-zero" {
		sourceIdx := -1
		for i, k := range f33Kinds() {
			if k == f35Underlying(kind) {
				sourceIdx = i
			}
		}
		if sourceIdx < 0 || sourceIdx >= 6 {
			return trial, nil, errF35
		}
		trainedSource := trained[sourceIdx]
		initial, e = f32Save(trainedSource)
		if e != nil {
			return trial, nil, e
		}
		if cold {
			trainedSource, e = f32Load(initial)
			if e != nil {
				return trial, nil, e
			}
		}
		model, e = f35Begin(kind, trainedSource, world.Sensors)
		if e != nil {
			return trial, nil, e
		}
		trial.TrainingSeen = model.Source.TrainingSeen
		trial.TrainingWork = model.Source.Work
		trial.ModelParameters = f35Params(kind)
	} else {
		initial, _ = json.Marshal(struct {
			Kind  string
			Seeds [2]uint32
		}{kind, [2]uint32{331, 337}})
	}
	trial.CheckpointSHA256 = f27Hash(initial)
	var goals []int
	var actions []int
	var sensors [][2]int
	var decisions []f33Decision
	sensors = append(sensors, world.Sensors)
	startWork := model.Source.Work
	for t := 0; t < 96; t += 2 {
		cue, e := f35Cue(seed, sched, t)
		if e != nil {
			return trial, nil, e
		}
		oddCue, e := f35Cue(seed, sched, t+1)
		if e != nil {
			return trial, nil, e
		}
		goal, e := f35Goal(seed, t)
		if e != nil {
			return trial, nil, e
		}
		goals = append(goals, goal)
		choice := 0
		p0, p1 := 0.0, 0.0
		if kind != "always-zero" {
			if e = model.forgetAtDecision(); e != nil {
				return trial, nil, e
			}
			q0, w0, err := f35Plan(model, t, cue, oddCue, 0, goal)
			if err != nil {
				return trial, nil, err
			}
			q1, w1, err := f35Plan(model, t, cue, oddCue, 1, goal)
			if err != nil {
				return trial, nil, err
			}
			p0, p1 = q0, q1
			trial.PlannerWork += w0 + w1
			if p1-p0 > .05 && trial.Interventions < 24 {
				choice = 1
			}
		}
		if choice == 1 {
			trial.Interventions++
		}
		decisions = append(decisions, f33Decision{Goal: goal, Action: choice, P0: p0, P1: p1})
		for sub := 0; sub < 2; sub++ {
			act := 0
			currentCue := oddCue
			if sub == 0 {
				act = choice
				currentCue = cue
			}
			actions = append(actions, act)
			_, next, err := world.step(t+sub, currentCue, act)
			if err != nil {
				return trial, nil, err
			}
			sensors = append(sensors, next)
			if kind != "always-zero" {
				if e = model.observe(t+sub, currentCue, act, next); e != nil {
					return trial, nil, e
				}
			}
		}
		if world.State == goal {
			trial.GoalsHit++
			trial.PhaseHits[t/24]++
			if t >= 24 && t < 28 {
				trial.EarlySwitchHits[0]++
			}
			if t >= 48 && t < 52 {
				trial.EarlySwitchHits[1]++
			}
			if t >= 72 && t < 76 {
				trial.EarlySwitchHits[2]++
			}
		}
	}
	trial.ObservedTransitions = world.Seen
	trial.NetReward = float64(trial.GoalsHit) - .05*float64(trial.Interventions)
	if kind != "always-zero" {
		trial.OnlineWork = model.Source.Work - startWork
		trial.Propagations = model.Propagations
		trial.PeakParticles = model.PeakParticles
		trial.LikelihoodFloors = model.LikelihoodFloors
	}
	bg, _ := json.Marshal(goals)
	trial.GoalsSHA256 = f27Hash(bg)
	ba, _ := json.Marshal(actions)
	trial.ActionsSHA256 = f27Hash(ba)
	bs, _ := json.Marshal(sensors)
	trial.SensorsSHA256 = f27Hash(bs)
	bd, _ := json.Marshal(decisions)
	trial.DecisionsSHA256 = f27Hash(bd)
	var terminal []byte
	if kind != "always-zero" {
		terminal, e = f35Save(model)
	} else {
		terminal, _ = json.Marshal(struct {
			Kind                    string
			Seed                    uint32
			GoalsHit, Interventions int
		}{kind, seed, trial.GoalsHit, trial.Interventions})
	}
	if e != nil {
		return trial, nil, e
	}
	trial.TerminalSHA256 = f27Hash(terminal)
	return trial, terminal, nil
}

type F35Arm struct {
	Seed                                            uint32      `json:"seed"`
	Schedule                                        string      `json:"schedule"`
	Trials                                          [8]F35Trial `json:"trials"`
	BestConventionalHits                            int         `json:"best_conventional_hits"`
	BestConventionalNet                             float64     `json:"best_conventional_net"`
	GainGoals, GainReplay, GainZeroMemory, GainCold int
	GainNet                                         float64
	Passes                                          bool `json:"passes"`
}
type F35Report struct {
	Schema, Parent, Classification                                                                                        string
	TrainingWorlds                                                                                                        [2]uint32
	TransferWorlds                                                                                                        [4]uint32
	TrainingTransitions, TransferTransitions, Decisions, Budget                                                           int
	MinGoalsGain, MinAblationGain                                                                                         int
	MinNetGain                                                                                                            float64
	Arms                                                                                                                  [4]F35Arm
	Passing                                                                                                               int
	DevelopmentOnly, EarlierNegativesPreserved                                                                            bool
	FirstUseConsumed, ScientificAccepted, OwnerEligible, DispatchAuthorized, WholeProcessCostProven, MatchedComputeProven bool
	DigestSHA256                                                                                                          string
}

func f35Digest(r F35Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func f35Calculate() (F35Report, error) {
	r := F35Report{Schema: F35Schema, Parent: F35Parent, TrainingWorlds: [2]uint32{331, 337}, TransferWorlds: [4]uint32{389, 397, 401, 409}, TrainingTransitions: 256, TransferTransitions: 96, Decisions: 48, Budget: 24, MinGoalsGain: 3, MinAblationGain: 4, MinNetGain: 2.5, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	trained, e := f33Train()
	if e != nil {
		return r, e
	}
	for i, world := range f35Worlds() {
		arm := F35Arm{Seed: world.Seed, Schedule: world.Schedule}
		for j, k := range f35Kinds() {
			cold, cb, err := f35Trial(trained, k, world.Seed, world.Schedule, true)
			if err != nil {
				return r, err
			}
			warm, wb, err := f35Trial(trained, k, world.Seed, world.Schedule, false)
			if err != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return r, errF35
			}
			arm.Trials[j] = cold
		}
		for j, v := range arm.Trials {
			if v.Kind != f35Kinds()[j] || v.Opportunities != 48 || v.ObservedTransitions != 96 || v.Interventions < 0 || v.Interventions > 24 || v.GoalsHit < 0 || v.GoalsHit > 48 || v.GoalsSHA256 != arm.Trials[0].GoalsSHA256 || !v.ColdMatches {
				return r, errF35
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
		arm.GainReplay = arm.Trials[0].GoalsHit - arm.Trials[4].GoalsHit
		arm.GainZeroMemory = arm.Trials[0].GoalsHit - arm.Trials[5].GoalsHit
		arm.GainCold = arm.Trials[0].GoalsHit - arm.Trials[6].GoalsHit
		arm.Passes = arm.GainGoals >= 3 && arm.GainNet >= 2.5 && arm.GainReplay >= 4 && arm.GainZeroMemory >= 4 && arm.GainCold >= 4
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F35NoGo
	if r.Passing == 4 {
		r.Classification = F35Signal
	}
	r.DigestSHA256 = f35Digest(r)
	return r, nil
}

var f35Once sync.Once
var f35Cached F35Report
var f35Err error

func F35Development() (F35Report, error) {
	f35Once.Do(func() { f35Cached, f35Err = f35Calculate() })
	return f35Cached, f35Err
}
func F35Validate(r F35Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f35Digest(r) || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven {
		return errF35
	}
	expected, e := F35Development()
	if e != nil || !reflect.DeepEqual(r, expected) {
		return errF35
	}
	return nil
}
