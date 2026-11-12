// Eureka F36: two-actuator, 16-state delayed causal-control development benchmark.
// No scientific first-use, controller, owner, dispatch, or deployment hooks.
package nativediscovery

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"reflect"
	"sync"
)

const (
	F36Schema        = "forge.native-discovery.two-actuator-causal-control.dev.v1"
	F36Parent        = "23a76b20cb968ee3779bdafddf01d889e6978cf5"
	F36NoGo          = "F36_DEV_NO_GO"
	F36Signal        = "F36_DEV_SIGNAL_UNVERIFIED"
	F36TrainingSteps = 192
	F36TransferSteps = 96
)

var errF36 = errors.New("FORGE_EUREKA_F36_INVALID_SOURCE_OR_AUTHORITY")

type f36Event struct{ Due, Mask int }
type f36Spec struct{ Mask, Lag int }
type f36LawTable [4][2]f36Spec

func f36Worlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{{439, "balanced"}, {443, "skewed"}, {449, "balanced"}, {457, "skewed"}}
}
func f36SeedOK(seed uint32) bool {
	if seed == 431 || seed == 433 {
		return true
	}
	for _, s := range f36Worlds() {
		if seed == s.Seed {
			return true
		}
	}
	return false
}

// Hidden laws are simulator-only. Policy training never calls this function.
func f36Law(phase byte) (f36LawTable, error) {
	a := f36LawTable{{{1, 1}, {6, 3}}, {{2, 2}, {9, 1}}, {{4, 3}, {3, 2}}, {{8, 2}, {12, 3}}}
	b := f36LawTable{{{3, 3}, {8, 2}}, {{5, 1}, {2, 3}}, {{10, 2}, {4, 1}}, {{1, 3}, {6, 2}}}
	switch phase {
	case 'A':
		return a, nil
	case 'B':
		return b, nil
	case 'C':
		var out f36LawTable
		for c := 0; c < 4; c++ {
			for j := 0; j < 2; j++ {
				if c%2 == 0 {
					out[c][j] = f36Spec{a[c][j].Mask, b[c][j].Lag}
				} else {
					out[c][j] = f36Spec{b[c][j].Mask, a[c][j].Lag}
				}
			}
		}
		return out, nil
	case 'D':
		var out f36LawTable
		for c := 0; c < 4; c++ {
			for j := 0; j < 2; j++ {
				if c%2 == 0 {
					out[c][j] = f36Spec{b[c][j].Mask, a[c][j].Lag}
				} else {
					out[c][j] = f36Spec{a[c][j].Mask, b[c][j].Lag}
				}
			}
		}
		return out, nil
	}
	return f36LawTable{}, errF36
}
func f36Phase(seed uint32, t int) (byte, error) {
	if !f36SeedOK(seed) || t < 0 || (seed == 431 || seed == 433) && t >= F36TrainingSteps || seed != 431 && seed != 433 && t >= F36TransferSteps {
		return 0, errF36
	}
	if seed == 431 {
		return 'A', nil
	}
	if seed == 433 {
		return 'B', nil
	}
	startA := seed == 439 || seed == 449
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
		if seed == 439 || seed == 457 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF36
}
func f36TrainingSchedule(t int) (int, int, error) {
	if t < 0 || t >= F36TrainingSteps {
		return 0, 0, errF36
	}
	w := t / 12
	j := t % 12
	a := 0
	if j == 0 {
		a = 1
	} else if j == 5 {
		a = 2
	}
	return w % 4, a, nil
}
func f36Cue(seed uint32, schedule string, t int) (int, error) {
	if !f36SeedOK(seed) || seed == 431 || seed == 433 || t < 0 || t >= F36TransferSteps {
		return 0, errF36
	}
	switch schedule {
	case "balanced":
		return (t/2 + int(seed%4)) % 4, nil
	case "skewed":
		if t%8 == 6 {
			return (t/4 + int(seed%4)) % 4, nil
		}
		return (t/4 + int(seed%2)) % 2, nil
	}
	return 0, errF36
}
func f36Goal(seed uint32, t int) (int, error) {
	if !f36SeedOK(seed) || seed == 431 || seed == 433 || t < 0 || t >= 96 {
		return 0, errF36
	}
	return int(f27Mix(seed^uint32(t/4+1)*0x7f4a7c15^0x52dce729) & 15), nil
}
func f36Emission(obs, clean, sensor int) float64 {
	if obs < 0 || obs > 15 || clean < 0 || clean > 15 || sensor < 0 || sensor > 1 {
		return 0
	}
	correct, flip := .92, .02
	if sensor == 1 {
		correct, flip = .84, .04
	}
	if obs == clean {
		return correct
	}
	d := obs ^ clean
	if d == 1 || d == 2 || d == 4 || d == 8 {
		return flip
	}
	return 0
}
func f36Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f36SeedOK(seed) || t < 0 || t > F36TrainingSteps || clean < 0 || clean > 15 || sensor < 0 || sensor > 1 {
		return 0, errF36
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

type f36World struct {
	Seed        uint32
	State, Seen int
	Pending     []f36Event
	Sensors     [2]int
}

func f36NewWorld(seed uint32) (f36World, error) {
	if !f36SeedOK(seed) {
		return f36World{}, errF36
	}
	w := f36World{Seed: seed, State: int(f27Mix(seed^0x4cf5ad43) & 15)}
	for i := 0; i < 2; i++ {
		v, e := f36Sensor(seed, 0, w.State, i)
		if e != nil {
			return f36World{}, e
		}
		w.Sensors[i] = v
	}
	return w, nil
}
func (w *f36World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || c < 0 || c > 3 || a < 0 || a > 2 {
		return 0, [2]int{}, errF36
	}
	phase, e := f36Phase(w.Seed, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	if a > 0 {
		law, e := f36Law(phase)
		if e != nil {
			return 0, [2]int{}, e
		}
		s := law[c][a-1]
		w.Pending = append(w.Pending, f36Event{t + s.Lag - 1, s.Mask})
	}
	remain := make([]f36Event, 0, len(w.Pending))
	for _, p := range w.Pending {
		if p.Due == t {
			w.State ^= p.Mask
		} else if p.Due > t {
			remain = append(remain, p)
		} else {
			return 0, [2]int{}, errF36
		}
	}
	w.Pending = remain
	w.Seen++
	var obs [2]int
	for i := 0; i < 2; i++ {
		v, e := f36Sensor(w.Seed, w.Seen, w.State, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		obs[i] = v
	}
	w.Sensors = obs
	return w.State, obs, nil
}
func f36Likelihood(obs [2]int, s int) float64 {
	return f36Emission(obs[0], s, 0) * f36Emission(obs[1], s, 1)
}
func f36Posterior(obs [2]int) ([16]float64, error) {
	var p [16]float64
	z := 0.0
	for i := 0; i < 16; i++ {
		p[i] = f36Likelihood(obs, i)
		z += p[i]
	}
	if z == 0 {
		return p, errF36
	}
	for i := range p {
		p[i] /= z
	}
	return p, nil
}

// The training pulse likelihood integrates out the unobserved pre-pulse state.
func f36PulseLikelihood(obs [4][2]int, mask, lag int) float64 {
	z := 0.0
	for s := 0; s < 16; s++ {
		p := f36Likelihood(obs[0], s) / 16
		for time := 0; time < 3; time++ {
			state := s
			if time >= lag-1 {
				state ^= mask
			}
			p *= f36Likelihood(obs[time+1], state)
		}
		z += p
	}
	return z
}

type f36Archive struct {
	A           f36LawTable
	B           f36LawTable
	Pooled      f36LawTable
	Coverage    [2][4][2]int
	TrainSHA256 string
	TrainSteps  int
}

func f36Train() (f36Archive, error) {
	var archive f36Archive
	var likelihood [2][4][2][15][3]float64
	var trainTrace [2]struct {
		Actions [192][2]int
		Sensors [193][2]int
	}
	for bi, seed := range [2]uint32{431, 433} {
		world, e := f36NewWorld(seed)
		if e != nil {
			return archive, e
		}
		trainTrace[bi].Sensors[0] = world.Sensors
		for t := 0; t < 192; t++ {
			cue, action, e := f36TrainingSchedule(t)
			if e != nil {
				return archive, e
			}
			trainTrace[bi].Actions[t] = [2]int{cue, action}
			_, next, e := world.step(t, cue, action)
			if e != nil {
				return archive, e
			}
			trainTrace[bi].Sensors[t+1] = next
		}
		for cycle := 0; cycle < 16; cycle++ {
			cue := cycle % 4
			for ai, off := range [2]int{0, 5} {
				base := cycle*12 + off
				var obs [4][2]int
				copy(obs[:], trainTrace[bi].Sensors[base:base+4])
				for mask := 1; mask <= 15; mask++ {
					for lag := 1; lag <= 3; lag++ {
						v := f36PulseLikelihood(obs, mask, lag)
						likelihood[bi][cue][ai][mask-1][lag-1] += math.Log(math.Max(v, 1e-300))
					}
				}
				archive.Coverage[bi][cue][ai]++
			}
		}
	}
	for cue := 0; cue < 4; cue++ {
		for ai := 0; ai < 2; ai++ {
			bestBank := [2]f36Spec{}
			for bi := 0; bi < 2; bi++ {
				best := math.Inf(-1)
				for mask := 1; mask <= 15; mask++ {
					for lag := 1; lag <= 3; lag++ {
						v := likelihood[bi][cue][ai][mask-1][lag-1]
						if v > best {
							best = v
							bestBank[bi] = f36Spec{mask, lag}
						}
					}
				}
			}
			archive.A[cue][ai] = bestBank[0]
			archive.B[cue][ai] = bestBank[1]
			best := math.Inf(-1)
			for mask := 1; mask <= 15; mask++ {
				for lag := 1; lag <= 3; lag++ {
					v := likelihood[0][cue][ai][mask-1][lag-1] + likelihood[1][cue][ai][mask-1][lag-1]
					if v > best {
						best = v
						archive.Pooled[cue][ai] = f36Spec{mask, lag}
					}
				}
			}
		}
	}
	raw, _ := json.Marshal(trainTrace)
	archive.TrainSHA256 = f27Hash(raw)
	archive.TrainSteps = 384
	for bi := 0; bi < 2; bi++ {
		for c := 0; c < 4; c++ {
			for a := 0; a < 2; a++ {
				if archive.Coverage[bi][c][a] != 4 {
					return archive, errF36
				}
			}
		}
	}
	return archive, nil
}
func f36Combine(a, b f36LawTable, cross int) f36LawTable {
	if cross == 0 {
		return a
	}
	if cross == 3 {
		return b
	}
	var result f36LawTable
	for c := 0; c < 4; c++ {
		for j := 0; j < 2; j++ {
			if cross == 1 {
				if c%2 == 0 {
					result[c][j] = f36Spec{a[c][j].Mask, b[c][j].Lag}
				} else {
					result[c][j] = f36Spec{b[c][j].Mask, a[c][j].Lag}
				}
			} else {
				if c%2 == 0 {
					result[c][j] = f36Spec{b[c][j].Mask, a[c][j].Lag}
				} else {
					result[c][j] = f36Spec{a[c][j].Mask, b[c][j].Lag}
				}
			}
		}
	}
	return result
}
func f36Kinds() [8]string {
	return [8]string{"compositional-issued-memory", "two-bank-issued-bayes", "pooled-issued-bayes", "history-logistic", "drop-history", "cold-zero", "always-zero", "random-budget"}
}

type f36Model struct {
	Kind                     string
	Templates                [4]f36LawTable
	Weights                  [4]float64
	Beliefs                  [4][16]float64
	Events                   [4][]f36Event
	Previous                 [2]int
	History                  [3][2]int
	Logistic                 [16][41]float64
	Have                     bool
	Actions, Work, FloorHits int
}

func f36Init(archive f36Archive, kind string, initial [2]int) (f36Model, error) {
	m := f36Model{Kind: kind, Previous: initial}
	ok := false
	for _, k := range f36Kinds() {
		if k == kind {
			ok = true
		}
	}
	if !ok {
		return m, errF36
	}
	switch kind {
	case "two-bank-issued-bayes":
		m.Templates = [4]f36LawTable{archive.A, archive.A, archive.B, archive.B}
	case "pooled-issued-bayes":
		m.Templates = [4]f36LawTable{archive.Pooled, archive.Pooled, archive.Pooled, archive.Pooled}
	case "cold-zero":
		var t f36LawTable
		for c := 0; c < 4; c++ {
			for j := 0; j < 2; j++ {
				t[c][j] = f36Spec{1, 1}
			}
		}
		m.Templates = [4]f36LawTable{t, t, t, t}
	default:
		m.Templates = [4]f36LawTable{archive.A, f36Combine(archive.A, archive.B, 1), f36Combine(archive.A, archive.B, 2), archive.B}
	}
	p, e := f36Posterior(initial)
	if e != nil {
		return m, e
	}
	for k := 0; k < 4; k++ {
		m.Weights[k] = .25
		m.Beliefs[k] = p
	}
	m.Have = true
	return m, nil
}
func (m *f36Model) scoreGoal(t, c, a, goal int) (float64, error) {
	if !m.Have || t < 0 || t >= 96 || c < 0 || c > 3 || a < 0 || a > 2 || goal < 0 || goal > 15 {
		return 0, errF36
	}
	terminal := t/4*4 + 3
	out := 0.0
	for k := 0; k < 4; k++ {
		delta := 0
		for _, e := range m.Events[k] {
			if e.Due <= terminal && e.Due >= t {
				delta ^= e.Mask
			}
		}
		if a > 0 {
			spec := m.Templates[k][c][a-1]
			if t+spec.Lag-1 <= terminal {
				delta ^= spec.Mask
			}
		}
		for s, p := range m.Beliefs[k] {
			if s^delta == goal {
				out += m.Weights[k] * p
			}
		}
	}
	m.Work += 4 * 16
	return out, nil
}
func (m *f36Model) observe(t, c, a int, next [2]int) error {
	if !m.Have || t < 0 || t >= 96 || c < 0 || c > 3 || a < 0 || a > 2 {
		return errF36
	}
	var z [4]float64
	for k := 0; k < 4; k++ {
		if m.Kind == "drop-history" {
			m.Events[k] = nil
		}
		if a > 0 {
			spec := m.Templates[k][c][a-1]
			m.Events[k] = append(m.Events[k], f36Event{Due: t + spec.Lag - 1, Mask: spec.Mask})
		}
		delta := 0
		rem := make([]f36Event, 0, len(m.Events[k]))
		for _, e := range m.Events[k] {
			if e.Due == t {
				delta ^= e.Mask
			} else if e.Due > t {
				rem = append(rem, e)
			} else {
				return errF36
			}
		}
		m.Events[k] = rem
		var nextBelief [16]float64
		for s, prob := range m.Beliefs[k] {
			at := s ^ delta
			v := prob * f36Likelihood(next, at)
			nextBelief[at] += v
			z[k] += v
		}
		if z[k] <= 0 {
			m.FloorHits++
			for s, prob := range m.Beliefs[k] {
				nextBelief[s^delta] = prob
			}
			z[k] = 1e-9
		} else {
			for s := range nextBelief {
				nextBelief[s] /= z[k]
			}
		}
		m.Beliefs[k] = nextBelief
	}
	zTotal := 0.0
	for k := 0; k < 4; k++ {
		m.Weights[k] = (.95*m.Weights[k] + .05/4) * math.Max(z[k], 1e-9)
		zTotal += m.Weights[k]
	}
	if zTotal <= 0 {
		return errF36
	}
	for k := 0; k < 4; k++ {
		m.Weights[k] /= zTotal
	}
	m.History[2] = m.History[1]
	m.History[1] = m.History[0]
	m.History[0] = [2]int{c, a}
	m.Previous = next
	m.Work += 4 * 16 * 2
	return nil
}
func f36Features(cur int, history [3][2]int, c, a int) ([41]float64, error) {
	var f [41]float64
	if cur < 0 || cur > 15 || c < 0 || c > 3 || a < 0 || a > 2 {
		return f, errF36
	}
	f[0] = 1
	f[1+cur] = 1
	h := [3][2]int{{c, a}, history[0], history[1]}
	for j, p := range h {
		if p[1] > 0 && p[0] >= 0 && p[0] < 4 {
			f[17+j*8+p[0]*2+p[1]-1] = 1
		}
	}
	return f, nil
}
func f36Softmax(w [16][41]float64, f [41]float64) [16]float64 {
	var z, p [16]float64
	highest := math.Inf(-1)
	for k := 0; k < 16; k++ {
		for j := 0; j < 41; j++ {
			z[k] += w[k][j] * f[j]
		}
		if z[k] > highest {
			highest = z[k]
		}
	}
	total := 0.0
	for k := 0; k < 16; k++ {
		p[k] = math.Exp(z[k] - highest)
		total += p[k]
	}
	for k := 0; k < 16; k++ {
		p[k] /= total
	}
	return p
}
func (m *f36Model) logisticUpdate(c, a int, next [2]int) error {
	if !m.Have {
		return errF36
	}
	obs, e := f36Posterior(next)
	if e != nil {
		return e
	}
	prev, _ := f36Posterior(m.Previous)
	arg := 0
	for i := 1; i < 16; i++ {
		if prev[i] > prev[arg] {
			arg = i
		}
	}
	f, e := f36Features(arg, m.History, c, a)
	if e != nil {
		return e
	}
	for pass := 0; pass < 4; pass++ {
		p := f36Softmax(m.Logistic, f)
		for k := 0; k < 16; k++ {
			for j := 0; j < 41; j++ {
				m.Logistic[k][j] += .05 * ((obs[k]-p[k])*f[j] - .0001*m.Logistic[k][j])
			}
		}
	}
	m.Work += 16 * 41 * 4
	m.History[2] = m.History[1]
	m.History[1] = m.History[0]
	m.History[0] = [2]int{c, a}
	m.Previous = next
	return nil
}
func (m *f36Model) logisticGoal(t, c, a, goal int) (float64, error) {
	if !m.Have || goal < 0 || goal > 15 {
		return 0, errF36
	}
	var dist [16]float64
	old, e := f36Posterior(m.Previous)
	if e != nil {
		return 0, e
	}
	dist = old
	h := m.History
	for time := t; time <= t/4*4+3; time++ {
		act := 0
		if time == t {
			act = a
		}
		var next [16]float64
		for s, mass := range dist {
			if mass <= 0 {
				continue
			}
			f, e := f36Features(s, h, c, act)
			if e != nil {
				return 0, e
			}
			q := f36Softmax(m.Logistic, f)
			for v, p := range q {
				next[v] += mass * p
			}
		}
		dist = next
		h[2] = h[1]
		h[1] = h[0]
		h[0] = [2]int{c, act}
	}
	m.Work += (t/4*4 + 4 - t) * 16 * 16 * 41
	return dist[goal], nil
}

// Frozen source training for the conventional autoregressive model: all 384 observed transitions.
func f36TrainLogistic() (f36Model, error) {
	archive, e := f36Train()
	if e != nil {
		return f36Model{}, e
	}
	m := f36Model{Kind: "history-logistic"}
	for _, seed := range [2]uint32{431, 433} {
		w, e := f36NewWorld(seed)
		if e != nil {
			return m, e
		}
		m.Have = true
		m.Previous = w.Sensors
		m.History = [3][2]int{}
		for t := 0; t < 192; t++ {
			c, a, e := f36TrainingSchedule(t)
			if e != nil {
				return m, e
			}
			_, next, e := w.step(t, c, a)
			if e != nil {
				return m, e
			}
			if e = m.logisticUpdate(c, a, next); e != nil {
				return m, e
			}
		}
	}
	m.Have = false
	m.Actions = 0
	_ = archive
	return m, nil
}
func f36LoadModel(raw []byte) (f36Model, error) {
	var m f36Model
	if json.Unmarshal(raw, &m) != nil {
		return m, errF36
	}
	b, _ := json.Marshal(m)
	if !bytes.Equal(b, raw) {
		return m, errF36
	}
	return m, nil
}
func f36LoadArchive(raw []byte) (f36Archive, error) {
	var a f36Archive
	if json.Unmarshal(raw, &a) != nil {
		return a, errF36
	}
	b, _ := json.Marshal(a)
	if !bytes.Equal(b, raw) {
		return a, errF36
	}
	return a, nil
}
func f36ValidParams(archive f36Archive) bool {
	if archive.TrainSteps != 384 || len(archive.TrainSHA256) != 64 {
		return false
	}
	for bi := 0; bi < 2; bi++ {
		for c := 0; c < 4; c++ {
			for ai := 0; ai < 2; ai++ {
				if archive.Coverage[bi][c][ai] != 4 {
					return false
				}
			}
		}
	}
	for _, t := range []f36LawTable{archive.A, archive.B, archive.Pooled} {
		for c := 0; c < 4; c++ {
			for ai := 0; ai < 2; ai++ {
				x := t[c][ai]
				if x.Mask < 1 || x.Mask > 15 || x.Lag < 1 || x.Lag > 3 {
					return false
				}
			}
		}
	}
	return true
}

type F36Trial struct {
	Kind                                                                             string
	Hits, ReturnHits, NovelHits, Actions, TrainingSteps, Work, FloorHits, Parameters int
	NetReward                                                                        float64
	GoalsSHA256, ActionsSHA256, SensorsSHA256, CheckpointSHA256, TerminalSHA256      string
	ColdMatches                                                                      bool
}

func f36Trial(archive f36Archive, logistic f36Model, kind string, seed uint32, sched string, cold bool) (F36Trial, []byte, error) {
	if !f36SeedOK(seed) || seed == 431 || seed == 433 {
		return F36Trial{}, nil, errF36
	}
	world, e := f36NewWorld(seed)
	if e != nil {
		return F36Trial{}, nil, e
	}
	m, e := f36Init(archive, kind, world.Sensors)
	if e != nil {
		return F36Trial{}, nil, e
	}
	if kind == "history-logistic" {
		m.Logistic = logistic.Logistic
	}
	// Cold restore at training boundary (contains the trained archive/weights, no replay).
	ck, _ := json.Marshal(m)
	if cold {
		m, e = f36LoadModel(ck)
		if e != nil {
			return F36Trial{}, nil, e
		}
	}
	tr := F36Trial{Kind: kind, TrainingSteps: 384, CheckpointSHA256: f27Hash(ck), ColdMatches: true}
	if kind == "history-logistic" {
		tr.Parameters = 16 * 41
	} else {
		tr.Parameters = 3*4*2*2 + 4*16
	}
	var goals []int
	var actions []int
	var obs [][2]int
	obs = append(obs, world.Sensors)
	for t := 0; t < 96; t++ {
		c, e := f36Cue(seed, sched, t)
		if e != nil {
			return tr, nil, e
		}
		goal, e := f36Goal(seed, t)
		if e != nil {
			return tr, nil, e
		}
		if t%4 == 0 {
			goals = append(goals, goal)
		}
		act := 0
		if tr.Actions < 36 {
			if kind == "random-budget" {
				if f27Mix(seed^uint32(t+1)*0x27d4eb2d)%3 > 0 {
					act = int(f27Mix(seed^uint32(t+1)*0x27d4eb2d) % 3)
				}
			} else if kind != "always-zero" {
				best := -math.MaxFloat64
				for a := 0; a <= 2; a++ {
					v := 0.0
					if kind == "history-logistic" {
						v, e = m.logisticGoal(t, c, a, goal)
					} else {
						v, e = m.scoreGoal(t, c, a, goal)
					}
					if e != nil {
						return tr, nil, e
					}
					if a > 0 {
						v -= .03
					}
					if v > best+1e-12 {
						best = v
						act = a
					}
				}
			}
		}
		if act > 0 {
			tr.Actions++
		}
		actions = append(actions, act)
		actual, next, e := world.step(t, c, act)
		if e != nil {
			return tr, nil, e
		}
		if kind == "history-logistic" {
			e = m.logisticUpdate(c, act, next)
		} else {
			e = m.observe(t, c, act, next)
		}
		if e != nil {
			return tr, nil, e
		}
		obs = append(obs, next)
		if t%4 == 3 && actual == goal {
			tr.Hits++
			if t/4 >= 12 && t/4 <= 17 {
				tr.ReturnHits++
			}
			if t/4 >= 18 {
				tr.NovelHits++
			}
		}
	}
	tr.NetReward = float64(tr.Hits) - .03*float64(tr.Actions)
	tr.Work = m.Work
	tr.FloorHits = m.FloorHits
	b, _ := json.Marshal(goals)
	tr.GoalsSHA256 = f27Hash(b)
	b, _ = json.Marshal(actions)
	tr.ActionsSHA256 = f27Hash(b)
	b, _ = json.Marshal(obs)
	tr.SensorsSHA256 = f27Hash(b)
	terminal, _ := json.Marshal(m)
	tr.TerminalSHA256 = f27Hash(terminal)
	return tr, terminal, nil
}

type F36Arm struct {
	Seed                 uint32
	Schedule             string
	Trials               [8]F36Trial
	BestConventionalHits int
	BestConventionalNet  float64
	Passes               bool
}
type F36Report struct {
	Schema, Parent, Classification, TrainingSHA256, DigestSHA256                                  string
	TrainingSeeds                                                                                 [2]uint32
	TransferSeeds                                                                                 [4]uint32
	Coverage                                                                                      [2][4][2]int
	Arms                                                                                          [4]F36Arm
	Passing                                                                                       int
	DevelopmentOnly, PriorNegativesPreserved                                                      bool
	ScientificAccepted, FirstUseConsumed, DispatchAuthorized, OwnerEligible, MatchedComputeProven bool
}

func f36Digest(r F36Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func f36Calculate() (F36Report, error) {
	archive, e := f36Train()
	if e != nil || !f36ValidParams(archive) {
		return F36Report{}, errF36
	}
	logistic, e := f36TrainLogistic()
	if e != nil {
		return F36Report{}, e
	}
	r := F36Report{Schema: F36Schema, Parent: F36Parent, TrainingSeeds: [2]uint32{431, 433}, TransferSeeds: [4]uint32{439, 443, 449, 457}, TrainingSHA256: archive.TrainSHA256, Coverage: archive.Coverage, DevelopmentOnly: true, PriorNegativesPreserved: true}
	for i, w := range f36Worlds() {
		arm := F36Arm{Seed: w.Seed, Schedule: w.Schedule, BestConventionalNet: math.Inf(-1)}
		for j, kind := range f36Kinds() {
			cold, ck, e := f36Trial(archive, logistic, kind, w.Seed, w.Schedule, true)
			if e != nil {
				return F36Report{}, fmt.Errorf("%s %d: %w", kind, w.Seed, e)
			}
			warm, wk, e := f36Trial(archive, logistic, kind, w.Seed, w.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(ck, wk) {
				return F36Report{}, errF36
			}
			arm.Trials[j] = cold
		}
		for j, tr := range arm.Trials {
			if tr.GoalsSHA256 != arm.Trials[0].GoalsSHA256 || tr.Actions > 36 || tr.TrainingSteps != 384 || tr.Hits < 0 || tr.Hits > 24 || tr.ReturnHits < 0 || tr.ReturnHits > 6 || tr.NovelHits < 0 || tr.NovelHits > 6 || len(tr.CheckpointSHA256) != 64 || len(tr.TerminalSHA256) != 64 || !tr.ColdMatches {
				return F36Report{}, errF36
			}
			if j >= 1 && j <= 3 {
				if tr.Hits > arm.BestConventionalHits {
					arm.BestConventionalHits = tr.Hits
				}
				if tr.NetReward > arm.BestConventionalNet {
					arm.BestConventionalNet = tr.NetReward
				}
			}
		}
		candidate := arm.Trials[0]
		arm.Passes = candidate.Hits >= arm.BestConventionalHits+2 && candidate.NetReward >= arm.BestConventionalNet+1.5 && candidate.Hits >= arm.Trials[4].Hits+2 && candidate.Hits >= arm.Trials[5].Hits+2
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F36NoGo
	if r.Passing == 4 {
		r.Classification = F36Signal
	}
	r.DigestSHA256 = f36Digest(r)
	return r, nil
}

var f36Once sync.Once
var f36Cached F36Report
var f36CachedErr error

func F36Development() (F36Report, error) {
	f36Once.Do(func() { f36Cached, f36CachedErr = f36Calculate() })
	return f36Cached, f36CachedErr
}
func F36Validate(r F36Report) error {
	if r.Schema != F36Schema || r.Parent != F36Parent || r.DigestSHA256 != f36Digest(r) || !r.DevelopmentOnly || !r.PriorNegativesPreserved || r.ScientificAccepted || r.FirstUseConsumed || r.DispatchAuthorized || r.OwnerEligible || r.MatchedComputeProven {
		return errF36
	}
	expected, e := F36Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF36
	}
	return nil
}
