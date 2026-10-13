package fsaepochstore

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

 "github.com/spoonman136668-ai/forge/researchlog"
 "github.com/spoonman136668-ai/forge/workerfence"
)

type clock struct{now uint64; fail bool}
func(c *clock)NowUnix(_ context.Context)(uint64,error){
 if c.fail{return 0,errors.New("CLOCK_UNAVAILABLE")}
 return c.now,nil
}
type signer struct{key ed25519.PrivateKey;fail bool}
func(s *signer)Sign(_ context.Context,msg []byte)([]byte,error){
 if s.fail{return nil,errors.New("SIGNER_UNAVAILABLE")}
 return ed25519.Sign(s.key,msg),nil
}
type fixture struct{
 store *Store
 root string
 pin Pin
 admin ed25519.PrivateKey
 signer *signer
 clock *clock
}
func newFixture(t *testing.T)*fixture{
 t.Helper()
 adminPub,adminKey,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 receiptPub,receiptKey,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 pin:=Pin{ArchiveID:strings.Repeat("a",64),AuthoritySequence:0,
  AuthorityHeadSHA256:researchlog.Genesis,OwnerID:"FORGE_TEST_A",
  OwnerEpoch:21,TransferPublicKey:adminPub,StepReceiptPublicKey:receiptPub}
 root:=filepath.Join(t.TempDir(),FolderName)
 now:=&clock{now:1000}
 issuance:=&signer{key:receiptKey}
 store,err:=Provision(root,pin,now,issuance)
 if err!=nil{t.Fatal(err)}
 return &fixture{store:store,root:root,pin:pin,admin:adminKey,signer:issuance,clock:now}
}
func(f *fixture)claim(owner string,epoch,lease uint64,step string)workerfence.StepClaim{
 return workerfence.StepClaim{
  Schema:workerfence.StepSchema,ArchiveID:f.pin.ArchiveID,
  AuthoritySequence:f.pin.AuthoritySequence,AuthorityHeadSHA256:f.pin.AuthorityHeadSHA256,
  Lane:"Wingless",OriginalID:"original_w_1",IntentSHA256:strings.Repeat("b",64),
  OwnerID:owner,OwnerEpoch:epoch,WorkerID:"FORGE_WORKER_1",
  WorkerBinarySHA256:strings.Repeat("c",64),LeaseSequence:lease,
  ExpiresAtUnix:2000,StepSHA256:step}
}
func(f *fixture)transfer(to string)SignedTransfer{
 return SignedTransfer{Schema:TransferSchema,ArchiveID:f.pin.ArchiveID,
  FromOwnerID:"FORGE_TEST_A",FromEpoch:21,ToOwnerID:to,ToEpoch:22,
  NonceSHA256:strings.Repeat("d",64)}
}
func signTransfer(t *testing.T,x SignedTransfer,private ed25519.PrivateKey)SignedTransfer{
 t.Helper()
 x.SignatureHex=""
 b,err:=json.Marshal(x);if err!=nil{t.Fatal(err)}
 x.SignatureHex=hex.EncodeToString(ed25519.Sign(private,append([]byte(TransferDomain),b...)))
 return x
}
func TestEpochOwnershipAndOneShotSignedStepReopen(t *testing.T){
 f:=newFixture(t)
 ctx:=context.Background()
 first:=f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64))
 receipt,err:=f.store.ConsumeOnce(ctx,first)
 if err!=nil||!validateStep(f.pin,receipt){t.Fatal("unsigned or uncommitted step",err)}
 if _,err:=f.store.ConsumeOnce(ctx,first);!errors.Is(err,ErrConsumed){
  t.Fatal("first-use step replayed",err)
 }
 snapshot,err:=f.store.Read(ctx);if err!=nil||snapshot.Ordinal!=1||snapshot.OwnerEpoch!=21{t.Fatal(snapshot,err)}
 tfer:=signTransfer(t,f.transfer("FORGE_TEST_B"),f.admin)
 if err:=f.store.TransferOwner(ctx,tfer);err!=nil{t.Fatal(err)}
 if _,err:=f.store.ConsumeOnce(ctx,f.claim("FORGE_TEST_A",21,2,strings.Repeat("f",64)));
  !errors.Is(err,ErrBlocked){t.Fatal("revoked old epoch consumed step",err)}
 second:=f.claim("FORGE_TEST_B",22,2,strings.Repeat("f",64))
 second.Lane="Yggdrasil"
 second.OriginalID="original_y_1"
 if _,err:=f.store.ConsumeOnce(ctx,second);err!=nil{t.Fatal("new epoch rejected",err)}
 reopenedPin:=f.pin;reopenedPin.MinimumOrdinal=3
 reopened,err:=Open(f.root,reopenedPin,f.clock,f.signer);if err!=nil{t.Fatal(err)}
 snapshot,err=reopened.Read(ctx)
 if err!=nil||snapshot.OwnerID!="FORGE_TEST_B"||snapshot.OwnerEpoch!=22||snapshot.Ordinal!=3{t.Fatal(snapshot,err)}
 if _,err=reopened.ConsumeOnce(ctx,first);!errors.Is(err,ErrBlocked){t.Fatal("reboot forgot revoked epoch",err)}
 if _,err=reopened.ConsumeOnce(ctx,second);!errors.Is(err,ErrConsumed){t.Fatal("reboot replayed signed step",err)}
}
func TestUntrustedOwnerTransferNeverAdvancesEpoch(t *testing.T){
 f:=newFixture(t)
 tfer:=signTransfer(t,f.transfer("FORGE_TEST_B"),f.admin)
 cases:=[]struct{name string;change func(*SignedTransfer)}{
  {"wrong signer",func(x *SignedTransfer){x.SignatureHex=strings.Repeat("0",128)}},
  {"foreign new owner",func(x *SignedTransfer){x.ToOwnerID="CKB"}},
  {"skipped epoch",func(x *SignedTransfer){x.ToEpoch=25}},
  {"wrong predecessor",func(x *SignedTransfer){x.FromEpoch=20}},
  {"foreign archive",func(x *SignedTransfer){x.ArchiveID=strings.Repeat("c",64)}},
  {"wrong nonce",func(x *SignedTransfer){x.NonceSHA256=strings.Repeat("0",64)}},
 }
 for _,test:=range cases{
  t.Run(test.name,func(t *testing.T){
   bad:=tfer;test.change(&bad)
   if err:=f.store.TransferOwner(context.Background(),bad);!errors.Is(err,ErrBlocked){
    t.Fatal("untrusted owner transfer admitted",err)
   }
   snapshot,err:=f.store.Read(context.Background())
   if err!=nil||snapshot.Ordinal!=0||snapshot.OwnerEpoch!=21{t.Fatal(snapshot,err)}
  })
 }
}
func TestEpochStepLeaseClockAndSignatureFailClosed(t *testing.T){
 f:=newFixture(t)
 ctx:=context.Background()
 claim:=f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64))
 cases:=[]struct{name string;change func(*workerfence.StepClaim)}{
  {"foreign epoch",func(c *workerfence.StepClaim){c.OwnerEpoch++}},
  {"foreign owner",func(c *workerfence.StepClaim){c.OwnerID="KTRADE"}},
  {"foreign binary",func(c *workerfence.StepClaim){c.WorkerBinarySHA256="invalid"}},
  {"wrong head",func(c *workerfence.StepClaim){c.AuthorityHeadSHA256=strings.Repeat("b",64)}},
  {"zero lease",func(c *workerfence.StepClaim){c.LeaseSequence=0}},
  {"bad lane",func(c *workerfence.StepClaim){c.Lane="Other"}},
 }
 for _,test:=range cases{
  t.Run(test.name,func(t *testing.T){
   bad:=claim;test.change(&bad)
   if _,err:=f.store.ConsumeOnce(ctx,bad);!errors.Is(err,ErrBlocked){t.Fatal("invalid step accepted",err)}
  })
 }
 f.clock.now=2000
 if _,err:=f.store.ConsumeOnce(ctx,claim);!errors.Is(err,ErrBlocked){t.Fatal("expired step accepted",err)}
 f.clock.now=1000;f.clock.fail=true
 if _,err:=f.store.ConsumeOnce(ctx,claim);!errors.Is(err,ErrBlocked){t.Fatal("untrusted time accepted",err)}
 f.clock.fail=false
 canceled,cancel:=context.WithCancel(ctx);cancel()
 if _,err:=f.store.ConsumeOnce(canceled,claim);!errors.Is(err,ErrBlocked){t.Fatal("canceled commit accepted",err)}
 if snapshot,err:=f.store.Read(ctx);err!=nil||snapshot.Ordinal!=0{t.Fatal(snapshot,err)}
 f.signer.fail=true
 if _,err:=f.store.ConsumeOnce(ctx,claim);!errors.Is(err,ErrIndeterminate){
  t.Fatal("unavailable signer permitted step",err)
 }
 f.signer.fail=false
 if _,err:=f.store.ConsumeOnce(ctx,claim);!errors.Is(err,ErrBlocked){
  t.Fatal("poisoned signing path retried",err)
 }
}
func TestEpochStoreRollbackAndTamperRejectsEvenValidTail(t *testing.T){
 f:=newFixture(t)
 ctx:=context.Background()
 claim:=f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64))
 if _,err:=f.store.ConsumeOnce(ctx,claim);err!=nil{t.Fatal(err)}
 path:=filepath.Join(f.root,"records","00000001.json")
 original,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 if err=os.Remove(path);err!=nil{t.Fatal(err)}
 pin:=f.pin;pin.MinimumOrdinal=1
 if _,err:=Open(f.root,pin,f.clock,f.signer);!errors.Is(err,ErrBlocked){
  t.Fatal("valid-tail rollback passed pinned ordinal",err)
 }
 if _,err:=f.store.Read(ctx);!errors.Is(err,ErrBlocked){t.Fatal("same instance forgot consumed step",err)}
 if err=os.WriteFile(path,original,0600);err!=nil{t.Fatal(err)}
 if _,err:=f.store.ConsumeOnce(ctx,f.claim("FORGE_TEST_A",21,2,strings.Repeat("f",64)));
  !errors.Is(err,ErrBlocked){t.Fatal("poisoned store resumed",err)}
 restored,err:=Open(f.root,pin,f.clock,f.signer);if err!=nil{t.Fatal(err)}
 if snapshot,err:=restored.Read(ctx);err!=nil||snapshot.Ordinal!=1{t.Fatal(snapshot,err)}
 if err=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err=Open(f.root,pin,f.clock,f.signer);!errors.Is(err,ErrBlocked){t.Fatal("corrupted record accepted",err)}
}
func TestEpochStoreConcurrentSameStepExactlyOne(t *testing.T){
 f:=newFixture(t)
 claim:=f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64))
 start:=make(chan struct{})
 out:=make(chan error,2)
 var wg sync.WaitGroup
 for i:=0;i<2;i++{wg.Add(1);go func(){
  defer wg.Done();<-start
  _,err:=f.store.ConsumeOnce(context.Background(),claim)
  out<-err
 }()}
 close(start);wg.Wait();close(out)
 success,denied:=0,0
 for err:=range out{if err==nil{success++}else if errors.Is(err,ErrConsumed){denied++}else{t.Fatal(err)}}
 if success!=1||denied!=1{t.Fatalf("double consumption allowed: success=%d denied=%d",success,denied)}
 snapshot,err:=f.store.Read(context.Background());if err!=nil||snapshot.Ordinal!=1{t.Fatal(snapshot,err)}
}
func TestEpochStoreCrossInstanceCompetingWritersFailClosed(t *testing.T){
 f:=newFixture(t)
 other,err:=Open(f.root,f.pin,f.clock,f.signer);if err!=nil{t.Fatal(err)}
 claim:=f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64))
 start:=make(chan struct{})
 out:=make(chan error,2)
 var wg sync.WaitGroup
 for _,store:=range []*Store{f.store,other}{
  wg.Add(1);go func(s *Store){defer wg.Done();<-start
   _,err:=s.ConsumeOnce(context.Background(),claim);out<-err
  }(store)
 }
 close(start);wg.Wait();close(out)
 success,denied:=0,0
 for err:=range out{
  if err==nil{success++}else if errors.Is(err,ErrConsumed)||errors.Is(err,ErrIndeterminate)||errors.Is(err,ErrBlocked){denied++}else{t.Fatal(err)}
 }
 if success!=1||denied!=1{t.Fatalf("two processes both committed: %d %d",success,denied)}
 opened,err:=Open(f.root,f.pin,f.clock,f.signer);if err!=nil{t.Fatal(err)}
 snapshot,err:=opened.Read(context.Background());if err!=nil||snapshot.Ordinal!=1{t.Fatal(snapshot,err)}
}
func TestEpochStoreForeignAndSymlinkReject(t *testing.T){
 f:=newFixture(t)
 if _,err:=Provision(filepath.Join(t.TempDir(),"CKBR",FolderName),f.pin,f.clock,f.signer);err==nil{
  t.Fatal("CKB parent accepted")
 }
 if _,err:=Provision(f.root,f.pin,f.clock,f.signer);err==nil{t.Fatal("reprovision overwrote durable store")}
 target:=filepath.Join(f.root,"records","00000001.json")
 foreign:=filepath.Join(t.TempDir(),"foreign")
 if err:=os.WriteFile(foreign,[]byte("foreign"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(foreign,target);err!=nil{t.Skip("symlinks unavailable",err)}
 if _,err:=f.store.ConsumeOnce(context.Background(),f.claim("FORGE_TEST_A",21,1,strings.Repeat("e",64)));err==nil{
  t.Fatal("symlinked journal entry accepted")
 }
}
