package fsagate

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "crypto/sha256"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/dreamrsi/prospective"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type fixtureAuthority struct{
 mu sync.Mutex
 anchor fsahead.Anchor
 archiveID string
 calls int
 swapAfterFirst bool
 unavailable bool
}
func (m *fixtureAuthority)ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 m.mu.Lock();defer m.mu.Unlock()
 if m.unavailable{return fsahead.Anchor{},errors.New("offline")}
 m.calls++
 a:=m.anchor
 if m.swapAfterFirst&&m.calls==2{
  a.Sequence++
  a.HeadSHA256=hashFixture("stale-mutated-head")
 }
 return a,nil
}
func (m *fixtureAuthority)ConfirmArchiveBinding(ctx context.Context,id string)(bool,error){
 if m.unavailable{return false,errors.New("offline")}
 return id==m.archiveID,nil
}
func (m *fixtureAuthority)CompareAndSwap(ctx context.Context,a,b fsahead.Anchor)(bool,error){
 panic("FSA read-only reviewer must NEVER attempt CAS")
}
func hashFixture(s string)string{
 sum:=scopeHashFixture([]byte(s))
 return sum
}
func scopeHashFixture(b []byte)string{
 d:=sha256Fixture(b)
 return hex.EncodeToString(d[:])
}
func sha256Fixture(b []byte)[32]byte{
 // Test helper explicit pure digest so no repository secrets are accessed.
 return sha256.Sum256(b)
}
type setup struct{
 scope Scope
 scopeSHA string
 request dreamrsi.FSASelectionRequest
 signed prospective.SignedSelection
 pin prospective.IndependentPin
 policy dreamrsi.Policy
 store *privatearchive.Store
 backend *fixtureAuthority
 identity fsatrust.Identity
}
func makeFixture(t *testing.T,lane string)*setup {
 t.Helper()
 policy:=dreamrsi.BasePolicies(lane,101)[0]
 archive,err:=privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName))
 if err!=nil{t.Fatal(err)}
 source:=strings.Repeat("a",40)
 hypothesisSource:=strings.Repeat("b",40)
 preregSource:=strings.Repeat("c",40)
 cohort:=hashFixture(lane+"/unused-cohort/42")
 prereg:=hashFixture(lane+"/frozen-prereg")
 witness:=hashFixture(lane+"/qualified-source-witness")
 identity:=fsatrust.Identity{
  ArchiveID:hashFixture(lane+"/private-FSA-archive"),KeyID:"fixture-authority",
  PublicKey:bytes.Repeat([]byte{75},32),AuthorityEpoch:3,
 }
 id:="experiment42"
 events:=[]researchlog.Event{
  {Lane:lane,Generation:4,ExperimentID:id,Kind:researchlog.Hypothesis,SourceCommitSHA:hypothesisSource},
  {Lane:lane,Generation:4,ExperimentID:id,Kind:researchlog.Preregister,SourceCommitSHA:preregSource,PreregSHA256:prereg,CohortSHA256:cohort},
  {Lane:lane,Generation:4,ExperimentID:id,Kind:researchlog.SourceQualified,SourceCommitSHA:source,PreregSHA256:prereg,CohortSHA256:cohort,WitnessSHA256:witness},
 }
 var last researchlog.Record
 for _,e:=range events{
  last,err=archive.AppendEvent(e);if err!=nil{t.Fatal(err)}
 }
 backend:=&fixtureAuthority{archiveID:identity.ArchiveID,
  anchor:fsahead.Anchor{ArchiveID:identity.ArchiveID,KeyID:identity.KeyID,
   PublicKey:append(ed25519.PublicKey(nil),identity.PublicKey...),
   AuthorityEpoch:identity.AuthorityEpoch,Sequence:last.Sequence,HeadSHA256:last.RecordSHA256},
 }
 candidates:=[]dreamrsi.Option{{
  ID:"candidateA",Family:"mechanism",CohortSHA256:cohort,
  Impact:55,Novelty:75,Robustness:80,Diversity:80,EstimatedCost:80,Risk:5,
 },{
  ID:"candidateB",Family:"control",CohortSHA256:hashFixture(lane+"/other-cohort/42"),
  Impact:10,Novelty:10,Robustness:10,Diversity:10,EstimatedCost:10,Risk:5,
 }}
 choice,err:=dreamrsi.Select(policy,dreamrsi.Decision{Options:candidates,ContextSHA256:hashFixture(lane+"/predecision-context")})
 if err!=nil||choice!="candidateA"{t.Fatal("fixture control policy changed:",choice,err)}
 scope:=Scope{
  Schema:ScopeSchema,Lane:lane,Generation:4,ExperimentID:id,
  HypothesisCommitSHA:hypothesisSource,PreregCommitSHA:preregSource,
  SourceCommitSHA:source,PreregSHA256:prereg,CandidateCohortSHA256:cohort,
  SourceQualificationWitnessSHA256:witness,
  EligibleHistoricalSourceSHA256:hashFixture(lane+"/authenticated-historical-source"),
  PolicySHA256:policy.ID(),PolicyLineageHeadSHA256:hashFixture(lane+"/policy-lineage"),
  FrozenOptimizerSpecSHA256:hashFixture(lane+"/optimizer-spec"),
  MaxComputeUnits:125,AuthorityEpoch:3,
 }
 request:=dreamrsi.FSASelectionRequest{
  Schema:dreamrsi.ContractSchema,Mode:"UNPRIVILEGED_FSA_REVIEW_REQUEST",
  Lane:lane,SourceHistorySHA256:scope.EligibleHistoricalSourceSHA256,
  FrozenSpecSHA256:scope.FrozenOptimizerSpecSHA256,
  OptimizerLineageHeadSHA256:scope.PolicyLineageHeadSHA256,
  PolicySHA256:scope.PolicySHA256,CandidateID:choice,
  CandidateCohortSHA256:cohort,
 }
 selection:=prospective.Selection{
  Schema:prospective.DecisionSchema,Lane:lane,Epoch:3,Tick:10,
  SourceCommitSHA:source,FrozenPreregSHA256:prereg,
  PolicySHA256:policy.ID(),PolicyLineageSHA256:scope.PolicyLineageHeadSHA256,
  ContextSHA256:hashFixture(lane+"/predecision-context"),
  Options:candidates,ChosenID:choice,ChosenCohortSHA256:cohort,
  MaxComputeUnits:125,LoggingMode:prospective.Observational,
 }
 key:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{13},32))
 raw,err:=json.Marshal(selection);if err!=nil{t.Fatal(err)}
 signature:=ed25519.Sign(key,append([]byte(prospective.DecisionDomain),raw...))
 pin:=prospective.IndependentPin{ExpectedSHA256:scopeHashFixture(raw),
  PublicKeyHex:hex.EncodeToString(key.Public().(ed25519.PublicKey))}
 return &setup{
  scope:scope,scopeSHA:scopeHash(scope),request:request,
  signed:prospective.SignedSelection{Selection:selection,SignatureHex:hex.EncodeToString(signature)},
  pin:pin,policy:policy,store:archive,backend:backend,identity:identity,
 }
}
func (s *setup)review()(Review,error){
 return ReviewAtAuthenticatedHead(context.Background(),s.backend,s.store,
  s.identity,s.signed,s.pin,s.policy,s.request,s.scope,s.scopeSHA)
}
func TestFSARealArchiveQualifiedPreregReadOnly(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  s:=makeFixture(t,lane)
  r,err:=s.review();if err!=nil{t.Fatal(err)}
  if r.Schema!=ReviewSchema||r.Mode!="FSA_REVIEW_ONLY_NO_CONSUMPTION"||
   !r.EligibilityForFSAReviewOnly||!r.SourceQualifiedInAuthenticatedArchive||
   !r.CohortUnstartedAtObservedHead||r.FSAHighwaterSequence!=3||
   r.ScientificAccepted||r.DispatchAuthorized||r.CohortReserved||
   r.FirstUseConsumed||r.ProtectedPhysicalIndependenceProven||
   r.OriginalEvidenceAudited||r.RandomizationAudited{
   t.Fatalf("FSA review authority drift: %+v",r)
  }
  if s.backend.calls!=2{t.Fatal("external highwater not read twice")}
  if after,err:=s.review();err!=nil||after.FrozenScopeSHA256!=r.FrozenScopeSHA256{
   t.Fatal("read-only, stable repeat observation denied:",err)
  }
  j,err:=s.store.Load();if err!=nil||len(j.Entries)!=3{t.Fatal("FSA archive was mutated")}
 }
}
func TestFSAFirstUseAndUnknownOutcomesNeverReplay(t *testing.T){
 s:=makeFixture(t,"Wingless")
 e:=researchlog.Event{Lane:s.scope.Lane,Generation:s.scope.Generation,
  ExperimentID:s.scope.ExperimentID,Kind:researchlog.PrimaryStarted,
  SourceCommitSHA:s.scope.SourceCommitSHA,
  PreregSHA256:s.scope.PreregSHA256,CohortSHA256:s.scope.CandidateCohortSHA256,
  WitnessSHA256:s.scope.SourceQualificationWitnessSHA256,RunID:5678}
 row,err:=s.store.AppendEvent(e);if err!=nil{t.Fatal(err)}
 s.backend.anchor.Sequence=row.Sequence
 s.backend.anchor.HeadSHA256=row.RecordSHA256
 if _,err=s.review();!errors.Is(err,ErrConsumed){t.Fatal("already consumed original admissible:",err)}
}
func TestFSAExternalAnchorAndForkOrOutageFailClosed(t *testing.T){
 s:=makeFixture(t,"Yggdrasil")
 s.backend.unavailable=true
 if _,err:=s.review();err==nil{t.Fatal("independent FSA outage admitted")}
 s.backend.unavailable=false
 s.backend.swapAfterFirst=true
 if _,err:=s.review();err==nil{t.Fatal("mid-recovery head change admitted")}
 s.backend.swapAfterFirst=false;s.backend.calls=0
 s.backend.anchor.HeadSHA256=hashFixture("forged_external_highwater")
 if _,err:=s.review();err==nil{t.Fatal("FSA anchored fork/rollback admitted")}
}
func TestFSAOptimizerCannotCreatePrivilegesOrWidenFrozenBudget(t *testing.T){
 s:=makeFixture(t,"Wingless")
 s.request.DispatchAuthorized=true
 if _,err:=s.review();err==nil{t.Fatal("optimizer escalated FSA dispatch")}
 s=makeFixture(t,"Wingless")
 s.scope.MaxComputeUnits++
 s.scopeSHA=scopeHash(s.scope)
 if _,err:=s.review();err==nil{t.Fatal("externally frozen original budget drift accepted")}
 s=makeFixture(t,"Wingless")
 s.request.PolicySHA256=hashFixture("unrelated_policy")
 if _,err:=s.review();err==nil{t.Fatal("policy identity substituted")}
 s=makeFixture(t,"Wingless")
 s.signed.Selection.ChosenID="candidateB"
 if _,err:=s.review();err==nil{t.Fatal("changed signed choice accepted")}
}
func TestFSAUnsupportedFreshExperimentDoesNotInheritAnotherLane(t *testing.T){
 s:=makeFixture(t,"Yggdrasil")
 s.scope.Lane="Wingless"
 s.scopeSHA=scopeHash(s.scope)
 if _,err:=s.review();err==nil{t.Fatal("cross-lane scope admitted")}
 s=makeFixture(t,"Yggdrasil")
 s.scope.ExperimentID="differentExperiment"
 s.scopeSHA=scopeHash(s.scope)
 if _,err:=s.review();err==nil{t.Fatal("missing prereg source accepted")}
}
func TestFSASourceRepairRevokesOldReadOnlyEligibility(t *testing.T){
 s:=makeFixture(t,"Wingless")
 e:=researchlog.Event{Lane:s.scope.Lane,Generation:s.scope.Generation,
  ExperimentID:s.scope.ExperimentID,Kind:researchlog.SourceRepair,
  SourceCommitSHA:s.scope.SourceCommitSHA,
  PreregSHA256:s.scope.PreregSHA256,CohortSHA256:s.scope.CandidateCohortSHA256,
  WitnessSHA256:s.scope.SourceQualificationWitnessSHA256}
 row,err:=s.store.AppendEvent(e);if err!=nil{t.Fatal(err)}
 s.backend.anchor.Sequence=row.Sequence
 s.backend.anchor.HeadSHA256=row.RecordSHA256
 if _,err=s.review();err==nil{t.Fatal("source-repair old certificate accepted")}
}
func TestFSABothLaneReviewIndependence(t *testing.T){
 left:=makeFixture(t,"Wingless")
 right:=makeFixture(t,"Yggdrasil")
 for _,s:=range []*setup{left,right}{
  if _,err:=s.review();err!=nil{t.Fatal(err)}
 }
 if left.scope.CandidateCohortSHA256==right.scope.CandidateCohortSHA256{
  t.Fatal("fixture cross lane cohort collision")
 }
}
func TestFSANoWriterOrExternalServiceProvisioned(t *testing.T){
 s:=makeFixture(t,"Wingless")
 if _,err:=s.review();err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Join(t.TempDir(),"runtime-dispatch"));!os.IsNotExist(err){
  t.Fatal("unexpected worker output")
 }
}
