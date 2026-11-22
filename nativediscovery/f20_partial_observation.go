// Eureka F20: preregistered, bounded noisy partial-observation active intervention.
// Development evidence only. No native owner/first-use/dispatch or research-loop action.
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
	F20Schema          = "forge.native-discovery.noisy-active-causal-probing.dev.v1"
	F20NoGo            = "F20_DEV_NO_GO"
	F20Signal          = "F20_DEV_SIGNAL_UNVERIFIED"
	F20Actions         = 18
	F20MinStrongGain   = 2
	F20MinAblationGain = 3
	F20RuleCount       = 256
)

var errF20 = errors.New("FORGE_EUREKA_F20_SOURCE_OR_AUTHORITY_INVALID")

func f20Seeds() [2]uint32     { return [2]uint32{113, 127} }
func f20Schedules() [2]string { return [2]string{"balanced", "skewed"} }
func f20Kinds() [10]string {
	return [10]string{
		"pending-coverage", "bayes-risk", "bayes-ig", "bayes-two-step", "credited-coverage",
		"posterior-thompson", "balanced-actions", "cue-following", "no-intervention", "wrong-credit",
	}
}
func f20Law(seed uint32) (int, error) {
	switch seed {
	case 113:
		return 0xa6, nil
	case 127:
		return 0x5c, nil
	}
	return 0, errF20
}
func f20Cue(seed uint32, schedule string, step int) (int, error) {
	if _, err := f20Law(seed); err != nil || step < 0 || step > F20Actions {
		return 0, errF20
	}
	switch schedule {
	case "balanced":
		return (3*step + int(seed%4)) % 4, nil
	case "skewed":
		if step%4 == 3 {
			return (step/4 + int(seed%4)) % 4, nil
		}
		return (step/3 + int(seed%2)) % 2, nil
	default:
		return 0, errF20
	}
}

// Truth is used by the separate simulator and scorer; NEVER by f20Select.
func f20Truth(rule, cue, action int) int {
	return ((rule >> cue) & 1) ^ (action & ((rule >> (cue + 4)) & 1))
}
func f20Outcome(seed uint32, step, cue, action int) (value int, erased, flipped bool, err error) {
	law, e := f20Law(seed)
	if e != nil || step < 0 || step >= F20Actions || cue < 0 || cue >= 4 || action < 0 || action > 1 {
		return 0, false, false, errF20
	}
	if f12Mix(seed^0x517cc1b7^uint32(step+1)*0x9e3779b9)%5 == 0 {
		return -1, true, false, nil
	}
	flip := f12Mix(seed^0xdab5a609^uint32(step+1)*0x85ebca6b)%8 == 0
	v := f20Truth(law, cue, action)
	if flip {
		v ^= 1
	}
	return v, false, flip, nil
}

type f20Probe struct {
	Step        int `json:"step"`
	Cue         int `json:"cue"`
	Action      int `json:"action"`
	WrongAction int `json:"wrong_action"`
}
type f20Credit struct {
	Step        int `json:"step"`
	Cue         int `json:"cue"`
	Action      int `json:"action"`
	WrongAction int `json:"wrong_action"`
	Value       int `json:"observed"`
}
type f20State struct {
	Seen    int         `json:"seen"`
	Credits []f20Credit `json:"credits"`
	Pending []f20Probe  `json:"pending"`
}

