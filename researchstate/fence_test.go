package researchstate

import (
 "context"
 "errors"
 "strings"
 "testing"
)
type fakeFence struct{current Fence;readErr error;casErr error;approve bool;calls int}
func(f *fakeFence)ReadFence(context.Context)(Fence,error){return f.current,f.readErr}
func(f *fakeFence)CompareAndSwapHead(_ context.Context,expected Fence,next string)(bool,error){
 f.calls++
 if f.casErr!=nil{return false,f.casErr}
 if !f.approve||f.current!=expected{return false,nil}
 f.current.JournalHeadSHA256=next
 return true,nil
}
func TestFencedCommitAndStaleOwner(t *testing.T){
 j:=New();ev:=Event{Lane:"Wingless",ExperimentID:"existing_w_1",FrozenSHA256:strings.Repeat("a",64),To:Proposed}
 expected:=Fence{OwnerID:"forge-shadow-test",Epoch:17,JournalHeadSHA256:Genesis,Authenticated:true}
 a:=&fakeFence{current:expected,approve:true}
 next,err:=CommitFenced(context.Background(),a,expected.OwnerID,expected,j,ev)
 if err!=nil||len(next.Entries)!=1||a.calls!=1{t.Fatal(err)}
 if _,err:=CommitFenced(context.Background(),a,expected.OwnerID,expected,j,ev);!errors.Is(err,ErrBlocked){t.Fatal("stale fence accepted")}
}
func TestFenceRejectsSplitBrainAndUnknownCAS(t *testing.T){
 j:=New();e:=Event{Lane:"Yggdrasil",ExperimentID:"existing_y_1",FrozenSHA256:strings.Repeat("b",64),To:Proposed}
 good:=Fence{OwnerID:"forge-shadow-test",Epoch:3,JournalHeadSHA256:Genesis,Authenticated:true}
 for _,tc:=range []struct{name string;observed Fence;err error;approve bool;want error}{
  {"unknown commit",good,errors.New("timeout"),true,ErrIndeterminate},
  {"conflict",good,nil,false,ErrBlocked},
  {"fenced by new owner",Fence{OwnerID:"another",Epoch:4,JournalHeadSHA256:Genesis,Authenticated:true},nil,true,ErrBlocked},
  {"unauthenticated head",Fence{OwnerID:"forge-shadow-test",Epoch:3,JournalHeadSHA256:Genesis},nil,true,ErrBlocked},
 }{
  t.Run(tc.name,func(t *testing.T){
   a:=&fakeFence{current:tc.observed,casErr:tc.err,approve:tc.approve}
   _,err:=CommitFenced(context.Background(),a,good.OwnerID,good,j,e)
   if !errors.Is(err,tc.want){t.Fatalf("wanted %v got %v",tc.want,err)}
  })
 }
}
