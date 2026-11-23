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
func TestIndependentTerminalWitnessSignature(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY SCIENTIFIC WITNESS"))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 expected:=workerreconcile.Expected{Lane:"Wingless",OriginalRunID:"original",OwnerEpoch:12}
 e:=TerminalEvidence{Lane:"Wingless",OriginalRunID:"original",EvidenceSHA256:strings.Repeat("a",64),ClassificationSHA256:strings.Repeat("b",64),SourceHeadSHA256:strings.Repeat("c",64),IndependentlyAuthenticated:true}
 signed:=SignedTerminal{Evidence:e,WorkerEvidenceSHA256:e.EvidenceSHA256,OwnerEpoch:12}
 raw,err:=json.Marshal(struct{Evidence TerminalEvidence `json:"evidence"`;WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`;OwnerEpoch uint64 `json:"owner_epoch"`}{e,e.EvidenceSHA256,12})
 if err!=nil{t.Fatal(err)}
 signed.SignatureHex=hex.EncodeToString(ed25519.Sign(priv,append([]byte("FORGE-TERMINAL-SCIENCE-WITNESS-V1\n"),raw...)))
 w:=AttestedTerminalWitness{PublicKey:priv.Public().(ed25519.PublicKey),Expected:expected,Signed:signed}
 if ok,err:=w.VerifyTerminal(context.Background(),e);err!=nil||!ok{t.Fatal(ok,err)}
 e.ClassificationSHA256=strings.Repeat("d",64)
 if ok,err:=w.VerifyTerminal(context.Background(),e);err==nil||ok{t.Fatal("classification tamper accepted")}
 e=signed.Evidence;w.Expected.OwnerEpoch=13
 if ok,err:=w.VerifyTerminal(context.Background(),e);err==nil||ok{t.Fatal("stale authority epoch accepted")}
}
