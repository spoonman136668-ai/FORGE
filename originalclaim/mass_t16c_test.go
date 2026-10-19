package originalclaim
import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "os"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func TestMassT16CDurableFirstUseCannotBeClaimedTwice(t *testing.T){
 root:=t.TempDir()
 c:=fixture();c.Lane="MassResearch";c.ExperimentID="mass-t16c-dry-fixture"
 c.OriginalRunID="mass-t16c-unique"
 if err:=Consume(root,c);err!=nil{t.Fatal(err)}
 if _,err:=Read(root,c);err!=nil{t.Fatal(err)}
 if err:=Consume(root,c);err==nil{t.Fatal("mass source first-use replay admitted")}
 changed:=c;changed.SourceCommitSHA=strings.Repeat("d",40)
 if err:=Consume(root,changed);err==nil{t.Fatal("source drift allowed duplicate claim")}
 if _,err:=Read(root,changed);err==nil{t.Fatal("source drift in Mass custody")}
}
func TestMassT16CNoWorkerRestartOrScienceAdmission(t *testing.T){
 root:=t.TempDir();c:=fixture();c.Lane="MassResearch"
 c.ExperimentID="mass-t16c-synthetic-unique"
 c.OriginalRunID="mass-t16c-fake-00001"
 if err:=Consume(root,c);err!=nil{t.Fatal(err)}
 public,private,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 e:=workerreconcile.Expected{Lane:c.Lane,ExperimentID:c.ExperimentID,
  FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,
  OriginalRunID:c.OriginalRunID,OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,
  WorkerPublicKey:public}
 result,err:=Assess(root,c,e,nil,nil)
 if err!=nil||result.Disposition!=workerreconcile.Unknown||result.RedispatchAuthorized||
  result.IndependentResultAccepted {t.Fatalf("unsafe absent worker: %+v %v",result,err)}
 gen:=func(stage,evidence string)*workerreconcile.Signed{
  r:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:c.Lane,
   ExperimentID:c.ExperimentID,FrozenSHA256:c.FrozenSHA256,
   IntentSHA256:c.IntentSHA256,OriginalRunID:c.OriginalRunID,
   OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,Stage:stage,EvidenceSHA256:evidence}
  b,_:=json.Marshal(r)
  sig:=ed25519.Sign(private,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),b...))
  return &workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(sig)}
 }
 start:=gen("STARTED","");end:=gen("TERMINAL",strings.Repeat("a",64))
 got,err:=Assess(root,c,e,start,end)
 if err!=nil||got.Disposition!=workerreconcile.Terminal||got.RedispatchAuthorized||
  got.IndependentResultAccepted {t.Fatalf("Mass terminal bypassed science review: %+v %v",got,err)}
 end.SignatureHex=strings.Repeat("0",128)
 if _,err:=Assess(root,c,e,start,end);err==nil{t.Fatal("forged Mass worker receipt accepted")}
}
func TestMassT16CTamperCannotResetHighWaterClaim(t *testing.T){
 root:=t.TempDir();c:=fixture();c.Lane="MassResearch"
 c.ExperimentID="mass-claim-cannot-reset"
 if err:=Consume(root,c);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(path(root,c),[]byte("{}\n"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Read(root,c);err==nil{t.Fatal("tampered Mass claim accepted")}
 if err:=Consume(root,c);err==nil{t.Fatal("tampered Mass claim permitted original replay")}
}
