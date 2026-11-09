// Eureka F23: prospectively frozen A/B/C/A latent-regime belief, DEV ONLY.
// No runtime research admission, scientific first-use, workers, or external execution.
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
	F23Schema     = "forge.native-discovery.latent-regime-belief.dev.v1"
	F23NoGo       = "F23_DEV_NO_GO"
	F23Signal     = "F23_DEV_SIGNAL_UNVERIFIED"
	F23Actions    = 128
	F23F22Parent  = "a9e074acc0c2ab8462d75f2c0f31c00e7caeb514"
	f23KindsCount = 13
)

var errF23 = errors.New("FORGE_EUREKA_F23_SOURCE_OR_AUTHORITY_INVALID")

func f23Seeds() [2]uint32    { return [2]uint32{151, 157} }
func f23Policies() [2]string { return [2]string{"balanced", "skewed"} }
func f23Kinds() [f23KindsCount]string {
	return [f23KindsCount]string{
		"regime-belief", "full-bayes", "rolling6-bayes", "rolling8-bayes", "rolling16-bayes",
		"discount-bayes", "switching-mle", "empirical-table", "online-selector",
		"no-archive", "uniform-retrieval", "wrong-credit", "random-retrieval",
	}
}
func f23Laws(seed uint32) ([3]int, error) {
	switch seed {
	case 151:
		return [3]int{0xe2, 0x1d, 0x69}, nil
	case 157:
		return [3]int{0x4b, 0xd4, 0x35}, nil
	}
	return [3]int{}, errF23
}
func f23ActionCue(seed uint32, policy string, t int) (int, int, error) {
	if _, e := f23Laws(seed); e != nil || t < 0 || t >= F23Actions {
		return 0, 0, errF23
	}
	switch policy {
	case "balanced":
		return int(f12Mix(seed^uint32(t+1)*0x7f4a7c15) & 3), int(f12Mix(seed^uint32(t+1)*0x6a09e667) & 1), nil
	case "skewed":
		cue := (t/4 + int(seed%2)) % 2
		if t%7 == 6 {
			cue = (t/7 + int(seed%4)) % 4
		}
		return cue, int(f12Mix(seed^uint32(t+1)*0xbb67ae85) & 1), nil
	}
	return 0, 0, errF23
}
func f23Truth(seed uint32, t, cue, action int) (int, error) {
	laws, e := f23Laws(seed)
	if e != nil || t < 0 || t >= F23Actions || cue < 0 || cue > 3 || action < 0 || action > 1 {
		return 0, errF23
	}
	law := laws[0]
	if t >= 32 && t < 64 {
		law = laws[1]
	}
	if t >= 64 && t < 96 {
		law = laws[2]
	}
	return f20Truth(law, cue, action), nil
}
func f23Observation(seed uint32, t, cue, action int) (int, error) {
	truth, e := f23Truth(seed, t, cue, action)
	if e != nil {
		return 0, e
	}
	if f12Mix(seed^0x243f6a88^uint32(t+1)*0x9e3779b9)%11 == 0 {
		return -1, nil
	}
	if f12Mix(seed^0x85a308d3^uint32(t+1)*0x85ebca6b)%13 == 0 {
		truth ^= 1
	}
	return truth, nil
}

func f23ValidCredit(r f20Credit) bool {
	return r.Step >= 0 && r.Step < F23Actions && r.Cue >= 0 && r.Cue <= 3 &&
		r.Action >= 0 && r.Action <= 1 && r.WrongAction >= 0 && r.WrongAction <= 1 &&
		r.Value >= -1 && r.Value <= 1
}
func f23ValidCredits(recs []f20Credit) bool {
	if len(recs) > F23Actions-2 {
		return false
	}
	for _, r := range recs {
		if !f23ValidCredit(r) {
			return false
		}
	}
	return true
}

type f23Factors [4][4]float64

