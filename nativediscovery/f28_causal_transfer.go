// F28: incremental causal-law archive retrieval after interference and new-law composition.
// Development-only evidence; no owner, execution, scientific first-use or deployment hooks.
package nativediscovery

import (
	"bytes"
	"encoding/json"
	"errors"
	"math"
	"reflect"
)

const (
	F28Schema        = "forge.native-discovery.causal-law-transfer.dev.v1"
	F28NoGo          = "F28_DEV_NO_GO"
	F28Signal        = "F28_DEV_SIGNAL_UNVERIFIED"
	F28Parent        = "1da019c46ed1ed8a1b4a9e61784614b1df1ceb7f"
	F28TrainSteps    = 128
	F28TransferSteps = 48
)

var errF28 = errors.New("FORGE_EUREKA_F28_SOURCE_OR_AUTHORITY_INVALID")

func f28Kinds() [8]string {
	return [8]string{"contradiction-archive", "factorized-bayes", "switch-bayes", "stationary-delta", "markov-bayes", "online-softmax", "overwrite-memory", "wrong-action"}
}
func f28Known(seed uint32) bool {
	switch seed {
	case 241, 243, 251, 257, 263, 269:
		return true
	}
	return false
}
func f28Training(seed uint32) bool { return seed == 241 || seed == 243 }
func f28SeedWorlds() [4]struct {
	Seed     uint32
	Schedule string
} {
	return [4]struct {
		Seed     uint32
		Schedule string
	}{{251, "balanced"}, {257, "skewed"}, {263, "balanced"}, {269, "skewed"}}
}
func f28Cue(seed uint32, schedule string, t int) (int, error) {
	if !f28Known(seed) || t < 0 || t >= 64 || (!f28Training(seed) && t >= F28TransferSteps) {
		return 0, errF28
	}
	switch schedule {
	case "balanced":
		return int(f27Mix(seed^uint32(t+1)*0x27d4eb2d) & 3), nil
	case "skewed":
		if t%5 == 4 {
			return (t/5 + int(seed%4)) % 4, nil
		}
		return (t/5 + int(seed%2)) % 2, nil
	}
	return 0, errF28
}
func f28Action(seed uint32, t int) (int, error) {
	if !f28Known(seed) || t < 0 || t >= 64 || (!f28Training(seed) && t >= F28TransferSteps) {
		return 0, errF28
	}
	return int(f27Mix(seed^uint32(t+1)*0x165667b1) & 1), nil
}
func f28Sensor(seed uint32, t, clean, sensor int) (int, error) {
	if !f28Known(seed) || t < 0 || t > 64 || clean < 0 || clean > 3 || sensor < 0 || sensor > 1 {
		return 0, errF28
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

// Hidden laws and phase are simulator-only. No model method calls f28Law.
func f28Law(law byte, cue int) (int, int, error) {
	if cue < 0 || cue > 3 {
		return 0, 0, errF28
	}
	aBase := [4]int{1, 0, 3, 2}
	aEffect := [4]int{2, 1, 2, 3}
	bBase := [4]int{2, 3, 1, 0}
	bEffect := [4]int{1, 2, 3, 1}
	switch law {
	case 'A':
		return aBase[cue], aEffect[cue], nil
	case 'B':
		return bBase[cue], bEffect[cue], nil
	case 'C':
		if cue%2 == 0 {
			return aBase[cue], bEffect[cue], nil
		}
		return bBase[cue], aEffect[cue], nil
	case 'D':
		if cue%2 == 0 {
			return bBase[cue], aEffect[cue], nil
		}
		return aBase[cue], bEffect[cue], nil
	}
	return 0, 0, errF28
}
func f28Phase(seed uint32, t int) (byte, error) {
	if !f28Known(seed) || t < 0 || t >= 64 || (!f28Training(seed) && t >= 48) {
		return 0, errF28
	}
	if seed == 241 {
		return 'A', nil
	}
	if seed == 243 {
		return 'B', nil
	}
	even := seed == 251 || seed == 263
	switch t / 12 {
	case 0, 2:
		if even {
			return 'A', nil
		}
		return 'B', nil
	case 1:
		if even {
			return 'B', nil
		}
		return 'A', nil
	case 3:
		if seed == 251 || seed == 269 {
			return 'C', nil
		}
		return 'D', nil
	}
	return 0, errF28
}

type f28World struct {
	Seed            uint32
	Schedule        string
	S, Offset, Seen int
	Sensors         [2]int
}

func f28NewWorld(seed uint32, schedule string) (f28World, error) {
	if _, e := f28Cue(seed, schedule, 0); e != nil {
		return f28World{}, e
	}
	w := f28World{Seed: seed, Schedule: schedule, S: int(f27Mix(seed^0x4cf5ad43) & 3), Offset: int(f27Mix(seed^0x6d2b79f5) & 3)}
	for i := 0; i < 2; i++ {
		x, e := f28Sensor(seed, 0, w.clean(), i)
		if e != nil {
			return f28World{}, e
		}
		w.Sensors[i] = x
	}
	return w, nil
}
func (w *f28World) clean() int { return (w.S + w.Offset) % 4 }
func (w *f28World) step(t, cue, action int) (int, [2]int, error) {
	if t != w.Seen || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, [2]int{}, errF28
	}
	phase, e := f28Phase(w.Seed, t)
	if e != nil {
		return 0, [2]int{}, e
	}
	base, effect, e := f28Law(phase, cue)
	if e != nil {
		return 0, [2]int{}, e
	}
	w.S = (w.S + base + action*effect) % 4
	w.Seen++
	clean := w.clean()
	var next [2]int
	for i := 0; i < 2; i++ {
		x, e := f28Sensor(w.Seed, w.Seen, clean, i)
		if e != nil {
			return 0, [2]int{}, e
		}
		next[i] = x
	}
	w.Sensors = next
	return clean, next, nil
}

// Pairwise posterior over actual transition deltas derived from *sensor evidence only*.
func f28ObservedDelta(prev, next [2]int) ([4]float64, error) {
	var out [4]float64
	old, e := f27Posterior(prev)
	if e != nil {
		return out, errF28
	}
	current, e := f27Posterior(next)
	if e != nil {
		return out, errF28
	}
	for a := 0; a < 4; a++ {
		for b := 0; b < 4; b++ {
			out[(b-a+4)%4] += old[a] * current[b]
		}
	}
	return out, nil
}
func f28DeltaProb(bank [4][2][4]float64, cue, action int) [4]float64 {
	var out [4]float64
	denom := 4.0
	for d := 0; d < 4; d++ {
		denom += bank[cue][action][d]
	}
	for d := 0; d < 4; d++ {
		out[d] = (bank[cue][action][d] + 1) / denom
	}
	return out
}
func f28Agreement(evidence, q [4]float64) float64 {
	z := 0.0
	for i := 0; i < 4; i++ {
		z += evidence[i] * q[i]
	}
	return math.Max(z, 1e-12)
}
func f28ArchiveMode(kind string) bool {
	return kind == "contradiction-archive" || kind == "factorized-bayes" || kind == "switch-bayes" || kind == "overwrite-memory" || kind == "wrong-action"
}
func f28BaseMode(kind string) string {
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

type f28Model struct {
	Kind         string             `json:"kind"`
	A            [4][2][4]float64   `json:"archive_a"`
	B            [4][2][4]float64   `json:"archive_b"`
	Scratch      [4][2][4]float64   `json:"scratch"`
	Recent       [4][2][][4]float64 `json:"recent"`
	Factor       [4][2][3]float64   `json:"factor_weights"`
	Global       [3]float64         `json:"global_weights"`
	Base         f27Model           `json:"base"`
	Prev         [2]int             `json:"previous"`
	HasWorld     bool               `json:"has_world"`
	TrainingSeen int                `json:"training_seen"`
	TransferSeen int                `json:"transfer_seen"`
	Work         int                `json:"work"`
}

func f28New(kind string) (f28Model, error) {
	ok := false
	for _, k := range f28Kinds() {
		if k == kind {
			ok = true
		}
	}
	if !ok {
		return f28Model{}, errF28
	}
	m := f28Model{Kind: kind}
	if k := f28BaseMode(kind); k != "" {
		b, e := f27New(k)
		if e != nil {
			return f28Model{}, e
		}
		m.Base = b
	}
	return m, nil
}
func (m *f28Model) beginWorld(obs [2]int) error {
	if _, e := f27Posterior(obs); e != nil {
		return errF28
	}
	m.Prev = obs
	m.HasWorld = true
	m.Recent = [4][2][][4]float64{}
	for c := 0; c < 4; c++ {
		for a := 0; a < 2; a++ {
			m.Factor[c][a] = [3]float64{1.0 / 3, 1.0 / 3, 1.0 / 3}
		}
	}
	m.Global = [3]float64{1.0 / 3, 1.0 / 3, 1.0 / 3}
	if f28BaseMode(m.Kind) != "" {
		return m.Base.beginWorld(obs)
	}
	return nil
}
func (m *f28Model) bankSelection(c, a int) [4]float64 {
	qa := f28DeltaProb(m.A, c, a)
	qb := f28DeltaProb(m.B, c, a)
	qs := f28DeltaProb(m.Scratch, c, a)
	var out [4]float64
	switch m.Kind {
	case "factorized-bayes":
		weights := m.Factor[c][a]
		for d := 0; d < 4; d++ {
			out[d] = qa[d]*weights[0] + qb[d]*weights[1] + qs[d]*weights[2]
		}
	case "switch-bayes":
		weights := m.Global
		for d := 0; d < 4; d++ {
			out[d] = qa[d]*weights[0] + qb[d]*weights[1] + qs[d]*weights[2]
		}
	default:
		recent := m.Recent[c][a]
		loga, logb := 0.0, 0.0
		for _, e := range recent {
			loga += math.Log(f28Agreement(e, qa))
			logb += math.Log(f28Agreement(e, qb))
		}
		// Novelty detection uses credited evidence, never hidden phase or truth.
		if len(recent) >= 2 && math.Exp(loga/float64(len(recent))) < .22 && math.Exp(logb/float64(len(recent))) < .22 {
			return qs
		}
		if loga-logb > .30 {
			return qa
		}
		if logb-loga > .30 {
			return qb
		}
		for d := 0; d < 4; d++ {
			out[d] = (qa[d] + qb[d]) / 2
		}
	}
	return out
}
func (m *f28Model) forecast(c, a int) ([4]float64, error) {
	var p [4]float64
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return p, errF28
	}
	if f28BaseMode(m.Kind) != "" {
		return m.Base.forecast(c, a)
	}
	state, e := f27Posterior(m.Prev)
	if e != nil {
		return p, errF28
	}
	delta := m.bankSelection(c, a)
	for s := 0; s < 4; s++ {
		for d := 0; d < 4; d++ {
			p[(s+d)%4] += state[s] * delta[d]
		}
	}
	m.Work += 48
	return p, nil
}
func (m *f28Model) observe(c, a int, next [2]int, training, trainA bool) error {
	if !m.HasWorld || c < 0 || c > 3 || a < 0 || a > 1 {
		return errF28
	}
	if f28BaseMode(m.Kind) != "" {
		if e := m.Base.observe(c, a, next, training); e != nil {
			return e
		}
	} else {
		ev, e := f28ObservedDelta(m.Prev, next)
		if e != nil {
			return e
		}
		creditedAction := a
		if m.Kind == "wrong-action" {
			creditedAction = 1 - a
		}
		if training {
			dest := &m.B
			if trainA {
				dest = &m.A
			}
			for d := 0; d < 4; d++ {
				dest[c][creditedAction][d] += ev[d]
			}
		} else {
			if m.Kind == "factorized-bayes" {
				w := m.Factor[c][creditedAction]
				q := [3][4]float64{f28DeltaProb(m.A, c, creditedAction), f28DeltaProb(m.B, c, creditedAction), f28DeltaProb(m.Scratch, c, creditedAction)}
				z := 0.0
				for k := 0; k < 3; k++ {
					w[k] *= f28Agreement(ev, q[k])
					z += w[k]
				}
				if z <= 0 {
					return errF28
				}
				for k := 0; k < 3; k++ {
					w[k] /= z
				}
				m.Factor[c][creditedAction] = w
			} else if m.Kind == "switch-bayes" {
				w := m.Global
				q := [3][4]float64{f28DeltaProb(m.A, c, creditedAction), f28DeltaProb(m.B, c, creditedAction), f28DeltaProb(m.Scratch, c, creditedAction)}
				z := 0.0
				for k := 0; k < 3; k++ {
					w[k] = (.92*w[k] + .08/3) * f28Agreement(ev, q[k])
					z += w[k]
				}
				if z <= 0 {
					return errF28
				}
				for k := 0; k < 3; k++ {
					w[k] /= z
				}
				m.Global = w
			}
			for d := 0; d < 4; d++ {
				m.Scratch[c][creditedAction][d] += ev[d]
			}
			x := append(m.Recent[c][creditedAction], ev)
			if len(x) > 3 {
				x = x[len(x)-3:]
			}
			m.Recent[c][creditedAction] = x
		}
		m.Work += 64
	}
	m.Prev = next
	if training {
		m.TrainingSeen++
	} else {
		m.TransferSeen++
	}
	return nil
}
func f28Finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v, 0) && v >= 0 }
func f28Valid(m f28Model) bool {
	ok := false
	for _, k := range f28Kinds() {
		if k == m.Kind {
			ok = true
		}
	}
	if !ok || m.Work < 0 || m.TrainingSeen < 0 || m.TrainingSeen > F28TrainSteps || m.TransferSeen < 0 || m.TransferSeen > F28TransferSteps {
		return false
	}
	if f28BaseMode(m.Kind) != "" && !f27Valid(m.Base) {
		return false
	}
	for _, v := range m.Prev {
		if v < 0 || v > 3 {
			return false
		}
	}
	for c := 0; c < 4; c++ {
		for a := 0; a < 2; a++ {
			if len(m.Recent[c][a]) > 3 {
				return false
			}
			for _, r := range m.Recent[c][a] {
				for _, v := range r {
					if !f28Finite(v) || v > 1 {
						return false
					}
				}
			}
			for d := 0; d < 4; d++ {
				if !f28Finite(m.A[c][a][d]) || !f28Finite(m.B[c][a][d]) || !f28Finite(m.Scratch[c][a][d]) {
					return false
				}
			}
			for k := 0; k < 3; k++ {
				if !f28Finite(m.Factor[c][a][k]) {
					return false
				}
			}
		}
	}
	for _, v := range m.Global {
		if !f28Finite(v) {
			return false
		}
	}
	return true
}
func f28Save(m f28Model) ([]byte, error) {
	if !f28Valid(m) {
		return nil, errF28
	}
	return json.Marshal(m)
}
func f28Load(raw []byte) (f28Model, error) {
	var m f28Model
	if json.Unmarshal(raw, &m) != nil || !f28Valid(m) {
		return f28Model{}, errF28
	}
	canon, e := json.Marshal(m)
	if e != nil || !bytes.Equal(raw, canon) {
		return f28Model{}, errF28
	}
	return m, nil
}
func f28Train(kind string) (f28Model, error) {
	m, e := f28New(kind)
	if e != nil {
		return m, e
	}
	for _, item := range []struct {
		seed     uint32
		schedule string
		phaseA   bool
	}{{241, "balanced", true}, {243, "skewed", false}} {
		w, e := f28NewWorld(item.seed, item.schedule)
		if e != nil {
			return f28Model{}, e
		}
		if e = m.beginWorld(w.Sensors); e != nil {
			return f28Model{}, e
		}
		for t := 0; t < 64; t++ {
			c, e := f28Cue(item.seed, item.schedule, t)
			if e != nil {
				return f28Model{}, e
			}
			a, e := f28Action(item.seed, t)
			if e != nil {
				return f28Model{}, e
			}
			if _, e = m.forecast(c, a); e != nil {
				return f28Model{}, e
			}
			_, next, e := w.step(t, c, a)
			if e != nil {
				return f28Model{}, e
			}
			if e = m.observe(c, a, next, true, item.phaseA); e != nil {
				return f28Model{}, e
			}
		}
	}
	if m.Kind == "overwrite-memory" {
		m.A = m.B
	}
	if m.TrainingSeen != 128 {
		return f28Model{}, errF28
	}
	return m, nil
}

