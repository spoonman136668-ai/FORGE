// Eureka F37: matched-trajectory prequential calibration of existing F36 learned sources.
// Diagnostic development only. This file does not change F36 model or scientific classifications.
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
	F37Schema    = "forge.native-discovery.observation-calibration.dev.v1"
	F37Parent    = "3cdff5ba4454543db30e1f54b3c07b12cdd8336b"
	F37CalSignal = "F37_CALIBRATION_DEV_SIGNAL"
	F37CalNoGo   = "F37_CALIBRATION_DEV_NO_GO"
	F37Epsilon   = .025
)

var errF37 = errors.New("FORGE_EUREKA_F37_SOURCE_OR_AUTHORITY_INVALID")

// This deterministic forecast uses only an online policy's belief, its issued
// event receipts, and the current actual action. The clean state never enters.
func f37NextPrior(m f36Model, t, cue, action int, eps float64) ([4][16]float64, error) {
	var prior [4][16]float64
	if !m.Have || t < 0 || t >= 96 || cue < 0 || cue >= 4 || action < 0 || action > 2 || eps < 0 || eps >= 1 {
		return prior, errF37
	}
	for k := 0; k < 4; k++ {
		delta := 0
		for _, ev := range m.Events[k] {
			if ev.Due < t || ev.Mask < 1 || ev.Mask > 15 {
				return prior, errF37
			}
			if ev.Due == t {
				delta ^= ev.Mask
			}
		}
		if action > 0 {
			spec := m.Templates[k][cue][action-1]
			if spec.Mask < 1 || spec.Mask > 15 || spec.Lag < 1 || spec.Lag > 3 {
				return prior, errF37
			}
			if spec.Lag == 1 {
				delta ^= spec.Mask
			}
		}
		for s, x := range m.Beliefs[k] {
			if x < 0 || math.IsNaN(x) || math.IsInf(x, 0) {
				return prior, errF37
			}
			prior[k][s^delta] += x * (1 - eps)
		}
		for s := 0; s < 16; s++ {
			prior[k][s] += eps / 16
		}
	}
	return prior, nil
}

func f37Evidence(m f36Model, t, cue, action int, next [2]int, eps float64) ([4][16]float64, [4]float64, float64, error) {
	var z [4]float64
	prior, e := f37NextPrior(m, t, cue, action, eps)
	if e != nil {
		return prior, z, 0, e
	}
	p := 0.0
	for k := 0; k < 4; k++ {
		for s, x := range prior[k] {
			z[k] += x * f36Likelihood(next, s)
		}
		p += m.Weights[k] * z[k]
	}
	if !f36FiniteF37(p) {
		return prior, z, 0, errF37
	}
	return prior, z, p, nil
}
func f36FiniteF37(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x, 0) && x >= 0 }

// Proper emission-conditioned Bayes update with frozen epsilon transition prior.
// The original F36 observe remains completely unchanged for the legacy control.
func f37CalibratedObserve(m *f36Model, t, c, a int, next [2]int) error {
	if !m.Have || m.Kind != "compositional-issued-memory" && m.Kind != "two-bank-issued-bayes" {
		return errF37
	}
	prior, z, _, e := f37Evidence(*m, t, c, a, next, F37Epsilon)
	if e != nil {
		return e
	}
	nextWeights := [4]float64{}
	total := 0.0
	for k := 0; k < 4; k++ {
		if z[k] <= 0 {
			return errF37
		} // no invented normalization: epsilon guarantees support
		for s := 0; s < 16; s++ {
			m.Beliefs[k][s] = prior[k][s] * f36Likelihood(next, s) / z[k]
		}
		nextWeights[k] = (.95*m.Weights[k] + .05/4) * z[k]
		total += nextWeights[k]
		if a > 0 {
			sp := m.Templates[k][c][a-1]
			m.Events[k] = append(m.Events[k], f36Event{Due: t + sp.Lag - 1, Mask: sp.Mask})
		}
		retained := make([]f36Event, 0, len(m.Events[k]))
		for _, ev := range m.Events[k] {
			if ev.Due > t {
				retained = append(retained, ev)
			} else if ev.Due < t {
				return errF37
			}
		}
		m.Events[k] = retained
	}
	if total <= 0 {
		return errF37
	}
	for k := 0; k < 4; k++ {
		m.Weights[k] = nextWeights[k] / total
	}
	m.History[2] = m.History[1]
	m.History[1] = m.History[0]
	m.History[0] = [2]int{c, a}
	m.Previous = next
	m.Work += 4 * 16 * 2
	return nil
}

