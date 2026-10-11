package hostedgrant
import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
)
func testPrivate()(ed25519.PrivateKey,ed25519.PrivateKey){
 a:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{54},32))
 b:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{55},32))
 return a,b
}
type setup struct{
 envelope Envelope
 pin Pin
 ctx Context
 scope fsagate.Scope
 proof fsagate.FirstUseProof
 signer ed25519.PrivateKey
}
func fresh(t *testing.T,lane string)setup{
 t.Helper()
 signer,head:=testPrivate()
 scope:=fsagate.Scope{Schema:fsagate.ScopeSchema,Lane:lane,
  Generation:17,ExperimentID:"EXPERIMENT_17",
  HypothesisCommitSHA:strings.Repeat("a",40),
  PreregCommitSHA:strings.Repeat("b",40),
  SourceCommitSHA:strings.Repeat("c",40),
  PreregSHA256:strings.Repeat("d",64),
  CandidateCohortSHA256:strings.Repeat("e",64),
  SourceQualificationWitnessSHA256:strings.Repeat("f",64),
  EligibleHistoricalSourceSHA256:strings.Repeat("1",64),
  PolicySHA256:strings.Repeat("2",64),
  PolicyLineageHeadSHA256:strings.Repeat("3",64),
  FrozenOptimizerSpecSHA256:strings.Repeat("4",64),
  MaxComputeUnits:128,AuthorityEpoch:7}
 proof:=fsagate.FirstUseProof{
  Schema:fsagate.FirstUseProofSchema,
  Mode:"EXTERNAL_FSA_FIRST_USE_OBSERVED_NO_DISPATCH",
  PlanSHA256:strings.Repeat("5",64),Lane:lane,CandidateID:"CANDIDATE_17",
  CohortSHA256:scope.CandidateCohortSHA256,
  StartedRecordSHA256:strings.Repeat("6",64),
  ObservedTrustedSequence:4,
  ObservedTrustedHeadSHA256:strings.Repeat("6",64),
  FSAFirstUseCommitted:true,FirstUseConsumed:true}
 scopeHash,_:=sha(scope);proofHash,_:=sha(proof)
 context:=Context{Repository:ExpectedRepository,
  Workflow:ExpectedWorkflow,RunID:"38180000099",Attempt:1,
  SourceSHA:scope.SourceCommitSHA,TreeSHA:strings.Repeat("7",40),
  Lane:lane}
 g:=Grant{Schema:GrantSchema,Repository:context.Repository,
  Workflow:context.Workflow,RunID:context.RunID,Attempt:1,
  SourceSHA:context.SourceSHA,TreeSHA:context.TreeSHA,Lane:lane,
  Generation:scope.Generation,ExperimentID:scope.ExperimentID,
  CandidateID:proof.CandidateID,CohortSHA256:scope.CandidateCohortSHA256,
  PreregSHA256:scope.PreregSHA256,ScopeSHA256:scopeHash,
  ArchiveID:strings.Repeat("8",64),AuthorityEpoch:scope.AuthorityEpoch,
  FirstUsePlanSHA256:proof.PlanSHA256,FirstUseProofSHA256:proofHash,
  StartedRecordSHA256:proof.StartedRecordSHA256,
  CommittedSequence:proof.ObservedTrustedSequence,
  CommittedHeadSHA256:proof.ObservedTrustedHeadSHA256,
  MaxComputeUnits:scope.MaxComputeUnits,ScienceRunID:88001,AuthorizingFSA:true}
 data,_:=json.Marshal(g)
 sig:=ed25519.Sign(signer,append([]byte(Domain),data...))
 h,_:=sha(g)
 pin:=Pin{GrantSHA256:h,
  GrantKeyHex:hex.EncodeToString(signer.Public().(ed25519.PublicKey)),
  IndependentFSAHeadKeyHex:hex.EncodeToString(head.Public().(ed25519.PublicKey))}
 return setup{Envelope{Grant:g,SignatureHex:hex.EncodeToString(sig)},
  pin,context,scope,proof,signer}
}
func (s *setup)resign(){
 raw,_:=json.Marshal(s.envelope.Grant)
 s.envelope.SignatureHex=hex.EncodeToString(ed25519.Sign(s.signer,append([]byte(Domain),raw...)))
 s.pin.GrantSHA256,_=sha(s.envelope.Grant)
}
func (s setup)review()(Review,error){return ReviewGrant(s.envelope,s.pin,s.ctx,s.scope,s.proof)}
func TestSignedFSASelectionLinksOnlyExistingFirstUse(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  s:=fresh(t,lane)
  got,err:=s.review()
  if err!=nil||got.Schema!=ReviewSchema||!got.FirstUseObserved||
   got.ScienceExecuted||got.AcceptedScience||got.LiveFSAOperational||
   got.ProtectedReplayLockAcquired||got.IndependentPhysicalCustodyVerified||
   got.Mode!="CRYPTOGRAPHIC_REVIEW_ONLY_NO_EXECUTION"{
   t.Fatalf("incorrect science authority: %v %+v",err,got)
  }
 }
}
func TestRejectAbsentOrForgedIndependentGrant(t *testing.T){
 s:=fresh(t,"Wingless")
 s.envelope.SignatureHex=""
 if _,err:=s.review();!errors.Is(err,ErrDenied){t.Fatal("missing FSA signature accepted")}
 s=fresh(t,"Wingless")
 s.envelope.Grant.MaxComputeUnits++
 if _,err:=s.review();err==nil{t.Fatal("altered budget accepted")}
 s=fresh(t,"Wingless")
 s.pin.GrantKeyHex=s.pin.IndependentFSAHeadKeyHex
 if _,err:=s.review();err==nil{t.Fatal("same FSA grant and head key accepted")}
 s=fresh(t,"Wingless")
 s.pin.GrantSHA256=strings.Repeat("0",64)
 if _,err:=s.review();err==nil{t.Fatal("forged independent pin accepted")}
 s=fresh(t,"Wingless")
 s.envelope.Grant.CohortSHA256=strings.Repeat("0",64)
 s.resign()
 if _,err:=s.review();err==nil{t.Fatal("different FSA-authorized cohort accepted")}
}
func TestRejectRunReplayForeignRepoWorkflowAndTree(t *testing.T){
 for _,change:=range []func(*setup){
  func(s *setup){s.ctx.Attempt=2},
  func(s *setup){s.ctx.RunID="38180000100"},
  func(s *setup){s.ctx.Repository="attacker/FORGE"},
  func(s *setup){s.ctx.Workflow=".github/workflows/attacker.yml"},
  func(s *setup){s.ctx.TreeSHA=strings.Repeat("9",40)},
  func(s *setup){s.ctx.SourceSHA=strings.Repeat("9",40)},
  func(s *setup){s.ctx.Lane="Yggdrasil"},
  func(s *setup){s.envelope.Grant.Attempt=2;s.resign()},
  func(s *setup){s.envelope.Grant.AuthorizingFSA=false;s.resign()},
 } {
  s:=fresh(t,"Wingless");change(&s)
  if _,err:=s.review();err==nil{t.Fatal("forged or rerun GitHub context accepted")}
 }
}
func TestRejectUncommittedStaleOrReclassifiedFSAProof(t *testing.T){
 for _,change:=range []func(*setup){
  func(s *setup){s.proof.FirstUseConsumed=false},
  func(s *setup){s.proof.FSAFirstUseCommitted=false},
  func(s *setup){s.proof.DispatchAuthorized=true},
  func(s *setup){s.proof.ScientificAccepted=true},
  func(s *setup){s.proof.PhysicalIndependenceDemonstrated=true},
  func(s *setup){s.proof.ObservedTrustedSequence++},
  func(s *setup){s.proof.ObservedTrustedHeadSHA256=strings.Repeat("a",64)},
  func(s *setup){s.proof.CohortSHA256=strings.Repeat("a",64)},
  func(s *setup){s.scope.MaxComputeUnits++},
  func(s *setup){s.scope.Lane="Yggdrasil"},
  func(s *setup){s.scope.AuthorityEpoch++},
 }{
  s:=fresh(t,"Wingless");change(&s)
  if _,err:=s.review();err==nil{t.Fatal("stale/mutated FSA proof accepted")}
 }
}
func TestMalformedEnvelopeFailClosed(t *testing.T){
 for _,b:=range [][]byte{nil,[]byte("{"),
  []byte("{}{}"),[]byte("{}\nnull"),[]byte(`{"Grant":{"BadKey":1},"SignatureHex":"a"}`)} {
  if _,err:=ParseEnvelope(b);err==nil{t.Fatal("malformed FSA envelope accepted")}
 }
 s:=fresh(t,"Yggdrasil")
 raw,_:=json.Marshal(s.envelope)
 decoded,err:=ParseEnvelope(raw)
 if err!=nil||decoded.EnvelopeGrantMatches(s.envelope)==false{
  t.Fatal("canonical valid signed envelope parsing drift",err)
 }
}
// No execution happens on a positive proof. A future independent FSA
// must maintain a protected, atomic dispatch consumption ledger.
func (e Envelope)EnvelopeGrantMatches(other Envelope)bool{
 a,_:=json.Marshal(e);b,_:=json.Marshal(other)
 return bytes.Equal(a,b)
}
