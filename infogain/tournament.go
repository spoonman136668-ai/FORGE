package infogain

// Bounded hypothesis tournaments reuse FORGE's validated, frozen forecasts
// to select follow-up experiments from caller-observed four-way outcomes.
// They do not execute experiments, call a model, admit science or dispatch.
import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"math/big"
)

const TournamentSchema = "forge.infogain.bounded-hypothesis-tournament.dev.v1"
const TournamentReceiptDomain = "FORGE-INFOGAIN-TOURNAMENT-DEV-V1\n"

type TournamentObservation struct {
	CandidateID     string `json:"candidate_id"`
	MechanismSHA256 string `json:"mechanism_sha256"`
	SourceSHA       string `json:"source_sha"`
	// 0=support, 1=refute, 2=limitation, 3=uninformative.
	Outcome        int    `json:"outcome"`
	EvidenceSHA256 string `json:"caller_supplied_evidence_sha256"`
}

type TournamentState struct {
	Schema                       string                  `json:"schema"`
	Lane                         string                  `json:"lane"`
	FrozenSHA256                 string                  `json:"frozen_sha256"`
	Observations                 []TournamentObservation `json:"observations"`
	ReceiptSHA256                string                  `json:"development_receipt_sha256"`
	DevelopmentOnly              bool                    `json:"development_only"`
	DispatchAuthorized           bool                    `json:"dispatch_authorized"`
	ScientificFirstUseAuthorized bool                    `json:"scientific_first_use_authorized"`
	ScientificAccepted           bool                    `json:"scientific_accepted"`
	AcceptedRefMutation          bool                    `json:"accepted_ref_mutation"`
}

type TournamentProbe struct {
	CandidateID                   string   `json:"candidate_id"`
	MechanismSHA256               string   `json:"mechanism_sha256"`
	SourceSHA                     string   `json:"source_sha"`
	ProjectedInformationMicrobits int64    `json:"projected_information_microbits"`
	EstimatedComputeUnits         int64    `json:"estimated_compute_units"`
	PosteriorBP                   []uint16 `json:"development_posterior_bp"`
	StepsCompleted                int      `json:"steps_completed"`
	BudgetRemaining               int64    `json:"compute_budget_remaining"`
	Exhausted                     bool     `json:"exhausted"`
	ForecastOnly                  bool     `json:"forecast_only"`
	DispatchAuthorized            bool     `json:"dispatch_authorized"`
}

func tournamentReceipt(s TournamentState) string {
	s.ReceiptSHA256 = ""
	raw, _ := json.Marshal(s)
	sum := sha256.Sum256(append([]byte(TournamentReceiptDomain), raw...))
	return hex.EncodeToString(sum[:])
}

// NewTournament creates a source-bound, locally checkable history.
// The SHA is not a signature, independent witness, or external-data proof.
func NewTournament(f Frozen, pin string) (TournamentState, error) {
	if err := validate(f, pin); err != nil {
		return TournamentState{}, err
	}
	s := TournamentState{Schema: TournamentSchema, Lane: f.Lane, FrozenSHA256: pin,
		Observations: []TournamentObservation{}, DevelopmentOnly: true}
	s.ReceiptSHA256 = tournamentReceipt(s)
	return s, nil
}

// Deterministic largest-remainder rounding preserves 10,000 bp of mass.
// Zero-likelihood outcomes fail closed; zero-mass hypotheses stay at zero.
// tournamentExactMass starts from the frozen unrounded prior and must be
// replayed with ALL observations. No mass is silently removed by a UI/score
// display rounding step.
func tournamentExactMass(prior []uint16) []*big.Int {
    masses := make([]*big.Int, len(prior))
    for i, bp := range prior {
        masses[i] = big.NewInt(int64(bp))
    }
    return masses
}

// Bounded by frozen 2..6 hypotheses and 8 steps. Exact integer products
// avoid irreversible loss of sub-basis-point hypotheses between observations.
// This is local forecast arithmetic, not independent evidence authentication.
func tournamentExactUpdate(masses []*big.Int, likelihood []uint16) ([]*big.Int, error) {
    if len(masses) != len(likelihood) || len(masses) < 2 || len(masses) > 6 {
        return nil, ErrFrozen
    }
    next := make([]*big.Int, len(masses))
    total := new(big.Int)
    for i, mass := range masses {
        if mass == nil || mass.Sign() < 0 {
            return nil, ErrFrozen
        }
        next[i] = new(big.Int).Mul(mass, big.NewInt(int64(likelihood[i])))
        total.Add(total, next[i])
    }
    if total.Sign() == 0 {
        return nil, ErrFrozen
    }
    return next, nil
}

