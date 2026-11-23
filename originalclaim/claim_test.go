package originalclaim

import(
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func fixture()Claim{
 return Claim{Schema:Schema,Lane:"Wingless",ExperimentID:"r24-original-01",FrozenSHA256:strings.Repeat("a",64),
 IntentSHA256:strings.Repeat("b",64),SourceCommitSHA:strings.Repeat("c",40),
 OriginalRunID:"r24-unique-first-use",OwnerEpoch:1,WorkerID:"isolated-01",FirstUseConsumed:true}
}
func TestDurableClaimOnlyOneWinnerEvenAcrossConcurrentAttempts(t *testing.T){
 root:=t.TempDir();c:=fixture()
 var wait sync.WaitGroup
 hits:=make(chan bool,64)
 for i:=0;i<64;i++{wait.Add(1);go func(){defer wait.Done();hits<-Consume(root,c)==nil}()}
 wait.Wait();close(hits)
 successes:=0;for v:=range hits{if v{successes++}}
 if successes!=1{t.Fatalf("duplicate original admission: %d",successes)}
 if _,err:=Read(root,c);err!=nil{t.Fatal(err)}
 if err:=Consume(root,c);err==nil{t.Fatal("restart granted duplicate original")}
}
func TestTamperMismatchAndUncertainClaimNeverAuthorizeReplay(t *testing.T){
 root:=t.TempDir();c:=fixture()
 if err:=Consume(root,c);err!=nil{t.Fatal(err)}
 altered:=c;altered.IntentSHA256=strings.Repeat("f",64)
 if _,err:=Read(root,altered);err==nil{t.Fatal("identity drift accepted")}
 if err:=Consume(root,altered);err==nil{t.Fatal("changed claim reentered original")}
 p:=path(root,c)
 if err:=os.WriteFile(p,[]byte("{}\n"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Read(root,c);err==nil{t.Fatal("corrupted first-use custody accepted")}
 if err:=Consume(root,c);err==nil{t.Fatal("corrupted claim allowed replay")}
}
func TestMissingOrRelativeDirectoryCannotClaimOrGrantStart(t *testing.T){
 c:=fixture()
 if err:=Consume(filepath.Join(t.TempDir(),"absent"),c);err==nil{t.Fatal("created untrusted root")}
 relativeRoot:=t.TempDir()
 cwd,err:=os.Getwd();if err!=nil{t.Fatal(err)}
 relative,err:=filepath.Rel(cwd,relativeRoot)
 if err==nil&&filepath.IsAbs(relative)==false {
  if err:=Consume(relative,c);err==nil{t.Fatal("existing relative custody directory was accepted")}
 }
 c.FirstUseConsumed=false
 if err:=Consume(t.TempDir(),c);err==nil{t.Fatal("unconsumed claim admitted")}
}
func TestSignedOriginalReceiptsRequireIndependentReviewAndNeverRedispatch(t *testing.T){
 root:=t.TempDir();c:=fixture()
 if err:=Consume(root,c);err!=nil{t.Fatal(err)}
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 expected:=workerreconcile.Expected{Lane:c.Lane,ExperimentID:c.ExperimentID,
 FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,OriginalRunID:c.OriginalRunID,
 OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,WorkerPublicKey:pub}
 assessment,err:=Assess(root,c,expected,nil,nil)
 if err!=nil||assessment.Disposition!=workerreconcile.Unknown||
 assessment.RedispatchAuthorized||assessment.IndependentResultAccepted{t.Fatalf("unknown original was eligible: %+v %v",assessment,err)}
 signed:=func(stage,evidence string)*workerreconcile.Signed{
  receipt:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:c.Lane,ExperimentID:c.ExperimentID,
  FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,OriginalRunID:c.OriginalRunID,
  OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,Stage:stage,EvidenceSHA256:evidence}
  // The signature domain is verified by workerreconcile.
  raw,_:=json.Marshal(receipt)
  sig:=ed25519.Sign(priv,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...))
  return &workerreconcile.Signed{Receipt:receipt,SignatureHex:hex.EncodeToString(sig)}
 }
 start:=signed("STARTED","")
 assessment,err=Assess(root,c,expected,start,nil)
 if err!=nil||assessment.Disposition!=workerreconcile.Started||
 assessment.RedispatchAuthorized||assessment.IndependentResultAccepted{t.Fatalf("started duplicate accepted: %+v %v",assessment,err)}
 end:=signed("TERMINAL",strings.Repeat("d",64))
 assessment,err=Assess(root,c,expected,start,end)
 if err!=nil||assessment.Disposition!=workerreconcile.Terminal||
 assessment.IndependentResultAccepted||assessment.RedispatchAuthorized{
  t.Fatalf("terminal bypassed review: %+v %v",assessment,err)
 }
 end.SignatureHex=strings.Repeat("0",128)
 if _,err=Assess(root,c,expected,start,end);err==nil{t.Fatal("forged terminal admitted")}
}
