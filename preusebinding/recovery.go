package preusebinding

// R37: reconcile an already-consumed original without recreating a permit.
// This is a strict read-only recovery classification, NOT dispatch authority.
import "errors"

var ErrRecovery=errors.New("R37_FIRST_USE_RECOVERY_NEEDS_INDEPENDENT_OWNER_REVIEW")
const RecoverySchema="forge.r37.original-recovery-observation.v1"

type RecoveryEvidence struct{
 OriginalKeySHA256 string
 DecisionSHA256 string
 OwnerEpoch uint64
 Sequence uint64
 DatabaseClaimPresent bool
 ClaimIdentityMatches bool
 IndependentlyWitnessedClaim bool
 WorkerStartedReceiptPresent bool
 WorkerTerminalReceiptPresent bool
 StartedAndTerminalIdentityMatch bool
}
type RecoveryReport struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 CanRetry bool `json:"can_retry"`
 CanDispatch bool `json:"can_dispatch"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ExternalFirstUseVerified bool `json:"external_first_use_verified"`
}
func Reconcile(c Claim,e RecoveryEvidence)(RecoveryReport,error){
 zero:=RecoveryReport{}
 if !validHex(c.OriginalKeySHA256,64)||!validHex(c.FrozenPredecisionSHA256,64)||
  c.OwnerEpoch==0||c.ClaimedSequence==0||c.ScientificAuthorized||
  e.OriginalKeySHA256!=c.OriginalKeySHA256||
  e.DecisionSHA256!=c.FrozenPredecisionSHA256||
  e.OwnerEpoch!=c.OwnerEpoch||e.Sequence!=c.ClaimedSequence{
  return zero,ErrRecovery
 }
 if !e.DatabaseClaimPresent||!e.ClaimIdentityMatches||!e.IndependentlyWitnessedClaim{
  return zero,ErrRecovery
 }
 status:="CONSUMED_UNCERTAIN_NO_RETRY"
 if e.WorkerStartedReceiptPresent&&e.WorkerTerminalReceiptPresent&&e.StartedAndTerminalIdentityMatch{
  status="CONSUMED_TERMINAL_NEEDS_SCIENTIFIC_REVIEW"
 }else if e.WorkerTerminalReceiptPresent&&!e.WorkerStartedReceiptPresent{
  return zero,ErrRecovery
 }else if e.WorkerStartedReceiptPresent&&!e.StartedAndTerminalIdentityMatch{
  status="CONSUMED_INTERRUPTED_NO_RETRY"
 }
 return RecoveryReport{Schema:RecoverySchema,Status:status,FirstUseConsumed:true,
  ExternalFirstUseVerified:false},nil
}
