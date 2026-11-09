// Eureka F19: preregistered DEV-only genuine action-selection under delayed feedback.
// This code has no scientific first-use, owner dispatch, queue, scheduler, or integration path.
package nativediscovery

import (
	"bytes"
	"errors"
	"reflect"
	"sync"
)

const (
	F19Schema          = "forge.native-discovery.active-causal-interventions.dev.v1"
	F19NO_GO           = "F19_DEV_NO_GO"
	F19Signal          = "F19_DEV_SIGNAL_UNVERIFIED"
	F19Actions         = 18
	F19MinStrongGain   = 4
	F19MinAblationGain = 8
)

var errF19 = errors.New("FORGE_EUREKA_F19_SOURCE_OR_AUTHORITY_INVALID")

func f19Seeds() [2]uint32     { return [2]uint32{107, 109} }
func f19Schedules() [2]string { return [2]string{"confounded", "varied"} }
func f19Kinds() [9]string {
	return [9]string{"pending-aware", "queue-lookahead", "two-step-ig", "one-step-ig",
		"thompson", "balanced", "passive", "no-intervention", "wrong-credit"}
}

// The true rule is world/scorer-only. It is not reachable from f19Select.
func f19WorldRule(seed uint32) (int, error) {
	switch seed {
	case 107:
		return 3, nil
	case 109:
		return 11, nil
	}
	return 0, errF19
}
func f19Cue(seed uint32, schedule string, step int) (int, error) {
	if _, err := f19WorldRule(seed); err != nil || step < 0 || step > F19Actions {
		return 0, errF19
	}
	switch schedule {
	case "confounded":
		return step & 1, nil
	case "varied":
		return f12Cue(seed, step, 1), nil
	}
	return 0, errF19
}
func f19Residual(rule, cue, action int) int {
	result := 0
	if rule&1 != 0 {
		result ^= action
	}
	if rule&2 != 0 {
		result ^= cue & 1
	}
	if rule&8 != 0 {
		result ^= 1
	}
	return result
}

type f19Probe struct{ cue, action int }

// Uniform posterior on the exact best-fitting 8-mask hypothesis class. A
// contradictory (e.g. wrong-attribution) record never creates an empty class.
func f19Posterior(credits []f13Credit, wrong bool) ([]int, int) {
	masks := f18Masks()
	best := -1
	out := make([]int, 0, len(masks))
	work := 0
	for _, mask := range masks {
		hits := 0
		for _, c := range credits {
			if f13Match(mask, c, wrong) {
				hits++
			}
			work++
		}
		if hits > best {
			best = hits
			out = out[:0]
			out = append(out, mask)
		} else if hits == best {
			out = append(out, mask)
		}
	}
	return out, work
}
func f19Collision(models []int, probes []f19Probe) (int, int) {
	var buckets [16]int
	work := 0
	for _, rule := range models {
		signature := 0
		for i, p := range probes {
			signature |= f19Residual(rule, p.cue, p.action) << i
			work++
		}
		buckets[signature]++
	}
	cost := 0
	for _, v := range buckets {
		cost += v * v
	}
	return cost, work + len(buckets)
}

