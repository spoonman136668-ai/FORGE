// Eureka F27 sequential action-consequence learning and observation-shift transfer.
// Synthetic developmental comparison only; no owner, first-use or runtime integration.
package nativediscovery

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"math"
	"reflect"
)

const (
	F27Schema        = "forge.native-discovery.sequential-transfer.dev.v1"
	F27NoGo          = "F27_DEV_NO_GO"
	F27Signal        = "F27_DEV_SIGNAL_UNVERIFIED"
	F27Parent        = "b41f0c5b99f26d955952b315487fdd4021e59f5f"
	F27TrainingSteps = 128
	F27TransferSteps = 48
)

var errF27 = errors.New("FORGE_EUREKA_F27_SOURCE_OR_AUTHORITY_INVALID")

func f27Kinds() [6]string {
	return [6]string{"recurrent-causal-delta", "markov-bayes", "delta-count", "online-softmax", "action-blind", "cold-zero"}
}
func f27TransferWorlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{{227, "balanced"}, {229, "skewed"}, {233, "balanced"}, {239, "skewed"}}
}
func f27Mix(x uint32) uint32 {
	x ^= x >> 16
	x *= 0x7feb352d
	x ^= x >> 15
	x *= 0x846ca68b
	return x ^ (x >> 16)
}
func f27Known(seed uint32) bool {
	switch seed {
	case 211, 223, 227, 229, 233, 239:
		return true
	}
	return false
}
func f27Cue(seed uint32, schedule string, t int) (int, error) {
	if !f27Known(seed) || t < 0 || t >= 64 {
		return 0, errF27
	}
	switch schedule {
	case "balanced":
		return (3*t + int(seed%4)) % 4, nil
	case "skewed":
		if t%5 == 4 {
			return (t/5 + int(seed%4)) % 4, nil
		}
		return (t/5 + int(seed%2)) % 2, nil
	}
	return 0, errF27
}
func f27Action(t int) int {
	if t%4 == 0 || t%7 == 0 {
		return 1
	}
	return 0
}
func f27Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f27Known(seed) || t < 0 || t > 64 || clean < 0 || clean > 3 || sensor < 0 || sensor > 1 {
		return 0, errF27
	}
	// Separate deterministic stream per sensor and step, not a prediction-time oracle.
	u := f27Mix(seed^(uint32(t+1)*0x9e3779b9)^(uint32(sensor+1)*0x85ebca6b)^0x6a09e667) % 100
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
func f27Likelihood(ob [2]int, clean int) float64 {
	result := 1.0
	for sensor, v := range ob {
		if v < 0 || v > 3 {
			return 0
		}
		if sensor == 0 {
			switch v {
			case clean:
				result *= .90
			case (clean + 1) % 4:
				result *= .06
			case (clean + 3) % 4:
				result *= .04
			default:
				return 0
			}
		} else {
			switch v {
			case clean:
				result *= .80
			case (clean + 1) % 4:
				result *= .10
			case (clean + 3) % 4:
				result *= .10
			default:
				return 0
			}
		}
	}
	return result
}
func f27Posterior(ob [2]int) ([4]float64, error) {
	var out [4]float64
	z := 0.0
	for s := 0; s < 4; s++ {
		out[s] = f27Likelihood(ob, s)
		z += out[s]
	}
	if z <= 0 {
		return out, errF27
	}
	for i := range out {
		out[i] /= z
	}
	return out, nil
}
func f27ArgMax(p [4]float64) int {
	winner := 0
	for i := 1; i < 4; i++ {
		if p[i] > p[winner] {
			winner = i
		}
	}
	return winner
}
func f27Hash(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }

// State tracks learned transitions, separate from the ephemeral per-world filtered state.
// Numeric 4-state observation stream, no tokenization or text prediction.
type f27Model struct {
	Mode         string              `json:"mode"`
	Delta        [4][2][4]float64    `json:"delta"`
	Markov       [4][2][4][4]float64 `json:"markov"`
	Weights      [4][18]float64      `json:"weights"`
	Belief       [4]float64          `json:"belief"`
	Previous     [2]int              `json:"previous"`
	HasWorld     bool                `json:"has_world"`
	TrainingSeen int                 `json:"training_seen"`
	TransferSeen int                 `json:"transfer_seen"`
	Work         int                 `json:"work"`
}

