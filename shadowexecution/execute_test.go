package shadowexecution

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/durableauthority"
 "github.com/spoonman136668-ai/forge/sandboxworker"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func keys()(ed25519.PublicKey,ed25519.PrivateKey,ed25519.PrivateKey){
 a:=sha256.Sum256([]byte("TEST ONLY shadow independent authority"))
 b:=sha256.Sum256([]byte("TEST ONLY shadow synthetic worker"))
 signer:=ed25519.NewKeyFromSeed(a[:])
 return signer.Public().(ed25519.PublicKey),signer,ed25519.NewKeyFromSeed(b[:])
}
func syntheticTask(t *testing.T,signer,worker ed25519.PrivateKey,lane,id,head string,epoch uint64,root string)Task{
 t.Helper()
 frozen:=strings.Repeat("a",64);intent:=strings.Repeat("b",64)
 grant:=durableauthority.Grant{Schema:durableauthority.GrantSchema,
 Lane:lane,OriginalID:id,FrozenSHA256:frozen,IntentSHA256:intent,
 OwnerID:"SYNTHETIC_TEST_OWNER",OwnerEpoch:epoch,ExpectedHeadSHA256:head}
 raw,err:=json.Marshal(grant);if err!=nil{t.Fatal(err)}
 grant.SignatureHex=hex.EncodeToString(ed25519.Sign(signer,append([]byte("FORGE-ORIGINAL-RESERVATION-GRANT-V1\n"),raw...)))
 expected:=workerreconcile.Expected{Lane:lane,ExperimentID:id,OriginalRunID:id,FrozenSHA256:frozen,
 IntentSHA256:intent,OwnerEpoch:epoch,WorkerID:"existing_synthetic_worker",WorkerPublicKey:worker.Public().(ed25519.PublicKey)}
 return Task{Grant:grant,Worker:sandboxworker.Task{Expected:expected,OwnerID:"SYNTHETIC_TEST_OWNER",Epoch:epoch},Root:root}
}
func checkReceipts(t *testing.T,root string,expected workerreconcile.Expected){
 t.Helper()
 children,err:=os.ReadDir(root);if err!=nil{t.Fatal(err)}
 started,terminal:=false,false
 for _,entry:=range children{
  name:=entry.Name()
  if !strings.HasPrefix(name,"start-")&&!strings.HasPrefix(name,"terminal-"){continue}
  content,err:=os.ReadFile(filepath.Join(root,name));if err!=nil{t.Fatal(err)}
  var signed workerreconcile.Signed
  if err:=json.Unmarshal(content,&signed);err!=nil{t.Fatal(err)}
  if err:=workerreconcile.Verify(signed,expected);err!=nil{t.Fatal(err)}
  if signed.Receipt.Stage=="STARTED"{started=true}
  if signed.Receipt.Stage=="TERMINAL"{terminal=true}
 }
 if !started||!terminal{t.Fatalf("incomplete synthetic receipts: started=%t terminal=%t",started,terminal)}
}
func TestTwoExistingLanesTwoConsecutiveSyntheticCycles(t *testing.T){
 public,signer,worker:=keys()
 store,err:=durableauthority.OpenShadow(t.TempDir(),public);if err!=nil{t.Fatal(err)}
 head:=strings.Repeat("0",64)
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  for cycle:=1;cycle<=2;cycle++{
   id:=strings.ToLower(lane)+"_original_"+string(rune('0'+cycle))
   root:=filepath.Join(t.TempDir(),"forge-synthetic-worker")
   task:=syntheticTask(t,signer,worker,lane,id,head,17,root)
   next,err:=RunOnce(context.Background(),store,task,worker)
   if err!=nil{t.Fatal(lane,cycle,err)}
   checkReceipts(t,root,task.Worker.Expected)
   head=next
   if _,err:=RunOnce(context.Background(),store,task,worker);!errors.Is(err,durableauthority.ErrConsumed){
    t.Fatalf("%s cycle %d original replayed: %v",lane,cycle,err)
   }
  }
 }
 if err:=store.Close();err!=nil{t.Fatal(err)}
}
func TestWorkerFailureAfterIrreversibleReservationIsQuarantined(t *testing.T){
 public,signer,worker:=keys()
 dir:=t.TempDir()
 store,err:=durableauthority.OpenShadow(dir,public);if err!=nil{t.Fatal(err)}
 root:=filepath.Join(t.TempDir(),"forge-synthetic-worker")
 if err:=os.Mkdir(root,0700);err!=nil{t.Fatal(err)}
 task:=syntheticTask(t,signer,worker,"Wingless","original_failure",strings.Repeat("0",64),8,root)
 _,err=RunOnce(context.Background(),store,task,worker)
 if !errors.Is(err,ErrOriginalRisk){t.Fatalf("worker failure not quarantined: %v",err)}
 if _,err=RunOnce(context.Background(),store,task,worker);!errors.Is(err,durableauthority.ErrConsumed){t.Fatal("failed original rerun",err)}
 if err=store.Close();err!=nil{t.Fatal(err)}
 opened,err:=durableauthority.OpenShadow(dir,public);if err!=nil{t.Fatal(err)}
 if _,err=RunOnce(context.Background(),opened,task,worker);!errors.Is(err,durableauthority.ErrConsumed){t.Fatal("original retried after restart",err)}
 if err=opened.Close();err!=nil{t.Fatal(err)}
}
func TestUnqualifiedWorkerPreflightDoesNotConsumeFirstUse(t *testing.T){
 public,signer,worker:=keys()
 dir:=t.TempDir();store,err:=durableauthority.OpenShadow(dir,public);if err!=nil{t.Fatal(err)}
 task:=syntheticTask(t,signer,worker,"Yggdrasil","original_unconsumed",strings.Repeat("0",64),1,filepath.Join(t.TempDir(),"forge-synthetic-worker"))
 wrongSeed:=sha256.Sum256([]byte("TEST ONLY wrong worker key"))
 wrong:=ed25519.NewKeyFromSeed(wrongSeed[:])
 if _,err:=RunOnce(context.Background(),store,task,wrong);!errors.Is(err,ErrUnsafe){t.Fatal("invalid worker accepted",err)}
 snapshot,err:=durableauthority.Load(dir,public)
 if err!=nil||len(snapshot.Entries)!=0{t.Fatal("preflight consumed unused original",err)}
 if err=store.Close();err!=nil{t.Fatal(err)}
}
