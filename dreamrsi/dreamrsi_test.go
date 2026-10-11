package dreamrsi

import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "reflect"
 "strings"
 "sync"
 "testing"
)

func signedFixture(t *testing.T,lane string,start,n int)(Envelope,TrustPin,Verified){
 t.Helper()
 seed:=make([]byte,32)
 copy(seed,[]byte("DREAMRSI_FIXTURE_KEY_NOT_FOR_REAL"))
 private:=ed25519.NewKeyFromSeed(seed)
 public:=private.Public().(ed25519.PublicKey)
 history:=History{Schema:HistorySchema,Lane:lane,Epoch:1}
 for i:=0;i<n;i++{
  tick:=uint64(start+i)
  d:=Decision{
   Tick:tick,ContextSHA256:hash([]byte(fmt.Sprintf("context/%s/%d",lane,tick))),
   SourceCommitSHA:strings.Repeat("a",40),
   ReceiptSHA256:hash([]byte(fmt.Sprintf("receipt/%s/%d",lane,tick))),
   LoggingMode:Randomized,LoggedActionProbabilityBP:3333,
   RandomizationProofSHA256:hash([]byte("fixture-only-randomized-logging")),
  }
  for j:=0;j<3;j++{
   o:=Option{
    ID:fmt.Sprintf("C%d",j),
    CohortSHA256:hash([]byte(fmt.Sprintf("cohort/%s/%d/%d",lane,tick,j))),
    Family:fmt.Sprintf("family%d",j),
    Impact:20+(i*7+j*23)%80,
    Novelty:20+(i*13+j*31)%75,
    Robustness:10+(i*5+j*9)%85,
    Diversity:10+(i*3+j*17)%85,
    EstimatedCost:15+(i*5+j*11)%70,
    Risk:10+(i*7+j*19)%75,
   }
   d.Options=append(d.Options,o)
  }
  chosen:=(i*17+start)%3
  d.ChosenID=d.Options[chosen].ID
  d.ChosenCohortSHA256=d.Options[chosen].CohortSHA256
  d.ComputeUnits=d.Options[chosen].EstimatedCost+10
  sum:=d.Options[chosen].Impact+d.Options[chosen].Novelty-
   d.Options[chosen].EstimatedCost
  switch{
  case i%19==0:d.Outcome="INVALID"
  case i%23==0:d.Outcome="CONSUMED_INDETERMINATE"
  case sum>110:d.Outcome="SUPPORTED"
  case sum>70:d.Outcome="MIXED"
  default:d.Outcome="NEGATIVE"
  }
  history.Decisions=append(history.Decisions,d)
 }
 raw,err:=json.Marshal(history);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(private,append([]byte(AttestationDomain),raw...))
 env:=Envelope{History:history,SignatureHex:hex.EncodeToString(sig)}
 pin:=TrustPin{ExpectedHistorySHA256:hash(raw),IndependentEd25519PublicKeyHex:hex.EncodeToString(public)}
 verified,err:=VerifyEnvelope(env,pin);if err!=nil{t.Fatal(err)}
 return env,pin,verified
}
func TestSignedHistoryAndIndependentPins(t *testing.T){
 env,pin,h:=signedFixture(t,"Wingless",1,60)
 if h.Lane!="Wingless"||len(h.Decisions)!=60{t.Fatal("signed source not verified")}
 bad:=env
 bad.History.Decisions=append([]Decision(nil),env.History.Decisions...)
 bad.History.Decisions[0].Outcome="SUPPORTED"
 if _,err:=VerifyEnvelope(bad,pin);err==nil{t.Fatal("tampered outcome accepted")}
 bad=env
 bad.SignatureHex=strings.Repeat("0",128)
 if _,err:=VerifyEnvelope(bad,pin);err==nil{t.Fatal("forged signature accepted")}
 p:=pin;p.ExpectedHistorySHA256=hash([]byte("unrelated"))
 if _,err:=VerifyEnvelope(env,p);err==nil{t.Fatal("untrusted pin accepted")}
 // Signed mode must not suppress a prior negative or an invalid outcome.
 hasInvalid:=false;hasNegative:=false
 for _,d:=range h.Decisions{
  hasInvalid=hasInvalid||d.Outcome=="INVALID"
  hasNegative=hasNegative||d.Outcome=="NEGATIVE"
 }
 if !hasInvalid||!hasNegative{t.Fatal("historical negatives omitted")}
}
func TestMissingCounterfactualNeverFabricated(t *testing.T){
 _,_,h:=signedFixture(t,"Wingless",1,60)
 p:=BasePolicies("Wingless",41)[0]
 r,err:=Evaluate(p,h,4,1000);if err!=nil{t.Fatal(err)}
 if r.UnsupportedCounterfactuals+r.Matched!=r.Records||r.Records!=60||
  !r.RandomizationAuditRequired||r.Supported+r.Mixed+r.Negative+r.Invalid+r.Indeterminate!=r.Records{
  t.Fatalf("unsupported actions improperly completed %+v",r)
 }
 obs:=h
 obs.Decisions=append([]Decision(nil),h.Decisions...)
 for i:=range obs.Decisions{
  obs.Decisions[i].LoggingMode=Observational
  obs.Decisions[i].LoggedActionProbabilityBP=0
  obs.Decisions[i].RandomizationProofSHA256=""
 }
 observed,err:=Evaluate(p,obs,4,1000)
 if err!=nil||!observed.ObservationalOnly||observed.CanCompare||
  observed.EstimatedQuality!=0||observed.GainPerCompute!=0{
  t.Fatalf("nonrandom history promoted %+v %v",observed,err)
 }
}
func TestSelectionCannotSeeOutcome(t *testing.T){
 _,_,h:=signedFixture(t,"Yggdrasil",1,64)
 p:=BasePolicies("Yggdrasil",123)[0]
 first:=h.Decisions[0]
 a,_:=Select(p,first)
 first.Outcome="INVALID"
 first.ChosenID="C2"
 first.ComputeUnits=9999
 b,_:=Select(p,first)
 if a!=b{t.Fatal("hindsight outcome changed exploration choice")}
}
func frozen(t *testing.T,lane string)(Verified,Verified,FrozenSpec,string){
 t.Helper()
 _,_,tr:=signedFixture(t,lane,1,90)
 _,_,va:=signedFixture(t,lane,110,90)
 spec:=FrozenSpec{Schema:SpecSchema,Lane:lane,Epoch:1,
  TrainHistorySHA256:tr.HistorySHA256,ValidationHistorySHA256:va.HistorySHA256,
  TrainUntilTick:90,ValidateFromTick:110,MaxGenerations:4,Population:8,
  MutationsPerGeneration:24,MaxEvaluations:128,MaxReplayDecisions:15000,
  MinEffectiveSampleSize:4,MinMatchBP:1000,Seed:412021}
 b,_:=json.Marshal(spec)
 return tr,va,spec,hash(b)
}
func TestOptimizeDeterminismBudgetAndBaselines(t *testing.T){
 tr,va,spec,pin:=frozen(t,"Wingless")
 a,err:=Optimize(tr,va,spec,pin);if err!=nil{t.Fatal(err)}
 b,err:=Optimize(tr,va,spec,pin);if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(a,b){t.Fatal("policy evolution nondeterministic")}
 if len(a.Baselines)!=4||a.EvaluationsUsed>spec.MaxEvaluations||
  a.DecisionReplaysUsed>spec.MaxReplayDecisions||
  a.ScientificAccepted||a.DispatchAuthorized||a.ImprovementEstablished{
  t.Fatalf("budget or authority escalation %+v",a)
 }
 if ValidateOptimization(a)!=nil||len(a.Records)<4{
  t.Fatal("invalid policy lineage")
 }
 // An altered split or threshold is not silently optimized against.
 spec.Seed++
 if _,err=Optimize(tr,va,spec,pin);err==nil{t.Fatal("frozen seed drift accepted")}
}
func TestTemporalHoldoutAndCohortNonReuse(t *testing.T){
 tr,va,spec,pin:=frozen(t,"Yggdrasil")
 if VerifySpec(spec,pin,tr,va)!=nil{t.Fatal("genuine train/validation rejected")}
 _,_,held:=signedFixture(t,"Yggdrasil",220,48)
 if err:=VerifyTemporalHoldout(tr,va,held,200);err!=nil{t.Fatal(err)}
 if err:=VerifyTemporalHoldout(tr,va,held,240);err==nil{
  t.Fatal("overlapping holdout time accepted")
 }
 shuffled:=va;shuffled.Decisions=append([]Decision(nil),va.Decisions...)
 shuffled.Decisions[0].ChosenCohortSHA256=tr.Decisions[0].ChosenCohortSHA256
 if err:=VerifySpec(spec,pin,tr,shuffled);err==nil{t.Fatal("cohort overlap accepted")}
}
func TestLineageRestartTamperAndConcurrentCollision(t *testing.T){
 tr,va,spec,pin:=frozen(t,"Wingless")
 o,err:=Optimize(tr,va,spec,pin);if err!=nil{t.Fatal(err)}
 dir:=filepath.Join(t.TempDir(),"lineage")
 if err=PersistLineage(dir,o.Records,"Wingless");err!=nil{t.Fatal(err)}
 if err=PersistLineage(dir,o.Records,"Wingless");err!=nil{t.Fatal("idempotent restart:",err)}
 got,err:=ReadLineage(dir,"Wingless")
 if err!=nil||len(got)!=len(o.Records){t.Fatal("restart lost records",err)}
 copyRec:=append([]PolicyRecord(nil),o.Records...)
 copyRec[0].Policy.Weights[0]++
 if err=PersistLineage(dir,copyRec,"Wingless");err==nil{t.Fatal("replaced accepted record")}
 first:=filepath.Join(dir,"000001.json")
 if err=os.WriteFile(first,[]byte("{"),0600);err!=nil{t.Fatal(err)}
 if err=PersistLineage(dir,o.Records,"Wingless");err==nil{t.Fatal("torn record silently replayed")}
 // A new sequence can only be exclusively created, never overwritten.
 other:=filepath.Join(t.TempDir(),"concurrent")
 var wg sync.WaitGroup
 errs:=make(chan error,2)
 for i:=0;i<2;i++{wg.Add(1);go func(){defer wg.Done();errs<-PersistLineage(other,o.Records,"Wingless")}()}
 wg.Wait();close(errs)
 // Under contention, either one may fail closed; at least one must leave
 // a valid exact chain. There must never be a divergent accepted record.
 valid,err:=ReadLineage(other,"Wingless")
 if err!=nil||len(valid)!=len(o.Records){t.Fatal("concurrency created torn lineage",err)}
}
func TestFSAOnlyProposalDoesNotBecomeAuthority(t *testing.T){
 tr,va,spec,pin:=frozen(t,"Wingless")
 result,err:=Optimize(tr,va,spec,pin);if err!=nil{t.Fatal(err)}
 if !result.QualifiedForProspectiveTest{
  t.Skip("fixture sample insufficient for FSA proposal; no forced qualification")
 }
 req,err:=ProposeSelection(result,va.Decisions[0]);if err!=nil{t.Fatal(err)}
 if err=ValidateFSARequest(req);err!=nil{t.Fatal(err)}
 req.DispatchAuthorized=true
 if err=ValidateFSARequest(req);err==nil{t.Fatal("optimizer self-promotion accepted")}
}
func BenchmarkReplaySyntheticFixture(b *testing.B){
 // No primary experiment execution: bounded signed fixture only.
 t:=&testing.T{}
 _,_,h:=signedFixture(t,"Wingless",1,120)
 p:=BasePolicies("Wingless",41)[0]
 b.ResetTimer()
 for i:=0;i<b.N;i++{
  if _,err:=Evaluate(p,h,4,1000);err!=nil{b.Fatal(err)}
 }
}


