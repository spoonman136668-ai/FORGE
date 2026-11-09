// Eureka F26: effect-specific expected information gain with cue-budget reservations.
// Development only. No first-use, owner, research-loop or deployment hooks.
package nativediscovery

import (
	"bytes"
	"encoding/json"
	"errors"
	"math"
	"reflect"
)

const (
	F26Schema  = "forge.native-discovery.effect-information-gain.dev.v1"
	F26NoGo    = "F26_DEV_NO_GO"
	F26Signal  = "F26_DEV_SIGNAL_UNVERIFIED"
	F26Actions = 48
	F26Budget  = 8
	F26Parent  = "7cf32ad71d13f94f3740b5ce278f3cf2b7aa84f8"
)

var errF26 = errors.New("FORGE_EUREKA_F26_SOURCE_OR_AUTHORITY_INVALID")

func f26Seeds() [2]uint32     { return [2]uint32{193, 197} }
func f26Schedules() [2]string { return [2]string{"balanced", "skewed"} }
func f26Kinds() [9]string {
	return [9]string{"effect-ig", "f25-causal-pair", "bayes-ig", "bayes-error", "thompson", "periodic", "random", "no-intervention", "wrong-credit"}
}
func f26Law(seed uint32) (int, error) {
	switch seed {
	case 193:
		return 0x4b, nil
	case 197:
		return 0xb2, nil
	}
	return 0, errF26
}
func f26Cue(seed uint32, schedule string, step int) (int, error) {
	if _, e := f26Law(seed); e != nil || step < 0 || step >= F26Actions {
		return 0, errF26
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
	return 0, errF26
}

// Simulator-only ground truth, never called by f26Select or effect information gain.
func f26Outcome(seed uint32, step, cue, action int) (int, error) {
	law, e := f26Law(seed)
	if e != nil || step < 0 || step >= F26Actions || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, errF26
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
func f26EffectEntropy(f [4]float64) float64 { return f24Entropy(f[2] + f[3]) }

// Mutual information I(effect bit; observed outcome | selected intervention).
// 8:1 likelihood matches f24Fit and all comparator models.
func f26EffectIG(f [4]float64, action int) float64 {
	prior := f26EffectEntropy(f)
	future := 0.0
	for y := 0; y < 2; y++ {
		var conditional [4]float64
		predictive := 0.0
		for p, mass := range f {
			v := (p & 1) ^ (action & ((p >> 1) & 1))
			likelihood := 1.0 / 9.0
			if v == y {
				likelihood = 8.0 / 9.0
			}
			conditional[p] = mass * likelihood
			predictive += conditional[p]
		}
		if predictive <= 0 {
			continue
		}
		for j := range conditional {
			conditional[j] /= predictive
		}
		future += predictive * f26EffectEntropy(conditional)
	}
	return prior - future
}
func f26Select(recs []f20Credit, pending []f20Probe, cue, step, spent int, seed uint32, kind string) (int, int, error) {
	if _, e := f26Law(seed); e != nil || cue < 0 || cue > 3 || step < 0 || step >= F26Actions || spent < 0 || spent > F26Budget {
		return 0, 0, errF26
	}
	valid := false
	for _, k := range f26Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return 0, 0, errF26
	}
	if spent == F26Budget || kind == "no-intervention" {
		return 0, 1, nil
	}
	switch kind {
	case "periodic":
		if step%6 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	case "random":
		if f12Mix(seed^uint32(step+1)*0x9e3779b9)%6 == 0 {
			return 1, 1, nil
		}
		return 0, 1, nil
	}
	wrong := kind == "wrong-credit"
	f, work, e := f24Fit(recs, wrong)
	if e != nil {
		return 0, 0, e
	}
	p0, p1 := f24P(f, cue, 0), f24P(f, cue, 1)
	switch kind {
	case "effect-ig", "wrong-credit":
		credited := 0
		for _, r := range recs {
			if r.Cue == cue && r.Action == 1 {
				credited++
			}
		}
		for _, p := range pending {
			if p.Cue == cue && p.Action == 1 {
				credited++
			}
		}
		if credited < 2 && f26EffectIG(f[cue], 1) > f26EffectIG(f[cue], 0)+1e-8 {
			return 1, work + 32, nil
		}
		return 0, work + 32, nil
	case "f25-causal-pair":
		count := 0
		for _, r := range recs {
			if r.Cue == cue && r.Action == 1 {
				count++
			}
		}
		queued := false
		for _, p := range pending {
			if p.Cue == cue && p.Action == 1 {
				queued = true
			}
		}
		effect := f[cue][2] + f[cue][3]
		if (p0 <= .20 || p0 >= .80) && effect >= .18 && effect <= .82 && count < 3 && !queued {
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
		total := 0.0
		for pair, p := range f[cue] {
			total += p
			if u < total || pair == 3 {
				if pair&2 != 0 {
					return 1, work, nil
				}
				break
			}
		}
	}
	return 0, work, nil
}

type f26State struct {
	Seen        int         `json:"seen"`
	Credits     []f20Credit `json:"credits"`
	Pending     []f20Probe  `json:"pending"`
	Actions     []int       `json:"actions"`
	Spent       int         `json:"spent"`
	Work        int         `json:"work"`
	Trace       string      `json:"trace"`
	Checkpoints [4]int      `json:"checkpoints"`
}

func f26TraceLength(seen int) int {
	n := 0
	for _, t := range [4]int{10, 18, 26, 34} {
		if seen > t {
			n += 8
		}
	}
	return n
}
func f26Valid(s f26State) bool {
	if s.Seen < 0 || s.Seen > F26Actions || len(s.Credits) != max(0, s.Seen-2) || len(s.Pending) != min(s.Seen, 2) || len(s.Actions) != s.Seen || s.Spent < 0 || s.Spent > F26Budget || s.Work < 0 || len(s.Trace) != f26TraceLength(s.Seen) {
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
		if r.Step != i || r.Cue < 0 || r.Cue > 3 || r.Action != s.Actions[i] || r.WrongAction != 1-r.Action || r.Value < -1 || r.Value > 1 {
			return false
		}
	}
	for j, p := range s.Pending {
		i := s.Seen - len(s.Pending) + j
		if p.Step != i || p.Cue < 0 || p.Cue > 3 || p.Action != s.Actions[i] || p.WrongAction != 1-p.Action {
			return false
		}
	}
	return true
}
func f26Save(s f26State) ([]byte, error) {
	if !f26Valid(s) {
		return nil, errF26
	}
	return json.Marshal(s)
}
func f26Load(raw []byte) (f26State, error) {
	var s f26State
	if json.Unmarshal(raw, &s) != nil || !f26Valid(s) {
		return f26State{}, errF26
	}
	canonical, _ := json.Marshal(s)
	if !bytes.Equal(canonical, raw) {
		return f26State{}, errF26
	}
	return s, nil
}
func f26Score(s *f26State, seed uint32, t int, wrong bool) error {
	idx := -1
	for i, x := range [4]int{10, 18, 26, 34} {
		if x == t {
			idx = i
		}
	}
	if idx < 0 || s.Seen != t || len(s.Credits) != t-1 || len(s.Pending) != 1 {
		return errF26
	}
	law, e := f26Law(seed)
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
				s.Checkpoints[idx]++
				s.Trace += "1"
			} else {
				s.Trace += "0"
			}
		}
	}
	return nil
}
func f26Step(s *f26State, seed uint32, sched, kind string) error {
	if !f26Valid(*s) || s.Seen >= F26Actions {
		return errF26
	}
	t := s.Seen
	if t >= 2 {
		p := s.Pending[0]
		value, e := f26Outcome(seed, p.Step, p.Cue, p.Action)
		if e != nil {
			return e
		}
		s.Credits = append(s.Credits, f20Credit{Step: p.Step, Cue: p.Cue, Action: p.Action, WrongAction: 1 - p.Action, Value: value})
		s.Pending = s.Pending[1:]
	}
	for _, x := range [4]int{10, 18, 26, 34} {
		if x == t {
			if e := f26Score(s, seed, t, kind == "wrong-credit"); e != nil {
				return e
			}
		}
	}
	cue, e := f26Cue(seed, sched, t)
	if e != nil {
		return e
	}
	action, w, e := f26Select(s.Credits, s.Pending, cue, t, s.Spent, seed, kind)
	if e != nil {
		return e
	}
	s.Work += w
	s.Actions = append(s.Actions, action)
	s.Spent += action
	s.Pending = append(s.Pending, f20Probe{Step: t, Cue: cue, Action: action, WrongAction: 1 - action})
	s.Seen++
	if !f26Valid(*s) {
		return errF26
	}
	return nil
}

