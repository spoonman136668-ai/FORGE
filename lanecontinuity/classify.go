// Package lanecontinuity classifies research lane interruptions without
// invoking a model, dispatching experiments, or granting scientific authority.
package lanecontinuity

import "errors"

type Lane string
const (
 Wingless Lane = "Wingless"
 Yggdrasil Lane = "Yggdrasil"
)
type Failure string
const (
 None Failure = "NONE"
 ModelQuota Failure = "MODEL_QUOTA"
 ModelOffline Failure = "MODEL_OFFLINE"
 RunnerOffline Failure = "RUNNER_OFFLINE"
 TestFailure Failure = "TEST_FAILURE"
 NegativeResult Failure = "NEGATIVE_RESULT"
 EvidenceMissing Failure = "EVIDENCE_MISSING"
 AuthorityUnavailable Failure = "AUTHORITY_UNAVAILABLE"
 UnknownStart Failure = "UNKNOWN_START"
 BudgetExhausted Failure = "BUDGET_EXHAUSTED"
)
type Decision string
const (
 ContinueEligible Decision = "CONTINUE_ELIGIBLE"
 DeferModelWork Decision = "DEFER_MODEL_ONLY"
 RetryBounded Decision = "RETRY_BOUNDED"
 RequireQualification Decision = "REQUALIFY"
 PreserveNegative Decision = "ARCHIVE_NEGATIVE_AND_SELECT_PREREGISTERED_SUCCESSOR"
 HoldLane Decision = "HOLD_LANE"
)
type Input struct {
 Lane Lane
 Failure Failure
 // Eligibility is independently verified upstream. It cannot be asserted
 // merely by receiving this decision; no output grants execution permission.
 QualifiedWorkAvailable bool
 QualifiedAlternativeRunner bool
 RetryCount uint8
 RetryLimit uint8
}
type Output struct {
 Lane Lane
 Decision Decision
 OtherLaneUnaffected bool
 RequiresIndependentAdmission bool
}
var ErrInvalidInput = errors.New("FORGE_LANE_CONTINUITY_INVALID_INPUT")

// Classify is pure and deterministic. It makes a scheduling recommendation
// only. All scientific admission, budget, source pin, start receipt and
// external monotonic trust checks must occur independently before dispatch.
func Classify(in Input) (Output,error) {
 if in.Lane!=Wingless && in.Lane!=Yggdrasil {return Output{},ErrInvalidInput}
 if in.RetryLimit>3 || in.RetryCount>in.RetryLimit {return Output{},ErrInvalidInput}
 out:=Output{Lane:in.Lane,Decision:HoldLane,OtherLaneUnaffected:true,RequiresIndependentAdmission:true}
 switch in.Failure {
 case None:
  if in.QualifiedWorkAvailable {out.Decision=ContinueEligible}
 case ModelQuota,ModelOffline:
  if in.QualifiedWorkAvailable {out.Decision=ContinueEligible} else {out.Decision=DeferModelWork}
 case RunnerOffline:
  if in.QualifiedWorkAvailable && in.QualifiedAlternativeRunner {out.Decision=ContinueEligible}
 case TestFailure:
  if in.RetryCount<in.RetryLimit {out.Decision=RetryBounded} else {out.Decision=RequireQualification}
 case NegativeResult:
  out.Decision=PreserveNegative
 case EvidenceMissing,AuthorityUnavailable,UnknownStart,BudgetExhausted:
  // No retry/replay may bypass an unknown start, missing evidence,
  // exhausted budget or unavailable independent authority.
 case "":
  return Output{},ErrInvalidInput
 default:
  return Output{},ErrInvalidInput
 }
 return out,nil
}
