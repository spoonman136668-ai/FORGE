package fsaissuance

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
 "github.com/spoonman136668-ai/forge/dreamrsi/prospective"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func testHash(s string)string{v:=sha256.Sum256([]byte(s));return hex.EncodeToString(v[:])}
func shaJSON(x any)string{raw,_:=json.Marshal(x);v:=sha256.Sum256(raw);return hex.EncodeToString(v[:])}
type mockFloor struct {
 mu sync.Mutex
 current fsahead.Anchor
 reads,cas,commits int
 denied,ambiguous,offline bool
}
func (m *mockFloor) ReadAnchor(context.Context)(fsahead.Anchor,error){
 m.mu.Lock();defer m.mu.Unlock()
 m.reads++
 if m.offline{return fsahead.Anchor{},errors.New("fixture floor down")}
 c:=m.current;c.PublicKey=append([]byte(nil),c.PublicKey...)
 return c,nil
}
func (m *mockFloor) ConfirmArchiveBinding(_ context.Context,id string)(bool,error){
 m.mu.Lock();defer m.mu.Unlock()
 if m.offline{return false,errors.New("fixture binding down")}
 return id==m.current.ArchiveID,nil
}
func (m *mockFloor) CompareAndSwap(_ context.Context,from,to fsahead.Anchor)(bool,error){
 m.mu.Lock();defer m.mu.Unlock()
 m.cas++
 if m.offline{return false,errors.New("partition")}
 if m.denied||m.current.Sequence!=from.Sequence||
  m.current.HeadSHA256!=from.HeadSHA256{return false,nil}
 m.current=to;m.commits++
 if m.ambiguous{return false,errors.New("committed but acknowledgment lost")}
 return true,nil
}
type mockIssuer struct {
 mu sync.Mutex
 private ed25519.PrivateKey
 calls int
 denied,badSigner,badHead bool
}
func (i *mockIssuer) IssueFirstUse(_ context.Context,req IssuanceRequest)(fsahead.SignedHead,error){
 i.mu.Lock()
 defer i.mu.Unlock()
 i.calls++
 if i.denied{return fsahead.SignedHead{},errors.New("FSA denied")}
 next:=req.ProposedHeadSHA256
 if i.badHead{next=testHash("wrong checkpoint head")}
 payload:=fsahead.Payload{
  Schema:fsahead.Schema,Domain:fsahead.Domain,
  ArchiveID:req.ArchiveID,KeyID:"FORGE_TEST_R6",
  AuthorityEpoch:req.AuthorityEpoch,
  ParentSequence:req.PreviousSequence,
  ParentHeadSHA256:req.PreviousHeadSHA256,
  Sequence:req.ProposedSequence,HeadSHA256:next,
 }
 raw,_:=json.Marshal(payload)
 private:=i.private
 if i.badSigner{private=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{42},32))}
 msg:=append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),raw...)
 return fsahead.SignedHead{Payload:payload,
  SignatureHex:hex.EncodeToString(ed25519.Sign(private,msg))},nil
}
type fixture struct {
 archive *privatearchive.Store
 floor *mockFloor
 issuer *mockIssuer
 identity fsatrust.Identity
 plan fsagate.FirstUsePlan
 pin string
}
func create(t *testing.T,lane string)*fixture {
 t.Helper()
 archive,err:=privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName))
 if err!=nil{t.Fatal(err)}
 sigKey:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{17},32))
 identity:=fsatrust.Identity{
  ArchiveID:testHash(lane+"/physical-mock-FSA"),
  KeyID:"FORGE_TEST_R6",PublicKey:sigKey.Public().(ed25519.PublicKey),
  AuthorityEpoch:7,
 }
 source:=strings.Repeat("a",40)
 hyp:=strings.Repeat("b",40)
 preregSource:=strings.Repeat("c",40)
 prereg:=testHash("prereg-"+lane)
 cohort:=testHash("cohort-"+lane)
 witness:=testHash("source-qualified-"+lane)
 var row researchlog.Record
 for _,e:=range []researchlog.Event{
  {Lane:lane,Generation:5,ExperimentID:"EXP_5",Kind:researchlog.Hypothesis,SourceCommitSHA:hyp},
  {Lane:lane,Generation:5,ExperimentID:"EXP_5",Kind:researchlog.Preregister,SourceCommitSHA:preregSource,PreregSHA256:prereg,CohortSHA256:cohort},
  {Lane:lane,Generation:5,ExperimentID:"EXP_5",Kind:researchlog.SourceQualified,SourceCommitSHA:source,PreregSHA256:prereg,CohortSHA256:cohort,WitnessSHA256:witness},
 } {
  row,err=archive.AppendEvent(e)
  if err!=nil{t.Fatal(err)}
 }
 floor:=&mockFloor{current:fsahead.Anchor{
  ArchiveID:identity.ArchiveID,KeyID:identity.KeyID,
  PublicKey:append([]byte(nil),identity.PublicKey...),
  AuthorityEpoch:identity.AuthorityEpoch,
  Sequence:row.Sequence,HeadSHA256:row.RecordSHA256,
 }}
 policy:=dreamrsi.BasePolicies(lane,50)[0]
 choiceOptions:=[]dreamrsi.Option{
  {ID:"first",CohortSHA256:cohort,Family:"novel",
   Impact:89,Novelty:90,Robustness:90,Diversity:70,
   EstimatedCost:60,Risk:1},
  {ID:"second",CohortSHA256:testHash(lane+"/unused-other"),Family:"control",
   Impact:20,Novelty:10,Robustness:20,Diversity:20,
   EstimatedCost:20,Risk:5},
 }
 contextSHA:=testHash(lane+"/frozen-predecision")
 choice,err:=dreamrsi.Select(policy,dreamrsi.Decision{
  ContextSHA256:contextSHA,Options:choiceOptions,
 })
 if err!=nil||choice!="first"{t.Fatal("unexpected policy decision",choice,err)}
 historySHA:=testHash(lane+"/independent-history")
 specSHA:=testHash(lane+"/frozen-optimizer")
 lineageSHA:=testHash(lane+"/policy-lineage")
 scope:=fsagate.Scope{
  Schema:fsagate.ScopeSchema,Lane:lane,Generation:5,
  ExperimentID:"EXP_5",
  HypothesisCommitSHA:hyp,PreregCommitSHA:preregSource,
  SourceCommitSHA:source,PreregSHA256:prereg,
  CandidateCohortSHA256:cohort,SourceQualificationWitnessSHA256:witness,
  EligibleHistoricalSourceSHA256:historySHA,
  PolicySHA256:policy.ID(),PolicyLineageHeadSHA256:lineageSHA,
  FrozenOptimizerSpecSHA256:specSHA,
  MaxComputeUnits:101,AuthorityEpoch:identity.AuthorityEpoch,
 }
 scopeSHA:=shaJSON(scope)
 request:=dreamrsi.FSASelectionRequest{
  Schema:dreamrsi.ContractSchema,
  Mode:"UNPRIVILEGED_FSA_REVIEW_REQUEST",
  Lane:lane,SourceHistorySHA256:historySHA,
  FrozenSpecSHA256:specSHA,OptimizerLineageHeadSHA256:lineageSHA,
  PolicySHA256:policy.ID(),CandidateID:"first",
  CandidateCohortSHA256:cohort,
 }
 selection:=prospective.Selection{
  Schema:prospective.DecisionSchema,Lane:lane,
  Epoch:identity.AuthorityEpoch,Tick:90,
  SourceCommitSHA:source,FrozenPreregSHA256:prereg,
  PolicySHA256:policy.ID(),PolicyLineageSHA256:lineageSHA,
  ContextSHA256:contextSHA,Options:choiceOptions,
  ChosenID:"first",ChosenCohortSHA256:cohort,
  MaxComputeUnits:scope.MaxComputeUnits,
  LoggingMode:prospective.Observational,
 }
 selectionKey:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{28},32))
 raw,_:=json.Marshal(selection)
 msg:=append([]byte(prospective.DecisionDomain),raw...)
 signed:=prospective.SignedSelection{Selection:selection,
  SignatureHex:hex.EncodeToString(ed25519.Sign(selectionKey,msg))}
 signedPin:=prospective.IndependentPin{
  ExpectedSHA256:shaJSON(selection),
  PublicKeyHex:hex.EncodeToString(selectionKey.Public().(ed25519.PublicKey)),
 }
 plan,err:=fsagate.PrepareFirstUse(context.Background(),floor,archive,identity,
  signed,signedPin,policy,request,scope,scopeSHA,
  testHash(lane+"/external-FSA-STARTED-receipt"),50505)
 if err!=nil{t.Fatal(err)}
 pin,err:=fsagate.PlanSHA(plan)
 if err!=nil{t.Fatal(err)}
 return &fixture{archive:archive,floor:floor,
  issuer:&mockIssuer{private:sigKey},identity:identity,plan:plan,pin:pin}
}
func (f *fixture)commit()(fsagate.FirstUseProof,error){
 return CommitFirstUse(context.Background(),f.floor,f.archive,f.identity,
  f.issuer,f.plan,f.pin)
}
func TestRealFSAArchiveMockIssuerCommitsOnlyOnceAndNeverDispatches(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  f:=create(t,lane)
  proof,err:=f.commit();if err!=nil{t.Fatal(err)}
  if !proof.FirstUseConsumed||!proof.FSAFirstUseCommitted||
   proof.DispatchAuthorized||proof.ScientificAccepted||
   proof.PhysicalIndependenceDemonstrated||
   proof.AcceptedRefMutation||f.floor.commits!=1||
   f.floor.cas!=1||f.issuer.calls!=1 {
   t.Fatalf("FSA source-only first-use proof drift %+v",proof)
  }
  if _,err=f.commit();!errors.Is(err,ErrDenied){t.Fatal("repeated committed first-use not denied")}
  if f.floor.cas!=1||f.issuer.calls!=1{t.Fatal("repeat issued another FSA transaction")}
  j,err:=f.archive.Load()
  if err!=nil||len(j.Entries)!=4||
   j.Entries[3].Event.Kind!=researchlog.PrimaryStarted{t.Fatal("exact started record not retained")}
 }
}
func TestFSAAmbiguousCommitNeverRetriesAndOnlyReadOnlyReconcile(t *testing.T){
 f:=create(t,"Wingless")
 f.floor.ambiguous=true
 if _,err:=f.commit();!errors.Is(err,ErrUncertain){
  t.Fatal("committed but lost response incorrectly acknowledged:",err)
 }
 if f.floor.cas!=1||f.floor.commits!=1||f.issuer.calls!=1{
  t.Fatal("ambiguous CAS not exactly once")
 }
 signed,err:=f.issuer.IssueFirstUse(context.Background(),IssuanceRequest{
  PlanSHA256:f.pin,ArchiveID:f.plan.ArchiveID,AuthorityEpoch:f.plan.AuthorityEpoch,
  PreviousSequence:f.plan.PreviousSequence,PreviousHeadSHA256:f.plan.PreviousHeadSHA256,
  ProposedSequence:f.plan.PlannedSequence,ProposedHeadSHA256:f.plan.PlannedStartedRecordSHA256,
 })
 if err!=nil{t.Fatal(err)}
 proof,err:=ReconcileCommittedFirstUse(context.Background(),f.floor,f.archive,
  f.identity,f.plan,f.pin,signed)
 if err!=nil||!proof.FirstUseConsumed{t.Fatal("read-only reconciliation failed:",err)}
 if f.floor.cas!=1{t.Fatal("reconciler made second CAS")}
 if _,err=f.commit();!errors.Is(err,ErrDenied){t.Fatal("repeated original after ambiguous committed CAS accepted")}
 if f.floor.cas!=1{t.Fatal("unsafe CAS retry")}
}
func TestFSADeniedIssuerAndInvalidCertificatesNeverMutate(t *testing.T){
 for _,testcase:=range []struct{
  name string
  deny,badSigner,badHead bool
 }{
  {"denied",true,false,false},
  {"untrusted-key",false,true,false},
  {"bad-result-head",false,false,true},
 } {
  t.Run(testcase.name,func(t *testing.T){
   f:=create(t,"Yggdrasil")
   f.issuer.denied=testcase.deny
   f.issuer.badSigner=testcase.badSigner
   f.issuer.badHead=testcase.badHead
   if _,err:=f.commit();!errors.Is(err,ErrDenied){t.Fatal("invalid issuer not rejected",err)}
   if f.floor.cas!=0||f.floor.commits!=0{t.Fatal("bad issuer modified external FSA")}
   j,err:=f.archive.Load()
   if err!=nil||len(j.Entries)!=3{t.Fatal("bad issuer consumed start locally")}
  })
 }
}
func TestFSADeniedCASLeavesUncertainConsumedEvidenceNoReplay(t *testing.T){
 f:=create(t,"Yggdrasil")
 f.floor.denied=true
 if _,err:=f.commit();!errors.Is(err,ErrUncertain){t.Fatal("failed CAS not classified as unknown:",err)}
 if f.floor.commits!=0||f.floor.cas!=1{t.Fatal("failed CAS count wrong")}
 j,err:=f.archive.Load();if err!=nil||len(j.Entries)!=4{t.Fatal("incomplete consumption not recorded")}
 if _,err=f.commit();!errors.Is(err,ErrDenied){t.Fatal("retry after denied CAS unexpectedly allowed")}
 if f.floor.cas!=1{t.Fatal("denied CAS retried")}
}
func TestFSAOutageAndStalePinnedPlanFailClosed(t *testing.T){
 f:=create(t,"Wingless")
 f.floor.offline=true
 if _,err:=f.commit();!errors.Is(err,ErrDenied){t.Fatal("offline FSA allowed first use")}
 if f.floor.cas!=0||f.issuer.calls!=0{t.Fatal("offline FSA triggered issuer or CAS")}
 f.floor.offline=false
 f.plan.PreviousHeadSHA256=testHash("fake-old-head")
 if _,err:=f.commit();!errors.Is(err,ErrDenied){t.Fatal("stale predecessor accepted")}
 f.plan.PreviousHeadSHA256=f.floor.current.HeadSHA256
 f.pin=testHash("false independently pinned plan")
 if _,err:=f.commit();!errors.Is(err,ErrDenied){t.Fatal("untrusted pinned plan allowed")}
}
func TestRacingFSAFirstUseOnlyOneWriterOrCAS(t *testing.T){
 f:=create(t,"Wingless")
 var wg sync.WaitGroup
 start:=make(chan struct{})
 outcomes:=make(chan error,2)
 for i:=0;i<2;i++{
  wg.Add(1)
  go func(){defer wg.Done();<-start
   _,err:=f.commit();outcomes<-err
  }()
 }
 close(start);wg.Wait();close(outcomes)
 success:=0
 for err:=range outcomes{if err==nil{success++}}
 // One may fail before append or after losing O_EXCL. In either case the
 // monotonic floor cannot be committed twice and no science is dispatched.
 if success!=1||f.floor.commits!=1||f.floor.cas!=1{
  t.Fatalf("FSA race yielded success=%d commits=%d CAS=%d",
   success,f.floor.commits,f.floor.cas)
 }
 j,err:=f.archive.Load()
 if err!=nil||len(j.Entries)!=4{t.Fatal("racing first-use archive mismatch")}
}
