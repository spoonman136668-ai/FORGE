// F38 uses fresh, preregistered DEV transfer seeds without altering F36/F37 training or controls.
// It is not scientific first-use, matched-compute qualification or execution authority.
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
	F38Schema = "forge.native-discovery.heldout-calibration-goal-control.dev.v1"
	F38Parent = "43722d6274160e1bffbce5b4b049ddc9535b6434"
	F38NoGo   = "F38_DEV_NO_GO"
	F38Signal = "F38_DEV_SIGNAL_UNVERIFIED"
)

var errF38 = errors.New("FORGE_EUREKA_F38_SOURCE_OR_AUTHORITY_INVALID")

type f38WorldSpec struct {
	Seed            uint32
	Schedule        string
	StartsA, NovelC bool
}

func f38Worlds() [4]f38WorldSpec {
	return [4]f38WorldSpec{
		{461, "balanced", true, true},
		{463, "skewed", false, false},
		{467, "balanced", true, false},
		{479, "skewed", false, true},
	}
}
func f38WorldFor(seed uint32, sched string) (f38WorldSpec, error) {
	for _, w := range f38Worlds() {
		if seed == w.Seed && sched == w.Schedule {
			return w, nil
		}
	}
	return f38WorldSpec{}, errF38
}
func f38Phase(w f38WorldSpec, t int) (byte, error) {
	if t < 0 || t >= 96 {
		return 0, errF38
	}
	switch t / 24 {
	case 0, 2:
		if w.StartsA {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if w.StartsA {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if w.NovelC {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF38
}
func f38Cue(w f38WorldSpec, t int) (int, error) {
	if t < 0 || t >= 96 {
		return 0, errF38
	}
	if w.Schedule == "balanced" {
		return (t/2 + int(w.Seed%4)) % 4, nil
	}
	if w.Schedule == "skewed" {
		if t%8 == 6 {
			return (t/4 + int(w.Seed%4)) % 4, nil
		}
		return (t/4 + int(w.Seed%2)) % 2, nil
	}
	return 0, errF38
}
func f38Goal(w f38WorldSpec, t int) (int, error) {
	if t < 0 || t >= 96 {
		return 0, errF38
	}
	return int(f27Mix(w.Seed^uint32(t/4+1)*0x7f4a7c15^0x52dce729) & 15), nil
}
func f38Sensor(seed uint32, t, clean, sensor int) (int, error) {
	valid := false
	for _, w := range f38Worlds() {
		if w.Seed == seed {
			valid = true
		}
	}
	if !valid || t < 0 || t > 96 || clean < 0 || clean > 15 || sensor < 0 || sensor > 1 {
		return 0, errF38
	}
	u := f27Mix(seed^uint32(t+1)*0x9e3779b9^uint32(sensor+1)*0x85ebca6b^0x6a09e667) % 100
	threshold := uint32(92)
	if sensor == 1 {
		threshold = 84
	}
	if u < threshold {
		return clean, nil
	}
	bit := f27Mix(seed^uint32(t+1)*0x27d4eb2d^uint32(sensor+1)*0x165667b1) & 3
	return clean ^ (1 << bit), nil
}

type f38World struct {
	Spec        f38WorldSpec
	State, Seen int
	Pending     []f36Event
	Sensors     [2]int
}

func f38NewWorld(seed uint32, sched string) (f38World, error) {
	spec, e := f38WorldFor(seed, sched)
	if e != nil {
		return f38World{}, e
	}
	w := f38World{Spec: spec, State: int(f27Mix(seed^0x4cf5ad43) & 15)}
	for j := 0; j < 2; j++ {
		v, e := f38Sensor(seed, 0, w.State, j)
		if e != nil {
			return f38World{}, e
		}
		w.Sensors[j] = v
	}
	return w, nil
}
func (w *f38World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || c < 0 || c > 3 || a < 0 || a > 2 {
		return 0, [2]int{}, errF38
	}
	phase, e := f38Phase(w.Spec, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	if a > 0 {
		table, e := f36Law(phase)
		if e != nil {
			return 0, [2]int{}, e
		}
		sp := table[c][a-1]
		w.Pending = append(w.Pending, f36Event{Due: t + sp.Lag - 1, Mask: sp.Mask})
	}
	keep := make([]f36Event, 0, len(w.Pending))
	for _, ev := range w.Pending {
		if ev.Due < t {
			return 0, [2]int{}, errF38
		}
		if ev.Due == t {
			w.State ^= ev.Mask
		} else {
			keep = append(keep, ev)
		}
	}
	w.Pending = keep
	w.Seen++
	var obs [2]int
	for j := 0; j < 2; j++ {
		v, e := f38Sensor(w.Spec.Seed, w.Seen, w.State, j)
		if e != nil {
			return 0, [2]int{}, e
		}
		obs[j] = v
	}
	w.Sensors = obs
	return w.State, obs, nil
}

// Same epsilon filter as F37, generalized only to the already trained pooled control.
// For four-bank and two-bank, call the exact F37 implementation.
func f38Observe(m *f36Model, t, c, a int, next [2]int, eps float64) error {
	if eps == 0 {
		return m.observe(t, c, a, next)
	}
	if eps != F37Epsilon {
		return errF38
	}
	if m.Kind == "compositional-issued-memory" || m.Kind == "two-bank-issued-bayes" {
		return f37CalibratedObserve(m, t, c, a, next)
	}
	if m.Kind != "pooled-issued-bayes" {
		return errF38
	}
	prior, z, _, e := f37Evidence(*m, t, c, a, next, eps)
	if e != nil {
		return e
	}
	var nw [4]float64
	total := 0.0
	for k := 0; k < 4; k++ {
		if z[k] <= 0 {
			return errF38
		}
		for s := 0; s < 16; s++ {
			m.Beliefs[k][s] = prior[k][s] * f36Likelihood(next, s) / z[k]
		}
		nw[k] = (.95*m.Weights[k] + .05/4) * z[k]
		total += nw[k]
		if a > 0 {
			sp := m.Templates[k][c][a-1]
			m.Events[k] = append(m.Events[k], f36Event{Due: t + sp.Lag - 1, Mask: sp.Mask})
		}
		kept := make([]f36Event, 0, len(m.Events[k]))
		for _, ev := range m.Events[k] {
			if ev.Due < t {
				return errF38
			}
			if ev.Due > t {
				kept = append(kept, ev)
			}
		}
		m.Events[k] = kept
	}
	if total <= 0 {
		return errF38
	}
	for k := 0; k < 4; k++ {
		m.Weights[k] = nw[k] / total
	}
	m.History[2] = m.History[1]
	m.History[1] = m.History[0]
	m.History[0] = [2]int{c, a}
	m.Previous = next
	m.Work += 4 * 16 * 2
	return nil
}

type F38Trial struct {
	Model                                                                        string  `json:"model"`
	MeanSensorNLL                                                                float64 `json:"mean_sensor_nll"`
	ScorerCleanNLL                                                               float64 `json:"scorer_clean_nll"`
	GoalHits, ReturnHits, NovelHits, Actions, LegacyFallbacks, Unsupported, Work int
	NetReward                                                                    float64 `json:"net_reward"`
	TrainingTransitions                                                          int     `json:"training_transitions"`
	GoalsSHA256                                                                  string  `json:"goals_sha256"`
	ActionsSHA256                                                                string  `json:"actions_sha256"`
	SensorsSHA256                                                                string  `json:"sensors_sha256"`
	CheckpointSHA256                                                             string  `json:"checkpoint_sha256"`
	MidCheckpointSHA256                                                          string  `json:"mid_checkpoint_sha256"`
	TerminalSHA256                                                               string  `json:"terminal_sha256"`
	ColdMatches                                                                  bool    `json:"cold_matches"`
}

func f38Kinds() [5]string {
	return [5]string{"compositional-issued-memory", "two-bank-issued-bayes", "pooled-issued-bayes", "history-logistic", "always-zero"}
}

// fixedActions: nil for on-policy, 96 actual choices for matched replay.
// A cold restore at t47 is compared against uninterrupted warm execution.
func f38Trial(archive f36Archive, logistic f36Model, kind string, seed uint32, sched string, eps float64, fixedActions []int, cold bool) (F38Trial, []int, []byte, error) {
	tr := F38Trial{Model: kind, ColdMatches: true, TrainingTransitions: 384}
	if eps != 0 && eps != F37Epsilon {
		return tr, nil, nil, errF38
	}
	if len(fixedActions) != 0 && len(fixedActions) != 96 {
		return tr, nil, nil, errF38
	}
	validKind := false
	for _, k := range f38Kinds() {
		if kind == k {
			validKind = true
		}
	}
	if !validKind {
		return tr, nil, nil, errF38
	}
	if kind == "history-logistic" && eps != 0 || kind == "always-zero" && eps != 0 {
		return tr, nil, nil, errF38
	}
	world, e := f38NewWorld(seed, sched)
	if e != nil {
		return tr, nil, nil, e
	}
	m, e := f36Init(archive, kind, world.Sensors)
	if e != nil {
		return tr, nil, nil, e
	}
	if kind == "history-logistic" {
		m.Logistic = logistic.Logistic
	}
	ck, _ := json.Marshal(m)
	tr.CheckpointSHA256 = f27Hash(ck)
	if cold {
		m, e = f36LoadModel(ck)
		if e != nil {
			return tr, nil, nil, e
		}
	}
	actions := make([]int, 0, 96)
	sensors := make([][2]int, 0, 97)
	goals := make([]int, 0, 24)
	sensors = append(sensors, world.Sensors)
	loss, sClean := 0.0, 0.0
	for t := 0; t < 96; t++ {
		cue, e := f38Cue(world.Spec, t)
		if e != nil {
			return tr, nil, nil, e
		}
		goal, e := f38Goal(world.Spec, t)
		if e != nil {
			return tr, nil, nil, e
		}
		if t%4 == 0 {
			goals = append(goals, goal)
		}
		act := 0
		if fixedActions != nil {
			act = fixedActions[t]
			// Charge the same decision forecasting work on replay.
			if kind != "always-zero" && kind != "history-logistic" {
				if _, e = f37Decision(&m, t, cue, goal, tr.Actions); e != nil {
					return tr, nil, nil, e
				}
			}
		} else if kind == "always-zero" {
			act = 0
		} else if kind == "history-logistic" {
			if tr.Actions < 36 {
				best := -math.MaxFloat64
				for a := 0; a < 3; a++ {
					score, er := m.logisticGoal(t, cue, a, goal)
					if er != nil {
						return tr, nil, nil, er
					}
					if a > 0 {
						score -= .03
					}
					if score > best+1e-12 {
						act = a
						best = score
					}
				}
			}
		} else {
			act, e = f37Decision(&m, t, cue, goal, tr.Actions)
			if e != nil {
				return tr, nil, nil, e
			}
		}
		if act < 0 || act > 2 {
			return tr, nil, nil, errF38
		}
		if act > 0 {
			tr.Actions++
			if tr.Actions > 36 {
				return tr, nil, nil, errF38
			}
		}
		actions = append(actions, act)
		clean, next, e := world.step(t, cue, act)
		if e != nil {
			return tr, nil, nil, e
		}
		sensors = append(sensors, next)
		if kind != "history-logistic" && kind != "always-zero" {
			prior, z, p, e := f37Evidence(m, t, cue, act, next, eps)
			if e != nil {
				return tr, nil, nil, e
			}
			cleanP := 0.0
			for k := 0; k < 4; k++ {
				cleanP += m.Weights[k] * prior[k][clean]
				if z[k] == 0 {
					tr.Unsupported++
				}
			}
			loss -= math.Log(math.Max(p, 1e-12))
			sClean -= math.Log(math.Max(cleanP, 1e-12))
			if e = f38Observe(&m, t, cue, act, next, eps); e != nil {
				return tr, nil, nil, e
			}
		} else if kind == "history-logistic" {
			if e = m.logisticUpdate(cue, act, next); e != nil {
				return tr, nil, nil, e
			}
		}
		if t%4 == 3 && clean == goal {
			tr.GoalHits++
			if t/4 >= 12 && t/4 <= 17 {
				tr.ReturnHits++
			}
			if t/4 >= 18 {
				tr.NovelHits++
			}
		}
		if t == 47 {
			raw, _ := json.Marshal(m)
			tr.MidCheckpointSHA256 = f27Hash(raw)
			if cold {
				m, e = f36LoadModel(raw)
				if e != nil {
					return tr, nil, nil, e
				}
			}
		}
	}
	if kind != "always-zero" && kind != "history-logistic" {
		tr.MeanSensorNLL = loss / 96
		tr.ScorerCleanNLL = sClean / 96
	}
	tr.Work = m.Work
	tr.LegacyFallbacks = m.FloorHits
	tr.NetReward = float64(tr.GoalHits) - .03*float64(tr.Actions)
	raw, _ := json.Marshal(actions)
	tr.ActionsSHA256 = f27Hash(raw)
	raw, _ = json.Marshal(sensors)
	tr.SensorsSHA256 = f27Hash(raw)
	raw, _ = json.Marshal(goals)
	tr.GoalsSHA256 = f27Hash(raw)
	terminal, _ := json.Marshal(m)
	tr.TerminalSHA256 = f27Hash(terminal)
	return tr, actions, terminal, nil
}

type F38Paired struct {
	Family        string   `json:"family"`
	Legacy        F38Trial `json:"legacy"`
	Calibrated    F38Trial `json:"calibrated"`
	SensorNLLGain float64  `json:"sensor_nll_gain"`
	Passes        bool     `json:"passes"`
}
type F38World struct {
	Seed                 uint32       `json:"seed"`
	Schedule             string       `json:"schedule"`
	Matched              [2]F38Paired `json:"matched_comparison"`
	OnPolicy             [5]F38Trial  `json:"on_policy"`
	BestConventionalHits int          `json:"best_conventional_hits"`
	BestConventionalNet  float64      `json:"best_conventional_net"`
	CandidateGoalPass    bool         `json:"candidate_goal_pass"`
}
type F38Report struct {
	Schema, Parent, Classification, TrainingSHA256                                                string
	Seeds                                                                                         [4]uint32
	Epsilon, MinSensorGain, MinNetGain                                                            float64
	MinGoalGain                                                                                   int
	TrainingSteps, PassingCalibration, PassingControl                                             int
	CalibrationPass, ControlPass                                                                  bool
	Worlds                                                                                        [4]F38World
	DevelopmentOnly, PreviousNegativesPreserved                                                   bool
	FirstUseConsumed, ScientificAccepted, OwnerEligible, DispatchAuthorized, MatchedComputeProven bool
	DigestSHA256                                                                                  string
}

func f38Digest(r F38Report) string {
	r.DigestSHA256 = ""
	raw, _ := json.Marshal(r)
	return f27Hash(raw)
}
func f38Compute() (F38Report, error) {
	r := F38Report{Schema: F38Schema, Parent: F38Parent, Seeds: [4]uint32{461, 463, 467, 479}, Epsilon: F37Epsilon, MinSensorGain: .05, MinGoalGain: 2, MinNetGain: 1.5, TrainingSteps: 384, DevelopmentOnly: true, PreviousNegativesPreserved: true}
	archive, e := f36Train()
	if e != nil || !f36ValidParams(archive) {
		return F38Report{}, errF38
	}
	logistic, e := f36TrainLogistic()
	if e != nil {
		return F38Report{}, e
	}
	r.TrainingSHA256 = archive.TrainSHA256
	for i, w := range f38Worlds() {
		world := F38World{Seed: w.Seed, Schedule: w.Schedule}
		for j, kind := range [2]string{"compositional-issued-memory", "two-bank-issued-bayes"} {
			legacy, actions, lend, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, 0, nil, false)
			if e != nil {
				return F38Report{}, e
			}
			legacyCold, _, lcend, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, 0, actions, true)
			if e != nil || !reflect.DeepEqual(legacy, legacyCold) || !bytes.Equal(lend, lcend) {
				return F38Report{}, errF38
			}
			cal, _, cend, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, F37Epsilon, actions, false)
			if e != nil {
				return F38Report{}, e
			}
			calCold, _, ccend, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, F37Epsilon, actions, true)
			if e != nil || !reflect.DeepEqual(cal, calCold) || !bytes.Equal(cend, ccend) {
				return F38Report{}, errF38
			}
			if cal.ActionsSHA256 != legacy.ActionsSHA256 || cal.SensorsSHA256 != legacy.SensorsSHA256 || cal.GoalsSHA256 != legacy.GoalsSHA256 {
				return F38Report{}, errF38
			}
			pair := F38Paired{Family: kind, Legacy: legacy, Calibrated: cal, SensorNLLGain: legacy.MeanSensorNLL - cal.MeanSensorNLL}
			pair.Passes = pair.SensorNLLGain >= .05 && cal.Unsupported == 0 && legacy.LegacyFallbacks > 0
			if pair.Passes {
				r.PassingCalibration++
			}
			world.Matched[j] = pair
		}
		for j, kind := range f38Kinds() {
			epsilon := F37Epsilon
			if kind == "history-logistic" || kind == "always-zero" {
				epsilon = 0
			}
			tr, _, terminal, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, epsilon, nil, false)
			if e != nil {
				return F38Report{}, e
			}
			c, _, ct, e := f38Trial(archive, logistic, kind, w.Seed, w.Schedule, epsilon, nil, true)
			if e != nil || !reflect.DeepEqual(tr, c) || !bytes.Equal(terminal, ct) {
				return F38Report{}, errF38
			}
			world.OnPolicy[j] = tr
			if j >= 1 && j <= 3 {
				if tr.GoalHits > world.BestConventionalHits {
					world.BestConventionalHits = tr.GoalHits
				}
				if tr.NetReward > world.BestConventionalNet {
					world.BestConventionalNet = tr.NetReward
				}
			}
			if tr.GoalHits < 0 || tr.GoalHits > 24 || tr.Actions > 36 || tr.TrainingTransitions != 384 {
				return F38Report{}, errF38
			}
		}
		candidate := world.OnPolicy[0]
		two := world.OnPolicy[1]
		world.CandidateGoalPass = candidate.GoalHits >= world.BestConventionalHits+2 && candidate.NetReward >= world.BestConventionalNet+1.5 && float64(candidate.Work) <= float64(two.Work)*1.10
		if world.CandidateGoalPass {
			r.PassingControl++
		}
		r.Worlds[i] = world
	}
	r.CalibrationPass = r.PassingCalibration == 8
	r.ControlPass = r.PassingControl == 4
	r.Classification = F38NoGo
	if r.CalibrationPass && r.ControlPass {
		r.Classification = F38Signal
	}
	r.DigestSHA256 = f38Digest(r)
	return r, nil
}

var f38Once sync.Once
var f38Report F38Report
var f38Err error

func F38Development() (F38Report, error) {
	f38Once.Do(func() { f38Report, f38Err = f38Compute() })
	return f38Report, f38Err
}
func F38Validate(r F38Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f38Digest(r) || r.Schema != F38Schema || r.Parent != F38Parent || !r.DevelopmentOnly || !r.PreviousNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.MatchedComputeProven || r.Epsilon != F37Epsilon || r.MinSensorGain != .05 || r.MinGoalGain != 2 || r.MinNetGain != 1.5 {
		return errF38
	}
	expected, e := F38Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF38
	}
	return nil
}
