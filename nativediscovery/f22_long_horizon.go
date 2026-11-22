// Eureka F22: frozen noisy A/B/A causal recall DEV, no scientific first-use/owner action.
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
	F22Schema  = "forge.native-discovery.long-horizon-causal-recall.dev.v1"
	F22NoGo    = "F22_DEV_NO_GO"
	F22Signal  = "F22_DEV_SIGNAL_UNVERIFIED"
	F22Actions = 96
)

var errF22 = errors.New("FORGE_EUREKA_F22_SOURCE_OR_AUTHORITY_INVALID")

func f22Seeds() [2]uint32    { return [2]uint32{131, 137} }
func f22Policies() [2]string { return [2]string{"balanced", "skewed"} }
func f22Kinds() [11]string {
	return [11]string{
		"archive-contradiction", "full-bayes", "rolling6-bayes", "rolling8-bayes", "rolling16-bayes",
		"discount-bayes", "switching-mle", "empirical-table", "no-archive", "always-archive", "wrong-credit",
	}
}
func f22Laws(seed uint32) (int, int, error) {
	switch seed {
	case 131:
		return 0xa6, 0x39, nil
	case 137:
		return 0x5c, 0xc3, nil
	}
	return 0, 0, errF22
}
func f22ActionCue(seed uint32, policy string, t int) (int, int, error) {
	if _, _, e := f22Laws(seed); e != nil || t < 0 || t >= F22Actions {
		return 0, 0, errF22
	}
	switch policy {
	case "balanced":
		return int(f12Mix(seed^uint32(t+1)*0xd8163841) & 3),
			int(f12Mix(seed^uint32(t+1)*0x9e3779b9) & 1), nil
	case "skewed":
		cue := (t/3 + int(seed%2)) % 2
		if t%5 == 4 {
			cue = (t/5 + int(seed%4)) % 4
		}
		return cue, int(f12Mix(seed^uint32(t+1)*0x85ebca6b) & 1), nil
	}
	return 0, 0, errF22
}
func f22Truth(seed uint32, t, cue, action int) (int, error) {
	a, b, e := f22Laws(seed)
	if e != nil || t < 0 || t >= F22Actions || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, errF22
	}
	if t >= 32 && t < 64 {
		a = b
	}
	return f20Truth(a, cue, action), nil
}
func f22Observation(seed uint32, t, cue, action int) (int, error) {
	bit, e := f22Truth(seed, t, cue, action)
	if e != nil {
		return 0, e
	}
	if f12Mix(seed^0x517cc1b7^uint32(t+1)*0x9e3779b9)%7 == 0 {
		return -1, nil
	}
	if f12Mix(seed^0xdab5a609^uint32(t+1)*0x85ebca6b)%9 == 0 {
		bit ^= 1
	}
	return bit, nil
}

type f22Ledger struct {
	Seen    int         `json:"seen"`
	Credits []f20Credit `json:"credits"`
	Pending []f20Probe  `json:"pending"`
}

func f22LedgerValid(s f22Ledger) bool {
	if s.Seen < 0 || s.Seen > F22Actions || len(s.Credits) != max(0, s.Seen-2) || len(s.Pending) != min(s.Seen, 2) {
		return false
	}
	for i, c := range s.Credits {
		if c.Step != i || c.Cue < 0 || c.Cue > 3 || c.Action < 0 || c.Action > 1 ||
			c.WrongAction < 0 || c.WrongAction > 1 || c.Value < -1 || c.Value > 1 {
			return false
		}
	}
	for i, p := range s.Pending {
		if p.Step != s.Seen-len(s.Pending)+i || p.Cue < 0 || p.Cue > 3 ||
			p.Action < 0 || p.Action > 1 || p.WrongAction < 0 || p.WrongAction > 1 {
			return false
		}
	}
	return true
}
func f22Snapshot(s f22Ledger) ([]byte, error) {
	if !f22LedgerValid(s) {
		return nil, errF22
	}
	return json.Marshal(s)
}
func f22Load(raw []byte, sha string) (f22Ledger, error) {
	if f3Hash(raw) != sha {
		return f22Ledger{}, errF22
	}
	var out f22Ledger
	if json.Unmarshal(raw, &out) != nil || !f22LedgerValid(out) {
		return f22Ledger{}, errF22
	}
	rep, e := f22Snapshot(out)
	if e != nil || !bytes.Equal(raw, rep) {
		return f22Ledger{}, errF22
	}
	return out, nil
}

