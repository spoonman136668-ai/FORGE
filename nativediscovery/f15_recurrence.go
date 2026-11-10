// Eureka F15: development-only recurrent causal mechanism retrieval.
// All planners receive the same credited two-step delayed observations.
package nativediscovery

import (
	"bytes"
	"errors"
	"reflect"
	"sync"
)

const (
	F15Schema          = "forge.native-discovery.recurrent-causal-memory.dev.v1"
	F15ReturnStep      = 49
	F15MiddleStep      = 33
	F15Actions         = 60
	F15MinStrongGain   = 4
	F15MinAblationGain = 8
	F15NoGo            = "F15_DEV_NO_GO"
	F15Signal          = "F15_DEV_SIGNAL_UNVERIFIED"
)

var errF15 = errors.New("FORGE_EUREKA_F15_RECURRENT_MEMORY_INVALID")

// The hidden rule schedule is owned only by the synthetic development world.
// Learners receive neither the rule ID nor either switch boundary.
func f15Generate(seed uint32, policy string) ([]f12Event, error) {
	before, middle, err := f13Rules(seed)
	if err != nil || policy != "fixed" && policy != "random" {
		return nil, errF15
	}
	state := int(f12Mix(seed^0x125ecafe) & 3)
	initial := state
	history := make([]int, 0, F15Actions)
	events := make([]f12Event, 0, F15Actions)
	for step := 0; step < F15Actions; step++ {
		action, err := f13Action(seed, policy, step)
		if err != nil {
			return nil, errF15
		}
		cue := f12Cue(seed, step, 0)
		delayed := -1
		if step == 1 {
			delayed = initial
		}
		if step >= 2 {
			delayed = history[step-2]
		}
		events = append(events, f12Event{Step: step, Phase: 0, Cue: cue,
			Action: action, Sensor: state & 1, DelayedState: delayed})
		rule := before
		if step >= F15MiddleStep && step < F15ReturnStep {
			rule = middle
		}
		state = f12Next(rule, state, 0, cue, action)
		history = append(history, state)
	}
	return events, nil
}

// Frozen candidate: remember high-confidence mechanisms from earlier disjoint
// eight-credit windows, then identify a returning law using only the latest
// four genuinely credited action consequences. There is no rule oracle.
func f15BankRule(records []f13Credit, wrongLag bool) (int, int) {
	var archive [F12RuleCount]bool
	work := 0
	for start := 0; start+8 <= len(records); start += 8 {
		best, hits := f13Best(records[start:start+8], wrongLag, false)
		work += F12RuleCount * 8
		if hits >= 7 {
			archive[best] = true
		}
	}
	recent := f13Recent(records, 4)
	rule, peak := 0, -1
	found := false
	for i, saved := range archive {
		if !saved {
			continue
		}
		found = true
		hits := 0
		for _, rec := range recent {
			if f13Match(i, rec, wrongLag) {
				hits++
			}
		}
		work += len(recent)
		if hits > peak {
			rule, peak = i, hits
		}
	}
	if !found {
		rule, _ = f13Best(recent, wrongLag, false)
		work += F12RuleCount * len(recent)
	}
	return rule, work
}

// Strong conventional comparator: penalized best one/two-change-point
// maximum likelihood over the entire credited 16-rule sequence.
// All split locations are inferred from observations, never from the world.
func f15SwitchingRule(records []f13Credit) (int, int) {
	n := len(records)
	var prefix [F12RuleCount][F15Actions + 1]int
	work := 0
	for rule := 0; rule < F12RuleCount; rule++ {
		for i, rec := range records {
			prefix[rule][i+1] = prefix[rule][i]
			if f13Match(rule, rec, false) {
				prefix[rule][i+1]++
			}
			work++
		}
	}
	bestSegment := func(a, b int) (int, int) {
		rule, peak := 0, -1
		for r := 0; r < F12RuleCount; r++ {
			hits := prefix[r][b] - prefix[r][a]
			if hits > peak {
				rule, peak = r, hits
			}
			work++
		}
		return rule, peak
	}
	chosen, score := bestSegment(0, n)
	// Each additional regime pays a fixed three-correct-transition penalty.
	for split := 4; split <= n-4; split++ {
		_, left := bestSegment(0, split)
		rightRule, right := bestSegment(split, n)
		if value := left + right - 3; value > score {
			chosen, score = rightRule, value
		}
	}
	for first := 4; first <= n-8; first++ {
		_, left := bestSegment(0, first)
		for second := first + 4; second <= n-4; second++ {
			_, middle := bestSegment(first, second)
			rightRule, right := bestSegment(second, n)
			if value := left + middle + right - 6; value > score {
				chosen, score = rightRule, value
			}
		}
	}
	return chosen, work
}

