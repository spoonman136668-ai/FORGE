package fsatrust

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
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type fakeAuthority struct {
 mu sync.Mutex
 current fsahead.Anchor
 bound bool
 casAppliedThenError bool
 denyCAS bool
 readError bool
 commits int
}
func (f *fakeAuthority)ReadAnchor(context.Context)(fsahead.Anchor,error){
 f.mu.Lock();defer f.mu.Unlock()
 if f.readError{return fsahead.Anchor{},errors.New("synthetic backend offline")}
 return clone(f.current),nil
}
func (f *fakeAuthority)ConfirmArchiveBinding(_ context.Context,id string)(bool,error){
 f.mu.Lock();defer f.mu.Unlock()
 return f.bound&&id==f.current.ArchiveID,nil
}
func (f *fakeAuthority)CompareAndSwap(_ context.Context,prev,next fsahead.Anchor)(bool,error){
 f.mu.Lock();defer f.mu.Unlock()
 if f.denyCAS||!identical(f.current,prev){return false,nil}
 f.commits++
 f.current=clone(next)
 if f.casAppliedThenError{return false,errors.New("synthetic commit acknowledged ambiguously")}
 return true,nil
}
func hexRepeat(c string,n int)string{return strings.Repeat(c,n)}
func setup(t *testing.T)(*privatearchive.Store,string,*fakeAuthority,Identity,ed25519.PrivateKey){
 t.Helper()
 root:=filepath.Join(t.TempDir(),privatearchive.FolderName)
 archive,err:=privatearchive.Initialize(root);if err!=nil{t.Fatal(err)}
 seed:=sha256.Sum256([]byte("FORGE synthetic local test key, never for a deployed authority"))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 pub:=append(ed25519.PublicKey(nil),priv.Public().(ed25519.PublicKey)...)
 a:=fsahead.Anchor{
  ArchiveID:hexRepeat("a",64),KeyID:"FORGE_TEST_AUTHORITY",PublicKey:pub,
  AuthorityEpoch:3,Sequence:0,HeadSHA256:researchlog.Genesis,
 }
 id:=Identity{ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKey:append(ed25519.PublicKey(nil),pub...),AuthorityEpoch:a.AuthorityEpoch}
 return archive,root,&fakeAuthority{current:a,bound:true},id,priv
}
func writeHypothesis(t *testing.T,archive *privatearchive.Store)researchlog.Record{
 t.Helper()
 r,err:=archive.AppendEvent(researchlog.Event{
  Lane:"Wingless",Generation:1,ExperimentID:"W0001",Kind:researchlog.Hypothesis,
  SourceCommitSHA:hexRepeat("b",40),Note:"Synthetic scientific hypothesis",
 })
 if err!=nil{t.Fatal(err)}
 return r
}
func sign(t *testing.T,a fsahead.Anchor,sk ed25519.PrivateKey,seq uint64,head string)fsahead.SignedHead{
 t.Helper()
 p:=fsahead.Payload{
  Schema:fsahead.Schema,Domain:fsahead.Domain,ArchiveID:a.ArchiveID,
  KeyID:a.KeyID,AuthorityEpoch:a.AuthorityEpoch,ParentSequence:a.Sequence,
  ParentHeadSHA256:a.HeadSHA256,Sequence:seq,HeadSHA256:head,
 }
 raw,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
 msg:=append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),raw...)
 return fsahead.SignedHead{Payload:p,SignatureHex:hex.EncodeToString(ed25519.Sign(sk,msg))}
}
func TestSignedCheckpointDurableCASAndReadOnlyRecovery(t *testing.T){
 archive,_,authority,id,sk:=setup(t)
 row:=writeHypothesis(t,archive)
 old:=clone(authority.current)
 cp:=sign(t,old,sk,row.Sequence,row.RecordSHA256)
 newHead,err:=Advance(context.Background(),authority,archive,id,cp)
 if err!=nil{t.Fatal(err)}
 if newHead.Sequence!=1||newHead.HeadSHA256!=row.RecordSHA256||authority.commits!=1{t.Fatal("wrong trusted high water")}
 recovered,err:=Recover(context.Background(),authority,archive,id)
 if err!=nil||!identical(recovered,newHead){t.Fatal("recovery drift",err)}
 if _,err:=Advance(context.Background(),authority,archive,id,cp);err==nil{t.Fatal("replayed certificate accepted")}
 if authority.commits!=1{t.Fatal("duplicate CAS")}
 e:=researchlog.Event{
  Lane:"Wingless",Generation:1,ExperimentID:"W0001",Kind:researchlog.Preregister,
  SourceCommitSHA:hexRepeat("b",40),PreregSHA256:hexRepeat("c",64),
  CohortSHA256:hexRepeat("d",64),
 }
 second,err:=archive.AppendEvent(e);if err!=nil{t.Fatal(err)}
 cp2:=sign(t,newHead,sk,second.Sequence,second.RecordSHA256)
 latest,err:=Advance(context.Background(),authority,archive,id,cp2)
 if err!=nil||latest.Sequence!=2||authority.commits!=2{t.Fatal("monotonic next certificate",err)}
 if _,err:=Recover(context.Background(),authority,archive,id);err!=nil{t.Fatal(err)}
}
func TestIndeterminateCASMustReconcileNotReplay(t *testing.T){
 archive,_,authority,id,sk:=setup(t)
 row:=writeHypothesis(t,archive)
 cp:=sign(t,authority.current,sk,row.Sequence,row.RecordSHA256)
 authority.casAppliedThenError=true
 if _,err:=Advance(context.Background(),authority,archive,id,cp);!errors.Is(err,ErrCommitIndeterminate){
  t.Fatal("ambiguous commit claimed success",err)
 }
 if authority.commits!=1{t.Fatal("synthetic CAS did not take effect")}
 updated,err:=Recover(context.Background(),authority,archive,id)
 if err!=nil||updated.Sequence!=1{t.Fatal("could not reconcile committed checkpoint",err)}
 if _,err:=Advance(context.Background(),authority,archive,id,cp);err==nil||authority.commits!=1{
  t.Fatal("uncertain first use silently replayed")
 }
}
func TestForeignBindingsAndAuthorityUnavailableFailClosed(t *testing.T){
 archive,_,authority,id,sk:=setup(t)
 row:=writeHypothesis(t,archive)
 cp:=sign(t,authority.current,sk,row.Sequence,row.RecordSHA256)
 authority.bound=false
 if _,err:=Advance(context.Background(),authority,archive,id,cp);!errors.Is(err,ErrBinding){t.Fatal("unbound archive accepted",err)}
 authority.bound=true
 forgedID:=id;forgedID.ArchiveID=hexRepeat("e",64)
 if _,err:=Advance(context.Background(),authority,archive,forgedID,cp);!errors.Is(err,ErrMismatch){t.Fatal("foreign authority accepted",err)}
 forgedID=id;forgedID.KeyID="KTRADE_EXECUTION_AUTHORITY"
 if _,err:=Advance(context.Background(),authority,archive,forgedID,cp);!errors.Is(err,ErrMismatch){t.Fatal("KTRADE identity accepted",err)}
 authority.readError=true
 if _,err:=Advance(context.Background(),authority,archive,id,cp);!errors.Is(err,ErrUnavailable){t.Fatal("unavailable private authority accepted",err)}
 authority.readError=false
 authority.denyCAS=true
 if _,err:=Advance(context.Background(),authority,archive,id,cp);!errors.Is(err,ErrConflict){t.Fatal("rejected CAS claimed success",err)}
 if authority.commits!=0{t.Fatal("rejecting service mutated trusted head")}
 if _,err:=Advance(context.Background(),nil,archive,id,cp);err==nil{t.Fatal("missing external authority accepted")}
 if _,err:=Advance(context.Background(),authority,nil,id,cp);err==nil{t.Fatal("missing archive accepted")}
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=Advance(ctx,authority,archive,id,cp);err==nil{t.Fatal("cancelled checkpoint accepted")}
}
func TestOriginalLossAndValidTailRollbackDetected(t *testing.T){
 archive,root,authority,id,sk:=setup(t)
 event:=researchlog.Event{
  Lane:"Yggdrasil",Generation:1,ExperimentID:"Y0001",Kind:researchlog.Hypothesis,
  SourceCommitSHA:hexRepeat("b",40),
 }
 series:=[]researchlog.Kind{researchlog.Hypothesis,researchlog.Preregister,researchlog.SourceQualified,researchlog.PrimaryStarted,researchlog.PrimaryTerminal}
 raw,err:=archive.SaveOriginal([]byte("original synthetic terminal stdout stderr exit code"))
 if err!=nil{t.Fatal(err)}
 var last researchlog.Record
 for _,kind:=range series{
  event.Kind=kind
  switch kind{
  case researchlog.Preregister:
   event.PreregSHA256=hexRepeat("c",64);event.CohortSHA256=hexRepeat("d",64)
  case researchlog.SourceQualified:
   event.WitnessSHA256=hexRepeat("e",64)
  case researchlog.PrimaryStarted:
   event.RunID=2001;event.WitnessSHA256=hexRepeat("f",64)
  case researchlog.PrimaryTerminal:
   event.Outcome="NEGATIVE";event.OriginalEvidenceSHA256=raw;event.WitnessSHA256=hexRepeat("1",64)
  }
  last,err=archive.AppendEvent(event);if err!=nil{t.Fatal(err)}
 }
 cp:=sign(t,authority.current,sk,last.Sequence,last.RecordSHA256)
 if _,err:=Advance(context.Background(),authority,archive,id,cp);err!=nil{t.Fatal(err)}
 originalPath:=filepath.Join(root,"originals",raw+".raw")
 if err:=os.Remove(originalPath);err!=nil{t.Fatal(err)}
 if _,err:=Recover(context.Background(),authority,archive,id);err==nil{t.Fatal("lost original accepted")}
 if _,err:=archive.SaveOriginal([]byte("original synthetic terminal stdout stderr exit code"));err!=nil{t.Fatal(err)}
 if err:=os.Remove(filepath.Join(root,"records","00000005.json"));err!=nil{t.Fatal(err)}
 if _,err:=Recover(context.Background(),authority,archive,id);err==nil{t.Fatal("deleted final record accepted")}
}
func TestRacingCASCannotAdvanceSameCheckpointTwice(t *testing.T){
 archive,_,authority,id,sk:=setup(t)
 row:=writeHypothesis(t,archive)
 cp:=sign(t,authority.current,sk,row.Sequence,row.RecordSHA256)
 var wg sync.WaitGroup
 start:=make(chan struct{})
 errs:=make(chan error,2)
 for j:=0;j<2;j++{
  wg.Add(1)
  go func(){
   defer wg.Done();<-start
   _,err:=Advance(context.Background(),authority,archive,id,cp);errs<-err
  }()
 }
 close(start);wg.Wait();close(errs)
 passed,denied:=0,0
 for err:=range errs{if err==nil{passed++}else{denied++}}
 if passed!=1||denied!=1||authority.commits!=1{
  t.Fatalf("CAS results success=%d rejected=%d commits=%d",passed,denied,authority.commits)
 }
 if _,err:=Recover(context.Background(),authority,archive,id);err!=nil{t.Fatal(err)}
}
