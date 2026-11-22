// Eureka F25: identify action effects from actually credited interventions.
// Synthetic DEV only; no owner, first-use, workflow or controller integration.
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
	F25Schema  = "forge.native-discovery.causal-identification.dev.v1"
	F25NoGo    = "F25_DEV_NO_GO"
	F25Signal  = "F25_DEV_SIGNAL_UNVERIFIED"
	F25Actions = 96
	F25Budget  = 12
	F25Parent  = "b34ed42f57c7f8cd0acb9559b41f4f0b8219d36b"
)

var errF25 = errors.New("FORGE_EUREKA_F25_SOURCE_OR_AUTHORITY_INVALID")

func f25Seeds() [2]uint32     { return [2]uint32{173, 179} }
func f25Schedules() [2]string { return [2]string{"balanced", "skewed"} }
func f25Kinds() [8]string {
	return [8]string{"causal-pair", "bayes-ig", "bayes-error", "thompson", "periodic", "random", "no-intervention", "wrong-credit"}
}
func f25Known(seed uint32) bool { return seed == 173 || seed == 179 }

// Simulator/scorer-only law: never called from an action selector or predictor.
func f25World(seed uint32) (int, error) {
	switch seed {
	case 173:
		return 0xb6, nil
	case 179:
		return 0xd9, nil
	}
	return 0, errF25
}
func f25Cue(seed uint32, schedule string, step int) (int, error) {
	if !f25Known(seed) || step < 0 || step >= F25Actions {
		return 0, errF25
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
	return 0, errF25
}
func f25Observed(seed uint32, step, cue, action int) (int, error) {
	law, e := f25World(seed)
	if e != nil || step < 0 || step >= F25Actions || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, errF25
	}
	if f12Mix(seed^0x31415926^uint32(step+1)*0x9e3779b9)%13 == 0 {
		return -1, nil
	}
	value := f20Truth(law, cue, action)
	if f12Mix(seed^0x27182818^uint32(step+1)*0x85ebca6b)%17 == 0 {
		value ^= 1
	}
	return value, nil
}
func f25Predict(recs []f20Credit, cue, action int, wrong bool) (int, int, error) {
	if cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, 0, errF25
	}
	p, w, e := f24Fit(recs, wrong)
	if e != nil {
		return 0, 0, e
	}
	if f24P(p, cue, action) > .5 {
		return 1, w + 4, nil
	}
	return 0, w + 4, nil
}
func f25Select(recs []f20Credit, pending []f20Probe, cue, step, spent int, seed uint32, kind string) (int, int, error) {
	if !f25Known(seed) || cue < 0 || cue > 3 || step < 0 || step >= F25Actions || spent < 0 || spent > F25Budget {
		return 0, 0, errF25
	}
	valid := false
	for _, k := range f25Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return 0, 0, errF25
	}
	if spent == F25Budget || kind == "no-intervention" {
		return 0, 1, nil
	}
	switch kind {
	case "periodic":
		if step%8 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	case "random":
		if f12Mix(seed^uint32(step+1)*0x9e3779b9)%8 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	}
	wrong := kind == "wrong-credit"
	p, work, e := f24Fit(recs, wrong)
	if e != nil {
		return 0, 0, e
	}
	p0, p1 := f24P(p, cue, 0), f24P(p, cue, 1)
	switch kind {
	case "causal-pair", "wrong-credit":
		// Prior causal-effect uncertainty, not historic-vs-recent disagreement.
		effect := p[cue][2] + p[cue][3]
		baselineKnown := p0 <= .20 || p0 >= .80
		cueSpent := 0
		for _, r := range recs {
			if r.Cue == cue && r.Action == 1 {
				cueSpent++
			}
		}
		pendingSame := false
		for _, r := range pending {
			if r.Cue == cue && r.Action == 1 {
				pendingSame = true
			}
		}
		if baselineKnown && effect >= .18 && effect <= .82 && cueSpent < 3 && !pendingSame {
			return 1, work, nil
		}
	case "bayes-ig":
		if f24Entropy(p1) > f24Entropy(p0)+1e-12 {
			return 1, work, nil
		}
	case "bayes-error":
		if math.Min(p1, 1-p1) > math.Min(p0, 1-p0)+1e-12 {
			return 1, work, nil
		}
	case "thompson":
		u := float64(f12Mix(seed^uint32(step+1)*0x165667b1)) / 4294967296.0
		s := 0.0
		for pair, q := range p[cue] {
			s += q
			if u < s || pair == 3 {
				if pair&2 != 0 {
					return 1, work, nil
				}
				break
			}
		}
	}
	return 0, work, nil
}

