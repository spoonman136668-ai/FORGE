// Package fsaprobe verifies two independently pinned FSA HTTPS roles from
// outside their processes. It is observational and grants no science authority.
package fsaprobe

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/url"
 "os"
 "path/filepath"
 "runtime"

 "github.com/spoonman136668-ai/forge/fsaremote"
)
const Schema="forge.fsa.external-trust-probe.v1"
const Mode="READONLY_DUAL_FSA_TRUST_OBSERVED_NOT_DEPLOYMENT_ATTESTED"
var ErrBlocked=errors.New("FORGE_FSA_EXTERNAL_TRUST_PROBE_BLOCKED")
type PeerConfig struct {
 BaseURL string `json:"base_url"`
 ClientCAFile string `json:"client_ca_file"`
 ServerSPKISHA256 string `json:"server_spki_sha256"`
}
type Config struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityPublicKeyHex string `json:"authority_public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 MinimumWitnessRevision uint64 `json:"minimum_witness_revision"`
 MinimumCheckpointSequence uint64 `json:"minimum_checkpoint_sequence"`
 ClientCertFile string `json:"client_cert_file"`
 ClientKeyFile string `json:"client_key_file"`
 Authority PeerConfig `json:"authority"`
 Witness PeerConfig `json:"witness"`
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
 BindingVerified bool `json:"binding_verified"`
 DeploymentIndependenceVerified bool `json:"deployment_independence_verified"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ScienceActivated bool `json:"science_activated"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,ch:=range s{if !(ch>='0'&&ch<='9'||ch>='a'&&ch<='f'){return false}}
 return true
}
func trustedFile(path string,secret bool)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrBlocked}
 clean:=filepath.Clean(path)
 for p:=clean;;{
  stat,err:=os.Lstat(p)
  if err!=nil||stat.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return nil,ErrBlocked}
  if p==clean{
   if !stat.Mode().IsRegular()||stat.Size()<=0||stat.Size()>1<<20{return nil,ErrBlocked}
   if secret&&runtime.GOOS!="windows"&&stat.Mode().Perm()&0077!=0{return nil,ErrBlocked}
  }else if !stat.IsDir(){return nil,ErrBlocked}
  next:=filepath.Dir(p);if next==p{break};p=next
 }
 raw,err:=os.ReadFile(clean)
 if err!=nil||len(raw)==0||len(raw)>1<<20{return nil,ErrBlocked}
 return raw,nil
}
func (c Config)pin()(fsaremote.Pin,error){
 if c.Schema!=Schema||!validHex(c.ArchiveID,64)||
  !validHex(c.AuthorityPublicKeyHex,64)||!validHex(c.BindingSHA256,64)||
  !validHex(c.WitnessPublicKeyHex,64)||c.AuthorityEpoch==0||
  c.MinimumWitnessRevision==0||c.MinimumCheckpointSequence>100000{
  return fsaremote.Pin{},ErrBlocked
 }
 ap,_:=hex.DecodeString(c.AuthorityPublicKeyHex)
 wp,_:=hex.DecodeString(c.WitnessPublicKeyHex)
 if len(ap)!=ed25519.PublicKeySize||len(wp)!=ed25519.PublicKeySize||
  bytes.Equal(ap,wp){return fsaremote.Pin{},ErrBlocked}
 return fsaremote.Pin{ArchiveID:c.ArchiveID,KeyID:c.KeyID,
  PublicKey:ap,AuthorityEpoch:c.AuthorityEpoch,BindingSHA256:c.BindingSHA256,
  WitnessPublicKey:wp,MinimumRevision:c.MinimumWitnessRevision},nil
}
func validatePeer(p PeerConfig)bool{
 if !validHex(p.ServerSPKISHA256,64)||p.ClientCAFile==""||p.BaseURL==""{return false}
 u,err:=url.Parse(p.BaseURL)
 return err==nil&&u.Scheme=="https"&&u.Hostname()!=""&&
  u.User==nil&&(u.Path==""||u.Path=="/")&&u.RawQuery==""&&u.Fragment==""
}
func(c Config)check()error{
 if _,err:=c.pin();err!=nil{return err}
 if !validatePeer(c.Authority)||!validatePeer(c.Witness)||
  c.Authority.BaseURL==c.Witness.BaseURL||
  c.Authority.ServerSPKISHA256==c.Witness.ServerSPKISHA256{
  return ErrBlocked
 }
 return nil
}
func Load(path string)(Config,error){
 var c Config
 raw,err:=trustedFile(path,false)
 if err!=nil||len(raw)>8192{return Config{},ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if d.Decode(&c)!=nil||d.Decode(new(any))!=io.EOF{return Config{},ErrBlocked}
 canonical,err:=json.Marshal(c)
 if err!=nil||!bytes.Equal(bytes.TrimSuffix(raw,[]byte("\n")),canonical)||c.check()!=nil{
  return Config{},ErrBlocked
 }
 return c,nil
}
func(c Config)client()(tls.Certificate,error){
 cert,err:=trustedFile(c.ClientCertFile,false)
 if err!=nil{return tls.Certificate{},err}
 key,err:=trustedFile(c.ClientKeyFile,true)
 if err!=nil{return tls.Certificate{},err}
 pair,err:=tls.X509KeyPair(cert,key)
 if err!=nil{return tls.Certificate{},ErrBlocked}
 return pair,nil
}
func(c Config)peer(p PeerConfig,cert tls.Certificate)(fsaremote.Peer,error){
 ca,err:=trustedFile(p.ClientCAFile,false)
 if err!=nil{return fsaremote.Peer{},err}
 roots:=x509.NewCertPool()
 if !roots.AppendCertsFromPEM(ca){return fsaremote.Peer{},ErrBlocked}
 return fsaremote.Peer{BaseURL:p.BaseURL,Roots:roots,
  Certificate:cert,ServerSPKISHA256:p.ServerSPKISHA256},nil
}
// Check validates an authenticated authority head against an independently
// signed witness and independently signed archive-binding commitment. This
// says NOTHING about physical separation, signer custody or live cutover.
func Check(ctx context.Context,c Config)(Report,error){
 var empty Report
 if ctx==nil||ctx.Err()!=nil||c.check()!=nil{return empty,ErrBlocked}
 pin,err:=c.pin();if err!=nil{return empty,ErrBlocked}
 cert,err:=c.client();if err!=nil{return empty,ErrBlocked}
 primary,err:=c.peer(c.Authority,cert);if err!=nil{return empty,ErrBlocked}
 witness,err:=c.peer(c.Witness,cert);if err!=nil{return empty,ErrBlocked}
 remote,err:=fsaremote.NewClient(primary,witness,pin)
 if err!=nil{return empty,ErrBlocked}
 first,err:=remote.ReadAnchor(ctx)
 if err!=nil||first.Sequence<c.MinimumCheckpointSequence{return empty,ErrBlocked}
 bound,err:=remote.ConfirmArchiveBinding(ctx,pin.ArchiveID)
 if err!=nil||!bound||ctx.Err()!=nil{return empty,ErrBlocked}
 second,err:=remote.ReadAnchor(ctx)
 if err!=nil||first.Sequence!=second.Sequence||first.HeadSHA256!=second.HeadSHA256||
  first.AuthorityEpoch!=second.AuthorityEpoch||ctx.Err()!=nil{return empty,ErrBlocked}
 return Report{Schema:Schema,Mode:Mode,ArchiveID:pin.ArchiveID,
  AuthorityEpoch:first.AuthorityEpoch,Sequence:first.Sequence,
  HeadSHA256:first.HeadSHA256,BindingVerified:true,
  DeploymentIndependenceVerified:false,ExecutionAuthorized:false,
  ScienceActivated:false},nil
}