func f15Kinds() [9]string {
	return [9]string{"memory-bank", "full-mle", "rolling4-mle", "rolling8-mle",
		"rolling16-mle", "switching-mle", "table", "no-bank", "wrong-credit"}
}
func f15Fit(kind string, records []f13Credit) (int, int, error) {
	if len(records) < 8 || len(records) > F15Actions-2 {
		return 0, 0, errF15
	}
	switch kind {
	case "memory-bank":
		r, w := f15BankRule(records, false)
		return r, w, nil
	case "wrong-credit":
		r, w := f15BankRule(records, true)
		return r, w, nil
	case "switching-mle":
		r, w := f15SwitchingRule(records)
		return r, w, nil
	case "table":
		return 0, 0, nil
	case "full-mle", "rolling4-mle", "rolling8-mle", "rolling16-mle", "no-bank":
		used := records
		switch kind {
		case "rolling4-mle", "no-bank":
			used = f13Recent(records, 4)
		case "rolling8-mle":
			used = f13Recent(records, 8)
		case "rolling16-mle":
			used = f13Recent(records, 16)
		}
		rule, _ := f13Best(used, false, false)
		return rule, F12RuleCount * len(used), nil
	}
	return 0, 0, errF15
}
func f15Score(kind string, m *f13Notebook, seed uint32, changed bool) (int, int, error) {
	if m == nil || m.Validate() != nil {
		return 0, 0, errF15
	}
	rule, work, err := f15Fit(kind, m.Credits)
	if err != nil {
		return 0, 0, errF15
	}
	correct := 0
	for episode := 0; episode < 8; episode++ {
		events, after, err := f13Evaluation(seed, episode, changed)
		if err != nil {
			return 0, 0, errF15
		}
		for step := 2; step < 10; step++ {
			last, current := events[step-1], events[step]
			predicted := 0
			if kind == "table" {
				mid := f13Table(m.Credits, current.DelayedState, last.Cue, last.Action)
				predicted = f13Table(m.Credits, mid, current.Cue, current.Action)
				work += len(m.Credits) * 2
			} else {
				mid := f12Next(rule, current.DelayedState, 0, last.Cue, last.Action)
				predicted = f12Next(rule, mid, 0, current.Cue, current.Action)
				work += 2
			}
			if predicted == after[step] {
				correct++
			}
		}
	}
	if correct < 0 || correct > 64 {
		return 0, 0, errF15
	}
	return correct, work, nil
}

