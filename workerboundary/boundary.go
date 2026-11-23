// Package workerboundary provides the no-replay, read-only reconciliation
// boundary between the existing science journal and an independently
// authenticated worker. It does not launch or authorize workers.
package workerboundary

import (
 "errors"

 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)

var ErrUnsafe=errors.New("FORGE_WORKER_BOUNDARY_UNSAFE")

type Input struct {
 Journal researchstate.Journal
 Lane string
 ExperimentID string
 Lease workerlease.Lease
 OwnerID string
 OwnerEpoch uint64
 NowUnix uint64
 ExpectedWorker workerreconcile.Expected
 Started *workerreconcile.Signed
 Terminal *workerreconcile.Signed
}
type Disposition string
const(
 Reconcile Disposition="RECONCILE_WITHOUT_REPLAY"
 ReviewEvidence Disposition="REVIEW_TERMINAL_EVIDENCE"
 NoLaunch Disposition="NO_LAUNCH"
)
// Inspect checks journal identity BEFORE worker receipts and then evaluates
// ownership fencing before returning terminal evidence review. A valid signed
// receipt under a revoked epoch must never be treated as an active completion.
func Inspect(x Input)(Disposition,error){
 if x.Lane!="Wingless"&&x.Lane!="Yggdrasil"{return NoLaunch,ErrUnsafe}
 phase,found,err:=researchstate.Status(x.Journal,x.Lane,x.ExperimentID)
 if err!=nil||!found{return NoLaunch,ErrUnsafe}
 var frozen string
 for i:=len(x.Journal.Entries)-1;i>=0;i--{
  ev:=x.Journal.Entries[i]
  if ev.Lane==x.Lane&&ev.ExperimentID==x.ExperimentID{
   frozen=ev.FrozenSHA256;break
  }
 }
 if frozen==""||x.ExpectedWorker.Lane!=x.Lane||
 x.ExpectedWorker.ExperimentID!=x.ExperimentID||
 x.ExpectedWorker.FrozenSHA256!=frozen||
 x.ExpectedWorker.IntentSHA256!=x.Lease.IntentSHA256||
 x.ExpectedWorker.WorkerID!=x.Lease.WorkerID||
 x.ExpectedWorker.OwnerEpoch!=x.Lease.OwnerEpoch||
 x.Lease.Lane!=x.Lane||x.Lease.ExperimentID!=x.ExperimentID||
 x.Lease.OwnerID!=x.OwnerID||x.Lease.OwnerEpoch!=x.OwnerEpoch||
 x.OwnerID==""||x.OwnerEpoch==0{return NoLaunch,ErrUnsafe}
 leaseDecision,err:=workerlease.Inspect(x.Lease,x.NowUnix,x.OwnerID,x.OwnerEpoch)
 if err!=nil{return NoLaunch,ErrUnsafe}
 state,err:=workerreconcile.Reconcile(x.ExpectedWorker,x.Started,x.Terminal)
 if err!=nil{return NoLaunch,ErrUnsafe}
 if state==workerreconcile.Terminal{
  // Even a terminal receipt cannot be accepted if the journal was not at
  // original first-use risk. It merely permits independent evidence review.
  if phase!=researchstate.Executing&&phase!=researchstate.Quarantined&&phase!=researchstate.EvidenceSealed{
   return NoLaunch,ErrUnsafe
  }
  return ReviewEvidence,nil
 }
 if state==workerreconcile.Started||leaseDecision==workerlease.Quarantine||
  phase==researchstate.Authorized||phase==researchstate.Executing||
  phase==researchstate.Quarantined{return Reconcile,nil}
 // Silent worker and lease expiry are ALWAYS inconclusive.
 return Reconcile,nil
}
