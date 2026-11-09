// Eureka F16: pre-registered online A->B->A recovery with delayed causal credit.
// DEV only: no first-use, owner dispatch, new model process or research-loop mutation.
package nativediscovery

import (
	"bytes"
	"errors"
	"reflect"
)

const (
	F16Schema          = "forge.native-discovery.online-return-recovery.dev.v1"
	F16MiddleStep      = 18
	F16ReturnStep      = 47
	F16Actions         = 60
	F16MinReturnGain   = 2
	F16MinLatencyGain  = 2
	F16MinAblationGain = 2
	F16NO_GO           = "F16_DEV_NO_GO"
	F16Signal          = "F16_DEV_SIGNAL_UNVERIFIED"
)

var errF16 = errors.New("FORGE_EUREKA_F16_SOURCE_OR_AUTHORITY_INVALID")

// A synthetic world with a different predeclared history ratio from F15.
// Only world generation knows the hidden rule. Every learner sees Phase=0.
func f16Generate(seed uint32, policy string) ([]f12Event, error) {
	a, b, err := f13Rules(seed)
	if err != nil || policy != "fixed" && policy != "random" {
		return nil, errF16
	}
	state := int(f12Mix(seed^0x125ecafe) & 3)
	initial := state
	past := make([]int, 0, F16Actions)
	events := make([]f12Event, 0, F16Actions)
	for step := 0; step < F16Actions; step++ {
		action, e := f13Action(seed, policy, step)
		if e != nil {
			return nil, errF16
		}
		delayed := -1
		if step == 1 {
			delayed = initial
		}
		if step >= F13Delay {
			delayed = past[step-F13Delay]
		}
		cue := f12Cue(seed, step, 0)
		events = append(events, f12Event{Step: step, Phase: 0, Cue: cue,
			Action: action, Sensor: state & 1, DelayedState: delayed})
		rule := a
		if step >= F16MiddleStep && step < F16ReturnStep {
			rule = b
		}
		state = f12Next(rule, state, 0, cue, action)
		past = append(past, state)
	}
	return events, nil
}

// Deliberately NO seed, world-generator, future event or expected label argument.
// At action t the model knows only the credited state after t-2 and actions
// t-1 and t. The existing F15 candidate/strong baselines remain unchanged.
func f16Forecast(kind string, m *f13Notebook, last, current f12Event) (int, int, error) {
	if m == nil || m.Validate() != nil || m.Seen != current.Step+1 ||
		current.Step < 2 || current.Step != last.Step+1 ||
		current.DelayedState < 0 || current.DelayedState > 3 ||
		current.Phase != 0 || last.Phase != 0 ||
		last.Cue < 0 || last.Cue >= 4 || current.Cue < 0 || current.Cue >= 4 ||
		last.Action < 0 || last.Action > 1 || current.Action < 0 || current.Action > 1 {
		return 0, 0, errF16
	}
	rule, work, err := f15Fit(kind, m.Credits)
	if err != nil {
		return 0, 0, errF16
	}
	if kind == "table" {
		mid := f13Table(m.Credits, current.DelayedState, last.Cue, last.Action)
		return f13Table(m.Credits, mid, current.Cue, current.Action), work + 2*len(m.Credits), nil
	}
	mid := f12Next(rule, current.DelayedState, 0, last.Cue, last.Action)
	return f12Next(rule, mid, 0, current.Cue, current.Action), work + 2, nil
}

type F16Window struct {
	Name         string    `json:"name"`
	FirstAction  int       `json:"first_action"`
	LastAction   int       `json:"last_action"`
	Trials       int       `json:"trials"`
	Correct      [9]int    `json:"correct"`
	CorrectTrace [9]string `json:"correct_trace"`
	RuleWork     [9]int    `json:"rule_work"`
}

func f16Windows() [3]F16Window {
	return [3]F16Window{
		{Name: "original-A", FirstAction: 9, LastAction: 17, Trials: 9},
		{Name: "middle-B", FirstAction: 36, LastAction: 46, Trials: 11},
		{Name: "returned-A", FirstAction: 47, LastAction: 57, Trials: 11},
	}
}
func f16RecoveryOffset(trace string) int {
	if len(trace) != 11 {
		return 11
	}
	for i := 0; i <= 8; i++ {
		if trace[i:i+3] == "111" {
			return i
		}
	}
	return 11
}
func f16Strongest(win F16Window) (int, string, int) {
	score, kind, latency := -1, "", 11
	for i := 1; i <= 6; i++ {
		if win.Correct[i] > score {
			score, kind = win.Correct[i], f15Kinds()[i]
		}
		if win.Name == "returned-A" {
			v := f16RecoveryOffset(win.CorrectTrace[i])
			if v < latency {
				latency = v
			}
		}
	}
	return score, kind, latency
}