func f27New(kind string) (f27Model, error) {
	for _, k := range f27Kinds() {
		if k == kind {
			return f27Model{Mode: kind}, nil
		}
	}
	return f27Model{}, errF27
}
func (m *f27Model) beginWorld(ob [2]int) error {
	p, e := f27Posterior(ob)
	if e != nil {
		return e
	}
	m.Belief = p
	m.Previous = ob
	m.HasWorld = true
	return nil
}
func (m *f27Model) effectiveAction(a int) int {
	if m.Mode == "action-blind" {
		return 0
	}
	return a
}
func (m *f27Model) deltaProb(c, a int) [4]float64 {
	var q [4]float64
	total := 4.0
	for d := 0; d < 4; d++ {
		total += m.Delta[c][a][d]
	}
	for d := 0; d < 4; d++ {
		q[d] = (m.Delta[c][a][d] + 1) / total
	}
	return q
}
func (m *f27Model) markovProb(c, a, s int) [4]float64 {
	var q [4]float64
	total := 4.0
	for next := 0; next < 4; next++ {
		total += m.Markov[c][a][s][next]
	}
	for next := 0; next < 4; next++ {
		q[next] = (m.Markov[c][a][s][next] + 1) / total
	}
	return q
}
func f27Features(ob [2]int, c, a int) [18]float64 {
	var x [18]float64
	x[0] = 1
	x[1+ob[0]] = 1
	x[5+ob[1]] = 1
	x[9+c] = 1
	x[13] = float64(a)
	x[14+c] = float64(a)
	return x
}
func (m *f27Model) softmax(x [18]float64) [4]float64 {
	var z, p [4]float64
	largest := math.Inf(-1)
	for k := 0; k < 4; k++ {
		for j := 0; j < 18; j++ {
			z[k] += m.Weights[k][j] * x[j]
		}
		if z[k] > largest {
			largest = z[k]
		}
	}
	total := 0.0
	for k := 0; k < 4; k++ {
		p[k] = math.Exp(z[k] - largest)
		total += p[k]
	}
	for k := 0; k < 4; k++ {
		p[k] /= total
	}
	return p
}
func (m *f27Model) forecast(c, a int) ([4]float64, error) {
	var p [4]float64
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return p, errF27
	}
	eff := m.effectiveAction(a)
	switch m.Mode {
	case "recurrent-causal-delta", "action-blind", "cold-zero", "delta-count":
		q := m.deltaProb(c, eff)
		b := m.Belief
		if m.Mode == "delta-count" {
			b = [4]float64{}
			b[f27ArgMax(m.Belief)] = 1
		}
		for s := 0; s < 4; s++ {
			for d := 0; d < 4; d++ {
				p[(s+d)%4] += b[s] * q[d]
			}
		}
		m.Work += 16
	case "markov-bayes":
		for s := 0; s < 4; s++ {
			q := m.markovProb(c, eff, s)
			for next := 0; next < 4; next++ {
				p[next] += m.Belief[s] * q[next]
			}
		}
		m.Work += 16
	case "online-softmax":
		p = m.softmax(f27Features(m.Previous, c, eff))
		m.Work += 72
	default:
		return p, errF27
	}
	return p, nil
}
func (m *f27Model) observe(c, a int, next [2]int, training bool) error {
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return errF27
	}
	obs, e := f27Posterior(next)
	if e != nil {
		return e
	}
	eff := m.effectiveAction(a)
	switch m.Mode {
	case "recurrent-causal-delta", "action-blind", "cold-zero":
		q := m.deltaProb(c, eff)
		var delta [4]float64
		var posterior [4]float64
		total := 0.0
		for s := 0; s < 4; s++ {
			for d := 0; d < 4; d++ {
				nxt := (s + d) % 4
				w := m.Belief[s] * q[d] * f27Likelihood(next, nxt)
				delta[d] += w
				posterior[nxt] += w
				total += w
			}
		}
		if total <= 0 {
			return errF27
		}
		for d := 0; d < 4; d++ {
			m.Delta[c][eff][d] += delta[d] / total
			posterior[d] /= total
		}
		m.Belief = posterior
		m.Work += 64
	case "markov-bayes":
		var posterior [4]float64
		var joint [4][4]float64
		total := 0.0
		for s := 0; s < 4; s++ {
			q := m.markovProb(c, eff, s)
			for nxt := 0; nxt < 4; nxt++ {
				w := m.Belief[s] * q[nxt] * f27Likelihood(next, nxt)
				joint[s][nxt] = w
				posterior[nxt] += w
				total += w
			}
		}
		if total <= 0 {
			return errF27
		}
		for s := 0; s < 4; s++ {
			for nxt := 0; nxt < 4; nxt++ {
				m.Markov[c][eff][s][nxt] += joint[s][nxt] / total
			}
		}
		for s := 0; s < 4; s++ {
			posterior[s] /= total
		}
		m.Belief = posterior
		m.Work += 64
	case "delta-count":
		prev := f27ArgMax(m.Belief)
		current := f27ArgMax(obs)
		m.Delta[c][eff][(current-prev+4)%4]++
		m.Belief = obs
		m.Work += 16
	case "online-softmax":
		features := f27Features(m.Previous, c, eff)
		for pass := 0; pass < 4; pass++ {
			p := m.softmax(features)
			for k := 0; k < 4; k++ {
				for j := 0; j < 18; j++ {
					m.Weights[k][j] += .05 * ((obs[k]-p[k])*features[j] - .0001*m.Weights[k][j])
				}
			}
		}
		m.Belief = obs
		m.Work += 4 * 72
	default:
		return errF27
	}
	m.Previous = next
	if training {
		m.TrainingSeen++
	} else {
		m.TransferSeen++
	}
	return nil
}
func (m *f27Model) resetTrainingForAblation() {
	m.Delta = [4][2][4]float64{}
	m.Markov = [4][2][4][4]float64{}
	m.Weights = [4][18]float64{}
}
func f27Save(m f27Model) ([]byte, error) {
	if !f27Valid(m) {
		return nil, errF27
	}
	return json.Marshal(m)
}
func f27Valid(m f27Model) bool {
	kindOK := false
	for _, k := range f27Kinds() {
		if m.Mode == k {
			kindOK = true
		}
	}
	if !kindOK || m.Work < 0 || m.TrainingSeen < 0 || m.TrainingSeen > F27TrainingSteps || m.TransferSeen < 0 || m.TransferSeen > F27TransferSteps {
		return false
	}
	for _, u := range m.Belief {
		if math.IsNaN(u) || math.IsInf(u, 0) || u < 0 || u > 1 {
			return false
		}
	}
	for c := 0; c < 4; c++ {
		for a := 0; a < 2; a++ {
			for d := 0; d < 4; d++ {
				v := m.Delta[c][a][d]
				if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 {
					return false
				}
				for n := 0; n < 4; n++ {
					v = m.Markov[c][a][d][n]
					if math.IsNaN(v) || math.IsInf(v, 0) || v < 0 {
						return false
					}
				}
			}
		}
	}
	for k := 0; k < 4; k++ {
		for j := 0; j < 18; j++ {
			v := m.Weights[k][j]
			if math.IsNaN(v) || math.IsInf(v, 0) {
				return false
			}
		}
	}
	return true
}
func f27Load(raw []byte) (f27Model, error) {
	var m f27Model
	if json.Unmarshal(raw, &m) != nil || !f27Valid(m) {
		return f27Model{}, errF27
	}
	canonical, e := json.Marshal(m)
	if e != nil || !bytes.Equal(canonical, raw) {
		return f27Model{}, errF27
	}
	return m, nil
}

