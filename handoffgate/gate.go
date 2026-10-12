// Package handoffgate combines original worker, lease and journal evidence.
// It is a read-only admission decision, never a queue consumer or authority.
package handoffgate

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
var ErrBlocked=errors.New("FORGE_ORIGINAL_HANDOFF_UNSAFE")
type Outcome string
const (
 ReconcileOnly Outcome="RECONCILE_ORIGINAL_NO_REPLAY"
 ReviewTerminal Outcome="REVIEW_AUTHENTICATED_TERMINAL"
 AwaitAuthority Outcome="AWAIT_INDEPENDENT_AUTHORITY"
)
type Input struct {
 Journal researchstate.Journal
 Lane string
 ExperimentID string
 Lease workerlease.Lease
 CurrentOwnerID string
 CurrentEpoch uint64
 NowUnix uint64
 Original workerreconcile.Expected
 Started *workerreconcile.Signed
 Terminal *workerreconcile.Signed
}
// Inspect is conservative: no returned disposition can authorize a launch.
func Inspect(x Input)(Outcome,error) {
 phase,found,err:=researchstate.Status(x.Journal,x.Lane,x.ExperimentID)
 if err!=nil||!found{return "",ErrBlocked}
 if x.Original.Lane!=x.Lane||x.Original.ExperimentID!=x.ExperimentID||
  x.Lease.Lane!=x.Lane||x.Lease.ExperimentID!=x.ExperimentID||
  x.Original.IntentSHA256!=x.Lease.IntentSHA256||
  x.Original.WorkerID!=x.Lease.WorkerID||
  x.Original.OwnerEpoch!=x.Lease.OwnerEpoch||
  x.Lease.OwnerID!=x.CurrentOwnerID||
  x.Lease.OwnerEpoch!=x.CurrentEpoch||
  x.CurrentOwnerID==""||x.CurrentEpoch==0{return "",ErrBlocked}
 state,err:=workerreconcile.Reconcile(x.Original,x.Started,x.Terminal)
 if err!=nil{return "",ErrBlocked}
 lease,err:=workerlease.Inspect(x.Lease,x.NowUnix,x.CurrentOwnerID,x.CurrentEpoch)
 if err!=nil{return "",ErrBlocked}
 if state==workerreconcile.Terminal{
  // A terminal receipt is evidence for independent admission, not success.
  return ReviewTerminal,nil
 }
 if state==workerreconcile.Started||lease==workerlease.Quarantine||
  phase==researchstate.Executing||phase==researchstate.Quarantined||
  phase==researchstate.Authorized{return ReconcileOnly,nil}
 if state==workerreconcile.Unknown {
  // An expired lease cannot prove original first-use was unconsumed.
  return ReconcileOnly,nil
 }
 return AwaitAuthority,nil
}