func f37Decision(m *f36Model, t, c, goal, used int) (int, error) {
	if used < 0 || used > 36 {
		return 0, errF37
	}
	if used >= 36 {
		return 0, nil
	}
	best := -math.MaxFloat64
	selected := 0
	for a := 0; a <= 2; a++ {
		v, e := m.scoreGoal(t, c, a, goal)
		if e != nil {
			return 0, e
		}
		if a > 0 {
			v -= .03
		}
		if v > best+1e-12 {
			best = v
			selected = a
		}
	}
	return selected, nil
}

type F37Trial struct {
	Model                  string  `json:"model"`
	Epsilon                float64 `json:"epsilon"`
	MeanSensorNLL          float64 `json:"mean_sensor_nll"`
	MeanScorerCleanNLL     float64 `json:"mean_scorer_clean_nll"`
	ZeroProbabilityUpdates int     `json:"zero_probability_updates"`
	LegacyFallbacks        int     `json:"legacy_fallbacks"`
	GoalHits               int     `json:"goal_hits"`
	NonzeroActions         int     `json:"nonzero_actions"`
	Work                   int     `json:"work"`
	GoalsSHA256            string  `json:"goals_sha256"`
	ActionsSHA256          string  `json:"actions_sha256"`
	SensorsSHA256          string  `json:"sensors_sha256"`
	CheckpointSHA256       string  `json:"checkpoint_sha256"`
	MidCheckpointSHA256    string  `json:"mid_checkpoint_sha256"`
	TerminalSHA256         string  `json:"terminal_sha256"`
	ColdMatches            bool    `json:"cold_matches"`
}

type F37Compare struct {
	Model              string   `json:"model"`
	Legacy             F37Trial `json:"matched_legacy"`
	Calibrated         F37Trial `json:"matched_calibrated"`
	CalibratedOnPolicy F37Trial `json:"calibrated_on_policy"`
	OriginalF36Goals   int      `json:"original_f36_goal_hits"`
	SensorNLLGain      float64  `json:"sensor_nll_gain"`
	Passes             bool     `json:"passes"`
}
type F37World struct {
	Seed        uint32        `json:"seed"`
	Schedule    string        `json:"schedule"`
	Comparisons [2]F37Compare `json:"comparisons"`
}
type F37Report struct {
	Schema                     string      `json:"schema"`
	Parent                     string      `json:"parent"`
	Classification             string      `json:"classification"`
	TrainingSHA256             string      `json:"training_sha256"`
	TrainingSteps              int         `json:"training_steps"`
	Seeds                      [4]uint32   `json:"seeds"`
	Epsilon                    float64     `json:"epsilon"`
	MinSensorNLLGain           float64     `json:"min_sensor_nll_gain"`
	Worlds                     [4]F37World `json:"worlds"`
	PassingPairs               int         `json:"passing_pairs"`
	DevelopmentOnly            bool        `json:"development_only"`
	PreviousNegativesPreserved bool        `json:"previous_negatives_preserved"`
	FirstUseConsumed           bool        `json:"first_use_consumed"`
	ScientificAccepted         bool        `json:"scientific_accepted"`
	OwnerEligible              bool        `json:"owner_eligible"`
	DispatchAuthorized         bool        `json:"dispatch_authorized"`
	MatchedComputeProven       bool        `json:"matched_compute_proven"`
	DigestSHA256               string      `json:"digest_sha256"`
}

func f37Digest(r F37Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }

