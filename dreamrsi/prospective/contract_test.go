package prospective

import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/dreamrsi"
)

func testSigner(marker byte) ed25519.PrivateKey {
 seed:=bytes.Repeat([]byte{marker},32)
 return ed25519.NewKeyFromSeed(seed)
}
func sign(data any, private ed25519.PrivateKey,domain string)(string,IndependentPin) {
 raw,_:=json.Marshal(data)
 signature:=ed25519.Sign(private,append([]byte(domain),raw...))
 return hex.EncodeToString(signature),IndependentPin{
  ExpectedSHA256:hash(raw),
  PublicKeyHex:hex.EncodeToString(private.Public().(ed25519.PublicKey)),
 }
}
func fixture(lane, outcome string,tick uint64)(SignedSelection,IndependentPin,dreamrsi.Policy,SignedOriginal,IndependentPin){
 p:=dreamrsi.BasePolicies(lane,511)[0]
 options:=[]dreamrsi.Option{}
 for i:=0;i<3;i++ {
  id:=string(rune('A'+i))
  options=append(options,dreamrsi.Option{
   ID:id,Family:"family"+id,CohortSHA256:hash([]byte(lane+id+string(rune(tick+50)))),
   Impact:15+i*22,Novelty:30+i*13,Robustness:60,Diversity:55,
   EstimatedCost:25+i*12,Risk:2+i,
  })
 }
 d:=Selection{
  Schema:DecisionSchema,Lane:lane,Epoch:1,Tick:tick,
  SourceCommitSHA:strings.Repeat("a",40),
  FrozenPreregSHA256:hash([]byte("frozen_prereg_"+lane)),
  PolicySHA256:p.ID(),PolicyLineageSHA256:hash([]byte("qualified_policy_lineage_"+lane)),
  ContextSHA256:hash([]byte("predecision_context_"+lane+string(rune(tick+50)))),
  Options:options,MaxComputeUnits:130,LoggingMode:Observational,
 }
 id,_:=dreamrsi.Select(p,dreamrsi.Decision{Options:options,ContextSHA256:d.ContextSHA256})
 d.ChosenID=id
 for _,option:=range options{if option.ID==id{d.ChosenCohortSHA256=option.CohortSHA256}}
 sig,pin:=sign(d,testSigner(41),DecisionDomain)
 signed:=SignedSelection{Selection:d,SignatureHex:sig}
 raw:=OriginalLink{
  Schema:ResultSchema,Lane:lane,Epoch:1,Tick:tick,
  PredecisionSHA256:pin.ExpectedSHA256,
  SourceCommitSHA:d.SourceCommitSHA,FrozenPreregSHA256:d.FrozenPreregSHA256,
  ChosenID:id,ConsumedCohortSHA256:d.ChosenCohortSHA256,
  RunID:"Original_38128621982",RunAttempt:1,
  StartedSHA256:hash([]byte("original_started_"+lane)),
  RawSHA256:hash([]byte("raw_science_"+lane)),
  DispositionSHA256:hash([]byte("classified_"+lane)),
  Outcome:outcome,ActualComputeUnits:80,
 }
 resSig,resPin:=sign(raw,testSigner(98),ResultDomain)
 return signed,pin,p,SignedOriginal{Original:raw,SignatureHex:resSig},resPin
}
func verifyPair(t *testing.T,lane,outcome string,tick uint64)(VerifiedSelection,VerifiedOriginal,Observation) {
 t.Helper()
 d,pin,p,r,rawPin:=fixture(lane,outcome,tick)
 before,err:=VerifySelection(d,pin,p);if err!=nil{t.Fatal(err)}
 after,err:=VerifyOriginal(r,rawPin);if err!=nil{t.Fatal(err)}
 observation,err:=Join(before,after);if err!=nil{t.Fatal(err)}
 return before,after,observation
}
func TestSignedDecisionToHistoricalObservationCannotSelfAuthorize(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  for i,outcome:=range []string{"SUPPORTED","MIXED","NEGATIVE","INVALID","CONSUMED_INDETERMINATE"}{
   before,after,observation:=verifyPair(t,lane,outcome,uint64(i+1))
   if observation.ScientificAccepted||observation.DispatchAuthorized||
    observation.AcceptedRefMutation||observation.EligibleForCausalPolicyReplay||
    observation.RandomizationIndependentlyAudited||
    observation.TemporalPredecisionOrderIndependentlyAttested||
    observation.OriginalScientificEvidenceIndependentlyAudited{
    t.Fatal("signed data granted FSA authority")
   }
   converted,err:=ToObservationalDecision(before,after)
   if err!=nil||converted.Outcome!=outcome||converted.LoggingMode!=dreamrsi.Observational||
    converted.LoggedActionProbabilityBP!=0||converted.RandomizationProofSHA256!=""{
    t.Fatalf("fabricated randomized outcomes: %+v %v",converted,err)
   }
  }
 }
}
func TestNoMutationOfSignedContents(t *testing.T){
 d,pin,p,r,rawPin:=fixture("Wingless","NEGATIVE",1)
 original,err:=VerifySelection(d,pin,p);if err!=nil{t.Fatal(err)}
 observed,err:=VerifyOriginal(r,rawPin);if err!=nil{t.Fatal(err)}
 d.Selection.Options[0].Impact++
 if _,err=VerifySelection(d,pin,p);err==nil{t.Fatal("tampered decision signature allowed")}
 original.Selection.Options[0].Impact++
 if _,err=Join(original,observed);err==nil{t.Fatal("postverification decision mutation allowed")}
 observed.Original.Outcome="SUPPORTED"
 if _,err=Join(original,observed);err==nil{t.Fatal("postverification result mutation allowed")}
 _=rawPin
}
func TestDistinctSignersAndNoResultOrCostRewriting(t *testing.T){
 d,pin,p,r,rpin:=fixture("Yggdrasil","MIXED",3)
 pre,err:=VerifySelection(d,pin,p);if err!=nil{t.Fatal(err)}
 after,err:=VerifyOriginal(r,rpin);if err!=nil{t.Fatal(err)}
 after.Original.ActualComputeUnits=200
 if _,err=Join(pre,after);err==nil{t.Fatal("postverify compute cost rewrite accepted")}
 r.Original.ActualComputeUnits=150
 r.SignatureHex,rpin=sign(r.Original,testSigner(98),ResultDomain)
 after,err=VerifyOriginal(r,rpin);if err!=nil{t.Fatal(err)}
 if _,err=Join(pre,after);err==nil{t.Fatal("budget overrun accepted")}
 r.Original.ActualComputeUnits=80
 r.Original.ConsumedCohortSHA256=hash([]byte("wrong cohort"))
 r.SignatureHex,rpin=sign(r.Original,testSigner(98),ResultDomain)
 after,err=VerifyOriginal(r,rpin);if err!=nil{t.Fatal(err)}
 if _,err=Join(pre,after);err==nil{t.Fatal("cohort substitution accepted")}
 r.Original.ConsumedCohortSHA256=d.Selection.ChosenCohortSHA256
 r.SignatureHex,rpin=sign(r.Original,testSigner(41),ResultDomain)
 after,err=VerifyOriginal(r,rpin);if err!=nil{t.Fatal(err)}
 if _,err=Join(pre,after);err==nil{t.Fatal("same pre/post signer accepted")}
}
func TestRandomizedLoggingRemainsUnauditedAndCannotLeakIPS(t *testing.T){
 d,_,p,r,_:=fixture("Wingless","SUPPORTED",5)
 d.Selection.LoggingMode=RandomizedUnaudited
 d.Selection.AssignedProbabilitiesBP=map[string]int{"A":2000,"B":3000,"C":5000}
 d.Selection.RandomnessCommitSHA256=hash([]byte("external_frozen_nonce_commitment"))
 d.SignatureHex,pin:=sign(d.Selection,testSigner(41),DecisionDomain)
 pre,err:=VerifySelection(d,pin,p);if err!=nil{t.Fatal(err)}
 r.Original.PredecisionSHA256=pin.ExpectedSHA256
 r.SignatureHex,rpin:=sign(r.Original,testSigner(98),ResultDomain)
 after,err:=VerifyOriginal(r,rpin);if err!=nil{t.Fatal(err)}
 obs,err:=Join(pre,after);if err!=nil{t.Fatal(err)}
 if obs.RandomizationIndependentlyAudited||obs.EligibleForCausalPolicyReplay{t.Fatal("unaudited randomness promoted")}
 historical,err:=ToObservationalDecision(pre,after)
 if err!=nil||historical.LoggingMode!=dreamrsi.Observational{t.Fatal("unaudited propensity used")}
 d.Selection.AssignedProbabilitiesBP["A"]=1000
 d.SignatureHex,pin=sign(d.Selection,testSigner(41),DecisionDomain)
 if _,err=VerifySelection(d,pin,p);err==nil{t.Fatal("invalid probability simplex allowed")}
}
func TestChronologicalLaneAndIndependentCohortProtection(t *testing.T){
 _,_,a:=verifyPair(t,"Wingless","SUPPORTED",1)
 _,_,b:=verifyPair(t,"Wingless","NEGATIVE",2)
 _,_,y:=verifyPair(t,"Yggdrasil","INVALID",1)
 if err:=VerifyChronologicalLane([]Observation{a,b},"Wingless");err!=nil{t.Fatal(err)}
 if err:=CompareLaneIsolation([]Observation{a,b},[]Observation{y});err!=nil{t.Fatal(err)}
 if err:=VerifyChronologicalLane([]Observation{b,a},"Wingless");err==nil{t.Fatal("temporal inversion")}
 if err:=VerifyChronologicalLane([]Observation{a,a},"Wingless");err==nil{t.Fatal("duplicate original")}
 y.ConsumedCohortSHA256=a.ConsumedCohortSHA256
 if err:=CompareLaneIsolation([]Observation{a},[]Observation{y});err==nil{t.Fatal("cross-lane cohort reuse")}
}
func TestExclusiveLocalObservationAndUnsafeInput(t *testing.T){
 _,_,obs:=verifyPair(t,"Wingless","MIXED",9)
 path:=filepath.Join(t.TempDir(),"observation.json")
 if err:=PersistOnce(path,obs);err!=nil{t.Fatal(err)}
 if err:=PersistOnce(path,obs);err==nil{t.Fatal("second first-use write accepted")}
 raw,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 var read Observation
 if err=json.Unmarshal(raw,&read);err!=nil||read.PredecisionSHA256!=obs.PredecisionSHA256{t.Fatal("original record lost")}
 if _,err:=ParseSignedSelection([]byte("{}{}"));err==nil{t.Fatal("concatenated JSON")}
 if _,err:=ParseSignedOriginal([]byte("{"));err==nil{t.Fatal("malformed JSON")}
 if err:=PersistOnce("relative.json",obs);err==nil{t.Fatal("relative write accepted")}
}
func TestConcurrentOEXCLPreventsDuplicateWriting(t *testing.T){
 _,_,obs:=verifyPair(t,"Wingless","MIXED",12)
 path:=filepath.Join(t.TempDir(),"once.json")
 ch:=make(chan error,2);var wg sync.WaitGroup
 for i:=0;i<2;i++{wg.Add(1);go func(){defer wg.Done();ch<-PersistOnce(path,obs)}()}
 wg.Wait();close(ch)
 success,failure:=0,0
 for err:=range ch {if err==nil{success++}else{failure++}}
 if success!=1||failure!=1{t.Fatal("duplicate first-use local records")}
}
func BenchmarkDecisionVerifyJoin(b *testing.B){
 d,pin,p,r,rpin:=fixture("Wingless","MIXED",1)
 b.ResetTimer()
 for i:=0;i<b.N;i++{
  before,e:=VerifySelection(d,pin,p);if e!=nil{b.Fatal(e)}
  after,e:=VerifyOriginal(r,rpin);if e!=nil{b.Fatal(e)}
  if _,e=Join(before,after);e!=nil{b.Fatal(e)}
 }
}
