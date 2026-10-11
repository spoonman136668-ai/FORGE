// fsa-probe performs read-only TLS-pinned observations of existing FORGE
// authority and witness services. It never sends a CAS or configures a server.
package main

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "time"

 "github.com/spoonman136668-ai/forge/fsaremote"
)

const configSchema = "forge.fsa.remote-readonly-probe-config.v1"
const maxConfigBytes = 16384

type peerConfig struct {
 URL string `json:"url"`
 TrustedCAFile string `json:"trusted_ca_file"`
 ClientCertFile string `json:"client_cert_file"`
 ClientKeyFile string `json:"client_key_file"`
 ServerSPKISHA256 string `json:"server_spki_sha256"`
}
type config struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 AuthorityKeyHex string `json:"authority_public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 WitnessKeyHex string `json:"witness_public_key_hex"`
 MinimumRevision uint64 `json:"minimum_revision"`
 Authority peerConfig `json:"authority"`
 Witness peerConfig `json:"witness"`
}
var errConfig=errors.New("FORGE_FSA_PROBE_INDEPENDENT_PIN_OR_CREDENTIAL_CONFIGURATION_REQUIRED")
func lowerHex(s string, size int)bool {
 if len(s)!=size{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func decode(raw []byte)(config,error) {
 var out config
 if len(raw)==0||len(raw)>maxConfigBytes{return out,errConfig}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(&out);err!=nil{return config{},errConfig}
 var extra any
 if err:=dec.Decode(&extra);err!=io.EOF{return config{},errConfig}
 if out.Schema!=configSchema||!lowerHex(out.ArchiveID,64)||
  !lowerHex(out.BindingSHA256,64)||
  !lowerHex(out.AuthorityKeyHex,64)||
  !lowerHex(out.WitnessKeyHex,64)||out.AuthorityKeyHex==out.WitnessKeyHex||
  out.AuthorityEpoch==0||out.MinimumRevision==0||
  len(out.KeyID)<3||len(out.KeyID)>80{return config{},errConfig}
 for _,c:=range out.KeyID {
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'){
   return config{},errConfig
  }
 }
 if out.Authority.URL==out.Witness.URL ||
  !lowerHex(out.Authority.ServerSPKISHA256,64)||
  !lowerHex(out.Witness.ServerSPKISHA256,64)||
  out.Authority.ServerSPKISHA256==out.Witness.ServerSPKISHA256{
  return config{},errConfig
 }
 return out,nil
}
func readRegular(path string, max int)([]byte,error) {
 if path==""||!filepath.IsAbs(path){return nil,errConfig}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<=0||info.Size()>int64(max){
  return nil,errConfig
 }
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)==0||len(raw)>max{return nil,errConfig}
 return raw,nil
}
func peer(p peerConfig)(fsaremote.Peer,error) {
 fail:=func()(fsaremote.Peer,error){return fsaremote.Peer{},errConfig}
 ca,err:=readRegular(p.TrustedCAFile,65536)
 if err!=nil{return fail()}
 roots:=x509.NewCertPool()
 if !roots.AppendCertsFromPEM(ca)||len(roots.Subjects())==0{return fail()}
 // No key bytes or file paths ever appear in output.
 if _,err=readRegular(p.ClientCertFile,65536);err!=nil{return fail()}
 if _,err=readRegular(p.ClientKeyFile,65536);err!=nil{return fail()}
 cert,err:=tls.LoadX509KeyPair(p.ClientCertFile,p.ClientKeyFile)
 if err!=nil{return fail()}
 return fsaremote.Peer{BaseURL:p.URL,Roots:roots,Certificate:cert,
  ServerSPKISHA256:p.ServerSPKISHA256},nil
}
func create(c config)(*fsaremote.Client,error) {
 authority,err:=peer(c.Authority)
 if err!=nil{return nil,errConfig}
 witness,err:=peer(c.Witness)
 if err!=nil{return nil,errConfig}
 a,err:=hex.DecodeString(c.AuthorityKeyHex)
 if err!=nil{return nil,errConfig}
 w,err:=hex.DecodeString(c.WitnessKeyHex)
 if err!=nil{return nil,errConfig}
 pin:=fsaremote.Pin{ArchiveID:c.ArchiveID,KeyID:c.KeyID,
  PublicKey:ed25519.PublicKey(a),AuthorityEpoch:c.AuthorityEpoch,
  BindingSHA256:c.BindingSHA256,
  WitnessPublicKey:ed25519.PublicKey(w),
  MinimumRevision:c.MinimumRevision}
 client,err:=fsaremote.NewClient(authority,witness,pin)
 if err!=nil{return nil,errConfig}
 return client,nil
}
func run(path string)(fsaremote.ProbeObservation,error) {
 raw,err:=readRegular(path,maxConfigBytes)
 if err!=nil{return fsaremote.ProbeObservation{},errConfig}
 cfg,err:=decode(raw)
 if err!=nil{return fsaremote.ProbeObservation{},errConfig}
 client,err:=create(cfg)
 if err!=nil{return fsaremote.ProbeObservation{},errConfig}
 ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second)
 defer cancel()
 return client.Probe(ctx)
}
func main() {
 var path string
 flag.StringVar(&path,"config","","absolute path to separately pinned local probe configuration")
 flag.Parse()
 if flag.NArg()!=0 {
  fmt.Fprintln(os.Stderr,"FORGE_FSA_PROBE_CONFIG_REQUIRED")
  os.Exit(2)
 }
 observation,err:=run(path)
 if err!=nil {
  // Do not expose the original error because TLS failures may contain
  // operator-private paths and peer details.
  fmt.Fprintln(os.Stderr,"FORGE_FSA_REMOTE_READONLY_PROBE_BLOCKED")
  os.Exit(2)
 }
 output,err:=json.Marshal(observation)
 if err!=nil {
  fmt.Fprintln(os.Stderr,"FORGE_FSA_PROBE_ENCODING_FAILED")
  os.Exit(2)
 }
 fmt.Println(string(output))
}