// When actions=nil, real actions are selected online by this model. When a
// 96-action trace is supplied, both filters are evaluated on precisely the
// same physical interventions/sensors rather than confounded policy rollouts.
func f37Trial(archive f36Archive, kind string, seed uint32, sched string, eps float64, actions []int, midCold bool) (F37Trial, []int, []byte, error) {
	tr := F37Trial{Model: kind, Epsilon: eps, ColdMatches: true}
	if (kind != "compositional-issued-memory" && kind != "two-bank-issued-bayes") || eps != 0 && eps != F37Epsilon || len(actions) != 0 && len(actions) != 96 {
		return tr, nil, nil, errF37
	}
	ok := false
	for _, w := range f36Worlds() {
		if seed == w.Seed && sched == w.Schedule {
			ok = true
		}
	}
	if !ok {
		return tr, nil, nil, errF37
	}
	world, e := f36NewWorld(seed)
	if e != nil {
		return tr, nil, nil, e
	}
	m, e := f36Init(archive, kind, world.Sensors)
	if e != nil {
		return tr, nil, nil, e
	}
	initial, _ := json.Marshal(m)
	tr.CheckpointSHA256 = f27Hash(initial)
	m, e = f36LoadModel(initial)
	if e != nil {
		return tr, nil, nil, e
	}
	var steps []int
	var goals []int
	var sensors [][2]int
	sensors = append(sensors, world.Sensors)
	sensorLoss, cleanLoss := 0.0, 0.0
	for t := 0; t < 96; t++ {
		c, e := f36Cue(seed, sched, t)
		if e != nil {
			return tr, nil, nil, e
		}
		goal, e := f36Goal(seed, t)
		if e != nil {
			return tr, nil, nil, e
		}
		if t%4 == 0 {
			goals = append(goals, goal)
		}
		var a int
		if len(actions) != 0 {
			// Recompute the same three policy forecasts for work/terminal custody,
			// but execute the precommitted physical action for fair replay.
			_, err := f37Decision(&m, t, c, goal, tr.NonzeroActions)
			if err != nil {
				return tr, nil, nil, err
			}
			a = actions[t]
		} else {
			a, e = f37Decision(&m, t, c, goal, tr.NonzeroActions)
			if e != nil {
				return tr, nil, nil, e
			}
		}
		if a < 0 || a > 2 {
			return tr, nil, nil, errF37
		}
		if a > 0 {
			tr.NonzeroActions++
			if tr.NonzeroActions > 36 {
				return tr, nil, nil, errF37
			}
		}
		steps = append(steps, a)
		actual, next, e := world.step(t, c, a)
		if e != nil {
			return tr, nil, nil, e
		}
		prior, z, sensorP, e := f37Evidence(m, t, c, a, next, eps)
		if e != nil {
			return tr, nil, nil, e
		}
		_ = z
		cleanP := 0.0
		for k := 0; k < 4; k++ {
			cleanP += m.Weights[k] * prior[k][actual]
		}
		sensorLoss -= math.Log(math.Max(sensorP, 1e-12))
		cleanLoss -= math.Log(math.Max(cleanP, 1e-12))
		if sensorP <= 0 {
			tr.ZeroProbabilityUpdates++
		}
		if eps == 0 {
			e = m.observe(t, c, a, next)
		} else {
			e = f37CalibratedObserve(&m, t, c, a, next)
		}
		if e != nil {
			return tr, nil, nil, e
		}
		sensors = append(sensors, next)
		if t%4 == 3 && actual == goal {
			tr.GoalHits++
		}
		if t == 47 {
			checkpoint, _ := json.Marshal(m)
			tr.MidCheckpointSHA256 = f27Hash(checkpoint)
			if midCold {
				m, e = f36LoadModel(checkpoint)
				if e != nil {
					return tr, nil, nil, e
				}
			}
		}
	}
	tr.MeanSensorNLL = sensorLoss / 96
	tr.MeanScorerCleanNLL = cleanLoss / 96
	tr.Work = m.Work
	tr.LegacyFallbacks = m.FloorHits
	raw, _ := json.Marshal(steps)
	tr.ActionsSHA256 = f27Hash(raw)
	raw, _ = json.Marshal(goals)
	tr.GoalsSHA256 = f27Hash(raw)
	raw, _ = json.Marshal(sensors)
	tr.SensorsSHA256 = f27Hash(raw)
	terminal, _ := json.Marshal(m)
	tr.TerminalSHA256 = f27Hash(terminal)
	return tr, steps, terminal, nil
}

var f37Once sync.Once
var f37Cache F37Report
var f37CacheErr error

