// Eureka F18: predeclared compositional causal transfer to an unseen raw context.
// Synthetic development only; never a production research or owner admission path.
package nativediscovery

import (
	"errors"
	"reflect"
	"sync"
)

const (
	F18Schema          = "forge.native-discovery.causal-composition-transfer.dev.v1"
	F18NO_GO           = "F18_DEV_NO_GO"
	F18Signal          = "F18_DEV_SIGNAL_UNVERIFIED"
	F18SourceActions   = 18
	F18TargetActions   = 12
	F18MinStrongGain   = 2
	F18MinAblationGain = 2
)

var errF18 = errors.New("FORGE_EUREKA_F18_SOURCE_OR_AUTHORITY_INVALID")

func f18Seeds() [2]uint32    { return [2]uint32{101, 103} }
func f18Policies() [2]string { return [2]string{"fixed", "random"} }

// Hidden causal laws are exclusively a responsibility of world generation.
// Neither fit nor forecast receives seed, law IDs, or the hidden coefficients.
func f18World(seed uint32) (base, a, b int, err error) {
	switch seed {
	case 101:
		return 1, 2, 8, nil
	case 103:
		return 10, 1, 2, nil
	default:
		return 0, 0, 0, errF18
	}
}
func f18Action(seed uint32, policy string, context, step int) (int, error) {
	if _, _, _, err := f18World(seed); err != nil || context < 0 || context > 3 || step < 0 ||
		(context < 3 && step >= F18SourceActions) || (context == 3 && step >= F18TargetActions) {
		return 0, errF18
	}
	switch policy {
	case "fixed":
		return step & 1, nil
	case "random":
		return int(f12Mix(seed^uint32(context+1)*0x9e3779b9^uint32(step+17)*0x85ebca6b) & 1), nil
	default:
		return 0, errF18
	}
}
func f18Generate(seed uint32, policy string, context int) ([]f12Event, error) {
	base, a, b, err := f18World(seed)
	if err != nil || context < 0 || context > 3 || (policy != "fixed" && policy != "random") {
		return nil, errF18
	}
	law := base
	if context&1 != 0 {
		law ^= a
	}
	if context&2 != 0 {
		law ^= b
	}
	length := F18SourceActions
	if context == 3 {
		length = F18TargetActions
	}
	state := int(f12Mix(seed^uint32(context+1)*0x7f4a7c15^0x125ecafe) & 3)
	initial := state
	past := make([]int, 0, length)
	out := make([]f12Event, 0, length)
	for step := 0; step < length; step++ {
		action, e := f18Action(seed, policy, context, step)
		if e != nil {
			return nil, errF18
		}
		delayed := -1
		if step == 1 {
			delayed = initial
		}
		if step >= 2 {
			delayed = past[step-2]
		}
		cue := f12Cue(seed, step, context)
		out = append(out, f12Event{Step: step, Phase: 0, Cue: cue, Action: action, Sensor: state & 1, DelayedState: delayed})
		state = f12Next(law, state, 0, cue, action)
		past = append(past, state)
	}
	return out, nil
}

// Rule IDs are full original 16-hypothesis masks with the unobservable
// phase-bit excluded: eight identifiable mechanisms, no target law oracle.
func f18Masks() [8]int { return [8]int{0, 1, 2, 3, 8, 9, 10, 11} }
func f18Composite(sources [3][]f13Credit, noAction, wrongLag bool) (int, int) {
	var fitted [3]int
	work := 0
	for i, records := range sources {
		fitted[i], _ = f13Best(records, wrongLag, noAction)
		work += F12RuleCount * len(records)
	}
	return fitted[0] ^ fitted[1] ^ fitted[2], work
}