func TestSyntheticBaselineComparisonReport(t *testing.T){
 names:=[]string{"portfolio","balanced","fixed","deterministic-uniform"}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  tr,va,spec,pin:=frozen(t,lane)
  result,err:=Optimize(tr,va,spec,pin);if err!=nil{t.Fatal(err)}
  t.Logf("FIXTURE lane=%s policies=%d evaluations=%d replay_ops=%d improvement_claim=false",lane,len(result.Records),result.EvaluationsUsed,result.DecisionReplaysUsed)
  for i,b:=range result.Baselines{
   t.Logf("FIXTURE baseline=%s lane=%s ips_quality=%.6f ips_compute=%.6f gain_per_compute=%.6f ci95=[%.6f,%.6f] coverage=%d/%d ess=%.3f unsupported=%d comparable=%t",
    names[i],lane,b.EstimatedQuality,b.EstimatedCompute,b.GainPerCompute,
    b.CI95Low,b.CI95High,b.Matched,b.Records,b.EffectiveSampleSize,
    b.UnsupportedCounterfactuals,b.CanCompare)
  }
  s:=result.SelectedValidation
  t.Logf("FIXTURE selected lane=%s policy=%s ips_quality=%.6f ips_compute=%.6f gain_per_compute=%.6f ci95=[%.6f,%.6f] coverage=%d/%d ess=%.3f comparable=%t accepted=false",
   lane,result.SelectedPolicySHA256,s.EstimatedQuality,s.EstimatedCompute,
   s.GainPerCompute,s.CI95Low,s.CI95High,s.Matched,s.Records,
   s.EffectiveSampleSize,s.CanCompare)
 }
}
