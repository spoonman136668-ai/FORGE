package workerboundary

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func receipt(t *testing.T,w workerreconcile.Expected,priv ed25519.PrivateKey,stage string)workerreconcile.Signed{
 t.Helper()
 r:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:w.Lane,ExperimentID:w.ExperimentID,
  FrozenSHA256:w.FrozenSHA256,IntentSHA256:w.IntentSHA256,OriginalRunID:w.OriginalRunID,
  WorkerID:w.WorkerID,OwnerEpoch:w.OwnerEpoch,Stage:stage}
 if stage=="TERMINAL"{r.EvidenceSHA256=strings.Repeat("c",64)}
 raw,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 // Test signer uses the versioned worker protocol domain.
 return workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(priv,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...)))}
}
func TestWorkerBoundaryNoReplayAndEpochDenial(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY integrated worker"))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 w:=workerreconcile.Expected{Lane:"Wingless",ExperimentID:"existing_parent",FrozenSHA256:strings.Repeat("a",64),
  IntentSHA256:strings.Repeat("b",64),OriginalRunID:"original_one",OwnerEpoch:9,WorkerID:"existing_worker",
  WorkerPublicKey:priv.Public().(ed25519.PublicKey)}
 j:=researchstate.New()
 previous:=researchstate.Phase("")
 for _,phase:=range []researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,
  researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing}{
  head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  e:=researchstate.Event{Lane:w.Lane,ExperimentID:w.ExperimentID,FrozenSHA256:w.FrozenSHA256,
   From:previous,To:phase,IrreversibleRisk:phase==researchstate.Executing}
  if phase==researchstate.Qualified||phase==researchstate.Authorized||phase==researchstate.Executing{
   e.EvidenceSHA256=w.IntentSHA256
  }
  j,err=researchstate.Append(j,e,head);if err!=nil{t.Fatal(err)}
  previous=phase
 }
 x:=Input{Journal:j,Lane:w.Lane,ExperimentID:w.ExperimentID,ExpectedWorker:w,OwnerID:"CKB",OwnerEpoch:9,NowUnix:100,
  Lease:workerlease.Lease{Lane:w.Lane,ExperimentID:w.ExperimentID,IntentSHA256:w.IntentSHA256,
   OwnerID:"CKB",OwnerEpoch:9,WorkerID:w.WorkerID,LeaseSequence:1,ExpiresAtUnix:10,FirstUseRisk:true}}
 if outcome,err:=Inspect(x);err!=nil||outcome!=Reconcile{t.Fatal("missing receipt replayed",outcome,err)}
 terminal:=receipt(t,w,priv,"TERMINAL")
 x.Terminal=&terminal
 if outcome,err:=Inspect(x);err!=nil||outcome!=ReviewEvidence{t.Fatal("valid terminal rejected",outcome,err)}
 x.OwnerEpoch=10
 if _,err:=Inspect(x);err==nil{t.Fatal("revoked owner accepted signed receipt")}
 x.OwnerEpoch=9;terminal.Receipt.Lane="Yggdrasil"
 if _,err:=Inspect(x);err==nil{t.Fatal("cross-lane terminal accepted")}
}