func f20StateValid(s f20State) bool {
	if s.Seen < 0 || s.Seen > F20Actions || len(s.Credits) != max(0, s.Seen-2) || len(s.Pending) != min(s.Seen, 2) {
		return false
	}
	for i, c := range s.Credits {
		if c.Step != i || c.Cue < 0 || c.Cue > 3 || c.Action < 0 || c.Action > 1 ||
			c.WrongAction < 0 || c.WrongAction > 1 || c.Value < -1 || c.Value > 1 {
			return false
		}
	}
	for i, p := range s.Pending {
		if p.Step != s.Seen-len(s.Pending)+i || p.Cue < 0 || p.Cue > 3 || p.Action < 0 || p.Action > 1 || p.WrongAction < 0 || p.WrongAction > 1 {
			return false
		}
	}
	return true
}
func f20Snapshot(s f20State) ([]byte, error) {
	if !f20StateValid(s) {
		return nil, errF20
	}
	return json.Marshal(s)
}
func f20Load(raw []byte, digest string) (f20State, error) {
	if f3Hash(raw) != digest {
		return f20State{}, errF20
	}
	var s f20State
	if json.Unmarshal(raw, &s) != nil || !f20StateValid(s) {
		return f20State{}, errF20
	}
	canonical, e := f20Snapshot(s)
	if e != nil || !bytes.Equal(canonical, raw) {
		return f20State{}, errF20
	}
	return s, nil
}

// The same fully expressive, noisy-channel Bayesian posterior for EVERY arm.
// Weights are 7^(matched non-missing observations), normalized by total mass.
func f20Posterior(records []f20Credit, wrong bool) ([F20RuleCount]float64, int, error) {
	var out [F20RuleCount]float64
	if len(records) > F20Actions-2 {
		return out, 0, errF20
	}
	work := 0
	total := 0.0
	for law := 0; law < F20RuleCount; law++ {
		weight := 1.0
		for _, r := range records {
			if r.Step < 0 || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 ||
				r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
				return out, 0, errF20
			}
			if r.Value < 0 {
				continue
			}
			action := r.Action
			if wrong {
				action = r.WrongAction
			}
			if f20Truth(law, r.Cue, action) == r.Value {
				weight *= 7
			}
			work++
		}
		out[law] = weight
		total += weight
	}
	if total <= 0 || math.IsInf(total, 0) || math.IsNaN(total) {
		return out, 0, errF20
	}
	for i := range out {
		out[i] /= total
	}
	return out, work + F20RuleCount, nil
}
func f20PredProb(w [F20RuleCount]float64, cue, action int) (float64, int) {
	p := 0.0
	for law, mass := range w {
		if f20Truth(law, cue, action) == 1 {
			p += mass
		}
	}
	return p, F20RuleCount
}
func f20Entropy(p float64) float64 {
	if p <= 0 || p >= 1 {
		return 0
	}
	return -p*math.Log(p) - (1-p)*math.Log(1-p)
}
func f20Info(w [F20RuleCount]float64, cue, action int) (float64, int) {
	p, cost := f20PredProb(w, cue, action)
	return f20Entropy(0.125+0.75*p) - f20Entropy(0.125), cost
}
func f20Condition(w [F20RuleCount]float64, cue, action, obs int) ([F20RuleCount]float64, float64, int) {
	var next [F20RuleCount]float64
	total := 0.0
	for law, mass := range w {
		multiplier := 1.0
		if f20Truth(law, cue, action) == obs {
			multiplier = 7
		}
		next[law] = mass * multiplier
		total += next[law]
	}
	for i := range next {
		next[i] /= total
	}
	return next, total / 8, F20RuleCount
}

// Expected correct decisions of the Bayes-optimal 0/1 classifier on eight probes.
func f20BayesCorrect(w [F20RuleCount]float64) (float64, int) {
	correct, cost := 0.0, 0
	for cue := 0; cue < 4; cue++ {
		for action := 0; action < 2; action++ {
			p, ops := f20PredProb(w, cue, action)
			correct += math.Max(p, 1-p)
			cost += ops
		}
	}
	return correct, cost
}
func f20ExpectedRisk(w [F20RuleCount]float64, cue, action int) (float64, int) {
	total, work := 0.0, 0
	for observed := 0; observed <= 1; observed++ {
		conditional, prob, cost := f20Condition(w, cue, action, observed)
		accuracy, more := f20BayesCorrect(conditional)
		total += prob * accuracy
		work += cost + more
	}
	return total, work
}