// The decisive conventional control: exhaustive same-class source MLE,
// explicitly including all task contexts, not a deliberately weak comparator.
func f18JointMLE(sources [3][]f13Credit) (int, int) {
	masks := f18Masks()
	best, score, work := 0, -1, 0
	for _, base := range masks {
		for _, a := range masks {
			for _, b := range masks {
				laws := [3]int{base, base ^ a, base ^ b}
				hits := 0
				for i, records := range sources {
					for _, record := range records {
						if f13Match(laws[i], record, false) {
							hits++
						}
						work++
					}
				}
				if hits > score {
					best, score = base^a^b, hits
				}
			}
		}
	}
	return best, work
}
func f18Kinds() [9]string {
	return [9]string{"composite", "joint-context-mle", "nearest-source-mle", "pooled-source-mle",
		"target-online-mle", "source-plus-target-mle", "context-blind-table", "no-action", "wrong-credit"}
}
func f18Forecast(kind string, sources [3][]f13Credit, target []f13Credit, last, current f12Event) (int, int, error) {
	if current.Step < 2 || current.Step >= 10 || last.Step != current.Step-1 ||
		len(target) != current.Step-1 || current.Phase != 0 || last.Phase != 0 ||
		current.DelayedState < 0 || current.DelayedState > 3 ||
		last.Action < 0 || last.Action > 1 || current.Action < 0 || current.Action > 1 ||
		last.Cue < 0 || last.Cue >= 4 || current.Cue < 0 || current.Cue >= 4 {
		return 0, 0, errF18
	}
	for _, records := range sources {
		if len(records) != F18SourceActions-2 {
			return 0, 0, errF18
		}
	}
	work, rule := 0, 0
	var all []f13Credit
	switch kind {
	case "composite", "no-action", "wrong-credit":
		rule, work = f18Composite(sources, kind == "no-action", kind == "wrong-credit")
	case "joint-context-mle":
		rule, work = f18JointMLE(sources)
	case "nearest-source-mle":
		rule, _ = f13Best(sources[1], false, false)
		work = F12RuleCount * len(sources[1])
	case "pooled-source-mle", "source-plus-target-mle", "context-blind-table":
		for _, records := range sources {
			all = append(all, records...)
		}
		if kind == "source-plus-target-mle" || kind == "context-blind-table" {
			all = append(all, target...)
		}
		if kind != "context-blind-table" {
			rule, _ = f13Best(all, false, false)
			work = F12RuleCount * len(all)
		}
	case "target-online-mle":
		rule, _ = f13Best(target, false, false)
		work = F12RuleCount * len(target)
	default:
		return 0, 0, errF18
	}
	if kind == "context-blind-table" {
		middle := f13Table(all, current.DelayedState, last.Cue, last.Action)
		return f13Table(all, middle, current.Cue, current.Action), 2 * len(all), nil
	}
	middle := f12Next(rule, current.DelayedState, 0, last.Cue, last.Action)
	return f12Next(rule, middle, 0, current.Cue, current.Action), work + 2, nil
}

type F18Arm struct {
	Seed                 uint32    `json:"seed"`
	Policy               string    `json:"policy"`
	SourceTraceSHA256    [3]string `json:"source_trace_sha256"`
	SourceStateSHA256    [3]string `json:"source_state_sha256"`
	SourceCredited       [3]int    `json:"source_credited"`
	SourcePending        [3]int    `json:"source_pending"`
	SourceCorrect        [3]int    `json:"source_rule_fits"`
	TargetTraceSHA256    string    `json:"target_trace_sha256"`
	TargetStateSHA256    string    `json:"target_state_sha256"`
	TargetCredited       int       `json:"target_credited"`
	TargetPending        int       `json:"target_pending"`
	ColdMatches          bool      `json:"cold_matches"`
	Score                [9]int    `json:"score"`
	CorrectTrace         [9]string `json:"correct_trace"`
	RuleWork             [9]int    `json:"rule_work"`
	StrongestName        string    `json:"strongest_name"`
	StrongestScore       int       `json:"strongest_score"`
	AdvantageStrongest   int       `json:"advantage_strongest"`
	AdvantageNoAction    int       `json:"advantage_no_action"`
	AdvantageWrongCredit int       `json:"advantage_wrong_credit"`
	RecoveryOffset       int       `json:"recovery_offset"`
	FastestControlOffset int       `json:"fastest_control_offset"`
	PassesThreshold      bool      `json:"passes_threshold"`
}