func f23Uniform() f23Factors {
	var out f23Factors
	for c := range out {
		for p := range out[c] {
			out[c][p] = 0.25
		}
	}
	return out
}
func f23BitProb(f f23Factors, cue, action, bit int) float64 {
	p := 0.0
	for pair, v := range f[cue] {
		if f21BitResponse(pair, action) == bit {
			p += v
		}
	}
	return p
}
func f23Update(f *f23Factors, r f20Credit, wrong bool) (float64, int, error) {
	if !f23ValidCredit(r) {
		return 0, 0, errF23
	}
	if r.Value == -1 {
		return 1, 0, nil
	}
	action := r.Action
	if wrong {
		action = r.WrongAction
	}
	p := f23BitProb(*f, r.Cue, action, r.Value)
	likelihood := (1 + 7*p) / 9
	if likelihood <= 0 || math.IsNaN(likelihood) || math.IsInf(likelihood, 0) {
		return 0, 0, errF23
	}
	mass := 0.0
	for pair := range f[r.Cue] {
		if f21BitResponse(pair, action) == r.Value {
			f[r.Cue][pair] *= 8
		}
		mass += f[r.Cue][pair]
	}
	if mass <= 0 || math.IsNaN(mass) || math.IsInf(mass, 0) {
		return 0, 0, errF23
	}
	for pair := range f[r.Cue] {
		f[r.Cue][pair] /= mass
	}
	return likelihood, 8, nil
}
func f23Fit(records []f20Credit, wrong bool) (f23Factors, int, error) {
	if !f23ValidCredits(records) {
		return f23Factors{}, 0, errF23
	}
	f := f23Uniform()
	work := 16
	for _, r := range records {
		_, w, e := f23Update(&f, r, wrong)
		if e != nil {
			return f23Factors{}, 0, e
		}
		work += w
	}
	return f, work, nil
}
func f23MAP(records []f20Credit) (int, int, error) {
	f, work, e := f23Fit(records, false)
	if e != nil {
		return 0, 0, e
	}
	mask := 0
	for c := 0; c < 4; c++ {
		best := 0
		for p := 1; p < 4; p++ {
			if f[c][p] > f[c][best] {
				best = p
			}
			work++
		}
		mask |= (best & 1) << c
		mask |= ((best >> 1) & 1) << (c + 4)
	}
	return mask, work, nil
}
func f23DiscountMAP(records []f20Credit) (int, int, error) {
	if !f23ValidCredits(records) {
		return 0, 0, errF23
	}
	var score [4][4]float64
	work := 16
	for i, r := range records {
		if r.Value < 0 {
			continue
		}
		v := math.Pow(.9, float64(len(records)-1-i))
		for p := 0; p < 4; p++ {
			if f21BitResponse(p, r.Action) == r.Value {
				score[r.Cue][p] += v
			}
			work++
		}
	}
	mask := 0
	for c := 0; c < 4; c++ {
		best := 0
		for p := 1; p < 4; p++ {
			if score[c][p] > score[c][best]+1e-12 {
				best = p
			}
			work++
		}
		mask |= (best & 1) << c
		mask |= ((best >> 1) & 1) << (c + 4)
	}
	return mask, work, nil
}
func f23Switching(records []f20Credit) (int, int, error) {
	if !f23ValidCredits(records) {
		return 0, 0, errF23
	}
	n := len(records)
	if n == 0 {
		return 0, 0, nil
	}
	var counts [4][4][F23Actions + 1]int
	work := 0
	for i, r := range records {
		for c := 0; c < 4; c++ {
			for p := 0; p < 4; p++ {
				counts[c][p][i+1] = counts[c][p][i]
				if r.Value >= 0 && r.Cue == c && f21BitResponse(p, r.Action) == r.Value {
					counts[c][p][i+1]++
				}
				work++
			}
		}
	}
	type segment struct{ hits, law int }
	var seg [F23Actions + 1][F23Actions + 1]segment
	for lo := 0; lo < n; lo++ {
		for hi := lo + 1; hi <= n; hi++ {
			var s segment
			for c := 0; c < 4; c++ {
				best := 0
				matches := -1
				for p := 0; p < 4; p++ {
					hits := counts[c][p][hi] - counts[c][p][lo]
					if hits > matches {
						best = p
						matches = hits
					}
					work++
				}
				s.hits += matches
				s.law |= (best & 1) << c
				s.law |= ((best >> 1) & 1) << (c + 4)
			}
			seg[lo][hi] = s
		}
	}
	chosen, score := seg[0][n].law, seg[0][n].hits
	for a := 8; a <= n-8; a++ {
		v := seg[0][a].hits + seg[a][n].hits - 3
		if v > score {
			score, chosen = v, seg[a][n].law
		}
		work++
	}
	for a := 8; a <= n-16; a++ {
		for b := a + 8; b <= n-8; b++ {
			v := seg[0][a].hits + seg[a][b].hits + seg[b][n].hits - 6
			if v > score {
				score, chosen = v, seg[b][n].law
			}
			work++
		}
	}
	return chosen, work, nil
}
func f23Conventional(k int, records []f20Credit, cue, action int) (int, int, error) {
	if k < 0 || k >= 7 || cue < 0 || cue > 3 || action < 0 || action > 1 || !f23ValidCredits(records) {
		return 0, 0, errF23
	}
	var rule, work int
	var e error
	switch k {
	case 0:
		rule, work, e = f23MAP(records)
	case 1:
		rule, work, e = f23MAP(f22Recent(records, 6))
	case 2:
		rule, work, e = f23MAP(f22Recent(records, 8))
	case 3:
		rule, work, e = f23MAP(f22Recent(records, 16))
	case 4:
		rule, work, e = f23DiscountMAP(records)
	case 5:
		rule, work, e = f23Switching(records)
	case 6:
		z, o := 1, 1
		for _, r := range records {
			if r.Value < 0 || r.Cue != cue || r.Action != action {
				continue
			}
			if r.Value == 1 {
				o++
			} else {
				z++
			}
		}
		if o > z {
			return 1, len(records) + 2, nil
		}
		return 0, len(records) + 2, nil
	}
	if e != nil {
		return 0, 0, e
	}
	return f20Truth(rule, cue, action), work + 1, nil
}