type F16Arm struct {
	Seed                         uint32       `json:"seed"`
	Policy                       string       `json:"policy"`
	TraceSHA256                  string       `json:"trace_sha256"`
	Windows                      [3]F16Window `json:"windows"`
	G1SnapshotSHA256             string       `json:"g1_snapshot_sha256"`
	G2SnapshotSHA256             string       `json:"g2_snapshot_sha256"`
	G1Credited                   int          `json:"g1_credited"`
	G2Credited                   int          `json:"g2_credited"`
	G1Pending                    int          `json:"g1_pending"`
	G2Pending                    int          `json:"g2_pending"`
	ColdContinuationMatches      bool         `json:"cold_continuation_matches"`
	StrongestReturnScore         int          `json:"strongest_return_score"`
	StrongestReturnName          string       `json:"strongest_return_name"`
	FastestControlRecoveryOffset int          `json:"fastest_control_recovery_offset"`
	CandidateRecoveryOffset      int          `json:"candidate_recovery_offset"`
	AdvantageOverStrongest       int          `json:"advantage_over_strongest"`
	RecoveryOffsetAdvantage      int          `json:"recovery_offset_advantage"`
	AdvantageOverNoBank          int          `json:"advantage_over_no_bank"`
	AdvantageOverWrongCredit     int          `json:"advantage_over_wrong_credit"`
	OriginalAndMiddleRetained    bool         `json:"original_and_middle_retained"`
	PassesThreshold              bool         `json:"passes_threshold"`
}

func f16Arm(seed uint32, policy string) (F16Arm, error) {
	events, err := f16Generate(seed, policy)
	if err != nil || len(events) != F16Actions {
		return F16Arm{}, errF16
	}
	out := F16Arm{Seed: seed, Policy: policy,
		TraceSHA256: f8Digest("FORGE-EUREKA-F16-PREQUENTIAL-OBSERVATIONS-V1\n", events),
		Windows:     f16Windows()}
	m := f13New()
	var g1Bytes []byte
	for t, e := range events {
		if err := m.Observe(e); err != nil {
			return F16Arm{}, errF16
		}
		for i := range out.Windows {
			w := &out.Windows[i]
			if t < w.FirstAction || t > w.LastAction {
				continue
			}
			// Only the scorer reads the future t+2 revealed state; the forecasting
			// function above receives exactly two past/current events and memory.
			if t+2 >= len(events) {
				return F16Arm{}, errF16
			}
			target := events[t+2].DelayedState
			if target < 0 || target > 3 {
				return F16Arm{}, errF16
			}
			for k, kind := range f15Kinds() {
				prediction, work, err := f16Forecast(kind, m, events[t-1], e)
				if err != nil || prediction < 0 || prediction > 3 || work < 1 {
					return F16Arm{}, errF16
				}
				w.RuleWork[k] += work
				if prediction == target {
					w.Correct[k]++
					w.CorrectTrace[k] += "1"
				} else {
					w.CorrectTrace[k] += "0"
				}
			}
		}
		if t == 53 {
			out.G1Credited = len(m.Credits)
			out.G1Pending = m.Seen - len(m.Credits)
			g1Bytes, err = m.Snapshot()
			if err != nil {
				return F16Arm{}, errF16
			}
			out.G1SnapshotSHA256 = f3Hash(g1Bytes)
			cold, err := f13Load(g1Bytes, out.G1SnapshotSHA256)
			if err != nil || !reflect.DeepEqual(m, cold) {
				return F16Arm{}, errF16
			}
			// Continue G2 from the actual cold G1 state, never replay 54 old actions.
			m = cold
		}
	}
	out.G2Credited = len(m.Credits)
	out.G2Pending = m.Seen - len(m.Credits)
	g2, err := m.Snapshot()
	if err != nil {
		return F16Arm{}, errF16
	}
	out.G2SnapshotSHA256 = f3Hash(g2)
	cold, err := f13Load(g2, out.G2SnapshotSHA256)
	if err != nil || !reflect.DeepEqual(m, cold) {
		return F16Arm{}, errF16
	}
	fresh := f13New()
	for _, e := range events {
		if fresh.Observe(e) != nil {
			return F16Arm{}, errF16
		}
	}
	freshBytes, err := fresh.Snapshot()
	if err != nil || !bytes.Equal(g2, freshBytes) ||
		out.G1Credited != 52 || out.G2Credited != 58 || out.G1Pending != 2 || out.G2Pending != 2 {
		return F16Arm{}, errF16
	}
	out.ColdContinuationMatches = true
	for _, w := range out.Windows {
		for k := range w.Correct {
			if len(w.CorrectTrace[k]) != w.Trials || w.Correct[k] < 0 ||
				w.Correct[k] > w.Trials || w.RuleWork[k] <= 0 {
				return F16Arm{}, errF16
			}
		}
	}
	original, mid, ret := out.Windows[0], out.Windows[1], out.Windows[2]
	originalBest, _, _ := f16Strongest(original)
	midBest, _, _ := f16Strongest(mid)
	out.OriginalAndMiddleRetained = original.Correct[0] >= originalBest-1 && mid.Correct[0] >= midBest-1
	out.StrongestReturnScore, out.StrongestReturnName, out.FastestControlRecoveryOffset = f16Strongest(ret)
	out.CandidateRecoveryOffset = f16RecoveryOffset(ret.CorrectTrace[0])
	out.AdvantageOverStrongest = ret.Correct[0] - out.StrongestReturnScore
	out.RecoveryOffsetAdvantage = out.FastestControlRecoveryOffset - out.CandidateRecoveryOffset
	out.AdvantageOverNoBank = ret.Correct[0] - ret.Correct[7]
	out.AdvantageOverWrongCredit = ret.Correct[0] - ret.Correct[8]
	out.PassesThreshold = out.ColdContinuationMatches && out.OriginalAndMiddleRetained &&
		out.AdvantageOverStrongest >= F16MinReturnGain &&
		out.RecoveryOffsetAdvantage >= F16MinLatencyGain &&
		out.AdvantageOverNoBank >= F16MinAblationGain &&
		out.AdvantageOverWrongCredit >= F16MinAblationGain
	return out, nil
}

