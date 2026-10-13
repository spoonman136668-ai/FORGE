package fsaremote

import (
 "bytes"
 "context"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "net/url"
 "strings"
 "sync"
 "time"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
)

// Each peer is separately provisioned with a trusted TLS CA, client identity,
// and server public-key pin. The endpoints MUST reside in separate protected
// failure domains. Sharing one host, credential or storage is disallowed.
type Peer struct {
 BaseURL string
 Roots *x509.CertPool
 Certificate tls.Certificate
 ServerSPKISHA256 string
}
type Client struct {
 authorityURL string
 witnessURL string
 authority *http.Client
 witness *http.Client
 pin Pin
 mu sync.Mutex
 observedRevision uint64
 observedHead string
}
type anchorResponse struct {
 Schema string `json:"schema"`
 Anchor AnchorWire `json:"anchor"`
}
type bindingResponse struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 BindingSHA256 string `json:"binding_sha256"`
 Bound bool `json:"bound"`
}
type witnessResponse struct {
 Schema string `json:"schema"`
 Witness SignedWitness `json:"witness"`
}
type casRequest struct {
 Schema string `json:"schema"`
 Previous AnchorWire `json:"previous"`
 Next AnchorWire `json:"next"`
}
type casResponse struct {
 Schema string `json:"schema"`
 Committed bool `json:"committed"`
}
func checkedURL(s string)(string,error){
 u,err:=url.Parse(s)
 if err!=nil||u.Scheme!="https"||u.Host==""||u.User!=nil||
  u.Path!=""&&u.Path!="/"||u.RawQuery!=""||u.Fragment!=""||
  u.Hostname()==""||strings.ContainsAny(u.Host,"@\\\r\n\x00"){
  return "",errors.New("FORGE_FSA_REMOTE_ENDPOINT_UNSAFE")
 }
 return "https://"+u.Host,nil
}
func peerClient(p Peer)(string,*http.Client,error){
 endpoint,err:=checkedURL(p.BaseURL)
 if err!=nil{return "",nil,err}
 if p.Roots==nil||len(p.Certificate.Certificate)==0||p.Certificate.PrivateKey==nil||
  !validHex(p.ServerSPKISHA256,64){
  return "",nil,errors.New("FORGE_FSA_REMOTE_MTLS_AND_SPKI_REQUIRED")
 }
 pin:=p.ServerSPKISHA256
 conf:=&tls.Config{
  MinVersion:tls.VersionTLS13,
  RootCAs:p.Roots.Clone(),
  Certificates:[]tls.Certificate{p.Certificate},
  VerifyConnection:func(c tls.ConnectionState)error{
   if len(c.VerifiedChains)==0||len(c.PeerCertificates)==0{return ErrRemote}
   sum:=sha256.Sum256(c.PeerCertificates[0].RawSubjectPublicKeyInfo)
   if hex.EncodeToString(sum[:])!=pin{return ErrRemote}
   return nil
  },
 }
 transport:=&http.Transport{TLSClientConfig:conf,MaxIdleConnsPerHost:2,
  IdleConnTimeout:5*time.Second,TLSHandshakeTimeout:5*time.Second,
  DisableCompression:true}
 client:=&http.Client{Transport:transport,Timeout:12*time.Second,
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
 return endpoint,client,nil
}
func NewClient(authority,witness Peer,pin Pin)(*Client,error){
 if !pin.valid(){return nil,ErrMismatch}
 aURL,aClient,err:=peerClient(authority);if err!=nil{return nil,err}
 wURL,wClient,err:=peerClient(witness);if err!=nil{return nil,err}
 if aURL==wURL||authority.ServerSPKISHA256==witness.ServerSPKISHA256{return nil,errors.New("FORGE_FSA_REMOTE_SHARED_TRUST_ENDPOINT_OR_SERVER_KEY_FORBIDDEN")}
 return &Client{authorityURL:aURL,witnessURL:wURL,authority:aClient,witness:wClient,
  pin:pin,observedRevision:pin.MinimumRevision},nil
}
func (c *Client)exchange(ctx context.Context,target *http.Client,base,method,path string,request any,response any)(int,error){
 if c==nil||ctx==nil||ctx.Err()!=nil||target==nil||base==""{return 0,ErrRemote}
 var body io.Reader
 if request!=nil{
  b,err:=json.Marshal(request);if err!=nil||len(b)>MaxResponseBytes{return 0,ErrRemote}
  body=bytes.NewReader(b)
 }
 req,err:=http.NewRequestWithContext(ctx,method,base+path,body)
 if err!=nil{return 0,ErrRemote}
 req.Header.Set("Accept","application/json")
 if request!=nil{req.Header.Set("Content-Type","application/json")}
 result,err:=target.Do(req)
 if err!=nil{return 0,ErrRemote}
 defer result.Body.Close()
 if result.StatusCode==http.StatusConflict{return result.StatusCode,nil}
 if result.StatusCode!=http.StatusOK{return result.StatusCode,ErrRemote}
 raw,err:=io.ReadAll(io.LimitReader(result.Body,MaxResponseBytes+1))
 if err!=nil||len(raw)==0||len(raw)>MaxResponseBytes{return 0,ErrRemote}
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 if err:=decoder.Decode(response);err!=nil{return 0,ErrRemote}
 var extra any
 if err:=decoder.Decode(&extra);err!=io.EOF{return 0,ErrRemote}
 return result.StatusCode,nil
}
func (c *Client)receive(ctx context.Context)(fsahead.Anchor,SignedWitness,error){
 var empty fsahead.Anchor
 if c==nil{return empty,SignedWitness{},ErrRemote}
 var remote anchorResponse
 if _,err:=c.exchange(ctx,c.authority,c.authorityURL,http.MethodGet,"/v1/fsa/anchor",nil,&remote);err!=nil{return empty,SignedWitness{},err}
 if remote.Schema!=WireSchema{return empty,SignedWitness{},ErrRemote}
 a,err:=parseAnchor(remote.Anchor);if err!=nil||!c.pin.accepts(a){return empty,SignedWitness{},ErrMismatch}
 var witness witnessResponse
 route:="/v1/fsa/highwater?archive_id="+url.QueryEscape(c.pin.ArchiveID)
 if _,err:=c.exchange(ctx,c.witness,c.witnessURL,http.MethodGet,route,nil,&witness);err!=nil{return empty,SignedWitness{},err}
 if witness.Schema!=WireSchema||VerifyWitness(c.pin,witness.Witness,a)!=nil{return empty,SignedWitness{},ErrWitness}
 c.mu.Lock()
 defer c.mu.Unlock()
 rev:=witness.Witness.Head.Revision
 if rev<c.observedRevision||(rev==c.observedRevision&&c.observedHead!=""&&c.observedHead!=a.HeadSHA256){
  return empty,SignedWitness{},ErrWitness
 }
 c.observedRevision=rev
 c.observedHead=a.HeadSHA256
 return a,witness.Witness,nil
}
func (c *Client)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 a,_,err:=c.receive(ctx);return a,err
}
func (c *Client)ConfirmArchiveBinding(ctx context.Context,archiveID string)(bool,error){
 if c==nil||!c.pin.valid()||archiveID!=c.pin.ArchiveID{return false,ErrMismatch}
 if _,_,err:=c.receive(ctx);err!=nil{return false,err}
 var response bindingResponse
 route:="/v1/fsa/binding?archive_id="+url.QueryEscape(archiveID)
 if _,err:=c.exchange(ctx,c.authority,c.authorityURL,http.MethodGet,route,nil,&response);err!=nil{return false,err}
 if response.Schema!=WireSchema||response.ArchiveID!=archiveID||
  response.BindingSHA256!=c.pin.BindingSHA256{return false,ErrMismatch}
 return response.Bound,nil
}
func (c *Client)CompareAndSwap(ctx context.Context,previous,next fsahead.Anchor)(bool,error){
 if c==nil||!c.pin.valid()||!c.pin.accepts(previous)||!c.pin.accepts(next)||
  next.Sequence<=previous.Sequence||next.HeadSHA256==previous.HeadSHA256{
  return false,ErrMismatch
 }
 current,_,err:=c.receive(ctx)
 if err!=nil{return false,err}
 if !sameAnchor(previous,current){return false,nil}
 request:=casRequest{Schema:WireSchema,Previous:makeWire(previous),Next:makeWire(next)}
 var response casResponse
 code,err:=c.exchange(ctx,c.authority,c.authorityURL,http.MethodPost,"/v1/fsa/cas",request,&response)
 if err!=nil{return false,ErrRemote} // commit may already have occurred
 if code==http.StatusConflict{return false,nil}
 if response.Schema!=WireSchema||!response.Committed{return false,ErrRemote}
 observed,_,err:=c.receive(ctx)
 if err!=nil||!sameAnchor(observed,next){return false,ErrRemote}
 return true,nil
}
var _ fsatrust.Authority = (*Client)(nil)
