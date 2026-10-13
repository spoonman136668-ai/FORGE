package fsaservice

import (
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaanchorstore"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type linkedCheckpoint struct {
 store *fsaanchorstore.Store
 witnesses *fsawitnessstore.Store
 pin fsaremote.Pin
 signer ed25519.PrivateKey
 witnessOnCommit bool
 commits int
}
func(l *linkedCheckpoint)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){return l.store.ReadAnchor(ctx)}
func(l *linkedCheckpoint)ConfirmArchiveBinding(ctx context.Context,id string)(bool,error){return l.store.ConfirmArchiveBinding(ctx,id)}
func(l *linkedCheckpoint)CompareAndSwap(ctx context.Context,old,next fsahead.Anchor)(bool,error){
 ok,err:=l.store.CompareAndSwap(ctx,old,next)
 if err!=nil||!ok{return ok,err}
 l.commits++
 if l.witnessOnCommit{
  if err:=l.witnesses.Append(ctx,signedHighwater(next,3,l.pin,l.signer));err!=nil{return false,err}
 }
 return true,nil
}
func signedHighwater(a fsahead.Anchor,rev uint64,p fsaremote.Pin,signer ed25519.PrivateKey)fsaremote.SignedWitness{
 h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
  ArchiveID:p.ArchiveID,KeyID:p.KeyID,AuthorityEpoch:p.AuthorityEpoch,
  BindingSHA256:p.BindingSHA256,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256,Revision:rev}
 data,_:=json.Marshal(h)
 sig:=ed25519.Sign(signer,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),data...))
 return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(sig)}
}
func signedArchiveHead(a fsahead.Anchor,next researchlog.Record,private ed25519.PrivateKey)fsahead.SignedHead{
 p:=fsahead.Payload{Schema:fsahead.Schema,Domain:fsahead.Domain,
  ArchiveID:a.ArchiveID,KeyID:a.KeyID,AuthorityEpoch:a.AuthorityEpoch,
  ParentSequence:a.Sequence,ParentHeadSHA256:a.HeadSHA256,
  Sequence:next.Sequence,HeadSHA256:next.RecordSHA256}
 data,_:=json.Marshal(p)
 sig:=ed25519.Sign(private,append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),data...))
 return fsahead.SignedHead{Payload:p,SignatureHex:hex.EncodeToString(sig)}
}
type gateFixture struct{
 ctx context.Context
 archive *privatearchive.Store
 checkpoint *linkedCheckpoint
 gate *CheckpointGate
 binding *bindingProof
 signed fsahead.SignedHead
 pin fsaremote.Pin
 anchor fsahead.Anchor
 rawRoot string
 ca *x509.Certificate
 caPrivate ed25519.PrivateKey
 roots *x509.CertPool
 readerCert tls.Certificate
 readerSPKI string
}
func newGateFixture(t *testing.T,ackWitness bool)*gateFixture{
 t.Helper()
 authorityKey,authorityPrivate:=testKey(t)
 witnessKey,witnessPrivate:=testKey(t)
 pin:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),
  KeyID:"FORGE_SIGNED_ADMISSION_FIXTURE",PublicKey:authorityKey,
  AuthorityEpoch:51,BindingSHA256:strings.Repeat("b",64),
  WitnessPublicKey:witnessKey,MinimumRevision:2}
 head:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 archiveRoot:=filepath.Join(t.TempDir(),privatearchive.FolderName)
 archive,err:=privatearchive.Initialize(archiveRoot);if err!=nil{t.Fatal(err)}
 row,err:=archive.AppendEvent(researchlog.Event{
  Lane:"Wingless",Generation:1,ExperimentID:"W0001",
  Kind:researchlog.Hypothesis,SourceCommitSHA:strings.Repeat("c",40),
  Note:"synthetic source-only head fixture",
 });if err!=nil{t.Fatal(err)}
 checkpointStore,err:=fsaanchorstore.Provision(filepath.Join(t.TempDir(),fsaanchorstore.FolderName),head)
 if err!=nil{t.Fatal(err)}
 witnessStore,err:=fsawitnessstore.Provision(filepath.Join(t.TempDir(),fsawitnessstore.FolderName),pin,
  signedHighwater(head,2,pin,witnessPrivate));if err!=nil{t.Fatal(err)}
 linked:=&linkedCheckpoint{store:checkpointStore,witnesses:witnessStore,
  pin:pin,signer:witnessPrivate,witnessOnCommit:ackWitness}
 binding:=&bindingProof{digest:pin.BindingSHA256,bound:true}
 ca,caPrivate,roots:=testCA(t)
 clientCert,clientSPKI:=certFor(t,ca,caPrivate,true)
 authorityCert,authoritySPKI:=certFor(t,ca,caPrivate,false)
 witnessCert,witnessSPKI:=certFor(t,ca,caPrivate,false)
 adapter,err:=NewObservedAuthority(linked,binding);if err!=nil{t.Fatal(err)}
 ah,err:=AuthorityHandler(pin,clientSPKI,adapter);if err!=nil{t.Fatal(err)}
 wh,err:=WitnessHandler(pin,clientSPKI,witnessStore);if err!=nil{t.Fatal(err)}
 authorityServer:=testService(t,ah,authorityCert,roots)
 witnessServer:=testService(t,wh,witnessCert,roots)
 client,err:=fsaremote.NewClient(
  fsaremote.Peer{BaseURL:authorityServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:authoritySPKI},
  fsaremote.Peer{BaseURL:witnessServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},pin)
 if err!=nil{t.Fatal(err)}
 id:=fsatrust.Identity{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch}
 gate,err:=NewCheckpointGate(linked,binding,archive,client,id,pin.BindingSHA256)
 if err!=nil{t.Fatal(err)}
 return &gateFixture{ctx:context.Background(),archive:archive,checkpoint:linked,gate:gate,
  binding:binding,signed:signedArchiveHead(head,row,authorityPrivate),
  pin:pin,anchor:head,rawRoot:archiveRoot,
  ca:ca,caPrivate:caPrivate,roots:roots,readerCert:clientCert,readerSPKI:clientSPKI}
}
func TestSignedCheckpointGateRequiresWitnessBeforeAcknowledging(t *testing.T){
 f:=newGateFixture(t,true)
 got,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed)
 if err!=nil||got.Sequence!=1||f.checkpoint.commits!=1||f.gate.Indeterminate(){
  t.Fatal("fully witnessed signed checkpoint denied",got,err)
 }
 if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);err==nil||
  f.checkpoint.commits!=1{t.Fatal("signed checkpoint replay committed")}
 if _,err:=f.archive.Load();err!=nil{t.Fatal("source archive mutated",err)}
}
func TestSignedCheckpointGateWitnessLagPoisonsWithoutRetry(t *testing.T){
 f:=newGateFixture(t,false)
 _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed)
 if !errors.Is(err,ErrCheckpointGateIndeterminate)||!f.gate.Indeterminate(){
  t.Fatal("unwitnessed commit acknowledged",err)
 }
 if f.checkpoint.commits!=1{t.Fatal("expected synthetic committed checkpoint")}
 // Even if the signer's witness is later reconciled, this exact instance
 // must not clear uncertainty by retrying an original checkpoint.
 if err:=f.checkpoint.witnesses.Append(f.ctx,signedHighwater(
  fsahead.Anchor{ArchiveID:f.anchor.ArchiveID,KeyID:f.anchor.KeyID,PublicKey:f.anchor.PublicKey,
   AuthorityEpoch:f.anchor.AuthorityEpoch,Sequence:1,
   HeadSHA256:f.signed.Payload.HeadSHA256},3,f.pin,f.checkpoint.signer));err!=nil{t.Fatal(err)}
 if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);!errors.Is(err,ErrCheckpointGateIndeterminate){
  t.Fatal("stale checkpoint allowed after uncertainty",err)
 }
 if f.checkpoint.commits!=1{t.Fatal("silent checkpoint replay")}
}
func TestSignedCheckpointGateRejectsInvalidSourceAndExternalBinding(t *testing.T){
 t.Run("independent binding absent",func(t *testing.T){
  f:=newGateFixture(t,true)
  f.binding.bound=false
  if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);!errors.Is(err,ErrCheckpointGateBlocked){
   t.Fatal("unbound physical archive accepted",err)
  }
  if f.checkpoint.commits!=0{t.Fatal("unbound checkpoint mutated")}
 })
 t.Run("binding digest drift",func(t *testing.T){
  f:=newGateFixture(t,true)
  f.binding.digest=strings.Repeat("f",64)
  if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);!errors.Is(err,ErrCheckpointGateBlocked){
   t.Fatal("foreign binding digest accepted",err)
  }
 })
 t.Run("forged FSA signature",func(t *testing.T){
  f:=newGateFixture(t,true)
  f.signed.SignatureHex=strings.Repeat("0",128)
  if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);!errors.Is(err,ErrCheckpointGateBlocked){
   t.Fatal("forged signed checkpoint accepted",err)
  }
  if f.checkpoint.commits!=0{t.Fatal("forged certificate mutated backend")}
 })
 t.Run("archive head mismatch",func(t *testing.T){
  f:=newGateFixture(t,true)
  f.signed.Payload.HeadSHA256=strings.Repeat("d",64)
  if _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed);!errors.Is(err,ErrCheckpointGateBlocked){
   t.Fatal("tampered archive head accepted",err)
  }
 })
 t.Run("canceled",func(t *testing.T){
  f:=newGateFixture(t,true)
  ctx,cancel:=context.WithCancel(f.ctx);cancel()
  if _,err:=f.gate.AdvanceSignedCheckpoint(ctx,f.signed);!errors.Is(err,ErrCheckpointGateBlocked){
   t.Fatal("cancelled checkpoint wrote",err)
  }
 })
}
func TestSignedCheckpointGateSerializesDuplicateProposals(t *testing.T){
 f:=newGateFixture(t,true)
 var wg sync.WaitGroup
 start:=make(chan struct{})
 errs:=make(chan error,2)
 for i:=0;i<2;i++{wg.Add(1);go func(){
  defer wg.Done();<-start
  _,err:=f.gate.AdvanceSignedCheckpoint(f.ctx,f.signed)
  errs<-err
 }()}
 close(start);wg.Wait();close(errs)
 passed,denied:=0,0
 for err:=range errs{if err==nil{passed++}else{denied++}}
 if passed!=1||denied!=1||f.checkpoint.commits!=1{
  t.Fatalf("double checkpoint: ok=%d denied=%d writes=%d",passed,denied,f.checkpoint.commits)
 }
}
