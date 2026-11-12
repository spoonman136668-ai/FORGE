// Eureka F39: active intervention selection in an eight-state causal system.
// Synthetic developmental evidence ONLY: no execution, first-use, owner or deployment hooks.
package nativediscovery

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"math"
	"reflect"
	"sync"
)

const (
	F39Schema        = "forge.eureka.active-interventions.dev.v1"
	F39Parent        = "93a4b57dc9cf4afae9f4fdfe388b64edb858dded"
	F39NoGo          = "F39_DEV_NO_GO"
	F39Signal        = "F39_DEV_SIGNAL_UNVERIFIED"
	F39TrainSteps    = 192
	F39TransferSteps = 96
)

var errF39 = errors.New("FORGE_EUREKA_F39_SOURCE_OR_AUTHORITY_INVALID")

func f39Mix(x uint32) uint32 {
	x ^= x >> 16
	x *= 0x7feb352d
	x ^= x >> 15
	x *= 0x846ca68b
	x ^= x >> 16
	return x
}
func f39Kinds() [6]string {
	return [6]string{"uncertainty-directed", "greedy-bayes", "epsilon-greedy", "posterior-sampling", "wrong-action", "cold-zero"}
}

type f39WorldSpec struct {
	Seed     uint32
	Schedule string
}

func f39Worlds() [4]f39WorldSpec {
	return [4]f39WorldSpec{{503, "balanced"}, {509, "skewed"}, {521, "balanced"}, {523, "skewed"}}
}
func f39Training(seed uint32) bool { return seed == 491 || seed == 499 }
func f39SeedOK(seed uint32) bool {
	if f39Training(seed) {
		return true
	}
	for _, x := range f39Worlds() {
		if x.Seed == seed {
			return true
		}
	}
	return false
}
func f39Cue(seed uint32, schedule string, t int) (int, error) {
	if !f39SeedOK(seed) || t < 0 || t >= F39TransferSteps && !f39Training(seed) || t >= F39TrainSteps {
		return 0, errF39
	}
	if f39Training(seed) {
		if schedule != "training" {
			return 0, errF39
		}
		return (t / 3) % 4, nil
	}
	switch schedule {
	case "balanced":
		return (t/4 + int(seed%4)) % 4, nil
	case "skewed":
		if t%6 == 5 {
			return (t/6 + int(seed%4)) % 4, nil
		}
		return (t/6 + int(seed%2)) % 2, nil
	}
	return 0, errF39
}
func f39TrainingAction(t int) int { return t % 3 }
func f39Goal(seed uint32, t int) (int, error) {
	if f39Training(seed) || !f39SeedOK(seed) || t < 0 || t >= F39TransferSteps {
		return 0, errF39
	}
	return int(f39Mix(seed^uint32(t+1)*0x7f4a7c15^0x52dce729) & 7), nil
}
func f39Phase(seed uint32, t int) (byte, error) {
	if !f39SeedOK(seed) || t < 0 || t >= F39TrainSteps || !f39Training(seed) && t >= F39TransferSteps {
		return 0, errF39
	}
	if seed == 491 {
		return 'A', nil
	}
	if seed == 499 {
		return 'B', nil
	}
	startA := seed == 503 || seed == 521
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
		if seed == 503 || seed == 523 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF39
}