// Factorized exact 8:1 likelihood; the 256 identifiable masks are equivalent
// to four independent four-category action-response causal factors.
func f22MAP(records []f20Credit, wrong bool) (int, int, error) {
	var weight [4][4]float64
	for c := range weight {
		for pair := range weight[c] {
			weight[c][pair] = 1
		}
	}
	work := 16
	for _, r := range records {
		if r.Step < 0 || r.Step >= F22Actions || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 ||
			r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
			return 0, 0, errF22
		}
		if r.Value == -1 {
			continue
		}
		action := r.Action
		if wrong {
			action = r.WrongAction
		}
		for pair := 0; pair < 4; pair++ {
			if f21BitResponse(pair, action) == r.Value {
				weight[r.Cue][pair] *= 8
			}
			work++
		}
	}
	mask := 0
	for cue := 0; cue < 4; cue++ {
		best := 0
		for pair := 1; pair < 4; pair++ {
			if weight[cue][pair] > weight[cue][best] {
				best = pair
			}
			work++
		}
		mask |= (best & 1) << cue
		mask |= ((best >> 1) & 1) << (cue + 4)
	}
	return mask, work, nil
}
func f22DiscountMAP(records []f20Credit) (int, int, error) {
	var score [4][4]float64
	work := 16
	for i, r := range records {
		if r.Step < 0 || r.Step >= F22Actions || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 ||
			r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
			return 0, 0, errF22
		}
		if r.Value == -1 {
			continue
		}
		factor := math.Pow(.9, float64(len(records)-1-i))
		for pair := 0; pair < 4; pair++ {
			if f21BitResponse(pair, r.Action) == r.Value {
				score[r.Cue][pair] += factor
			}
			work++
		}
	}
	mask := 0
	for cue := 0; cue < 4; cue++ {
		best := 0
		for pair := 1; pair < 4; pair++ {
			if score[cue][pair] > score[cue][best]+1e-12 {
				best = pair
			}
			work++
		}
		mask |= (best & 1) << cue
		mask |= ((best >> 1) & 1) << (cue + 4)
	}
	return mask, work, nil
}
func f22Recent(x []f20Credit, n int) []f20Credit {
	if len(x) > n {
		return x[len(x)-n:]
	}
	return x
}
func f22Matches(mask int, recs []f20Credit, wrong bool) (int, int) {
	hits, n := 0, 0
	for _, r := range recs {
		if r.Value == -1 {
			continue
		}
		n++
		a := r.Action
		if wrong {
			a = r.WrongAction
		}
		if f20Truth(mask, r.Cue, a) == r.Value {
			hits++
		}
	}
	return hits, n
}
func f22Archive(records []f20Credit, always, wrong bool) (int, int, error) {
	recent := f22Recent(records, 8)
	fallback, work, e := f22MAP(recent, wrong)
	if e != nil {
		return 0, 0, e
	}
	blocks := len(records) / 12
	if blocks == 0 {
		return fallback, work, nil
	}
	// The preregistered evidence window is the last six *non-erased*
	// credited outcomes, not merely the last six ledger entries.
	evidence := make([]f20Credit, 0, 6)
	for i := len(records) - 1; i >= 0 && len(evidence) < 6; i-- {
		if records[i].Value >= 0 {
			evidence = append(evidence, records[i])
		}
	}
	_, total := f22Matches(fallback, evidence, wrong)
	if total < 3 && !always {
		return fallback, work, nil
	}
	base, _ := f22Matches(fallback, evidence, wrong)
	bestRule, bestHits := fallback, -1
	for i := 0; i < blocks; i++ {
		mask, w, e := f22MAP(records[i*12:i*12+12], wrong)
		if e != nil {
			return 0, 0, e
		}
		work += w
		hits, n := f22Matches(mask, evidence, wrong)
		work += n
		if hits > bestHits {
			bestRule, bestHits = mask, hits
		}
	}
	if always || bestHits >= base+2 {
		return bestRule, work, nil
	}
	return fallback, work, nil
}

