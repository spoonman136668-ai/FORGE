package fsaservice

import (
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "encoding/hex"
 "encoding/json"
 "math/big"
 "net"
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func testKey(t *testing.T)(ed25519.PublicKey,ed25519.PrivateKey){
 t.Helper()
 pub,key,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 return pub,key
}
func testCA(t *testing.T)(*x509.Certificate,ed25519.PrivateKey,*x509.CertPool){
 t.Helper()
 pub,key:=testKey(t)
 template:=&x509.Certificate{
  SerialNumber:big.NewInt(1),Subject:pkix.Name{CommonName:"FORGE_TEST_CA"},
  NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),
  KeyUsage:x509.KeyUsageCertSign|x509.KeyUsageCRLSign,
  IsCA:true,BasicConstraintsValid:true,
 }
 der,err:=x509.CreateCertificate(rand.Reader,template,template,pub,key)
 if err!=nil{t.Fatal(err)}
 cert,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 roots:=x509.NewCertPool();roots.AddCert(cert)
 return cert,key,roots
}
func certFor(t *testing.T,ca *x509.Certificate,caKey ed25519.PrivateKey,client bool)(tls.Certificate,string){
 t.Helper()
 pub,key:=testKey(t)
 serialLimit:=new(big.Int).Lsh(big.NewInt(1),128)
 serial,err:=rand.Int(rand.Reader,serialLimit);if err!=nil{t.Fatal(err)}
 tmpl:=&x509.Certificate{SerialNumber:serial,Subject:pkix.Name{CommonName:"FORGE_TEST_ONLY"},
  NotBefore:time.Now().Add(-time.Minute),NotAfter:time.Now().Add(time.Hour),
  KeyUsage:x509.KeyUsageDigitalSignature,
 }
 if client{tmpl.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}
 }else{
  tmpl.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}
  tmpl.IPAddresses=[]net.IP{net.ParseIP("127.0.0.1")}
 }
 der,err:=x509.CreateCertificate(rand.Reader,tmpl,ca,pub,caKey)
 if err!=nil{t.Fatal(err)}
 cert,err:=x509.ParseCertificate(der)
 if err!=nil{t.Fatal(err)}
 digest:=sha256.Sum256(cert.RawSubjectPublicKeyInfo)
 return tls.Certificate{Certificate:[][]byte{der,ca.Raw},PrivateKey:key,Leaf:cert},hex.EncodeToString(digest[:])
}
type staticAuthority struct{
 anchor fsahead.Anchor
 digest string
 active bool
}
func(s *staticAuthority)ReadAnchor(context.Context)(fsahead.Anchor,error){return s.anchor,nil}
func(s *staticAuthority)ReadBinding(context.Context,string)(string,bool,error){
 return s.digest,s.active,nil
}
type staticWitness struct{signed fsaremote.SignedWitness}
func(s *staticWitness)ReadWitness(context.Context,string)(fsaremote.SignedWitness,error){
 return s.signed,nil
}
func testService(t *testing.T,h http.Handler,server tls.Certificate,roots *x509.CertPool)*httptest.Server{
 t.Helper()
 service:=httptest.NewUnstartedServer(h)
 service.TLS=&tls.Config{
  MinVersion:tls.VersionTLS13,
  Certificates:[]tls.Certificate{server},
  ClientAuth:tls.RequireAndVerifyClientCert,
  ClientCAs:roots,
 }
 service.StartTLS()
 t.Cleanup(service.Close)
 return service
}
func TestIndependentReadOnlyHandlersThroughRealMutualTLSClient(t *testing.T){
 primaryPub,_:=testKey(t)
 witnessPub,witnessKey:=testKey(t)
 pin:=fsaremote.Pin{
  ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_TEST_PIN",
  PublicKey:primaryPub,AuthorityEpoch:12,
  BindingSHA256:strings.Repeat("b",64),WitnessPublicKey:witnessPub,
  MinimumRevision:3,
 }
 anchor:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis,
 }
 high:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,
  Domain:fsaremote.WitnessDomain,ArchiveID:pin.ArchiveID,
  KeyID:pin.KeyID,AuthorityEpoch:pin.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,
  Sequence:0,HeadSHA256:researchlog.Genesis,Revision:3,
 }
 raw,err:=json.Marshal(high);if err!=nil{t.Fatal(err)}
 witnessSig:=hex.EncodeToString(ed25519.Sign(witnessKey,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...)))
 aStore:=&staticAuthority{anchor:anchor,digest:pin.BindingSHA256,active:true}
 wStore:=&staticWitness{signed:fsaremote.SignedWitness{Head:high,SignatureHex:witnessSig}}
 ca,caKey,roots:=testCA(t)
 clientCert,clientSPKI:=certFor(t,ca,caKey,true)
 authorityCert,authoritySPKI:=certFor(t,ca,caKey,false)
 witnessCert,witnessSPKI:=certFor(t,ca,caKey,false)
 ah,err:=AuthorityHandler(pin,clientSPKI,aStore);if err!=nil{t.Fatal(err)}
 wh,err:=WitnessHandler(pin,clientSPKI,wStore);if err!=nil{t.Fatal(err)}
 aServer:=testService(t,ah,authorityCert,roots)
 wServer:=testService(t,wh,witnessCert,roots)
 client,err:=fsaremote.NewClient(
  fsaremote.Peer{BaseURL:aServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:authoritySPKI},
  fsaremote.Peer{BaseURL:wServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},pin)
 if err!=nil{t.Fatal(err)}
 ctx:=context.Background()
 got,err:=client.ReadAnchor(ctx)
 if err!=nil||got.Sequence!=0||got.HeadSHA256!=researchlog.Genesis{t.Fatal(got,err)}
 bound,err:=client.ConfirmArchiveBinding(ctx,pin.ArchiveID)
 if err!=nil||!bound{t.Fatal("independent physical binding rejected",err)}
 next:=got;next.Sequence=1;next.HeadSHA256=strings.Repeat("c",64)
 written,err:=client.CompareAndSwap(ctx,got,next)
 if err==nil||written{t.Fatal("unsigned read-only service authorized checkpoint mutation")}
 again,err:=client.ReadAnchor(ctx)
 if err!=nil||again.Sequence!=0{t.Fatal("CAS mutated protected anchor",again,err)}
 // A TLS client without a certificate cannot read either service.
 withoutClient:=&http.Client{Transport:&http.Transport{TLSClientConfig:&tls.Config{
  MinVersion:tls.VersionTLS13,RootCAs:roots}}}
 response,err:=withoutClient.Get(aServer.URL+"/v1/fsa/anchor")
 if err==nil{response.Body.Close();t.Fatal("anonymous TLS client admitted")}
 // The signing key is completely independent of both HTTP server keys.
 wStore.signed.SignatureHex=strings.Repeat("0",128)
 if _,err:=client.ReadAnchor(ctx);err==nil{t.Fatal("forged persisted witness admitted")}
 // Pinned server SPKI cannot be silently changed.
 altered,_:=fsaremote.NewClient(
  fsaremote.Peer{BaseURL:aServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},
  fsaremote.Peer{BaseURL:wServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},pin)
 if _,err:=altered.ReadAnchor(ctx);err==nil{t.Fatal("wrong server private key trusted")}
}
func TestHandlersRejectUnprovisionedStoresAndSharedSigner(t *testing.T){
 p:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"abc",
  AuthorityEpoch:1,BindingSHA256:strings.Repeat("b",64),MinimumRevision:1}
 if _,err:=AuthorityHandler(p,strings.Repeat("c",64),&staticAuthority{});err==nil{
  t.Fatal("authority service without independent keys provisioned")
 }
 pub,_:=testKey(t);p.PublicKey=pub;p.WitnessPublicKey=pub
 if _,err:=WitnessHandler(p,strings.Repeat("c",64),&staticWitness{});err==nil{
  t.Fatal("shared signing identity accepted")
 }
}