type F15Round struct {
	Generation               int    `json:"generation"`
	ActionsSeen              int    `json:"actions_seen"`
	CreditedConsequences     int    `json:"credited_consequences"`
	PendingConsequences      int    `json:"pending_consequences"`
	SnapshotSHA256           string `json:"snapshot_sha256"`
	ColdStateMatches         bool   `json:"cold_state_matches"`
	ReturnCorrect            [9]int `json:"returned_world_correct"`
	MiddleCorrect            [9]int `json:"middle_world_correct"`
	StrongestCorrect         int    `json:"strongest_control_correct"`
	StrongestName            string `json:"strongest_control_name"`
	AdvantageOverStrongest   int    `json:"advantage_over_strongest"`
	AdvantageOverNoBank      int    `json:"advantage_over_no_bank"`
	AdvantageOverWrongCredit int    `json:"advantage_over_wrong_credit"`
	RuleWorkChecks           int    `json:"rule_work_checks"`
}
type F15Arm struct {
	Seed                  uint32      `json:"seed"`
	Policy                string      `json:"policy"`
	TraceSHA256           string      `json:"trace_sha256"`
	Rounds                [2]F15Round `json:"rounds"`
	ReturningLawRetained  bool        `json:"returning_law_retained"`
	PassesFrozenThreshold bool        `json:"passes_frozen_threshold"`
}
type F15Report struct {
	Schema                      string    `json:"schema"`
	ParentF13DigestSHA256       string    `json:"parent_f13_digest_sha256"`
	F13NegativePreserved        bool      `json:"f13_negative_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Policies                    [2]string `json:"policies"`
	FirstSwitchStep             int       `json:"first_switch_step"`
	ReturnStep                  int       `json:"return_step"`
	ActionsPerArm               int       `json:"actions_per_arm"`
	DelaySteps                  int       `json:"delay_steps"`
	MinimumStrongGain           int       `json:"minimum_strong_gain"`
	MinimumAblationGain         int       `json:"minimum_ablation_gain"`
	Arms                        []F15Arm  `json:"arms"`
	PassingArms                 int       `json:"passing_arms"`
	TotalRuleWorkChecks         int       `json:"total_rule_work_checks"`
	Classification              string    `json:"classification"`
	DevelopmentOnly             bool      `json:"development_only"`
	IndependentFirstUseConsumed bool      `json:"independent_first_use_consumed"`
	ScientificAccepted          bool      `json:"scientific_accepted"`
	FullProcessEfficiencyProven bool      `json:"full_process_efficiency_proven"`
	OwnerEligible               bool      `json:"owner_eligible"`
	DispatchAuthorized          bool      `json:"dispatch_authorized"`
	ActiveResearchChanged       bool      `json:"active_research_changed"`
	AgentCalls                  int       `json:"agent_calls"`
	PaidAPICalls                int       `json:"paid_api_calls"`
	DigestSHA256                string    `json:"digest_sha256"`
}

func f15Digest(x F15Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F15-RECURRENT-CAUSAL-MEMORY-V1\n", x)
}
func f15Arm(seed uint32, policy string) (F15Arm, error) {
	trace, err := f15Generate(seed, policy)
	if err != nil || len(trace) != F15Actions {
		return F15Arm{}, errF15
	}
	arm := F15Arm{Seed: seed, Policy: policy,
		TraceSHA256: f8Digest("FORGE-EUREKA-F15-OBSERVATIONS-V1\n", trace)}
	notebook := f13New()
	for generation, cut := range [2]int{54, 60} {
		begin := 0
		if generation == 1 {
			begin = 54
		}
		for _, event := range trace[begin:cut] {
			if err := notebook.Observe(event); err != nil {
				return F15Arm{}, errF15
			}
		}
		snapshot, err := notebook.Snapshot()
		if err != nil {
			return F15Arm{}, errF15
		}
		hash := f3Hash(snapshot)
		cold, err := f13Load(snapshot, hash)
		if err != nil || !reflect.DeepEqual(notebook, cold) {
			return F15Arm{}, errF15
		}
		fresh := f13New()
		for _, event := range trace[:cut] {
			if fresh.Observe(event) != nil {
				return F15Arm{}, errF15
			}
		}
		replay, err := fresh.Snapshot()
		if err != nil || !bytes.Equal(snapshot, replay) {
			return F15Arm{}, errF15
		}
		round := F15Round{Generation: generation + 1, ActionsSeen: cut,
			CreditedConsequences: cut - 2, PendingConsequences: 2,
			SnapshotSHA256: hash, ColdStateMatches: true}
		for i, kind := range f15Kinds() {
			var cost int
			round.ReturnCorrect[i], cost, err = f15Score(kind, cold, seed, false)
			if err != nil {
				return F15Arm{}, errF15
			}
			round.RuleWorkChecks += cost
			round.MiddleCorrect[i], cost, err = f15Score(kind, cold, seed, true)
			if err != nil {
				return F15Arm{}, errF15
			}
			round.RuleWorkChecks += cost
		}
		for i := 1; i <= 6; i++ {
			if round.ReturnCorrect[i] > round.StrongestCorrect {
				round.StrongestCorrect = round.ReturnCorrect[i]
				round.StrongestName = f15Kinds()[i]
			}
		}
		round.AdvantageOverStrongest = round.ReturnCorrect[0] - round.StrongestCorrect
		round.AdvantageOverNoBank = round.ReturnCorrect[0] - round.ReturnCorrect[7]
		round.AdvantageOverWrongCredit = round.ReturnCorrect[0] - round.ReturnCorrect[8]
		arm.Rounds[generation] = round
		notebook = cold
	}
	first, second := arm.Rounds[0], arm.Rounds[1]
	arm.ReturningLawRetained = second.ReturnCorrect[0] >= first.ReturnCorrect[0]
	arm.PassesFrozenThreshold = arm.ReturningLawRetained && second.ColdStateMatches &&
		second.AdvantageOverStrongest >= F15MinStrongGain &&
		second.AdvantageOverNoBank >= F15MinAblationGain &&
		second.AdvantageOverWrongCredit >= F15MinAblationGain
	return arm, nil
}
func F15Development() (F15Report, error) {
	parent, err := F13Development()
	if err != nil || F13Validate(parent) != nil || parent.Classification != F13NO_GO ||
		parent.OwnerEligible || parent.ScientificAccepted || parent.DispatchAuthorized {
		return F15Report{}, errF15
	}
	out := F15Report{Schema: F15Schema, ParentF13DigestSHA256: parent.DigestSHA256,
		F13NegativePreserved: true, Seeds: f13Seeds(), Policies: f13Policies(),
		FirstSwitchStep: F15MiddleStep, ReturnStep: F15ReturnStep,
		ActionsPerArm: F15Actions, DelaySteps: F13Delay,
		MinimumStrongGain: F15MinStrongGain, MinimumAblationGain: F15MinAblationGain,
		Arms: make([]F15Arm, 0, 4), DevelopmentOnly: true}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			arm, err := f15Arm(seed, policy)
			if err != nil {
				return F15Report{}, errF15
			}
			out.Arms = append(out.Arms, arm)
			for _, round := range arm.Rounds {
				out.TotalRuleWorkChecks += round.RuleWorkChecks
			}
			if arm.PassesFrozenThreshold {
				out.PassingArms++
			}
		}
	}
	if len(out.Arms) != 4 {
		return F15Report{}, errF15
	}
	out.Classification = F15NoGo
	if out.PassingArms == 4 {
		out.Classification = F15Signal
	}
	out.DigestSHA256 = f15Digest(out)
	return out, nil
}
func F15Validate(x F15Report) error {
	if x.Schema != F15Schema || x.DigestSHA256 != f15Digest(x) ||
		!x.DevelopmentOnly || !x.F13NegativePreserved ||
		x.IndependentFirstUseConsumed || x.ScientificAccepted ||
		x.FullProcessEfficiencyProven || x.OwnerEligible || x.DispatchAuthorized ||
		x.ActiveResearchChanged || x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF15
	}
	// Reference is computed once per exact compiled source. Every candidate
	// (including forged, rehashed negatives) still receives the complete,
	// field-by-field comparison; the shared reference never escapes.
	f15ValidatedReference.once.Do(func() {
		f15ValidatedReference.report, f15ValidatedReference.err = F15Development()
	})
	if f15ValidatedReference.err != nil ||
		!reflect.DeepEqual(x, f15ValidatedReference.report) {
		return errF15
	}
	return nil
}

var f15ValidatedReference struct {
	once   sync.Once
	report F15Report
	err    error
}