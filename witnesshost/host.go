// Package witnesshost runs a separately provisioned, read-only FORGE FSA
// witness HTTPS service. It issues no signatures and cannot launch science.
package witnesshost

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net"
 "net/http"
 "os"
 "path/filepath"
 "runtime"
 "strconv"
 "strings"
 "time"

 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsaservice"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
)

const Schema="forge.fsa.readonly-witness-host.v1"
const MaxConfigBytes=8192
var ErrUnprovisioned=errors.New("FORGE_FSA_WITNESS_HOST_NOT_PROVISIONED")

// Config contains ONLY paths and independently provisioned public pins.
// The PEM server key stays on the witness host; there is no FSA signing key,
// worker token, provisioning endpoint, shared controller or live execution.
type Config struct{
 Schema string `json:"schema"`
 ListenAddress string `json:"listen_address"`
 AllowRemote bool `json:"allow_remote"`
 WitnessRoot string `json:"witness_root"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityPublicKeyHex string `json:"authority_public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 MinimumRevision uint64 `json:"minimum_revision"`
 AllowedClientSPKISHA256 string `json:"allowed_client_spki_sha256"`
 ClientCAFile string `json:"client_ca_file"`
 ServerCertFile string `json:"server_cert_file"`
 ServerKeyFile string `json:"server_key_file"`
}
func hexLower(x string,n int)bool{
 if len(x)!=n{return false}
 for _,c:=range x{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func trustedFile(path string,secret bool)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrUnprovisioned}
 p:=filepath.Clean(path)
 for dir:=p;;{
  info,err:=os.Lstat(dir)
  if err!=nil||info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return nil,ErrUnprovisioned}
  if dir==p{
   if !info.Mode().IsRegular()||info.Size()<=0||info.Size()>1<<20{return nil,ErrUnprovisioned}
   if secret&&runtime.GOOS!="windows"&&info.Mode().Perm()&0077!=0{return nil,ErrUnprovisioned}
  }else if !info.IsDir(){return nil,ErrUnprovisioned}
  next:=filepath.Dir(dir);if next==dir{break};dir=next
 }
 raw,err:=os.ReadFile(p)
 if err!=nil||len(raw)==0||len(raw)>1<<20{return nil,ErrUnprovisioned}
 return raw,nil
}
func(c Config)pin()(fsaremote.Pin,error){
 if c.Schema!=Schema||!hexLower(c.ArchiveID,64)||!hexLower(c.BindingSHA256,64)||
  !hexLower(c.AuthorityPublicKeyHex,64)||!hexLower(c.WitnessPublicKeyHex,64)||
  !hexLower(c.AllowedClientSPKISHA256,64)||c.AuthorityEpoch==0||c.MinimumRevision==0{
  return fsaremote.Pin{},ErrUnprovisioned
 }
 a,err:=hex.DecodeString(c.AuthorityPublicKeyHex);if err!=nil{return fsaremote.Pin{},ErrUnprovisioned}
 w,err:=hex.DecodeString(c.WitnessPublicKeyHex);if err!=nil{return fsaremote.Pin{},ErrUnprovisioned}
 if len(a)!=ed25519.PublicKeySize||len(w)!=ed25519.PublicKeySize||bytes.Equal(a,w){
  return fsaremote.Pin{},ErrUnprovisioned
 }
 return fsaremote.Pin{ArchiveID:c.ArchiveID,KeyID:c.KeyID,PublicKey:a,
  AuthorityEpoch:c.AuthorityEpoch,BindingSHA256:c.BindingSHA256,
  WitnessPublicKey:w,MinimumRevision:c.MinimumRevision},nil
}
func(c Config)checkListen()error{
 host,port,err:=net.SplitHostPort(c.ListenAddress)
 if err!=nil{return ErrUnprovisioned}
 ip:=net.ParseIP(host)
 n,err:=strconv.Atoi(port)
 if err!=nil||n<1||n>65535||ip==nil{return ErrUnprovisioned}
 // Explicit opt-in is required even for a private-network or all-interface
 // address. mTLS and external network policy remain mandatory on remote hosts.
 if !ip.IsLoopback()&&!c.AllowRemote{return ErrUnprovisioned}
 return nil
}
// Load reads one small canonical JSON config. No implicit defaults, env
// expansion, credential creation or replacement of a missing trusted pin.
func Load(path string)(Config,error){
 var c Config
 raw,err:=trustedFile(path,false)
 if err!=nil||len(raw)>MaxConfigBytes{return c,ErrUnprovisioned}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(&c)!=nil||dec.Decode(new(any))!=io.EOF{return Config{},ErrUnprovisioned}
 canonical,err:=json.Marshal(c)
 if err!=nil||!bytes.Equal(bytes.TrimSuffix(raw,[]byte("\n")),canonical){
  return Config{},ErrUnprovisioned
 }
 if c.checkListen()!=nil{return Config{},ErrUnprovisioned}
 if _,err:=c.pin();err!=nil{return Config{},err}
 return c,nil
}

