package fsaservice

import (
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaanchorstore"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type bindingProof struct{
 digest string
 bound bool
 fail bool
 mutate func()
}
func(p *bindingProof)ReadBinding(_ context.Context,_ string)(string,bool,error){
 if p.mutate!=nil{p.mutate()}
 if p.fail{return "",false,errors.New("INDEPENDENT_ATTESTATION_UNAVAILABLE")}
 return p.digest,p.bound,nil
}

func TestDurableCheckpointAndWitnessCoherenceThroughMutualTLS(t *testing.T){
 ctx:=context.Background()
 primary,_:=testKey(t)
 witnessPub,witnessPrivate:=testKey(t)
 pin:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_DUAL_DURABLE_TEST",
  PublicKey:primary,AuthorityEpoch:63,BindingSHA256:strings.Repeat("b",64),
  WitnessPublicKey:witnessPub,MinimumRevision:8}
 genesis:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 authorityRoot:=filepath.Join(t.TempDir(),fsaanchorstore.FolderName)
 witnessRoot:=filepath.Join(t.TempDir(),fsawitnessstore.FolderName)
 authority,err:=fsaanchorstore.Provision(authorityRoot,genesis)
 if err!=nil{t.Fatal("checkpoint genesis",err)}
 sign:=func(a fsahead.Anchor,rev uint64)fsaremote.SignedWitness{
  t.Helper()
  h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
   ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,AuthorityEpoch:pin.AuthorityEpoch,
   BindingSHA256:pin.BindingSHA256,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256,Revision:rev}
  raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
  signature:=ed25519.Sign(witnessPrivate,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
  return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(signature)}
 }
 witnesses,err:=fsawitnessstore.Provision(witnessRoot,pin,sign(genesis,8))
 if err!=nil{t.Fatal("signed genesis",err)}
 proof:=&bindingProof{digest:pin.BindingSHA256,bound:true}
 adapter,err:=NewObservedAuthority(authority,proof)
 if err!=nil{t.Fatal(err)}
 ca,caPrivate,roots:=testCA(t)
 clientCert,clientSPKI:=certFor(t,ca,caPrivate,true)
 authorityCert,authoritySPKI:=certFor(t,ca,caPrivate,false)
 witnessCert,witnessSPKI:=certFor(t,ca,caPrivate,false)
 ah,err:=AuthorityHandler(pin,clientSPKI,adapter);if err!=nil{t.Fatal(err)}
 wh,err:=WitnessHandler(pin,clientSPKI,witnesses);if err!=nil{t.Fatal(err)}
 authorityServer:=testService(t,ah,authorityCert,roots)
 witnessServer:=testService(t,wh,witnessCert,roots)
 clientFor:=func(p fsaremote.Pin)*fsaremote.Client{
  t.Helper()
  c,err:=fsaremote.NewClient(
   fsaremote.Peer{BaseURL:authorityServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:authoritySPKI},
   fsaremote.Peer{BaseURL:witnessServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},p)
  if err!=nil{t.Fatal(err)}
  return c
 }
 client:=clientFor(pin)
 if got,err:=client.ReadAnchor(ctx);err!=nil||got.Sequence!=0{t.Fatal("genesis read",got,err)}
 if ok,err:=client.ConfirmArchiveBinding(ctx,pin.ArchiveID);err!=nil||!ok{t.Fatal("separate binding proof",ok,err)}
 // Synthetic direct checkpoint advance: deliberately not a production
 // scientific admission or an HTTPS mutating endpoint.
 next:=genesis
 next.Sequence=1
 next.HeadSHA256=strings.Repeat("c",64)
 if committed,err:=authority.CompareAndSwap(ctx,genesis,next);err!=nil||!committed{t.Fatal("fixture checkpoint advance",committed,err)}
 if _,err:=client.ReadAnchor(ctx);err==nil{t.Fatal("authority ahead of signed witness admitted")}
 if err:=witnesses.Append(ctx,sign(next,9));err!=nil{t.Fatal("signed witness advance",err)}
 if got,err:=client.ReadAnchor(ctx);err!=nil||got.Sequence!=1{t.Fatal("coherent authenticated head denied",got,err)}
 // Witness ahead of authority is equally unsafe.
 future:=next;future.Sequence=2;future.HeadSHA256=strings.Repeat("d",64)
 if err:=witnesses.Append(ctx,sign(future,10));err!=nil{t.Fatal(err)}
 if _,err:=client.ReadAnchor(ctx);err==nil{t.Fatal("witness ahead of authority admitted")}
 if committed,err:=authority.CompareAndSwap(ctx,next,future);err!=nil||!committed{t.Fatal(err)}
 if _,err:=client.ReadAnchor(ctx);err!=nil{t.Fatal("coherent highwater denied",err)}
 // Both stores survive reopen with independent immutable genesis/revision pins.
 restartPin:=pin;restartPin.MinimumRevision=10
 reopenedAuthority,err:=fsaanchorstore.Open(authorityRoot,genesis)
 if err!=nil{t.Fatal("checkpoint restart",err)}
 reopenedWitness,err:=fsawitnessstore.Open(witnessRoot,restartPin)
 if err!=nil{t.Fatal("witness restart",err)}
 if head,err:=reopenedAuthority.ReadAnchor(ctx);err!=nil||head.Sequence!=2{t.Fatal(head,err)}
 if witness,err:=reopenedWitness.ReadWitness(ctx,pin.ArchiveID);err!=nil||witness.Head.Revision!=10{t.Fatal(witness,err)}
 if _,err:=clientFor(restartPin).ReadAnchor(ctx);err!=nil{t.Fatal("pinned readback",err)}
 // Locally valid complete-tail deletion must not satisfy the separately
 // persisted witness high-water proof.
 if err:=os.Remove(filepath.Join(authorityRoot,"receipts","00000002.json"));err!=nil{t.Fatal(err)}
 if _,err:=clientFor(restartPin).ReadAnchor(ctx);err==nil{t.Fatal("checkpoint rollback admitted against witness")}
}

