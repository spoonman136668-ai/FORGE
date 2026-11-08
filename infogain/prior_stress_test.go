package infogain

import (
 "reflect"
 "testing"
)

func TestPriorStressFindsOptimisticForecastsWithoutChangingSource(t *testing.T) {
 f := fixture()
 f.MinInformationMicrobits = 990000 // perfect 50/50 discrimination passes
 original := fixture()
 original.MinInformationMicrobits = 990000
 baseline, err := Recommend(f, Digest(f))
 if err != nil || len(baseline.Selected) != 2 { t.Fatalf("baseline invalid %v %+v", err, baseline) }
 report, err := AdvisePriorStress(f, Digest(f))
 if err != nil { t.Fatal(err) }
 if len(report.Rows) != 3 || report.PriorShiftBP != 1000 { t.Fatalf("incomplete report %+v", report) }
 for _, row := range report.Rows[:2] {
  if row.BaselineInformationMicrobits != 1000000 ||
   row.WorstInformationMicrobits >= f.MinInformationMicrobits ||
   row.WorstDonorHypothesis < 0 || row.WorstRecipientHypothesis < 0 ||
   row.Status != "PRIOR_SENSITIVE_FORECAST" {
   t.Fatalf("failure to reject fragile prior assumption: %+v", row)
  }
 }
 if report.Rows[2].Status != "INSUFFICIENT_INFORMATION_AT_FROZEN_PRIOR" {
  t.Fatalf("uninformative candidate upgraded: %+v", report.Rows[2])
 }
 if !reflect.DeepEqual(f, original) { t.Fatal("modified frozen source") }
 repeat, err := AdvisePriorStress(f, Digest(f))
 if err != nil || !reflect.DeepEqual(report, repeat) { t.Fatal("nondeterministic prior stress", err) }
 if !report.ForecastOnly || report.ScientificFirstUseAuthorized ||
  report.DispatchAuthorized || report.ScientificAccepted ||
  report.AcceptedRefMutation || report.OriginalSourceChanged {
  t.Fatalf("advisory gained execution or science authority: %+v", report)
 }
}

func TestPriorStressRetainsHistoricalNegativeWithoutReplay(t *testing.T) {
 f := fixture()
 f.History = []HistoryRecord{{
  MechanismSHA256: f.Candidates[0].MechanismSHA256,
  SourceSHA: f.Candidates[0].SourceSHA,
  EvidenceSHA256: repHex(64, "7"),
  Classification: "NEGATIVE",
 }}
 f.HistorySHA256 = HistoryDigest(f.History)
 report, err := AdvisePriorStress(f, Digest(f))
 if err != nil { t.Fatal(err) }
 if report.Rows[0].Status != "HISTORICAL_SOURCE_OR_MECHANISM_CONSUMED" ||
  report.Rows[0].BaselineInformationMicrobits != 0 ||
  !reflect.DeepEqual(report.HistoryPreserved, f.History) {
  t.Fatalf("historical negative was recycled or discarded %+v", report)
 }
}

func TestPriorStressBoundsExtremePriorsAndRejectsUnfrozenSource(t *testing.T) {
 f := fixture()
 f.Hypotheses[0].PriorBP = 1
 f.Hypotheses[1].PriorBP = 9999
 if _, err := AdvisePriorStress(f, Digest(f)); err != nil { t.Fatal(err) }
 f.Hypotheses[0].PriorBP = 5000
 if _, err := AdvisePriorStress(f, Digest(fixture())); err != ErrFrozen {
  t.Fatalf("tampered prior accepted: %v", err)
 }
 f = fixture()
 f.Candidates[0].ComputeUnits = 0
 if _, err := AdvisePriorStress(f, Digest(f)); err != ErrFrozen {
  t.Fatalf("unbounded or invalid budget accepted: %v", err)
 }
}