// Exact penalized maximum-likelihood one-or-two-changepoint control.
// Segment statistics reuse per-rule/observation prefix counts; every admissible
// segmentation with at most two switches and >=8 credits per segment is scored.
func f22Switching(records []f20Credit) (int, int, error) {
	n := len(records)
	if n == 0 {
		return 0, 0, nil
	}
	var prefix [4][4][F22Actions + 1]int
	work := 0
	for i, r := range records {
		if r.Step < 0 || r.Step >= F22Actions || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 ||
			r.WrongAction < 0 || r.WrongAction > 1 || r.Value < -1 || r.Value > 1 {
			return 0, 0, errF22
		}
		for cue := 0; cue < 4; cue++ {
			for pair := 0; pair < 4; pair++ {
				prefix[cue][pair][i+1] = prefix[cue][pair][i]
				if r.Value >= 0 && r.Cue == cue && f21BitResponse(pair, r.Action) == r.Value {
					prefix[cue][pair][i+1]++
				}
				work++
			}
		}
	}
	type seg struct{ score, rule int }
	var segs [F22Actions + 1][F22Actions + 1]seg
	for lo := 0; lo < n; lo++ {
		for hi := lo + 1; hi <= n; hi++ {
			v := seg{}
			for cue := 0; cue < 4; cue++ {
				best, val := 0, -1
				for pair := 0; pair < 4; pair++ {
					hits := prefix[cue][pair][hi] - prefix[cue][pair][lo]
					if hits > val {
						best, val = pair, hits
					}
					work++
				}
				v.score += val
				v.rule |= (best & 1) << cue
				v.rule |= ((best >> 1) & 1) << (cue + 4)
			}
			segs[lo][hi] = v
		}
	}
	chosen, score := segs[0][n].rule, segs[0][n].score
	for a := 8; a <= n-8; a++ {
		val := segs[0][a].score + segs[a][n].score - 3
		if val > score {
			score, chosen = val, segs[a][n].rule
		}
		work++
	}
	for a := 8; a <= n-16; a++ {
		for b := a + 8; b <= n-8; b++ {
			val := segs[0][a].score + segs[a][b].score + segs[b][n].score - 6
			if val > score {
				score, chosen = val, segs[b][n].rule
			}
			work++
		}
	}
	return chosen, work, nil
}
func f22Table(records []f20Credit, cue, action int) (int, int, error) {
	zeros, ones := 1, 1
	for _, r := range records {
		if r.Cue != cue || r.Action != action || r.Value < 0 {
			continue
		}
		if r.Value == 1 {
			ones++
		} else {
			zeros++
		}
	}
	if ones > zeros {
		return 1, len(records) + 2, nil
	}
	return 0, len(records) + 2, nil
}
func f22Forecast(kind string, records []f20Credit, cue, action int) (int, int, error) {
	if cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, 0, errF22
	}
	n := len(records)
	var rule, work int
	var e error
	switch kind {
	case "archive-contradiction":
		rule, work, e = f22Archive(records, false, false)
	case "full-bayes":
		rule, work, e = f22MAP(records, false)
	case "rolling6-bayes":
		rule, work, e = f22MAP(f22Recent(records, 6), false)
	case "rolling8-bayes", "no-archive":
		rule, work, e = f22MAP(f22Recent(records, 8), false)
	case "rolling16-bayes":
		rule, work, e = f22MAP(f22Recent(records, 16), false)
	case "discount-bayes":
		rule, work, e = f22DiscountMAP(records)
	case "switching-mle":
		rule, work, e = f22Switching(records)
	case "empirical-table":
		return f22Table(records, cue, action)
	case "always-archive":
		rule, work, e = f22Archive(records, true, false)
	case "wrong-credit":
		rule, work, e = f22Archive(records, false, true)
	default:
		return 0, 0, errF22
	}
	if e != nil || n > F22Actions {
		return 0, 0, errF22
	}
	return f20Truth(rule, cue, action), work + 1, nil
}

