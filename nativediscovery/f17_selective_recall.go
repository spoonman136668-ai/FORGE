// Eureka F17: selective causal archive retrieval after two interfering laws.
// Development-only source; no owner admission, first-use or production path.
package nativediscovery

import (
	"bytes"
	"errors"
	"reflect"
	"sync"
)

const (
	F17Schema          = "forge.native-discovery.selective-causal-recall.dev.v1"
	F17Actions         = 60
	F17ReturnStep      = 48
	F17MinStrongGain   = 2
	F17MinLatencyGain  = 1
	F17MinAblationGain = 2
	F17MinAlwaysGain   = 1
	F17NO_GO           = "F17_DEV_NO_GO"
	F17Signal          = "F17_DEV_SIGNAL_UNVERIFIED"
)

var errF17 = errors.New("FORGE_EUREKA_F17_SOURCE_OR_AUTHORITY_INVALID")

func f17Seeds() [2]uint32    { return [2]uint32{71, 97} }
func f17Policies() [2]string { return [2]string{"fixed", "random"} }

// Only the isolated synthetic generator may call this function.
func f17WorldRules(seed uint32) ([3]int, error) {
	switch seed {
	case 71:
		return [3]int{3, 8, 1}, nil
	case 97:
		return [3]int{11, 2, 9}, nil
	default:
		return [3]int{}, errF17
	}
}
func f17Action(seed uint32, policy string, step int) (int, error) {
	if _, err := f17WorldRules(seed); err != nil || step < 0 || step >= F17Actions {
		return 0, errF17
	}
	switch policy {
	case "fixed":
		return step & 1, nil
	case "random":
		return int(f12Mix(seed^uint32(step+13)*0x9e3779b9) & 1), nil
	}
	return 0, errF17
}
func f17Generate(seed uint32, policy string) ([]f12Event, error) {
	laws, err := f17WorldRules(seed)
	if err != nil || policy != "fixed" && policy != "random" {
		return nil, errF17
	}
	state := int(f12Mix(seed^0x125ecafe) & 3)
	original := state
	history := make([]int, 0, F17Actions)
	events := make([]f12Event, 0, F17Actions)
	for step := 0; step < F17Actions; step++ {
		action, e := f17Action(seed, policy, step)
		if e != nil {
			return nil, errF17
		}
		cue := f12Cue(seed, step, 0)
		delayed := -1
		if step == 1 {
			delayed = original
		}
		if step >= 2 {
			delayed = history[step-2]
		}
		events = append(events, f12Event{Step: step, Phase: 0, Cue: cue, Action: action,
			Sensor: state & 1, DelayedState: delayed})
		rule := laws[0]
		if step >= 16 && step < 32 {
			rule = laws[1]
		}
		if step >= 32 && step < F17ReturnStep {
			rule = laws[2]
		}
		state = f12Next(rule, state, 0, cue, action)
		history = append(history, state)
	}
	return events, nil
}

