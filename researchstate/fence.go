package researchstate

import (
 "context"
 "errors"
)

// Fence is an externally authenticated, monotonically increasing owner epoch.
// The epoch must be enforced by the actual independent durable authority and
// by every downstream worker. A local file lock is NEVER an authority fence.
type Fence struct {
 OwnerID string
 Epoch uint64
 JournalHeadSHA256 string
 Authenticated bool
}
type FenceAuthority interface {
 ReadFence(context.Context)(Fence,error)
 CompareAndSwapHead(context.Context,Fence,string)(bool,error)
}
var ErrIndeterminate=errors.New("FORGE_FENCED_COMMIT_INDETERMINATE_NO_DISPATCH")

// CommitFenced validates a proposed transition locally, then offers its new
// head to an external CAS authority. A timeout, conflict, or uncertain outcome
// never authorizes a worker launch. No caller can acquire new authority here.
func CommitFenced(ctx context.Context, a FenceAuthority, owner string, expected Fence, j Journal, ev Event)(Journal,error){
 if ctx==nil||ctx.Err()!=nil||a==nil||owner==""||
  expected.OwnerID!=owner||expected.Epoch==0||!expected.Authenticated{
  return Journal{},ErrBlocked
 }
 oldHead,err:=Head(j)
 if err!=nil||oldHead!=expected.JournalHeadSHA256{return Journal{},ErrBlocked}
 observed,err:=a.ReadFence(ctx)
 if err!=nil||!observed.Authenticated||observed!=expected{return Journal{},ErrBlocked}
 next,err:=Append(j,ev,oldHead);if err!=nil{return Journal{},err}
 nextHead,err:=Head(next);if err!=nil{return Journal{},ErrBlocked}
 accepted,err:=a.CompareAndSwapHead(ctx,expected,nextHead)
 if err!=nil{return Journal{},ErrIndeterminate}
 if !accepted{return Journal{},ErrBlocked}
 // Even CAS success alone is not worker-dispatch permission. The caller must
 // durably seal the journal, obtain an independent high-water witness, and
 // confirm the downstream execution fence before any first-use invocation.
 return next,nil
}