// Exact two-decision Bayesian information lookahead, marginalizing current
// noisy outcome and choosing the best conditional next action.
func f20TwoStep(w [F20RuleCount]float64, cue, nextCue, action int) (float64, int) {
	info, work := f20Info(w, cue, action)
	future := 0.0
	for outcome := 0; outcome < 2; outcome++ {
		conditioned, p, cost := f20Condition(w, cue, action, outcome)
		work += cost
		best := -1.0
		for nextAction := 0; nextAction <= 1; nextAction++ {
			score, ops := f20Info(conditioned, nextCue, nextAction)
			work += ops
			if score > best {
				best = score
			}
		}
		future += p * best
	}
	return info + future, work
}
func f20Select(kind string, credits []f20Credit, pending []f20Probe, cue, nextCue, step int) (int, int, error) {
	if step < 0 || step >= F20Actions || cue < 0 || cue > 3 || nextCue < 0 || nextCue > 3 ||
		len(credits) != max(0, step-1) || len(pending) != min(step, 1) {
		return 0, 0, errF20
	}
	for i, r := range credits {
		if r.Step != i || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 ||
			r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
			return 0, 0, errF20
		}
	}
	for _, p := range pending {
		if p.Cue < 0 || p.Cue > 3 || p.Action < 0 || p.Action > 1 {
			return 0, 0, errF20
		}
	}
	switch kind {
	case "balanced-actions":
		return step & 1, 1, nil
	case "cue-following":
		return cue & 1, 1, nil
	case "no-intervention":
		return 0, 1, nil
	case "pending-coverage", "bayes-risk", "bayes-ig", "bayes-two-step",
		"credited-coverage", "posterior-thompson", "wrong-credit":
	default:
		return 0, 0, errF20
	}
	weights, work, e := f20Posterior(credits, kind == "wrong-credit")
	if e != nil {
		return 0, 0, errF20
	}
	if kind == "pending-coverage" || kind == "wrong-credit" || kind == "credited-coverage" {
		count := [2]int{}
		for _, r := range credits {
			if r.Value != -1 && r.Cue == cue {
				count[r.Action]++
			}
		}
		if kind != "credited-coverage" {
			for _, p := range pending {
				if p.Cue == cue {
					count[p.Action]++
				}
			}
		}
		if count[0] != count[1] {
			if count[0] < count[1] {
				return 0, work + len(credits) + len(pending), nil
			}
			return 1, work + len(credits) + len(pending), nil
		}
		if kind == "credited-coverage" {
			return 0, work + len(credits), nil
		}
		a0, n0 := f20Info(weights, cue, 0)
		a1, n1 := f20Info(weights, cue, 1)
		work += n0 + n1
		if a1 > a0+1e-12 {
			return 1, work, nil
		}
		return 0, work, nil
	}
	if kind == "posterior-thompson" {
		fraction := float64(f12Mix(uint32(step+1)*0x9e3779b9^uint32(len(credits)+1)*0x85ebca6b)) / 4294967296.0
		selected := 255
		for law, mass := range weights {
			fraction -= mass
			if fraction < 0 {
				selected = law
				break
			}
		}
		if f20Truth(selected, cue, 1) == 1 && f20Truth(selected, cue, 0) == 0 {
			return 1, work + F20RuleCount, nil
		}
		return 0, work + F20RuleCount, nil
	}
	best := -1.0
	choice := 0
	for action := 0; action < 2; action++ {
		var value float64
		var ops int
		switch kind {
		case "bayes-risk":
			value, ops = f20ExpectedRisk(weights, cue, action)
		case "bayes-ig":
			value, ops = f20Info(weights, cue, action)
		case "bayes-two-step":
			value, ops = f20TwoStep(weights, cue, nextCue, action)
		}
		work += ops
		if value > best+1e-12 {
			best, choice = value, action
		}
	}
	return choice, work, nil
}
func f20OracleScore(w [F20RuleCount]float64, law int) (int, int) {
	score, work := 0, 0
	for cue := 0; cue < 4; cue++ {
		for action := 0; action < 2; action++ {
			p, ops := f20PredProb(w, cue, action)
			prediction := 0
			if p > 0.5+1e-12 {
				prediction = 1
			}
			if prediction == f20Truth(law, cue, action) {
				score++
			}
			work += ops
		}
	}
	return score, work
}