func f18Recovery(bits string) int {
	if len(bits) != 8 {
		return 8
	}
	for i := 0; i <= 5; i++ {
		if bits[i:i+3] == "111" {
			return i
		}
	}
	return 8
}
func f18Arm(seed uint32, policy string) (F18Arm, error) {
	arm := F18Arm{Seed: seed, Policy: policy}
	var sources [3][]f13Credit
	for context := 0; context < 3; context++ {
		events, err := f18Generate(seed, policy, context)
		if err != nil || len(events) != F18SourceActions {
			return F18Arm{}, errF18
		}
		arm.SourceTraceSHA256[context] = f8Digest("FORGE-EUREKA-F18-SOURCE-OBSERVATIONS-V1\n", events)
		m := f13New()
		for _, e := range events {
			if m.Observe(e) != nil {
				return F18Arm{}, errF18
			}
		}
		arm.SourceCredited[context] = len(m.Credits)
		arm.SourcePending[context] = m.Seen - len(m.Credits)
		bytes, err := m.Snapshot()
		if err != nil {
			return F18Arm{}, errF18
		}
		sha := f3Hash(bytes)
		arm.SourceStateSHA256[context] = sha
		cold, err := f13Load(bytes, sha)
		if err != nil || !reflect.DeepEqual(cold, m) {
			return F18Arm{}, errF18
		}
		sources[context] = append([]f13Credit(nil), cold.Credits...)
		_, hits := f13Best(sources[context], false, false)
		arm.SourceCorrect[context] = hits
	}
	events, err := f18Generate(seed, policy, 3)
	if err != nil || len(events) != F18TargetActions {
		return F18Arm{}, errF18
	}
	arm.TargetTraceSHA256 = f8Digest("FORGE-EUREKA-F18-TARGET-OBSERVATIONS-V1\n", events)
	m := f13New()
	for step, e := range events {
		if m.Observe(e) != nil {
			return F18Arm{}, errF18
		}
		if step < 2 || step > 9 {
			continue
		}
		target := events[step+2].DelayedState // scorer ONLY: never passed to a learner
		if target < 0 || target > 3 {
			return F18Arm{}, errF18
		}
		for k, kind := range f18Kinds() {
			guess, cost, e := f18Forecast(kind, sources, m.Credits, events[step-1], events[step])
			if e != nil || cost <= 0 || guess < 0 || guess > 3 {
				return F18Arm{}, errF18
			}
			arm.RuleWork[k] += cost
			if guess == target {
				arm.Score[k]++
				arm.CorrectTrace[k] += "1"
			} else {
				arm.CorrectTrace[k] += "0"
			}
		}
	}
	arm.TargetCredited = len(m.Credits)
	arm.TargetPending = m.Seen - len(m.Credits)
	checkpoint, err := m.Snapshot()
	if err != nil {
		return F18Arm{}, errF18
	}
	arm.TargetStateSHA256 = f3Hash(checkpoint)
	cold, err := f13Load(checkpoint, arm.TargetStateSHA256)
	if err != nil || !reflect.DeepEqual(cold, m) {
		return F18Arm{}, errF18
	}
	arm.ColdMatches = true
	for _, n := range arm.SourceCredited {
		if n != 16 {
			return F18Arm{}, errF18
		}
	}
	for _, n := range arm.SourcePending {
		if n != 2 {
			return F18Arm{}, errF18
		}
	}
	if arm.TargetCredited != 10 || arm.TargetPending != 2 {
		return F18Arm{}, errF18
	}
	for i := range arm.Score {
		if len(arm.CorrectTrace[i]) != 8 || arm.Score[i] < 0 || arm.Score[i] > 8 || arm.RuleWork[i] <= 0 {
			return F18Arm{}, errF18
		}
	}
	arm.StrongestScore = -1
	arm.FastestControlOffset = 8
	for i := 1; i <= 6; i++ {
		if arm.Score[i] > arm.StrongestScore {
			arm.StrongestScore = arm.Score[i]
			arm.StrongestName = f18Kinds()[i]
		}
		if offset := f18Recovery(arm.CorrectTrace[i]); offset < arm.FastestControlOffset {
			arm.FastestControlOffset = offset
		}
	}
	arm.AdvantageStrongest = arm.Score[0] - arm.StrongestScore
	arm.AdvantageNoAction = arm.Score[0] - arm.Score[7]
	arm.AdvantageWrongCredit = arm.Score[0] - arm.Score[8]
	arm.RecoveryOffset = f18Recovery(arm.CorrectTrace[0])
	arm.PassesThreshold = arm.ColdMatches && arm.AdvantageStrongest >= F18MinStrongGain &&
		arm.AdvantageNoAction >= F18MinAblationGain && arm.AdvantageWrongCredit >= F18MinAblationGain &&
		arm.RecoveryOffset <= arm.FastestControlOffset
	for _, n := range arm.SourceCorrect {
		if n < 14 {
			arm.PassesThreshold = false
		}
	}
	return arm, nil
}