// Action selection sees only actually credited transitions, own pending real
// interventions, current/next public cues and the action step. Never a seed,
// hidden law, post-action outcome or oracle evaluation score.
func f19Select(kind string, credits []f13Credit, pending []f19Probe, cue, nextCue, step int) (int, int, error) {
	if step < 0 || step >= F19Actions || cue < 0 || cue > 3 || nextCue < 0 || nextCue > 3 ||
		len(credits) != max(0, step-1) || len(pending) != min(step, 2) {
		return 0, 0, errF19
	}
	for _, p := range pending {
		if p.cue < 0 || p.cue > 3 || p.action < 0 || p.action > 1 {
			return 0, 0, errF19
		}
	}
	for i, c := range credits {
		if c.Step != i || c.Before < 0 || c.Before > 3 || c.After < 0 || c.After > 3 ||
			c.Cue < 0 || c.Cue > 3 || c.Action < 0 || c.Action > 1 ||
			c.WrongCue < 0 || c.WrongCue > 3 || c.WrongAction < 0 || c.WrongAction > 1 {
			return 0, 0, errF19
		}
	}
	switch kind {
	case "balanced":
		return step & 1, 1, nil
	case "passive":
		return cue & 1, 1, nil
	case "no-intervention":
		return 0, 1, nil
	case "pending-aware", "queue-lookahead", "two-step-ig", "one-step-ig", "thompson", "wrong-credit":
	default:
		return 0, 0, errF19
	}
	models, work := f19Posterior(credits, kind == "wrong-credit")
	if len(models) == 0 {
		return 0, 0, errF19
	}
	if kind == "thompson" {
		index := int(f12Mix(uint32(step+1)*0x9e3779b9^uint32(len(credits)+1)*0x85ebca6b) % uint32(len(models)))
		mask := models[index]
		preferred := 0
		if f19Residual(mask, cue, 1) > f19Residual(mask, cue, 0) {
			preferred = 1
		}
		return preferred, work + 2, nil
	}
	if kind == "one-step-ig" {
		bestCost := int(^uint(0) >> 1)
		selected := 0
		for a := 0; a < 2; a++ {
			value, w := f19Collision(models, []f19Probe{{cue, a}})
			work += w
			if value < bestCost {
				bestCost, selected = value, a
			}
		}
		return selected, work, nil
	}
	base := pending
	if kind == "two-step-ig" {
		base = nil
	}
	bestCost := int(^uint(0) >> 1)
	selected := 0
	bestTie := -1
	for a := 0; a < 2; a++ {
		// The candidate considers only the current choice and already pending
		// probes. The stronger queue-lookahead enumerates future choices too.
		if kind == "pending-aware" || kind == "wrong-credit" {
			probes := make([]f19Probe, 0, len(base)+1)
			probes = append(probes, base...)
			probes = append(probes, f19Probe{cue, a})
			value, w := f19Collision(models, probes)
			work += w
			tie := 0
			if a != (cue & 1) {
				tie = 1
			}
			if value < bestCost || value == bestCost && tie > bestTie {
				bestCost, selected, bestTie = value, a, tie
			}
			continue
		}
		for b := 0; b < 2; b++ {
			probes := make([]f19Probe, 0, len(base)+2)
			probes = append(probes, base...)
			probes = append(probes, f19Probe{cue, a}, f19Probe{nextCue, b})
			value, w := f19Collision(models, probes)
			work += w
			if value < bestCost {
				bestCost, selected = value, a
			}
		}
	}
	return selected, work, nil
}

func f19EstimateScore(credits []f13Credit, wrong bool, trueRule int) (int, int) {
	models, work := f19Posterior(credits, wrong)
	rule := models[0] // predeclared lexicographic MLE, no hidden-law selection
	correct := 0
	for prior := 0; prior < 4; prior++ {
		for cue := 0; cue < 4; cue++ {
			for action := 0; action < 2; action++ {
				if f12Next(rule, prior, 0, cue, action) == f12Next(trueRule, prior, 0, cue, action) {
					correct++
				}
				work += 2
			}
		}
	}
	return correct, work
}

type F19PolicyTrace struct {
	Name              string `json:"name"`
	ActionBits        string `json:"action_bits"`
	ObservationSHA256 string `json:"observation_sha256"`
	G1StateSHA256     string `json:"g1_state_sha256"`
	G2StateSHA256     string `json:"g2_state_sha256"`
	Correct           [4]int `json:"causal_probe_correct"`
	TotalCorrect      int    `json:"total_correct"`
	RuleWork          int    `json:"rule_work"`
	G1Credited        int    `json:"g1_credited"`
	G1Pending         int    `json:"g1_pending"`
	G2Credited        int    `json:"g2_credited"`
	G2Pending         int    `json:"g2_pending"`
	ColdMatches       bool   `json:"cold_matches"`
}