type F20PolicyTrace struct {
	Name              string `json:"name"`
	Actions           string `json:"actions"`
	ObservationSHA256 string `json:"observation_sha256"`
	G1SnapshotSHA256  string `json:"g1_snapshot_sha256"`
	G2SnapshotSHA256  string `json:"g2_snapshot_sha256"`
	Correct           [4]int `json:"correct"`
	TotalCorrect      int    `json:"total_correct"`
	Work              int    `json:"model_work"`
	Delivered         int    `json:"delivered"`
	Missing           int    `json:"missing"`
	Flipped           int    `json:"flipped"`
	G1Credited        int    `json:"g1_credited"`
	G1Pending         int    `json:"g1_pending"`
	G2Credited        int    `json:"g2_credited"`
	G2Pending         int    `json:"g2_pending"`
	ColdMatches       bool   `json:"cold_matches"`
}

// coldMode determines whether continuation really uses serialized state.
func f20Simulate(seed uint32, schedule, kind string, coldMode bool) (F20PolicyTrace, []byte, error) {
	law, err := f20Law(seed)
	if err != nil {
		return F20PolicyTrace{}, nil, errF20
	}
	state := f20State{Credits: make([]f20Credit, 0, F20Actions), Pending: make([]f20Probe, 0, 2)}
	out := F20PolicyTrace{Name: kind}
	marks := [4]int{4, 7, 10, 14}
	for step := 0; step < F20Actions; step++ {
		if step >= 2 {
			due := state.Pending[0]
			if due.Step != step-2 {
				return F20PolicyTrace{}, nil, errF20
			}
			val, missing, flipped, e := f20Outcome(seed, due.Step, due.Cue, due.Action)
			if e != nil {
				return F20PolicyTrace{}, nil, errF20
			}
			if missing {
				out.Missing++
			}
			if flipped {
				out.Flipped++
			}
			state.Credits = append(state.Credits, f20Credit{
				Step: due.Step, Cue: due.Cue, Action: due.Action, WrongAction: due.WrongAction, Value: val})
			out.Delivered++
			state.Pending = state.Pending[1:]
		}
		cue, e := f20Cue(seed, schedule, step)
		if e != nil {
			return F20PolicyTrace{}, nil, errF20
		}
		nextCue, e := f20Cue(seed, schedule, step+1)
		if e != nil {
			return F20PolicyTrace{}, nil, errF20
		}
		weights, w, e := f20Posterior(state.Credits, kind == "wrong-credit")
		if e != nil {
			return F20PolicyTrace{}, nil, errF20
		}
		for i, t := range marks {
			if step == t {
				score, ops := f20OracleScore(weights, law)
				out.Correct[i] = score
				out.TotalCorrect += score
				out.Work += w + ops
			}
		}
		action, cost, e := f20Select(kind, state.Credits, state.Pending, cue, nextCue, step)
		if e != nil || action < 0 || action > 1 || cost < 1 {
			return F20PolicyTrace{}, nil, errF20
		}
		out.Work += cost
		prior := 0
		if step > 0 {
			prior = int(out.Actions[step-1] - '0')
		}
		state.Pending = append(state.Pending, f20Probe{Step: step, Cue: cue, Action: action, WrongAction: prior})
		out.Actions += string(byte('0' + action))
		state.Seen++
		if !f20StateValid(state) {
			return F20PolicyTrace{}, nil, errF20
		}
		if step == 9 {
			out.G1Credited, out.G1Pending = len(state.Credits), len(state.Pending)
			snap, e := f20Snapshot(state)
			if e != nil {
				return F20PolicyTrace{}, nil, errF20
			}
			out.G1SnapshotSHA256 = f3Hash(snap)
			if coldMode {
				restored, e := f20Load(snap, out.G1SnapshotSHA256)
				if e != nil || !reflect.DeepEqual(restored, state) {
					return F20PolicyTrace{}, nil, errF20
				}
				state = restored
			}
		}
	}
	out.G2Credited, out.G2Pending = len(state.Credits), len(state.Pending)
	raw, err := f20Snapshot(state)
	if err != nil {
		return F20PolicyTrace{}, nil, errF20
	}
	out.G2SnapshotSHA256 = f3Hash(raw)
	out.ObservationSHA256 = f8Digest("FORGE-EUREKA-F20-REAL-ACTIVE-OBSERVATIONS-V1\n", state)
	out.ColdMatches = out.G1Credited == 8 && out.G1Pending == 2 && out.G2Credited == 16 && out.G2Pending == 2
	if len(out.Actions) != F20Actions || out.Delivered != 16 || !out.ColdMatches {
		return F20PolicyTrace{}, nil, errF20
	}
	return out, raw, nil
}
func f20PolicyRun(seed uint32, schedule, kind string) (F20PolicyTrace, error) {
	out, cold, err := f20Simulate(seed, schedule, kind, true)
	if err != nil {
		return F20PolicyTrace{}, errF20
	}
	fresh, raw, err := f20Simulate(seed, schedule, kind, false)
	if err != nil || !bytes.Equal(cold, raw) || !reflect.DeepEqual(out, fresh) {
		return F20PolicyTrace{}, errF20
	}
	return out, nil
}

