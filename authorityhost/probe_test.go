package authorityhost

import (
 "context"
 "crypto/x509"
 "encoding/json"
 "encoding/pem"
 "net"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaprobe"
 "github.com/spoonman136668-ai/forge/witnesshost"
)
func TestExternalProbeChecksBothRealTLSHostsWithoutExecutionAuthority(t *testing.T){
 f:=setup(t)
 aListener,err:=net.Listen("tcp","127.0.0.1:0");if err!=nil{t.Fatal(err)}
 wListener,err:=net.Listen("tcp","127.0.0.1:0");if err!=nil{t.Fatal(err)}
 f.cfg.ListenAddress=aListener.Addr().String()
 f.witness.ListenAddress=wListener.Addr().String()
 ctx,cancel:=context.WithCancel(context.Background())
 done:=make(chan error,2)
 go func(){done<-ServeOn(ctx,f.cfg,aListener)}()
 go func(){done<-witnesshost.ServeOn(ctx,f.witness,wListener)}()
 defer func(){cancel();for i:=0;i<2;i++{if err:=<-done;err!=nil{t.Fatal(err)}}}()
 root:=t.TempDir()
 certPath:=filepath.Join(root,"client.pem")
 keyPath:=filepath.Join(root,"client-key.pem")
 write(t,certPath,pem.EncodeToMemory(&pem.Block{
  Type:"CERTIFICATE",Bytes:f.client.Certificate[0]}),0644)
 der,err:=x509.MarshalPKCS8PrivateKey(f.client.PrivateKey);if err!=nil{t.Fatal(err)}
 write(t,keyPath,pem.EncodeToMemory(&pem.Block{Type:"PRIVATE KEY",Bytes:der}),0600)
 probe:=fsaprobe.Config{Schema:fsaprobe.Schema,
  ArchiveID:f.pin.ArchiveID,KeyID:f.pin.KeyID,
  AuthorityPublicKeyHex:f.cfg.AuthorityPublicKeyHex,
  AuthorityEpoch:f.pin.AuthorityEpoch,BindingSHA256:f.pin.BindingSHA256,
  WitnessPublicKeyHex:f.cfg.WitnessPublicKeyHex,
  MinimumWitnessRevision:1,MinimumCheckpointSequence:0,
  ClientCertFile:certPath,ClientKeyFile:keyPath,
  Authority:fsaprobe.PeerConfig{BaseURL:"https://"+aListener.Addr().String(),
   ClientCAFile:f.cfg.ClientCAFile,ServerSPKISHA256:f.serverAuthoritySPKI},
  Witness:fsaprobe.PeerConfig{BaseURL:"https://"+wListener.Addr().String(),
   ClientCAFile:f.cfg.ClientCAFile,ServerSPKISHA256:f.serverWitnessSPKI}}
 check:=func(p fsaprobe.Config)(fsaprobe.Report,error){return fsaprobe.Check(ctx,p)}
 report,err:=check(probe)
 if err!=nil||!report.BindingVerified||report.ExecutionAuthorized||
  report.DeploymentIndependenceVerified||report.ScienceActivated||report.Sequence!=0{
  t.Fatal("probe falsely claimed authority or refused verified trust",report,err)
 }
 probe.MinimumCheckpointSequence=1
 if _,err:=check(probe);err==nil{t.Fatal("stale trusted checkpoint passed externally pinned floor")}
 probe.MinimumCheckpointSequence=0
 wrong:=probe
 wrong.Witness.ServerSPKISHA256=strings.Repeat("f",64)
 if _,err:=check(wrong);err==nil{t.Fatal("untrusted witness TLS SPKI passed")}
 wrong=probe
 wrong.Witness.BaseURL=wrong.Authority.BaseURL
 if _,err:=check(wrong);err==nil{t.Fatal("same FSA host accepted for both roles")}
 next:=f.genesis;next.Sequence=1;next.HeadSHA256=strings.Repeat("c",64)
 if ok,err:=f.checkpoint.CompareAndSwap(ctx,f.genesis,next);err!=nil||!ok{t.Fatal(err)}
 if _,err:=check(probe);err==nil{t.Fatal("checkpoint ahead of witness accepted")}
 if err:=f.witnessStore.Append(ctx,externalWitness(t,f.pin,f.witnessKey,next,2));err!=nil{t.Fatal(err)}
 probe.MinimumWitnessRevision=2
 probe.MinimumCheckpointSequence=1
 if got,err:=check(probe);err!=nil||got.Sequence!=1{t.Fatal("dual signed recovery denied",got,err)}
 if err:=os.WriteFile(f.cfg.BindingProofFile,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=check(probe);err==nil{t.Fatal("external physical binding forgery accepted")}
 // Empty or malformed config is never interpreted as permissive defaults.
 configPath:=filepath.Join(root,"probe.json")
 raw,err:=json.Marshal(probe);if err!=nil{t.Fatal(err)}
 write(t,configPath,append(raw,'\n'),0600)
 if loaded,err:=fsaprobe.Load(configPath);err!=nil||loaded.Schema!=fsaprobe.Schema{
  t.Fatal("valid independent probe config refused",err)
 }
}
