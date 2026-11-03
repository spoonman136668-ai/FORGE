package optimizerbridge

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/promptlineage"
 "github.com/spoonman136668-ai/forge/thetaadapt"
 "github.com/spoonman136668-ai/forge/genenv"
)
func hx(s string)string{sum:=sha256.Sum256([]byte(s));return hex.EncodeToString(sum[:])}
func h40(r byte)string{return strings.Repeat(string(r),40)}
func signHistory(t *testing.T,lane string,start uint64,src string,private ed25519.PrivateKey)(dreamrsi.Envelope,string){
 t.Helper()
 h:=dreamrsi.History{Schema:dreamrsi.HistorySchema,Lane:lane,Epoch:1}
 for i:=0;i<64;i++{
  tick:=start+uint64(i)
  d:=dreamrsi.Decision{Tick:tick,ContextSHA256:hx(lane+"ctx"+string(rune(tick))),
    SourceCommitSHA:src,ReceiptSHA256:hx(lane+"receipt"+string(rune(tick))),
    LoggingMode:dreamrsi.Randomized,LoggedActionProbabilityBP:3333,
    RandomizationProofSHA256:hx(lane+"random-proof"+string(rune(tick))),
    ComputeUnits:25}
  for j:=0;j<3;j++{d.Options=append(d.Options,dreamrsi.Option{
    ID:[]string{"alpha","beta","gamma"}[j],Family:[]string{"memory","reasoning","exploration"}[j],
    CohortSHA256:hx(lane+"cohort"+string(rune(tick))+"x"+string(rune(j))),
    Impact:30+i%60,Novelty:20+j*20,Robustness:40,Diversity:20+j*12,
    EstimatedCost:18+j*3,Risk:20})}
  n:=(i+int(start))%3;d.ChosenID=d.Options[n].ID
  d.ChosenCohortSHA256=d.Options[n].CohortSHA256
  d.Outcome=[]string{"SUPPORTED","NEGATIVE","MIXED","INVALID"}[(i+int(start))%4]
  h.Decisions=append(h.Decisions,d)
 }
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(private,append([]byte(dreamrsi.AttestationDomain),raw...))
 return dreamrsi.Envelope{History:h,SignatureHex:hex.EncodeToString(sig)},hx(string(raw))
}
func fixture(t *testing.T,lane string)(LaneEvidence,LanePins){
 t.Helper()
 prefix:=byte('a');if lane=="Yggdrasil"{prefix='5'}
 src:=h40(prefix)
 f:=evoportfolio.Frozen{Schema:evoportfolio.Schema,Lane:lane,Epoch:1,
   HistoricalSourceSHA:hx(lane+"source-evidence"),
   MaxScreenCompute:12,MaxSealedCompute:10,MaxFinalists:2,MaxPerFamily:1,
   MaxScreensPerFamily:3}
 ids:=[]string{"alpha","beta","gamma","delta"}
 classes:=[]string{"SUPPORTED","NEGATIVE","MIXED","INVALID"}
 fams:=[]string{"memory","memory","reasoning","reasoning"}
 for i:=0;i<4;i++{f.Candidates=append(f.Candidates,evoportfolio.Candidate{
  ID:ids[i],Family:fams[i],SourceSHA:h40(prefix+byte(i)),
  ScreenSHA:hx(lane+"screen"+ids[i]),Score:int64(12+i),
  HistoricalClass:classes[i],ScreenCompute:2,SealedCompute:3})}
 lineage:=[]evoportfolio.IslandLineage{}
 for i,c:=range f.Candidates{
  island:="island_a";if i>=2{island="island_b"}
  lineage=append(lineage,evoportfolio.IslandLineage{CandidateID:c.ID,
    Family:c.Family,IslandID:island,SourceSHA:c.SourceSHA,
    ScreenSHA:c.ScreenSHA,HistoricalClass:c.HistoricalClass,
    OperatorSHA256:hx(lane+"operator"),ParentSHAs:[]string{}})
 }
 p:=evoportfolio.ParetoFreeze{Schema:evoportfolio.ParetoFreezeSchema,
   Lane:lane,PortfolioSHA256:evoportfolio.Digest(f),
   LineageSHA256:evoportfolio.DigestIslandLineage(lineage),BaselineID:"alpha",
   Islands:[]string{"island_a","island_b"},MaxFinalists:2,MaxIslandFinalists:1,
   FixedBeforeScreening:true,HistoricalOnly:true}
 seed:=sha256.Sum256([]byte("SYNTHETIC_TEST_KEY_ONLY_"+lane))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 train,trainPin:=signHistory(t,lane,1,src,priv)
 val,valPin:=signHistory(t,lane,101,src,priv)
 spec:=dreamrsi.FrozenSpec{Schema:dreamrsi.SpecSchema,Lane:lane,Epoch:1,
   TrainHistorySHA256:trainPin,ValidationHistorySHA256:valPin,
   TrainUntilTick:64,ValidateFromTick:101,MaxGenerations:2,Population:4,
   MutationsPerGeneration:6,MaxEvaluations:64,MaxReplayDecisions:50000,
   MinEffectiveSampleSize:4,MinMatchBP:1000,Seed:88}
 raw,_:=json.Marshal(spec)
 prompt:=promptlineage.Frozen{Schema:promptlineage.Schema,Lane:lane,Epoch:1,
   SourceSHA:src,Parent:"study graph roles",Vocabulary:[]string{"memory"},
   MaxOperations:1,Operations:[]promptlineage.Operation{{Kind:"replace",Position:1,Replacement:"memory"}}}
 thetaHistory:=thetaadapt.Training{Schema:thetaadapt.TrainingSchema,
   Lane:lane,SourceSHA:src,Records:[]thetaadapt.TrainingRecord{
    {Sequence:1,EvidenceSHA256:hx(lane+"theta-1"),Classification:"NEGATIVE",
      TrainingOnly:true,Compute:2,Direction:[]int64{-1,1}},
    {Sequence:2,EvidenceSHA256:hx(lane+"theta-2"),Classification:"INVALID",
      TrainingOnly:true,Compute:2,Direction:[]int64{0,0}},
   }}
 thPin:=thetaadapt.TrainingDigest(thetaHistory)
 theta:=thetaadapt.Frozen{Schema:thetaadapt.FrozenSchema,Lane:lane,
    Epoch:1,SourceSHA:src,TrainingSHA256:thPin,FeatureCount:2,
    InitialWeights:[]int64{1,1},MaxAbsWeight:10,LearningStep:1,
    MaxUpdates:3,MaxTrainingCompute:10}
 envHistory:=genenv.History{Schema:genenv.HistorySchema,Lane:lane,
   SourceSHA:src,Records:[]genenv.Record{
    {Sequence:1,EvidenceSHA256:hx(lane+"env-1"),TrainingOnly:true,
     Classification:"NEGATIVE",Vector:[]int64{2,1}},
    {Sequence:2,EvidenceSHA256:hx(lane+"env-2"),TrainingOnly:true,
     Classification:"MIXED",Vector:[]int64{1,2}},
   }}
 envPin:=genenv.HistoryDigest(envHistory)
 env:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:lane,SourceSHA:src,
   Epoch:1,HistorySHA256:envPin,Base:[]int64{2,2},MaxLevel:5,
   MaxCandidates:2,MaxOperations:2,Requests:[]genenv.Request{
    {ID:"novel",Changes:[]genenv.Change{{Index:0,Delta:1}}}}}
 input:=LaneEvidence{Lane:lane,Portfolio:f,ParetoFreeze:p,
   ParetoLineage:lineage,DreamTrain:train,DreamValidation:val,
   DreamSpec:spec,PromptFreeze:prompt,ThetaFreeze:theta,
   ThetaTraining:thetaHistory,EnvironmentFreeze:env,
   EnvironmentHistory:envHistory}
 pins:=LanePins{Lane:lane,PortfolioSHA256:evoportfolio.Digest(f),
   ParetoPolicySHA256:evoportfolio.DigestParetoFreeze(p),
   IndependentEd25519PublicKeyHex:hex.EncodeToString(priv.Public().(ed25519.PublicKey)),
   DreamTrainSHA256:trainPin,DreamValidationSHA256:valPin,
   DreamSpecSHA256:hx(string(raw)),
   PromptSHA256:promptlineage.Digest(prompt),
   ThetaFreezeSHA256:thetaadapt.FrozenDigest(theta),ThetaTrainingSHA256:thPin,
   EnvironmentFreezeSHA256:genenv.FrozenDigest(env),
   EnvironmentHistorySHA256:envPin}
 return input,pins
}
func TestDualLaneFiveEnhancementsSyntheticIsAdvisoryOnly(t *testing.T){
 w,wp:=fixture(t,"Wingless");y,yp:=fixture(t,"Yggdrasil")
 a,err:=EvaluatePair([]LaneEvidence{w,y},[]LanePins{wp,yp})
 if err!=nil{t.Fatal(err)}
 b,err:=EvaluatePair([]LaneEvidence{w,y},[]LanePins{wp,yp})
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("non-deterministic or invalid replay",err)}
 if a.Schema!="forge.research-enhancements.dual-lane-shadow.v1"||
   a.ScienceOriginalsExecuted!=0||a.ScientificAccepted||a.DispatchAuthorized||
   a.AcceptedRefMutation||a.FirstUseConsumed||
   a.ScientificImprovementEstablished||len(a.Lanes)!=2{
   t.Fatal("historical replay fabricated scientific authority")
 }
 for _,l:=range a.Lanes{
  if l.NegativeCount<1||l.MixedCount<1||l.InvalidCount<1||
    l.HistoricalArchiveCount!=4||l.PromptCandidateCount!=1||
    l.EnvironmentUntestedCount!=1||l.ThetaTrainingRecordsPreserved!=2||
    l.DreamPoliciesEvaluated<4||len(l.CapabilityModes)!=5||
    len(l.ParetoFinalists)<1||l.BaselineSealedComputeReserved>10||
    l.ParetoSealedComputeReserved>10{
    t.Fatalf("missing five-way nonauthorizing lineage: %+v",l)
  }
 }
}
func TestDualLaneOptimizerBoundaryFailClosed(t *testing.T){
 build:=func()([]LaneEvidence,[]LanePins){
  w,wp:=fixture(t,"Wingless");y,yp:=fixture(t,"Yggdrasil")
  return []LaneEvidence{w,y},[]LanePins{wp,yp}
 }
 cases:=[]struct{name string;mutate func([]LaneEvidence,[]LanePins)}{
  {"foreign source",func(e []LaneEvidence,p []LanePins){e[1].Portfolio.Candidates[0].SourceSHA=e[0].Portfolio.Candidates[0].SourceSHA}},
  {"swapped lane",func(e []LaneEvidence,p []LanePins){e[0].Lane="Yggdrasil"}},
  {"fake independent pin",func(e []LaneEvidence,p []LanePins){p[0].DreamTrainSHA256=hx("forged")}},
  {"outcome tamper",func(e []LaneEvidence,p []LanePins){e[0].DreamTrain.History.Decisions[0].Outcome="SUPPORTED"}},
  {"wrong pareto lineage",func(e []LaneEvidence,p []LanePins){e[0].ParetoLineage[0].SourceSHA=h40('f')}},
  {"unbudgeted prompt",func(e []LaneEvidence,p []LanePins){e[0].PromptFreeze.MaxOperations=0}},
  {"theta evidence drift",func(e []LaneEvidence,p []LanePins){e[1].ThetaTraining.Records[0].Classification="SUPPORTED"}},
  {"genenv hidden history edit",func(e []LaneEvidence,p []LanePins){e[1].EnvironmentHistory.Records[0].Classification="SUPPORTED"}},
  {"no audit public key",func(e []LaneEvidence,p []LanePins){p[0].IndependentEd25519PublicKeyHex=""}},
  {"missing optimizer",func(e []LaneEvidence,p []LanePins){e[0].EnvironmentFreeze.Requests=nil}},
 }
 for _,test:=range cases{t.Run(test.name,func(t *testing.T){
  e,p:=build();test.mutate(e,p)
  got,err:=EvaluatePair(e,p)
  if err==nil||!reflect.DeepEqual(got,Report{}){t.Fatalf("unqualified inputs permitted %+v",got)}
 })}
}