// This simulator is the world/scorer-only component. f19Select is supplied
// only a correctly credited *preview* of the latest delivered consequence.
func f19PolicyRun(seed uint32, schedule, kind string) (F19PolicyTrace, error) {
	trueRule, err := f19WorldRule(seed)
	if err != nil {
		return F19PolicyTrace{}, errF19
	}
	out := F19PolicyTrace{Name: kind}
	m := f13New()
	initial := int(f12Mix(seed^0x125ecafe) & 3)
	state := initial
	after := make([]int, 0, F19Actions)
	events := make([]f12Event, 0, F19Actions)
	steps := [4]int{4, 6, 8, 12}
	for t := 0; t < F19Actions; t++ {
		cue, e := f19Cue(seed, schedule, t)
		if e != nil {
			return F19PolicyTrace{}, errF19
		}
		nextCue, e := f19Cue(seed, schedule, t+1)
		if e != nil {
			return F19PolicyTrace{}, errF19
		}
		delivered := -1
		if t == 1 {
			delivered = initial
		}
		if t >= 2 {
			delivered = after[t-2]
		}
		preview := append([]f13Credit(nil), m.Credits...)
		if t >= 2 {
			p, q := m.Pending[0], m.Pending[1]
			preview = append(preview, f13Credit{Step: p.Step, Before: m.LastDelayed, After: delivered,
				Cue: p.Cue, Action: p.Action, WrongCue: q.Cue, WrongAction: q.Action})
		}
		if len(preview) != max(0, t-1) {
			return F19PolicyTrace{}, errF19
		}
		for i, cut := range steps {
			if t == cut {
				score, scoreWork := f19EstimateScore(preview, kind == "wrong-credit", trueRule)
				out.Correct[i] = score
				out.RuleWork += scoreWork
				out.TotalCorrect += out.Correct[i]
			}
		}
		pending := make([]f19Probe, 0, 2)
		if t == 1 {
			pending = append(pending, f19Probe{m.Pending[1].Cue, m.Pending[1].Action})
		}
		if t >= 2 {
			pending = append(pending,
				f19Probe{m.Pending[0].Cue, m.Pending[0].Action},
				f19Probe{m.Pending[1].Cue, m.Pending[1].Action})
		}
		action, work, e := f19Select(kind, preview, pending, cue, nextCue, t)
		if e != nil || action < 0 || action > 1 || work < 1 {
			return F19PolicyTrace{}, errF19
		}
		out.RuleWork += work
		if action == 0 {
			out.ActionBits += "0"
		} else {
			out.ActionBits += "1"
		}
		event := f12Event{Step: t, Phase: 0, Cue: cue, Action: action, Sensor: state & 1, DelayedState: delivered}
		if m.Observe(event) != nil || !reflect.DeepEqual(m.Credits, append([]f13Credit{}, preview...)) {
			return F19PolicyTrace{}, errF19
		}
		events = append(events, event)
		state = f12Next(trueRule, state, 0, cue, action)
		after = append(after, state)
		if t == 9 {
			out.G1Credited = len(m.Credits)
			out.G1Pending = m.Seen - len(m.Credits)
			snapshot, e := m.Snapshot()
			if e != nil {
				return F19PolicyTrace{}, errF19
			}
			out.G1StateSHA256 = f3Hash(snapshot)
			cold, e := f13Load(snapshot, out.G1StateSHA256)
			if e != nil || !reflect.DeepEqual(m, cold) {
				return F19PolicyTrace{}, errF19
			}
			m = cold
		}
	}
	out.G2Credited = len(m.Credits)
	out.G2Pending = m.Seen - len(m.Credits)
	final, e := m.Snapshot()
	if e != nil {
		return F19PolicyTrace{}, errF19
	}
	out.G2StateSHA256 = f3Hash(final)
	cold, e := f13Load(final, out.G2StateSHA256)
	if e != nil || !reflect.DeepEqual(m, cold) {
		return F19PolicyTrace{}, errF19
	}
	fresh := f13New()
	for _, event := range events {
		if fresh.Observe(event) != nil {
			return F19PolicyTrace{}, errF19
		}
	}
	raw, e := fresh.Snapshot()
	if e != nil || !bytes.Equal(raw, final) || out.G1Credited != 8 || out.G1Pending != 2 ||
		out.G2Credited != 16 || out.G2Pending != 2 || len(out.ActionBits) != F19Actions ||
		len(events) != F19Actions {
		return F19PolicyTrace{}, errF19
	}
	out.ObservationSHA256 = f8Digest("FORGE-EUREKA-F19-REAL-INTERVENTIONS-V1\n", events)
	out.ColdMatches = true
	return out, nil
}

type F19Arm struct {
	Seed                       uint32            `json:"seed"`
	Schedule                   string            `json:"schedule"`
	Policies                   [9]F19PolicyTrace `json:"policies"`
	StrongestControlName       string            `json:"strongest_control_name"`
	StrongestControlCorrect    int               `json:"strongest_control_correct"`
	CandidateNonPassiveActions int               `json:"candidate_non_passive_actions"`
	GainOverStrongest          int               `json:"gain_over_strongest"`
	GainOverNoIntervention     int               `json:"gain_over_no_intervention"`
	GainOverWrongCredit        int               `json:"gain_over_wrong_credit"`
	PassesThreshold            bool              `json:"passes_threshold"`
}

