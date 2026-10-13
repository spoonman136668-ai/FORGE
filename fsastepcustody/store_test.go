package fsastepcustody

import (
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/workerfence"
)

func fixture(t *testing.T)(*Store,ed25519.PublicKey,ed25519.PrivateKey,string){
 t.Helper()
 pub,private,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 root:=filepath.Join(t.TempDir(),FolderName)
 store,err:=Provision(root,pub);if err!=nil{t.Fatal(err)}
 return store,pub,private,root
}
func signed(t *testing.T,private ed25519.PrivateKey,lane,id,step string)workerfence.SignedStepReceipt{
 t.Helper()
 claim:=workerfence.StepClaim{Schema:workerfence.StepSchema,ArchiveID:strings.Repeat("a",64),
  AuthoritySequence:1,AuthorityHeadSHA256:strings.Repeat("b",64),
  Lane:lane,OriginalID:id,IntentSHA256:strings.Repeat("c",64),
  OwnerID:"FORGE_OWNER",OwnerEpoch:17,WorkerID:"worker_test_1",
  WorkerBinarySHA256:strings.Repeat("d",64),LeaseSequence:1,
  ExpiresAtUnix:2000,StepSHA256:step}
 r:=workerfence.SignedStepReceipt{Schema:workerfence.StepReceiptSchema,
  Claim:claim,Status:workerfence.Consumed}
 raw,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 r.SignatureHex=hex.EncodeToString(ed25519.Sign(private,
  append([]byte(workerfence.StepReceiptDomain),raw...)))
 return r
}
func TestStepCustodyDualLaneImmutableRestart(t *testing.T){
 s,pub,private,root:=fixture(t)
 a:=signed(t,private,"Wingless","original_w",strings.Repeat("e",64))
 b:=signed(t,private,"Yggdrasil","original_y",strings.Repeat("f",64))
 ctx:=context.Background()
 if err:=s.Retain(ctx,a);err!=nil{t.Fatal(err)}
 if err:=s.Retain(ctx,b);err!=nil{t.Fatal(err)}
 if n,err:=s.ReadCount(ctx);err!=nil||n!=2{t.Fatal(n,err)}
 reopened,err:=Open(root,pub,2);if err!=nil{t.Fatal(err)}
 if n,err:=reopened.ReadCount(ctx);err!=nil||n!=2{t.Fatal(n,err)}
 if err:=reopened.Retain(ctx,a);!errors.Is(err,ErrConsumed){
  t.Fatal("replayed original worker step retained",err)
 }
 if _,err:=Provision(root,pub);err==nil{t.Fatal("existing store overwritten")}
}
func TestStepCustodyRejectsForgeryAndCancelledWrite(t *testing.T){
 s,_,private,_:=fixture(t)
 r:=signed(t,private,"Wingless","original_w",strings.Repeat("e",64))
 forged:=r;forged.SignatureHex=strings.Repeat("0",128)
 if err:=s.Retain(context.Background(),forged);!errors.Is(err,ErrBlocked){
  t.Fatal("untrusted signer admitted",err)
 }
 changed:=r;changed.Claim.Lane="Yggdrasil"
 if err:=s.Retain(context.Background(),changed);!errors.Is(err,ErrBlocked){
  t.Fatal("cross-lane signed claim drift admitted",err)
 }
 changed=r;changed.Claim.WorkerBinarySHA256=strings.Repeat("f",64)
 if err:=s.Retain(context.Background(),changed);!errors.Is(err,ErrBlocked){
  t.Fatal("modified worker executable admitted",err)
 }
 canceled,cancel:=context.WithCancel(context.Background());cancel()
 if err:=s.Retain(canceled,r);!errors.Is(err,ErrBlocked){
  t.Fatal("cancelled request retained",err)
 }
 if n,err:=s.ReadCount(context.Background());err!=nil||n!=0{
  t.Fatal("invalid writes consumed original",n,err)
 }
}
func TestStepCustodyIndependentPinnedFloorAndProcessPoison(t *testing.T){
 s,pub,private,root:=fixture(t)
 ctx:=context.Background()
 r:=signed(t,private,"Wingless","original_w",strings.Repeat("e",64))
 if err:=s.Retain(ctx,r);err!=nil{t.Fatal(err)}
 path:=filepath.Join(root,"records",key(r.Claim)+".json")
 good,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 if err:=os.Remove(path);err!=nil{t.Fatal(err)}
 if _,err:=Open(root,pub,1);!errors.Is(err,ErrBlocked){
  t.Fatal("externally pinned completed-tail deletion admitted",err)
 }
 if _,err:=s.ReadCount(ctx);!errors.Is(err,ErrBlocked){
  t.Fatal("same process forgot signed step highwater",err)
 }
 if err:=os.WriteFile(path,good,0600);err!=nil{t.Fatal(err)}
 if err:=s.Retain(ctx,signed(t,private,"Wingless","original_new",strings.Repeat("f",64)));
  !errors.Is(err,ErrBlocked){t.Fatal("poisoned worker custody resumed",err)}
 recovered,err:=Open(root,pub,1);if err!=nil{t.Fatal("fresh pin recovery",err)}
 if n,err:=recovered.ReadCount(ctx);err!=nil||n!=1{t.Fatal(n,err)}
}
func TestStepCustodyCorruptAndForeignReceiptsBlockRestart(t *testing.T){
 s,pub,private,root:=fixture(t)
 r:=signed(t,private,"Yggdrasil","original_y",strings.Repeat("e",64))
 if err:=s.Retain(context.Background(),r);err!=nil{t.Fatal(err)}
 path:=filepath.Join(root,"records",key(r.Claim)+".json")
 if err:=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Open(root,pub,1);!errors.Is(err,ErrBlocked){t.Fatal("tamper admitted",err)}
 if err:=os.WriteFile(filepath.Join(root,"records","junk"),[]byte("data"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Open(root,pub,1);!errors.Is(err,ErrBlocked){t.Fatal("foreign file admitted",err)}
}
func TestStepCustodyConcurrentDuplicateExactlyOne(t *testing.T){
 s,_,private,_:=fixture(t)
 r:=signed(t,private,"Wingless","original_w",strings.Repeat("e",64))
 var wg sync.WaitGroup
 start:=make(chan struct{})
 out:=make(chan error,2)
 for i:=0;i<2;i++{wg.Add(1);go func(){
  defer wg.Done();<-start
  out<-s.Retain(context.Background(),r)
 }()}
 close(start);wg.Wait();close(out)
 success,consumed:=0,0
 for err:=range out{
  if err==nil{success++}else if errors.Is(err,ErrConsumed){consumed++}else{t.Fatal(err)}
 }
 if success!=1||consumed!=1{t.Fatalf("unsafe concurrent retention %d %d",success,consumed)}
 if n,err:=s.ReadCount(context.Background());err!=nil||n!=1{t.Fatal(n,err)}
}
func TestStepCustodyRejectsForeignRootsAndSymlinks(t *testing.T){
 _,pub,_,_:=fixture(t)
 if _,err:=Provision(filepath.Join(t.TempDir(),"CKBR",FolderName),pub);err==nil{
  t.Fatal("foreign CKB execution directory permitted")
 }
 if _,err:=Open(filepath.Join(t.TempDir(),"other"),pub,0);err==nil{
  t.Fatal("foreign root accepted")
 }
 s,_,private,root:=fixture(t)
 r:=signed(t,private,"Wingless","original_w",strings.Repeat("e",64))
 path:=filepath.Join(root,"records",key(r.Claim)+".json")
 external:=filepath.Join(t.TempDir(),"external")
 if err:=os.WriteFile(external,[]byte("data"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(external,path);err!=nil{t.Skip("symlinks unavailable",err)}
 if err:=s.Retain(context.Background(),r);err==nil{
  t.Fatal("symlinked step claim accepted")
 }
}
