package fsaanchorstore

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

func repeat(c string,n int)string{return strings.Repeat(c,n)}
func genesis() (fsahead.Anchor,ed25519.PrivateKey){
 seed:=sha256.Sum256([]byte("FORGE isolated synthetic test key, never provision"))
 sk:=ed25519.NewKeyFromSeed(seed[:])
 pub:=append(ed25519.PublicKey(nil),sk.Public().(ed25519.PublicKey)...)
 return fsahead.Anchor{
  ArchiveID:repeat("a",64),KeyID:"FORGE_FSA_PRIVATE_TEST",PublicKey:pub,
  AuthorityEpoch:1,Sequence:0,HeadSHA256:researchlog.Genesis,
 },sk
}
func setup(t *testing.T)(*Store,string,fsahead.Anchor,ed25519.PrivateKey){
 t.Helper()
 a,sk:=genesis()
 root:=filepath.Join(t.TempDir(),FolderName)
 s,err:=Provision(root,a);if err!=nil{t.Fatal(err)}
 return s,root,a,sk
}
func next(a fsahead.Anchor,seq uint64,sha string) fsahead.Anchor {
 n:=clone(a);n.Sequence=seq;n.HeadSHA256=sha;return n
}
func TestDurableMonotonicCASAndIndependentRestartPin(t *testing.T){
 s,root,gen,_:=setup(t);ctx:=context.Background()
 initial,err:=s.ReadAnchor(ctx);if err!=nil||!equal(initial,gen){t.Fatal("genesis mismatch",err)}
 n:=next(gen,1,repeat("b",64))
 yes,err:=s.CompareAndSwap(ctx,gen,n)
 if err!=nil||!yes{t.Fatal("first CAS",err)}
 if yes,err=s.CompareAndSwap(ctx,gen,n);err!=nil||yes{t.Fatal("stale CAS replay",err)}
 reopened,err:=Open(root,gen);if err!=nil{t.Fatal("restart",err)}
 actual,err:=reopened.ReadAnchor(ctx);if err!=nil||!equal(actual,n){t.Fatal("durability readback",err)}
 two:=next(n,3,repeat("c",64))
 yes,err=reopened.CompareAndSwap(ctx,n,two)
 if err!=nil||!yes{t.Fatal("monotonic advance",err)}
 actual,err=reopened.ReadAnchor(ctx);if err!=nil||!equal(actual,two){t.Fatal("head advance",err)}
 wrong:=gen;wrong.ArchiveID=repeat("d",64)
 if _,err:=Open(root,wrong);err==nil{t.Fatal("untrusted genesis substitution accepted")}
 if _,err:=Provision(root,gen);err==nil{t.Fatal("existing store reprovisioned")}
 ok,err:=reopened.ConfirmArchiveBinding(ctx,gen.ArchiveID)
 if err!=nil||!ok{t.Fatal("provisioned archive identity lost")}
 ok,err=reopened.ConfirmArchiveBinding(ctx,repeat("e",64))
 if err!=nil||ok{t.Fatal("foreign archive identity accepted")}
}
func TestCrashLeftIncompleteReceiptNeverSilentlyRepaired(t *testing.T){
 s,root,gen,_:=setup(t);ctx:=context.Background()
 n:=next(gen,1,repeat("b",64))
 path:=filepath.Join(root,"receipts","00000001.json")
 if err:=os.WriteFile(path,[]byte("{partial"),0600);err!=nil{t.Fatal(err)}
 if _,err:=s.ReadAnchor(ctx);err==nil{t.Fatal("partial receipt treated as valid")}
 if _,err:=Open(root,gen);err==nil{t.Fatal("restart silently removed partial receipt")}
 if _,err:=s.CompareAndSwap(ctx,gen,n);err==nil{t.Fatal("partial receipt automatically overwritten")}
 data,err:=os.ReadFile(path)
 if err!=nil||string(data)!="{partial"{t.Fatal("original failure witness deleted")}
}
func TestTamperGapAndTrailingReceiptLossBoundary(t *testing.T){
 s,root,gen,_:=setup(t);ctx:=context.Background()
 n:=next(gen,1,repeat("b",64))
 yes,err:=s.CompareAndSwap(ctx,gen,n);if err!=nil||!yes{t.Fatal(err)}
 p:=filepath.Join(root,"receipts","00000001.json")
 if err:=os.WriteFile(p,[]byte("garbage"),0600);err!=nil{t.Fatal(err)}
 if _,err:=s.ReadAnchor(ctx);err==nil{t.Fatal("tampering admitted")}
 if err:=os.Remove(p);err!=nil{t.Fatal(err)}
 // Local append-only chains do NOT detect complete-tail deletion alone.
 // The independently pinned high-water witness is still required.
 a,err:=s.ReadAnchor(ctx)
 if err!=nil||a.Sequence!=0{t.Fatal("unexpected rollback behavior",err)}
}
func TestCrossProcessExclusiveCASRace(t *testing.T){
 s,_,gen,_:=setup(t)
 start:=make(chan struct{})
 var wg sync.WaitGroup
 answers:=make(chan bool,2);failures:=make(chan error,2)
 for _,digest:=range []string{repeat("b",64),repeat("c",64)}{
  wg.Add(1)
  go func(head string){defer wg.Done();<-start
   ok,err:=s.CompareAndSwap(context.Background(),gen,next(gen,1,head))
   answers<-ok;failures<-err
  }(digest)
 }
 close(start);wg.Wait();close(answers);close(failures)
 passes:=0
 for result:=range answers{if result{passes++}}
 for err:=range failures{if err!=nil{t.Fatal("unexpected CAS failure",err)}}
 if passes!=1{t.Fatalf("write-once CAS successes=%d want 1",passes)}
 a,err:=s.ReadAnchor(context.Background())
 if err!=nil||a.Sequence!=1{t.Fatal("racing CAS corrupted durable state",err)}
}
func TestForeignRootsAndSymlinkBoundaries(t *testing.T){
 gen,_:=genesis()
 root:=filepath.Join(t.TempDir(),"KTRADE",FolderName)
 if _,err:=Provision(root,gen);err==nil{t.Fatal("KTRADE authority storage accepted")}
 root=filepath.Join(t.TempDir(),"CKBR",FolderName)
 if _,err:=Provision(root,gen);err==nil{t.Fatal("CKB controller path accepted")}
 root=filepath.Join(t.TempDir(),"forge-research-archive",FolderName)
 if _,err:=Provision(root,gen);err==nil{t.Fatal("research archive failure domain reused")}
 tmp:=t.TempDir()
 target:=filepath.Join(tmp,"target")
 if err:=os.Mkdir(target,0700);err!=nil{t.Fatal(err)}
 link:=filepath.Join(tmp,"alias")
 if err:=os.Symlink(target,link);err==nil{
  if _,err:=Provision(filepath.Join(link,FolderName),gen);err==nil{t.Fatal("symlink root redirection accepted")}
 }
 if _,err:=Provision("relative/"+FolderName,gen);err==nil{t.Fatal("relative path admitted")}
}
func TestRealArchiveSignedCheckpointThroughDurableAuthority(t *testing.T){
 parent:=t.TempDir()
 gen,sk:=genesis()
 trustRoot:=filepath.Join(parent,FolderName)
 trust,err:=Provision(trustRoot,gen);if err!=nil{t.Fatal(err)}
 archive,err:=privatearchive.Initialize(filepath.Join(parent,privatearchive.FolderName))
 if err!=nil{t.Fatal(err)}
 original,err:=archive.AppendEvent(researchlog.Event{
  Lane:"Wingless",Generation:1,ExperimentID:"W01",Kind:researchlog.Hypothesis,
  SourceCommitSHA:repeat("a",40),Note:"Synthetic, pre-specified hypothesis",
 });if err!=nil{t.Fatal(err)}
 p:=fsahead.Payload{
  Schema:fsahead.Schema,Domain:fsahead.Domain,
  ArchiveID:gen.ArchiveID,KeyID:gen.KeyID,AuthorityEpoch:gen.AuthorityEpoch,
  ParentSequence:0,ParentHeadSHA256:researchlog.Genesis,
  Sequence:original.Sequence,HeadSHA256:original.RecordSHA256,
 }
 body,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
 signed:=append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),body...)
 checkpoint:=fsahead.SignedHead{Payload:p,SignatureHex:hex.EncodeToString(ed25519.Sign(sk,signed))}
 id:=fsatrust.Identity{
  ArchiveID:gen.ArchiveID,KeyID:gen.KeyID,AuthorityEpoch:gen.AuthorityEpoch,
  PublicKey:append(ed25519.PublicKey(nil),gen.PublicKey...),
 }
 acknowledged,err:=fsatrust.Advance(context.Background(),trust,archive,id,checkpoint)
 if err!=nil||acknowledged.Sequence!=1{t.Fatal("end-to-end checkpoint failed",err)}
 restarted,err:=Open(trustRoot,gen);if err!=nil{t.Fatal(err)}
 recovered,err:=fsatrust.Recover(context.Background(),restarted,archive,id)
 if err!=nil||!bytes.Equal(recovered.PublicKey,gen.PublicKey)||recovered.HeadSHA256!=original.RecordSHA256{
  t.Fatal("restart recovery failed",err)
 }
 if _,err:=fsatrust.Advance(context.Background(),restarted,archive,id,checkpoint);err==nil{
  t.Fatal("scientific checkpoint replay accepted")
 }
 if _,err:=os.Stat(filepath.Join(parent,"KTRADE"));!os.IsNotExist(err){t.Fatal("foreign execution directory appeared")}
}
func TestCASNoKeyEpochOrArbitraryWrites(t *testing.T){
 s,_,gen,_:=setup(t);ctx:=context.Background()
 foreign:=next(gen,1,repeat("b",64));foreign.KeyID="KTRADE_EXECUTION"
 if ok,err:=s.CompareAndSwap(ctx,gen,foreign);err==nil||ok{t.Fatal("foreign key accepted")}
 foreign=next(gen,1,repeat("c",64));foreign.AuthorityEpoch++
 if ok,err:=s.CompareAndSwap(ctx,gen,foreign);err==nil||ok{t.Fatal("authority epoch drift admitted")}
 ctx,cancel:=context.WithCancel(ctx);cancel()
 if _,err:=s.ReadAnchor(ctx);err==nil{t.Fatal("cancelled read returned trusted state")}
 if _,err:=s.CompareAndSwap(ctx,gen,next(gen,1,repeat("b",64)));err==nil{t.Fatal("cancelled write proceeded")}
 var nilStore *Store
 if _,err:=nilStore.ReadAnchor(context.Background());err==nil{t.Fatal("unconfigured backend accepted")}
 if _,err:=Open("",gen);err==nil{t.Fatal("empty path accepted")}
 if errors.Is(nil,fsatrust.ErrConflict){t.Fatal("impossible error classification")}
}