type F22Window struct {
	Name    string     `json:"name"`
	Start   int        `json:"start"`
	End     int        `json:"end"`
	Correct [11]int    `json:"correct"`
	Trace   [11]string `json:"trace"`
	Work    [11]int    `json:"work"`
}
type F22Arm struct {
	Seed                  uint32       `json:"seed"`
	Policy                string       `json:"policy"`
	TraceSHA256           string       `json:"trace_sha256"`
	G1SHA256              string       `json:"g1_sha256"`
	G2SHA256              string       `json:"g2_sha256"`
	G1Credited            int          `json:"g1_credited"`
	G2Credited            int          `json:"g2_credited"`
	Pending               int          `json:"pending"`
	ColdMatches           bool         `json:"cold_matches"`
	Windows               [2]F22Window `json:"windows"`
	StrongestReturnName   string       `json:"strongest_return_name"`
	StrongestReturnScore  int          `json:"strongest_return_score"`
	FastestReturnOffset   int          `json:"fastest_return_offset"`
	CandidateReturnOffset int          `json:"candidate_return_offset"`
	GainStrongest         int          `json:"gain_strongest"`
	GainNoArchive         int          `json:"gain_no_archive"`
	GainWrongCredit       int          `json:"gain_wrong_credit"`
	GainAlwaysArchive     int          `json:"gain_always_archive"`
	RetainedMiddle        bool         `json:"retained_middle"`
	ArchiveReady          bool         `json:"archive_ready"`
	Passes                bool         `json:"passes"`
}