// All learning depends only on credited causal records, never true rule or seed.
// The archive is derivable from the portable learned-state checkpoint.
func f17Archive(records []f13Credit, wrongLag bool) ([F12RuleCount]bool, int, int) {
	var archived [F12RuleCount]bool
	work, quantity := 0, 0
	for start := 0; start+8 <= len(records); start += 8 {
		rule, hits := f13Best(records[start:start+8], wrongLag, false)
		work += F12RuleCount * 8
		if hits >= 7 && !archived[rule] {
			archived[rule] = true
			quantity++
		}
	}
	return archived, work, quantity
}
func f17SelectRule(records []f13Credit, kind string) (int, int, bool, int, error) {
	if len(records) < 8 || len(records) > F17Actions-2 {
		return 0, 0, false, 0, errF17
	}
	recent8 := f13Recent(records, 8)
	fallback, _ := f13Best(recent8, false, false)
	work := F12RuleCount * len(recent8)
	if kind == "no-archive" {
		return fallback, work, false, 0, nil
	}
	if kind != "selective" && kind != "always-archive" && kind != "wrong-lag" {
		return 0, 0, false, 0, errF17
	}
	wrongLag := kind == "wrong-lag"
	archive, archiveWork, quantity := f17Archive(records, wrongLag)
	work += archiveWork
	contradiction := false
	if len(records) >= 11 {
		older := records[len(records)-11 : len(records)-3]
		oldRule, _ := f13Best(older, wrongLag, false)
		work += F12RuleCount * len(older)
		misses := 0
		for _, rec := range records[len(records)-3:] {
			work++
			if !f13Match(oldRule, rec, wrongLag) {
				misses++
			}
		}
		contradiction = misses >= 2
	}
	if quantity == 0 || kind != "always-archive" && !contradiction {
		return fallback, work, contradiction, quantity, nil
	}
	chosen, peak := -1, -1
	tail := f13Recent(records, 2)
	for rule, exists := range archive {
		if !exists {
			continue
		}
		matches := 0
		for _, rec := range tail {
			work++
			if f13Match(rule, rec, wrongLag) {
				matches++
			}
		}
		if matches > peak {
			chosen, peak = rule, matches
		}
	}
	// Require both actually credited effects to match an archived rule.
	// Negative always-archive deliberately ignores the contradiction alarm.
	if chosen >= 0 && peak == len(tail) {
		return chosen, work, contradiction, quantity, nil
	}
	return fallback, work, contradiction, quantity, nil
}
func f17Kinds() [10]string {
	return [10]string{"selective", "full-mle", "rolling4-mle", "rolling8-mle",
		"rolling16-mle", "switching-mle", "table", "no-archive", "always-archive", "wrong-lag"}
}
func f17Forecast(kind string, m *f13Notebook, last, current f12Event) (int, int, error) {
	if m == nil || m.Validate() != nil || m.Seen != current.Step+1 || current.Step < 2 ||
		current.Step != last.Step+1 || current.Phase != 0 || last.Phase != 0 ||
		current.DelayedState < 0 || current.DelayedState > 3 ||
		current.Cue < 0 || current.Cue >= 4 || last.Cue < 0 || last.Cue >= 4 ||
		current.Action < 0 || current.Action > 1 || last.Action < 0 || last.Action > 1 {
		return 0, 0, errF17
	}
	switch kind {
	case "selective", "always-archive", "wrong-lag", "no-archive":
		rule, work, _, _, err := f17SelectRule(m.Credits, kind)
		if err != nil {
			return 0, 0, errF17
		}
		mid := f12Next(rule, current.DelayedState, 0, last.Cue, last.Action)
		return f12Next(rule, mid, 0, current.Cue, current.Action), work + 2, nil
	default:
		guess, work, err := f16Forecast(kind, m, last, current)
		if err != nil {
			return 0, 0, errF17
		}
		return guess, work, nil
	}
}

type F17Window struct {
	Name         string     `json:"name"`
	Start        int        `json:"start_action"`
	End          int        `json:"end_action"`
	Predictions  int        `json:"predictions"`
	Correct      [10]int    `json:"correct"`
	CorrectTrace [10]string `json:"correct_trace"`
	RuleWork     [10]int    `json:"rule_work"`
}

func f17Windows() [3]F17Window {
	return [3]F17Window{
		{Name: "middle-B", Start: 26, End: 30, Predictions: 5},
		{Name: "late-C", Start: 42, End: 46, Predictions: 5},
		{Name: "returned-A", Start: 48, End: 57, Predictions: 10},
	}
}
func f17Recovery(bits string) int {
	if len(bits) != 10 {
		return 10
	}
	for i := 0; i <= 7; i++ {
		if bits[i:i+3] == "111" {
			return i
		}
	}
	return 10
}
func f17Strongest(win F17Window) (int, string, int) {
	best, name, earliest := -1, "", 10
	kinds := f17Kinds()
	for k := 1; k <= 6; k++ {
		if win.Correct[k] > best {
			best, name = win.Correct[k], kinds[k]
		}
		if win.Name == "returned-A" {
			if v := f17Recovery(win.CorrectTrace[k]); v < earliest {
				earliest = v
			}
		}
	}
	return best, name, earliest
}