type F28Trial struct {
	Kind              string  `json:"kind"`
	MeanNLL           float64 `json:"mean_nll"`
	Accuracy          int     `json:"accuracy"`
	PhaseAccuracy     [4]int  `json:"phase_accuracy"`
	FirstAfterSwitch  [3]int  `json:"first_after_switch"`
	TrainingSeen      int     `json:"training_seen"`
	TransferSeen      int     `json:"transfer_seen"`
	Work              int     `json:"work"`
	Parameters        int     `json:"parameter_count"`
	ActionsSHA256     string  `json:"actions_sha256"`
	SensorsSHA256     string  `json:"sensors_sha256"`
	PredictionsSHA256 string  `json:"predictions_sha256"`
	CheckpointSHA256  string  `json:"checkpoint_sha256"`
	TerminalSHA256    string  `json:"terminal_sha256"`
	ColdMatches       bool    `json:"cold_matches"`
}

func f28ParameterCount(kind string) int {
	switch kind {
	case "stationary-delta":
		return 32
	case "markov-bayes":
		return 128
	case "online-softmax":
		return 72
	}
	return 96 + 96 + 24 + 3
}
func f28Trial(trained f28Model, seed uint32, sched string, cold bool) (F28Trial, []byte, error) {
	if trained.TrainingSeen != F28TrainSteps || trained.TransferSeen != 0 {
		return F28Trial{}, nil, errF28
	}
	checkpoint, e := f28Save(trained)
	if e != nil {
		return F28Trial{}, nil, e
	}
	m := trained
	if cold {
		m, e = f28Load(checkpoint)
		if e != nil {
			return F28Trial{}, nil, e
		}
	}
	w, e := f28NewWorld(seed, sched)
	if e != nil {
		return F28Trial{}, nil, e
	}
	if e = m.beginWorld(w.Sensors); e != nil {
		return F28Trial{}, nil, e
	}
	startWork := m.Work
	tr := F28Trial{Kind: m.Kind, TrainingSeen: m.TrainingSeen, Parameters: f28ParameterCount(m.Kind), CheckpointSHA256: f27Hash(checkpoint), ColdMatches: true}
	acts := make([]int, 0, 48)
	observations := make([][2]int, 0, 49)
	observations = append(observations, w.Sensors)
	forecasts := make([][4]float64, 0, 48)
	totalNLL := 0.0
	for t := 0; t < 48; t++ {
		c, e := f28Cue(seed, sched, t)
		if e != nil {
			return F28Trial{}, nil, e
		}
		a, e := f28Action(seed, t)
		if e != nil {
			return F28Trial{}, nil, e
		}
		acts = append(acts, a)
		p, e := m.forecast(c, a)
		if e != nil {
			return F28Trial{}, nil, e
		}
		forecasts = append(forecasts, p)
		actual, next, e := w.step(t, c, a)
		if e != nil {
			return F28Trial{}, nil, e
		}
		observations = append(observations, next)
		totalNLL -= math.Log(math.Max(p[actual], 1e-9))
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
		if e = m.observe(c, a, next, false, false); e != nil {
			return F28Trial{}, nil, e
		}
	}
	tr.MeanNLL = totalNLL / 48
	tr.TransferSeen = m.TransferSeen
	tr.Work = m.Work - startWork
	if f28BaseMode(m.Kind) != "" {
		tr.Work = m.Base.Work - trained.Base.Work
	}
	ra, _ := json.Marshal(acts)
	ro, _ := json.Marshal(observations)
	rp, _ := json.Marshal(forecasts)
	tr.ActionsSHA256 = f27Hash(ra)
	tr.SensorsSHA256 = f27Hash(ro)
	tr.PredictionsSHA256 = f27Hash(rp)
	terminal, e := f28Save(m)
	if e != nil {
		return F28Trial{}, nil, e
	}
	tr.TerminalSHA256 = f27Hash(terminal)
	return tr, terminal, nil
}

