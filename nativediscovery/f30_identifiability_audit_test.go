package nativediscovery

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"math"
	"testing"
)

const (
	f30Schema       = "forge.eureka.f30-identifiability-audit.dev.v1"
	f30Parent       = "e5f77d596bcac00d4e6df2f9cd66d6468ae26d73"
	f30Undercovered = "F30_ACTION_UNDERCOVERED"
	f30Blur         = "F30_RECONSTRUCTION_BLUR_CONFIRMED"
	f30Inconclusive = "F30_INCONCLUSIVE"
)

type f30Cell struct {
	Bank                  string  `json:"bank"`
	Cue                   int     `json:"cue"`
	Action0Count          int     `json:"action0_count"`
	Action1Count          int     `json:"action1_count"`
	TruthDelta1           int     `json:"scorer_only_true_action1_delta"`
	DirectTrueProb        float64 `json:"direct_true_probability"`
	ReconstructedTrueProb float64 `json:"reconstructed_true_probability"`
	DirectNLL             float64 `json:"direct_true_nll"`
	ReconstructedNLL      float64 `json:"reconstructed_true_nll"`
	Penalty               float64 `json:"reconstruction_nll_penalty"`
	DirectEntropy         float64 `json:"direct_entropy"`
	ReconstructedEntropy  float64 `json:"reconstructed_entropy"`
}

type f30OracleWorld struct {
	Seed                       uint32  `json:"seed"`
	Schedule                   string  `json:"schedule"`
	ScorerOnlyOracleNLL        float64 `json:"scorer_only_oracle_nll"`
	BestTrainedConventionalNLL float64 `json:"best_trained_conventional_nll"`
	OracleHeadroom             float64 `json:"oracle_headroom"`
	RealActions                int     `json:"real_actions"`
}

type f30Receipt struct {
	Schema               string            `json:"schema"`
	Parent               string            `json:"parent"`
	TrainingWorlds       [2]uint32         `json:"training_worlds"`
	TrainingTransitions  int               `json:"training_transitions"`
	Cells                [8]f30Cell        `json:"cells"`
	MinimumCellSupport   int               `json:"minimum_cell_support"`
	MeanNLLPenalty       float64           `json:"mean_nll_penalty"`
	PositivePenaltyCells int               `json:"positive_penalty_cells"`
	MeanEntropyIncrease  float64           `json:"mean_entropy_increase"`
	Classification       string            `json:"classification"`
	OracleReference      [4]f30OracleWorld `json:"oracle_reference"`
	F29NegativePreserved bool              `json:"f29_negative_preserved"`
	OracleIsNotLearner   bool              `json:"oracle_is_not_learner"`
	FirstUseConsumed     bool              `json:"first_use_consumed"`
	ScientificAccepted   bool              `json:"scientific_accepted"`
	MatchedComputeProven bool              `json:"matched_compute_proven"`
	OwnerEligible        bool              `json:"owner_eligible"`
	DigestSHA256         string            `json:"digest_sha256"`
}

func f30Entropy(p [4]float64) float64 {
	total := 0.0
	for _, v := range p {
		if v > 0 {
			total -= v * math.Log(v)
		}
	}
	return total
}

func f30Oracle(seed uint32, schedule string) (float64, error) {
	w, e := f29NewWorld(seed, schedule)
	if e != nil {
		return 0, e
	}
	posterior, e := f27Posterior(w.Sensors)
	if e != nil {
		return 0, e
	}
	loss := 0.0
	for t := 0; t < 48; t++ {
		cue, e := f29Cue(seed, schedule, t)
		if e != nil {
			return 0, e
		}
		action, e := f29Action(seed, t)
		if e != nil {
			return 0, e
		}
		phase, e := f29Phase(seed, t)
		if e != nil {
			return 0, e
		}
		b, eff, e := f28Law(phase, cue) // ORACLE / SCORER ONLY.
		if e != nil {
			return 0, e
		}
		delta := (b + action*eff) % 4
		var forecast [4]float64
		for s, mass := range posterior {
			forecast[(s+delta)%4] += mass
		}
		actual, next, e := w.step(t, cue, action)
		if e != nil {
			return 0, e
		}
		loss -= math.Log(math.Max(forecast[actual], 1e-9))
		total := 0.0
		for s, v := range forecast {
			posterior[s] = v * f27Likelihood(next, s)
			total += posterior[s]
		}
		if total <= 0 || math.IsNaN(total) {
			return 0, errF29
		}
		for s := range posterior {
			posterior[s] /= total
		}
	}
	return loss / 48, nil
}