// Hidden environment: simulator and scorer are isolated from model methods.
type f27World struct {
	Seed     uint32
	Schedule string
	S        int
	Offset   int
	Seen     int
	Sensors  [2]int
}

func f27NewWorld(seed uint32, sched string) (f27World, error) {
	if _, e := f27Cue(seed, sched, 0); e != nil {
		return f27World{}, e
	}
	w := f27World{Seed: seed, Schedule: sched, S: int(f27Mix(seed^0x4cf5ad43) & 3), Offset: int(f27Mix(seed^0x6d2b79f5) & 3)}
	for i := 0; i < 2; i++ {
		obs, e := f27Sensor(seed, 0, w.clean(), i)
		if e != nil {
			return f27World{}, e
		}
		w.Sensors[i] = obs
	}
	return w, nil
}
func (w *f27World) clean() int { return (w.S + w.Offset) % 4 }
func (w *f27World) step(t, c, a int) (int, [2]int, error) {
	if t != w.Seen || t < 0 || t >= 64 || c < 0 || c > 3 || a < 0 || a > 1 {
		return 0, [2]int{}, errF27
	}
	base := [4]int{1, 0, 3, 2}
	effect := [4]int{2, 1, 2, 3}
	w.S = (w.S + base[c] + a*effect[c]) % 4
	w.Seen++
	answer := w.clean()
	var next [2]int
	for i := 0; i < 2; i++ {
		x, e := f27Sensor(w.Seed, w.Seen, answer, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = x
	}
	w.Sensors = next
	return answer, next, nil
}

type F27Trial struct {
	Kind              string `json:"kind"`
	Score             int    `json:"score"`
	First16           int    `json:"first16"`
	Middle16          int    `json:"middle16"`
	Last16            int    `json:"last16"`
	InterventionScore int    `json:"intervention_score"`
	PassiveScore      int    `json:"passive_score"`
	Seen              int    `json:"seen"`
	TrainingSeen      int    `json:"training_seen"`
	Work              int    `json:"work"`
	UniqueCues        int    `json:"unique_cues"`
	ActionsSHA256     string `json:"actions_sha256"`
	PredictionsSHA256 string `json:"predictions_sha256"`
	CheckpointSHA256  string `json:"checkpoint_sha256"`
	TerminalSHA256    string `json:"terminal_sha256"`
	ColdMatches       bool   `json:"cold_matches"`
}

func f27TrialRun(model f27Model, seed uint32, schedule string, cold bool) (F27Trial, []byte, error) {
	if model.TrainingSeen != F27TrainingSteps || model.TransferSeen != 0 {
		return F27Trial{}, nil, errF27
	}
	trained, e := f27Save(model)
	if e != nil {
		return F27Trial{}, nil, e
	}
	if cold {
		model, e = f27Load(trained)
		if e != nil {
			return F27Trial{}, nil, e
		}
	}
	if model.Mode == "cold-zero" {
		model.resetTrainingForAblation()
	}
	world, e := f27NewWorld(seed, schedule)
	if e != nil {
		return F27Trial{}, nil, e
	}
	if e = model.beginWorld(world.Sensors); e != nil {
		return F27Trial{}, nil, e
	}
	trial := F27Trial{Kind: model.Mode, TrainingSeen: model.TrainingSeen, CheckpointSHA256: f27Hash(trained), ColdMatches: true}
	seenCue := [4]bool{}
	actions := make([]int, 0, F27TransferSteps)
	preds := make([]int, 0, F27TransferSteps)
	for t := 0; t < F27TransferSteps; t++ {
		c, e := f27Cue(seed, schedule, t)
		if e != nil {
			return F27Trial{}, nil, e
		}
		a := f27Action(t)
		seenCue[c] = true
		actions = append(actions, a)
		prob, e := model.forecast(c, a)
		if e != nil {
			return F27Trial{}, nil, e
		}
		pred := f27ArgMax(prob)
		preds = append(preds, pred)
		actual, next, e := world.step(t, c, a)
		if e != nil {
			return F27Trial{}, nil, e
		}
		if pred == actual {
			trial.Score++
			switch {
			case t < 16:
				trial.First16++
			case t < 32:
				trial.Middle16++
			default:
				trial.Last16++
			}
			if a == 1 {
				trial.InterventionScore++
			} else {
				trial.PassiveScore++
			}
		}
		if e = model.observe(c, a, next, false); e != nil {
			return F27Trial{}, nil, e
		}
	}
	for _, b := range seenCue {
		if b {
			trial.UniqueCues++
		}
	}
	trial.Seen = model.TransferSeen
	trial.Work = model.Work
	rawAct, _ := json.Marshal(actions)
	rawPred, _ := json.Marshal(preds)
	trial.ActionsSHA256 = f27Hash(rawAct)
	trial.PredictionsSHA256 = f27Hash(rawPred)
	terminal, e := f27Save(model)
	if e != nil {
		return F27Trial{}, nil, e
	}
	trial.TerminalSHA256 = f27Hash(terminal)
	return trial, terminal, nil
}
func f27Training(kind string) (f27Model, error) {
	model, e := f27New(kind)
	if e != nil {
		return model, e
	}
	for _, x := range [2]struct {
		Seed     uint32
		Schedule string
		Steps    int
	}{{211, "balanced", 64}, {223, "skewed", 64}} {
		world, e := f27NewWorld(x.Seed, x.Schedule)
		if e != nil {
			return f27Model{}, e
		}
		if e = model.beginWorld(world.Sensors); e != nil {
			return f27Model{}, e
		}
		for t := 0; t < x.Steps; t++ {
			c, e := f27Cue(x.Seed, x.Schedule, t)
			if e != nil {
				return f27Model{}, e
			}
			a := f27Action(t)
			if _, e = model.forecast(c, a); e != nil {
				return f27Model{}, e
			}
			_, next, e := world.step(t, c, a)
			if e != nil {
				return f27Model{}, e
			}
			if e = model.observe(c, a, next, true); e != nil {
				return f27Model{}, e
			}
		}
	}
	return model, nil
}

type F27Arm struct {
	Seed                  uint32      `json:"seed"`
	Schedule              string      `json:"schedule"`
	Trials                [6]F27Trial `json:"trials"`
	BestConventional      int         `json:"best_conventional"`
	BestConventionalEarly int         `json:"best_conventional_early"`
	GainStrong            int         `json:"gain_strong"`
	GainActionBlind       int         `json:"gain_action_blind"`
	GainColdZero          int         `json:"gain_cold_zero"`
	Passes                bool        `json:"passes"`
}
type F27Report struct {
	Schema                    string    `json:"schema"`
	Parent                    string    `json:"parent"`
	TrainingWorlds            [2]uint32 `json:"training_worlds"`
	TransferWorlds            [4]uint32 `json:"transfer_worlds"`
	TrainingTransitions       int       `json:"training_transitions"`
	TransferTransitions       int       `json:"transfer_transitions"`
	MinimumGain               int       `json:"minimum_gain"`
	MinimumAblationGain       int       `json:"minimum_ablation_gain"`
	MinimumEarlyGain          int       `json:"minimum_early_gain"`
	Arms                      [4]F27Arm `json:"arms"`
	Passing                   int       `json:"passing"`
	Classification            string    `json:"classification"`
	DevelopmentOnly           bool      `json:"development_only"`
	EarlierNegativesPreserved bool      `json:"earlier_negatives_preserved"`
	FirstUseConsumed          bool      `json:"first_use_consumed"`
	ScientificAccepted        bool      `json:"scientific_accepted"`
	OwnerEligible             bool      `json:"owner_eligible"`
	DispatchAuthorized        bool      `json:"dispatch_authorized"`
	WholeProcessCostProven    bool      `json:"whole_process_cost_proven"`
	MatchedComputeProven      bool      `json:"matched_compute_proven"`
	DigestSHA256              string    `json:"digest_sha256"`
}

func f27Digest(r F27Report) string {
	r.DigestSHA256 = ""
	raw, _ := json.Marshal(r)
	return f27Hash(raw)
}
func F27Development() (F27Report, error) {
	r := F27Report{Schema: F27Schema, Parent: F27Parent, TrainingWorlds: [2]uint32{211, 223}, TransferWorlds: [4]uint32{227, 229, 233, 239}, TrainingTransitions: F27TrainingSteps, TransferTransitions: F27TransferSteps, MinimumGain: 3, MinimumAblationGain: 5, MinimumEarlyGain: 1, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	worlds := f27TransferWorlds()
	trained := [6]f27Model{}
	for j, kind := range f27Kinds() {
		m, e := f27Training(kind)
		if e != nil {
			return F27Report{}, e
		}
		trained[j] = m
	}
	for i, w := range worlds {
		arm := F27Arm{Seed: w.Seed, Schedule: w.Schedule}
		for j, kind := range f27Kinds() {
			cold, cb, e := f27TrialRun(trained[j], w.Seed, w.Schedule, true)
			if e != nil {
				return F27Report{}, e
			}
			warm, wb, e := f27TrialRun(trained[j], w.Seed, w.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) || cold.Kind != kind {
				return F27Report{}, errF27
			}
			arm.Trials[j] = cold
		}
		refAction := arm.Trials[0].ActionsSHA256
		best, bestEarly := -1, -1
		for j, x := range arm.Trials {
			if x.ActionsSHA256 != refAction {
				return F27Report{}, errF27
			}
			if j >= 1 && j <= 3 {
				if x.Score > best {
					best = x.Score
				}
				if x.First16 > bestEarly {
					bestEarly = x.First16
				}
			}
		}
		arm.BestConventional = best
		arm.BestConventionalEarly = bestEarly
		arm.GainStrong = arm.Trials[0].Score - best
		arm.GainActionBlind = arm.Trials[0].Score - arm.Trials[4].Score
		arm.GainColdZero = arm.Trials[0].Score - arm.Trials[5].Score
		arm.Passes = arm.GainStrong >= 3 && arm.GainActionBlind >= 5 && arm.GainColdZero >= 5 && arm.Trials[0].First16 >= bestEarly+1
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F27NoGo
	if r.Passing == 4 {
		r.Classification = F27Signal
	}
	r.DigestSHA256 = f27Digest(r)
	return r, nil
}
func F27Validate(r F27Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f27Digest(r) || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		return errF27
	}
	expected, e := F27Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF27
	}
	return nil
}
