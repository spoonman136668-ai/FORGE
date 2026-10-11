package fsaremoteissuer

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "encoding/hex"
 "encoding/json"
 "encoding/pem"
 "errors"
 "math/big"
 "net"
 "net/http"
 "net/http/httptest"
 "sync"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaissuance"
)
type certs struct {
 roots *x509.CertPool
 server tls.Certificate
 client tls.Certificate
 spki string
}
func testPKI(t *testing.T)certs{
 t.Helper()
 now:=time.Now()
 _,caPrivate,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 caTemplate:=&x509.Certificate{SerialNumber:big.NewInt(1),
  Subject:pkix.Name{CommonName:"Test-only FORGE R7 root"},
  NotBefore:now.Add(-time.Hour),NotAfter:now.Add(time.Hour),
  IsCA:true,BasicConstraintsValid:true,
  KeyUsage:x509.KeyUsageDigitalSignature|x509.KeyUsageCertSign}
 caDER,err:=x509.CreateCertificate(rand.Reader,caTemplate,caTemplate,
  caPrivate.Public(),caPrivate)
 if err!=nil{t.Fatal(err)}
 ca,err:=x509.ParseCertificate(caDER);if err!=nil{t.Fatal(err)}
 pool:=x509.NewCertPool();pool.AddCert(ca)
 build:=func(serial int64,cn string,usage x509.ExtKeyUsage)(tls.Certificate,*x509.Certificate){
  _,private,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
  template:=&x509.Certificate{SerialNumber:big.NewInt(serial),
   Subject:pkix.Name{CommonName:cn},
   NotBefore:now.Add(-time.Hour),NotAfter:now.Add(time.Hour),
   KeyUsage:x509.KeyUsageDigitalSignature,
   ExtKeyUsage:[]x509.ExtKeyUsage{usage}}
  if usage==x509.ExtKeyUsageServerAuth{
   template.DNSNames=[]string{"localhost"}
   template.IPAddresses=[]net.IP{net.ParseIP("127.0.0.1")}
  }
  der,err:=x509.CreateCertificate(rand.Reader,template,ca,private.Public(),caPrivate)
  if err!=nil{t.Fatal(err)}
  certificate,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
  key,err:=x509.MarshalPKCS8PrivateKey(private);if err!=nil{t.Fatal(err)}
  pair,err:=tls.X509KeyPair(pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der}),
   pem.EncodeToMemory(&pem.Block{Type:"PRIVATE KEY",Bytes:key}))
  if err!=nil{t.Fatal(err)}
  return pair,certificate
 }
 server,cert:=build(2,"localhost",x509.ExtKeyUsageServerAuth)
 client,_:=build(3,"FORGE R7 client-only",x509.ExtKeyUsageClientAuth)
 sum:=sha256.Sum256(cert.RawSubjectPublicKeyInfo)
 return certs{roots:pool,server:server,client:client,spki:hex.EncodeToString(sum[:])}
}
type synthetic struct{
 server *httptest.Server
 config Config
 headPrivate ed25519.PrivateKey
 approvalPrivate ed25519.PrivateKey
 mu sync.Mutex
 seen []string
}
func fixture(t *testing.T,mutator func(*Reply),httpCode int)*synthetic{
 t.Helper()
 tlsCert:=testPKI(t)
 headPrivate:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{71},32))
 approvalPrivate:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{72},32))
 fx:=&synthetic{headPrivate:headPrivate,approvalPrivate:approvalPrivate}
 handler:=http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if r.TLS==nil||len(r.TLS.VerifiedChains)==0||
   len(r.TLS.PeerCertificates)!=1||r.Method!=http.MethodPost||
   r.URL.Path!="/v1/fsa/issue-first-use"{
   w.WriteHeader(http.StatusForbidden);return
  }
  var input Request
  decoder:=json.NewDecoder(http.MaxBytesReader(w,r.Body,MaxBytes))
  decoder.DisallowUnknownFields()
  if decoder.Decode(&input)!=nil||input.Schema!=WireSchema||
   !validHex(input.ChallengeHex,64){
   w.WriteHeader(http.StatusBadRequest);return
  }
  fx.mu.Lock();fx.seen=append(fx.seen,input.ChallengeHex);fx.mu.Unlock()
  if httpCode!=http.StatusOK{
   w.WriteHeader(httpCode);return
  }
  i:=input.Intent
  payload:=fsahead.Payload{Schema:fsahead.Schema,Domain:fsahead.Domain,
   ArchiveID:i.ArchiveID,KeyID:"FORGE_R7_TEST",
   AuthorityEpoch:i.AuthorityEpoch,
   ParentSequence:i.PreviousSequence,ParentHeadSHA256:i.PreviousHeadSHA256,
   Sequence:i.ProposedSequence,HeadSHA256:i.ProposedHeadSHA256,
  }
  cpBody,_:=json.Marshal(payload)
  checkpoint:=fsahead.SignedHead{Payload:payload,
   SignatureHex:hex.EncodeToString(ed25519.Sign(headPrivate,
    append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),cpBody...)))}
  reqHash,_:=digest(input)
  headHash,_:=digest(checkpoint)
  approval:=Approval{Schema:ApprovalSchema,
   ArchiveID:i.ArchiveID,AuthorityEpoch:i.AuthorityEpoch,
   Lane:i.Lane,CohortSHA256:i.CohortSHA256,
   RequestSHA256:reqHash,CheckpointSHA256:headHash,
   ChallengeHex:input.ChallengeHex,ApproverKeyID:"FORGE_R7_APPROVER",
   Verdict:"FSA_INDEPENDENT_FIRST_USE_APPROVED"}
  aBody,_:=json.Marshal(approval)
  reply:=Reply{Schema:WireSchema,Approval:approval,Checkpoint:checkpoint,
   ApprovalSignatureHex:hex.EncodeToString(ed25519.Sign(approvalPrivate,
    append([]byte(ApprovalDomain),aBody...)))}
  if mutator!=nil{mutator(&reply)}
  w.Header().Set("Content-Type","application/json")
  _=json.NewEncoder(w).Encode(reply)
 })
 srv:=httptest.NewUnstartedServer(handler)
 srv.TLS=&tls.Config{MinVersion:tls.VersionTLS13,ClientAuth:tls.RequireAndVerifyClientCert,
  ClientCAs:tlsCert.roots,Certificates:[]tls.Certificate{tlsCert.server}}
 srv.StartTLS()
 t.Cleanup(srv.Close)
 fx.server=srv
 fx.config=Config{BaseURL:srv.URL,
  AuthorityURL:"https://authority.forge-independent.example:443",
  WitnessURL:"https://witness.forge-independent.example:443",
  Roots:tlsCert.roots,ClientCertificate:tlsCert.client,
  ServerSPKISHA256:tlsCert.spki,
  ApprovalPublicKey:approvalPrivate.Public().(ed25519.PublicKey),
  FSAHeadPublicKey:headPrivate.Public().(ed25519.PublicKey),
  ApprovalKeyID:"FORGE_R7_APPROVER"}
 return fx
}
func intent()fsaissuance.IssuanceRequest{
 return fsaissuance.IssuanceRequest{PlanSHA256:repeatHex("a"),
  ArchiveID:repeatHex("b"),AuthorityEpoch:7,PreviousSequence:8,
  PreviousHeadSHA256:repeatHex("c"),ProposedSequence:9,
  ProposedHeadSHA256:repeatHex("d"),Lane:"Wingless",
  ExperimentID:"EXP_5",CohortSHA256:repeatHex("e"),
  SourceQualificationWitnessSHA256:repeatHex("f")}
}
func repeatHex(ch string)string{return strings.Repeat(ch,64)}
func TestMTLSIndependentSignedApprovalBindsExactFirstUse(t *testing.T){
 fx:=fixture(t,nil,http.StatusOK)
 client,err:=New(fx.config);if err!=nil{t.Fatal(err)};defer client.Close()
 i:=intent()
 result,err:=client.IssueFirstUse(context.Background(),i)
 if err!=nil{t.Fatal(err)}
 prior:=fsahead.Anchor{ArchiveID:i.ArchiveID,KeyID:"FORGE_R7_TEST",
  PublicKey:fx.headPrivate.Public().(ed25519.PublicKey),
  AuthorityEpoch:i.AuthorityEpoch,Sequence:i.PreviousSequence,
  HeadSHA256:i.PreviousHeadSHA256}
 after,err:=fsahead.VerifySignature(prior,result)
 if err!=nil||after.Sequence!=i.ProposedSequence||
  after.HeadSHA256!=i.ProposedHeadSHA256{t.Fatal("checkpoint not bound to original",err)}
 fx.mu.Lock();n:=len(fx.seen);fx.mu.Unlock()
 if n!=1{t.Fatal("unexpected issuance request count",n)}
}
func TestIndependentPinsAndEndpointSeparation(t *testing.T){
 fx:=fixture(t,nil,http.StatusOK)
 for _,modify:=range []func(*Config){
  func(c *Config){c.BaseURL="http://not-tls.test"},
  func(c *Config){c.AuthorityURL=c.BaseURL},
  func(c *Config){c.WitnessURL=c.BaseURL},
  func(c *Config){c.ApprovalPublicKey=c.FSAHeadPublicKey},
  func(c *Config){c.ServerSPKISHA256=repeatHex("0")},
  func(c *Config){c.Roots=nil},
  func(c *Config){c.ClientCertificate.PrivateKey=nil},
 }{
  c:=fx.config;modify(&c)
  if _,err:=New(c);err==nil{t.Fatal("untrusted issuer configuration accepted")}
 }
}
func TestSignedApprovalAndCertificateTamperingFails(t *testing.T){
 cases:=[]struct{name string;change func(*Reply)}{
  {"no-approval",func(r *Reply){r.ApprovalSignatureHex=repeatHex("0")+repeatHex("0")}},
  {"wrong-cohort",func(r *Reply){r.Approval.CohortSHA256=repeatHex("0")}},
  {"wrong-nonce",func(r *Reply){r.Approval.ChallengeHex=repeatHex("0")}},
  {"wrong-approved-identity",func(r *Reply){r.Approval.ApproverKeyID="ATTACKER"}},
  {"different-head",func(r *Reply){r.Checkpoint.Payload.HeadSHA256=repeatHex("0")}},
  {"wrong-cert-signature",func(r *Reply){r.Checkpoint.SignatureHex=repeatHex("0")+repeatHex("0")}},
  {"wrong-schema",func(r *Reply){r.Schema="forged"}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   fx:=fixture(t,tc.change,http.StatusOK)
   client,err:=New(fx.config);if err!=nil{t.Fatal(err)};defer client.Close()
   if _,err=client.IssueFirstUse(context.Background(),intent());!errors.Is(err,ErrUnauthorized){
    t.Fatal("tampered approval/certificate accepted:",err)
   }
  })
 }
}
func TestIssuerDeniedOrUncertainNeverRetries(t *testing.T){
 for _,status:=range []int{http.StatusForbidden,http.StatusConflict,http.StatusInternalServerError,http.StatusTemporaryRedirect}{
  fx:=fixture(t,nil,status)
  client,err:=New(fx.config);if err!=nil{t.Fatal(err)};defer client.Close()
  _,err=client.IssueFirstUse(context.Background(),intent())
  if err==nil{t.Fatal("denied/uncertain status issued checkpoint",status)}
  fx.mu.Lock();n:=len(fx.seen);fx.mu.Unlock()
  if n!=1{t.Fatalf("unexpected HTTP retry for %d, requests=%d",status,n)}
 }
}
func TestUniqueFreshChallengesNoCrossRequestReplay(t *testing.T){
 fx:=fixture(t,nil,http.StatusOK)
 client,err:=New(fx.config);if err!=nil{t.Fatal(err)};defer client.Close()
 for i:=0;i<2;i++{
  if _,err=client.IssueFirstUse(context.Background(),intent());err!=nil{t.Fatal(err)}
 }
 fx.mu.Lock();defer fx.mu.Unlock()
 if len(fx.seen)!=2||fx.seen[0]==fx.seen[1]{t.Fatal("replayed challenge")}
}
func TestInvalidScopeStopsBeforeNetwork(t *testing.T){
 fx:=fixture(t,nil,http.StatusOK)
 client,err:=New(fx.config);if err!=nil{t.Fatal(err)};defer client.Close()
 input:=intent();input.Lane="KTRADE"
 if _,err=client.IssueFirstUse(context.Background(),input);!errors.Is(err,ErrConfiguration){
  t.Fatal("foreign lane admitted",err)
 }
 fx.mu.Lock();n:=len(fx.seen);fx.mu.Unlock()
 if n!=0{t.Fatal("invalid scope reached FSA")}
}