// Physical laws are *only* used by the simulated environment and forensic tests.
func f39Law(phase byte, c int) (int, int, int, error) {
	if c < 0 || c > 3 {
		return 0, 0, 0, errF39
	}
	ab, aa, bb := [4]int{1, 3, 0, 2}, [4]int{2, 1, 3, 2}, [4]int{1, 3, 2, 1}
	db, da, eb := [4]int{2, 0, 3, 1}, [4]int{1, 3, 2, 1}, [4]int{3, 1, 1, 2}
	switch phase {
	case 'A':
		return ab[c], aa[c], bb[c], nil
	case 'B':
		return db[c], da[c], eb[c], nil
	case 'C':
		if c%2 == 0 {
			return ab[c], da[c], eb[c], nil
		}
		return db[c], aa[c], bb[c], nil
	case 'D':
		if c%2 == 0 {
			return db[c], aa[c], bb[c], nil
		}
		return ab[c], da[c], eb[c], nil
	}
	return 0, 0, 0, errF39
}
func f39Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f39SeedOK(seed) || t < 0 || t > F39TrainSteps || !f39Training(seed) && t > F39TransferSteps || clean < 0 || clean > 7 || sensor < 0 || sensor > 1 {
		return 0, errF39
	}
	u := f39Mix(seed^uint32(t+1)*0x9e3779b9^uint32(sensor+1)*0x85ebca6b^0x6a09e667) % 100
	if sensor == 0 {
		if u < 90 {
			return clean, nil
		}
		if u < 96 {
			return (clean + 1) % 8, nil
		}
		return (clean + 7) % 8, nil
	}
	if u < 80 {
		return clean, nil
	}
	if u < 90 {
		return (clean + 1) % 8, nil
	}
	return (clean + 7) % 8, nil
}
func f39Likelihood(observation [2]int, state int) float64 {
	if state < 0 || state > 7 {
		return 0
	}
	q := 1.0
	for i, y := range observation {
		if y < 0 || y > 7 {
			return 0
		}
		switch i {
		case 0:
			if y == state {
				q *= .90
			} else if y == (state+1)%8 {
				q *= .06
			} else if y == (state+7)%8 {
				q *= .04
			} else {
				return 0
			}
		case 1:
			if y == state {
				q *= .80
			} else if y == (state+1)%8 {
				q *= .10
			} else if y == (state+7)%8 {
				q *= .10
			} else {
				return 0
			}
		}
	}
	return q
}
func f39Posterior(obs [2]int) ([8]float64, error) {
	var p [8]float64
	z := 0.0
	for s := 0; s < 8; s++ {
		p[s] = f39Likelihood(obs, s)
		z += p[s]
	}
	if z <= 0 {
		return p, errF39
	}
	for s := range p {
		p[s] /= z
	}
	return p, nil
}
func f39DeltaEvidence(prev, next [2]int) ([8]float64, error) {
	var out [8]float64
	p, e := f39Posterior(prev)
	if e != nil {
		return out, e
	}
	q, e := f39Posterior(next)
	if e != nil {
		return out, e
	}
	for s := 0; s < 8; s++ {
		for n := 0; n < 8; n++ {
			out[(n-s+8)%8] += p[s] * q[n]
		}
	}
	return out, nil
}

type f39World struct {
	Seed     uint32
	Schedule string
	S, Seen  int
	Sensors  [2]int
}

