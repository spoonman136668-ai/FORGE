package fsaservice

import (
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/workerfence"
 "github.com/spoonman136668-ai/forge/workerlease"
)

type syntheticStepLedger struct{
 mu sync.Mutex
 key ed25519.PrivateKey
 seen map[string]bool
 writes int
 failAfterCommit bool
 badSignature bool
 afterCommit func()
}
func(s *syntheticStepLedger)ConsumeOnce(_ context.Context,c workerfence.StepClaim)(workerfence.SignedStepReceipt,error){
 s.mu.Lock()
 id:=c.Lane+":"+c.OriginalID+":"+c.StepSHA256
 if s.seen[id]{
  s.mu.Unlock()
  return workerfence.SignedStepReceipt{},errors.New("SYNTHETIC_STEP_ALREADY_CONSUMED")
 }
 s.seen[id]=true
 s.writes++
 r:=workerfence.SignedStepReceipt{Schema:workerfence.StepReceiptSchema,Claim:c,Status:workerfence.Consumed}
 raw,_:=json.Marshal(r)
 r.SignatureHex=hex.EncodeToString(ed25519.Sign(s.key,append([]byte(workerfence.StepReceiptDomain),raw...)))
 if s.badSignature{r.SignatureHex=strings.Repeat("0",128)}
 hook:=s.afterCommit
 ambiguous:=s.failAfterCommit
 s.mu.Unlock()
 if hook!=nil{hook()}
 if ambiguous{return workerfence.SignedStepReceipt{},errors.New("SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT")}
 return r,nil
}
func newStepFixture(t *testing.T,lane string)(*gateFixture,*syntheticStepLedger,ed25519.PublicKey,workerlease.Lease){
 t.Helper()
 f:=newGateFixture(t,false)
 pub,key:=testKey(t)
 ledger:=&syntheticStepLedger{key:key,seen:map[string]bool{}}
 lease:=workerlease.Lease{Lane:lane,ExperimentID:"original_step_1",
  IntentSHA256:strings.Repeat("d",64),OwnerID:"FORGE_SYNTHETIC_FSA",
  OwnerEpoch:f.anchor.AuthorityEpoch,WorkerID:"synthetic_worker",
  LeaseSequence:1,ExpiresAtUnix:2000}
 return f,ledger,pub,lease
}
func consumeStep(f *gateFixture,s *syntheticStepLedger,pub ed25519.PublicKey,l workerlease.Lease)(
 workerfence.StepObservation,error){
 return workerfence.InspectStep(context.Background(),f.remote,f.anchor,l,1000,
  strings.Repeat("e",64),strings.Repeat("f",64),s,pub)
}
func TestAuthenticatedOneShotWorkerStepConsumptionAcrossExistingLanes(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   f,ledger,pub,lease:=newStepFixture(t,lane)
   observed,err:=consumeStep(f,ledger,pub,lease)
   if err!=nil||!observed.ConsumptionObserved||observed.WorkerDispatchAuthorized||
    observed.ScientificExecutionAuthorized||observed.FirstUseReplayAuthorized||
    observed.AuthorityEpoch!=lease.OwnerEpoch{
    t.Fatal("unsafe step observation",observed,err)
   }
   if ledger.writes!=1{t.Fatal("lost synthetic step custody")}
   if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepIndeterminate){
    t.Fatal("repeated one-shot step accepted",err)
   }
   if ledger.writes!=1{t.Fatal("duplicate step committed")}
  })
 }
}
func TestWorkerStepDeniesStaleRevokedAndUnsafeLeases(t *testing.T){
 for _,testCase:=range []struct{name string;mutate func(*workerlease.Lease)}{
  {"first use ambiguity",func(l *workerlease.Lease){l.FirstUseRisk=true}},
  {"stale epoch",func(l *workerlease.Lease){l.OwnerEpoch++}},
  {"expired",func(l *workerlease.Lease){l.ExpiresAtUnix=900}},
  {"missing worker",func(l *workerlease.Lease){l.WorkerID=""}},
  {"missing intent",func(l *workerlease.Lease){l.IntentSHA256=""}},
 }{
  t.Run(testCase.name,func(t *testing.T){
   f,ledger,pub,lease:=newStepFixture(t,"Wingless")
   testCase.mutate(&lease)
   if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepBlocked){
    t.Fatal("unsafe worker reached one-shot authority",err)
   }
   if ledger.writes!=0{t.Fatal("invalid lease consumed step")}
  })
 }
}
func TestWorkerStepAmbiguousReceiptOrLostRemoteWitnessNeverAuthorizes(t *testing.T){
 t.Run("lost acknowledgement",func(t *testing.T){
  f,ledger,pub,lease:=newStepFixture(t,"Wingless")
  ledger.failAfterCommit=true
  if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepIndeterminate){
   t.Fatal("lost response became success",err)
  }
  ledger.failAfterCommit=false
  if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepIndeterminate){
   t.Fatal("ambiguous step retried",err)
  }
  if ledger.writes!=1{t.Fatal("ambiguous step duplicated")}
 })
 t.Run("untrusted signer",func(t *testing.T){
  f,ledger,pub,lease:=newStepFixture(t,"Yggdrasil")
  ledger.badSignature=true
  if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepIndeterminate){
   t.Fatal("forged consumed receipt trusted",err)
  }
  if ledger.writes!=1{t.Fatal("expected single disputed claim")}
 })
 t.Run("authority drift during consumption",func(t *testing.T){
  f,ledger,pub,lease:=newStepFixture(t,"Wingless")
  next:=f.anchor;next.Sequence=1;next.HeadSHA256=strings.Repeat("c",64)
  ledger.afterCommit=func(){
   ok,err:=f.checkpoint.store.CompareAndSwap(context.Background(),f.anchor,next)
   if err!=nil||!ok{t.Fatal("synthetic authority mutation",err)}
  }
  if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepIndeterminate){
   t.Fatal("authority drift after consumption admitted",err)
  }
  if ledger.writes!=1{t.Fatal("step duplicated during epoch uncertainty")}
 })
 t.Run("missing remote",func(t *testing.T){
  f,ledger,pub,lease:=newStepFixture(t,"Wingless")
  f.remote=nil
  if _,err:=consumeStep(f,ledger,pub,lease);!errors.Is(err,workerfence.ErrStepBlocked){
   t.Fatal("no remote witness admitted",err)
  }
  if ledger.writes!=0{t.Fatal("no remote step consumed")}
 })
 t.Run("no independent receipt key",func(t *testing.T){
  f,ledger,_,lease:=newStepFixture(t,"Wingless")
  if _,err:=consumeStep(f,ledger,f.anchor.PublicKey,lease);!errors.Is(err,workerfence.ErrStepBlocked){
   t.Fatal("scientific archive key incorrectly reused as execution receipt key",err)
  }
 })
}
func TestWorkerStepConcurrentConsumersOnlyOneObserved(t *testing.T){
 f,ledger,pub,lease:=newStepFixture(t,"Yggdrasil")
 start:=make(chan struct{})
 var wg sync.WaitGroup
 out:=make(chan error,2)
 for i:=0;i<2;i++{wg.Add(1);go func(){
  defer wg.Done();<-start
  _,err:=consumeStep(f,ledger,pub,lease)
  out<-err
 }()}
 close(start);wg.Wait();close(out)
 success,denied:=0,0
 for err:=range out{if err==nil{success++}else if errors.Is(err,workerfence.ErrStepIndeterminate){denied++}else{t.Fatal(err)}}
 if success!=1||denied!=1||ledger.writes!=1{
  t.Fatalf("synthetic authority double consumed: success=%d denied=%d writes=%d",success,denied,ledger.writes)
 }
}
var _ fsahead.Anchor