type F16Report struct {
	Schema                      string    `json:"schema"`
	ParentF15DigestSHA256       string    `json:"parent_f15_digest_sha256"`
	EarlierNegativesPreserved   bool      `json:"earlier_negatives_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Policies                    [2]string `json:"policies"`
	MiddleStep                  int       `json:"middle_step"`
	ReturnStep                  int       `json:"return_step"`
	ActionsPerArm               int       `json:"actions_per_arm"`
	Delay                       int       `json:"delay"`
	ReturnPredictionCount       int       `json:"return_prediction_count"`
	MinimumStrongGain           int       `json:"minimum_strong_gain"`
	MinimumLatencyGain          int       `json:"minimum_latency_gain"`
	MinimumAblationGain         int       `json:"minimum_ablation_gain"`
	Arms                        []F16Arm  `json:"arms"`
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

func f16Digest(x F16Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F16-FROZEN-ONLINE-RETURN-V1\n", x)
}
func F16Development() (F16Report, error) {
	parent, err := F15Development()
	if err != nil || F15Validate(parent) != nil || parent.Classification != F15NoGo ||
		parent.ScientificAccepted || parent.OwnerEligible || parent.DispatchAuthorized {
		return F16Report{}, errF16
	}
	out := F16Report{Schema: F16Schema, ParentF15DigestSHA256: parent.DigestSHA256,
		EarlierNegativesPreserved: true, Seeds: f13Seeds(), Policies: f13Policies(),
		MiddleStep: F16MiddleStep, ReturnStep: F16ReturnStep, ActionsPerArm: F16Actions,
		Delay: F13Delay, ReturnPredictionCount: 11,
		MinimumStrongGain: F16MinReturnGain, MinimumLatencyGain: F16MinLatencyGain,
		MinimumAblationGain: F16MinAblationGain,
		DevelopmentOnly:     true, Arms: make([]F16Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			arm, err := f16Arm(seed, policy)
			if err != nil {
				return F16Report{}, errF16
			}
			out.Arms = append(out.Arms, arm)
			for _, w := range arm.Windows {
				for _, cost := range w.RuleWork {
					out.TotalRuleWork += cost
				}
			}
			if arm.PassesThreshold {
				out.PassingArms++
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalRuleWork <= 0 {
		return F16Report{}, errF16
	}
	out.Classification = F16NO_GO
	if out.PassingArms == 4 {
		out.Classification = F16Signal
	}
	out.DigestSHA256 = f16Digest(out)
	return out, nil
}
func F16Validate(x F16Report) error {
	if x.Schema != F16Schema || x.DigestSHA256 != f16Digest(x) ||
		!x.DevelopmentOnly || !x.EarlierNegativesPreserved ||
		x.IndependentFirstUseConsumed || x.ScientificAccepted ||
		x.WholeProcessCostMeasured || x.OwnerEligible || x.DispatchAuthorized ||
		x.ActiveResearchChanged || x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF16
	}
	expected, err := F16Development()
	if err != nil || !reflect.DeepEqual(x, expected) {
		return errF16
	}
	return nil
}