// Package authorityhost provides a separately provisioned, read-only FSA
// checkpoint HTTPS process. It cannot sign science or issue worker authority.
package authorityhost

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net"
 "net/http"
 "os"
 "path/filepath"
 "strconv"
 "sync"
 "time"

 "github.com/spoonman136668-ai/forge/fsaanchorstore"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsaservice"
 "github.com/spoonman136668-ai/forge/researchlog"
 "github.com/spoonman136668-ai/forge/witnesshost"
)

const (
 Schema="forge.fsa.readonly-authority-host.v1"
 BindingSchema="forge.fsa.external-binding-proof.v1"
 BindingDomain="FORGE-FSA-EXTERNAL-ARCHIVE-BINDING-V1\n"
 MaxConfigBytes=8192
 MaxProofBytes=4096
)
var ErrUnprovisioned=errors.New("FORGE_FSA_AUTHORITY_HOST_UNPROVISIONED")

// Config is independently provisioned. No signer or writer is available
// to this process, even with a valid full scientific archive.
type Config struct {
 Schema string `json:"schema"`
 ListenAddress string `json:"listen_address"`
 AllowRemote bool `json:"allow_remote"`
 CheckpointRoot string `json:"checkpoint_root"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityPublicKeyHex string `json:"authority_public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 MinimumWitnessRevision uint64 `json:"minimum_witness_revision"`
 MinimumSequence uint64 `json:"minimum_sequence"`
 BindingProofFile string `json:"binding_proof_file"`
 BindingSignerPublicKeyHex string `json:"binding_signer_public_key_hex"`
 MinimumBindingRevision uint64 `json:"minimum_binding_revision"`
 AllowedClientSPKISHA256 string `json:"allowed_client_spki_sha256"`
 ClientCAFile string `json:"client_ca_file"`
 ServerCertFile string `json:"server_cert_file"`
 ServerKeyFile string `json:"server_key_file"`
}
// BindingHead MUST be signed by a distinct, externally operated attestor.
// A signature attests only what that attestor actually validated; it is
// never self-issued by a local checkpoint directory or by a worker.
type BindingHead struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 Revision uint64 `json:"revision"`
 Bound bool `json:"bound"`
}
type SignedBinding struct {
 Head BindingHead `json:"head"`
 SignatureHex string `json:"signature_hex"`
}
func lowerHex(x string,n int)bool{
 if len(x)!=n{return false}
 for _,ch:=range x{if !(ch>='0'&&ch<='9'||ch>='a'&&ch<='f'){return false}}
 return true
}
func readPlain(path string,limit int)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrUnprovisioned}
 clean:=filepath.Clean(path)
 for p:=clean;;{
  stat,err:=os.Lstat(p)
  if err!=nil||stat.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return nil,ErrUnprovisioned}
  if p==clean{
   if !stat.Mode().IsRegular()||stat.Size()<=0||stat.Size()>int64(limit){return nil,ErrUnprovisioned}
  }else if !stat.IsDir(){return nil,ErrUnprovisioned}
  next:=filepath.Dir(p);if next==p{break};p=next
 }
 raw,err:=os.ReadFile(clean)
 if err!=nil||len(raw)==0||len(raw)>limit{return nil,ErrUnprovisioned}
 return raw,nil
}
func canonicalFile(path string,limit int,target any)error{
 raw,err:=readPlain(path,limit);if err!=nil{return err}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(target)!=nil||dec.Decode(new(any))!=io.EOF{return ErrUnprovisioned}
 canonical,err:=json.Marshal(target)
 if err!=nil||!bytes.Equal(bytes.TrimSuffix(raw,[]byte("\n")),canonical){return ErrUnprovisioned}
 return nil
}
func(c Config)validListen()bool{
 host,port,err:=net.SplitHostPort(c.ListenAddress)
 if err!=nil{return false}
 ip:=net.ParseIP(host)
 p,err:=strconv.Atoi(port)
 return err==nil&&ip!=nil&&p>0&&p<=65535&&(ip.IsLoopback()||c.AllowRemote)
}
func(c Config)pin()(fsaremote.Pin,ed25519.PublicKey,error){
 if c.Schema!=Schema||!c.validListen()||!lowerHex(c.ArchiveID,64)||
  !lowerHex(c.AuthorityPublicKeyHex,64)||!lowerHex(c.WitnessPublicKeyHex,64)||
  !lowerHex(c.BindingSHA256,64)||!lowerHex(c.BindingSignerPublicKeyHex,64)||
  !lowerHex(c.AllowedClientSPKISHA256,64)||c.AuthorityEpoch==0||
  c.MinimumWitnessRevision==0||c.MinimumBindingRevision==0||
  c.MinimumSequence>researchlog.MaxEntries{
  return fsaremote.Pin{},nil,ErrUnprovisioned
 }
 a,_:=hex.DecodeString(c.AuthorityPublicKeyHex)
 w,_:=hex.DecodeString(c.WitnessPublicKeyHex)
 b,_:=hex.DecodeString(c.BindingSignerPublicKeyHex)
 if len(a)!=ed25519.PublicKeySize||len(w)!=ed25519.PublicKeySize||
  len(b)!=ed25519.PublicKeySize||bytes.Equal(a,w)||bytes.Equal(a,b)||
  bytes.Equal(w,b){return fsaremote.Pin{},nil,ErrUnprovisioned}
 return fsaremote.Pin{ArchiveID:c.ArchiveID,KeyID:c.KeyID,
  PublicKey:a,WitnessPublicKey:w,AuthorityEpoch:c.AuthorityEpoch,
  BindingSHA256:c.BindingSHA256,MinimumRevision:c.MinimumWitnessRevision},b,nil
}
func Load(path string)(Config,error){
 var c Config
 if err:=canonicalFile(path,MaxConfigBytes,&c);err!=nil{return Config{},err}
 if _,_,err:=c.pin();err!=nil{return Config{},err}
 return c,nil
}
// bindingVerifier is a negative-only adapter for independently signed
// external attestations. It re-verifies the proof on every observation.
type bindingVerifier struct{
 mu sync.Mutex
 cfg Config
 key ed25519.PublicKey
 observedRevision uint64
 observedSignature string
 poisoned bool
}
func(v *bindingVerifier)ReadBinding(ctx context.Context,id string)(string,bool,error){
 if v==nil||ctx==nil||ctx.Err()!=nil||id!=v.cfg.ArchiveID{
  return "",false,ErrUnprovisioned
 }
 v.mu.Lock();defer v.mu.Unlock()
 if v.poisoned{return "",false,ErrUnprovisioned}
 var proof SignedBinding
 if err:=canonicalFile(v.cfg.BindingProofFile,MaxProofBytes,&proof);err!=nil{
  v.poisoned=true;return "",false,ErrUnprovisioned
 }
 h:=proof.Head
 if h.Schema!=BindingSchema||h.ArchiveID!=id||
  h.AuthorityEpoch!=v.cfg.AuthorityEpoch||
  h.BindingSHA256!=v.cfg.BindingSHA256||!h.Bound||
  h.Revision<v.cfg.MinimumBindingRevision||h.Revision<v.observedRevision||
  !lowerHex(proof.SignatureHex,ed25519.SignatureSize*2){
  v.poisoned=true;return "",false,ErrUnprovisioned
 }
 if h.Revision==v.observedRevision&&v.observedSignature!=""&&
  proof.SignatureHex!=v.observedSignature{
  v.poisoned=true;return "",false,ErrUnprovisioned
 }
 sig,_:=hex.DecodeString(proof.SignatureHex)
 body,err:=json.Marshal(h)
 if err!=nil||!ed25519.Verify(v.key,append([]byte(BindingDomain),body...),sig){
  v.poisoned=true;return "",false,ErrUnprovisioned
 }
 if ctx.Err()!=nil{return "",false,ErrUnprovisioned}
 v.observedRevision=h.Revision
 v.observedSignature=proof.SignatureHex
 return h.BindingSHA256,true,nil
}
// checkpointReadOnly checks an externally pinned minimum sequence and
// same-process monotonicity. It cannot mutate the underlying checkpoint.
type checkpointReadOnly struct{
 mu sync.Mutex
 store *fsaanchorstore.Store
 minimum uint64
 observed uint64
 lastHead string
 poisoned bool
}
func(p *checkpointReadOnly)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 if p==nil||ctx==nil||ctx.Err()!=nil{return fsahead.Anchor{},ErrUnprovisioned}
 p.mu.Lock();defer p.mu.Unlock()
 if p.poisoned{return fsahead.Anchor{},ErrUnprovisioned}
 a,err:=p.store.ReadAnchor(ctx)
 if err!=nil||a.Sequence<p.minimum||a.Sequence<p.observed||
  (a.Sequence==p.observed&&p.lastHead!=""&&a.HeadSHA256!=p.lastHead){
  p.poisoned=true;return fsahead.Anchor{},ErrUnprovisioned
 }
 p.observed=a.Sequence;p.lastHead=a.HeadSHA256
 return a,nil
}
func(p *checkpointReadOnly)ConfirmArchiveBinding(ctx context.Context,id string)(bool,error){
 if p==nil||p.poisoned||ctx==nil||ctx.Err()!=nil{return false,ErrUnprovisioned}
 return p.store.ConfirmArchiveBinding(ctx,id)
}
func(p *checkpointReadOnly)CompareAndSwap(context.Context,fsahead.Anchor,fsahead.Anchor)(bool,error){
 return false,ErrUnprovisioned
}
func Server(c Config)(*http.Server,error){
 pin,bindingKey,err:=c.pin();if err!=nil{return nil,err}
 genesis:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:pin.PublicKey,AuthorityEpoch:pin.AuthorityEpoch,
  Sequence:0,HeadSHA256:researchlog.Genesis}
 store,err:=fsaanchorstore.Open(c.CheckpointRoot,genesis)
 if err!=nil{return nil,ErrUnprovisioned}
 reader:=&checkpointReadOnly{store:store,minimum:c.MinimumSequence}
 if _,err:=reader.ReadAnchor(context.Background());err!=nil{return nil,err}
 verifier:=&bindingVerifier{cfg:c,key:bindingKey}
 if _,ok,err:=verifier.ReadBinding(context.Background(),c.ArchiveID);err!=nil||!ok{
  return nil,ErrUnprovisioned
 }
 observed,err:=fsaservice.NewObservedAuthority(reader,verifier)
 if err!=nil{return nil,ErrUnprovisioned}
 handler,err:=fsaservice.AuthorityHandler(pin,c.AllowedClientSPKISHA256,observed)
 if err!=nil{return nil,ErrUnprovisioned}
 tlsConfig,err:=witnesshost.SecureTLS(c.ClientCAFile,c.ServerCertFile,c.ServerKeyFile)
 if err!=nil{return nil,err}
 return &http.Server{Addr:c.ListenAddress,Handler:handler,
  ReadHeaderTimeout:5*time.Second,ReadTimeout:10*time.Second,
  WriteTimeout:10*time.Second,IdleTimeout:15*time.Second,
  MaxHeaderBytes:8192,TLSConfig:tlsConfig},nil
}
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
   _=server.Shutdown(shutdownCtx);cancel()
  case <-stopped:
  }
 }()
 err=server.Serve(tls.NewListener(l,server.TLSConfig))
 close(stopped)
 if err==http.ErrServerClosed&&ctx.Err()!=nil{return nil}
 if err!=nil{return ErrUnprovisioned}
 return nil
}
func Run(ctx context.Context,c Config)error{
 if _,_,err:=c.pin();err!=nil||ctx==nil||ctx.Err()!=nil{return ErrUnprovisioned}
 listener,err:=net.Listen("tcp",c.ListenAddress)
 if err!=nil{return ErrUnprovisioned}
 defer listener.Close()
 return ServeOn(ctx,c,listener)
}
