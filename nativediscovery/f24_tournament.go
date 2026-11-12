// Eureka F24: frozen source-blind, budgeted causal intervention tournament.
// Synthetic development only. No owner, first-use, controller or deployment hooks.
package nativediscovery

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"reflect"
	"time"
)

const (
	F24Schema    = "forge.native-discovery.causal-intervention-tournament.dev.v1"
	F24NoGo      = "F24_DEV_NO_GO"
	F24Signal    = "F24_DEV_SIGNAL_UNVERIFIED"
	F24Actions   = 128
	F24Budget    = 12
	F24F23Parent = "abaf92fb3c72ebc72ebc0e0a200c3b5c0213096c"
)

var errF24 = errors.New("FORGE_EUREKA_F24_SOURCE_OR_AUTHORITY_INVALID")

func f24Kinds() [9]string {
	return [9]string{"tournament", "bayes-ig", "bayes-error", "two-window", "thompson", "periodic", "random", "no-intervention", "wrong-credit"}
}
func f24Seeds() [2]uint32     { return [2]uint32{163, 167} }
func f24Schedules() [2]string { return [2]string{"balanced", "skewed"} }
func f24Laws(seed uint32) ([3]int, error) {
	switch seed {
	case 163:
		return [3]int{0xc6, 0x19, 0x72}, nil
	case 167:
		return [3]int{0x5a, 0x87, 0x31}, nil
	}
	return [3]int{}, errF24
}
func f24Cue(seed uint32, schedule string, step int) (int, error) {
	if _, err := f24Laws(seed); err != nil || step < 0 || step >= F24Actions {
		return 0, errF24
	}
	switch schedule {
	case "balanced":
		return int(f12Mix(seed^uint32(step+1)*0x27d4eb2d) & 3), nil
	case "skewed":
		if step%5 == 4 {
			return (step/5 + int(seed%4)) % 4, nil
		}
		return (step/5 + int(seed%2)) % 2, nil
	}
	return 0, errF24
}

// This simulator-only function is never referenced by the action selector.
func f24Observation(seed uint32, step, cue, action int) (int, error) {
	laws, err := f24Laws(seed)
	if err != nil || step < 0 || step >= F24Actions || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, errF24
	}
	law := laws[0]
	if step >= 32 && step < 64 {
		law = laws[1]
	}
	if step >= 64 && step < 96 {
		law = laws[2]
	}
	if f12Mix(seed^0x31415926^uint32(step+1)*0x9e3779b9)%13 == 0 {
		return -1, nil
	}
	result := f20Truth(law, cue, action)
	if f12Mix(seed^0x27182818^uint32(step+1)*0x85ebca6b)%17 == 0 {
		result ^= 1
	}
	return result, nil
}

type f24Factors [4][4]float64