// Quantization is only for the existing advisory probe interface; the
// replay state keeps the exact weights and does not feed these rounded
// values back into the next Bayes update.
func tournamentRoundExact(masses []*big.Int) ([]uint16, error) {
    if len(masses) < 2 || len(masses) > 6 {
        return nil, ErrFrozen
    }
    total := new(big.Int)
    for _, mass := range masses {
        if mass == nil || mass.Sign() < 0 {
            return nil, ErrFrozen
        }
        total.Add(total, mass)
    }
    if total.Sign() == 0 {
        return nil, ErrFrozen
    }
    out := make([]uint16, len(masses))
    rem := make([]*big.Int, len(masses))
    sum := 0
    tenThousand := big.NewInt(10000)
    for i, mass := range masses {
        quotient := new(big.Int)
        remainder := new(big.Int)
        quotient.QuoRem(new(big.Int).Mul(mass, tenThousand), total, remainder)
        if !quotient.IsInt64() || quotient.Int64() > 10000 {
            return nil, ErrFrozen
        }
        out[i] = uint16(quotient.Int64())
        rem[i] = remainder
        sum += int(out[i])
    }
    if sum > 10000 {
        return nil, ErrFrozen
    }
    for remaining := 10000 - sum; remaining > 0; remaining-- {
        best := -1
        for i, r := range rem {
            if best == -1 || r.Cmp(rem[best]) > 0 {
                best = i
            }
        }
        out[best]++
        rem[best] = big.NewInt(-1)
    }
    return out, nil
}

// One-step compatibility helper: internally exact, rounded at public
// interface. Replay must NOT chain this helper across observations.
func tournamentPosterior(prior []uint16, likelihood []uint16) ([]uint16, error) {
    next, err := tournamentExactUpdate(tournamentExactMass(prior), likelihood)
    if err != nil {
        return nil, err
    }
    return tournamentRoundExact(next)
}

func tournamentPick(f Frozen, prior []uint16, masses []*big.Int, used map[string]bool,
	reserved int64, families map[string]int, steps int) TournamentProbe {
	result := TournamentProbe{PosteriorBP: append([]uint16(nil), prior...),
		StepsCompleted: steps, BudgetRemaining: f.ComputeBudget - reserved,
		Exhausted: true, ForecastOnly: true}
	if steps >= f.MaxSelected {
		return result
	}
	// Scores must use the preserved exact posterior, NOT the rounded
	// basis-point display. Otherwise an unlikely but live hypothesis can
	// lose every discriminating follow-up probe until it revives.
	total := new(big.Int)
	for _, mass := range masses {
		total.Add(total, mass)
	}
	totalFloat, _ := new(big.Float).SetInt(total).Float64()
	exactPrior := make([]float64, len(masses))
	for i, mass := range masses {
		value, _ := new(big.Float).SetInt(mass).Float64()
		exactPrior[i] = value / totalFloat
	}
	var best Ranked
	var found *Candidate
	consumedMechanisms, consumedSources := map[string]bool{}, map[string]bool{}
	for _, h := range f.History {
		consumedMechanisms[h.MechanismSHA256] = true
		consumedSources[h.SourceSHA] = true
	}
	for i := range f.Candidates {
		c := &f.Candidates[i]
		if used[c.ID] || consumedMechanisms[c.MechanismSHA256] ||
			consumedSources[c.SourceSHA] || families[c.Family] >= f.MaxPerFamily ||
			c.ComputeUnits > result.BudgetRemaining {
			continue
		}
		score := measureWithPrior(f, *c, exactPrior)
		if score.ExpectedInformationMicrobits < f.MinInformationMicrobits {
			continue
		}
		if found == nil || score.PredictedValuePerComputeMicro > best.PredictedValuePerComputeMicro ||
			(score.PredictedValuePerComputeMicro == best.PredictedValuePerComputeMicro &&
				(score.ExpectedInformationMicrobits > best.ExpectedInformationMicrobits ||
					(score.ExpectedInformationMicrobits == best.ExpectedInformationMicrobits && c.ID < found.ID))) {
			found = c
			best = score
		}
	}
	if found != nil {
		result.CandidateID = found.ID
		result.MechanismSHA256 = found.MechanismSHA256
		result.SourceSHA = found.SourceSHA
		result.ProjectedInformationMicrobits = best.ExpectedInformationMicrobits
		result.EstimatedComputeUnits = found.ComputeUnits
		result.Exhausted = false
	}
	return result
}