type F17Arm struct {
	Seed                         uint32       `json:"seed"`
	Policy                       string       `json:"policy"`
	TraceSHA256                  string       `json:"trace_sha256"`
	Windows                      [3]F17Window `json:"windows"`
	G1SnapshotSHA256             string       `json:"g1_snapshot_sha256"`
	G2SnapshotSHA256             string       `json:"g2_snapshot_sha256"`
	G1Credited                   int          `json:"g1_credited"`
	G2Credited                   int          `json:"g2_credited"`
	G1Pending                    int          `json:"g1_pending"`
	G2Pending                    int          `json:"g2_pending"`
	ColdMatches                  bool         `json:"cold_matches"`
	ReturnStrongestName          string       `json:"return_strongest_name"`
	ReturnStrongestCorrect       int          `json:"return_strongest_correct"`
	CandidateRecoveryOffset      int          `json:"candidate_recovery_offset"`
	FastestControlRecoveryOffset int          `json:"fastest_control_recovery_offset"`
	AdvantageStrongest           int          `json:"advantage_strongest"`
	AdvantageRecovery            int          `json:"advantage_recovery"`
	AdvantageNoArchive           int          `json:"advantage_no_archive"`
	AdvantageAlwaysArchive       int          `json:"advantage_always_archive"`
	AdvantageWrongLag            int          `json:"advantage_wrong_lag"`
	MiddleRetention              bool         `json:"middle_retention"`
	ArchiveCountAtG1             int          `json:"archive_count_at_g1"`
	PassesThreshold              bool         `json:"passes_threshold"`
}

func f17Arm(seed uint32, policy string) (F17Arm, error) {
	stream, err := f17Generate(seed, policy)
	if err != nil || len(stream) != F17Actions {
		return F17Arm{}, errF17
	}
	out := F17Arm{Seed: seed, Policy: policy, TraceSHA256: f8Digest(
		"FORGE-EUREKA-F17-INTERFERENCE-OBSERVATIONS-V1\n", stream), Windows: f17Windows()}
	m := f13New()
	for t, e := range stream {
		if err := m.Observe(e); err != nil {
			return F17Arm{}, errF17
		}
		if t == 53 {
			checkpoint, err := m.Snapshot()
			if err != nil {
				return F17Arm{}, errF17
			}
			out.G1Credited = len(m.Credits)
			out.G1Pending = m.Seen - len(m.Credits)
			out.G1SnapshotSHA256 = f3Hash(checkpoint)
			_, _, out.ArchiveCountAtG1 = f17Archive(m.Credits, false)
			cold, err := f13Load(checkpoint, out.G1SnapshotSHA256)
			if err != nil || !reflect.DeepEqual(cold, m) {
				return F17Arm{}, errF17
			}
			m = cold
		}
		for i := range out.Windows {
			w := &out.Windows[i]
			if t < w.Start || t > w.End {
				continue
			}
			if t+2 >= len(stream) {
				return F17Arm{}, errF17
			}
			target := stream[t+2].DelayedState // scorer-only; no fit API can see this
			for k, kind := range f17Kinds() {
				predicted, cost, err := f17Forecast(kind, m, stream[t-1], e)
				if err != nil || cost < 1 || predicted < 0 || predicted > 3 {
					return F17Arm{}, errF17
				}
				w.RuleWork[k] += cost
				if predicted == target {
					w.Correct[k]++
					w.CorrectTrace[k] += "1"
				} else {
					w.CorrectTrace[k] += "0"
				}
			}
		}
	}
	out.G2Credited = len(m.Credits)
	out.G2Pending = m.Seen - len(m.Credits)
	g2, err := m.Snapshot()
	if err != nil {
		return F17Arm{}, errF17
	}
	out.G2SnapshotSHA256 = f3Hash(g2)
	replay := f13New()
	for _, e := range stream {
		if replay.Observe(e) != nil {
			return F17Arm{}, errF17
		}
	}
	original, err := replay.Snapshot()
	if err != nil || !bytes.Equal(original, g2) ||
		out.G1Credited != 52 || out.G1Pending != 2 || out.G2Credited != 58 || out.G2Pending != 2 {
		return F17Arm{}, errF17
	}
	out.ColdMatches = true
	for _, w := range out.Windows {
		for k := range w.Correct {
			if w.Correct[k] < 0 || w.Correct[k] > w.Predictions ||
				len(w.CorrectTrace[k]) != w.Predictions || w.RuleWork[k] <= 0 {
				return F17Arm{}, errF17
			}
		}
	}
	b, c, returned := out.Windows[0], out.Windows[1], out.Windows[2]
	bestB, _, _ := f17Strongest(b)
	bestC, _, _ := f17Strongest(c)
	out.MiddleRetention = b.Correct[0] >= bestB-1 && c.Correct[0] >= bestC-1
	out.ReturnStrongestCorrect, out.ReturnStrongestName, out.FastestControlRecoveryOffset = f17Strongest(returned)
	out.CandidateRecoveryOffset = f17Recovery(returned.CorrectTrace[0])
	out.AdvantageStrongest = returned.Correct[0] - out.ReturnStrongestCorrect
	out.AdvantageRecovery = out.FastestControlRecoveryOffset - out.CandidateRecoveryOffset
	out.AdvantageNoArchive = returned.Correct[0] - returned.Correct[7]
	out.AdvantageAlwaysArchive = returned.Correct[0] - returned.Correct[8]
	out.AdvantageWrongLag = returned.Correct[0] - returned.Correct[9]
	out.PassesThreshold = out.ColdMatches && out.MiddleRetention && out.ArchiveCountAtG1 > 0 &&
		out.AdvantageStrongest >= F17MinStrongGain && out.AdvantageRecovery >= F17MinLatencyGain &&
		out.AdvantageNoArchive >= F17MinAblationGain && out.AdvantageWrongLag >= F17MinAblationGain &&
		out.AdvantageAlwaysArchive >= F17MinAlwaysGain
	return out, nil
}