func f24Fit(recs []f20Credit, wrong bool) (f24Factors, int, error) {
	var f f24Factors
	for c := 0; c < 4; c++ {
		for p := 0; p < 4; p++ {
			f[c][p] = .25
		}
	}
	work := 16
	for _, r := range recs {
		if r.Step < 0 || r.Step >= F24Actions || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 || r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
			return f24Factors{}, 0, errF24
		}
		if r.Value < 0 {
			continue
		}
		action := r.Action
		if wrong {
			action = r.WrongAction
		}
		mass := 0.0
		for p := 0; p < 4; p++ {
			bit := (p & 1) ^ (action & ((p >> 1) & 1))
			if bit == r.Value {
				f[r.Cue][p] *= 8
			}
			mass += f[r.Cue][p]
			work++
		}
		if mass <= 0 || math.IsNaN(mass) || math.IsInf(mass, 0) {
			return f24Factors{}, 0, errF24
		}
		for p := 0; p < 4; p++ {
			f[r.Cue][p] /= mass
		}
	}
	return f, work, nil
}
func f24P(f f24Factors, cue, action int) float64 {
	p := 0.0
	for pair, v := range f[cue] {
		if ((pair & 1) ^ (action & ((pair >> 1) & 1))) == 1 {
			p += v
		}
	}
	return p
}
func f24Recent(r []f20Credit, n int) []f20Credit {
	if len(r) > n {
		return r[len(r)-n:]
	}
	return r
}
func f24Entropy(p float64) float64 {
	if p <= 0 || p >= 1 {
		return 0
	}
	return -p*math.Log2(p) - (1-p)*math.Log2(1-p)
}
func f24Select(recs []f20Credit, cue, step, spent int, seed uint32, kind string) (int, int, error) {
	if cue < 0 || cue > 3 || step < 0 || step >= F24Actions || spent < 0 || spent > F24Budget {
		return 0, 0, errF24
	}
	// The selector may validate the public arm ID, but must never call the hidden-law generator.
	if seed != 163 && seed != 167 {
		return 0, 0, errF24
	}
	valid := false
	for _, k := range f24Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return 0, 0, errF24
	}
	if spent == F24Budget || kind == "no-intervention" {
		return 0, 1, nil
	}
	switch kind {
	case "periodic":
		if step%10 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	case "random":
		if f12Mix(seed^uint32(step+1)*0x9e3779b9)%9 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	}
	wrong := kind == "wrong-credit"
	recent := f24Recent(recs, 16)
	now, work, err := f24Fit(recent, wrong)
	if err != nil {
		return 0, 0, err
	}
	switch kind {
	case "tournament", "wrong-credit":
		if len(recs) < 24 {
			if step%8 == 0 {
				return 1, work, nil
			}
			return 0, work, nil
		}
		early, w, e := f24Fit(recs[:24], wrong)
		if e != nil {
			return 0, 0, e
		}
		work += w
		advantage := math.Abs(f24P(early, cue, 1)-f24P(now, cue, 1)) - math.Abs(f24P(early, cue, 0)-f24P(now, cue, 0))
		cueSpent := 0
		for _, r := range recent {
			if r.Cue == cue && r.Action == 1 {
				cueSpent++
			}
		}
		if advantage >= .20 && cueSpent < 2 {
			return 1, work, nil
		}
	case "bayes-ig":
		if f24Entropy(f24P(now, cue, 1)) > f24Entropy(f24P(now, cue, 0))+1e-12 {
			return 1, work, nil
		}
	case "bayes-error":
		p0, p1 := f24P(now, cue, 0), f24P(now, cue, 1)
		if math.Min(p1, 1-p1) > math.Min(p0, 1-p0)+1e-12 {
			return 1, work, nil
		}
	case "two-window":
		long, w, e := f24Fit(f24Recent(recs, 24), false)
		if e != nil {
			return 0, 0, e
		}
		work += w
		short, w, e := f24Fit(f24Recent(recs, 8), false)
		if e != nil {
			return 0, 0, e
		}
		work += w
		v := math.Abs(f24P(short, cue, 1)-f24P(long, cue, 1)) - math.Abs(f24P(short, cue, 0)-f24P(long, cue, 0))
		if v >= .20 {
			return 1, work, nil
		}
	case "thompson":
		u := float64(f12Mix(seed^uint32(step+1)*0x165667b1)) / 4294967296.0
		sum := 0.0
		for pair, p := range now[cue] {
			sum += p
			if u < sum || pair == 3 {
				if pair&2 != 0 {
					return 1, work, nil
				}
				break
			}
		}
	}
	return 0, work, nil
}

// Each selected action has one independently evolving credited consequence.
// Scorer-only label access is intentionally outside f24Select/f24Predict.
type f24State struct {
	Seen             int         `json:"seen"`
	Credits          []f20Credit `json:"credits"`
	Pending          []f20Probe  `json:"pending"`
	Actions          []int       `json:"actions"`
	Spent            int         `json:"spent"`
	Work             int         `json:"work"`
	ScoreTrace       string      `json:"score_trace"`
	CheckpointScores [4]int      `json:"checkpoint_scores"`
}