func f22Recovery(bits string) int {
	if len(bits) != 12 {
		return 12
	}
	for i := 0; i <= 9; i++ {
		if bits[i:i+3] == "111" {
			return i
		}
	}
	return 12
}
func f22Strongest(w F22Window) (int, string, int) {
	score, name, fastest := -1, "", 12
	for i := 1; i <= 7; i++ {
		if w.Correct[i] > score {
			score, name = w.Correct[i], f22Kinds()[i]
		}
		if o := f22Recovery(w.Trace[i]); o < fastest {
			fastest = o
		}
	}
	return score, name, fastest
}
func f22Run(seed uint32, policy string, cold bool) (F22Arm, []byte, error) {
	if _, _, e := f22Laws(seed); e != nil || policy != "balanced" && policy != "skewed" {
		return F22Arm{}, nil, errF22
	}
	out := F22Arm{Seed: seed, Policy: policy, Windows: [2]F22Window{{Name: "middle-B", Start: 50, End: 61}, {Name: "returned-A", Start: 64, End: 75}}}
	m := f22Ledger{Credits: make([]f20Credit, 0, F22Actions), Pending: make([]f20Probe, 0, 2)}
	for t := 0; t < F22Actions; t++ {
		if t >= 2 {
			due := m.Pending[0]
			if due.Step != t-2 {
				return F22Arm{}, nil, errF22
			}
			value, e := f22Observation(seed, due.Step, due.Cue, due.Action)
			if e != nil {
				return F22Arm{}, nil, e
			}
			m.Credits = append(m.Credits, f20Credit{Step: due.Step, Cue: due.Cue, Action: due.Action, WrongAction: due.WrongAction, Value: value})
			m.Pending = m.Pending[1:]
		}
		cue, action, e := f22ActionCue(seed, policy, t)
		if e != nil {
			return F22Arm{}, nil, e
		}
		for wi := range out.Windows {
			w := &out.Windows[wi]
			if t < w.Start || t > w.End {
				continue
			}
			correct, e := f22Truth(seed, t, cue, action)
			if e != nil {
				return F22Arm{}, nil, e
			}
			for ki, kind := range f22Kinds() {
				guess, work, e := f22Forecast(kind, m.Credits, cue, action)
				if e != nil || work < 1 {
					return F22Arm{}, nil, errF22
				}
				w.Work[ki] += work
				if guess == correct {
					w.Correct[ki]++
					w.Trace[ki] += "1"
				} else {
					w.Trace[ki] += "0"
				}
			}
		}
		wrong := 0
		if t > 0 {
			wrong = m.Pending[len(m.Pending)-1].Action
		}
		m.Pending = append(m.Pending, f20Probe{Step: t, Cue: cue, Action: action, WrongAction: wrong})
		m.Seen++
		if !f22LedgerValid(m) {
			return F22Arm{}, nil, errF22
		}
		if t == 63 {
			out.G1Credited = len(m.Credits)
			out.Pending = len(m.Pending)
			raw, e := f22Snapshot(m)
			if e != nil {
				return F22Arm{}, nil, e
			}
			out.G1SHA256 = f3Hash(raw)
			if cold {
				after, e := f22Load(raw, out.G1SHA256)
				if e != nil || !reflect.DeepEqual(after, m) {
					return F22Arm{}, nil, errF22
				}
				m = after
			}
		}
	}
	out.G2Credited = len(m.Credits)
	raw, e := f22Snapshot(m)
	if e != nil {
		return F22Arm{}, nil, e
	}
	out.G2SHA256 = f3Hash(raw)
	out.TraceSHA256 = f8Digest("FORGE-EUREKA-F22-CAUSAL-CREDITS-V1\n", m)
	out.ColdMatches = out.G1Credited == 62 && out.G2Credited == 94 && out.Pending == 2 && len(m.Pending) == 2 &&
		m.Pending[0].Step == 94 && m.Pending[1].Step == 95
	mid, ret := out.Windows[0], out.Windows[1]
	midScore, _, _ := f22Strongest(mid)
	out.RetainedMiddle = mid.Correct[0] >= midScore-2
	out.StrongestReturnScore, out.StrongestReturnName, out.FastestReturnOffset = f22Strongest(ret)
	out.CandidateReturnOffset = f22Recovery(ret.Trace[0])
	out.GainStrongest = ret.Correct[0] - out.StrongestReturnScore
	out.GainNoArchive = ret.Correct[0] - ret.Correct[8]
	out.GainAlwaysArchive = ret.Correct[0] - ret.Correct[9]
	out.GainWrongCredit = ret.Correct[0] - ret.Correct[10]
	out.ArchiveReady = len(m.Credits)/12 >= 1
	out.Passes = out.ColdMatches && out.ArchiveReady && out.RetainedMiddle && out.GainStrongest >= 2 &&
		out.FastestReturnOffset-out.CandidateReturnOffset >= 1 &&
		out.GainNoArchive >= 2 && out.GainWrongCredit >= 2 && out.GainAlwaysArchive >= 1
	for _, w := range out.Windows {
		for ki := range w.Correct {
			if len(w.Trace[ki]) != 12 || w.Correct[ki] < 0 || w.Correct[ki] > 12 || w.Work[ki] < 1 {
				return F22Arm{}, nil, errF22
			}
		}
	}
	return out, raw, nil
}
func f22Arm(seed uint32, policy string) (F22Arm, error) {
	a, raw, e := f22Run(seed, policy, true)
	if e != nil {
		return F22Arm{}, errF22
	}
	b, original, e := f22Run(seed, policy, false)
	if e != nil || !reflect.DeepEqual(a, b) || !bytes.Equal(raw, original) {
		return F22Arm{}, errF22
	}
	return a, nil
}

