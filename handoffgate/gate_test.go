package handoffgate
import (
 "crypto/ed25519"
 "crypto/sha256"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func TestOriginalNeverInferredUnused(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY original worker"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 pin:=strings.Repeat("a",64);intent:=strings.Repeat("b",64)
 j:=researchstate.New()
 head,_:=researchstate.Head(j)
 next,err:=researchstate.Append(j,researchstate.Event{Lane:"Wingless",ExperimentID:"old1",FrozenSHA256:pin,To:researchstate.Proposed},head)
 if err!=nil{t.Fatal(err)}
 x:=Input{
  Journal:next,Lane:"Wingless",ExperimentID:"old1",
  Lease:workerlease.Lease{Lane:"Wingless",ExperimentID:"old1",IntentSHA256:intent,OwnerID:"CKB",OwnerEpoch:7,WorkerID:"worker",LeaseSequence:1,ExpiresAtUnix:20},
  CurrentOwnerID:"CKB",CurrentEpoch:7,NowUnix:100,
  Original:workerreconcile.Expected{Lane:"Wingless",ExperimentID:"old1",FrozenSHA256:pin,IntentSHA256:intent,OriginalRunID:"oldrun",OwnerEpoch:7,WorkerID:"worker",WorkerPublicKey:key.Public().(ed25519.PublicKey)},
 }
 got,err:=Inspect(x);if err!=nil||got!=ReconcileOnly{t.Fatal(got,err)}
 x.Lease.FirstUseRisk=true
 got,err=Inspect(x);if err!=nil||got!=ReconcileOnly{t.Fatal(got,err)}
 x.Original.OwnerEpoch=8
 if _,err:=Inspect(x);err==nil{t.Fatal("cross-epoch receipt accepted")}
 x.Original.OwnerEpoch=7;x.CurrentEpoch=8
 if _,err:=Inspect(x);err==nil{t.Fatal("stale owner admitted")}
}
