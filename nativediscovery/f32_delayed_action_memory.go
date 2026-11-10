// Eureka F32: delayed causal effects and cold-memory transfer, frozen synthetic DEV only.
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
	F32Schema        = "forge.native-discovery.delayed-action-memory.dev.v1"
	F32NoGo          = "F32_DEV_NO_GO"
	F32Signal        = "F32_DEV_SIGNAL_UNVERIFIED"
	F32Parent        = "0fc0f9a3cfbd95c64051704fa20a8ae5df06bae7"
	F32TrainingSteps = 256
	F32TransferSteps = 96
)

var errF32 = errors.New("FORGE_EUREKA_F32_INVALID_SOURCE_OR_AUTHORITY")

type f32Spec struct{ Mask, Lag int }
type f32Event struct{ Due, Mask int }
type f32World struct {
	Seed        uint32
	State, Seen int
	Sensors     [2]int
	Due         []f32Event
}
type f32Trace struct {
	Seed                 uint32
	Cues, Actions, Clean []int
	Sensors              [][2]int
}

func f32Worlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{{347, "balanced"}, {349, "skewed"}, {353, "balanced"}, {359, "skewed"}}
}
func f32Known(seed uint32) bool {
	if seed == 331 || seed == 337 {
		return true
	}
	for _, w := range f32Worlds() {
		if w.Seed == seed {
			return true
		}
	}
	return false
}
func f32Training(seed uint32) bool { return seed == 331 || seed == 337 }
func f32Schedule(seed uint32, sched string, t int) (int, int, error) {
	if !f32Known(seed) || t < 0 || (f32Training(seed) && t >= 128) || (!f32Training(seed) && t >= 96) {
		return 0, 0, errF32
	}
	if f32Training(seed) {
		if sched != "isolated" {
			return 0, 0, errF32
		}
		a := 0
		if t%8 == 0 {
			a = 1
		}
		return (t / 8) % 4, a, nil
	}
	a := 0
	if t%2 == 0 {
		a = 1
	}
	switch sched {
	case "balanced":
		return (t/2 + int(seed%4)) % 4, a, nil
	case "skewed":
		if t%8 == 6 {
			return (t/4 + int(seed%4)) % 4, a, nil
		}
		return (t/4 + int(seed%2)) % 2, a, nil
	}
	return 0, 0, errF32
}
func f32Phase(seed uint32, t int) (byte, error) {
	if !f32Known(seed) || t < 0 || (f32Training(seed) && t >= 128) || (!f32Training(seed) && t >= 96) {
		return 0, errF32
	}
	if seed == 331 {
		return 'A', nil
	}
	if seed == 337 {
		return 'B', nil
	}
	startA := seed == 347 || seed == 353
	switch t / 24 {
	case 0, 2:
		if startA {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if startA {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if seed == 347 || seed == 359 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF32
}

// Hidden law belongs exclusively to the simulator. Model functions use learned pulse archives.
func f32Law(phase byte, c int) (f32Spec, error) {
	if c < 0 || c > 3 {
		return f32Spec{}, errF32
	}
	ma := [4]int{1, 2, 3, 1}
	la := [4]int{1, 2, 3, 2}
	mb := [4]int{2, 1, 3, 2}
	lb := [4]int{3, 1, 2, 3}
	switch phase {
	case 'A':
		return f32Spec{ma[c], la[c]}, nil
	case 'B':
		return f32Spec{mb[c], lb[c]}, nil
	case 'C':
		if c%2 == 0 {
			return f32Spec{ma[c], lb[c]}, nil
		}
		return f32Spec{mb[c], la[c]}, nil
	case 'D':
		if c%2 == 0 {
			return f32Spec{mb[c], la[c]}, nil
		}
		return f32Spec{ma[c], lb[c]}, nil
	}
	return f32Spec{}, errF32
}
func f32Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f32Known(seed) || t < 0 || t > 128 || clean < 0 || clean > 3 || sensor < 0 || sensor > 1 {
		return 0, errF32
	}
	v := f27Mix(seed^uint32(t+1)*0x9e3779b9^uint32(sensor+1)*0x85ebca6b^0x6a09e667) % 100
	if sensor == 0 {
		if v < 90 {
			return clean, nil
		}
		if v < 96 {
			return (clean + 1) % 4, nil
		}
		return (clean + 3) % 4, nil
	}
	if v < 80 {
		return clean, nil
	}
	if v < 90 {
		return (clean + 1) % 4, nil
	}
	return (clean + 3) % 4, nil
}
func f32NewWorld(seed uint32) (f32World, error) {
	if !f32Known(seed) {
		return f32World{}, errF32
	}
	w := f32World{Seed: seed, State: int(f27Mix(seed^0x4cf5ad43) & 3)}
	for i := 0; i < 2; i++ {
		v, e := f32Sensor(seed, 0, w.State, i)
		if e != nil {
			return f32World{}, e
		}
		w.Sensors[i] = v
	}
	return w, nil
}
func (w *f32World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || c < 0 || c > 3 || a < 0 || a > 1 {
		return 0, [2]int{}, errF32
	}
	phase, e := f32Phase(w.Seed, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	if a == 1 {
		spec, e := f32Law(phase, c)
		if e != nil {
			return 0, [2]int{}, e
		}
		w.Due = append(w.Due, f32Event{Due: t + spec.Lag - 1, Mask: spec.Mask})
	}
	var outstanding []f32Event
	for _, v := range w.Due {
		if v.Due == t {
			w.State ^= v.Mask
		} else if v.Due > t {
			outstanding = append(outstanding, v)
		} else {
			return 0, [2]int{}, errF32
		}
	}
	w.Due = outstanding
	w.Seen++
	var next [2]int
	for i := 0; i < 2; i++ {
		v, e := f32Sensor(w.Seed, w.Seen, w.State, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = v
	}
	w.Sensors = next
	return w.State, next, nil
}
func f32MakeTrace(seed uint32, sched string) (f32Trace, error) {
	w, e := f32NewWorld(seed)
	if e != nil {
		return f32Trace{}, e
	}
	length := 96
	if f32Training(seed) {
		length = 128
	}
	tr := f32Trace{Seed: seed, Sensors: [][2]int{w.Sensors}}
	for t := 0; t < length; t++ {
		c, a, e := f32Schedule(seed, sched, t)
		if e != nil {
			return f32Trace{}, e
		}
		actual, next, e := w.step(t, c, a)
		if e != nil {
			return f32Trace{}, e
		}
		tr.Cues = append(tr.Cues, c)
		tr.Actions = append(tr.Actions, a)
		tr.Clean = append(tr.Clean, actual)
		tr.Sensors = append(tr.Sensors, next)
	}
	return tr, nil
}

// Marginalize unobserved initial state for every pulse, with no clean targets.
func f32PulseLogLikelihood(visible [5][2]int, mask, lag int) float64 {
	if mask < 1 || mask > 3 || lag < 1 || lag > 3 {
		return math.Inf(-1)
	}
	z := 0.0
	for old := 0; old < 4; old++ {
		val := .25 * f27Likelihood(visible[0], old)
		for k := 1; k <= 4; k++ {
			now := old
			if k >= lag {
				now ^= mask
			}
			val *= f27Likelihood(visible[k], now)
		}
		z += val
	}
	return math.Log(math.Max(z, 1e-100))
}
func f32TrainLog(tr f32Trace) ([4][9]float64, [4]int, error) {
	var logs [4][9]float64
	var coverage [4]int
	if len(tr.Actions) != 128 || len(tr.Sensors) != 129 || !f32Training(tr.Seed) {
		return logs, coverage, errF32
	}
	for start := 0; start < 128; start += 8 {
		c := tr.Cues[start]
		if c < 0 || c >= 4 || tr.Actions[start] != 1 {
			return logs, coverage, errF32
		}
		var sensor [5][2]int
		for k := 0; k <= 4; k++ {
			sensor[k] = tr.Sensors[start+k]
		}
		for mask := 1; mask <= 3; mask++ {
			for lag := 1; lag <= 3; lag++ {
				j := (mask-1)*3 + (lag - 1)
				logs[c][j] += f32PulseLogLikelihood(sensor, mask, lag)
			}
		}
		coverage[c]++
		for k := 1; k < 8; k++ {
			if tr.Actions[start+k] != 0 {
				return logs, coverage, errF32
			}
		}
	}
	for _, v := range coverage {
		if v != 4 {
			return logs, coverage, errF32
		}
	}
	return logs, coverage, nil
}
func f32MAP(logs [9]float64) f32Spec {
	idx := 0
	for j := 1; j < 9; j++ {
		if logs[j] > logs[idx] {
			idx = j
		}
	}
	return f32Spec{Mask: idx/3 + 1, Lag: idx%3 + 1}
}
func f32Features(obs [2]int, nowCue, nowAction int, history []f32Issued) ([17]float64, error) {
	var x [17]float64
	x[0] = 1
	p, e := f27Posterior(obs)
	if e != nil {
		return x, e
	}
	copy(x[1:5], p[:])
	for d := 0; d < 3; d++ {
		cue, a := 0, 0
		if d == 0 {
			cue, a = nowCue, nowAction
		} else if len(history) >= d {
			v := history[len(history)-d]
			cue, a = v.Cue, v.Action
		}
		if a == 1 {
			x[5+d*4+cue] = 1
		}
	}
	return x, nil
}

type f32Issued struct{ Cue, Action int }
type f32Model struct {
	Kind              string           `json:"kind"`
	Banks             [2][4][9]float64 `json:"banks"`
	SourceTemplates   [4][4]f32Spec    `json:"source_templates"`
	Pool              [4]f32Spec       `json:"pooled_templates"`
	Weights           [4]float64       `json:"regime_weights"`
	Softmax           [4][17]float64   `json:"softmax_weights"`
	Last              [2]int           `json:"last_sensors"`
	History           []f32Issued      `json:"issued_action_history"`
	HasWorld          bool             `json:"has_world"`
	TrainingSeen      int              `json:"training_seen"`
	TransferSeen      int              `json:"transfer_seen"`
	EvidenceConflicts int              `json:"evidence_conflicts"`
	Work              int              `json:"work"`
}

func f32Kinds() [6]string {
	return [6]string{"delayed-event-memory", "two-bank-event-bayes", "pooled-event-bayes", "history-logistic", "history-blind", "cold-zero"}
}
func f32New(kind string) (f32Model, error) {
	for _, v := range f32Kinds() {
		if kind == v {
			return f32Model{Kind: kind}, nil
		}
	}
	return f32Model{}, errF32
}
func f32TemplatesFromLogs(logA, logB [4][9]float64) ([4][4]f32Spec, [4]f32Spec) {
	var templates [4][4]f32Spec
	var pooled [4]f32Spec
	for cue := 0; cue < 4; cue++ {
		a, b := f32MAP(logA[cue]), f32MAP(logB[cue])
		templates[0][cue] = a
		templates[1][cue] = b
		templates[2][cue] = f32Spec{Mask: a.Mask, Lag: b.Lag}
		templates[3][cue] = f32Spec{Mask: b.Mask, Lag: a.Lag}
		var combined [9]float64
		for i := 0; i < 9; i++ {
			combined[i] = logA[cue][i] + logB[cue][i]
		}
		pooled[cue] = f32MAP(combined)
	}
	return templates, pooled
}
func (m *f32Model) beginWorld(ob [2]int) error {
	if _, e := f27Posterior(ob); e != nil {
		return errF32
	}
	m.Last = ob
	m.History = nil
	m.HasWorld = true
	m.TransferSeen = 0
	switch m.Kind {
	case "pooled-event-bayes":
		m.Weights = [4]float64{1, 0, 0, 0}
	case "two-bank-event-bayes":
		m.Weights = [4]float64{.5, .5, 0, 0}
	default:
		m.Weights = [4]float64{.25, .25, .25, .25}
	}
	return nil
}
func f32Due(history []f32Issued, now f32Issued, t int, template [4]f32Spec, ignorePast bool) int {
	delta := 0
	for lag := 1; lag <= 3; lag++ {
		idx := t - lag + 1
		if idx < 0 {
			continue
		}
		var issue f32Issued
		if idx == t {
			issue = now
		} else {
			if ignorePast || len(history) < t-idx {
				continue
			}
			issue = history[idx]
		}
		if issue.Action == 1 && issue.Cue >= 0 && issue.Cue < 4 && template[issue.Cue].Lag == lag {
			delta ^= template[issue.Cue].Mask
		}
	}
	return delta
}
func (m *f32Model) nextPred(c, a int) ([4]float64, [4]float64, error) {
	var pred [4]float64
	var likes [4]float64
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return pred, likes, errF32
	}
	if m.Kind == "history-logistic" {
		f, e := f32Features(m.Last, c, a, m.History)
		if e != nil {
			return pred, likes, e
		}
		var z [4]float64
		max := math.Inf(-1)
		for j := 0; j < 4; j++ {
			for k := 0; k < 17; k++ {
				z[j] += m.Softmax[j][k] * f[k]
			}
			if z[j] > max {
				max = z[j]
			}
		}
		total := 0.0
		for j := 0; j < 4; j++ {
			pred[j] = math.Exp(z[j] - max)
			total += pred[j]
		}
		for j := 0; j < 4; j++ {
			pred[j] /= total
		}
		m.Work += 68
		return pred, likes, nil
	}
	posterior, e := f27Posterior(m.Last)
	if e != nil {
		return pred, likes, e
	}
	event := f32Issued{Cue: c, Action: a}
	n := 4
	if m.Kind == "two-bank-event-bayes" {
		n = 2
	}
	if m.Kind == "pooled-event-bayes" {
		n = 1
	}
	for k := 0; k < n; k++ {
		template := m.SourceTemplates[k]
		if m.Kind == "pooled-event-bayes" {
			template = m.Pool
		}
		if m.Kind == "cold-zero" {
			for i := range template {
				template[i] = f32Spec{Mask: 1, Lag: 1}
			}
		}
		delta := f32Due(m.History, event, len(m.History), template, m.Kind == "history-blind")
		for old := 0; old < 4; old++ {
			pred[old^delta] += posterior[old] * m.Weights[k]
		}
	}
	m.Work += 4*n*3 + 16
	return pred, likes, nil
}
func (m *f32Model) observe(c, a int, next [2]int, training bool) error {
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return errF32
	}
	if m.Kind == "history-logistic" {
		feature, e := f32Features(m.Last, c, a, m.History)
		if e != nil {
			return e
		}
		target, e := f27Posterior(next)
		if e != nil {
			return e
		}
		for pass := 0; pass < 4; pass++ {
			var z [4]float64
			max := math.Inf(-1)
			for j := 0; j < 4; j++ {
				for k := 0; k < 17; k++ {
					z[j] += m.Softmax[j][k] * feature[k]
				}
				if z[j] > max {
					max = z[j]
				}
			}
			sum := 0.0
			for j := 0; j < 4; j++ {
				z[j] = math.Exp(z[j] - max)
				sum += z[j]
			}
			for j := 0; j < 4; j++ {
				for k := 0; k < 17; k++ {
					m.Softmax[j][k] += .05 * ((target[j]-z[j]/sum)*feature[k] - .0001*m.Softmax[j][k])
				}
			}
		}
		m.Work += 4 * 68
	} else {
		old, e := f27Posterior(m.Last)
		if e != nil {
			return e
		}
		num := 4
		if m.Kind == "two-bank-event-bayes" {
			num = 2
		}
		if m.Kind == "pooled-event-bayes" {
			num = 1
		}
		var updated [4]float64
		sum := 0.0
		for k := 0; k < num; k++ {
			tpl := m.SourceTemplates[k]
			if m.Kind == "pooled-event-bayes" {
				tpl = m.Pool
			}
			if m.Kind == "cold-zero" {
				for i := range tpl {
					tpl[i] = f32Spec{Mask: 1, Lag: 1}
				}
			}
			delta := f32Due(m.History, f32Issued{Cue: c, Action: a}, len(m.History), tpl, m.Kind == "history-blind")
			like := 0.0
			for s := 0; s < 4; s++ {
				like += old[s] * f27Likelihood(next, s^delta)
			}
			prior := .93*m.Weights[k] + .07/float64(num)
			updated[k] = prior * like
			sum += updated[k]
		}
		if sum <= 0 {
			// All learned hypotheses assign zero likelihood to this observation.
			// No posterior exists: retain a normalized hazard-mixed prior,
			// record the conflict, and do not invent a new causal effect.
			m.EvidenceConflicts++
			for k := 0; k < num; k++ {
				m.Weights[k] = .93*m.Weights[k] + .07/float64(num)
			}
		} else {
			for k := 0; k < num; k++ {
				m.Weights[k] = updated[k] / sum
			}
		}
		m.Work += 16 * num
	}
	m.History = append(m.History, f32Issued{Cue: c, Action: a})
	m.Last = next
	if training {
		m.TrainingSeen++
	} else {
		m.TransferSeen++
	}
	return nil
}
func f32Train(kind string, training [2]f32Trace) (f32Model, error) {
	m, e := f32New(kind)
	if e != nil {
		return m, e
	}
	var logs [2][4][9]float64
	for i, tr := range training {
		a, _, e := f32TrainLog(tr)
		if e != nil {
			return f32Model{}, e
		}
		logs[i] = a
	}
	m.Banks = logs
	m.SourceTemplates, m.Pool = f32TemplatesFromLogs(logs[0], logs[1])
	for _, tr := range training {
		if e = m.beginWorld(tr.Sensors[0]); e != nil {
			return f32Model{}, e
		}
		for t := range tr.Cues {
			if _, _, e = m.nextPred(tr.Cues[t], tr.Actions[t]); e != nil {
				return f32Model{}, e
			}
			if e = m.observe(tr.Cues[t], tr.Actions[t], tr.Sensors[t+1], true); e != nil {
				return f32Model{}, e
			}
		}
	}
	if m.TrainingSeen != 256 {
		return f32Model{}, errF32
	}
	m.HasWorld = false
	m.History = nil
	return m, nil
}
func f32Valid(m f32Model) bool {
	validKind := false
	for _, v := range f32Kinds() {
		if m.Kind == v {
			validKind = true
		}
	}
	if !validKind || m.TrainingSeen != 256 || m.TransferSeen < 0 || m.TransferSeen > 96 || m.EvidenceConflicts < 0 || m.EvidenceConflicts > m.TrainingSeen+m.TransferSeen || m.Work < 0 {
		return false
	}
	for k := 0; k < 2; k++ {
		for c := 0; c < 4; c++ {
			for _, v := range m.Banks[k][c] {
				if math.IsNaN(v) || math.IsInf(v, 0) {
					return false
				}
			}
		}
	}
	for k := range m.Weights {
		if math.IsNaN(m.Weights[k]) || math.IsInf(m.Weights[k], 0) || m.Weights[k] < 0 || m.Weights[k] > 1 {
			return false
		}
	}
	for _, v := range m.Last {
		if v < 0 || v > 3 {
			return false
		}
	}
	for _, h := range m.History {
		if h.Cue < 0 || h.Cue > 3 || h.Action < 0 || h.Action > 1 {
			return false
		}
	}
	if len(m.History) > 96 && m.TransferSeen > 0 {
		return false
	}
	return true
}
func f32Save(m f32Model) ([]byte, error) {
	if !f32Valid(m) {
		return nil, errF32
	}
	return json.Marshal(m)
}
func f32Load(raw []byte) (f32Model, error) {
	var m f32Model
	if json.Unmarshal(raw, &m) != nil || !f32Valid(m) {
		return f32Model{}, errF32
	}
	b, _ := json.Marshal(m)
	if !bytes.Equal(raw, b) {
		return f32Model{}, errF32
	}
	return m, nil
}

type F32Trial struct {
	Kind                                                                              string  `json:"kind"`
	MeanNLL                                                                           float64 `json:"mean_nll"`
	Accuracy                                                                          int     `json:"accuracy"`
	PhaseAccuracy                                                                     [4]int  `json:"phase_accuracy"`
	FirstAfterSwitch                                                                  [3]int  `json:"first_after_switch"`
	TrainingSeen, TransferSeen, Work, Parameters, EvidenceConflicts                   int
	ActionsSHA256, SensorsSHA256, PredictionsSHA256, CheckpointSHA256, TerminalSHA256 string
	ColdMatches                                                                       bool
}

func f32Params(kind string) int {
	switch kind {
	case "history-logistic":
		return 4 * 17
	case "pooled-event-bayes":
		return 4 * 9
	case "two-bank-event-bayes":
		return 2*4*9 + 2
	}
	return 2*4*9 + 4
}
func f32Trial(trained f32Model, tr f32Trace, cold bool) (F32Trial, []byte, error) {
	checkpoint, e := f32Save(trained)
	if e != nil {
		return F32Trial{}, nil, e
	}
	m := trained
	if cold {
		m, e = f32Load(checkpoint)
		if e != nil {
			return F32Trial{}, nil, e
		}
	}
	if len(tr.Cues) != 96 || m.TrainingSeen != 256 {
		return F32Trial{}, nil, errF32
	}
	if e = m.beginWorld(tr.Sensors[0]); e != nil {
		return F32Trial{}, nil, e
	}
	startWork := m.Work
	result := F32Trial{Kind: m.Kind, Parameters: f32Params(m.Kind), TrainingSeen: 256, CheckpointSHA256: f27Hash(checkpoint), ColdMatches: true}
	var preds [][4]float64
	total := 0.0
	for t := 0; t < 96; t++ {
		pred, _, e := m.nextPred(tr.Cues[t], tr.Actions[t])
		if e != nil {
			return F32Trial{}, nil, e
		}
		preds = append(preds, pred)
		total -= math.Log(math.Max(pred[tr.Clean[t]], 1e-9))
		if f27ArgMax(pred) == tr.Clean[t] {
			result.Accuracy++
			result.PhaseAccuracy[t/24]++
			if t >= 24 && t < 32 {
				result.FirstAfterSwitch[0]++
			}
			if t >= 48 && t < 56 {
				result.FirstAfterSwitch[1]++
			}
			if t >= 72 && t < 80 {
				result.FirstAfterSwitch[2]++
			}
		}
		if e = m.observe(tr.Cues[t], tr.Actions[t], tr.Sensors[t+1], false); e != nil {
			return F32Trial{}, nil, e
		}
	}
	result.TransferSeen = m.TransferSeen
	result.EvidenceConflicts = m.EvidenceConflicts - trained.EvidenceConflicts
	result.Work = m.Work - startWork
	result.MeanNLL = total / 96
	acts, _ := json.Marshal(tr.Actions)
	obs, _ := json.Marshal(tr.Sensors)
	p, _ := json.Marshal(preds)
	result.ActionsSHA256 = f27Hash(acts)
	result.SensorsSHA256 = f27Hash(obs)
	result.PredictionsSHA256 = f27Hash(p)
	final, e := f32Save(m)
	if e != nil {
		return F32Trial{}, nil, e
	}
	result.TerminalSHA256 = f27Hash(final)
	return result, final, nil
}

type F32Arm struct {
	Seed                                                            uint32      `json:"seed"`
	Schedule                                                        string      `json:"schedule"`
	Trials                                                          [6]F32Trial `json:"trials"`
	BestConventionalNLL, GainStrong, GainHistoryBlind, GainColdZero float64
	BestReturn, BestNovel                                           int
	Passes                                                          bool
}
type F32Report struct {
	Schema, Parent, Classification                                                                                        string
	TrainSeeds                                                                                                            [2]uint32
	TransferSeeds                                                                                                         [4]uint32
	TrainTransitions, TransferTransitions                                                                                 int
	Coverage                                                                                                              [2][4]int
	MinGain, MinAblationGain                                                                                              float64
	MinNovelGain                                                                                                          int
	Arms                                                                                                                  [4]F32Arm
	Passing                                                                                                               int
	DevelopmentOnly, EarlierNegativesPreserved                                                                            bool
	FirstUseConsumed, ScientificAccepted, OwnerEligible, DispatchAuthorized, WholeProcessCostProven, MatchedComputeProven bool
	DigestSHA256                                                                                                          string
}

func f32Digest(r F32Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func f32Calculate() (F32Report, error) {
	r := F32Report{Schema: F32Schema, Parent: F32Parent, TrainSeeds: [2]uint32{331, 337}, TransferSeeds: [4]uint32{347, 349, 353, 359}, TrainTransitions: 256, TransferTransitions: 96, MinGain: .05, MinAblationGain: .10, MinNovelGain: 2, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	a, e := f32MakeTrace(331, "isolated")
	if e != nil {
		return r, e
	}
	b, e := f32MakeTrace(337, "isolated")
	if e != nil {
		return r, e
	}
	train := [2]f32Trace{a, b}
	for i, tr := range train {
		_, cover, e := f32TrainLog(tr)
		if e != nil {
			return r, e
		}
		r.Coverage[i] = cover
	}
	var trained [6]f32Model
	for i, kind := range f32Kinds() {
		m, e := f32Train(kind, train)
		if e != nil {
			return r, e
		}
		trained[i] = m
	}
	for i, w := range f32Worlds() {
		tr, e := f32MakeTrace(w.Seed, w.Schedule)
		if e != nil {
			return r, e
		}
		arm := F32Arm{Seed: w.Seed, Schedule: w.Schedule}
		best := math.Inf(1)
		for j := range trained {
			cold, cb, e := f32Trial(trained[j], tr, true)
			if e != nil {
				return r, e
			}
			warm, wb, e := f32Trial(trained[j], tr, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return r, errF32
			}
			arm.Trials[j] = cold
			if j > 0 && j <= 3 {
				if cold.MeanNLL < best {
					best = cold.MeanNLL
				}
				if cold.PhaseAccuracy[2] > arm.BestReturn {
					arm.BestReturn = cold.PhaseAccuracy[2]
				}
				if cold.PhaseAccuracy[3] > arm.BestNovel {
					arm.BestNovel = cold.PhaseAccuracy[3]
				}
			}
		}
		for _, v := range arm.Trials {
			if v.ActionsSHA256 != arm.Trials[0].ActionsSHA256 || v.SensorsSHA256 != arm.Trials[0].SensorsSHA256 || v.TrainingSeen != 256 || v.TransferSeen != 96 {
				return r, errF32
			}
		}
		arm.BestConventionalNLL = best
		arm.GainStrong = best - arm.Trials[0].MeanNLL
		arm.GainHistoryBlind = arm.Trials[4].MeanNLL - arm.Trials[0].MeanNLL
		arm.GainColdZero = arm.Trials[5].MeanNLL - arm.Trials[0].MeanNLL
		arm.Passes = arm.GainStrong >= .05 && arm.GainHistoryBlind >= .10 && arm.GainColdZero >= .10 && arm.Trials[0].PhaseAccuracy[2] >= arm.BestReturn && arm.Trials[0].PhaseAccuracy[3] >= arm.BestNovel+2
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F32NoGo
	if r.Passing == 4 {
		r.Classification = F32Signal
	}
	r.DigestSHA256 = f32Digest(r)
	return r, nil
}

var f32Once sync.Once
var f32Cached F32Report
var f32CacheError error

func F32Development() (F32Report, error) {
	f32Once.Do(func() { f32Cached, f32CacheError = f32Calculate() })
	return f32Cached, f32CacheError
}
func F32Validate(r F32Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f32Digest(r) || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven {
		return errF32
	}
	expected, e := F32Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF32
	}
	return nil
}