type F20Arm struct {
	Seed               uint32             `json:"seed"`
	Schedule           string             `json:"schedule"`
	Policies           [10]F20PolicyTrace `json:"policies"`
	StrongestName      string             `json:"strongest_name"`
	StrongestScore     int                `json:"strongest_score"`
	GainStrongest      int                `json:"gain_strongest"`
	GainNoIntervention int                `json:"gain_no_intervention"`
	GainWrongCredit    int                `json:"gain_wrong_credit"`
	NonCueActions      int                `json:"non_cue_actions"`
	Passes             bool               `json:"passes"`
}

func f20Arm(seed uint32, schedule string) (F20Arm, error) {
	if _, e := f20Law(seed); e != nil {
		return F20Arm{}, errF20
	}
	out := F20Arm{Seed: seed, Schedule: schedule, StrongestScore: -1}
	for i, kind := range f20Kinds() {
		trace, e := f20PolicyRun(seed, schedule, kind)
		if e != nil {
			return F20Arm{}, errF20
		}
		out.Policies[i] = trace
		if i >= 1 && i <= 7 && trace.TotalCorrect > out.StrongestScore {
			out.StrongestName = kind
			out.StrongestScore = trace.TotalCorrect
		}
	}
	for step, ch := range out.Policies[0].Actions {
		cue, _ := f20Cue(seed, schedule, step)
		if int(ch-'0') != cue&1 {
			out.NonCueActions++
		}
	}
	out.GainStrongest = out.Policies[0].TotalCorrect - out.StrongestScore
	out.GainNoIntervention = out.Policies[0].TotalCorrect - out.Policies[8].TotalCorrect
	out.GainWrongCredit = out.Policies[0].TotalCorrect - out.Policies[9].TotalCorrect
	out.Passes = out.GainStrongest >= F20MinStrongGain && out.GainNoIntervention >= F20MinAblationGain &&
		out.GainWrongCredit >= F20MinAblationGain && out.NonCueActions >= 2 && out.StrongestScore < 32
	for _, p := range out.Policies {
		if !p.ColdMatches {
			out.Passes = false
		}
	}
	return out, nil
}