func f24ValidState(s f24State) bool {
	if s.Seen < 0 || s.Seen > F24Actions || len(s.Credits) != max(0, s.Seen-2) || len(s.Pending) != min(2, s.Seen) || len(s.Actions) != s.Seen || s.Spent < 0 || s.Spent > F24Budget || s.Work < 0 {
		return false
	}
	used := 0
	for _, a := range s.Actions {
		if a < 0 || a > 1 {
			return false
		}
		used += a
	}
	if used != s.Spent {
		return false
	}
	for i, r := range s.Credits {
		if r.Step != i || r.Action != s.Actions[i] || r.WrongAction != 1-r.Action || r.Cue < 0 || r.Cue > 3 || r.Value < -1 || r.Value > 1 {
			return false
		}
	}
	for j, p := range s.Pending {
		i := s.Seen - len(s.Pending) + j
		if p.Step != i || p.Action != s.Actions[i] || p.WrongAction != 1-p.Action || p.Cue < 0 || p.Cue > 3 {
			return false
		}
	}
	if len(s.ScoreTrace) != 8*min(4, max(0, (s.Seen-89)/8)) {
		return false
	}
	return true
}
func f24Save(s f24State) ([]byte, error) {
	if !f24ValidState(s) {
		return nil, errF24
	}
	return json.Marshal(s)
}
func f24Load(raw []byte) (f24State, error) {
	var s f24State
	if json.Unmarshal(raw, &s) != nil || !f24ValidState(s) {
		return f24State{}, errF24
	}
	canonical, e := json.Marshal(s)
	if e != nil || !bytes.Equal(canonical, raw) {
		return f24State{}, errF24
	}
	return s, nil
}
func f24Hash(raw []byte) string { v := sha256.Sum256(raw); return hex.EncodeToString(v[:]) }
func f24Predict(recs []f20Credit, cue, action int) (int, int, error) {
	if cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, 0, errF24
	}
	f, w, e := f24Fit(f24Recent(recs, 16), false)
	if e != nil {
		return 0, 0, e
	}
	if f24P(f, cue, action) > .5 {
		return 1, w + 4, nil
	}
	return 0, w + 4, nil
}
func f24Score(s *f24State, seed uint32, step int) error {
	if step < 96 || step > 120 || (step-96)%8 != 0 || s.Seen != step || len(s.Credits) != step-1 || len(s.Pending) != 1 {
		return errF24
	}
	laws, e := f24Laws(seed)
	if e != nil {
		return e
	}
	pos := (step - 96) / 8
	count := 0
	for cue := 0; cue < 4; cue++ {
		for action := 0; action < 2; action++ {
			predicted, w, err := f24Predict(s.Credits, cue, action)
			if err != nil {
				return err
			}
			s.Work += w
			if predicted == f20Truth(laws[0], cue, action) {
				count++
				s.ScoreTrace += "1"
			} else {
				s.ScoreTrace += "0"
			}
		}
	}
	s.CheckpointScores[pos] = count
	return nil
}
func f24Step(s *f24State, seed uint32, schedule, kind string) error {
	if !f24ValidState(*s) || s.Seen >= F24Actions {
		return errF24
	}
	t := s.Seen
	if t >= 2 {
		p := s.Pending[0]
		v, e := f24Observation(seed, p.Step, p.Cue, p.Action)
		if e != nil {
			return e
		}
		s.Credits = append(s.Credits, f20Credit{Step: p.Step, Cue: p.Cue, Action: p.Action, WrongAction: p.WrongAction, Value: v})
		s.Pending = s.Pending[1:]
	}
	if t >= 96 && t <= 120 && (t-96)%8 == 0 {
		if e := f24Score(s, seed, t); e != nil {
			return e
		}
	}
	cue, e := f24Cue(seed, schedule, t)
	if e != nil {
		return e
	}
	action, w, e := f24Select(s.Credits, cue, t, s.Spent, seed, kind)
	if e != nil {
		return e
	}
	s.Work += w
	s.Spent += action
	s.Actions = append(s.Actions, action)
	s.Pending = append(s.Pending, f20Probe{Step: t, Cue: cue, Action: action, WrongAction: 1 - action})
	s.Seen++
	if !f24ValidState(*s) {
		return errF24
	}
	return nil
}

type F24Trial struct {
	Kind             string `json:"kind"`
	Score            int    `json:"score"`
	Checkpoints      [4]int `json:"checkpoints"`
	Trace            string `json:"trace"`
	ActionsSHA256    string `json:"actions_sha256"`
	CheckpointSHA256 string `json:"checkpoint_sha256"`
	FinalSHA256      string `json:"final_sha256"`
	Spent            int    `json:"spent"`
	Credits          int    `json:"credits"`
	Pending          int    `json:"pending"`
	Work             int    `json:"work"`
	ColdMatches      bool   `json:"cold_matches"`
}

func f24Run(seed uint32, schedule, kind string, cold bool) (F24Trial, []byte, []byte, error) {
	if _, err := f24Laws(seed); err != nil {
		return F24Trial{}, nil, nil, err
	}
	if _, err := f24Cue(seed, schedule, 0); err != nil {
		return F24Trial{}, nil, nil, err
	}
	valid := false
	for _, k := range f24Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return F24Trial{}, nil, nil, errF24
	}
	s := f24State{Credits: []f20Credit{}, Pending: []f20Probe{}, Actions: []int{}}
	for s.Seen < 96 {
		if e := f24Step(&s, seed, schedule, kind); e != nil {
			return F24Trial{}, nil, nil, fmt.Errorf("seed %d %s %s step %d: %w", seed, schedule, kind, s.Seen, e)
		}
	}
	checkpoint, e := f24Save(s)
	if e != nil {
		return F24Trial{}, nil, nil, e
	}
	if cold {
		s, e = f24Load(checkpoint)
		if e != nil {
			return F24Trial{}, nil, nil, e
		}
	}
	for s.Seen < 128 {
		if e := f24Step(&s, seed, schedule, kind); e != nil {
			return F24Trial{}, nil, nil, fmt.Errorf("seed %d %s %s step %d: %w", seed, schedule, kind, s.Seen, e)
		}
	}
	raw, e := f24Save(s)
	if e != nil {
		return F24Trial{}, nil, nil, e
	}
	actionsRaw, _ := json.Marshal(s.Actions)
	score := 0
	for _, v := range s.CheckpointScores {
		score += v
	}
	return F24Trial{Kind: kind, Score: score, Checkpoints: s.CheckpointScores, Trace: s.ScoreTrace,
		ActionsSHA256: f24Hash(actionsRaw), CheckpointSHA256: f24Hash(checkpoint), FinalSHA256: f24Hash(raw),
		Spent: s.Spent, Credits: len(s.Credits), Pending: len(s.Pending), Work: s.Work, ColdMatches: true}, checkpoint, raw, nil
}