type F22Report struct {
	Schema                    string    `json:"schema"`
	ParentF20SHA256           string    `json:"parent_f20_sha256"`
	EarlierNegativesPreserved bool      `json:"earlier_negatives_preserved"`
	Seeds                     [2]uint32 `json:"seeds"`
	Policies                  [2]string `json:"policies"`
	Actions                   int       `json:"actions"`
	FeedbackDelay             int       `json:"feedback_delay"`
	Middle                    [2]int    `json:"middle"`
	Return                    [2]int    `json:"return"`
	MinimumGain               int       `json:"minimum_gain"`
	Arms                      []F22Arm  `json:"arms"`
	PassingArms               int       `json:"passing_arms"`
	TotalWork                 int       `json:"total_work"`
	Classification            string    `json:"classification"`
	DevelopmentOnly           bool      `json:"development_only"`
	FirstUseConsumed          bool      `json:"first_use_consumed"`
	ScientificAccepted        bool      `json:"scientific_accepted"`
	WholeProcessCostProven    bool      `json:"whole_process_cost_proven"`
	OwnerEligible             bool      `json:"owner_eligible"`
	DispatchAuthorized        bool      `json:"dispatch_authorized"`
	ActiveResearchChanged     bool      `json:"active_research_changed"`
	AgentCalls                int       `json:"agent_calls"`
	PaidAPICalls              int       `json:"paid_api_calls"`
	DigestSHA256              string    `json:"digest_sha256"`
}

func f22Digest(x F22Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F22-DELAYED-A-B-A-DEV-V1\n", x)
}
func F22Development() (F22Report, error) {
	prev, e := F20Development()
	if e != nil || F20Validate(prev) != nil || prev.Classification != F20NoGo ||
		prev.ScientificAccepted || prev.OwnerEligible || prev.DispatchAuthorized {
		return F22Report{}, errF22
	}
	out := F22Report{Schema: F22Schema, ParentF20SHA256: prev.DigestSHA256, EarlierNegativesPreserved: true,
		Seeds: f22Seeds(), Policies: f22Policies(), Actions: 96, FeedbackDelay: 2, Middle: [2]int{50, 61},
		Return: [2]int{64, 75}, MinimumGain: 2, DevelopmentOnly: true, Arms: make([]F22Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			arm, e := f22Arm(seed, policy)
			if e != nil {
				return F22Report{}, errF22
			}
			out.Arms = append(out.Arms, arm)
			if arm.Passes {
				out.PassingArms++
			}
			for _, w := range arm.Windows {
				for _, cost := range w.Work {
					out.TotalWork += cost
				}
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalWork <= 0 {
		return F22Report{}, errF22
	}
	out.Classification = F22NoGo
	if out.PassingArms == 4 {
		out.Classification = F22Signal
	}
	out.DigestSHA256 = f22Digest(out)
	return out, nil
}

var f22Reference struct {
	once   sync.Once
	report F22Report
	err    error
}

func F22Validate(x F22Report) error {
	if x.Schema != F22Schema || x.DigestSHA256 != f22Digest(x) || !x.DevelopmentOnly ||
		!x.EarlierNegativesPreserved || x.FirstUseConsumed || x.ScientificAccepted || x.WholeProcessCostProven ||
		x.OwnerEligible || x.DispatchAuthorized || x.ActiveResearchChanged || x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF22
	}
	f22Reference.once.Do(func() { f22Reference.report, f22Reference.err = F22Development() })
	if f22Reference.err != nil || !reflect.DeepEqual(x, f22Reference.report) {
		return errF22
	}
	return nil
}