func f30Audit() (f30Receipt, error) {
	report := f30Receipt{Schema: f30Schema, Parent: f30Parent, TrainingWorlds: [2]uint32{241, 243}, TrainingTransitions: 128, MinimumCellSupport: 999, OracleIsNotLearner: true, F29NegativePreserved: true}
	trained, e := f28Train("factorized-bayes")
	if e != nil {
		return report, e
	}
	if trained.TrainingSeen != 128 {
		return report, errF29
	}
	banks := [2]struct {
		label    string
		seed     uint32
		schedule string
		id       byte
	}{
		{"A", 241, "balanced", 'A'}, {"B", 243, "skewed", 'B'},
	}
	auditModel := f29Model{A: trained.A, B: trained.B}
	totalPenalty, totalEntropy := 0.0, 0.0
	index := 0
	for bankIdx, bank := range banks {
		var counts [4][2]int
		for t := 0; t < 64; t++ {
			cue, e := f28Cue(bank.seed, bank.schedule, t)
			if e != nil {
				return report, e
			}
			action, e := f28Action(bank.seed, t)
			if e != nil {
				return report, e
			}
			counts[cue][action]++
		}
		for cue := 0; cue < 4; cue++ {
			var raw [4][2][4]float64
			if bankIdx == 0 {
				raw = trained.A
			} else {
				raw = trained.B
			}
			direct := f28DeltaProb(raw, cue, 1)
			pairs, e := f29Banks(auditModel, cue)
			if e != nil {
				return report, e
			}
			k := 0
			if bankIdx == 1 {
				k = 3
			}
			reconstructed := pairs[k]
			base, eff, e := f28Law(bank.id, cue) // scorer-only
			if e != nil {
				return report, e
			}
			truth := (base + eff) % 4
			directNLL := -math.Log(math.Max(direct[truth], 1e-12))
			recNLL := -math.Log(math.Max(reconstructed[truth], 1e-12))
			cell := f30Cell{
				Bank: bank.label, Cue: cue, Action0Count: counts[cue][0], Action1Count: counts[cue][1], TruthDelta1: truth,
				DirectTrueProb: direct[truth], ReconstructedTrueProb: reconstructed[truth], DirectNLL: directNLL, ReconstructedNLL: recNLL,
				Penalty: recNLL - directNLL, DirectEntropy: f30Entropy(direct), ReconstructedEntropy: f30Entropy(reconstructed),
			}
			if cell.Action0Count < report.MinimumCellSupport {
				report.MinimumCellSupport = cell.Action0Count
			}
			if cell.Action1Count < report.MinimumCellSupport {
				report.MinimumCellSupport = cell.Action1Count
			}
			for _, dist := range [2][4]float64{direct, reconstructed} {
				sum := 0.0
				for _, v := range dist {
					if v < 0 || v > 1 || math.IsNaN(v) {
						return report, errF29
					}
					sum += v
				}
				if math.Abs(sum-1) > 1e-8 {
					return report, errF29
				}
			}
			report.Cells[index] = cell
			index++
			totalPenalty += cell.Penalty
			totalEntropy += cell.ReconstructedEntropy - cell.DirectEntropy
			if cell.Penalty > 1e-12 {
				report.PositivePenaltyCells++
			}
		}
	}
	report.MeanNLLPenalty = totalPenalty / 8
	report.MeanEntropyIncrease = totalEntropy / 8
	if report.MinimumCellSupport < 3 {
		report.Classification = f30Undercovered
	} else if report.MeanNLLPenalty >= .05 && report.PositivePenaltyCells >= 6 {
		report.Classification = f30Blur
	} else {
		report.Classification = f30Inconclusive
	}
	f29, e := F29Development()
	if e != nil {
		return report, e
	}
	if f29.Classification != F29NoGo || f29.Passing != 0 {
		return report, errF29
	}
	for i, w := range f29Worlds() {
		oracle, e := f30Oracle(w.Seed, w.Schedule)
		if e != nil {
			return report, e
		}
		report.OracleReference[i] = f30OracleWorld{
			Seed: w.Seed, Schedule: w.Schedule, ScorerOnlyOracleNLL: oracle,
			BestTrainedConventionalNLL: f29.Arms[i].BestConventionalNLL,
			OracleHeadroom:             f29.Arms[i].BestConventionalNLL - oracle, RealActions: 48,
		}
	}
	tmp := report
	tmp.DigestSHA256 = ""
	encoded, e := json.Marshal(tmp)
	if e != nil {
		return report, e
	}
	digest := sha256.Sum256(encoded)
	report.DigestSHA256 = hex.EncodeToString(digest[:])
	return report, nil
}

