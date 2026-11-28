package main
import (
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "math/big"
 "net"
 "net/http"
 "net/http/httputil"
 "net/url"
 "os"
 "path/filepath"
 "strconv"
 "strings"
 "time"
)
func must(e error){if e!=nil{panic("fixture proxy error")}}
func main(){
 if len(os.Args)!=4{panic("fixture proxy arguments")}
 port,err:=strconv.Atoi(os.Args[1]);must(err);if port<=1024||port>65535{panic("fixture port")}
 root:=os.Args[2]
 upstream,_:=url.Parse(fmt.Sprintf("http://127.0.0.1:%d",port))
 key,err:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);must(err)
 now:=time.Now()
 cert:=x509.Certificate{SerialNumber:big.NewInt(1),Subject:pkix.Name{CommonName:"K-Messenger disposable fixture"},NotBefore:now.Add(-time.Minute),NotAfter:now.Add(30*time.Minute),IPAddresses:[]net.IP{net.ParseIP("127.0.0.1")},KeyUsage:x509.KeyUsageDigitalSignature,ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
 der,err:=x509.CreateCertificate(rand.Reader,&cert,&cert,&key.PublicKey,key);must(err)
 spki,err:=x509.MarshalPKIXPublicKey(&key.PublicKey);must(err);hash:=sha256.Sum256(spki)
 l,err:=net.Listen("tcp4","127.0.0.1:0");must(err)
 origin:="https://"+l.Addr().String()
 rp:=httputil.NewSingleHostReverseProxy(upstream)
 rp.Transport=&http.Transport{Proxy:nil,DialContext:(&net.Dialer{Timeout:5*time.Second}).DialContext,ResponseHeaderTimeout:45*time.Second}
 rp.ModifyResponse=func(r *http.Response)error{if r.StatusCode>=300&&r.StatusCode<400{return fmt.Errorf("redirect denied")};return nil}
 h:=http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if r.Host!=l.Addr().String(){http.Error(w,"denied",421);return}
  w.Header().Set("Cache-Control","no-store")
  w.Header().Set("Referrer-Policy","no-referrer")
  w.Header().Set("X-Content-Type-Options","nosniff")
  w.Header().Set("Content-Security-Policy","default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
  if strings.HasPrefix(r.URL.Path,"/_matrix/client/"){
   if r.URL.Query().Has("access_token"){http.Error(w,"denied",403);return}
   rp.ServeHTTP(w,r);return
  }
  if r.Method!="GET"&&r.Method!="HEAD"{http.Error(w,"denied",405);return}
  switch r.URL.Path{
  case "/":w.Header().Set("Content-Type","text/html; charset=utf-8");fmt.Fprint(w,"<!doctype html><meta charset=utf-8><title>Disposable browser qualification</title><script type=module src=/app.js></script>")
  case "/app.js":w.Header().Set("Content-Type","application/javascript");http.ServeFile(w,r,filepath.Join(root,"app.js"))
  case "/pkg/matrix_sdk_crypto_wasm_bg.wasm":w.Header().Set("Content-Type","application/wasm");http.ServeFile(w,r,filepath.Join(root,"pkg","matrix_sdk_crypto_wasm_bg.wasm"))
  default:http.NotFound(w,r)
  }
 })
 info,err:=json.Marshal(map[string]string{"origin":origin,"pin":base64.StdEncoding.EncodeToString(hash[:])});must(err)
 must(os.WriteFile(os.Args[3],info,0600))
 s:=&http.Server{Handler:h,ReadHeaderTimeout:10*time.Second,TLSConfig:&tls.Config{MinVersion:tls.VersionTLS12,Certificates:[]tls.Certificate{{Certificate:[][]byte{der},PrivateKey:key}}}}
 must(s.Serve(tls.NewListener(l,s.TLSConfig)))
}