// Exactly the six most recent non-erased credited observations are used as
// sequential online evidence; no component's prior includes the evidence.
func f23Evidence(records []f20Credit) (int, []f20Credit) {
	start := len(records)
	n := 0
	for i := len(records) - 1; i >= 0 && n < 6; i-- {
		if records[i].Value >= 0 {
			start = i
			n++
		}
	}
	if n == 0 {
		return len(records), nil
	}
	evidence := make([]f20Credit, 0, n)
	for _, r := range records[start:] {
		if r.Value >= 0 {
			evidence = append(evidence, r)
		}
	}
	return start, evidence
}
func f23Belief(records []f20Credit, cue, action, t int, kind string) (int, int, int, error) {
	if t < 0 || t >= F23Actions || cue < 0 || cue > 3 || action < 0 || action > 1 || !f23ValidCredits(records) {
		return 0, 0, 0, errF23
	}
	if kind != "regime-belief" && kind != "no-archive" && kind != "uniform-retrieval" && kind != "wrong-credit" && kind != "random-retrieval" {
		return 0, 0, 0, errF23
	}
	wrong := kind == "wrong-credit"
	start, evidence := f23Evidence(records)
	fresh, work, e := f23Fit(f22Recent(records[:start], 8), wrong)
	if e != nil {
		return 0, 0, 0, e
	}
	bank := []f23Factors{fresh}
	if kind != "no-archive" {
		for j := 0; j < 5 && (j+1)*24 <= start; j++ {
			f, w, e := f23Fit(records[j*24:(j+1)*24], wrong)
			if e != nil {
				return 0, 0, 0, e
			}
			bank = append(bank, f)
			work += w
		}
	}
	count := len(bank) - 1
	weights := make([]float64, len(bank))
	weights[0] = 1
	if count > 0 {
		weights[0] = 0.5
		for j := 1; j <= count; j++ {
			weights[j] = 0.5 / float64(count)
		}
	}
	for _, r := range evidence {
		total := 0.0
		for j := range bank {
			probability, w, e := f23Update(&bank[j], r, wrong)
			if e != nil {
				return 0, 0, 0, e
			}
			weights[j] *= probability
			total += weights[j]
			work += w + 2
		}
		if total <= 0 || math.IsNaN(total) || math.IsInf(total, 0) {
			return 0, 0, 0, errF23
		}
		for j := range weights {
			weights[j] /= total
		}
	}
	if kind == "uniform-retrieval" {
		for j := range weights {
			weights[j] = 1 / float64(len(weights))
		}
	}
	if kind == "random-retrieval" && count > 0 {
		chosen := 1 + int(f12Mix(uint32(t)^0x93a5298d)%uint32(count))
		for j := range weights {
			weights[j] = 0
		}
		weights[chosen] = 1
	}
	p := 0.0
	for j, f := range bank {
		p += weights[j] * f23BitProb(f, cue, action, 1)
		work += 4
	}
	if math.IsNaN(p) || math.IsInf(p, 0) || p < -1e-12 || p > 1+1e-12 {
		return 0, 0, 0, errF23
	}
	if p > 0.5 {
		return 1, work + 1, count, nil
	}
	return 0, work + 1, count, nil
}

