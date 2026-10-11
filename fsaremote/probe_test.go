package fsaremote

import (
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "net/http"
 "sync/atomic"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/researchlog"
)

func TestRealMutualTLSReadOnlyProbeAndNoWrites(t *testing.T) {
 pub,_:=kpair("FSA")
 witnessPublic,witnessPrivate:=kpair("independent-witness")
 pin:=Pin{ArchiveID:hx("a",64),KeyID:"FORGE_TEST_ONLY",
  PublicKey:pub,AuthorityEpoch:4,BindingSHA256:hx("b",64),
  WitnessPublicKey:witnessPublic,MinimumRevision:1}
 genesis:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 var posts,anchorGets,witnessGets,bindingGets atomic.Int32
 var drift,missingBinding,cutWitness atomic.Bool
 signedFor:=func(a fsahead.Anchor,revision uint64)SignedWitness{
  h:=WitnessHead{Schema:WitnessSchema,Domain:WitnessDomain,
   ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,AuthorityEpoch:pin.AuthorityEpoch,
   BindingSHA256:pin.BindingSHA256,Sequence:a.Sequence,
   HeadSHA256:a.HeadSHA256,Revision:revision}
  msg,_:=json.Marshal(h)
  return SignedWitness{Head:h,SignatureHex:hex.EncodeToString(
   ed25519.Sign(witnessPrivate,append([]byte(domainPrefix),msg...)))}
 }
 a:=newRealMTLSPeer(t,"read-only-probe-authority",func(w http.ResponseWriter,r *http.Request){
  if r.Method==http.MethodPost {posts.Add(1);http.Error(w,"forbidden",405);return}
  if r.Method!=http.MethodGet {http.Error(w,"forbidden",405);return}
  switch r.URL.Path {
  case "/v1/fsa/anchor":
   index:=anchorGets.Add(1)
   current:=genesis
   if drift.Load()&&index%2==0{current.Sequence=1;current.HeadSHA256=hx("c",64)}
   _=json.NewEncoder(w).Encode(anchorResponse{Schema:WireSchema,Anchor:makeWire(current)})
  case "/v1/fsa/binding":
   bindingGets.Add(1)
   _=json.NewEncoder(w).Encode(bindingResponse{
    Schema:WireSchema,ArchiveID:pin.ArchiveID,BindingSHA256:pin.BindingSHA256,
    Bound:!missingBinding.Load()})
  default:http.NotFound(w,r)
  }
 })
 witness:=newRealMTLSPeer(t,"read-only-probe-witness",func(w http.ResponseWriter,r *http.Request){
  if r.Method==http.MethodPost {posts.Add(1);http.Error(w,"forbidden",405);return}
  if r.Method!=http.MethodGet||r.URL.Path!="/v1/fsa/highwater"{
   http.NotFound(w,r);return
  }
  index:=witnessGets.Add(1)
  if cutWitness.Load(){http.Error(w,"unavailable",503);return}
  current:=genesis
  revision:=uint64(1)
  if drift.Load()&&index%2==0{
   current.Sequence=1;current.HeadSHA256=hx("c",64);revision=2
  }
  _=json.NewEncoder(w).Encode(witnessResponse{Schema:WireSchema,
   Witness:signedFor(current,revision)})
 })
 client,err:=NewClient(a.peer,witness.peer,pin)
 if err!=nil{t.Fatal(err)}
 got,err:=client.Probe(context.Background())
 if err!=nil{t.Fatal(err)}
 if got.Schema!=ProbeSchema||got.ArchiveID!=pin.ArchiveID||
  got.HeadSHA256!=genesis.HeadSHA256||got.WitnessRevision!=1||
  !got.BindingConfirmed||got.ScientificAccepted||got.ExecutionAuthorized||
  got.PhysicalIndependenceVerified||got.IndependentFloorVerified||
  len(got.WitnessSHA256)!=64{t.Fatalf("incorrect observation %+v",got)}
 if posts.Load()!=0||anchorGets.Load()!=2||witnessGets.Load()!=2||
  bindingGets.Load()!=1{t.Fatal("probe performed a write or incorrect requests")}
 // A supposedly physical read must not silently accept a changed pair.
 anchorGets.Store(0);witnessGets.Store(0);drift.Store(true)
 changed,err:=client.Probe(context.Background())
 if err==nil||changed.BindingConfirmed||posts.Load()!=0{
  t.Fatalf("concurrent head drift accepted: %+v, %v",changed,err)
 }
 // An indeterminate observation permanently raises this client's
 // in-memory high-water. A separate read session needs a fresh client.
 client,err=NewClient(a.peer,witness.peer,pin)
 if err!=nil{t.Fatal(err)}
 drift.Store(false);anchorGets.Store(0);witnessGets.Store(0)
 missingBinding.Store(true)
 if _,err:=client.Probe(context.Background());!errors.Is(err,ErrMismatch){
  t.Fatalf("binding loss accepted: %v",err)
 }
 missingBinding.Store(false);cutWitness.Store(true)
 if _,err:=client.Probe(context.Background());!errors.Is(err,ErrRemote){
  t.Fatalf("witness outage accepted: %v",err)
 }
 if _,err:=client.Probe(nil);!errors.Is(err,ErrRemote){t.Fatal("nil context accepted")}
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=client.Probe(ctx);!errors.Is(err,ErrRemote){t.Fatal("cancelled context accepted")}
 if posts.Load()!=0{t.Fatal("probe performed forbidden CAS")}
}

func TestUnconfiguredProbeFailsClosed(t *testing.T) {
 var client *Client
 if _,err:=client.Probe(context.Background());!errors.Is(err,ErrRemote){
  t.Fatalf("unconfigured observation passed: %v",err)
 }
}
