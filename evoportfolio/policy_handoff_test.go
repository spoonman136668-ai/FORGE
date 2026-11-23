package evoportfolio

import (
 "errors"
 "testing"
)
func TestPolicyToFrozenFinalistHandoff(t *testing.T){
 h:=policyFixture()
 f:=fixture()
 out,err:=PlanAfterReplay(h,ReplayPolicyDigest(h),f,Digest(f))
 if err!=nil{t.Fatal(err)}
 if out.Policy.SelectedPolicy!="diverse-efficiency"||out.Next.NextID!="alpha"||
  out.Next.DispatchAuthorized||out.Portfolio.DispatchAuthorized||
  out.DispatchAuthorized||out.Portfolio.ScientificAccepted{
   t.Fatalf("unexpected authority or selection: %+v",out)
 }
 f.Lane="Yggdrasil"
 if _,err:=PlanAfterReplay(h,ReplayPolicyDigest(h),f,Digest(f));!errors.Is(err,ErrFrozen){t.Fatalf("lane mixing accepted: %v",err)}
}
