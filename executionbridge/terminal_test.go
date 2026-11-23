package executionbridge

import(
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
type terminalReceipts struct{
 signed *workerreconcile.Signed
}
func(x terminalReceipts)LoadStarted(context.Context,string)(*workerreconcile.Signed,error){return nil,nil}
func(x terminalReceipts)LoadTerminal(context.Context,string)(*workerreconcile.Signed,error){return x.signed,nil}
type scienceWitness bool
func(w scienceWitness)VerifyTerminal(context.Context,TerminalEvidence)(bool,error){return bool(w),nil}
func TestTerminalReceiptIsNotScientificAcceptance(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST_ONLY_TERMINAL_WITNESS"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 e:=workerreconcile.Expected{Lane:"Wingless",ExperimentID:"original_1",OriginalRunID:"original_1",FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),OwnerEpoch:3,WorkerID:"old_worker",WorkerPublicKey:key.Public().(ed25519.PublicKey)}
 r:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,OriginalRunID:e.OriginalRunID,FrozenSHA256:e.FrozenSHA256,IntentSHA256:e.IntentSHA256,OwnerEpoch:e.OwnerEpoch,WorkerID:e.WorkerID,Stage:"TERMINAL",EvidenceSHA256:strings.Repeat("c",64)}
 raw,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 signed:=workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(key,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...)))}
 without:=terminalReceipts{}
 a,err:=EvaluateOriginal(context.Background(),without,scienceWitness(true),e,nil)
 if err!=nil||a!=WaitForReconciliation{t.Fatal(a,err)}
 with:=terminalReceipts{signed:&signed}
 a,err=EvaluateOriginal(context.Background(),with,scienceWitness(true),e,nil)
 if err!=nil||a!=AuthenticateEvidence{t.Fatal(a,err)}
 ev:=TerminalEvidence{Lane:e.Lane,OriginalRunID:e.OriginalRunID,EvidenceSHA256:r.EvidenceSHA256,ClassificationSHA256:strings.Repeat("d",64),SourceHeadSHA256:strings.Repeat("e",64),IndependentlyAuthenticated:true}
 a,err=EvaluateOriginal(context.Background(),with,scienceWitness(false),e,&ev)
 if err==nil||a!=WaitForReconciliation{t.Fatal(a,err)}
 a,err=EvaluateOriginal(context.Background(),with,scienceWitness(true),e,&ev)
 if err!=nil||a!=IndependentSuccessor{t.Fatal(a,err)}
 ev.Lane="Yggdrasil"
 if _,err=EvaluateOriginal(context.Background(),with,scienceWitness(true),e,&ev);err==nil{t.Fatal("cross-lane evidence")}
}
