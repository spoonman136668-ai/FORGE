package infogain

// Prior stress is an advisory sensitivity analysis of FROZEN experiment
// forecasts. It does not create a hypothesis, measure learning, rerank the
// native FORGE controller, dispatch, or authorize scientific first-use.
// At most 1,000 basis points of prior mass moves from one hypothesis to
// another. All original predictions, source identities and budgets stay fixed.
const PriorStressSchema = "forge.infogain.prior-stress-development.v1"
const PriorShiftBP uint16 = 1000

type PriorStressRow struct {
 ID string `json:"id"`
 MechanismSHA256 string `json:"mechanism_sha256"`
 SourceSHA string `json:"source_sha"`
 BaselineInformationMicrobits int64 `json:"baseline_information_microbits"`
 WorstInformationMicrobits int64 `json:"worst_information_microbits"`
 WorstValuePerComputeMicro int64 `json:"worst_value_per_compute_micro"`
 WorstDonorHypothesis int `json:"worst_donor_hypothesis"`
 WorstRecipientHypothesis int `json:"worst_recipient_hypothesis"`
 Status string `json:"status"`
}

type PriorStressReport struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenSHA256 string `json:"frozen_sha256"`
 PriorShiftBP uint16 `json:"prior_shift_bp"`
 Rows []PriorStressRow `json:"rows"`
 HistoryPreserved []HistoryRecord `json:"history_preserved"`
 HistorySHA256 string `json:"history_sha256"`
 ForecastOnly bool `json:"forecast_only"`
 OriginalSourceChanged bool `json:"original_source_changed"`
 ScientificFirstUseAuthorized bool `json:"scientific_first_use_authorized"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

// AdvisePriorStress probes whether the fixed forecasts are overly dependent
// on one chosen hypothesis prior. This is not a robust scientific lower bound:
// the predicted outcome distributions themselves remain unverified.
// Consumption is copied from the supplied frozen history, which is not an
// independently authenticated complete owner ledger.
func AdvisePriorStress(f Frozen, pin string) (PriorStressReport, error) {
 var empty PriorStressReport
 if err := validate(f, pin); err != nil { return empty, err }
 // Reuse the existing full-history and admissibility checks without changing
 // the ordinary recommendation or giving the advisory an execution path.
 if _, err := Recommend(f, pin); err != nil { return empty, err }
 out := PriorStressReport{
  Schema: PriorStressSchema, Lane: f.Lane, FrozenSHA256: pin,
  PriorShiftBP: PriorShiftBP, Rows: make([]PriorStressRow, 0, len(f.Candidates)),
  HistoryPreserved: append([]HistoryRecord{}, f.History...),
  HistorySHA256: f.HistorySHA256, ForecastOnly: true,
 }
 consumedMechanisms, consumedSources := map[string]bool{}, map[string]bool{}
 for _, history := range f.History {
  consumedMechanisms[history.MechanismSHA256] = true
  consumedSources[history.SourceSHA] = true
 }
 for _, candidate := range f.Candidates {
  row := PriorStressRow{
   ID: candidate.ID, MechanismSHA256: candidate.MechanismSHA256,
   SourceSHA: candidate.SourceSHA, WorstDonorHypothesis: -1,
   WorstRecipientHypothesis: -1,
  }
  if consumedMechanisms[candidate.MechanismSHA256] || consumedSources[candidate.SourceSHA] {
   row.Status = "HISTORICAL_SOURCE_OR_MECHANISM_CONSUMED"
   out.Rows = append(out.Rows, row)
   continue
  }
  original := measure(f, candidate)
  row.BaselineInformationMicrobits = original.ExpectedInformationMicrobits
  row.WorstInformationMicrobits = original.ExpectedInformationMicrobits
  row.WorstValuePerComputeMicro = original.PredictedValuePerComputeMicro
  // Enumerate each directed pair, transferring the largest admissible mass
  // (up to 10%). No post-result tuning or modification of frozen inputs.
  for donor := range f.Hypotheses {
   available := int(f.Hypotheses[donor].PriorBP) - 1
   if available <= 0 { continue }
   if available > int(PriorShiftBP) { available = int(PriorShiftBP) }
   for recipient := range f.Hypotheses {
    if recipient == donor { continue }
    stressed := f
    stressed.Hypotheses = append([]Hypothesis(nil), f.Hypotheses...)
    stressed.Hypotheses[donor].PriorBP -= uint16(available)
    stressed.Hypotheses[recipient].PriorBP += uint16(available)
    projected := measure(stressed, candidate)
    // Information and total advisory value have different objectives:
    // preserve their independent minima, not the score at the lowest MI.
    if projected.PredictedValuePerComputeMicro < row.WorstValuePerComputeMicro {
     row.WorstValuePerComputeMicro = projected.PredictedValuePerComputeMicro
    }
    if projected.ExpectedInformationMicrobits < row.WorstInformationMicrobits {
     row.WorstInformationMicrobits = projected.ExpectedInformationMicrobits
     row.WorstDonorHypothesis = donor
     row.WorstRecipientHypothesis = recipient
    }
   }
  }
  switch {
  case row.BaselineInformationMicrobits < f.MinInformationMicrobits:
   row.Status = "INSUFFICIENT_INFORMATION_AT_FROZEN_PRIOR"
  case row.WorstInformationMicrobits < f.MinInformationMicrobits:
   row.Status = "PRIOR_SENSITIVE_FORECAST"
  default:
   row.Status = "SURVIVES_PRIOR_STRESS_FORECAST_ONLY"
  }
  out.Rows = append(out.Rows, row)
 }
 return out, nil
}
