package originalclaim

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)

// These tests execute a separate OS process, kill it AFTER real durable
// first-use consumption, then start fresh processes to prove no redispatch.
// The arithmetic payload is deliberately a frozen non-scientific fixture.
func processClaim()Claim{
 return Claim{Schema:Schema,Lane:"Wingless",ExperimentID:"r25-bounded-payload",
 FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),
 SourceCommitSHA:strings.Repeat("c",40),OriginalRunID:"r25-local-process-001",
 OwnerEpoch:1,WorkerID:"r25-process",FirstUseConsumed:true}
}
func processKeys()(ed25519.PublicKey,ed25519.PrivateKey){
 seed:=sha256.Sum256([]byte("R25-NONPRODUCTION-TEST-KEY-NO-REAL-SCIENCE"))
 private:=ed25519.NewKeyFromSeed(seed[:])
 return private.Public().(ed25519.PublicKey),private
}
func writeReceipt(root,stage,evidence string)error{
 c:=processClaim()
 _,key:=processKeys()
 receipt:=workerreconcile.Receipt{Schema:workerreconcile.Schema,
 Lane:c.Lane,ExperimentID:c.ExperimentID,FrozenSHA256:c.FrozenSHA256,
 IntentSHA256:c.IntentSHA256,OriginalRunID:c.OriginalRunID,
 WorkerID:c.WorkerID,OwnerEpoch:c.OwnerEpoch,Stage:stage,EvidenceSHA256:evidence}
 raw,err:=json.Marshal(receipt);if err!=nil{return err}
 sig:=ed25519.Sign(key,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...))
 signed:=workerreconcile.Signed{Receipt:receipt,SignatureHex:hex.EncodeToString(sig)}
 b,err:=json.Marshal(signed);if err!=nil{return err}
 return os.WriteFile(filepath.Join(root,stage+".json"),append(b,'\n'),0600)
}
func processReadReceipt(root,stage string)(*workerreconcile.Signed,error){
 b,err:=os.ReadFile(filepath.Join(root,stage+".json"));if err!=nil{return nil,err}
 var s workerreconcile.Signed
 if err=json.Unmarshal(b,&s);err!=nil{return nil,err}
 return &s,nil
}
func processVerify(root string,expectTerminal bool)error{
 c:=processClaim()
 pub,_:=processKeys()
 expected:=workerreconcile.Expected{Lane:c.Lane,ExperimentID:c.ExperimentID,
 FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,
 OriginalRunID:c.OriginalRunID,WorkerID:c.WorkerID,OwnerEpoch:c.OwnerEpoch,WorkerPublicKey:pub}
 started,err:=processReadReceipt(root,"STARTED")
 if err!=nil{return err}
 var terminal *workerreconcile.Signed
 if expectTerminal{
  terminal,err=processReadReceipt(root,"TERMINAL")
  if err!=nil{return err}
 }
 outcome,err:=Assess(root,c,expected,started,terminal)
 if err!=nil{return err}
 if outcome.RedispatchAuthorized||outcome.IndependentResultAccepted{return errors.New("premature science promotion")}
 if expectTerminal{
  if outcome.Disposition!=workerreconcile.Terminal{return errors.New("terminal custody unverified")}
  raw,err:=os.ReadFile(filepath.Join(root,"bounded-payload.txt"))
  if err!=nil{return err}
  // Independently recompute the entire fixed input and expected output.
  total:=0
  for i:=1;i<=1000;i++{total+=i*i}
  expectedPayload:=fmt.Sprintf("BOUNDED_NONSCIENTIFIC_RESULT=%d\n",total)
  if string(raw)!=expectedPayload{return errors.New("independent payload mismatch")}
  h:=sha256.Sum256(raw)
  if terminal.Receipt.EvidenceSHA256!=hex.EncodeToString(h[:]){
   return errors.New("worker evidence commitment drift")
  }
 }else if outcome.Disposition!=workerreconcile.Started{
  return errors.New("interrupted start not quarantined")
 }
 return nil
}
func TestR25WorkerChild(t *testing.T){
 mode:=os.Getenv("FORGE_R25_CHILD")
 if mode==""{return}
 root:=os.Getenv("FORGE_R25_ROOT")
 if !filepath.IsAbs(root){os.Exit(40)}
 c:=processClaim()
 switch mode {
 case "interrupt":
  if err:=Consume(root,c);err!=nil{os.Exit(41)}
  if err:=writeReceipt(root,"STARTED","");err!=nil{os.Exit(42)}
  if err:=os.WriteFile(filepath.Join(root,"start-observed"),[]byte("STARTED\n"),0600);err!=nil{os.Exit(43)}
  // Intentionally hang here until the parent kills the REAL OS process.
  time.Sleep(30*time.Second)
  os.Exit(44)
 case "duplicate":
  if err:=Consume(root,c);err==nil{os.Exit(45)}
  if _,err:=os.Stat(filepath.Join(root,"TERMINAL.json"));err==nil{os.Exit(46)}
  return
 case "inspect-interrupted":
  if err:=processVerify(root,false);err!=nil{os.Exit(47)}
  return
 case "complete":
  if err:=Consume(root,c);err!=nil{os.Exit(48)}
  if err:=writeReceipt(root,"STARTED","");err!=nil{os.Exit(49)}
  total:=0
  for i:=1;i<=1000;i++{total+=i*i}
  raw:=[]byte(fmt.Sprintf("BOUNDED_NONSCIENTIFIC_RESULT=%d\n",total))
  if err:=os.WriteFile(filepath.Join(root,"bounded-payload.txt"),raw,0600);err!=nil{os.Exit(50)}
  sha:=sha256.Sum256(raw)
  if err:=writeReceipt(root,"TERMINAL",hex.EncodeToString(sha[:]));err!=nil{os.Exit(51)}
  return
 case "inspect-complete":
  if err:=processVerify(root,true);err!=nil{os.Exit(52)}
  return
 default:os.Exit(53)
 }
}
func processRun(t *testing.T,root,mode string)error{
 t.Helper()
 cmd:=exec.Command(os.Args[0],"-test.run=^TestR25WorkerChild$")
 cmd.Env=append(os.Environ(),"FORGE_R25_CHILD="+mode,"FORGE_R25_ROOT="+root)
 out,err:=cmd.CombinedOutput()
 if err!=nil{t.Logf("%s: %v %s",mode,err,string(out))}
 return err
}
func TestR25ActualProcessKilledAndRecoveredWithoutDuplicateOriginal(t *testing.T){
 root:=t.TempDir()
 cmd:=exec.Command(os.Args[0],"-test.run=^TestR25WorkerChild$")
 cmd.Env=append(os.Environ(),"FORGE_R25_CHILD=interrupt","FORGE_R25_ROOT="+root)
 if err:=cmd.Start();err!=nil{t.Fatal(err)}
 started:=false
 for i:=0;i<100;i++{
  if _,err:=os.Stat(filepath.Join(root,"start-observed"));err==nil{started=true;break}
  time.Sleep(20*time.Millisecond)
 }
 if !started{
  _=cmd.Process.Kill();_ =cmd.Wait()
  t.Fatal("worker never durably recorded STARTED")
 }
 if err:=cmd.Process.Kill();err!=nil{t.Fatal(err)}
 if err:=cmd.Wait();err==nil{t.Fatal("interrupted worker exited successfully")}
 if err:=processRun(t,root,"inspect-interrupted");err!=nil{t.Fatal("independent process refused valid start custody",err)}
 if err:=processRun(t,root,"duplicate");err!=nil{t.Fatal("worker restart attempted duplicate original",err)}
 if _,err:=os.Stat(filepath.Join(root,"TERMINAL.json"));!os.IsNotExist(err){
  t.Fatal("interrupted original manufactured a terminal result")
 }
}
func TestR25BoundedWorkloadIndependentlyRecomputedNoAutomaticAcceptance(t *testing.T){
 root:=t.TempDir()
 if err:=processRun(t,root,"complete");err!=nil{t.Fatal(err)}
 if err:=processRun(t,root,"inspect-complete");err!=nil{t.Fatal("independent process rejected bounded computation",err)}
 if err:=processRun(t,root,"duplicate");err==nil{
  // The duplicate mode refuses to claim but intentionally rejects terminal
  // when the separate completed original is already terminal.
  t.Fatal("duplicate process accidentally passed while terminal existed")
 }
 if err:=Consume(root,processClaim());err==nil{t.Fatal("completed original was reentered")}
}