type f23Ledger struct {
	Seen         int         `json:"seen"`
	Credits      []f20Credit `json:"credits"`
	Pending      []f20Probe  `json:"pending"`
	ControlPreds [][7]int    `json:"control_preds"`
}

func f23LedgerValid(m f23Ledger) bool {
	if m.Seen < 0 || m.Seen > F23Actions || len(m.Credits) != max(0, m.Seen-2) || len(m.Pending) != min(m.Seen, 2) || len(m.ControlPreds) != m.Seen {
		return false
	}
	for i, r := range m.Credits {
		if !f23ValidCredit(r) || r.Step != i {
			return false
		}
	}
	for i, r := range m.Pending {
		if r.Step != m.Seen-len(m.Pending)+i || r.Cue < 0 || r.Cue > 3 || r.Action < 0 || r.Action > 1 || r.WrongAction < 0 || r.WrongAction > 1 {
			return false
		}
	}
	for _, arr := range m.ControlPreds {
		for _, v := range arr {
			if v != 0 && v != 1 {
				return false
			}
		}
	}
	return true
}
func f23Snapshot(m f23Ledger) ([]byte, error) {
	if !f23LedgerValid(m) {
		return nil, errF23
	}
	return json.Marshal(m)
}
func f23Load(raw []byte, expected string) (f23Ledger, error) {
	if f3Hash(raw) != expected {
		return f23Ledger{}, errF23
	}
	var m f23Ledger
	if json.Unmarshal(raw, &m) != nil || !f23LedgerValid(m) {
		return f23Ledger{}, errF23
	}
	again, e := f23Snapshot(m)
	if e != nil || !bytes.Equal(again, raw) {
		return f23Ledger{}, errF23
	}
	return m, nil
}
func f23SelectOnline(m f23Ledger) (int, int) {
	counts := [7]int{}
	used := 0
	for i := len(m.Credits) - 1; i >= 0 && used < 12; i-- {
		r := m.Credits[i]
		if r.Value < 0 {
			continue
		}
		used++
		for k := 0; k < 7; k++ {
			if m.ControlPreds[r.Step][k] == r.Value {
				counts[k]++
			}
		}
	}
	best := 0
	for k := 1; k < 7; k++ {
		if counts[k] > counts[best] {
			best = k
		}
	}
	return best, used*7 + 7
}