func f19Arm(seed uint32, schedule string) (F19Arm, error) {
	if _, err := f19WorldRule(seed); err != nil {
		return F19Arm{}, errF19
	}
	out := F19Arm{Seed: seed, Schedule: schedule, StrongestControlCorrect: -1}
	for i, kind := range f19Kinds() {
		trace, err := f19PolicyRun(seed, schedule, kind)
		if err != nil {
			return F19Arm{}, errF19
		}
		out.Policies[i] = trace
		if i >= 1 && i <= 6 && trace.TotalCorrect > out.StrongestControlCorrect {
			out.StrongestControlCorrect = trace.TotalCorrect
			out.StrongestControlName = kind
		}
	}
	if out.StrongestControlCorrect < 0 {
		return F19Arm{}, errF19
	}
	for step := 0; step < F19Actions; step++ {
		cue, err := f19Cue(seed, schedule, step)
		if err != nil {
			return F19Arm{}, errF19
		}
		if out.Policies[0].ActionBits[step] != byte('0'+(cue&1)) {
			out.CandidateNonPassiveActions++
		}
	}
	out.GainOverStrongest = out.Policies[0].TotalCorrect - out.StrongestControlCorrect
	out.GainOverNoIntervention = out.Policies[0].TotalCorrect - out.Policies[7].TotalCorrect
	out.GainOverWrongCredit = out.Policies[0].TotalCorrect - out.Policies[8].TotalCorrect
	out.PassesThreshold = out.GainOverStrongest >= F19MinStrongGain &&
		out.GainOverNoIntervention >= F19MinAblationGain &&
		out.GainOverWrongCredit >= F19MinAblationGain && out.CandidateNonPassiveActions >= 2
	for _, p := range out.Policies {
		if !p.ColdMatches {
			out.PassesThreshold = false
		}
	}
	return out, nil
}

type F19Report struct {
	Schema                      string    `json:"schema"`
	ParentF18DigestSHA256       string    `json:"parent_f18_digest_sha256"`
	EarlierNegativesPreserved   bool      `json:"earlier_negatives_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Schedules                   [2]string `json:"schedules"`
	TotalActions                int       `json:"total_actions"`
	FeedbackDelay               int       `json:"feedback_delay"`
	Milestones                  [4]int    `json:"milestones"`
	MaximumScore                int       `json:"maximum_score"`
	MinimumStrongGain           int       `json:"minimum_strong_gain"`
	MinimumAblationGain         int       `json:"minimum_ablation_gain"`
	Arms                        []F19Arm  `json:"arms"`
	PassingArms                 int       `json:"passing_arms"`
	TotalRuleWork               int       `json:"total_rule_work"`
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

func f19Digest(x F19Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F19-FROZEN-ACTIVE-CAUSAL-V1\n", x)
}
func F19Development() (F19Report, error) {
	prev, err := F18Development()
	if err != nil || F18Validate(prev) != nil || prev.Classification != F18NO_GO ||
		prev.ScientificAccepted || prev.OwnerEligible || prev.DispatchAuthorized {
		return F19Report{}, errF19
	}
	out := F19Report{Schema: F19Schema, ParentF18DigestSHA256: prev.DigestSHA256,
		EarlierNegativesPreserved: true, Seeds: f19Seeds(), Schedules: f19Schedules(),
		TotalActions: F19Actions, FeedbackDelay: 2, Milestones: [4]int{4, 6, 8, 12}, MaximumScore: 128,
		MinimumStrongGain: F19MinStrongGain, MinimumAblationGain: F19MinAblationGain,
		Arms: make([]F19Arm, 0, 4), DevelopmentOnly: true}
	for _, seed := range out.Seeds {
		for _, schedule := range out.Schedules {
			arm, e := f19Arm(seed, schedule)
			if e != nil {
				return F19Report{}, errF19
			}
			out.Arms = append(out.Arms, arm)
			if arm.PassesThreshold {
				out.PassingArms++
			}
			for _, p := range arm.Policies {
				out.TotalRuleWork += p.RuleWork
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalRuleWork <= 0 {
		return F19Report{}, errF19
	}
	out.Classification = F19NO_GO
	if out.PassingArms == 4 {
		out.Classification = F19Signal
	}
	out.DigestSHA256 = f19Digest(out)
	return out, nil
}

var f19Reference struct {
	once   sync.Once
	report F19Report
	err    error
}

func F19Validate(x F19Report) error {
	if x.Schema != F19Schema || x.DigestSHA256 != f19Digest(x) ||
		!x.DevelopmentOnly || !x.EarlierNegativesPreserved ||
		x.IndependentFirstUseConsumed || x.ScientificAccepted || x.WholeProcessCostMeasured ||
		x.OwnerEligible || x.DispatchAuthorized || x.ActiveResearchChanged ||
		x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF19
	}
	f19Reference.once.Do(func() { f19Reference.report, f19Reference.err = F19Development() })
	if f19Reference.err != nil || !reflect.DeepEqual(x, f19Reference.report) {
		return errF19
	}
	return nil
}
