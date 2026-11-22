// Eureka F31: coverage-complete causal contrast and direct observation preserves evidence.
// Synthetic DEV only. No first-use, owner, controller, research-loop or deployment hooks.
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
	F31Schema        = "forge.native-discovery.covered-direct-contrast.dev.v1"
	F31NoGo          = "F31_DEV_NO_GO"
	F31Signal        = "F31_DEV_SIGNAL_UNVERIFIED"
	F31Parent        = "0f979891553edb6c08da0e2426f288a5768c75a5"
	F31TrainSteps    = 128
	F31TransferSteps = 48
)

var errF31 = errors.New("FORGE_EUREKA_F31_SOURCE_OR_AUTHORITY_INVALID")

func f31Kinds() [8]string {
	return [8]string{
		"direct-contrast", "stationary-delta", "markov-bayes", "online-softmax",
		"factorized-bayes", "direct-bank", "no-cross", "wrong-action",
	}
}
func f31Worlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{
		{307, "balanced"}, {311, "skewed"}, {313, "balanced"}, {317, "skewed"},
	}
}
func f31Known(seed uint32) bool {
	if seed == 301 || seed == 303 {
		return true
	}
	for _, w := range f31Worlds() {
		if seed == w.Seed {
			return true
		}
	}
	return false
}
func f31Training(seed uint32) bool { return seed == 301 || seed == 303 }
func f31Cue(seed uint32, sched string, t int) (int, error) {
	if !f31Known(seed) || t < 0 || (f31Training(seed) && t >= 64) || (!f31Training(seed) && t >= F31TransferSteps) {
		return 0, errF31
	}
	if f31Training(seed) {
		if sched != "balanced" {
			return 0, errF31
		}
		return (t / 2) % 4, nil
	}
	switch sched {
	case "balanced":
		return (t/2 + int(seed%4)) % 4, nil
	case "skewed":
		if t%5 == 4 {
			return (t/5 + int(seed%4)) % 4, nil
		}
		return (t/5 + int(seed%2)) % 2, nil
	}
	return 0, errF31
}
func f31Action(seed uint32, t int) (int, error) {
	if !f31Known(seed) || t < 0 || (f31Training(seed) && t >= 64) || (!f31Training(seed) && t >= F31TransferSteps) {
		return 0, errF31
	}
	return t % 2, nil
}
func f31Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f31Known(seed) || t < 0 || (f31Training(seed) && t > 64) || (!f31Training(seed) && t > F31TransferSteps) || clean < 0 || clean > 3 || sensor < 0 || sensor > 1 {
		return 0, errF31
	}
	u := f27Mix(seed^uint32(t+1)*0x9e3779b9^uint32(sensor+1)*0x85ebca6b^0x6a09e667) % 100
	if sensor == 0 {
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

// Physical hidden law and phase are *only* accessed by the simulator/scorer.
func f31Phase(seed uint32, t int) (byte, error) {
	if !f31Known(seed) || t < 0 || (f31Training(seed) && t >= 64) || (!f31Training(seed) && t >= F31TransferSteps) {
		return 0, errF31
	}
	if seed == 301 {
		return 'A', nil
	}
	if seed == 303 {
		return 'B', nil
	}
	startsA := seed == 307 || seed == 313
	switch t / 12 {
	case 0, 2:
		if startsA {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if startsA {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if seed == 307 || seed == 317 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF31
}

type f31World struct {
	Seed            uint32
	Schedule        string
	S, Offset, Seen int
	Sensors         [2]int
}

func f31NewWorld(seed uint32, sched string) (f31World, error) {
	if _, e := f31Cue(seed, sched, 0); e != nil {
		return f31World{}, e
	}
	w := f31World{Seed: seed, Schedule: sched, S: int(f27Mix(seed^0x4cf5ad43) & 3), Offset: int(f27Mix(seed^0x6d2b79f5) & 3)}
	for i := 0; i < 2; i++ {
		v, e := f31Sensor(seed, 0, (w.S+w.Offset)%4, i)
		if e != nil {
			return f31World{}, e
		}
		w.Sensors[i] = v
	}
	return w, nil
}
func (w *f31World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || c < 0 || c > 3 || a < 0 || a > 1 {
		return 0, [2]int{}, errF31
	}
	law, e := f31Phase(w.Seed, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	base, effect, e := f28Law(law, c)
	if e != nil {
		return 0, [2]int{}, e
	}
	w.S = (w.S + base + a*effect) % 4
	w.Seen++
	clean := (w.S + w.Offset) % 4
	var next [2]int
	for i := 0; i < 2; i++ {
		v, e := f31Sensor(w.Seed, w.Seen, clean, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = v
	}
	w.Sensors = next
	return clean, next, nil
}
func f31Coverage() ([2][4][2]int, error) {
	var out [2][4][2]int
	for j, seed := range [2]uint32{301, 303} {
		for t := 0; t < 64; t++ {
			c, e := f31Cue(seed, "balanced", t)
			if e != nil {
				return out, e
			}
			a, e := f31Action(seed, t)
			if e != nil {
				return out, e
			}
			out[j][c][a]++
		}
	}
	return out, nil
}
func f31IsDirect(kind string) bool {
	return kind == "direct-contrast" || kind == "direct-bank" || kind == "no-cross" || kind == "wrong-action"
}
func f31NativeMode(kind string) string {
	switch kind {
	case "stationary-delta":
		return "recurrent-causal-delta"
	case "markov-bayes":
		return "markov-bayes"
	case "online-softmax":
		return "online-softmax"
	}
	return ""
}

type f31Model struct {
	Mode         string              `json:"mode"`
	Bank         [2][4][2][4]float64 `json:"banks"`
	Weight       [4][4]float64       `json:"component_weights"`
	Belief       [4]float64          `json:"state_belief"`
	Prev         [2]int              `json:"previous_observation"`
	HasWorld     bool                `json:"has_world"`
	TrainingSeen int                 `json:"training_seen"`
	TransferSeen int                 `json:"transfer_seen"`
	Work         int                 `json:"work"`
}

func (m *f31Model) beginWorld(obs [2]int) error {
	p, e := f27Posterior(obs)
	if e != nil {
		return errF31
	}
	m.Belief = p
	m.Prev = obs
	m.HasWorld = true
	for c := 0; c < 4; c++ {
		if m.Mode == "no-cross" || m.Mode == "direct-bank" {
			m.Weight[c] = [4]float64{.5, 0, 0, .5}
		} else {
			m.Weight[c] = [4]float64{.25, .25, .25, .25}
		}
	}
	return nil
}
func f31ArgMax(p [4]float64) int { return f27ArgMax(p) }
func (m *f31Model) pairDeltas(c, a int) ([4][4]float64, error) {
	var q [4][4]float64
	if c < 0 || c > 3 || a < 0 || a > 1 {
		return q, errF31
	}
	for k := 0; k < 4; k++ {
		base, eff := k/2, k%2
		if a == 0 {
			q[k] = f28DeltaProb(m.Bank[base], c, 0)
			continue
		}
		if base == eff {
			q[k] = f28DeltaProb(m.Bank[base], c, 1)
			continue
		}
		// Crucial difference to F29: *no* double baseline convolution.
		q0base := f28DeltaProb(m.Bank[base], c, 0)
		q0effect := f28DeltaProb(m.Bank[eff], c, 0)
		q1effect := f28DeltaProb(m.Bank[eff], c, 1)
		offset := (f31ArgMax(q1effect) - f31ArgMax(q0effect) + 4) % 4
		for d := 0; d < 4; d++ {
			q[k][(d+offset)%4] += q0base[d]
		}
	}
	return q, nil
}
func (m *f31Model) delta(c, a int) ([4]float64, error) {
	var out [4]float64
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return out, errF31
	}
	q, e := m.pairDeltas(c, a)
	if e != nil {
		return out, e
	}
	for k := 0; k < 4; k++ {
		for d := 0; d < 4; d++ {
			out[d] += m.Weight[c][k] * q[k][d]
		}
	}
	return out, nil
}
func (m *f31Model) forecast(c, a int) ([4]float64, error) {
	var out [4]float64
	q, e := m.delta(c, a)
	if e != nil {
		return out, e
	}
	for s := 0; s < 4; s++ {
		for d := 0; d < 4; d++ {
			out[(s+d)%4] += m.Belief[s] * q[d]
		}
	}
	m.Work += 80
	return out, nil
}
func (m *f31Model) observe(c, a int, next [2]int, training, trainA bool) error {
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return errF31
	}
	evidence, e := f28ObservedDelta(m.Prev, next)
	if e != nil {
		return errF31
	}
	if training {
		b := 1
		if trainA {
			b = 0
		}
		for d := 0; d < 4; d++ {
			m.Bank[b][c][a][d] += evidence[d]
		}
	} else {
		q, e := m.delta(c, a)
		if e != nil {
			return e
		}
		var belief [4]float64
		mass := 0.0
		for s := 0; s < 4; s++ {
			for d := 0; d < 4; d++ {
				state := (s + d) % 4
				x := m.Belief[s] * q[d] * f27Likelihood(next, state)
				belief[state] += x
				mass += x
			}
		}
		if mass <= 0 {
			return errF31
		}
		for i := range belief {
			belief[i] /= mass
		}
		m.Belief = belief
		credit := a
		if m.Mode == "wrong-action" {
			credit = 1 - a
		}
		candidates, e := m.pairDeltas(c, credit)
		if e != nil {
			return e
		}
		var posterior [4]float64
		z := 0.0
		for k := 0; k < 4; k++ {
			if (m.Mode == "no-cross" || m.Mode == "direct-bank") && (k == 1 || k == 2) {
				continue
			}
			prior := .95*m.Weight[c][k] + .05/4
			if m.Mode == "no-cross" || m.Mode == "direct-bank" {
				prior = .95*m.Weight[c][k] + .025
			}
			posterior[k] = prior * f28Agreement(evidence, candidates[k])
			z += posterior[k]
		}
		if z <= 0 {
			return errF31
		}
		for k := 0; k < 4; k++ {
			posterior[k] /= z
		}
		m.Weight[c] = posterior
		m.TransferSeen++
	}
	if training {
		// During training, keep a sensor-only belief; only bank credit is trained.
		p, e := f27Posterior(next)
		if e != nil {
			return errF31
		}
		m.Belief = p
		m.TrainingSeen++
	}
	m.Prev = next
	m.Work += 224
	return nil
}
func (m f31Model) valid() bool {
	if !f31IsDirect(m.Mode) || m.TrainingSeen < 0 || m.TrainingSeen > 128 || m.TransferSeen < 0 || m.TransferSeen > 48 || m.Work < 0 {
		return false
	}
	for _, v := range m.Prev {
		if v < 0 || v > 3 {
			return false
		}
	}
	for b := 0; b < 2; b++ {
		for c := 0; c < 4; c++ {
			for a := 0; a < 2; a++ {
				for _, v := range m.Bank[b][c][a] {
					if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 {
						return false
					}
				}
			}
		}
	}
	if m.HasWorld {
		s := 0.0
		for _, v := range m.Belief {
			if v < 0 || v > 1 || math.IsNaN(v) {
				return false
			}
			s += v
		}
		if math.Abs(s-1) > 1e-7 {
			return false
		}
		for c := 0; c < 4; c++ {
			s = 0
			for k, v := range m.Weight[c] {
				if v < 0 || v > 1 || math.IsNaN(v) {
					return false
				}
				if (m.Mode == "direct-bank" || m.Mode == "no-cross") && (k == 1 || k == 2) && v != 0 {
					return false
				}
				s += v
			}
			if math.Abs(s-1) > 1e-7 {
				return false
			}
		}
	}
	return true
}

type f31Trained struct {
	Kind         string   `json:"kind"`
	Direct       f31Model `json:"direct"`
	Native       f27Model `json:"native"`
	Archive      f28Model `json:"archive"`
	TrainingSeen int      `json:"training_seen"`
}

func (m f31Trained) valid() bool {
	if m.TrainingSeen != 128 {
		return false
	}
	if f31IsDirect(m.Kind) {
		return m.Direct.valid() && m.Direct.TrainingSeen == 128 && m.Direct.Mode == m.Kind
	}
	if k := f31NativeMode(m.Kind); k != "" {
		return m.Native.Mode == k && m.Native.TrainingSeen == 128 && f27Valid(m.Native)
	}
	return m.Kind == "factorized-bayes" && m.Archive.Kind == "factorized-bayes" && m.Archive.TrainingSeen == 128 && f28Valid(m.Archive)
}
func f31Save(m f31Trained) ([]byte, error) {
	if !m.valid() {
		return nil, errF31
	}
	return json.Marshal(m)
}
func f31Load(raw []byte) (f31Trained, error) {
	var m f31Trained
	if json.Unmarshal(raw, &m) != nil || !m.valid() {
		return f31Trained{}, errF31
	}
	canonical, _ := json.Marshal(m)
	if !bytes.Equal(raw, canonical) {
		return f31Trained{}, errF31
	}
	return m, nil
}
func f31Train(kind string) (f31Trained, error) {
	m := f31Trained{Kind: kind}
	switch {
	case f31IsDirect(kind):
		m.Direct.Mode = kind
	case f31NativeMode(kind) != "":
		native, e := f27New(f31NativeMode(kind))
		if e != nil {
			return f31Trained{}, e
		}
		m.Native = native
	case kind == "factorized-bayes":
		a, e := f28New("factorized-bayes")
		if e != nil {
			return f31Trained{}, e
		}
		m.Archive = a
	default:
		return f31Trained{}, errF31
	}
	for j, seed := range [2]uint32{301, 303} {
		w, e := f31NewWorld(seed, "balanced")
		if e != nil {
			return f31Trained{}, e
		}
		if f31IsDirect(kind) {
			e = m.Direct.beginWorld(w.Sensors)
		} else if kind == "factorized-bayes" {
			e = m.Archive.beginWorld(w.Sensors)
		} else {
			e = m.Native.beginWorld(w.Sensors)
		}
		if e != nil {
			return f31Trained{}, e
		}
		for t := 0; t < 64; t++ {
			c, e := f31Cue(seed, "balanced", t)
			if e != nil {
				return f31Trained{}, e
			}
			a, e := f31Action(seed, t)
			if e != nil {
				return f31Trained{}, e
			}
			if f31IsDirect(kind) {
				_, e = m.Direct.forecast(c, a)
			} else if kind == "factorized-bayes" {
				_, e = m.Archive.forecast(c, a)
			} else {
				_, e = m.Native.forecast(c, a)
			}
			if e != nil {
				return f31Trained{}, e
			}
			_, next, e := w.step(t, c, a)
			if e != nil {
				return f31Trained{}, e
			}
			if f31IsDirect(kind) {
				e = m.Direct.observe(c, a, next, true, j == 0)
			} else if kind == "factorized-bayes" {
				e = m.Archive.observe(c, a, next, true, j == 0)
			} else {
				e = m.Native.observe(c, a, next, true)
			}
			if e != nil {
				return f31Trained{}, e
			}
		}
	}
	m.TrainingSeen = 128
	if !m.valid() {
		return f31Trained{}, errF31
	}
	return m, nil
}
func f31Parameters(kind string) int {
	switch kind {
	case "stationary-delta":
		return 32
	case "markov-bayes":
		return 128
	case "online-softmax":
		return 72
	case "factorized-bayes":
		return f28ParameterCount(kind)
	default:
		return 2*4*2*4 + 4*4 + 4
	}
}

type F31Trial struct {
	Kind              string  `json:"kind"`
	MeanNLL           float64 `json:"mean_nll"`
	Accuracy          int     `json:"accuracy"`
	PhaseAccuracy     [4]int  `json:"phase_accuracy"`
	FirstAfterSwitch  [3]int  `json:"first_after_switch"`
	TrainingSeen      int     `json:"training_seen"`
	TransferSeen      int     `json:"transfer_seen"`
	TrainingWork      int     `json:"training_work"`
	TransferWork      int     `json:"transfer_work"`
	Parameters        int     `json:"parameters"`
	ActionsSHA256     string  `json:"actions_sha256"`
	SensorsSHA256     string  `json:"sensors_sha256"`
	PredictionsSHA256 string  `json:"predictions_sha256"`
	CheckpointSHA256  string  `json:"checkpoint_sha256"`
	TerminalSHA256    string  `json:"terminal_sha256"`
	ColdMatches       bool    `json:"cold_matches"`
}

func f31Trial(trained f31Trained, seed uint32, schedule string, cold bool) (F31Trial, []byte, error) {
	if !trained.valid() {
		return F31Trial{}, nil, errF31
	}
	if _, e := f31Cue(seed, schedule, 0); e != nil || f31Training(seed) {
		return F31Trial{}, nil, errF31
	}
	ck, e := f31Save(trained)
	if e != nil {
		return F31Trial{}, nil, e
	}
	if cold {
		trained, e = f31Load(ck)
		if e != nil {
			return F31Trial{}, nil, e
		}
	}
	world, e := f31NewWorld(seed, schedule)
	if e != nil {
		return F31Trial{}, nil, e
	}
	k := trained.Kind
	if f31IsDirect(k) {
		e = trained.Direct.beginWorld(world.Sensors)
	} else if k == "factorized-bayes" {
		e = trained.Archive.beginWorld(world.Sensors)
	} else {
		e = trained.Native.beginWorld(world.Sensors)
	}
	if e != nil {
		return F31Trial{}, nil, e
	}
	tr := F31Trial{Kind: k, TrainingSeen: 128, Parameters: f31Parameters(k), CheckpointSHA256: f27Hash(ck), ColdMatches: true}
	start := 0
	if f31IsDirect(k) {
		start = trained.Direct.Work
		tr.TrainingWork = start
	} else if k == "factorized-bayes" {
		start = trained.Archive.Work
		tr.TrainingWork = start
	} else {
		start = trained.Native.Work
		tr.TrainingWork = start
	}
	acts := []int{}
	sens := [][2]int{world.Sensors}
	preds := [][4]float64{}
	total := 0.0
	for t := 0; t < F31TransferSteps; t++ {
		cue, e := f31Cue(seed, schedule, t)
		if e != nil {
			return F31Trial{}, nil, e
		}
		action, e := f31Action(seed, t)
		if e != nil {
			return F31Trial{}, nil, e
		}
		var p [4]float64
		if f31IsDirect(k) {
			p, e = trained.Direct.forecast(cue, action)
		} else if k == "factorized-bayes" {
			p, e = trained.Archive.forecast(cue, action)
		} else {
			p, e = trained.Native.forecast(cue, action)
		}
		if e != nil {
			return F31Trial{}, nil, e
		}
		actual, next, e := world.step(t, cue, action)
		if e != nil {
			return F31Trial{}, nil, e
		}
		total -= math.Log(math.Max(p[actual], 1e-9))
		if f27ArgMax(p) == actual {
			tr.Accuracy++
			tr.PhaseAccuracy[t/12]++
			if t >= 12 && t < 16 {
				tr.FirstAfterSwitch[0]++
			}
			if t >= 24 && t < 28 {
				tr.FirstAfterSwitch[1]++
			}
			if t >= 36 && t < 40 {
				tr.FirstAfterSwitch[2]++
			}
		}
		acts = append(acts, action)
		sens = append(sens, next)
		preds = append(preds, p)
		if f31IsDirect(k) {
			e = trained.Direct.observe(cue, action, next, false, false)
		} else if k == "factorized-bayes" {
			e = trained.Archive.observe(cue, action, next, false, false)
		} else {
			e = trained.Native.observe(cue, action, next, false)
		}
		if e != nil {
			return F31Trial{}, nil, e
		}
	}
	tr.TransferSeen = 48
	tr.MeanNLL = total / 48
	if f31IsDirect(k) {
		tr.TransferWork = trained.Direct.Work - start
	} else if k == "factorized-bayes" {
		tr.TransferWork = trained.Archive.Work - start
	} else {
		tr.TransferWork = trained.Native.Work - start
	}
	tr.TrainingWork = start
	ab, _ := json.Marshal(acts)
	tr.ActionsSHA256 = f27Hash(ab)
	sb, _ := json.Marshal(sens)
	tr.SensorsSHA256 = f27Hash(sb)
	pb, _ := json.Marshal(preds)
	tr.PredictionsSHA256 = f27Hash(pb)
	terminal, e := f31Save(trained)
	if e != nil {
		return F31Trial{}, nil, e
	}
	tr.TerminalSHA256 = f27Hash(terminal)
	return tr, terminal, nil
}

type F31Arm struct {
	Seed            uint32      `json:"seed"`
	Schedule        string      `json:"schedule"`
	Trials          [8]F31Trial `json:"trials"`
	BestControlNLL  float64     `json:"best_control_nll"`
	BestReturn      int         `json:"best_return"`
	BestNovel       int         `json:"best_novel"`
	GainStrong      float64     `json:"gain_strong"`
	GainNoCross     float64     `json:"gain_no_cross"`
	GainWrongAction float64     `json:"gain_wrong_action"`
	Passes          bool        `json:"passes"`
}
type F31Report struct {
	Schema                    string       `json:"schema"`
	Parent                    string       `json:"parent"`
	TrainingWorlds            [2]uint32    `json:"training_worlds"`
	TransferWorlds            [4]uint32    `json:"transfer_worlds"`
	Coverage                  [2][4][2]int `json:"coverage"`
	TrainingTransitions       int          `json:"training_transitions"`
	TransferTransitions       int          `json:"transfer_transitions"`
	MinimumGain               float64      `json:"minimum_gain"`
	MinimumAblationGain       float64      `json:"minimum_ablation_gain"`
	MinimumNovelGain          int          `json:"minimum_novel_gain"`
	Arms                      [4]F31Arm    `json:"arms"`
	Passing                   int          `json:"passing"`
	Classification            string       `json:"classification"`
	DevelopmentOnly           bool         `json:"development_only"`
	EarlierNegativesPreserved bool         `json:"earlier_negatives_preserved"`
	FirstUseConsumed          bool         `json:"first_use_consumed"`
	ScientificAccepted        bool         `json:"scientific_accepted"`
	OwnerEligible             bool         `json:"owner_eligible"`
	DispatchAuthorized        bool         `json:"dispatch_authorized"`
	MatchedComputeProven      bool         `json:"matched_compute_proven"`
	WholeProcessCostProven    bool         `json:"whole_process_cost_proven"`
	DigestSHA256              string       `json:"digest_sha256"`
}

func f31Digest(r F31Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func f31Calculate() (F31Report, error) {
	r := F31Report{Schema: F31Schema, Parent: F31Parent, TrainingWorlds: [2]uint32{301, 303}, TransferWorlds: [4]uint32{307, 311, 313, 317}, TrainingTransitions: 128, TransferTransitions: 48, MinimumGain: .05, MinimumAblationGain: .10, MinimumNovelGain: 1, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	coverage, e := f31Coverage()
	if e != nil {
		return F31Report{}, e
	}
	for _, world := range coverage {
		for _, cue := range world {
			for _, n := range cue {
				if n != 8 {
					return F31Report{}, errF31
				}
			}
		}
	}
	r.Coverage = coverage
	var trained [8]f31Trained
	for j, k := range f31Kinds() {
		m, e := f31Train(k)
		if e != nil {
			return F31Report{}, e
		}
		trained[j] = m
	}
	for i, w := range f31Worlds() {
		arm := F31Arm{Seed: w.Seed, Schedule: w.Schedule}
		for j := range f31Kinds() {
			cold, cb, e := f31Trial(trained[j], w.Seed, w.Schedule, true)
			if e != nil {
				return F31Report{}, e
			}
			warm, wb, e := f31Trial(trained[j], w.Seed, w.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return F31Report{}, errF31
			}
			arm.Trials[j] = cold
		}
		best := math.Inf(1)
		refAct, refSens := arm.Trials[0].ActionsSHA256, arm.Trials[0].SensorsSHA256
		for j, tr := range arm.Trials {
			if tr.TrainingSeen != 128 || tr.TransferSeen != 48 || tr.ActionsSHA256 != refAct || tr.SensorsSHA256 != refSens || tr.Parameters < 1 || tr.TrainingWork < 1 || tr.TransferWork < 1 {
				return F31Report{}, errF31
			}
			if math.IsNaN(tr.MeanNLL) || math.IsInf(tr.MeanNLL, 0) || tr.MeanNLL < 0 {
				return F31Report{}, errF31
			}
			if j >= 1 && j <= 5 {
				if tr.MeanNLL < best {
					best = tr.MeanNLL
				}
				if tr.PhaseAccuracy[2] > arm.BestReturn {
					arm.BestReturn = tr.PhaseAccuracy[2]
				}
				if tr.PhaseAccuracy[3] > arm.BestNovel {
					arm.BestNovel = tr.PhaseAccuracy[3]
				}
			}
		}
		arm.BestControlNLL = best
		arm.GainStrong = best - arm.Trials[0].MeanNLL
		arm.GainNoCross = arm.Trials[6].MeanNLL - arm.Trials[0].MeanNLL
		arm.GainWrongAction = arm.Trials[7].MeanNLL - arm.Trials[0].MeanNLL
		arm.Passes = arm.GainStrong >= .05 && arm.GainNoCross >= .10 && arm.GainWrongAction >= .10 && arm.Trials[0].PhaseAccuracy[2] >= arm.BestReturn && arm.Trials[0].PhaseAccuracy[3] >= arm.BestNovel+1
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F31NoGo
	if r.Passing == 4 {
		r.Classification = F31Signal
	}
	r.DigestSHA256 = f31Digest(r)
	return r, nil
}

var f31Once sync.Once
var f31ReportCache F31Report
var f31ReportError error

func F31Development() (F31Report, error) {
	f31Once.Do(func() { f31ReportCache, f31ReportError = f31Calculate() })
	return f31ReportCache, f31ReportError
}
func F31Validate(r F31Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f31Digest(r) || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.MatchedComputeProven || r.WholeProcessCostProven {
		return errF31
	}
	expected, e := F31Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF31
	}
	return nil
}
