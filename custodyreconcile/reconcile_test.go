package custodyreconcile

import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/workerboundary"
 "github.com/spoonman136668-ai/forge/workerlease"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func signed(t *testing.T,priv ed25519.PrivateKey,r workerreconcile.Receipt)workerreconcile.Signed{
 t.Helper()
 b,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 return workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(priv,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),b...)))}
}
func TestDurableOriginalReceiptRequiredBeforeWorkerTerminal(t *testing.T){
 sum:=sha256.Sum256([]byte("custody integration test"))
 priv:=ed25519.NewKeyFromSeed(sum[:])
 exp:=workerreconcile.Expected{Lane:"Wingless",ExperimentID:"synth_existing",OriginalRunID:"original1",
  FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),
  WorkerID:"worker1",OwnerEpoch:7,WorkerPublicKey:priv.Public().(ed25519.PublicKey)}
 j:=researchstate.New();prev:=researchstate.Phase("")
 for _,phase:=range []researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,
  researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing}{
  head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  ev:=researchstate.Event{Lane:exp.Lane,ExperimentID:exp.ExperimentID,FrozenSHA256:exp.FrozenSHA256,
   From:prev,To:phase,IrreversibleRisk:phase==researchstate.Executing}
  if phase==researchstate.Qualified||phase==researchstate.Authorized||phase==researchstate.Executing{
   ev.EvidenceSHA256=exp.IntentSHA256
  }
  j,err=researchstate.Append(j,ev,head);if err!=nil{t.Fatal(err)}
  prev=phase
 }
 rec:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:exp.Lane,ExperimentID:exp.ExperimentID,
  OriginalRunID:exp.OriginalRunID,FrozenSHA256:exp.FrozenSHA256,IntentSHA256:exp.IntentSHA256,
  WorkerID:exp.WorkerID,OwnerEpoch:exp.OwnerEpoch,Stage:"STARTED"}
 start:=signed(t,priv,rec)
 rec.Stage="TERMINAL";rec.EvidenceSHA256=strings.Repeat("c",64)
 terminal:=signed(t,priv,rec)
 fingerprint,err:=workerreconcile.Fingerprint(start);if err!=nil{t.Fatal(err)}
 custody:=attemptjournal.Record{Schema:attemptjournal.Schema,Lane:exp.Lane,ExperimentID:exp.ExperimentID,
  OriginalRunID:exp.OriginalRunID,FrozenSHA256:exp.FrozenSHA256,IntentSHA256:exp.IntentSHA256,
  OwnerEpoch:exp.OwnerEpoch,WorkerID:exp.WorkerID,ReceiptSHA256:fingerprint,State:"ORIGINAL_RISK_RECORDED"}
 x:=workerboundary.Input{Journal:j,Lane:exp.Lane,ExperimentID:exp.ExperimentID,
  ExpectedWorker:exp,Started:&start,Terminal:&terminal,OwnerID:"old_owner",OwnerEpoch:exp.OwnerEpoch,NowUnix:100,
  Lease:workerlease.Lease{Lane:exp.Lane,ExperimentID:exp.ExperimentID,IntentSHA256:exp.IntentSHA256,
   OwnerID:"old_owner",OwnerEpoch:exp.OwnerEpoch,WorkerID:exp.WorkerID,LeaseSequence:1,
   ExpiresAtUnix:50,FirstUseRisk:true}}
 dir:=t.TempDir()
 if _,err:=Inspect(dir,x,custody);err==nil{t.Fatal("missing custody admitted")}
 if err:=attemptjournal.WriteOnce(dir,custody);err!=nil{t.Fatal(err)}
 if got,err:=Inspect(dir,x,custody);err!=nil||got!=workerboundary.ReviewEvidence{
  t.Fatal("qualified evidence review not allowed",got,err)
 }
 x.Started=nil
 if _,err:=Inspect(dir,x,custody);err==nil{t.Fatal("missing start signed receipt admitted")}
 x.Started=&start;x.OwnerEpoch++
 if _,err:=Inspect(dir,x,custody);err==nil{t.Fatal("stale epoch admitted")}
 x.OwnerEpoch--;x.Terminal=nil
 if got,err:=Inspect(dir,x,custody);err!=nil||got!=workerboundary.Reconcile{
  t.Fatal("silent terminal must reconcile without replay",got,err)
 }
}