func f39NewWorld(seed uint32, schedule string) (f39World, error) {
	if _, e := f39Cue(seed, schedule, 0); e != nil {
		return f39World{}, e
	}
	w := f39World{Seed: seed, Schedule: schedule, S: int(f39Mix(seed^0x4cf5ad43) & 7)}
	for i := 0; i < 2; i++ {
		v, e := f39Sensor(seed, 0, w.S, i)
		if e != nil {
			return f39World{}, e
		}
		w.Sensors[i] = v
	}
	return w, nil
}
func (w *f39World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || a < 0 || a > 3 || c < 0 || c > 3 {
		return 0, [2]int{}, errF39
	}
	phase, e := f39Phase(w.Seed, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	base, e1, e2, e := f39Law(phase, c)
	if e != nil {
		return 0, [2]int{}, e
	}
	delta := base
	if a&1 != 0 {
		delta += e1
	}
	if a&2 != 0 {
		delta += e2
	}
	w.S = (w.S + delta) % 8
	w.Seen++
	var next [2]int
	for i := 0; i < 2; i++ {
		v, e := f39Sensor(w.Seed, w.Seen, w.S, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = v
	}
	w.Sensors = next
	return w.S, next, nil
}
func f39Q(bank [4][4][8]float64, c, a int) [8]float64 {
	var q [8]float64
	den := 8.0
	for d := 0; d < 8; d++ {
		den += bank[c][a][d]
	}
	for d := 0; d < 8; d++ {
		q[d] = (bank[c][a][d] + 1) / den
	}
	return q
}
func f39Agreement(p, q [8]float64) float64 {
	v := 0.0
	for d := 0; d < 8; d++ {
		v += p[d] * q[d]
	}
	return math.Max(v, 1e-12)
}

type f39Model struct {
	Kind         string           `json:"kind"`
	A            [4][4][8]float64 `json:"source_a"`
	B            [4][4][8]float64 `json:"source_b"`
	Scratch      [4][4][8]float64 `json:"scratch"`
	Counts       [4][4]float64    `json:"counts"`
	W            [4][3]float64    `json:"source_weights"`
	Prev         [2]int           `json:"previous_observation"`
	HasWorld     bool             `json:"has_world"`
	TrainingSeen int              `json:"training_seen"`
	TransferSeen int              `json:"transfer_seen"`
	Work         int              `json:"work"`
}

func f39New(kind string) (f39Model, error) {
	for _, k := range f39Kinds() {
		if kind == k {
			return f39Model{Kind: kind}, nil
		}
	}
	return f39Model{}, errF39
}
func (m *f39Model) beginWorld(obs [2]int) error {
	if _, e := f39Posterior(obs); e != nil {
		return errF39
	}
	m.Prev = obs
	m.HasWorld = true
	m.Scratch = [4][4][8]float64{}
	m.TransferSeen = 0
	for c := 0; c < 4; c++ {
		m.W[c] = [3]float64{1.0 / 3, 1.0 / 3, 1.0 / 3}
	}
	return nil
}
func (m *f39Model) components(c, a int) [3][8]float64 {
	return [3][8]float64{f39Q(m.A, c, a), f39Q(m.B, c, a), f39Q(m.Scratch, c, a)}
}
func f39Shift(p, q [8]float64) [8]float64 {
	var out [8]float64
	for s := 0; s < 8; s++ {
		for d := 0; d < 8; d++ {
			out[(s+d)%8] += p[s] * q[d]
		}
	}
	return out
}
func (m *f39Model) actionForecast(c, a int) ([8]float64, [3][8]float64, error) {
	var empty [8]float64
	var slices [3][8]float64
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 3 {
		return empty, slices, errF39
	}
	old, e := f39Posterior(m.Prev)
	if e != nil {
		return empty, slices, e
	}
	comps := m.components(c, a)
	var mixture [8]float64
	for j := 0; j < 3; j++ {
		for d := 0; d < 8; d++ {
			mixture[d] += m.W[c][j] * comps[j][d]
		}
		slices[j] = f39Shift(old, comps[j])
	}
	// All methods perform both mixture and component forecasts, regardless of policy.
	m.Work += 256
	return f39Shift(old, mixture), slices, nil
}
func (m *f39Model) observe(c, a int, next [2]int, training bool, worldA bool) error {
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 3 {
		return errF39
	}
	ev, e := f39DeltaEvidence(m.Prev, next)
	if e != nil {
		return e
	}
	if training {
		target := &m.B
		if worldA {
			target = &m.A
		}
		for d := 0; d < 8; d++ {
			target[c][a][d] += ev[d]
		}
		m.Counts[c][a]++
		m.TrainingSeen++
	} else {
		credited := a
		if m.Kind == "wrong-action" {
			if a == 1 {
				credited = 2
			} else if a == 2 {
				credited = 1
			}
		}
		q := m.components(c, credited)
		var nextW [3]float64
		z := 0.0
		for j := 0; j < 3; j++ {
			nextW[j] = (.97*m.W[c][j] + .03/3) * f39Agreement(ev, q[j])
			z += nextW[j]
		}
		if z <= 0 {
			return errF39
		}
		for j := 0; j < 3; j++ {
			nextW[j] /= z
		}
		m.W[c] = nextW
		for d := 0; d < 8; d++ {
			m.Scratch[c][credited][d] += ev[d]
		}
		m.Counts[c][credited]++
		m.TransferSeen++
		m.Work += 256
	}
	m.Prev = next
	return nil
}
func (m *f39Model) decide(seed uint32, t, c, goal, used int) (int, [4][8]float64, error) {
	var predictions [4][8]float64
	if !m.HasWorld || c < 0 || c > 3 || goal < 0 || goal > 7 || t < 0 || t >= F39TransferSteps || used < 0 || used > 48 {
		return 0, predictions, errF39
	}
	best, bestScore := 0, math.Inf(-1)
	var thompson int
	choice := float64(f39Mix(seed^uint32(t+1)*0x2ff61471)%100000) / 100000
	for j := 0; j < 3; j++ {
		choice -= m.W[c][j]
		if choice < 0 {
			thompson = j
			break
		}
	}
	for a := 0; a < 4; a++ {
		p, each, e := m.actionForecast(c, a)
		if e != nil {
			return 0, predictions, e
		}
		predictions[a] = p
		if a > 0 && used >= 48 {
			continue
		}
		cost := 0.0
		if a > 0 {
			cost = .04
		}
		// Compute this fixed diagnostic for all policies, even controls.
		bonus := .08 / math.Sqrt(1+m.Counts[c][a])
		score := p[goal] - cost
		if m.Kind == "uncertainty-directed" || m.Kind == "wrong-action" || m.Kind == "cold-zero" {
			score += bonus
		}
		if m.Kind == "posterior-sampling" {
			score = each[thompson][goal] - cost
		}
		if score > bestScore+1e-14 {
			best, bestScore = a, score
		}
	}
	if m.Kind == "epsilon-greedy" && f39Mix(seed^uint32(t+1)*0x14c2d7b1)%10 == 0 {
		pick := int(f39Mix(seed^uint32(t+1)*0x35f078da) % 4)
		if pick == 0 || used < 48 {
			best = pick
		}
	}
	return best, predictions, nil
}
func f39Valid(m f39Model) bool {
	found := false
	for _, k := range f39Kinds() {
		if k == m.Kind {
			found = true
		}
	}
	if !found || m.TrainingSeen != 384 || m.TransferSeen < 0 || m.TransferSeen > 96 || m.Work < 0 {
		return false
	}
	for _, v := range m.Prev {
		if v < 0 || v > 7 {
			return false
		}
	}
	for c := 0; c < 4; c++ {
		sum := 0.0
		for _, v := range m.W[c] {
			if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 || v > 1 {
				return false
			}
			sum += v
		}
		if m.HasWorld && math.Abs(sum-1) > 1e-8 {
			return false
		}
		for a := 0; a < 4; a++ {
			n := m.Counts[c][a]
			if math.IsNaN(n) || math.IsInf(n, 0) || n < 0 || n > 100 {
				return false
			}
			for d := 0; d < 8; d++ {
				for _, v := range [3]float64{m.A[c][a][d], m.B[c][a][d], m.Scratch[c][a][d]} {
					if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 || v > 200 {
						return false
					}
				}
			}
		}
	}
	return true
}
func f39Save(m f39Model) ([]byte, error) {
	if !f39Valid(m) {
		return nil, errF39
	}
	return json.Marshal(m)
}
func f39Load(raw []byte) (f39Model, error) {
	var m f39Model
	if json.Unmarshal(raw, &m) != nil || !f39Valid(m) {
		return f39Model{}, errF39
	}
	b, e := json.Marshal(m)
	if e != nil || !bytes.Equal(b, raw) {
		return f39Model{}, errF39
	}
	return m, nil
}
func f39Train(kind string) (f39Model, error) {
	m, e := f39New(kind)
	if e != nil {
		return f39Model{}, e
	}
	for _, seed := range []uint32{491, 499} {
		w, e := f39NewWorld(seed, "training")
		if e != nil {
			return f39Model{}, e
		}
		if e = m.beginWorld(w.Sensors); e != nil {
			return f39Model{}, e
		}
		for t := 0; t < F39TrainSteps; t++ {
			c, e := f39Cue(seed, "training", t)
			if e != nil {
				return f39Model{}, e
			}
			a := f39TrainingAction(t)
			_, next, e := w.step(t, c, a)
			if e != nil {
				return f39Model{}, e
			}
			if e = m.observe(c, a, next, true, seed == 491); e != nil {
				return f39Model{}, e
			}
		}
	}
	if m.TrainingSeen != 384 {
		return f39Model{}, errF39
	}
	for c := 0; c < 4; c++ {
		for a := 0; a < 3; a++ {
			if m.Counts[c][a] != 32 {
				return f39Model{}, errF39
			}
		}
		if m.Counts[c][3] != 0 {
			return f39Model{}, errF39
		}
	}
	if kind == "cold-zero" {
		m.A = [4][4][8]float64{}
		m.B = [4][4][8]float64{}
		m.Counts = [4][4]float64{}
	}
	// Source training never gives transfer an oracle on phase or clean state.
	return m, nil
}
func f39Hash(v any) string         { b, _ := json.Marshal(v); return f39SHA256(b) }
func f39SHA256(data []byte) string { sum := sha256.Sum256(data); return hex.EncodeToString(sum[:]) }

type F39Trial struct {
	Kind             string  `json:"kind"`
	Goals            int     `json:"goals"`
	PhaseGoals       [4]int  `json:"phase_goals"`
	Interventions    int     `json:"interventions"`
	NetReward        float64 `json:"net_reward"`
	TrainingSeen     int     `json:"training_seen"`
	TransferSeen     int     `json:"transfer_seen"`
	Work             int     `json:"counted_work"`
	Parameters       int     `json:"parameter_count"`
	ActionsSHA256    string  `json:"actions_sha256"`
	SensorsSHA256    string  `json:"sensors_sha256"`
	ForecastSHA256   string  `json:"forecasts_sha256"`
	CheckpointSHA256 string  `json:"checkpoint_sha256"`
	TerminalSHA256   string  `json:"terminal_sha256"`
	ColdMatches      bool    `json:"cold_matches"`
}
type F39WorldReport struct {
	Seed                   uint32      `json:"seed"`
	Schedule               string      `json:"schedule"`
	Trials                 [6]F39Trial `json:"trials"`
	BestConventionalGoals  int         `json:"best_conventional_goals"`
	BestConventionalReturn int         `json:"best_conventional_return"`
	BestConventionalNovel  int         `json:"best_conventional_novel"`
	GainGoals              int         `json:"gain_goals"`
	GainWrongAction        int         `json:"gain_wrong_action"`
	GainColdZero           int         `json:"gain_cold_zero"`
	Passes                 bool        `json:"passes"`
}
type F39Report struct {
	Schema                           string            `json:"schema"`
	Parent                           string            `json:"parent"`
	Classification                   string            `json:"classification"`
	TrainingSeeds                    [2]uint32         `json:"training_seeds"`
	TransferSeeds                    [4]uint32         `json:"transfer_seeds"`
	TrainingStepsPerWorld            int               `json:"training_steps_per_world"`
	TransferSteps                    int               `json:"transfer_steps"`
	SourceTraceSHA256                string            `json:"source_trace_sha256"`
	MinGoalGain                      int               `json:"min_goal_gain"`
	MinNovelGain                     int               `json:"min_novel_gain"`
	MinAblationGain                  int               `json:"min_ablation_gain"`
	MaxInterventions                 int               `json:"max_interventions"`
	MaxWorkRatio                     float64           `json:"max_work_ratio"`
	Bonus                            float64           `json:"bonus"`
	Hazard                           float64           `json:"hazard"`
	Worlds                           [4]F39WorldReport `json:"worlds"`
	Passing                          int               `json:"passing"`
	DevelopmentOnly                  bool              `json:"development_only"`
	EarlierNegativesPreserved        bool              `json:"earlier_negatives_preserved"`
	FirstUseConsumed                 bool              `json:"first_use_consumed"`
	ScientificAccepted               bool              `json:"scientific_accepted"`
	OwnerEligible                    bool              `json:"owner_eligible"`
	DispatchAuthorized               bool              `json:"dispatch_authorized"`
	MatchedWholeProcessComputeProven bool              `json:"matched_whole_process_compute_proven"`
	DigestSHA256                     string            `json:"digest_sha256"`
}

func f39SourceTrace() (string, error) {
	type trace struct {
		Seed    uint32
		Actions []int
		Sensors [][2]int
	}
	out := make([]trace, 0, 2)
	for _, seed := range []uint32{491, 499} {
		w, e := f39NewWorld(seed, "training")
		if e != nil {
			return "", e
		}
		v := trace{Seed: seed, Sensors: [][2]int{w.Sensors}}
		for t := 0; t < F39TrainSteps; t++ {
			c, e := f39Cue(seed, "training", t)
			if e != nil {
				return "", e
			}
			a := f39TrainingAction(t)
			v.Actions = append(v.Actions, a)
			_, n, e := w.step(t, c, a)
			if e != nil {
				return "", e
			}
			v.Sensors = append(v.Sensors, n)
		}
		out = append(out, v)
	}
	return f39Hash(out), nil
}
func f39Trial(m f39Model, seed uint32, sched string, cold bool) (F39Trial, []byte, error) {
	if !f39SeedOK(seed) || f39Training(seed) || m.TrainingSeen != 384 || m.TransferSeen != 0 {
		return F39Trial{}, nil, errF39
	}
	checkpoint, e := f39Save(m)
	if e != nil {
		return F39Trial{}, nil, e
	}
	if cold {
		m, e = f39Load(checkpoint)
		if e != nil {
			return F39Trial{}, nil, e
		}
	}
	w, e := f39NewWorld(seed, sched)
	if e != nil {
		return F39Trial{}, nil, e
	}
	if e = m.beginWorld(w.Sensors); e != nil {
		return F39Trial{}, nil, e
	}
	tr := F39Trial{Kind: m.Kind, TrainingSeen: 384, Parameters: 412, CheckpointSHA256: f39SHA256(checkpoint), ColdMatches: true}
	work := m.Work
	actions := make([]int, 0, 96)
	sensors := make([][2]int, 0, 97)
	forecasts := make([][4][8]float64, 0, 96)
	sensors = append(sensors, w.Sensors)
	for t := 0; t < F39TransferSteps; t++ {
		cue, e := f39Cue(seed, sched, t)
		if e != nil {
			return F39Trial{}, nil, e
		}
		goal, e := f39Goal(seed, t)
		if e != nil {
			return F39Trial{}, nil, e
		}
		action, p, e := m.decide(seed, t, cue, goal, tr.Interventions)
		if e != nil {
			return F39Trial{}, nil, e
		}
		if action < 0 || action > 3 || action != 0 && tr.Interventions >= 48 {
			return F39Trial{}, nil, errF39
		}
		if action != 0 {
			tr.Interventions++
		}
		clean, next, e := w.step(t, cue, action)
		if e != nil {
			return F39Trial{}, nil, e
		}
		if clean == goal {
			tr.Goals++
			tr.PhaseGoals[t/24]++
		}
		if e = m.observe(cue, action, next, false, false); e != nil {
			return F39Trial{}, nil, e
		}
		actions = append(actions, action)
		sensors = append(sensors, next)
		forecasts = append(forecasts, p)
	}
	if tr.Interventions > 48 || m.TransferSeen != 96 {
		return F39Trial{}, nil, errF39
	}
	tr.NetReward = float64(tr.Goals) - .04*float64(tr.Interventions)
	tr.TransferSeen = m.TransferSeen
	tr.Work = m.Work - work
	tr.ActionsSHA256 = f39Hash(actions)
	tr.SensorsSHA256 = f39Hash(sensors)
	tr.ForecastSHA256 = f39Hash(forecasts)
	terminal, e := f39Save(m)
	if e != nil {
		return F39Trial{}, nil, e
	}
	tr.TerminalSHA256 = f39SHA256(terminal)
	return tr, terminal, nil
}
func f39Digest(r F39Report) string { r.DigestSHA256 = ""; return f39Hash(r) }
func f39Compute() (F39Report, error) {
	r := F39Report{Schema: F39Schema, Parent: F39Parent, Classification: F39NoGo, TrainingSeeds: [2]uint32{491, 499}, TransferSeeds: [4]uint32{503, 509, 521, 523}, TrainingStepsPerWorld: 192, TransferSteps: 96, MinGoalGain: 4, MinNovelGain: 3, MinAblationGain: 4, MaxInterventions: 48, MaxWorkRatio: 1.25, Bonus: .08, Hazard: .03, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	h, e := f39SourceTrace()
	if e != nil {
		return F39Report{}, e
	}
	r.SourceTraceSHA256 = h
	var trained [6]f39Model
	for i, k := range f39Kinds() {
		m, e := f39Train(k)
		if e != nil {
			return F39Report{}, e
		}
		trained[i] = m
	}
	// All non-ablated policies start with literally identical trained causal banks.
	for i := 1; i < 5; i++ {
		if i == 5 {
			continue
		}
		if !reflect.DeepEqual(trained[0].A, trained[i].A) || !reflect.DeepEqual(trained[0].B, trained[i].B) {
			return F39Report{}, errF39
		}
	}
	for i, world := range f39Worlds() {
		v := F39WorldReport{Seed: world.Seed, Schedule: world.Schedule}
		for j := range trained {
			cold, cb, e := f39Trial(trained[j], world.Seed, world.Schedule, true)
			if e != nil {
				return F39Report{}, e
			}
			warm, wb, e := f39Trial(trained[j], world.Seed, world.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return F39Report{}, errF39
			}
			v.Trials[j] = cold
		}
		for j, trial := range v.Trials {
			if trial.Kind != f39Kinds()[j] || trial.Interventions > 48 || trial.TransferSeen != 96 || trial.TrainingSeen != 384 || trial.Work <= 0 || trial.Goals < 0 || trial.Goals > 96 {
				return F39Report{}, errF39
			}
			if j >= 1 && j <= 3 {
				if trial.Goals > v.BestConventionalGoals {
					v.BestConventionalGoals = trial.Goals
				}
				if trial.PhaseGoals[2] > v.BestConventionalReturn {
					v.BestConventionalReturn = trial.PhaseGoals[2]
				}
				if trial.PhaseGoals[3] > v.BestConventionalNovel {
					v.BestConventionalNovel = trial.PhaseGoals[3]
				}
			}
		}
		cand := v.Trials[0]
		v.GainGoals = cand.Goals - v.BestConventionalGoals
		v.GainWrongAction = cand.Goals - v.Trials[4].Goals
		v.GainColdZero = cand.Goals - v.Trials[5].Goals
		// Strongest conventional by raw goals, tie broken by model order.
		bestIndex := 1
		for j := 2; j <= 3; j++ {
			if v.Trials[j].Goals > v.Trials[bestIndex].Goals {
				bestIndex = j
			}
		}
		v.Passes = v.GainGoals >= 4 && cand.PhaseGoals[3] >= v.BestConventionalNovel+3 && cand.PhaseGoals[2] >= v.BestConventionalReturn && v.GainWrongAction >= 4 && v.GainColdZero >= 4 && float64(cand.Work) <= 1.25*float64(v.Trials[bestIndex].Work)
		if v.Passes {
			r.Passing++
		}
		r.Worlds[i] = v
	}
	if r.Passing == 4 {
		r.Classification = F39Signal
	}
	r.DigestSHA256 = f39Digest(r)
	return r, nil
}

var f39Once sync.Once
var f39Cached F39Report
var f39CacheError error

func F39Development() (F39Report, error) {
	f39Once.Do(func() { f39Cached, f39CacheError = f39Compute() })
	return f39Cached, f39CacheError
}
func F39Validate(r F39Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f39Digest(r) || !r.DevelopmentOnly || !r.EarlierNegativesPreserved || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.MatchedWholeProcessComputeProven {
		return errF39
	}
	expected, e := F39Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF39
	}
	return nil
}
