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
func TestBoundTerminalRejectsEvidenceSubstitution(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST WORKER KEY"));worker:=ed25519.NewKeyFromSeed(seed[:])
 wseed:=sha256.Sum256([]byte("TEST INDEPENDENT KEY"));witness:=ed25519.NewKeyFromSeed(wseed[:])
 e:=workerreconcile.Expected{Lane:"Yggdrasil",ExperimentID:"original",OriginalRunID:"original",FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),OwnerEpoch:7,WorkerID:"worker",WorkerPublicKey:worker.Public().(ed25519.PublicKey)}
 receipt:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,IntentSHA256:e.IntentSHA256,OriginalRunID:e.OriginalRunID,OwnerEpoch:e.OwnerEpoch,WorkerID:e.WorkerID,Stage:"TERMINAL",EvidenceSHA256:strings.Repeat("c",64)}
 raw,_:=json.Marshal(receipt)
 signed:=workerreconcile.Signed{Receipt:receipt,SignatureHex:hex.EncodeToString(ed25519.Sign(worker,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),raw...)))}
 ev:=TerminalEvidence{Lane:e.Lane,OriginalRunID:e.OriginalRunID,EvidenceSHA256:receipt.EvidenceSHA256,ClassificationSHA256:strings.Repeat("d",64),SourceHeadSHA256:strings.Repeat("e",64),IndependentlyAuthenticated:true}
 claim:=SignedTerminal{Evidence:ev,WorkerEvidenceSHA256:ev.EvidenceSHA256,OwnerEpoch:e.OwnerEpoch}
 proof,_:=json.Marshal(struct{Evidence TerminalEvidence `json:"evidence"`;WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`;OwnerEpoch uint64 `json:"owner_epoch"`}{ev,ev.EvidenceSHA256,e.OwnerEpoch})
 claim.SignatureHex=hex.EncodeToString(ed25519.Sign(witness,append([]byte("FORGE-TERMINAL-SCIENCE-WITNESS-V1\n"),proof...)))
 trusted:=AttestedTerminalWitness{PublicKey:witness.Public().(ed25519.PublicKey),Expected:e,Signed:claim}
 got,err:=EvaluateBoundOriginal(context.Background(),terminalReceipts{signed:&signed},trusted,e,ev)
 if err!=nil||got!=IndependentSuccessor{t.Fatal(got,err)}
 ev.EvidenceSHA256=strings.Repeat("f",64)
 if got,err:=EvaluateBoundOriginal(context.Background(),terminalReceipts{signed:&signed},trusted,e,ev);err==nil||got!=WaitForReconciliation{t.Fatal("substitution accepted",got,err)}
}