type F17Report struct {
	Schema                      string    `json:"schema"`
	ParentF16DigestSHA256       string    `json:"parent_f16_digest_sha256"`
	EarlierNegativesPreserved   bool      `json:"earlier_negatives_preserved"`
	Seeds                       [2]uint32 `json:"seeds"`
	Policies                    [2]string `json:"policies"`
	SwitchSteps                 [3]int    `json:"switch_steps"`
	ActionsPerArm               int       `json:"actions_per_arm"`
	DelaySteps                  int       `json:"delay_steps"`
	ReturnPredictions           int       `json:"return_predictions"`
	MinimumStrongGain           int       `json:"minimum_strong_gain"`
	MinimumLatencyGain          int       `json:"minimum_latency_gain"`
	MinimumAblationGain         int       `json:"minimum_ablation_gain"`
	MinimumAlwaysGain           int       `json:"minimum_always_gain"`
	Arms                        []F17Arm  `json:"arms"`
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

func f17Digest(x F17Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F17-SELECTIVE-RECALL-V1\n", x)
}
func F17Development() (F17Report, error) {
	previous, err := F16Development()
	if err != nil || F16Validate(previous) != nil || previous.Classification != F16NO_GO ||
		previous.ScientificAccepted || previous.OwnerEligible || previous.DispatchAuthorized {
		return F17Report{}, errF17
	}
	out := F17Report{Schema: F17Schema, ParentF16DigestSHA256: previous.DigestSHA256,
		EarlierNegativesPreserved: true, Seeds: f17Seeds(), Policies: f17Policies(),
		SwitchSteps: [3]int{16, 32, 48}, ActionsPerArm: F17Actions, DelaySteps: 2,
		ReturnPredictions: 10, MinimumStrongGain: F17MinStrongGain,
		MinimumLatencyGain: F17MinLatencyGain, MinimumAblationGain: F17MinAblationGain,
		MinimumAlwaysGain: F17MinAlwaysGain, DevelopmentOnly: true, Arms: make([]F17Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			arm, err := f17Arm(seed, policy)
			if err != nil {
				return F17Report{}, errF17
			}
			out.Arms = append(out.Arms, arm)
			for _, w := range arm.Windows {
				for _, v := range w.RuleWork {
					out.TotalRuleWork += v
				}
			}
			if arm.PassesThreshold {
				out.PassingArms++
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalRuleWork <= 0 {
		return F17Report{}, errF17
	}
	out.Classification = F17NO_GO
	if out.PassingArms == 4 {
		out.Classification = F17Signal
	}
	out.DigestSHA256 = f17Digest(out)
	return out, nil
}

var f17ValidatedReference struct {
	once   sync.Once
	report F17Report
	err    error
}

func F17Validate(x F17Report) error {
	if x.Schema != F17Schema || x.DigestSHA256 != f17Digest(x) ||
		!x.DevelopmentOnly || !x.EarlierNegativesPreserved || x.IndependentFirstUseConsumed ||
		x.ScientificAccepted || x.WholeProcessCostMeasured || x.OwnerEligible ||
		x.DispatchAuthorized || x.ActiveResearchChanged || x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF17
	}
	f17ValidatedReference.once.Do(func() {
		f17ValidatedReference.report, f17ValidatedReference.err = F17Development()
	})
	if f17ValidatedReference.err != nil || !reflect.DeepEqual(x, f17ValidatedReference.report) {
		return errF17
	}
	return nil
}
