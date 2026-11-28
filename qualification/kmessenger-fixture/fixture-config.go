package main
import (
 "crypto/rand"
 "encoding/hex"
 "os"
 "github.com/element-hq/dendrite/setup/config"
 "gopkg.in/yaml.v2"
)
func main(){
 var cfg config.Dendrite
 cfg.Defaults(config.DefaultOpts{Generate:true,SingleDatabase:false})
 cfg.Global.ServerName="km-fixture.invalid"
 cfg.Global.PrivateKeyPath="matrix_key.pem"
 cfg.Global.DisableFederation=true
 cfg.Global.TrustedIDServers=[]string{}
 cfg.Global.JetStream.StoragePath="jetstream"
 cfg.Global.JetStream.DisableTLSValidation=false
 cfg.Global.ReportStats.Enabled=false
 cfg.Global.Metrics.Enabled=false
 cfg.Global.Sentry.Enabled=false
 cfg.FederationAPI.KeyPerspectives=config.KeyPerspectives{}
 cfg.FederationAPI.EnableRelays=false
 cfg.FederationAPI.DenyNetworkCIDRs=[]string{"0.0.0.0/0","::/0"}
 cfg.FederationAPI.AllowNetworkCIDRs=[]string{}
 cfg.ClientAPI.RegistrationDisabled=true
 cfg.ClientAPI.GuestsDisabled=true
 var random [32]byte
 if _,err:=rand.Read(random[:]);err!=nil{panic("random")}
 cfg.ClientAPI.RegistrationSharedSecret=hex.EncodeToString(random[:])
 cfg.MediaAPI.BasePath="media"
 cfg.Logging=[]config.LogrusHook{{Type:"std",Level:"warn"}}
 data,err:=yaml.Marshal(&cfg);if err!=nil{panic("config")}
 if err=os.WriteFile("dendrite.yaml",data,0600);err!=nil{panic("write config")}
 if err=os.WriteFile("registration.txt",[]byte(cfg.ClientAPI.RegistrationSharedSecret),0600);err!=nil{panic("write secret")}
}