func TestObservedAuthorityBindingFailsClosed(t *testing.T){
 ctx:=context.Background()
 primary,_:=testKey(t)
 genesis:=fsahead.Anchor{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_ADAPTER_TEST",PublicKey:primary,
  AuthorityEpoch:4,Sequence:0,HeadSHA256:researchlog.Genesis}
 store,err:=fsaanchorstore.Provision(filepath.Join(t.TempDir(),fsaanchorstore.FolderName),genesis)
 if err!=nil{t.Fatal(err)}
 if _,err:=NewObservedAuthority(nil,&bindingProof{});!errors.Is(err,ErrAuthorityObservation){t.Fatal("missing authority",err)}
 if _,err:=NewObservedAuthority(store,nil);!errors.Is(err,ErrAuthorityObservation){t.Fatal("missing binding",err)}
 proof:=&bindingProof{digest:strings.Repeat("b",64),bound:true}
 adapter,err:=NewObservedAuthority(store,proof);if err!=nil{t.Fatal(err)}
 if _,ok,err:=adapter.ReadBinding(ctx,strings.Repeat("c",64));ok||!errors.Is(err,ErrAuthorityObservation){t.Fatal("foreign archive admitted")}
 proof.bound=false
 if _,ok,err:=adapter.ReadBinding(ctx,genesis.ArchiveID);ok||!errors.Is(err,ErrAuthorityObservation){t.Fatal("unbound archive admitted")}
 proof.bound=true;proof.fail=true
 if _,ok,err:=adapter.ReadBinding(ctx,genesis.ArchiveID);ok||!errors.Is(err,ErrAuthorityObservation){t.Fatal("broken independent source admitted")}
 proof.fail=false
 next:=genesis;next.Sequence=1;next.HeadSHA256=strings.Repeat("c",64)
 proof.mutate=func(){
  proof.mutate=nil
  if ok,err:=store.CompareAndSwap(ctx,genesis,next);err!=nil||!ok{t.Fatal("synthetic race",err)}
 }
 if _,ok,err:=adapter.ReadBinding(ctx,genesis.ArchiveID);ok||!errors.Is(err,ErrAuthorityObservation){t.Fatal("checkpoint race admitted")}
 cancelCtx,cancel:=context.WithCancel(ctx);cancel()
 if _,ok,err:=adapter.ReadBinding(cancelCtx,genesis.ArchiveID);ok||!errors.Is(err,ErrAuthorityObservation){t.Fatal("canceled attestation admitted")}
}
