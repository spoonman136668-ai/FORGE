package fsaservice

import (
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsawitnessstore"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func TestDurableWitnessRestartThroughIndependentMutualTLSServers(t *testing.T){
 primary,_:=testKey(t)
 witnessPub,witnessKey:=testKey(t)
 pin:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_DURABLE_TEST",
  PublicKey:primary,AuthorityEpoch:31,
  BindingSHA256:strings.Repeat("b",64),WitnessPublicKey:witnessPub,MinimumRevision:5}
 anchor:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,PublicKey:pin.PublicKey,
  AuthorityEpoch:pin.AuthorityEpoch,Sequence:0,HeadSHA256:researchlog.Genesis}
 sign:=func(rev uint64)fsaremote.SignedWitness{
  h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,
   Domain:fsaremote.WitnessDomain,ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
   AuthorityEpoch:pin.AuthorityEpoch,BindingSHA256:pin.BindingSHA256,
   Sequence:0,HeadSHA256:researchlog.Genesis,Revision:rev}
  raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
  signature:=ed25519.Sign(witnessKey,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
  return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(signature)}
 }
 root:=filepath.Join(t.TempDir(),fsawitnessstore.FolderName)
 witnessStore,err:=fsawitnessstore.Provision(root,pin,sign(5))
 if err!=nil{t.Fatal(err)}
 ca,caKey,roots:=testCA(t)
 clientCert,clientSPKI:=certFor(t,ca,caKey,true)
 authorityCert,authoritySPKI:=certFor(t,ca,caKey,false)
 witnessCert,witnessSPKI:=certFor(t,ca,caKey,false)
 aStore:=&staticAuthority{anchor:anchor,digest:pin.BindingSHA256,active:true}
 ah,err:=AuthorityHandler(pin,clientSPKI,aStore);if err!=nil{t.Fatal(err)}
 ws,err:=WitnessHandler(pin,clientSPKI,witnessStore);if err!=nil{t.Fatal(err)}
 aServer:=testService(t,ah,authorityCert,roots)
 wServer:=testService(t,ws,witnessCert,roots)
 makeClient:=func(p fsaremote.Pin)*fsaremote.Client{
  t.Helper()
  client,err:=fsaremote.NewClient(
   fsaremote.Peer{BaseURL:aServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:authoritySPKI},
   fsaremote.Peer{BaseURL:wServer.URL,Roots:roots,Certificate:clientCert,ServerSPKISHA256:witnessSPKI},p)
  if err!=nil{t.Fatal(err)}
  return client
 }
 first:=makeClient(pin)
 if _,err:=first.ReadAnchor(context.Background());err!=nil{t.Fatal("initial signed witness denied",err)}
 if err:=witnessStore.Append(context.Background(),sign(6));err!=nil{t.Fatal(err)}
 if _,err:=first.ReadAnchor(context.Background());err!=nil{t.Fatal("advanced signed revision denied",err)}
 restartPin:=pin
 restartPin.MinimumRevision=6
 restarted,err:=fsawitnessstore.Open(root,restartPin)
 if err!=nil{t.Fatal("durable witness reopen",err)}
 got,err:=restarted.ReadWitness(context.Background(),pin.ArchiveID)
 if err!=nil||got.Head.Revision!=6{t.Fatal("new signed floor lost on restart",got,err)}
 if _,err:=makeClient(restartPin).ReadAnchor(context.Background());err!=nil{
  t.Fatal("remote TLS client rejected independently persisted witness",err)
 }
 // Simulate a filesystem rollback: the independent pinned high-water floor
 // prevents a restarted client from accepting the older VALID signature.
 if err:=os.Remove(filepath.Join(root,"receipts","00000001.json"));err!=nil{t.Fatal(err)}
 if _,err:=makeClient(restartPin).ReadAnchor(context.Background());err==nil{
  t.Fatal("stale signed witness admitted after local rollback")
 }
}
