package workerreconcile
import("crypto/ed25519";"crypto/sha256";"encoding/hex";"encoding/json";"strings";"testing")
func signed(t *testing.T,w Expected,key ed25519.PrivateKey,stage string)Signed{
 t.Helper()
 r:=Receipt{Schema:Schema,Lane:w.Lane,ExperimentID:w.ExperimentID,FrozenSHA256:w.FrozenSHA256,IntentSHA256:w.IntentSHA256,OriginalRunID:w.OriginalRunID,OwnerEpoch:w.OwnerEpoch,WorkerID:w.WorkerID,Stage:stage}
 if stage=="TERMINAL"{r.EvidenceSHA256=strings.Repeat("c",64)}
 b,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 return Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(key,append([]byte(prefix),b...)))}
}
func TestWorkerReconciliationAndNoReplay(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY worker signing seed"));key:=ed25519.NewKeyFromSeed(seed[:])
 w:=Expected{Lane:"Wingless",ExperimentID:"old_1",FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),OriginalRunID:"original_1",OwnerEpoch:23,WorkerID:"existing_worker",WorkerPublicKey:key.Public().(ed25519.PublicKey)}
 if state,err:=Reconcile(w,nil,nil);err!=nil||state!=Unknown{t.Fatal(state,err)}
 a,b:=signed(t,w,key,"STARTED"),signed(t,w,key,"TERMINAL")
 if state,err:=Reconcile(w,&a,nil);err!=nil||state!=Started{t.Fatal(state,err)}
 if state,err:=Reconcile(w,&a,&b);err!=nil||state!=Terminal{t.Fatal(state,err)}
 b.Receipt.OwnerEpoch=22
 if _,err:=Reconcile(w,&a,&b);err==nil{t.Fatal("stale epoch accepted")}
 b=signed(t,w,key,"TERMINAL");b.SignatureHex=strings.Repeat("0",128)
 if _,err:=Reconcile(w,nil,&b);err==nil{t.Fatal("forged signature accepted")}
 b=signed(t,w,key,"TERMINAL");b.Receipt.Lane="Yggdrasil"
 if _,err:=Reconcile(w,nil,&b);err==nil{t.Fatal("cross lane accepted")}
}