func replayTournament(f Frozen, pin string, state TournamentState) (TournamentProbe, error) {
	var empty TournamentProbe
	if err := validate(f, pin); err != nil {
		return empty, err
	}
	if state.Schema != TournamentSchema || state.Lane != f.Lane ||
		state.FrozenSHA256 != pin || !state.DevelopmentOnly ||
		state.DispatchAuthorized || state.ScientificAccepted ||
		state.ScientificFirstUseAuthorized || state.AcceptedRefMutation ||
		len(state.Observations) > f.MaxSelected ||
		state.ReceiptSHA256 != tournamentReceipt(state) {
		return empty, ErrFrozen
	}
	prior := make([]uint16, len(f.Hypotheses))
	for i, h := range f.Hypotheses {
		prior[i] = h.PriorBP
	}
	// Keep nonzero mass across all replay steps; the probe exposes only
	// a rounded 10,000-basis-point view for the existing advisory contract.
	masses := tournamentExactMass(prior)
	used, evidence := map[string]bool{}, map[string]bool{}
	// Evidence consumed before this tournament cannot be silently reused.
	// This is a frozen-source replay guard, not external custody validation.
	for _, prior := range f.History {
		evidence[prior.EvidenceSHA256] = true
	}
	families := map[string]int{}
	var reserved int64
	for i, obs := range state.Observations {
		selected := tournamentPick(f, prior, masses, used, reserved, families, i)
		if selected.Exhausted || selected.CandidateID != obs.CandidateID ||
			selected.SourceSHA != obs.SourceSHA ||
			selected.MechanismSHA256 != obs.MechanismSHA256 ||
			obs.Outcome < 0 || obs.Outcome > 3 ||
			!validHex(obs.EvidenceSHA256, 64) || evidence[obs.EvidenceSHA256] {
			return empty, ErrFrozen
		}
		var candidate *Candidate
		for k := range f.Candidates {
			if f.Candidates[k].ID == obs.CandidateID {
				candidate = &f.Candidates[k]
				break
			}
		}
		if candidate == nil {
			return empty, ErrFrozen
		}
		likelihood := make([]uint16, len(f.Hypotheses))
		for h := range likelihood {
			likelihood[h] = candidate.OutcomeGivenHypothesis[h][obs.Outcome]
		}
		nextMasses, err := tournamentExactUpdate(masses, likelihood)
		if err != nil {
			return empty, err
		}
		prior, err = tournamentRoundExact(nextMasses)
		if err != nil {
			return empty, err
		}
		masses = nextMasses
		used[obs.CandidateID] = true
		evidence[obs.EvidenceSHA256] = true
		families[candidate.Family]++
		reserved += candidate.ComputeUnits
	}
	return tournamentPick(f, prior, masses, used, reserved, families, len(state.Observations)), nil
}

// NextTournamentProbe names the next candidate; it never invokes a runner.
func NextTournamentProbe(f Frozen, pin string, state TournamentState) (TournamentProbe, error) {
	return replayTournament(f, pin, state)
}

// An observation is caller-supplied and locally replayed, NOT authenticated
// as genuine external experimental evidence.
func RecordTournamentOutcome(f Frozen, pin string, state TournamentState,
	observation TournamentObservation) (TournamentState, error) {
	next, err := replayTournament(f, pin, state)
	if err != nil {
		return TournamentState{}, err
	}
	if next.Exhausted || next.CandidateID != observation.CandidateID ||
		next.MechanismSHA256 != observation.MechanismSHA256 ||
		next.SourceSHA != observation.SourceSHA || observation.Outcome < 0 ||
		observation.Outcome > 3 || !validHex(observation.EvidenceSHA256, 64) {
		return TournamentState{}, ErrFrozen
	}
	newState := state
	newState.Observations = append(append([]TournamentObservation(nil), state.Observations...), observation)
	newState.ReceiptSHA256 = tournamentReceipt(newState)
	if _, err := replayTournament(f, pin, newState); err != nil {
		return TournamentState{}, err
	}
	return newState, nil
}