type F26Trial struct {
	Kind             string `json:"kind"`
	Score            int    `json:"score"`
	Checkpoints      [4]int `json:"checkpoints"`
	Trace            string `json:"trace"`
	Spent            int    `json:"spent"`
	Credits          int    `json:"credits"`
	Pending          int    `json:"pending"`
	Work             int    `json:"work"`
	ActionsSHA256    string `json:"actions_sha256"`
	CheckpointSHA256 string `json:"checkpoint_sha256"`
	FinalSHA256      string `json:"final_sha256"`
	ColdMatches      bool   `json:"cold_matches"`
}

func f26Run(seed uint32, sched, kind string, cold bool) (F26Trial, []byte, []byte, error) {
	if _, e := f26Cue(seed, sched, 0); e != nil {
		return F26Trial{}, nil, nil, e
	}
	valid := false
	for _, k := range f26Kinds() {
		if k == kind {
			valid = true
		}
	}
	if !valid {
		return F26Trial{}, nil, nil, errF26
	}
	s := f26State{Credits: []f20Credit{}, Pending: []f20Probe{}, Actions: []int{}}
	for s.Seen < 24 {
		if e := f26Step(&s, seed, sched, kind); e != nil {
			return F26Trial{}, nil, nil, e
		}
	}
	checkpoint, e := f26Save(s)
	if e != nil {
		return F26Trial{}, nil, nil, e
	}
	if cold {
		s, e = f26Load(checkpoint)
		if e != nil {
			return F26Trial{}, nil, nil, e
		}
	}
	for s.Seen < F26Actions {
		if e := f26Step(&s, seed, sched, kind); e != nil {
			return F26Trial{}, nil, nil, e
		}
	}
	final, e := f26Save(s)
	if e != nil {
		return F26Trial{}, nil, nil, e
	}
	actions, _ := json.Marshal(s.Actions)
	score := 0
	for _, n := range s.Checkpoints {
		score += n
	}
	return F26Trial{Kind: kind, Score: score, Checkpoints: s.Checkpoints, Trace: s.Trace, Spent: s.Spent, Credits: len(s.Credits), Pending: len(s.Pending), Work: s.Work, ActionsSHA256: f25Hash(actions), CheckpointSHA256: f25Hash(checkpoint), FinalSHA256: f25Hash(final), ColdMatches: true}, checkpoint, final, nil
}

