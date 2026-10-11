package fsaservice

import (
 "bytes"
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
 "net/http/httptest"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
)
type fakeAuthority struct {
 mu sync.Mutex
 anchor fsahead.Anchor
 attempts int
 indeterminate bool
}
func(s *fakeAuthority)ReadAnchor(context.Context)(fsahead.Anchor,error){
 s.mu.Lock();defer s.mu.Unlock();return s.anchor,nil
}
func(s *fakeAuthority)ConfirmArchiveBinding(context.Context,string)(bool,error){return true,nil}
func(s *fakeAuthority)CompareAndSwap(_ context.Context,p,n fsahead.Anchor)(bool,error){
 s.mu.Lock();defer s.mu.Unlock();s.attempts++
 if s.indeterminate{return false,errors.New("ambiguous")}
 if !sameAnchor(s.anchor,p){return false,nil}
 s.anchor=n;return true,nil
}
type fakeAdmission struct {
 bound bool
 verified bool
 bindingCalls int
 transitionCalls int
}
func(s *fakeAdmission)VerifyPhysicalBinding(_ context.Context,id,hash string)(bool,error){
 s.bindingCalls++
 return s.bound&&id==strings.Repeat("a",64)&&hash==strings.Repeat("c",64),nil
}
func(s *fakeAdmission)VerifySignedTransition(_ context.Context,_,_ fsahead.Anchor)(bool,error){
 s.transitionCalls++;return s.verified,nil
}
type fakeWitness struct { value fsaremote.SignedWitness; err error }
func (s *fakeWitness)ReadHighWater(_ context.Context,_ string)(fsaremote.SignedWitness,error){
 return s.value,s.err
}
func fixedGenesis()fsahead.Anchor{
 pub:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{1},32)).Public().(ed25519.PublicKey)
 return fsahead.Anchor{ArchiveID:strings.Repeat("a",64),KeyID:"fsa-key-1",
  PublicKey:pub,AuthorityEpoch:2,Sequence:0,HeadSHA256:researchlog.Genesis}
}
func testPeer()(*x509.Certificate,string){
 cert:=&x509.Certificate{RawSubjectPublicKeyInfo:[]byte("test-client-key-not-a-production-credential")}
 sum:=sha256.Sum256(cert.RawSubjectPublicKeyInfo)
 return cert,hex.EncodeToString(sum[:])
}
func call(h http.Handler,method,path string,body []byte,authorize bool)*httptest.ResponseRecorder{
 var reader io.Reader
 if len(body)>0{reader=bytes.NewReader(body)}
 r:=httptest.NewRequest(method,"https://fsa.invalid"+path,reader)
 if len(body)>0{r.Header.Set("Content-Type","application/json")}
 if authorize{
  cert,_:=testPeer()
  r.TLS=&tls.ConnectionState{Version:tls.VersionTLS13,
   PeerCertificates:[]*x509.Certificate{cert},VerifiedChains:[][]*x509.Certificate{{cert}}}
 }
 w:=httptest.NewRecorder();h.ServeHTTP(w,r);return w
}
func TestAuthorityHTTPAuthenticationBoundCASAndNoReplay(t *testing.T){
 genesis:=fixedGenesis()
 _,clientPin:=testPeer()
 store:=&fakeAuthority{anchor:genesis}
 admit:=&fakeAdmission{bound:true,verified:true}
 h,err:=NewAuthorityHandler(AuthorityConfig{Backend:store,Admission:admit,Genesis:genesis,
  BindingSHA256:strings.Repeat("c",64),ClientSPKISHA256:clientPin})
 if err!=nil{t.Fatal(err)}
 if got:=call(h,"GET","/v1/fsa/anchor",nil,false).Code;got!=403{t.Fatalf("unauth=%d",got)}
 if admit.bindingCalls!=0{t.Fatal("unauthenticated request invoked admission")}
 if got:=call(h,"GET","/v1/fsa/anchor",nil,true);got.Code!=200{t.Fatalf("anchor=%d %s",got.Code,got.Body.String())}
 if got:=call(h,"GET","/v1/fsa/binding?archive_id="+genesis.ArchiveID,nil,true);got.Code!=200{t.Fatalf("binding=%d",got.Code)}
 for _,path:=range []string{"/v1/fsa/binding?archive_id="+genesis.ArchiveID+"&extra=1",
  "/v1/fsa/binding?archive_id="+genesis.ArchiveID+"&archive_id="+genesis.ArchiveID,
  "/v1/fsa/unknown","/v1/fsa/anchor?extra=1"}{
  if got:=call(h,"GET",path,nil,true);got.Code==200{t.Fatalf("unexpected route accepted: %s",path)}
 }
 next:=genesis;next.Sequence=1;next.HeadSHA256=strings.Repeat("b",64)
 req,_:=json.Marshal(casEnvelope{Schema:fsaremote.WireSchema,Previous:wire(genesis),Next:wire(next)})
 if got:=call(h,"POST","/v1/fsa/cas",req,true);got.Code!=200{t.Fatalf("CAS=%d %s",got.Code,got.Body.String())}
 if got:=call(h,"POST","/v1/fsa/cas",req,true);got.Code!=409{t.Fatalf("replay=%d",got.Code)}
 if store.attempts!=2{t.Fatalf("CAS attempts=%d",store.attempts)}
 var remote anchorEnvelope
 got:=call(h,"GET","/v1/fsa/anchor",nil,true)
 if err:=json.Unmarshal(got.Body.Bytes(),&remote);err!=nil||remote.Anchor.Sequence!=1{
  t.Fatalf("readback: %v %+v",err,remote)
 }
 broken:=next;broken.Sequence=2;broken.HeadSHA256=next.HeadSHA256
 invalid,_:=json.Marshal(casEnvelope{Schema:fsaremote.WireSchema,Previous:wire(next),Next:wire(broken)})
 if got:=call(h,"POST","/v1/fsa/cas",invalid,true);got.Code!=400{t.Fatalf("same-head=%d",got.Code)}
 if store.attempts!=2{t.Fatal("invalid CAS reached backend")}
 admit.bound=false
 if got:=call(h,"POST","/v1/fsa/cas",req,true);got.Code!=503{t.Fatalf("unbound=%d",got.Code)}
 if store.attempts!=2{t.Fatal("unbound CAS reached backend")}
}
func TestAuthorityIndeterminateFailsClosed(t *testing.T){
 genesis:=fixedGenesis();_,pin:=testPeer()
 store:=&fakeAuthority{anchor:genesis,indeterminate:true}
 admit:=&fakeAdmission{bound:true,verified:true}
 h,err:=NewAuthorityHandler(AuthorityConfig{Backend:store,Admission:admit,Genesis:genesis,
  BindingSHA256:strings.Repeat("c",64),ClientSPKISHA256:pin})
 if err!=nil{t.Fatal(err)}
 next:=genesis;next.Sequence=1;next.HeadSHA256=strings.Repeat("b",64)
 raw,_:=json.Marshal(casEnvelope{Schema:fsaremote.WireSchema,Previous:wire(genesis),Next:wire(next)})
 if got:=call(h,"POST","/v1/fsa/cas",raw,true);got.Code!=503{t.Fatalf("ambiguous=%d",got.Code)}
 if store.attempts!=1{t.Fatalf("silent CAS replay: %d",store.attempts)}
 admit.verified=false;store.indeterminate=false
 if got:=call(h,"POST","/v1/fsa/cas",raw,true);got.Code!=503{t.Fatalf("unverified=%d",got.Code)}
 if store.attempts!=1{t.Fatal("unsigned transition reached backend")}
}
func TestWitnessReadOnlySignatureAndIdentity(t *testing.T){
 genesis:=fixedGenesis();_,clientPin:=testPeer()
 witnessSeed:=bytes.Repeat([]byte{2},32)
 priv:=ed25519.NewKeyFromSeed(witnessSeed)
 pin:=fsaremote.Pin{ArchiveID:genesis.ArchiveID,KeyID:genesis.KeyID,
  PublicKey:genesis.PublicKey,AuthorityEpoch:genesis.AuthorityEpoch,
  BindingSHA256:strings.Repeat("c",64),WitnessPublicKey:priv.Public().(ed25519.PublicKey),
  MinimumRevision:5}
 head:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
  ArchiveID:genesis.ArchiveID,KeyID:genesis.KeyID,AuthorityEpoch:genesis.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,Sequence:genesis.Sequence,HeadSHA256:genesis.HeadSHA256,Revision:5}
 body,err:=json.Marshal(head);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(priv,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),body...))
 source:=&fakeWitness{value:fsaremote.SignedWitness{Head:head,SignatureHex:hex.EncodeToString(sig)}}
 h,err:=NewWitnessHandler(WitnessConfig{Reader:source,Pin:pin,ClientSPKISHA256:clientPin})
 if err!=nil{t.Fatal(err)}
 path:="/v1/fsa/highwater?archive_id="+genesis.ArchiveID
 if got:=call(h,"GET",path,nil,false);got.Code!=403{t.Fatalf("unauth=%d",got.Code)}
 if got:=call(h,"GET",path,nil,true);got.Code!=200{t.Fatalf("witness=%d %s",got.Code,got.Body.String())}
 if got:=call(h,"POST",path,nil,true);got.Code==200{t.Fatal("witness accepted write")}
 source.value.Head.Revision=4
 if got:=call(h,"GET",path,nil,true);got.Code!=503{t.Fatalf("stale=%d",got.Code)}
 source.value.Head.Revision=5;source.value.SignatureHex=strings.Repeat("0",128)
 if got:=call(h,"GET",path,nil,true);got.Code!=503{t.Fatalf("forged=%d",got.Code)}
 source.err=errors.New("disconnected")
 if got:=call(h,"GET",path,nil,true);got.Code!=503{t.Fatalf("outage=%d",got.Code)}
}
func TestHandlersRefuseUnprovisionedInputs(t *testing.T){
 if h,err:=NewAuthorityHandler(AuthorityConfig{});err==nil||h!=nil{t.Fatal("empty authority accepted")}
 if h,err:=NewWitnessHandler(WitnessConfig{});err==nil||h!=nil{t.Fatal("empty witness accepted")}
}
