package workerlease
import("errors";"strings";"testing")
func TestLeaseExpiryNeverReplaysOriginal(t *testing.T){
 l:=Lease{Lane:"Wingless",ExperimentID:"existing",IntentSHA256:strings.Repeat("a",64),OwnerID:"old",OwnerEpoch:9,WorkerID:"worker",LeaseSequence:1,ExpiresAtUnix:100}
 if got,err:=Inspect(l,99,"old",9);err!=nil||got!=Held{t.Fatal(got,err)}
 if got,err:=Inspect(l,101,"old",9);err!=nil||got!=Available{t.Fatal(got,err)}
 l.FirstUseRisk=true
 if got,err:=Inspect(l,101,"old",9);err!=nil||got!=Quarantine{t.Fatal(got,err)}
 if _,err:=Renew(l,"old",9,2,200);!errors.Is(err,ErrBlocked){t.Fatal("risky original lease renewed")}
}
func TestStaleOwnerAndLeaseSequenceRejected(t *testing.T){
 l:=Lease{Lane:"Yggdrasil",ExperimentID:"existing",IntentSHA256:strings.Repeat("b",64),OwnerID:"old",OwnerEpoch:9,WorkerID:"worker",LeaseSequence:1,ExpiresAtUnix:100}
 if _,err:=Inspect(l,101,"old",10);!errors.Is(err,ErrBlocked){t.Fatal("stale owner admitted")}
 if _,err:=Renew(l,"old",9,3,200);!errors.Is(err,ErrBlocked){t.Fatal("skipped sequence")}
 if _,err:=Renew(l,"new",9,2,200);!errors.Is(err,ErrBlocked){t.Fatal("foreign owner")}
 next,err:=Renew(l,"old",9,2,200);if err!=nil||next.LeaseSequence!=2{t.Fatal(err)}
}