type F26Arm struct {
	Seed               uint32      `json:"seed"`
	Schedule           string      `json:"schedule"`
	Trials             [9]F26Trial `json:"trials"`
	BestConventional   int         `json:"best_conventional"`
	GainStrong         int         `json:"gain_strong"`
	GainNoIntervention int         `json:"gain_no_intervention"`
	GainWrongCredit    int         `json:"gain_wrong_credit"`
	Passes             bool        `json:"passes"`
}
type F26Report struct {
	Schema                    string    `json:"schema"`
	Parent                    string    `json:"parent"`
	Seeds                     [2]uint32 `json:"seeds"`
	Schedules                 [2]string `json:"schedules"`
	Actions                   int       `json:"actions"`
	Budget                    int       `json:"budget"`
	Checkpoints               [4]int    `json:"checkpoints"`
	MinimumGain               int       `json:"minimum_gain"`
	MinimumAblationGain       int       `json:"minimum_ablation_gain"`
	Arms                      [4]F26Arm `json:"arms"`
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

func f26Digest(r F26Report) string { r.DigestSHA256 = ""; b, _ := json.Marshal(r); return f25Hash(b) }
func F26Development() (F26Report, error) {
	r := F26Report{Schema: F26Schema, Parent: F26Parent, Seeds: f26Seeds(), Schedules: f26Schedules(), Actions: F26Actions, Budget: F26Budget, Checkpoints: [4]int{10, 18, 26, 34}, MinimumGain: 2, MinimumAblationGain: 3, EarlierNegativesPreserved: true, DevelopmentOnly: true}
	for i := range r.Arms {
		seed, sched := r.Seeds[i/2], r.Schedules[i%2]
		a := F26Arm{Seed: seed, Schedule: sched}
		for j, kind := range f26Kinds() {
			cold, ck, final, e := f26Run(seed, sched, kind, true)
			if e != nil {
				return F26Report{}, e
			}
			warm, wck, wfinal, e := f26Run(seed, sched, kind, false)
			if e != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(ck, wck) || !bytes.Equal(final, wfinal) {
				return F26Report{}, errF26
			}
			a.Trials[j] = cold
		}
		best := -1
		for j := 1; j <= 6; j++ {
			if a.Trials[j].Score > best {
				best = a.Trials[j].Score
			}
		}
		a.BestConventional = best
		a.GainStrong = a.Trials[0].Score - best
		a.GainNoIntervention = a.Trials[0].Score - a.Trials[7].Score
		a.GainWrongCredit = a.Trials[0].Score - a.Trials[8].Score
		a.Passes = a.GainStrong >= 2 && a.GainNoIntervention >= 3 && a.GainWrongCredit >= 3 && a.Trials[0].Spent >= 2 && a.Trials[0].Spent <= F26Budget
		if a.Passes {
			r.Passing++
		}
		r.Arms[i] = a
	}
	r.Classification = F26NoGo
	if r.Passing == 4 {
		r.Classification = F26Signal
	}
	r.DigestSHA256 = f26Digest(r)
	return r, nil
}
func F26Validate(r F26Report) error {
	if r.DigestSHA256 == "" || r.DigestSHA256 != f26Digest(r) || r.FirstUseConsumed || r.ScientificAccepted || r.OwnerEligible || r.DispatchAuthorized || r.WholeProcessCostProven || !r.DevelopmentOnly || !r.EarlierNegativesPreserved {
		return errF26
	}
	expected, e := F26Development()
	if e != nil || !reflect.DeepEqual(expected, r) {
		return errF26
	}
	return nil
}