type F23Window struct {
	Name             string                `json:"name"`
	Start            int                   `json:"start"`
	End              int                   `json:"end"`
	Correct          [f23KindsCount]int    `json:"correct"`
	Trace            [f23KindsCount]string `json:"trace"`
	Work             [f23KindsCount]int    `json:"work"`
	SelectorIDs      string                `json:"selector_ids"`
	DistinctRolling8 int                   `json:"distinct_rolling8"`
}
type F23Arm struct {
	Seed                 uint32       `json:"seed"`
	Policy               string       `json:"policy"`
	TraceSHA256          string       `json:"trace_sha256"`
	CheckpointSHA256     string       `json:"checkpoint_sha256"`
	FinalSHA256          string       `json:"final_sha256"`
	CheckpointCredits    int          `json:"checkpoint_credits"`
	FinalCredits         int          `json:"final_credits"`
	Pending              int          `json:"pending"`
	ColdMatches          bool         `json:"cold_matches"`
	MaxArchiveCount      int          `json:"max_archive_count"`
	Windows              [3]F23Window `json:"windows"`
	HindsightBestName    string       `json:"hindsight_best_name"`
	HindsightBestScore   int          `json:"hindsight_best_score"`
	GainSelector         int          `json:"gain_selector"`
	RecoveryGainSelector int          `json:"recovery_gain_selector"`
	GainNoArchive        int          `json:"gain_no_archive"`
	GainUniform          int          `json:"gain_uniform"`
	GainWrongCredit      int          `json:"gain_wrong_credit"`
	GainRandom           int          `json:"gain_random"`
	LateCRetention       bool         `json:"late_c_retention"`
	Passes               bool         `json:"passes"`
}