// Server is deliberately read-only. It loads ONLY already-signed and
// already-persisted witness evidence. All paths except GET high-water reject.
func Server(c Config)(*http.Server,error){
 if c.checkListen()!=nil{return nil,ErrUnprovisioned}
 pin,err:=c.pin();if err!=nil{return nil,err}
 witness,err:=fsawitnessstore.Open(c.WitnessRoot,pin)
 if err!=nil{return nil,ErrUnprovisioned}
 caPEM,err:=trustedFile(c.ClientCAFile,false);if err!=nil{return nil,err}
 roots:=x509.NewCertPool()
 if !roots.AppendCertsFromPEM(caPEM){return nil,ErrUnprovisioned}
 certPEM,err:=trustedFile(c.ServerCertFile,false);if err!=nil{return nil,err}
 keyPEM,err:=trustedFile(c.ServerKeyFile,true);if err!=nil{return nil,err}
 certificate,err:=tls.X509KeyPair(certPEM,keyPEM)
 if err!=nil||len(certificate.Certificate)==0{return nil,ErrUnprovisioned}
 parsed,err:=x509.ParseCertificate(certificate.Certificate[0])
 if err!=nil||parsed.IsCA||time.Now().Before(parsed.NotBefore)||time.Now().After(parsed.NotAfter)||
  !hasServerAuth(parsed.ExtKeyUsage){return nil,ErrUnprovisioned}
 handler,err:=fsaservice.WitnessHandler(pin,c.AllowedClientSPKISHA256,witness)
 if err!=nil{return nil,ErrUnprovisioned}
 return &http.Server{Addr:c.ListenAddress,Handler:handler,
  ReadHeaderTimeout:5*time.Second,ReadTimeout:10*time.Second,
  WriteTimeout:10*time.Second,IdleTimeout:15*time.Second,
  MaxHeaderBytes:8192,TLSConfig:&tls.Config{
   MinVersion:tls.VersionTLS13,
   ClientAuth:tls.RequireAndVerifyClientCert,
   ClientCAs:roots,
   Certificates:[]tls.Certificate{certificate},
  }},nil
}
func hasServerAuth(usages []x509.ExtKeyUsage)bool{
 for _,x:=range usages{if x==x509.ExtKeyUsageServerAuth{return true}}
 return false
}
// ServeOn supports isolated offline qualification with an externally owned
// listener. It never launches or provisions a worker or signing service.
func ServeOn(ctx context.Context,c Config,l net.Listener)error{
 if ctx==nil||ctx.Err()!=nil||l==nil{return ErrUnprovisioned}
 server,err:=Server(c);if err!=nil{return err}
 host,_,err:=net.SplitHostPort(l.Addr().String())
 if err!=nil{return ErrUnprovisioned}
 ip:=net.ParseIP(host)
 if ip==nil||!c.AllowRemote&&!ip.IsLoopback(){return ErrUnprovisioned}
 stopped:=make(chan struct{})
 go func(){
  select{
  case <-ctx.Done():
   shutdownCtx,cancel:=context.WithTimeout(context.Background(),5*time.Second)
   _=server.Shutdown(shutdownCtx)
   cancel()
  case <-stopped:
  }
 }()
 err=server.Serve(tls.NewListener(l,server.TLSConfig))
 close(stopped)
 if err==http.ErrServerClosed&&ctx.Err()!=nil{return nil}
 if err!=nil{return fmt.Errorf("%w: service: %v",ErrUnprovisioned,err)}
 return nil
}
// Run binds an explicitly configured IP address. No public port or
// global 0.0.0.0 listener is chosen automatically.
func Run(ctx context.Context,c Config)error{
 if c.checkListen()!=nil||ctx==nil||ctx.Err()!=nil{return ErrUnprovisioned}
 l,err:=net.Listen("tcp",c.ListenAddress)
 if err!=nil{return fmt.Errorf("%w: bind: %v",ErrUnprovisioned,err)}
 defer l.Close()
 return ServeOn(ctx,c,l)
}
var _ = strings.TrimSpace