func TestF30FrozenAudit(t *testing.T) {
	r, e := f30Audit()
	if e != nil {
		t.Fatal(e)
	}
	if r.Parent != f30Parent || r.Schema != f30Schema || r.TrainingTransitions != 128 || r.TrainingWorlds != [2]uint32{241, 243} ||
		r.FirstUseConsumed || r.ScientificAccepted || r.MatchedComputeProven || r.OwnerEligible || !r.OracleIsNotLearner || !r.F29NegativePreserved {
		t.Fatal("forged status/source")
	}
	minSupport := 999
	positives := 0
	penalty, entropy := 0.0, 0.0
	for i, c := range r.Cells {
		if c.Cue != i%4 || (i < 4 && c.Bank != "A") || (i >= 4 && c.Bank != "B") {
			t.Fatal("incorrect cell alignment")
		}
		if c.Action0Count+c.Action1Count != 0 && c.Action0Count+c.Action1Count > 64 {
			t.Fatal("incorrect counts")
		}
		if c.Action0Count < minSupport {
			minSupport = c.Action0Count
		}
		if c.Action1Count < minSupport {
			minSupport = c.Action1Count
		}
		if c.Penalty > 1e-12 {
			positives++
		}
		penalty += c.Penalty
		entropy += c.ReconstructedEntropy - c.DirectEntropy
	}
	cls := f30Inconclusive
	if minSupport < 3 {
		cls = f30Undercovered
	} else if penalty/8 >= .05 && positives >= 6 {
		cls = f30Blur
	}
	if r.MinimumCellSupport != minSupport || r.PositivePenaltyCells != positives ||
		math.Abs(r.MeanNLLPenalty-penalty/8) > 1e-9 || math.Abs(r.MeanEntropyIncrease-entropy/8) > 1e-9 || r.Classification != cls {
		t.Fatal("classification or arithmetic drift")
	}
	for i, w := range r.OracleReference {
		if w.Seed != f29Worlds()[i].Seed || w.RealActions != 48 || math.IsNaN(w.ScorerOnlyOracleNLL) {
			t.Fatal("oracle reference integrity")
		}
	}
	// The audit does not mutate the original F29 frozen result or claim authority.
	original, e := F29Development()
	if e != nil || F29Validate(original) != nil || original.Classification != F29NoGo {
		t.Fatal("F29 negative changed")
	}
	jsonRaw, e := json.Marshal(r)
	if e != nil {
		t.Fatal(e)
	}
	var decoded f30Receipt
	if json.Unmarshal(jsonRaw, &decoded) != nil || decoded.DigestSHA256 != r.DigestSHA256 {
		t.Fatal("receipt noncanonical")
	}
	t.Logf("F30_AUDIT_JSON=%s", string(jsonRaw))
}