type F18Report struct {
	Schema                      string    `json:"schema"`
	ParentF17DigestSHA256       string    `json:"parent_f17_digest_sha256"`
	EarlierNegativesPreserved   bool      `json:"earlier_negatives_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Policies                    [2]string `json:"policies"`
	SourceContexts              [3]int    `json:"source_contexts"`
	TargetContext               int       `json:"target_context"`
	SourceActions               int       `json:"source_actions"`
	TargetActions               int       `json:"target_actions"`
	ScoredPredictions           int       `json:"scored_predictions"`
	MinimumStrongGain           int       `json:"minimum_strong_gain"`
	MinimumAblationGain         int       `json:"minimum_ablation_gain"`
	Arms                        []F18Arm  `json:"arms"`
	PassingArms                 int       `json:"passing_arms"`
	TotalRuleWork               int       `json:"total_rule_work"`
	Classification              string    `json:"classification"`
	DevelopmentOnly             bool      `json:"development_only"`
	IndependentFirstUseConsumed bool      `json:"independent_first_use_consumed"`
	ScientificAccepted          bool      `json:"scientific_accepted"`
	WholeProcessCostMeasured    bool      `json:"whole_process_cost_measured"`
	OwnerEligible               bool      `json:"owner_eligible"`
	DispatchAuthorized          bool      `json:"dispatch_authorized"`
	LiveResearchChanged         bool      `json:"live_research_changed"`
	AgentCalls                  int       `json:"agent_calls"`
	PaidAPICalls                int       `json:"paid_api_calls"`
	DigestSHA256                string    `json:"digest_sha256"`
}

func f18Digest(v F18Report) string {
	v.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F18-COMPOSITION-TRANSFER-V1\n", v)
}
func F18Development() (F18Report, error) {
	previous, err := F17Development()
	if err != nil || F17Validate(previous) != nil || previous.Classification != F17NO_GO ||
		previous.ScientificAccepted || previous.OwnerEligible || previous.DispatchAuthorized {
		return F18Report{}, errF18
	}
	out := F18Report{Schema: F18Schema, ParentF17DigestSHA256: previous.DigestSHA256,
		EarlierNegativesPreserved: true, Seeds: f18Seeds(), Policies: f18Policies(),
		SourceContexts: [3]int{0, 1, 2}, TargetContext: 3, SourceActions: F18SourceActions,
		TargetActions: F18TargetActions, ScoredPredictions: 8, MinimumStrongGain: F18MinStrongGain,
		MinimumAblationGain: F18MinAblationGain, DevelopmentOnly: true, Arms: make([]F18Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			arm, err := f18Arm(seed, policy)
			if err != nil {
				return F18Report{}, errF18
			}
			out.Arms = append(out.Arms, arm)
			for _, n := range arm.RuleWork {
				out.TotalRuleWork += n
			}
			if arm.PassesThreshold {
				out.PassingArms++
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalRuleWork <= 0 {
		return F18Report{}, errF18
	}
	out.Classification = F18NO_GO
	if out.PassingArms == 4 {
		out.Classification = F18Signal
	}
	out.DigestSHA256 = f18Digest(out)
	return out, nil
}

var f18Reference struct {
	once   sync.Once
	report F18Report
	err    error
}

func F18Validate(v F18Report) error {
	if v.Schema != F18Schema || v.DigestSHA256 != f18Digest(v) || !v.DevelopmentOnly ||
		!v.EarlierNegativesPreserved || v.IndependentFirstUseConsumed || v.ScientificAccepted ||
		v.WholeProcessCostMeasured || v.OwnerEligible || v.DispatchAuthorized ||
		v.LiveResearchChanged || v.AgentCalls != 0 || v.PaidAPICalls != 0 {
		return errF18
	}
	f18Reference.once.Do(func() { f18Reference.report, f18Reference.err = F18Development() })
	if f18Reference.err != nil || !reflect.DeepEqual(v, f18Reference.report) {
		return errF18
	}
	return nil
}