type F20Report struct {
	Schema                      string    `json:"schema"`
	ParentF19SHA256             string    `json:"parent_f19_sha256"`
	EarlierNegativesPreserved   bool      `json:"earlier_negatives_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Schedules                   [2]string `json:"schedules"`
	Actions                     int       `json:"actions"`
	Delay                       int       `json:"delay"`
	Milestones                  [4]int    `json:"milestones"`
	MaxScore                    int       `json:"max_score"`
	MinStrongGain               int       `json:"minimum_strong_gain"`
	MinAblationGain             int       `json:"minimum_ablation_gain"`
	Arms                        []F20Arm  `json:"arms"`
	PassingArms                 int       `json:"passing_arms"`
	TotalWork                   int       `json:"total_work"`
	Classification              string    `json:"classification"`
	DevelopmentOnly             bool      `json:"development_only"`
	IndependentFirstUseConsumed bool      `json:"independent_first_use_consumed"`
	ScientificAccepted          bool      `json:"scientific_accepted"`
	WholeProcessCostMeasured    bool      `json:"whole_process_cost_measured"`
	OwnerEligible               bool      `json:"owner_eligible"`
	DispatchAuthorized          bool      `json:"dispatch_authorized"`
	ActiveResearchChanged       bool      `json:"active_research_changed"`
	AgentCalls                  int       `json:"agent_calls"`
	PaidAPICalls                int       `json:"paid_api_calls"`
	DigestSHA256                string    `json:"digest_sha256"`
}

func f20Digest(v F20Report) string {
	v.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F20-FROZEN-NOISY-INTERVENTIONS-V1\n", v)
}
func F20Development() (F20Report, error) {
	parent, e := F19Development()
	if e != nil || F19Validate(parent) != nil || parent.Classification != F19NO_GO ||
		parent.ScientificAccepted || parent.OwnerEligible || parent.DispatchAuthorized {
		return F20Report{}, errF20
	}
	out := F20Report{Schema: F20Schema, ParentF19SHA256: parent.DigestSHA256,
		EarlierNegativesPreserved: true, Seeds: f20Seeds(), Schedules: f20Schedules(),
		Actions: F20Actions, Delay: 2, Milestones: [4]int{4, 7, 10, 14}, MaxScore: 32,
		MinStrongGain: F20MinStrongGain, MinAblationGain: F20MinAblationGain,
		DevelopmentOnly: true, Arms: make([]F20Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, schedule := range out.Schedules {
			arm, e := f20Arm(seed, schedule)
			if e != nil {
				return F20Report{}, errF20
			}
			out.Arms = append(out.Arms, arm)
			for _, p := range arm.Policies {
				out.TotalWork += p.Work
			}
			if arm.Passes {
				out.PassingArms++
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalWork <= 0 {
		return F20Report{}, errF20
	}
	out.Classification = F20NoGo
	if out.PassingArms == 4 {
		out.Classification = F20Signal
	}
	out.DigestSHA256 = f20Digest(out)
	return out, nil
}

var f20SourceReference struct {
	once   sync.Once
	report F20Report
	err    error
}

func F20Validate(v F20Report) error {
	if v.Schema != F20Schema || v.DigestSHA256 != f20Digest(v) || !v.DevelopmentOnly ||
		!v.EarlierNegativesPreserved || v.IndependentFirstUseConsumed || v.ScientificAccepted ||
		v.WholeProcessCostMeasured || v.OwnerEligible || v.DispatchAuthorized ||
		v.ActiveResearchChanged || v.AgentCalls != 0 || v.PaidAPICalls != 0 {
		return errF20
	}
	f20SourceReference.once.Do(func() { f20SourceReference.report, f20SourceReference.err = F20Development() })
	if f20SourceReference.err != nil || !reflect.DeepEqual(v, f20SourceReference.report) {
		return errF20
	}
	return nil
}
