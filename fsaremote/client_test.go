package fsaremote

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func kpair(label string)(ed25519.PublicKey,ed25519.PrivateKey){
 seed:=sha256.Sum256([]byte("FORGE-UNIT-TEST-NOT-A-SECRET-"+label))
 private:=ed25519.NewKeyFromSeed(seed[:])
 return append(ed25519.PublicKey(nil),private.Public().(ed25519.PublicKey)...),private
}
func hx(c string,n int)string{return strings.Repeat(c,n)}
type roundTripFunc func(*http.Request)(*http.Response,error)
func (f roundTripFunc)RoundTrip(r *http.Request)(*http.Response,error){return f(r)}
func jsonResponse(status int,x any)*http.Response{
 b,_:=json.Marshal(x)
 return &http.Response{StatusCode:status,Body:io.NopCloser(strings.NewReader(string(b))),Header:make(http.Header)}
}
type sim struct{
 sync.Mutex
 pin Pin
 current fsahead.Anchor
 witnessKey ed25519.PrivateKey
 revision uint64
 binding bool
 badSignature bool
 outage bool
 ambiguousCommit bool
 staleWitness bool
 commits int
 methods []string
}
func fixture(t *testing.T)(*Client,*sim,ed25519.PrivateKey){
 t.Helper()
 primaryPub,primaryKey:=kpair("FSA")
 witnessPub,witnessKey:=kpair("independent-witness")
 pin:=Pin{ArchiveID:hx("a",64),KeyID:"FORGE_TEST_ONLY",PublicKey:primaryPub,AuthorityEpoch:4,BindingSHA256:hx("b",64),
  WitnessPublicKey:witnessPub,MinimumRevision:1}
 anchor:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,PublicKey:pin.PublicKey,
 AuthorityEpoch:pin.AuthorityEpoch,Sequence:0,HeadSHA256:researchlog.Genesis}
 fake:=&sim{pin:pin,current:anchor,witnessKey:witnessKey,revision:1,binding:true}
 client:=&Client{authorityURL:"https://authority.forge.test",witnessURL:"https://witness.forge.test",
  authority:&http.Client{Transport:roundTripFunc(fake.serve("authority")),CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}},
  witness:&http.Client{Transport:roundTripFunc(fake.serve("witness")),CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}},
  pin:pin,observedRevision:pin.MinimumRevision}
 return client,fake,primaryKey
}
func (s *sim)serve(name string)roundTripFunc{
 return func(req *http.Request)(*http.Response,error){
  s.Lock();defer s.Unlock()
  s.methods=append(s.methods,name+":"+req.Method+":"+req.URL.Path)
  if req.URL.Scheme!="https"||req.URL.Host!=name+".forge.test"{
   return jsonResponse(404,map[string]string{"error":"wrong origin"}),nil
  }
  if name=="witness"{
   if req.Method!="GET"||req.URL.Path!="/v1/fsa/highwater"||req.URL.Query().Get("archive_id")!=s.pin.ArchiveID{
    return jsonResponse(405,map[string]string{"error":"scope"}),nil
   }
   if s.outage{return jsonResponse(503,map[string]string{"error":"unavailable"}),nil}
   h:=WitnessHead{Schema:WitnessSchema,Domain:WitnessDomain,ArchiveID:s.pin.ArchiveID,
    KeyID:s.pin.KeyID,AuthorityEpoch:s.pin.AuthorityEpoch,BindingSHA256:s.pin.BindingSHA256,
    Sequence:s.current.Sequence,HeadSHA256:s.current.HeadSHA256,Revision:s.revision}
   if s.staleWitness{h.Revision=1}
   raw,_:=json.Marshal(h)
   signature:=hex.EncodeToString(ed25519.Sign(s.witnessKey,append([]byte(domainPrefix),raw...)))
   if s.badSignature{signature=hx("0",128)}
   return jsonResponse(200,witnessResponse{Schema:WireSchema,Witness:SignedWitness{Head:h,SignatureHex:signature}}),nil
  }
  switch req.URL.Path{
  case "/v1/fsa/anchor":
   if req.Method!="GET"{return jsonResponse(405,"no"),nil}
   return jsonResponse(200,anchorResponse{Schema:WireSchema,Anchor:makeWire(s.current)}),nil
  case "/v1/fsa/binding":
   if req.Method!="GET"||req.URL.Query().Get("archive_id")!=s.pin.ArchiveID{
    return jsonResponse(400,"no"),nil
   }
   return jsonResponse(200,bindingResponse{Schema:WireSchema,ArchiveID:s.pin.ArchiveID,
    BindingSHA256:s.pin.BindingSHA256,Bound:s.binding}),nil
  case "/v1/fsa/cas":
   if req.Method!="POST"||req.Header.Get("Content-Type")!="application/json"{
    return jsonResponse(405,"no"),nil
   }
   var value casRequest
   if err:=json.NewDecoder(req.Body).Decode(&value);err!=nil{return jsonResponse(400,"no"),nil}
   old,err:=parseAnchor(value.Previous)
   if err!=nil||value.Schema!=WireSchema||!sameAnchor(old,s.current){
    return jsonResponse(409,"conflict"),nil
   }
   target,err:=parseAnchor(value.Next)
   if err!=nil||target.Sequence<=old.Sequence||!s.pin.accepts(target){
    return jsonResponse(409,"conflict"),nil
   }
   s.current=target
   s.revision++
   s.commits++
   if s.ambiguousCommit{return nil,errors.New("synthetic lost response AFTER server commit")}
   return jsonResponse(200,casResponse{Schema:WireSchema,Committed:true}),nil
  default:return jsonResponse(404,"not found"),nil
  }
 }
}
func signHead(t *testing.T,a fsahead.Anchor,private ed25519.PrivateKey,seq uint64,head string)fsahead.SignedHead{
 t.Helper()
 p:=fsahead.Payload{Schema:fsahead.Schema,Domain:fsahead.Domain,ArchiveID:a.ArchiveID,KeyID:a.KeyID,
 AuthorityEpoch:a.AuthorityEpoch,ParentSequence:a.Sequence,ParentHeadSHA256:a.HeadSHA256,Sequence:seq,HeadSHA256:head}
 b,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
 return fsahead.SignedHead{Payload:p,SignatureHex:hex.EncodeToString(ed25519.Sign(private,append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),b...)))}
}
func TestAuthenticatedIndependentWitnessAndCheckpointIntegration(t *testing.T){
 client,fake,signer:=fixture(t)
 a,err:=client.ReadAnchor(context.Background())
 if err!=nil||a.Sequence!=0{t.Fatal("genesis witness",err)}
 ok,err:=client.ConfirmArchiveBinding(context.Background(),a.ArchiveID)
 if err!=nil||!ok{t.Fatal("archive binding",err)}
 original,err:=privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName));if err!=nil{t.Fatal(err)}
 row,err:=original.AppendEvent(researchlog.Event{Lane:"Wingless",Generation:1,ExperimentID:"W0001",
 Kind:researchlog.Hypothesis,SourceCommitSHA:hx("c",40),Note:"Synthetic original hypothesis"})
 if err!=nil{t.Fatal(err)}
 id:=fsatrust.Identity{ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKey:a.PublicKey,AuthorityEpoch:a.AuthorityEpoch}
 cp:=signHead(t,a,signer,row.Sequence,row.RecordSHA256)
 trusted,err:=fsatrust.Advance(context.Background(),client,original,id,cp)
 if err!=nil||trusted.Sequence!=1{t.Fatal("witnessed CAS",err)}
 recovered,err:=fsatrust.Recover(context.Background(),client,original,id)
 if err!=nil||recovered.Sequence!=1{t.Fatal("read-only recovery",err)}
 if _,err:=fsatrust.Advance(context.Background(),client,original,id,cp);err==nil{t.Fatal("checkpoint replay accepted")}
 fake.Lock();commits:=fake.commits;methods:=append([]string(nil),fake.methods...);fake.Unlock()
 if commits!=1{t.Fatal("replayed CAS")}
 for _,m:=range methods{
  if strings.Contains(m,"KTRADE")||strings.Contains(m,"CKB")||strings.Contains(m,"Mind-Palace"){
   t.Fatal("foreign endpoint access")
  }
 }
}
func TestWitnessTamperAndBindingMismatchAreFailClosed(t *testing.T){
 client,sim,_:=fixture(t)
 sim.badSignature=true
 if _,err:=client.ReadAnchor(context.Background());!errors.Is(err,ErrWitness){t.Fatal("wrong signer admitted",err)}
 sim.badSignature=false;sim.binding=false
 ok,err:=client.ConfirmArchiveBinding(context.Background(),client.pin.ArchiveID)
 if err!=nil||ok{t.Fatal("unbound physical store admitted",err)}
 sim.binding=true;sim.outage=true
 if _,err:=client.ReadAnchor(context.Background());err==nil{t.Fatal("independent witness outage accepted")}
}
func TestAmbiguousCASRequiresRecoverNotRetry(t *testing.T){
 client,sim,_:=fixture(t)
 original,err:=client.ReadAnchor(context.Background());if err!=nil{t.Fatal(err)}
 next:=original;next.Sequence=1;next.HeadSHA256=hx("d",64)
 sim.ambiguousCommit=true
 if _,err:=client.CompareAndSwap(context.Background(),original,next);err==nil{
  t.Fatal("ambiguous commit wrongly reported success")
 }
 sim.Lock();commits:=sim.commits;sim.Unlock()
 if commits!=1{t.Fatal("simulation did not commit")}
 observed,err:=client.ReadAnchor(context.Background())
 if err!=nil||!sameAnchor(observed,next){t.Fatal("could not reconcile after lost acknowledgement",err)}
 if committed,err:=client.CompareAndSwap(context.Background(),original,next);err!=nil||committed{
  t.Fatal("uncertain operation replayed",err)
 }
}
func TestIndependentMonotonicWitnessRejectsRollback(t *testing.T){
 client,sim,_:=fixture(t)
 previous,err:=client.ReadAnchor(context.Background());if err!=nil{t.Fatal(err)}
 next:=previous;next.Sequence=1;next.HeadSHA256=hx("e",64)
 yes,err:=client.CompareAndSwap(context.Background(),previous,next)
 if err!=nil||!yes{t.Fatal("CAS",err)}
 sim.Lock();sim.current=previous;sim.revision=1;sim.Unlock()
 if _,err:=client.ReadAnchor(context.Background());err==nil{t.Fatal("same-process witnessed rollback accepted")}
 other,_,_:=fixture(t);other.pin.MinimumRevision=2;other.observedRevision=2;other.authority=client.authority;other.witness=client.witness
 if _,err:=other.ReadAnchor(context.Background());err==nil{t.Fatal("operator-pinned revision floor defeated")}
}
func TestRemoteConstructionRequiresIndependentPinnedMutualTLS(t *testing.T){
 c,_,_:=fixture(t);pin:=c.pin
 roots:=x509.NewCertPool()
 peer:=Peer{BaseURL:"https://authority.forge.test",Roots:roots,
 Certificate:tls.Certificate{Certificate:[][]byte{{1}},PrivateKey:struct{}{}},
 ServerSPKISHA256:hx("f",64)}
 if _,err:=NewClient(peer,peer,pin);err==nil{t.Fatal("shared authority and witness origin accepted")}
 witness:=peer;witness.BaseURL="https://witness.forge.test"
 if _,err:=NewClient(peer,witness,pin);err==nil{t.Fatal("different URLs using one server signing key accepted")}
 witness.ServerSPKISHA256=hx("e",64)
 if _,err:=NewClient(peer,witness,pin);err!=nil{t.Fatal("distinct server trust roots rejected",err)}
 untrusted:=peer;untrusted.Roots=nil
 if _,err:=NewClient(untrusted,witness,pin);err==nil{t.Fatal("untrusted TLS roots accepted")}
 untrusted=peer;untrusted.BaseURL="http://authority.forge.test"
 if _,err:=NewClient(untrusted,witness,pin);err==nil{t.Fatal("plain HTTP accepted")}
 untrusted=peer;untrusted.ServerSPKISHA256=""
 if _,err:=NewClient(untrusted,witness,pin);err==nil{t.Fatal("no server SPKI pin accepted")}
 pin.WitnessPublicKey=pin.PublicKey
 if _,err:=NewClient(peer,witness,pin);err==nil{t.Fatal("FSA signer reused for independent witness")}
}