func f23Recovery(trace string) int {
	if len(trace) != 16 {
		return 16
	}
	for i := 0; i <= 13; i++ {
		if trace[i:i+3] == "111" {
			return i
		}
	}
	return 16
}
func f23Run(seed uint32, policy string, cold bool) (F23Arm, []byte, error) {
	if _, e := f23Laws(seed); e != nil || policy != "balanced" && policy != "skewed" {
		return F23Arm{}, nil, errF23
	}
	out := F23Arm{Seed: seed, Policy: policy, Windows: [3]F23Window{
		{Name: "novel-C", Start: 64, End: 79}, {Name: "late-C", Start: 80, End: 95}, {Name: "return-A", Start: 96, End: 111},
	}}
	m := f23Ledger{Credits: make([]f20Credit, 0, F23Actions), Pending: make([]f20Probe, 0, 2), ControlPreds: make([][7]int, 0, F23Actions)}
	for t := 0; t < F23Actions; t++ {
		if t >= 2 {
			due := m.Pending[0]
			if due.Step != t-2 {
				return F23Arm{}, nil, errF23
			}
			obs, e := f23Observation(seed, due.Step, due.Cue, due.Action)
			if e != nil {
				return F23Arm{}, nil, e
			}
			m.Credits = append(m.Credits, f20Credit{Step: due.Step, Cue: due.Cue, Action: due.Action, WrongAction: due.WrongAction, Value: obs})
			m.Pending = m.Pending[1:]
		}
		cue, action, e := f23ActionCue(seed, policy, t)
		if e != nil {
			return F23Arm{}, nil, e
		}
		var preds [f23KindsCount]int
		var works [f23KindsCount]int
		preds[0], works[0], out.MaxArchiveCount, e = f23CandidateWithCount(m.Credits, cue, action, t, "regime-belief", out.MaxArchiveCount)
		if e != nil {
			return F23Arm{}, nil, e
		}
		var control [7]int
		for k := 0; k < 7; k++ {
			control[k], works[k+1], e = f23Conventional(k, m.Credits, cue, action)
			if e != nil {
				return F23Arm{}, nil, e
			}
			preds[k+1] = control[k]
		}
		selector, swork := f23SelectOnline(m)
		preds[8], works[8] = control[selector], swork
		for k, kind := range []string{"no-archive", "uniform-retrieval", "wrong-credit", "random-retrieval"} {
			preds[9+k], works[9+k], _, e = f23Belief(m.Credits, cue, action, t, kind)
			if e != nil {
				return F23Arm{}, nil, e
			}
		}
		for wi := range out.Windows {
			w := &out.Windows[wi]
			if t < w.Start || t > w.End {
				continue
			}
			truth, e := f23Truth(seed, t, cue, action)
			if e != nil {
				return F23Arm{}, nil, e
			}
			w.SelectorIDs += string(rune('0' + selector))
			if preds[0] != preds[3] {
				w.DistinctRolling8++
			}
			for k := range preds {
				if works[k] <= 0 {
					return F23Arm{}, nil, errF23
				}
				w.Work[k] += works[k]
				if preds[k] == truth {
					w.Correct[k]++
					w.Trace[k] += "1"
				} else {
					w.Trace[k] += "0"
				}
			}
		}
		wrong := 0
		if t > 0 {
			wrong = m.Pending[len(m.Pending)-1].Action
		}
		m.Pending = append(m.Pending, f20Probe{Step: t, Cue: cue, Action: action, WrongAction: wrong})
		m.ControlPreds = append(m.ControlPreds, control)
		m.Seen++
		if !f23LedgerValid(m) {
			return F23Arm{}, nil, errF23
		}
		if t == 95 {
			out.CheckpointCredits = len(m.Credits)
			raw, e := f23Snapshot(m)
			if e != nil {
				return F23Arm{}, nil, e
			}
			out.CheckpointSHA256 = f3Hash(raw)
			if cold {
				restored, e := f23Load(raw, out.CheckpointSHA256)
				if e != nil || !reflect.DeepEqual(restored, m) {
					return F23Arm{}, nil, errF23
				}
				m = restored
			}
		}
	}
	out.FinalCredits = len(m.Credits)
	out.Pending = len(m.Pending)
	raw, e := f23Snapshot(m)
	if e != nil {
		return F23Arm{}, nil, e
	}
	out.FinalSHA256 = f3Hash(raw)
	out.TraceSHA256 = f8Digest("FORGE-EUREKA-F23-CREDITED-TRACE-V1\n", m)
	out.ColdMatches = out.CheckpointCredits == 94 && out.FinalCredits == 126 && out.Pending == 2 &&
		len(m.Pending) == 2 && m.Pending[0].Step == 126 && m.Pending[1].Step == 127
	ret := out.Windows[2]
	for k := 1; k <= 7; k++ {
		if ret.Correct[k] > out.HindsightBestScore || out.HindsightBestName == "" {
			out.HindsightBestScore = ret.Correct[k]
			out.HindsightBestName = f23Kinds()[k]
		}
	}
	out.GainSelector = ret.Correct[0] - ret.Correct[8]
	out.RecoveryGainSelector = f23Recovery(ret.Trace[8]) - f23Recovery(ret.Trace[0])
	out.GainNoArchive = ret.Correct[0] - ret.Correct[9]
	out.GainUniform = ret.Correct[0] - ret.Correct[10]
	out.GainWrongCredit = ret.Correct[0] - ret.Correct[11]
	out.GainRandom = ret.Correct[0] - ret.Correct[12]
	out.LateCRetention = out.Windows[1].Correct[0] >= out.Windows[1].Correct[8]-2
	out.Passes = out.ColdMatches && out.MaxArchiveCount > 0 && out.LateCRetention &&
		out.GainSelector >= 2 && out.RecoveryGainSelector >= 1 && out.GainNoArchive >= 2 &&
		out.GainWrongCredit >= 2 && out.GainUniform >= 1 && out.GainRandom >= 1 && ret.DistinctRolling8 >= 2
	for _, w := range out.Windows {
		if len(w.SelectorIDs) != 16 {
			return F23Arm{}, nil, errF23
		}
		for k := 0; k < f23KindsCount; k++ {
			if len(w.Trace[k]) != 16 || w.Correct[k] < 0 || w.Correct[k] > 16 || w.Work[k] < 1 {
				return F23Arm{}, nil, errF23
			}
		}
	}
	return out, raw, nil
}
func f23CandidateWithCount(records []f20Credit, cue, action, t int, kind string, priorMax int) (int, int, int, error) {
	v, w, n, e := f23Belief(records, cue, action, t, kind)
	if n < priorMax {
		n = priorMax
	}
	return v, w, n, e
}
func f23Arm(seed uint32, policy string) (F23Arm, error) {
	a, raw, e := f23Run(seed, policy, true)
	b, original, e2 := f23Run(seed, policy, false)
	if e != nil || e2 != nil || !reflect.DeepEqual(a, b) || !bytes.Equal(raw, original) {
		return F23Arm{}, errF23
	}
	return a, nil
}

