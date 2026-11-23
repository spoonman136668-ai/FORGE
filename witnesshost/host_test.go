package witnesshost

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
 "io"
 "math/big"
 "net"
 "net/http"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
 "github.com/spoonman136668-ai/forge/researchlog"
)
type pki struct{
 rootPEM []byte
 ca *x509.Certificate
 caKey ed25519.PrivateKey
}
func newPKI(t *testing.T)pki{
 t.Helper()
 pub,key,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 ca:=&x509.Certificate{SerialNumber:big.NewInt(1),
  Subject:pkix.Name{CommonName:"FORGE offline test CA"},
  NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(24*time.Hour),
  IsCA:true,BasicConstraintsValid:true,KeyUsage:x509.KeyUsageCertSign}
 der,err:=x509.CreateCertificate(rand.Reader,ca,ca,pub,key)
 if err!=nil{t.Fatal(err)}
 cert,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 return pki{rootPEM:pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der}),ca:cert,caKey:key}
}
func(p pki)makeCert(t *testing.T,serial int64,client bool)([]byte,[]byte,tls.Certificate,string){
 t.Helper()
 pub,key,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 leaf:=&x509.Certificate{SerialNumber:big.NewInt(serial),
  Subject:pkix.Name{CommonName:"FORGE isolated test peer"},
  NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),
  KeyUsage:x509.KeyUsageDigitalSignature}
 if client{leaf.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}
 }else{leaf.ExtKeyUsage=[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}
  leaf.IPAddresses=[]net.IP{net.ParseIP("127.0.0.1")}}
 der,err:=x509.CreateCertificate(rand.Reader,leaf,p.ca,pub,p.caKey)
 if err!=nil{t.Fatal(err)}
 privDER,err:=x509.MarshalPKCS8PrivateKey(key);if err!=nil{t.Fatal(err)}
 certPEM:=pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der})
 keyPEM:=pem.EncodeToMemory(&pem.Block{Type:"PRIVATE KEY",Bytes:privDER})
 cert,err:=tls.X509KeyPair(certPEM,keyPEM);if err!=nil{t.Fatal(err)}
 sum:=sha256.Sum256(derSPKI(t,der))
 return certPEM,keyPEM,cert,hex.EncodeToString(sum[:])
}
func derSPKI(t *testing.T,der []byte)[]byte{
 t.Helper()
 c,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 return c.RawSubjectPublicKeyInfo
}
type fixture struct{
 cfg Config
 pin fsaremote.Pin
 root string
 store *fsawitnessstore.Store
 witnessKey ed25519.PrivateKey
 ca pki
 authorized tls.Certificate
 foreign tls.Certificate
 configPath string
}
func write(t *testing.T,path string,body []byte,mode os.FileMode){
 t.Helper()
 if err:=os.WriteFile(path,body,mode);err!=nil{t.Fatal(err)}
}
func newFixture(t *testing.T)fixture{
 t.Helper()
 dir:=t.TempDir()
 authorityPub,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 witnessPub,witnessKey,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 ca:=newPKI(t)
 serverPEM,serverKey,_,_:=ca.makeCert(t,2,false)
 _,_,allowed,allowedSPKI:=ca.makeCert(t,3,true)
 _,_,foreign,_:=ca.makeCert(t,4,true)
 caFile:=filepath.Join(dir,"clients.pem")
 certFile:=filepath.Join(dir,"server.pem")
 keyFile:=filepath.Join(dir,"server-key.pem")
 write(t,caFile,ca.rootPEM,0644)
 write(t,certFile,serverPEM,0644)
 write(t,keyFile,serverKey,0600)
 pin:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_WITNESS_HOST_TEST",
  PublicKey:authorityPub,AuthorityEpoch:8,BindingSHA256:strings.Repeat("b",64),
  WitnessPublicKey:witnessPub,MinimumRevision:1}
 root:=filepath.Join(dir,fsawitnessstore.FolderName)
 signed:=signWitness(t,pin,witnessKey,1)
 store,err:=fsawitnessstore.Provision(root,pin,signed)
 if err!=nil{t.Fatal(err)}
 cfg:=Config{Schema:Schema,ListenAddress:"127.0.0.1:14444",
  WitnessRoot:root,ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  AuthorityPublicKeyHex:hex.EncodeToString(pin.PublicKey),AuthorityEpoch:pin.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,WitnessPublicKeyHex:hex.EncodeToString(pin.WitnessPublicKey),
  MinimumRevision:1,AllowedClientSPKISHA256:allowedSPKI,
  ClientCAFile:caFile,ServerCertFile:certFile,ServerKeyFile:keyFile}
 configPath:=filepath.Join(dir,"witness-public-config.json")
 raw,err:=json.Marshal(cfg);if err!=nil{t.Fatal(err)}
 write(t,configPath,append(raw,'\n'),0600)
 return fixture{cfg:cfg,pin:pin,root:root,store:store,witnessKey:witnessKey,
  ca:ca,authorized:allowed,foreign:foreign,configPath:configPath}
}
func signWitness(t *testing.T,p fsaremote.Pin,key ed25519.PrivateKey,rev uint64)fsaremote.SignedWitness{
 t.Helper()
 h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,
  Domain:fsaremote.WitnessDomain,ArchiveID:p.ArchiveID,KeyID:p.KeyID,
  AuthorityEpoch:p.AuthorityEpoch,BindingSHA256:p.BindingSHA256,
  Sequence:0,HeadSHA256:researchlog.Genesis,Revision:rev}
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(key,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
 return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(sig)}
}
func client(p pki,cert *tls.Certificate)*http.Client{
 roots:=x509.NewCertPool();roots.AppendCertsFromPEM(p.rootPEM)
 conf:=&tls.Config{MinVersion:tls.VersionTLS13,RootCAs:roots}
 if cert!=nil{conf.Certificates=[]tls.Certificate{*cert}}
 return &http.Client{Timeout:5*time.Second,Transport:&http.Transport{TLSClientConfig:conf},
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
}
func call(t *testing.T,c *http.Client,method,url string)(int,[]byte,error){
 t.Helper()
 req,err:=http.NewRequest(method,url,nil);if err!=nil{t.Fatal(err)}
 resp,err:=c.Do(req)
 if err!=nil{return 0,nil,err}
 defer resp.Body.Close()
 raw,err:=io.ReadAll(io.LimitReader(resp.Body,fsaremote.MaxResponseBytes+1))
 return resp.StatusCode,raw,err
}
func TestWitnessHostRealTLSReadOnlyAndRestartHighwater(t *testing.T){
 f:=newFixture(t)
 cfg,err:=Load(f.configPath);if err!=nil{t.Fatal("canonical provisioned config",err)}
 listener,err:=net.Listen("tcp","127.0.0.1:0");if err!=nil{t.Fatal(err)}
 cfg.ListenAddress=listener.Addr().String()
 ctx,cancel:=context.WithCancel(context.Background())
 finished:=make(chan error,1)
 go func(){finished<-ServeOn(ctx,cfg,listener)}()
 defer func(){cancel();if err:=<-finished;err!=nil{t.Fatal(err)}}()
 url:="https://"+listener.Addr().String()+"/v1/fsa/highwater?archive_id="+f.pin.ArchiveID
 good:=client(f.ca,&f.authorized)
 status,raw,err:=call(t,good,http.MethodGet,url)
 if err!=nil||status!=http.StatusOK{t.Fatal("signed witness not served",status,err,string(raw))}
 var reply struct{Schema string `json:"schema"`;Witness fsaremote.SignedWitness `json:"witness"`}
 if err:=json.Unmarshal(raw,&reply);err!=nil||reply.Schema!=fsaremote.WireSchema{
  t.Fatal("invalid canonical witness",err)
 }
 anchor:=fsahead.Anchor{ArchiveID:f.pin.ArchiveID,KeyID:f.pin.KeyID,
  PublicKey:f.pin.PublicKey,AuthorityEpoch:f.pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 if err:=fsaremote.VerifyWitness(f.pin,reply.Witness,anchor);err!=nil{t.Fatal(err)}
 if code,_,_:=call(t,good,http.MethodPost,url);code!=http.StatusMethodNotAllowed{
  t.Fatal("mutating signed witness endpoint",code)
 }
 if code,_,_:=call(t,good,http.MethodGet,"https://"+listener.Addr().String()+"/v1/fsa/cas");code!=http.StatusNotFound{
  t.Fatal("unsigned write route exposed",code)
 }
 if code,_,_:=call(t,client(f.ca,&f.foreign),http.MethodGet,url);code!=http.StatusUnauthorized{
  t.Fatal("wrong client public key admitted",code)
 }
 if _,_,err:=call(t,client(f.ca,nil),http.MethodGet,url);err==nil{
  t.Fatal("TLS handshake without client certificate admitted")
 }
 if err:=f.store.Append(context.Background(),signWitness(t,f.pin,f.witnessKey,2));err!=nil{t.Fatal(err)}
 status,raw,err=call(t,good,http.MethodGet,url)
 if err!=nil||status!=http.StatusOK{t.Fatal("advanced signed revision not served",status,err)}
 if err:=json.Unmarshal(raw,&reply);err!=nil||reply.Witness.Head.Revision!=2{
  t.Fatal("signed revision not advanced",err)
 }
 // The local store cannot silently serve a previously witnessed lower state.
 if err:=os.Remove(filepath.Join(f.root,"receipts","00000001.json"));err!=nil{t.Fatal(err)}
 if code,_,err:=call(t,good,http.MethodGet,url);err!=nil||code!=http.StatusServiceUnavailable{
  t.Fatal("valid-tail rollback served to authenticated remote client",code,err)
 }
 cfg.MinimumRevision=2
 if _,err:=Server(cfg);!errors.Is(err,ErrUnprovisioned){
  t.Fatal("restart with external higher floor admitted rollback",err)
 }
}
func TestWitnessHostFailClosedProvisioningAndNoPublicDefault(t *testing.T){
 f:=newFixture(t)
 tests:=[]struct{name string;mutate func(*Config)}{
  {"wildcard without opt-in",func(c *Config){c.ListenAddress="0.0.0.0:14444"}},
  {"hostname not pinned",func(c *Config){c.ListenAddress="localhost:14444"}},
  {"missing revision pin",func(c *Config){c.MinimumRevision=0}},
  {"foreign signer",func(c *Config){c.WitnessPublicKeyHex=c.AuthorityPublicKeyHex}},
  {"untrusted client",func(c *Config){c.AllowedClientSPKISHA256=""}},
  {"missing TLS key",func(c *Config){c.ServerKeyFile=filepath.Join(t.TempDir(),"missing.pem")}},
  {"missing archive",func(c *Config){c.WitnessRoot=filepath.Join(t.TempDir(),fsawitnessstore.FolderName)}},
 }
 for _,tt:=range tests{t.Run(tt.name,func(t *testing.T){
  c:=f.cfg;tt.mutate(&c)
  if _,err:=Server(c);err==nil{t.Fatal("unsafe witness provisioning accepted")}
 })}
 bad:=[]byte(`{"schema":"`+Schema+`","schema":"duplicate"}`)
 write(t,f.configPath,bad,0600)
 if _,err:=Load(f.configPath);err==nil{t.Fatal("duplicate property admitted")}
 if runtime.GOOS!="windows"{
  write(t,f.cfg.ServerKeyFile,[]byte("EXPOSED"),0644)
  if _,err:=Server(f.cfg);err==nil{t.Fatal("world-readable private server key accepted")}
 }
}
