package fsawitnessstore

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
 "sync/atomic"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsaservice"
 "github.com/spoonman136668-ai/forge/researchlog"
)

var _ fsaservice.WitnessStore = (*Store)(nil)

func fixture(t *testing.T)(fsaremote.Pin,ed25519.PrivateKey){
 t.Helper()
 primary,_,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 witness,private,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 return fsaremote.Pin{ArchiveID:strings.Repeat("a",64),
  KeyID:"FORGE_TEST_WITNESS",PublicKey:primary,AuthorityEpoch:23,
  BindingSHA256:strings.Repeat("b",64),WitnessPublicKey:witness,
  MinimumRevision:2},private
}
func signed(t *testing.T,p fsaremote.Pin,private ed25519.PrivateKey,seq,rev uint64,head string)fsaremote.SignedWitness{
 t.Helper()
 h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,
  Domain:fsaremote.WitnessDomain,ArchiveID:p.ArchiveID,
  KeyID:p.KeyID,AuthorityEpoch:p.AuthorityEpoch,
  BindingSHA256:p.BindingSHA256,Sequence:seq,
  HeadSHA256:head,Revision:rev}
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(private,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
 return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(sig)}
}
func newStore(t *testing.T,p fsaremote.Pin,key ed25519.PrivateKey)(*Store,string){
 t.Helper()
 root:=filepath.Join(t.TempDir(),FolderName)
 initial:=signed(t,p,key,0,2,researchlog.Genesis)
 s,err:=Provision(root,p,initial)
 if err!=nil{t.Fatal("fixture provisioning",err)}
 return s,root
}
func TestWitnessAppendRestartAndExternallyPinnedRollbackFloor(t *testing.T){
 p,key:=fixture(t)
 store,root:=newStore(t,p,key)
 ctx:=context.Background()
 start,err:=store.ReadWitness(ctx,p.ArchiveID)
 if err!=nil||start.Head.Revision!=2{t.Fatal(start,err)}
 next:=signed(t,p,key,1,3,strings.Repeat("c",64))
 if err:=store.Append(ctx,next);err!=nil{t.Fatal(err)}
 restartedPin:=p
 restartedPin.MinimumRevision=3
 restarted,err:=Open(root,restartedPin)
 if err!=nil{t.Fatal("restart with operator-pinned floor",err)}
 read,err:=restarted.ReadWitness(ctx,p.ArchiveID)
 if err!=nil||read.Head!=next.Head||read.SignatureHex!=next.SignatureHex{
  t.Fatal("signed high-water not retained across restart",err)
 }
 if _,err:=restarted.ReadWitness(ctx,strings.Repeat("d",64));err==nil{
  t.Fatal("foreign archive read admitted")
 }
 if _,err:=Provision(root,p,start);err==nil{t.Fatal("provision overwrote existing store")}
 if err:=os.Remove(filepath.Join(root,"receipts","00000001.json"));err!=nil{t.Fatal(err)}
 if _,err:=Open(root,restartedPin);err==nil{
  t.Fatal("rollback below independently pinned restart revision admitted")
 }
 // An older low floor cannot prove rollback resistance; this is why the
 // external high-water revision is mandatory and must not be read from disk.
}
func TestWitnessRejectsForgedNonmonotonicAndCanceledUpdates(t *testing.T){
 p,key:=fixture(t)
 s,_:=newStore(t,p,key)
 ctx:=context.Background()
 step:=signed(t,p,key,1,3,strings.Repeat("c",64))
 forged:=step
 forged.SignatureHex=strings.Repeat("0",128)
 if err:=s.Append(ctx,forged);!errors.Is(err,ErrBlocked){t.Fatal("forgery not blocked",err)}
 canceled,cancel:=context.WithCancel(ctx);cancel()
 if err:=s.Append(canceled,step);!errors.Is(err,ErrBlocked){t.Fatal("canceled request not blocked",err)}
 if err:=s.Append(ctx,step);err!=nil{t.Fatal(err)}
 if err:=s.Append(ctx,step);!errors.Is(err,ErrConflict){t.Fatal("replayed witness accepted",err)}
 old:=signed(t,p,key,0,4,researchlog.Genesis)
 if err:=s.Append(ctx,old);!errors.Is(err,ErrConflict){t.Fatal("sequence rollback accepted",err)}
 fork:=signed(t,p,key,1,4,strings.Repeat("d",64))
 if err:=s.Append(ctx,fork);!errors.Is(err,ErrConflict){t.Fatal("same sequence fork accepted",err)}
 wrongEpoch:=step
 wrongEpoch.Head.AuthorityEpoch++
 if err:=s.Append(ctx,wrongEpoch);!errors.Is(err,ErrBlocked){t.Fatal("wrong epoch admitted",err)}
}
func TestWitnessCrashInspectionAndExclusiveAppend(t *testing.T){
 t.Run("corrupt",func(t *testing.T){
  p,key:=fixture(t);s,root:=newStore(t,p,key)
  if err:=os.WriteFile(filepath.Join(root,"receipts","00000000.json"),[]byte("{}"),0600);err!=nil{t.Fatal(err)}
  if _,err:=s.ReadWitness(context.Background(),p.ArchiveID);err==nil{t.Fatal("corrupt receipt accepted")}
  if _,err:=Open(root,p);err==nil{t.Fatal("corrupt store recovered silently")}
 })
 t.Run("foreign entry",func(t *testing.T){
  p,key:=fixture(t);s,root:=newStore(t,p,key)
  if err:=os.WriteFile(filepath.Join(root,"receipts","junk"),[]byte("data"),0600);err!=nil{t.Fatal(err)}
  if _,err:=s.ReadWitness(context.Background(),p.ArchiveID);err==nil{t.Fatal("extra receipt accepted")}
 })
 t.Run("symlink",func(t *testing.T){
  p,key:=fixture(t);s,root:=newStore(t,p,key)
  path:=filepath.Join(root,"receipts","00000000.json")
  data,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
  other:=filepath.Join(t.TempDir(),"external.json")
  if err:=os.WriteFile(other,data,0600);err!=nil{t.Fatal(err)}
  if err:=os.Remove(path);err!=nil{t.Fatal(err)}
  if err:=os.Symlink(other,path);err!=nil{t.Skip("symlink creation restricted by host",err)}
  if _,err:=s.ReadWitness(context.Background(),p.ArchiveID);err==nil{t.Fatal("symlink receipt accepted")}
 })
 t.Run("racing append",func(t *testing.T){
  p,key:=fixture(t);s,root:=newStore(t,p,key)
  next:=signed(t,p,key,1,3,strings.Repeat("c",64))
  var successes atomic.Int32
  var conflicts atomic.Int32
  var failures atomic.Int32
  var wg sync.WaitGroup
  for i:=0;i<2;i++{
   wg.Add(1)
   go func(){
    defer wg.Done()
    switch err:=s.Append(context.Background(),next);{
    case err==nil:successes.Add(1)
    case errors.Is(err,ErrConflict):conflicts.Add(1)
    default:failures.Add(1)
    }
   }()
  }
  wg.Wait()
  if successes.Load()!=1||conflicts.Load()!=1||failures.Load()!=0{
   t.Fatalf("unsafe concurrent append: success=%d conflict=%d failure=%d",successes.Load(),conflicts.Load(),failures.Load())
  }
  reopened,err:=Open(root,p);if err!=nil{t.Fatal(err)}
  got,err:=reopened.ReadWitness(context.Background(),p.ArchiveID)
  if err!=nil||got.Head!=next.Head{t.Fatal("racing append lost committed head",err)}
 })
}