type F23Report struct {
	Schema                    string    `json:"schema"`
	ParentF22Commit           string    `json:"parent_f22_commit"`
	EarlierNegativesPreserved bool      `json:"earlier_negatives_preserved"`
	Seeds                     [2]uint32 `json:"seeds"`
	Policies                  [2]string `json:"policies"`
	Actions                   int       `json:"actions"`
	FeedbackDelay             int       `json:"feedback_delay"`
	Novel                     [2]int    `json:"novel"`
	Late                      [2]int    `json:"late"`
	Return                    [2]int    `json:"return"`
	MinimumGain               int       `json:"minimum_gain"`
	Arms                      []F23Arm  `json:"arms"`
	PassingArms               int       `json:"passing_arms"`
	TotalRuleWork             int       `json:"total_rule_work"`
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

func f23Digest(x F23Report) string {
	x.DigestSHA256 = ""
	return f8Digest("FORGE-EUREKA-F23-LATENT-REGIME-DEV-V1\n", x)
}
func F23Development() (F23Report, error) {
	out := F23Report{Schema: F23Schema, ParentF22Commit: F23F22Parent, EarlierNegativesPreserved: true,
		Seeds: f23Seeds(), Policies: f23Policies(), Actions: F23Actions, FeedbackDelay: 2,
		Novel: [2]int{64, 79}, Late: [2]int{80, 95}, Return: [2]int{96, 111}, MinimumGain: 2,
		DevelopmentOnly: true, Arms: make([]F23Arm, 0, 4)}
	for _, seed := range out.Seeds {
		for _, policy := range out.Policies {
			a, e := f23Arm(seed, policy)
			if e != nil {
				return F23Report{}, e
			}
			out.Arms = append(out.Arms, a)
			if a.Passes {
				out.PassingArms++
			}
			for _, w := range a.Windows {
				for _, v := range w.Work {
					out.TotalRuleWork += v
				}
			}
		}
	}
	if len(out.Arms) != 4 || out.TotalRuleWork <= 0 {
		return F23Report{}, errF23
	}
	out.Classification = F23NoGo
	if out.PassingArms == 4 {
		out.Classification = F23Signal
	}
	out.DigestSHA256 = f23Digest(out)
	return out, nil
}

var f23Reference struct {
	once   sync.Once
	report F23Report
	err    error
}

func F23Validate(x F23Report) error {
	if x.Schema != F23Schema || x.DigestSHA256 != f23Digest(x) || x.ParentF22Commit != F23F22Parent ||
		!x.DevelopmentOnly || !x.EarlierNegativesPreserved || x.FirstUseConsumed || x.ScientificAccepted ||
		x.WholeProcessCostProven || x.OwnerEligible || x.DispatchAuthorized || x.ActiveResearchChanged ||
		x.AgentCalls != 0 || x.PaidAPICalls != 0 {
		return errF23
	}
	f23Reference.once.Do(func() { f23Reference.report, f23Reference.err = F23Development() })
	if f23Reference.err != nil || !reflect.DeepEqual(x, f23Reference.report) {
		return errF23
	}
	return nil
}
