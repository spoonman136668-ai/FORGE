package authorityhost

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
 "encoding/pem"
 "errors"
 "math/big"
 "net"
 "net/http"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/fsaanchorstore"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
 "github.com/spoonman136668-ai/forge/researchlog"
 "github.com/spoonman136668-ai/forge/witnesshost"
)
type pki struct{ca *x509.Certificate; key ed25519.PrivateKey; roots *x509.CertPool; caPEM []byte}
func newPKI(t *testing.T)pki{
 t.Helper()
 pub,key,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 c:=&x509.Certificate{SerialNumber:big.NewInt(1),
  Subject:pkix.Name{CommonName:"FORGE R13 ephemeral test CA"},
  NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),
  IsCA:true,BasicConstraintsValid:true,KeyUsage:x509.KeyUsageCertSign}
 der,err:=x509.CreateCertificate(rand.Reader,c,c,pub,key)
 if err!=nil{t.Fatal(err)}
 ca,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 caPEM:=pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der})
 pool:=x509.NewCertPool();if !pool.AppendCertsFromPEM(caPEM){t.Fatal("CA append")}
 return pki{ca:ca,key:key,roots:pool,caPEM:caPEM}
}
func(p pki)issue(t *testing.T,serial int64,isClient bool)([]byte,[]byte,tls.Certificate,string){
 t.Helper()
 pub,key,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 c:=&x509.Certificate{SerialNumber:big.NewInt(serial),NotBefore:time.Now().Add(-time.Hour),
  NotAfter:time.Now().Add(time.Hour),KeyUsage:x509.KeyUsageDigitalSignature}
 if isClient{c.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}
 }else{c.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}
  c.IPAddresses=[]net.IP{net.ParseIP("127.0.0.1")}}
 der,err:=x509.CreateCertificate(rand.Reader,c,p.ca,pub,p.key)
 if err!=nil{t.Fatal(err)}
 keyDER,err:=x509.MarshalPKCS8PrivateKey(key);if err!=nil{t.Fatal(err)}
 certificate:=pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der})
 private:=pem.EncodeToMemory(&pem.Block{Type:"PRIVATE KEY",Bytes:keyDER})
 pair,err:=tls.X509KeyPair(certificate,private);if err!=nil{t.Fatal(err)}
 parsed,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 h:=sha256.Sum256(parsed.RawSubjectPublicKeyInfo)
 return certificate,private,pair,hex.EncodeToString(h[:])
}
func write(t *testing.T,p string,b []byte,mode os.FileMode){
 t.Helper()
 if err:=os.WriteFile(p,b,mode);err!=nil{t.Fatal(err)}
}
func externalBinding(t *testing.T,c Config,private ed25519.PrivateKey,revision uint64)SignedBinding{
 t.Helper()
 h:=BindingHead{Schema:BindingSchema,ArchiveID:c.ArchiveID,
  AuthorityEpoch:c.AuthorityEpoch,BindingSHA256:c.BindingSHA256,
  Revision:revision,Bound:true}
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(private,append([]byte(BindingDomain),raw...))
 return SignedBinding{Head:h,SignatureHex:hex.EncodeToString(sig)}
}
func externalWitness(t *testing.T,p fsaremote.Pin,key ed25519.PrivateKey,a fsahead.Anchor,revision uint64)fsaremote.SignedWitness{
 t.Helper()
 h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
  ArchiveID:p.ArchiveID,KeyID:p.KeyID,AuthorityEpoch:p.AuthorityEpoch,
  BindingSHA256:p.BindingSHA256,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256,Revision:revision}
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(key,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
 return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(sig)}
}
type fixture struct {
 cfg Config
 witness witnesshost.Config
 pin fsaremote.Pin
 checkpoint *fsaanchorstore.Store
 witnessStore *fsawitnessstore.Store
 genesis fsahead.Anchor
 bindingKey ed25519.PrivateKey
 witnessKey ed25519.PrivateKey
 originalProof []byte
 pki pki
 client tls.Certificate
 serverAuthoritySPKI string
 serverWitnessSPKI string
}
func setup(t *testing.T)fixture{
 t.Helper()
 root:=t.TempDir()
 ca:=newPKI(t)
 authorityPub,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 witnessPub,witnessKey,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 bindingPub,bindingKey,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 pin:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_R13_TEST",
  PublicKey:authorityPub,AuthorityEpoch:6,BindingSHA256:strings.Repeat("b",64),
  WitnessPublicKey:witnessPub,MinimumRevision:1}
 genesis:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 checkpointRoot:=filepath.Join(root,fsaanchorstore.FolderName)
 checkpoint,err:=fsaanchorstore.Provision(checkpointRoot,genesis);if err!=nil{t.Fatal(err)}
 witnessRoot:=filepath.Join(root,fsawitnessstore.FolderName)
 witnessStore,err:=fsawitnessstore.Provision(witnessRoot,pin,externalWitness(t,pin,witnessKey,genesis,1))
 if err!=nil{t.Fatal(err)}
 cCA:=filepath.Join(root,"client-ca.pem");write(t,cCA,ca.caPEM,0644)
 aCert,aKey,_,aSPKI:=ca.issue(t,2,false)
 wCert,wKey,_,wSPKI:=ca.issue(t,3,false)
 _,_,clientCert,clientSPKI:=ca.issue(t,4,true)
 aCertPath:=filepath.Join(root,"authority.pem")
 aKeyPath:=filepath.Join(root,"authority-key.pem")
 wCertPath:=filepath.Join(root,"witness.pem")
 wKeyPath:=filepath.Join(root,"witness-key.pem")
 write(t,aCertPath,aCert,0644);write(t,aKeyPath,aKey,0600)
 write(t,wCertPath,wCert,0644);write(t,wKeyPath,wKey,0600)
 proofPath:=filepath.Join(root,"external-binding-proof.json")
 config:=Config{Schema:Schema,ListenAddress:"127.0.0.1:14444",
  CheckpointRoot:checkpointRoot,ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  AuthorityPublicKeyHex:hex.EncodeToString(pin.PublicKey),AuthorityEpoch:pin.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,WitnessPublicKeyHex:hex.EncodeToString(pin.WitnessPublicKey),
  MinimumWitnessRevision:1,MinimumSequence:0,
  BindingProofFile:proofPath,BindingSignerPublicKeyHex:hex.EncodeToString(bindingPub),
  MinimumBindingRevision:1,AllowedClientSPKISHA256:clientSPKI,
  ClientCAFile:cCA,ServerCertFile:aCertPath,ServerKeyFile:aKeyPath}
 proof:=externalBinding(t,config,bindingKey,1)
 data,err:=json.Marshal(proof);if err!=nil{t.Fatal(err)}
 write(t,proofPath,data,0600)
 wcfg:=witnesshost.Config{Schema:witnesshost.Schema,ListenAddress:"127.0.0.1:14445",
  WitnessRoot:witnessRoot,ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  AuthorityPublicKeyHex:config.AuthorityPublicKeyHex,AuthorityEpoch:pin.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,WitnessPublicKeyHex:config.WitnessPublicKeyHex,
  MinimumRevision:1,AllowedClientSPKISHA256:clientSPKI,
  ClientCAFile:cCA,ServerCertFile:wCertPath,ServerKeyFile:wKeyPath}
 return fixture{cfg:config,witness:wcfg,pin:pin,checkpoint:checkpoint,
  witnessStore:witnessStore,genesis:genesis,bindingKey:bindingKey,witnessKey:witnessKey,
  originalProof:data,pki:ca,client:clientCert,serverAuthoritySPKI:aSPKI,serverWitnessSPKI:wSPKI}
}
func TestIndependentReadOnlyHostsUseRealMutualTLSAndFullWitness(t *testing.T){
 f:=setup(t)
 authorityListener,err:=net.Listen("tcp","127.0.0.1:0");if err!=nil{t.Fatal(err)}
 witnessListener,err:=net.Listen("tcp","127.0.0.1:0");if err!=nil{t.Fatal(err)}
 f.cfg.ListenAddress=authorityListener.Addr().String()
 f.witness.ListenAddress=witnessListener.Addr().String()
 ctx,cancel:=context.WithCancel(context.Background())
 done:=make(chan error,2)
 go func(){done<-ServeOn(ctx,f.cfg,authorityListener)}()
 go func(){done<-witnesshost.ServeOn(ctx,f.witness,witnessListener)}()
 defer func(){cancel();for i:=0;i<2;i++{if err:=<-done;err!=nil{t.Fatal(err)}}}()
 remote,err:=fsaremote.NewClient(
  fsaremote.Peer{BaseURL:"https://"+authorityListener.Addr().String(),
   Roots:f.pki.roots,Certificate:f.client,ServerSPKISHA256:f.serverAuthoritySPKI},
  fsaremote.Peer{BaseURL:"https://"+witnessListener.Addr().String(),
   Roots:f.pki.roots,Certificate:f.client,ServerSPKISHA256:f.serverWitnessSPKI},f.pin)
 if err!=nil{t.Fatal(err)}
 if observed,err:=remote.ReadAnchor(ctx);err!=nil||observed.Sequence!=0{t.Fatal("matching independent signed hosts denied",err)}
 if bound,err:=remote.ConfirmArchiveBinding(ctx,f.pin.ArchiveID);err!=nil||!bound{
  t.Fatal("externally signed physical-binding claim denied",err)
 }
 // Neither executable implements the unsafe anchor-only write endpoint.
 badReq,err:=http.NewRequest(http.MethodPost,"https://"+authorityListener.Addr().String()+"/v1/fsa/cas",nil)
 if err!=nil{t.Fatal(err)}
 client:=&http.Client{Transport:&http.Transport{TLSClientConfig:&tls.Config{
  MinVersion:tls.VersionTLS13,RootCAs:f.pki.roots,Certificates:[]tls.Certificate{f.client},
 }},Timeout:5*time.Second}
 reply,err:=client.Do(badReq)
 if err!=nil{t.Fatal(err)}
 reply.Body.Close()
 if reply.StatusCode==http.StatusOK{t.Fatal("unsigned mutation exposed by authority host")}
 next:=f.genesis;next.Sequence=1;next.HeadSHA256=strings.Repeat("c",64)
 if committed,err:=f.checkpoint.CompareAndSwap(ctx,f.genesis,next);err!=nil||!committed{
  t.Fatal("synthetic fixture checkpoint",err)
 }
 if _,err:=remote.ReadAnchor(ctx);err==nil{t.Fatal("checkpoint ahead of independently signed witness accepted")}
 if err:=f.witnessStore.Append(ctx,externalWitness(t,f.pin,f.witnessKey,next,2));err!=nil{t.Fatal(err)}
 if got,err:=remote.ReadAnchor(ctx);err!=nil||got.Sequence!=1{t.Fatal("aligned independently witnessed checkpoint denied",err)}
 if err:=os.Remove(filepath.Join(f.cfg.CheckpointRoot,"receipts","00000001.json"));err!=nil{t.Fatal(err)}
 if _,err:=remote.ReadAnchor(ctx);err==nil{t.Fatal("rollback accepted after observed higher checkpoint")}
}
func TestReadOnlyAuthorityRefusesTamperedBindingAndRestoredProof(t *testing.T){
 f:=setup(t)
 srv,err:=Server(f.cfg)
 if err!=nil{t.Fatal("valid signed external attestation",err)}
 if srv.TLSConfig.MinVersion!=tls.VersionTLS13||srv.TLSConfig.ClientAuth!=tls.RequireAndVerifyClientCert{
  t.Fatal("authority TLS downgraded")
 }
 if err:=os.WriteFile(f.cfg.BindingProofFile,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Server(f.cfg);!errors.Is(err,ErrUnprovisioned){t.Fatal("untrusted physical attestation admitted",err)}
 write(t,f.cfg.BindingProofFile,f.originalProof,0600)
 bad:=f.cfg;bad.MinimumBindingRevision=2
 if _,err:=Server(bad);!errors.Is(err,ErrUnprovisioned){t.Fatal("independent higher binding revision floor ignored",err)}
 bad=f.cfg;bad.MinimumSequence=1
 if _,err:=Server(bad);!errors.Is(err,ErrUnprovisioned){t.Fatal("independent checkpoint floor ignored",err)}
 bad=f.cfg;bad.BindingSignerPublicKeyHex=bad.AuthorityPublicKeyHex
 if _,err:=Server(bad);!errors.Is(err,ErrUnprovisioned){t.Fatal("archive signer reused as independent binding root",err)}
 bad=f.cfg;bad.ListenAddress="0.0.0.0:14444"
 if _,err:=Server(bad);!errors.Is(err,ErrUnprovisioned){t.Fatal("public listener without opt-in",err)}
}
