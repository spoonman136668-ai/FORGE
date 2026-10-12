package shadowcore

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// CutoverReadiness is a fail-closed shadow gate. It never deactivates CKB,
// activates FORGE, creates lanes, or issues a scientific authorization.
type CutoverReadiness struct {
 ExistingWinglessCustodyAuthenticated bool
 ExistingYggdrasilCustodyAuthenticated bool
 OldOwnerQuiescenceAuthenticated bool
 OldOwnerExecutionRevoked bool
 IndependentFenceVerified bool
 IndependentOriginalLedgersReconciled bool
 WorkerEpochEnforced bool
 FinalIntegrationRegressionPassed bool
 OriginalScientificCyclesVerified bool
}
var ErrCutoverBlocked=errors.New("FORGE_CUTOVER_NOT_QUALIFIED")
func CheckCutover(j researchstate.Journal,r CutoverReadiness)error {
 snapshot,err:=Observe(j);if err!=nil{return ErrCutoverBlocked}
 if len(snapshot.Wingless)==0||len(snapshot.Yggdrasil)==0||
 !r.ExistingWinglessCustodyAuthenticated||!r.ExistingYggdrasilCustodyAuthenticated||
 !r.OldOwnerQuiescenceAuthenticated||!r.OldOwnerExecutionRevoked||
 !r.IndependentFenceVerified||!r.IndependentOriginalLedgersReconciled||
 !r.WorkerEpochEnforced||!r.FinalIntegrationRegressionPassed||
 !r.OriginalScientificCyclesVerified{return ErrCutoverBlocked}
 // This is still only a data preflight; any transition requires a separate
 // explicit operator authorization and independently atomic handoff service.
 return nil
}