func f37Calculate() (F37Report, error) {
	r := F37Report{Schema: F37Schema, Parent: F37Parent, Seeds: [4]uint32{439, 443, 449, 457}, Epsilon: F37Epsilon, MinSensorNLLGain: .05, TrainingSteps: 384, DevelopmentOnly: true, PreviousNegativesPreserved: true}
	archive, e := f36Train()
	if e != nil || !f36ValidParams(archive) {
		return F37Report{}, errF37
	}
	r.TrainingSHA256 = archive.TrainSHA256
	original, e := F36Development()
	if e != nil || original.Classification != F36NoGo {
		return F37Report{}, errF37
	}
	for i, w := range f36Worlds() {
		arm := F37World{Seed: w.Seed, Schedule: w.Schedule}
		for j, kind := range [2]string{"compositional-issued-memory", "two-bank-issued-bayes"} {
			// Compute the unchanged legacy on-policy action trace and compare
			// its identity to the previously frozen F36 report.
			legacy, actions, terminal, e := f37Trial(archive, kind, w.Seed, w.Schedule, 0, nil, false)
			if e != nil {
				return F37Report{}, e
			}
			if legacy.ActionsSHA256 != original.Arms[i].Trials[j].ActionsSHA256 || legacy.GoalHits != original.Arms[i].Trials[j].Hits || legacy.LegacyFallbacks != original.Arms[i].Trials[j].FloorHits {
				return F37Report{}, errF37
			}
			legacyCold, _, cb, e := f37Trial(archive, kind, w.Seed, w.Schedule, 0, actions, true)
			if e != nil || !reflect.DeepEqual(legacy, legacyCold) || !bytes.Equal(terminal, cb) {
				return F37Report{}, errF37
			}
			cal, _, cbytes, e := f37Trial(archive, kind, w.Seed, w.Schedule, F37Epsilon, actions, false)
			if e != nil {
				return F37Report{}, e
			}
			calCold, _, ccb, e := f37Trial(archive, kind, w.Seed, w.Schedule, F37Epsilon, actions, true)
			if e != nil || !reflect.DeepEqual(cal, calCold) || !bytes.Equal(cbytes, ccb) {
				return F37Report{}, errF37
			}
			if cal.ActionsSHA256 != legacy.ActionsSHA256 || cal.SensorsSHA256 != legacy.SensorsSHA256 || cal.GoalsSHA256 != legacy.GoalsSHA256 {
				return F37Report{}, errF37
			}
			online, _, onlineBytes, e := f37Trial(archive, kind, w.Seed, w.Schedule, F37Epsilon, nil, false)
			if e != nil {
				return F37Report{}, e
			}
			onlineCold, _, onlineCB, e := f37Trial(archive, kind, w.Seed, w.Schedule, F37Epsilon, nil, true)
			if e != nil || !reflect.DeepEqual(online, onlineCold) || !bytes.Equal(onlineBytes, onlineCB) {
				return F37Report{}, errF37
			}
			comp := F37Compare{Model: kind, Legacy: legacy, Calibrated: cal, CalibratedOnPolicy: online, OriginalF36Goals: original.Arms[i].Trials[j].Hits, SensorNLLGain: legacy.MeanSensorNLL - cal.MeanSensorNLL}
			comp.Passes = comp.SensorNLLGain >= .05 && cal.ZeroProbabilityUpdates == 0 && legacy.LegacyFallbacks > 0
			if comp.Passes {
				r.PassingPairs++
			}
			arm.Comparisons[j] = comp
		}
		r.Worlds[i] = arm
	}
	r.Classification = F37CalNoGo
	if r.PassingPairs == 8 {
		r.Classification = F37CalSignal
	}
	r.DigestSHA256 = f37Digest(r)
	return r, nil
}
func F37Development() (F37Report, error) {
	f37Once.Do(func() { f37Cache, f37CacheErr = f37Calculate() })
	return f37Cache, f37CacheErr
}
func F37Validate(r F37Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f37Digest(r) || !r.DevelopmentOnly || !r.PreviousNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.MatchedComputeProven || r.Epsilon != F37Epsilon || r.MinSensorNLLGain != .05 {
		return errF37
	}
	expected, e := F37Development()
	if e != nil || !reflect.DeepEqual(r, expected) {
		return errF37
	}
	return nil
}
