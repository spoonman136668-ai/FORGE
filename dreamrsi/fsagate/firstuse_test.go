package fsagate

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/researchlog"
)
type r5Authority struct{
 mu sync.Mutex
 current fsahead.Anchor
 archiveID string
 attempts int
 commits int
 denied bool
 ambiguous bool
 unavailable bool
}
func (f *r5Authority)ReadAnchor(context.Context)(fsahead.Anchor,error){
 f.mu.Lock();defer f.mu.Unlock()
 if f.unavailable{return fsahead.Anchor{},errors.New("synthetic floor unavailable")}
 a:=f.current
 a.PublicKey=append(ed25519.PublicKey(nil),a.PublicKey...)
 return a,nil
}
func (f *r5Authority)ConfirmArchiveBinding(_ context.Context,id string)(bool,error){
 f.mu.Lock();defer f.mu.Unlock()
 if f.unavailable{return false,errors.New("synthetic binding unavailable")}
 return id==f.archiveID,nil
}
func (f *r5Authority)CompareAndSwap(_ context.Context,prev,next fsahead.Anchor)(bool,error){
 f.mu.Lock();defer f.mu.Unlock()
 f.attempts++
 if f.unavailable{return false,errors.New("synthetic partition")}
 if f.denied||prev.Sequence!=f.current.Sequence||
  prev.HeadSHA256!=f.current.HeadSHA256{return false,nil}
 f.commits++
 f.current=next
 if f.ambiguous{return false,errors.New("CAS applied then timeout")}
 return true,nil
}
func r5Setup(t *testing.T,lane string)(*setup,*r5Authority,ed25519.PrivateKey){
 t.Helper()
 s:=makeFixture(t,lane)
 sk:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{19},32))
 pub:=append(ed25519.PublicKey(nil),sk.Public().(ed25519.PublicKey)...)
 s.identity.PublicKey=pub
 s.backend.anchor.PublicKey=pub
 a:=&r5Authority{current:s.backend.anchor,archiveID:s.identity.ArchiveID}
 return s,a,sk
}
func prepareR5(t *testing.T,s *setup,backend *r5Authority)(FirstUsePlan,string){
 t.Helper()
 p,err:=PrepareFirstUse(context.Background(),backend,s.store,
  s.identity,s.signed,s.pin,s.policy,s.request,s.scope,s.scopeSHA,
  hashFixture("immutable-FSA-STARTED-original-receipt"),76129)
 if err!=nil{t.Fatal(err)}
 sha,err:=PlanSHA(p)
 if err!=nil||sha==""{t.Fatal("invalid first-use plan:",err)}
 return p,sha
}
func signR5(t *testing.T,s *setup,sk ed25519.PrivateKey,p FirstUsePlan)fsahead.SignedHead{
 t.Helper()
 h:=fsahead.Payload{
  Schema:fsahead.Schema,Domain:fsahead.Domain,
  ArchiveID:s.identity.ArchiveID,KeyID:s.identity.KeyID,
  AuthorityEpoch:s.identity.AuthorityEpoch,
  ParentSequence:p.PreviousSequence,ParentHeadSHA256:p.PreviousHeadSHA256,
  Sequence:p.PlannedSequence,HeadSHA256:p.PlannedStartedRecordSHA256,
 }
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 msg:=append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),raw...)
 return fsahead.SignedHead{Payload:h,SignatureHex:hex.EncodeToString(ed25519.Sign(sk,msg))}
}
func TestFirstUsePlanRequiresExactR4EligibilityAndNoWrites(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  s,backend,_:=r5Setup(t,lane)
  p,sha:=prepareR5(t,s,backend)
  if p.Schema!=FirstUsePlanSchema||p.PlannedSequence!=4||
   p.PreviousSequence!=3||p.FSAFirstUseCommitted||
   p.ScientificAccepted||p.DispatchAuthorized||sha==""{
   t.Fatalf("bad nonexecuting first-use plan %+v",p)
  }
  j,err:=s.store.Load()
  if err!=nil||len(j.Entries)!=3{t.Fatal("planning consumed first use")}
  if backend.attempts!=0{t.Fatal("planning called remote CAS")}
  s.scope.MaxComputeUnits++
  if _,err:=PrepareFirstUse(context.Background(),backend,s.store,
   s.identity,s.signed,s.pin,s.policy,s.request,s.scope,scopeHash(s.scope),
   p.StartWitnessSHA256,76129);err==nil{
   t.Fatal("unsigned expanded budget admitted")
  }
 }
}
func TestFirstUseFSACommitProofAndNoReplay(t *testing.T){
 s,backend,sk:=r5Setup(t,"Wingless")
 p,sha:=prepareR5(t,s,backend)
 signed:=signR5(t,s,sk,p)
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed);
  !errors.Is(err,ErrFirstUseUncertain){t.Fatal("uncommitted intent claimed proof:",err)}
 row,err:=s.store.AppendEvent(EventForPlan(p));if err!=nil{t.Fatal(err)}
 if row.Sequence!=p.PlannedSequence||row.RecordSHA256!=p.PlannedStartedRecordSHA256{
  t.Fatal("FSA signer and independently written journal disagree")
 }
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed);err==nil{
  t.Fatal("unsigned external high-water accepted")
 }
 after,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed)
 if err!=nil||after.Sequence!=p.PlannedSequence||backend.commits!=1{
  t.Fatal("FSA external atomic CAS failed:",err)
 }
 proof,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed)
 if err!=nil{t.Fatal(err)}
 if !proof.FirstUseConsumed||!proof.FSAFirstUseCommitted||
  proof.PhysicalIndependenceDemonstrated||proof.ScientificAccepted||
  proof.DispatchAuthorized||proof.AcceptedRefMutation||
  proof.ObservedTrustedHeadSHA256!=p.PlannedStartedRecordSHA256{
  t.Fatalf("scientific authority leaked from FSA receipt %+v",proof)
 }
 if _,err:=PrepareFirstUse(context.Background(),backend,s.store,
  s.identity,s.signed,s.pin,s.policy,s.request,s.scope,s.scopeSHA,
  p.StartWitnessSHA256,p.RunID);err==nil{t.Fatal("consumed original planned a second time")}
 if _,err:=s.store.AppendEvent(EventForPlan(p));err==nil{t.Fatal("duplicate first-use written")}
 if _,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed);err==nil{
  t.Fatal("replayed checkpoint committed")
 }
 if backend.commits!=1{t.Fatal("multiple FSA first-use CAS commits")}
}
func TestIndeterminateFSACASReconcilesWithoutRetry(t *testing.T){
 s,backend,sk:=r5Setup(t,"Yggdrasil")
 p,sha:=prepareR5(t,s,backend)
 signed:=signR5(t,s,sk,p)
 if _,err:=s.store.AppendEvent(EventForPlan(p));err!=nil{t.Fatal(err)}
 backend.ambiguous=true
 if _,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed);
  !errors.Is(err,fsatrust.ErrCommitIndeterminate){t.Fatal("ambiguous remote CAS claimed success:",err)}
 if backend.attempts!=1||backend.commits!=1{t.Fatal("ambiguous CAS not simulated")}
 proof,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed)
 if err!=nil||!proof.FirstUseConsumed||proof.DispatchAuthorized{
  t.Fatal("reconciliation did not prove consumed state without dispatch:",err)
 }
 if backend.attempts!=1{t.Fatal("read-only proof retried CAS")}
 backend.unavailable=true
 if _,err=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed);
  !errors.Is(err,ErrFirstUseUncertain){t.Fatal("partition claimed trusted proof:",err)}
 if backend.attempts!=1{t.Fatal("partition triggered CAS replay")}
}
func TestUntrustedSignerStalePredecessorAndTamperedPlan(t *testing.T){
 s,backend,sk:=r5Setup(t,"Wingless")
 p,sha:=prepareR5(t,s,backend)
 signed:=signR5(t,s,sk,p)
 if _,err:=s.store.AppendEvent(EventForPlan(p));err!=nil{t.Fatal(err)}
 if _,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed);err!=nil{t.Fatal(err)}
 changed:=p;changed.RunID++
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,changed,sha,signed);err==nil{
  t.Fatal("modified first-use intent accepted")
 }
 rogue:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{20},32))
 forged:=signR5(t,s,rogue,p)
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,forged);err==nil{
  t.Fatal("different FSA signer accepted")
 }
 altered:=signed
 altered.Payload.ParentSequence--
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,altered);err==nil{
  t.Fatal("stale predecessor signature accepted")
 }
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,
  hashFixture("unrelated pinned plan"),signed);err==nil{
  t.Fatal("untrusted plan pin accepted")
 }
}
func TestRacingFirstUseCannotConsumeSameCohortTwice(t *testing.T){
 s,backend,sk:=r5Setup(t,"Yggdrasil")
 p,sha:=prepareR5(t,s,backend)
 signed:=signR5(t,s,sk,p)
 var wg sync.WaitGroup
 start:=make(chan struct{})
 errorsOut:=make(chan error,2)
 for i:=0;i<2;i++{
  wg.Add(1)
  go func(){defer wg.Done();<-start
   _,err:=s.store.AppendEvent(EventForPlan(p))
   errorsOut<-err
  }()
 }
 close(start);wg.Wait();close(errorsOut)
 success,denied:=0,0
 for err:=range errorsOut{if err==nil{success++}else{denied++}}
 if success!=1||denied!=1{t.Fatalf("first-use race: success=%d denied=%d",success,denied)}
 if _,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed);err!=nil{t.Fatal(err)}
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed);err!=nil{t.Fatal(err)}
 if backend.commits!=1{t.Fatal("FSA CAS raced twice")}
}
func TestFirstUseDenialLeavesConsumedLocalEvidenceAndNoDispatch(t *testing.T){
 s,backend,sk:=r5Setup(t,"Wingless")
 p,sha:=prepareR5(t,s,backend)
 signed:=signR5(t,s,sk,p)
 if _,err:=s.store.AppendEvent(EventForPlan(p));err!=nil{t.Fatal(err)}
 backend.denied=true
 if _,err:=fsatrust.Advance(context.Background(),backend,s.store,s.identity,signed);
  !errors.Is(err,fsatrust.ErrConflict){t.Fatal("denied FSA CAS granted first-use:",err)}
 if _,err:=ProveFSAFirstUse(context.Background(),backend,s.store,s.identity,p,sha,signed);
  !errors.Is(err,ErrFirstUseUncertain){t.Fatal("uncommitted started record claimed authority:",err)}
 if backend.commits!=0{t.Fatal("denied first-use committed")}
 if _,err:=s.store.AppendEvent(EventForPlan(p));err==nil{t.Fatal("denied CAS replayed local STARTED")}
}
func TestFirstUseClassificationCannotBeRetrofittedByPlan(t *testing.T){
 s,backend,_:=r5Setup(t,"Wingless")
 p,_:=prepareR5(t,s,backend)
 e:=EventForPlan(p)
 if e.Kind!=researchlog.PrimaryStarted||e.Outcome!=""||
  e.OriginalEvidenceSHA256!=""||e.RunID==0||
  e.CohortSHA256!=p.CohortSHA256{t.Fatal("planner forged post-outcome or preconsumed cohort")}
}