type F28Arm struct {
	Seed                   uint32      `json:"seed"`
	Schedule               string      `json:"schedule"`
	Trials                 [8]F28Trial `json:"trials"`
	BestConventionalNLL    float64     `json:"best_conventional_nll"`
	CandidateGainNLL       float64     `json:"candidate_gain_nll"`
	BestConventionalReturn int         `json:"best_conventional_return"`
	BestConventionalNovel  int         `json:"best_conventional_novel"`
	GainOverwriteNLL       float64     `json:"gain_overwrite_nll"`
	GainWrongActionNLL     float64     `json:"gain_wrong_action_nll"`
	Passes                 bool        `json:"passes"`
}
type F28Report struct {
	Schema                    string    `json:"schema"`
	Parent                    string    `json:"parent"`
	TrainingWorlds            [2]uint32 `json:"training_worlds"`
	TransferWorlds            [4]uint32 `json:"transfer_worlds"`
	TrainingTransitions       int       `json:"training_transitions"`
	TransferTransitions       int       `json:"transfer_transitions"`
	MinNLLGain                float64   `json:"min_nll_gain"`
	MinAblationNLLGain        float64   `json:"min_ablation_nll_gain"`
	MinSegmentGain            int       `json:"min_segment_gain"`
	Arms                      [4]F28Arm `json:"arms"`
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

func f28Digest(r F28Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f27Hash(b) }
func F28Development() (F28Report, error) {
	r := F28Report{Schema: F28Schema, Parent: F28Parent, TrainingWorlds: [2]uint32{241, 243}, TransferWorlds: [4]uint32{251, 257, 263, 269}, TrainingTransitions: F28TrainSteps, TransferTransitions: F28TransferSteps, MinNLLGain: .05, MinAblationNLLGain: .10, MinSegmentGain: 1, DevelopmentOnly: true, EarlierNegativesPreserved: true}
	var trained [8]f28Model
	for j, kind := range f28Kinds() {
		m, e := f28Train(kind)
		if e != nil {
			return F28Report{}, e
		}
		trained[j] = m
	}
	for i, world := range f28SeedWorlds() {
		arm := F28Arm{Seed: world.Seed, Schedule: world.Schedule}
		for j := range f28Kinds() {
			cold, cb, e := f28Trial(trained[j], world.Seed, world.Schedule, true)
			if e != nil {
				return F28Report{}, e
			}
			warm, wb, e := f28Trial(trained[j], world.Seed, world.Schedule, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(cb, wb) {
				return F28Report{}, errF28
			}
			arm.Trials[j] = cold
		}
		refAct, refSensor := arm.Trials[0].ActionsSHA256, arm.Trials[0].SensorsSHA256
		best := math.Inf(1)
		for j, v := range arm.Trials {
			if v.ActionsSHA256 != refAct || v.SensorsSHA256 != refSensor || v.TransferSeen != 48 || v.TrainingSeen != 128 || v.Accuracy < 0 || v.Accuracy > 48 {
				return F28Report{}, errF28
			}
			if j >= 1 && j <= 5 {
				if v.MeanNLL < best {
					best = v.MeanNLL
				}
				if v.PhaseAccuracy[2] > arm.BestConventionalReturn {
					arm.BestConventionalReturn = v.PhaseAccuracy[2]
				}
				if v.PhaseAccuracy[3] > arm.BestConventionalNovel {
					arm.BestConventionalNovel = v.PhaseAccuracy[3]
				}
			}
		}
		arm.BestConventionalNLL = best
		arm.CandidateGainNLL = best - arm.Trials[0].MeanNLL
		arm.GainOverwriteNLL = arm.Trials[6].MeanNLL - arm.Trials[0].MeanNLL
		arm.GainWrongActionNLL = arm.Trials[7].MeanNLL - arm.Trials[0].MeanNLL
		arm.Passes = arm.CandidateGainNLL >= .05 && arm.GainOverwriteNLL >= .10 && arm.GainWrongActionNLL >= .10 && arm.Trials[0].PhaseAccuracy[2] >= arm.BestConventionalReturn+1 && arm.Trials[0].PhaseAccuracy[3] >= arm.BestConventionalNovel+1
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F28NoGo
	if r.Passing == 4 {
		r.Classification = F28Signal
	}
	r.DigestSHA256 = f28Digest(r)
	return r, nil
}
func F28Validate(r F28Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f28Digest(r) || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || r.MatchedComputeProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		return errF28
	}
	expected, e := F28Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF28
	}
	return nil
}
