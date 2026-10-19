package workerreconcile
import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
)
func TestMassT16CSignedExecutionIsStillNotScientificAuthority(t *testing.T){
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 wanted:=Expected{Lane:"MassResearch",ExperimentID:"mass-t16c-synthetic",
  FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),
  OriginalRunID:"mass-firstuse-1",OwnerEpoch:9,WorkerID:"fake-worker",WorkerPublicKey:pub}
 makeReceipt:=func(stage string)*Signed{
  evidence:=""
  if stage=="TERMINAL"{evidence=strings.Repeat("c",64)}
  v:=Receipt{Schema:Schema,Lane:wanted.Lane,ExperimentID:wanted.ExperimentID,
    FrozenSHA256:wanted.FrozenSHA256,IntentSHA256:wanted.IntentSHA256,
    OriginalRunID:wanted.OriginalRunID,OwnerEpoch:wanted.OwnerEpoch,
    WorkerID:wanted.WorkerID,Stage:stage,EvidenceSHA256:evidence}
  raw,_:=json.Marshal(v)
  sig:=ed25519.Sign(priv,append([]byte(prefix),raw...))
  return &Signed{Receipt:v,SignatureHex:hex.EncodeToString(sig)}
 }
 start,end:=makeReceipt("STARTED"),makeReceipt("TERMINAL")
 got,err:=Reconcile(wanted,start,end)
 if err!=nil||got!=Terminal{t.Fatalf("mass synthetic receipts invalid: %s %v",got,err)}
 if _,err:=Reconcile(wanted,nil,end);err!=nil{
  // Terminal-only authentic receipts are still evidence-review required;
  // never infer that first use is available to dispatch.
  t.Fatal(err)
 }
 end.Receipt.Lane="Wingless"
 if _,err:=Reconcile(wanted,start,end);err==nil{t.Fatal("wrong lane accepted")}
 end=makeReceipt("TERMINAL")
 end.Receipt.EvidenceSHA256=strings.Repeat("f",64)
 if _,err:=Reconcile(wanted,start,end);err==nil{t.Fatal("tampered receipt accepted")}
}
func TestMassT16CUnsupportedLaneRemainsBlocked(t *testing.T){
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 r:=Receipt{Schema:Schema,Lane:"CKB",ExperimentID:"unsafe",
  FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),
  OriginalRunID:"ckb-1",OwnerEpoch:1,WorkerID:"one",Stage:"STARTED"}
 raw,_:=json.Marshal(r)
 signed:=Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(priv,append([]byte(prefix),raw...)))}
 if err:=Verify(signed,Expected{Lane:"CKB",ExperimentID:r.ExperimentID,
  FrozenSHA256:r.FrozenSHA256,IntentSHA256:r.IntentSHA256,
  OriginalRunID:r.OriginalRunID,OwnerEpoch:r.OwnerEpoch,
  WorkerID:r.WorkerID,WorkerPublicKey:pub});err==nil{
  t.Fatal("unrelated CKB dispatch admission")
 }
}