type F24Arm struct {
	Seed               uint32      `json:"seed"`
	Schedule           string      `json:"schedule"`
	Trials             [9]F24Trial `json:"trials"`
	BestConventional   int         `json:"best_conventional"`
	GainStrong         int         `json:"gain_strong"`
	GainNoIntervention int         `json:"gain_no_intervention"`
	GainWrongCredit    int         `json:"gain_wrong_credit"`
	Passes             bool        `json:"passes"`
}
type F24Report struct {
	Schema                    string    `json:"schema"`
	Parent                    string    `json:"parent"`
	Seeds                     [2]uint32 `json:"seeds"`
	Schedules                 [2]string `json:"schedules"`
	Actions                   int       `json:"actions"`
	Budget                    int       `json:"budget"`
	Checkpoints               [4]int    `json:"checkpoints"`
	MinimumGain               int       `json:"minimum_gain"`
	MinimumAblationGain       int       `json:"minimum_ablation_gain"`
	Arms                      [4]F24Arm `json:"arms"`
	Passing                   int       `json:"passing"`
	Classification            string    `json:"classification"`
	EarlierNegativesPreserved bool      `json:"earlier_negatives_preserved"`
	DevelopmentOnly           bool      `json:"development_only"`
	FirstUseConsumed          bool      `json:"first_use_consumed"`
	ScientificAccepted        bool      `json:"scientific_accepted"`
	OwnerEligible             bool      `json:"owner_eligible"`
	DispatchAuthorized        bool      `json:"dispatch_authorized"`
	WholeProcessCostProven    bool      `json:"whole_process_cost_proven"`
	DigestSHA256              string    `json:"digest_sha256"`
}

func f24Digest(r F24Report) string {
	r.DigestSHA256 = ""
	raw, _ := json.Marshal(r)
	return f24Hash(raw)
}
func F24Development() (F24Report, error) {
	r := F24Report{Schema: F24Schema, Parent: F24F23Parent, Seeds: f24Seeds(), Schedules: f24Schedules(),
		Actions: 128, Budget: 12, Checkpoints: [4]int{96, 104, 112, 120}, MinimumGain: 2, MinimumAblationGain: 3,
		EarlierNegativesPreserved: true, DevelopmentOnly: true}
	for i := range r.Arms {
		seed, schedule := r.Seeds[i/2], r.Schedules[i%2]
		arm := F24Arm{Seed: seed, Schedule: schedule}
		for k, kind := range f24Kinds() {
			cold, checkpoint, raw, e := f24Run(seed, schedule, kind, true)
			if e != nil {
				return F24Report{}, e
			}
			warm, warmCheckpoint, warmRaw, e := f24Run(seed, schedule, kind, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(checkpoint, warmCheckpoint) || !bytes.Equal(raw, warmRaw) {
				return F24Report{}, errF24
			}
			arm.Trials[k] = cold
		}
		best := -1
		for k := 1; k <= 6; k++ {
			if arm.Trials[k].Score > best {
				best = arm.Trials[k].Score
			}
		}
		arm.BestConventional = best
		arm.GainStrong = arm.Trials[0].Score - best
		arm.GainNoIntervention = arm.Trials[0].Score - arm.Trials[7].Score
		arm.GainWrongCredit = arm.Trials[0].Score - arm.Trials[8].Score
		arm.Passes = arm.GainStrong >= 2 && arm.GainNoIntervention >= 3 && arm.GainWrongCredit >= 3 && arm.Trials[0].Spent >= 2 && arm.Trials[0].Spent <= 12
		if arm.Passes {
			r.Passing++
		}
		r.Arms[i] = arm
	}
	r.Classification = F24NoGo
	if r.Passing == 4 {
		r.Classification = F24Signal
	}
	r.DigestSHA256 = f24Digest(r)
	return r, nil
}

// Rehashing a tampered report cannot turn development into scientific admission.
func F24Validate(r F24Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f24Digest(r) || r.FirstUseConsumed || r.ScientificAccepted ||
		r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		return errF24
	}
	expected, e := F24Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF24
	}
	return nil
}

// Expose bounded runtime diagnostics explicitly as diagnostics rather than scientific efficiency.
func F24DevelopmentTimed() (F24Report, time.Duration, error) {
	start := time.Now()
	r, e := F24Development()
	return r, time.Since(start), e
}
