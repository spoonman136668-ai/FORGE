package main
import(
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)
func TestInputRejectsUnpinnedOrExtraBytes(t *testing.T){
 var out bytes.Buffer
 if err:=run(nil,&out,1000);err==nil{t.Fatal("missing source accepted")}
 if out.Len()>0{t.Fatal("error leaked report")}
 src:=input{Schema:inputSchema}
 seed:=sha256.Sum256([]byte("TEST ONLY CLI key"))
 public:=ed25519.NewKeyFromSeed(seed[:]).Public().(ed25519.PublicKey)
 src.WitnessPins=[]witnessPin{{Lane:"Wingless",PublicKeyHex:hex.EncodeToString(public)},
  {Lane:"Yggdrasil",PublicKeyHex:hex.EncodeToString(public)}}
 src.ReviewerPins=[]reviewerPin{{Lane:"Wingless",PublicKeyHex:hex.EncodeToString(public)},
  {Lane:"Yggdrasil",PublicKeyHex:hex.EncodeToString(public)}}
 raw,err:=json.Marshal(src);if err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"pins.json")
 if err=os.WriteFile(path,append(raw,[]byte("{}")...),0600);err!=nil{t.Fatal(err)}
 if _,err=loadRequest(path,1000);err==nil{t.Fatal("trailing claim accepted")}
 if err=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 if _,err=loadRequest(path,1000);err!=nil{t.Fatal("syntax-only input should parse",err)}
 if err=run([]string{"--request",path,"--root",filepath.Join(t.TempDir(),"forge-shadow-recovery")},&out,1000);err==nil{
  t.Fatal("unverified signed scientific history accepted")
 }
}
