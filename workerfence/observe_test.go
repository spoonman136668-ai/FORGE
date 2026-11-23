package workerfence

import(
 "context"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func TestNoRemoteWitnessCanNeverGrantWorkerExecution(t *testing.T){
 anchor:=fsahead.Anchor{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_TEST",
  AuthorityEpoch:7,Sequence:0,HeadSHA256:researchlog.Genesis}
 lease:=workerlease.Lease{Lane:"Wingless",ExperimentID:"W-original",
  IntentSHA256:strings.Repeat("b",64),OwnerID:"FORGE_TEST_OWNER",
  OwnerEpoch:7,WorkerID:"W-TEST",LeaseSequence:1,ExpiresAtUnix:2000}
 if report,err:=Observe(context.Background(),nil,anchor,lease,1000);err==nil||
  report.WorkerDispatchAuthorized||report.ScienceActivated{
  t.Fatal("missing independent FSA witness became worker execution authority")
 }
 lease.FirstUseRisk=true
 if _,err:=Observe(context.Background(),nil,anchor,lease,1000);err==nil{
  t.Fatal("first-use risk accepted")
 }
}
func TestRemoteEpochEqualityIsStrictAndNotReplayClearance(t *testing.T){
 if same(fsahead.Anchor{ArchiveID:"one"},fsahead.Anchor{ArchiveID:"two"}){
  t.Fatal("authority changed archive identity")
 }
 if pinned(fsahead.Anchor{ArchiveID:strings.Repeat("a",64),KeyID:"K",
  AuthorityEpoch:1,Sequence:0,HeadSHA256:strings.Repeat("1",64)}){
  t.Fatal("invalid genesis state accepted")
 }
}
