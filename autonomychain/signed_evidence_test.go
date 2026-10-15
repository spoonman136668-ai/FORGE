package autonomychain

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/executionbridge"
 "github.com/spoonman136668-ai/forge/originalclaim"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
func fixtureSigner(s string) ed25519.PrivateKey {
 digest:=sha256.Sum256([]byte("F56_TEST_ONLY_"+s))
 return ed25519.NewKeyFromSeed(digest[:])
}
func signReceipt(t *testing.T,r workerreconcile.Receipt,priv ed25519.PrivateKey)workerreconcile.Signed{
 t.Helper()
 b,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 return workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(ed25519.Sign(priv,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),b...)))}
}
func signScience(t *testing.T,s executionbridge.SignedTerminal,priv ed25519.PrivateKey)executionbridge.SignedTerminal{
 t.Helper()
 b,err:=json.Marshal(struct{
  Evidence executionbridge.TerminalEvidence `json:"evidence"`
  WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`
  OwnerEpoch uint64 `json:"owner_epoch"`
 }{s.Evidence,s.WorkerEvidenceSHA256,s.OwnerEpoch})
 if err!=nil{t.Fatal(err)}
 s.SignatureHex=hex.EncodeToString(ed25519.Sign(priv,append([]byte("FORGE-TERMINAL-SCIENCE-WITNESS-V1\n"),b...)))
 return s
}
func mkSigned(t *testing.T,r *Original,root string,n int)SignedEvidence{
 t.Helper()
 wPriv:=fixtureSigner(r.Lane+"-worker")
 sPriv:=fixtureSigner(r.Lane+"-science")
 w:=workerreconcile.Expected{
  Lane:r.Lane,ExperimentID:r.ExperimentID,OriginalRunID:r.OriginalRunID,
  FrozenSHA256:r.FrozenPlanSHA256,IntentSHA256:fmt.Sprintf("%064x",n+400),
  WorkerID:r.Lane+"-worker",OwnerEpoch:12,
  WorkerPublicKey:wPriv.Public().(ed25519.PublicKey),
 }
 claim:=originalclaim.Claim{Schema:originalclaim.Schema,Lane:r.Lane,
  ExperimentID:r.ExperimentID,FrozenSHA256:w.FrozenSHA256,
  IntentSHA256:w.IntentSHA256,SourceCommitSHA:r.SourceCommitSHA,
  OriginalRunID:w.OriginalRunID,OwnerEpoch:w.OwnerEpoch,
  WorkerID:w.WorkerID,FirstUseConsumed:true}
 if err:=originalclaim.Consume(root,claim);err!=nil{t.Fatal(err)}
 base:=workerreconcile.Receipt{Schema:workerreconcile.Schema,Lane:w.Lane,
  ExperimentID:w.ExperimentID,FrozenSHA256:w.FrozenSHA256,
  IntentSHA256:w.IntentSHA256,OriginalRunID:w.OriginalRunID,
  WorkerID:w.WorkerID,OwnerEpoch:w.OwnerEpoch}
 start:=base;start.Stage="STARTED"
 end:=base;end.Stage="TERMINAL";end.EvidenceSHA256=fmt.Sprintf("%064x",n+800)
 st:=signReceipt(t,start,wPriv)
 te:=signReceipt(t,end,wPriv)
 r.StartReceiptSHA256,_=workerreconcile.Fingerprint(st)
 r.TerminalReceiptSHA256,_=workerreconcile.Fingerprint(te)
 sourceHead:=strings.Repeat("c",64)
 ev:=executionbridge.TerminalEvidence{
  Lane:r.Lane,OriginalRunID:r.OriginalRunID,EvidenceSHA256:end.EvidenceSHA256,
  ClassificationSHA256:strings.Repeat("e",64),SourceHeadSHA256:sourceHead,
  IndependentlyAuthenticated:true,
 }
 review:=signScience(t,executionbridge.SignedTerminal{Evidence:ev,
  WorkerEvidenceSHA256:ev.EvidenceSHA256,OwnerEpoch:w.OwnerEpoch},sPriv)
 r.IndependentReviewSHA256,_=executionbridge.TerminalWitnessFingerprint(review)
 return SignedEvidence{ClaimRoot:root,Claim:claim,Worker:w,
  Start:st,Terminal:te,
  Science:executionbridge.AttestedTerminalWitness{
   PublicKey:sPriv.Public().(ed25519.PublicKey),Expected:w,Signed:review,
  },
  PinnedSourceHeadSHA256:sourceHead}
}
func signedFixture(t *testing.T)(Candidate,EvidenceSet){
 t.Helper()
 c:=fixture()
 root:=t.TempDir()
 e:=EvidenceSet{}
 for i:=0;i<2;i++{
  e.Wingless[i]=mkSigned(t,&c.Wingless[i],root,i+1)
  e.Yggdrasil[i]=mkSigned(t,&c.Yggdrasil[i],root,i+3)
 }
 return c,e
}
func TestF56SignedEvidenceNoAuthority(t *testing.T){
 c,e:=signedFixture(t)
 r,err:=VerifySignedEvidence(context.Background(),c,e)
 if err!=nil{t.Fatal(err)}
 if !r.Structure.StructuralContinuity||!r.LocalFirstUseClaimsMatched||
  !r.SuppliedKeyWorkerSignaturesValid||!r.SuppliedKeyScienceSignaturesValid||
  r.IndependentOwnerHighWaterVerified||r.DistributedFirstUseCASVerified||
  r.AuthenticFirstUseVerified||r.NewOriginalsExecuted||
  r.IndependentScientificAcceptance||r.AutonomousDispatchAuthorized||
  r.OwnerCutoverAuthorized{t.Fatalf("authority fabricated: %+v",r)}
 r2,err:=VerifySignedEvidence(context.Background(),c,e)
 if err!=nil||r!=r2{t.Fatal("non-deterministic signed report",err)}
}
func TestF56RejectsSpoofedTamperedOrMissingInputs(t *testing.T){
 cases:=map[string]func(*Candidate,*EvidenceSet){
  "fake worker signature":func(c *Candidate,e *EvidenceSet){e.Wingless[0].Start.SignatureHex=strings.Repeat("0",128)},
  "fake independent witness":func(c *Candidate,e *EvidenceSet){e.Yggdrasil[1].Science.Signed.SignatureHex=strings.Repeat("0",128)},
  "changed source commit":func(c *Candidate,e *EvidenceSet){e.Yggdrasil[0].Claim.SourceCommitSHA=strings.Repeat("b",40)},
  "mismatched epoch":func(c *Candidate,e *EvidenceSet){e.Wingless[1].Worker.OwnerEpoch++},
  "drifted source head":func(c *Candidate,e *EvidenceSet){e.Wingless[0].PinnedSourceHeadSHA256=strings.Repeat("f",64)},
  "wrong evidence digest":func(c *Candidate,e *EvidenceSet){e.Yggdrasil[1].Terminal.Receipt.EvidenceSHA256=strings.Repeat("d",64)},
  "tampered receipt fingerprint":func(c *Candidate,e *EvidenceSet){c.Wingless[0].StartReceiptSHA256=strings.Repeat("9",64)},
  "crosslane signer reuse":func(c *Candidate,e *EvidenceSet){e.Yggdrasil[0].Worker.WorkerPublicKey=e.Wingless[0].Worker.WorkerPublicKey},
  "lost consumed claim":func(c *Candidate,e *EvidenceSet){e.Wingless[1].ClaimRoot=filepath.Join(t.TempDir(),"missing")},
  "missing science signature":func(c *Candidate,e *EvidenceSet){e.Yggdrasil[0].Science.Signed.SignatureHex=""},
 }
 for name,modify:=range cases{t.Run(name,func(t *testing.T){
  c,e:=signedFixture(t);modify(&c,&e)
  if _,err:=VerifySignedEvidence(context.Background(),c,e);err==nil{t.Fatal("untrusted continuity accepted")}
 })}
}
func TestF56CancelledContextBlocks(t *testing.T){
 c,e:=signedFixture(t)
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=VerifySignedEvidence(ctx,c,e);err==nil{t.Fatal("cancelled verification accepted")}
}
func TestF56ClaimCorruptionNotRepaired(t *testing.T){
 c,e:=signedFixture(t)
 // The local write-once claim must not be recreated by the read-only audit.
 path:=e.Wingless[0].ClaimRoot
 entries,err:=os.ReadDir(path);if err!=nil{t.Fatal(err)}
 if len(entries)!=4{t.Fatalf("expected 4 local synthetic claims, got %d",len(entries))}
 for _,entry:=range entries{if err:=os.Remove(filepath.Join(path,entry.Name()));err!=nil{t.Fatal(err)};break}
 if _,err:=VerifySignedEvidence(context.Background(),c,e);err==nil{t.Fatal("missing claim accepted")}
 entries,err=os.ReadDir(path);if err!=nil||len(entries)!=3{t.Fatal("audit rewrote first-use state")}
}