type f25State struct {
	Seen             int         `json:"seen"`
	Credits          []f20Credit `json:"credits"`
	Pending          []f20Probe  `json:"pending"`
	Actions          []int       `json:"actions"`
	Spent            int         `json:"spent"`
	Work             int         `json:"work"`
	ScoreTrace       string      `json:"score_trace"`
	CheckpointScores [4]int      `json:"checkpoint_scores"`
}

func f25ExpectedTrace(seen int) int {
	n := 0
	for _, t := range [4]int{24, 40, 56, 72} {
		if seen > t {
			n += 8
		}
	}
	return n
}
func f25Valid(s f25State) bool {
	if s.Seen < 0 || s.Seen > F25Actions || len(s.Credits) != max(0, s.Seen-2) || len(s.Pending) != min(2, s.Seen) || len(s.Actions) != s.Seen || s.Spent < 0 || s.Spent > F25Budget || s.Work < 0 || len(s.ScoreTrace) != f25ExpectedTrace(s.Seen) {
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
	return true
}
func f25Save(s f25State) ([]byte, error) {
	if !f25Valid(s) {
		return nil, errF25
	}
	return json.Marshal(s)
}
func f25Load(raw []byte) (f25State, error) {
	var s f25State
	if json.Unmarshal(raw, &s) != nil || !f25Valid(s) {
		return f25State{}, errF25
	}
	canonical, e := json.Marshal(s)
	if e != nil || !bytes.Equal(canonical, raw) {
		return f25State{}, errF25
	}
	return s, nil
}
func f25Hash(raw []byte) string { h := sha256.Sum256(raw); return hex.EncodeToString(h[:]) }
func f25Score(s *f25State, seed uint32, step int, wrong bool) error {
	pos := -1
	for i, t := range [4]int{24, 40, 56, 72} {
		if t == step {
			pos = i
		}
	}
	if pos < 0 || s.Seen != step || len(s.Credits) != step-1 || len(s.Pending) != 1 {
		return errF25
	}
	law, e := f25World(seed)
	if e != nil {
		return e
	}
	for cue := 0; cue < 4; cue++ {
		for action := 0; action < 2; action++ {
			pred, w, e := f25Predict(s.Credits, cue, action, wrong)
			if e != nil {
				return e
			}
			s.Work += w
			if pred == f20Truth(law, cue, action) {
				s.CheckpointScores[pos]++
				s.ScoreTrace += "1"
			} else {
				s.ScoreTrace += "0"
			}
		}
	}
	return nil
}
func f25Step(s *f25State, seed uint32, schedule, kind string) error {
	if !f25Valid(*s) || s.Seen >= F25Actions {
		return errF25
	}
	t := s.Seen
	if t >= 2 {
		p := s.Pending[0]
		v, e := f25Observed(seed, p.Step, p.Cue, p.Action)
		if e != nil {
			return e
		}
		s.Credits = append(s.Credits, f20Credit{Step: p.Step, Cue: p.Cue, Action: p.Action, WrongAction: 1 - p.Action, Value: v})
		s.Pending = s.Pending[1:]
	}
	if t == 24 || t == 40 || t == 56 || t == 72 {
		if e := f25Score(s, seed, t, kind == "wrong-credit"); e != nil {
			return e
		}
	}
	cue, e := f25Cue(seed, schedule, t)
	if e != nil {
		return e
	}
	action, w, e := f25Select(s.Credits, s.Pending, cue, t, s.Spent, seed, kind)
	if e != nil {
		return e
	}
	s.Work += w
	s.Spent += action
	s.Actions = append(s.Actions, action)
	s.Pending = append(s.Pending, f20Probe{Step: t, Cue: cue, Action: action, WrongAction: 1 - action})
	s.Seen++
	if !f25Valid(*s) {
		return errF25
	}
	return nil
}

type F25Trial struct {
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

func f25Run(seed uint32, schedule, kind string, cold bool) (F25Trial, []byte, []byte, error) {
	if !f25Known(seed) {
		return F25Trial{}, nil, nil, errF25
	}
	if _, e := f25Cue(seed, schedule, 0); e != nil {
		return F25Trial{}, nil, nil, e
	}
	valid := false
	for _, k := range f25Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return F25Trial{}, nil, nil, errF25
	}
	s := f25State{Credits: []f20Credit{}, Pending: []f20Probe{}, Actions: []int{}}
	for s.Seen < 48 {
		if e := f25Step(&s, seed, schedule, kind); e != nil {
			return F25Trial{}, nil, nil, e
		}
	}
	checkpoint, e := f25Save(s)
	if e != nil {
		return F25Trial{}, nil, nil, e
	}
	if cold {
		s, e = f25Load(checkpoint)
		if e != nil {
			return F25Trial{}, nil, nil, e
		}
	}
	for s.Seen < F25Actions {
		if e := f25Step(&s, seed, schedule, kind); e != nil {
			return F25Trial{}, nil, nil, e
		}
	}
	raw, e := f25Save(s)
	if e != nil {
		return F25Trial{}, nil, nil, e
	}
	actionRaw, _ := json.Marshal(s.Actions)
	score := 0
	for _, v := range s.CheckpointScores {
		score += v
	}
	return F25Trial{Kind: kind, Score: score, Checkpoints: s.CheckpointScores, Trace: s.ScoreTrace, ActionsSHA256: f25Hash(actionRaw), CheckpointSHA256: f25Hash(checkpoint), FinalSHA256: f25Hash(raw), Spent: s.Spent, Credits: len(s.Credits), Pending: len(s.Pending), Work: s.Work, ColdMatches: true}, checkpoint, raw, nil
}

type F25Arm struct {
	Seed               uint32      `json:"seed"`
	Schedule           string      `json:"schedule"`
	Trials             [8]F25Trial `json:"trials"`
	BestConventional   int         `json:"best_conventional"`
	GainStrong         int         `json:"gain_strong"`
	GainNoIntervention int         `json:"gain_no_intervention"`
	GainWrongCredit    int         `json:"gain_wrong_credit"`
	Passes             bool        `json:"passes"`
}
type F25Report struct {
	Schema                    string    `json:"schema"`
	Parent                    string    `json:"parent"`
	Seeds                     [2]uint32 `json:"seeds"`
	Schedules                 [2]string `json:"schedules"`
	Actions                   int       `json:"actions"`
	Budget                    int       `json:"budget"`
	Checkpoints               [4]int    `json:"checkpoints"`
	MinimumGain               int       `json:"minimum_gain"`
	MinimumAblationGain       int       `json:"minimum_ablation_gain"`
	Arms                      [4]F25Arm `json:"arms"`
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

func f25Digest(r F25Report) string {
	r.DigestSHA256 = ""
	raw, _ := json.Marshal(r)
	return f25Hash(raw)
}
func F25Development() (F25Report, error) {
	r := F25Report{Schema: F25Schema, Parent: F25Parent, Seeds: f25Seeds(), Schedules: f25Schedules(), Actions: F25Actions, Budget: F25Budget, Checkpoints: [4]int{24, 40, 56, 72}, MinimumGain: 2, MinimumAblationGain: 3, EarlierNegativesPreserved: true, DevelopmentOnly: true}
	for i := range r.Arms {
		seed, sched := r.Seeds[i/2], r.Schedules[i%2]
		a := F25Arm{Seed: seed, Schedule: sched}
		for j, kind := range f25Kinds() {
			cold, ck, final, e := f25Run(seed, sched, kind, true)
			if e != nil {
				return F25Report{}, e
			}
			warm, wck, wfinal, e := f25Run(seed, sched, kind, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(ck, wck) || !bytes.Equal(final, wfinal) {
				return F25Report{}, errF25
			}
			a.Trials[j] = cold
		}
		best := -1
		for j := 1; j <= 5; j++ {
			if a.Trials[j].Score > best {
				best = a.Trials[j].Score
			}
		}
		a.BestConventional = best
		a.GainStrong = a.Trials[0].Score - best
		a.GainNoIntervention = a.Trials[0].Score - a.Trials[6].Score
		a.GainWrongCredit = a.Trials[0].Score - a.Trials[7].Score
		a.Passes = a.GainStrong >= 2 && a.GainNoIntervention >= 3 && a.GainWrongCredit >= 3 && a.Trials[0].Spent >= 2 && a.Trials[0].Spent <= F25Budget
		if a.Passes {
			r.Passing++
		}
		r.Arms[i] = a
	}
	r.Classification = F25NoGo
	if r.Passing == 4 {
		r.Classification = F25Signal
	}
	r.DigestSHA256 = f25Digest(r)
	return r, nil
}
func F25Validate(r F25Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f25Digest(r) || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		return errF25
	}
	expected, e := F25Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF25
	}
	return nil
}
