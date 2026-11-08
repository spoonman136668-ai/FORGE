package nativediscovery

import (
 "context"
 "encoding/json"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "reflect"
 "strings"
 "testing"
 "time"
)

func f7VerifyArchive(t *testing.T,report F7Report,parent F5Report){
 t.Helper()
 if report.Schema!=F7Schema||report.F5SourceSHA256!=parent.F4GeneratedSourceSHA256||
  report.F6Schema!=F6Schema||report.TrainingSeeds!=[2]uint32{17,31}||
  report.Policies!=f5Policies()||report.GenerationsPerArm!=F7Generations||
  len(report.Arms)!=6||report.GeneratedCandidateCount!=48||
  !report.DevelopmentOnly||!report.GeneratedSourceCompiledInTestsOnly||
  report.NewExperimentObservations!=0||report.IndependentHoldoutConsumed||
  report.ScientificAccepted||report.GeneralRSIProven||report.OwnerActivation||
  report.DispatchAuthorized||report.AgentCalls!=0||report.PaidAPICalls!=0{
  t.Fatalf("bad source, budget or forbidden authority claim: %+v",report)
 }
 for i,arm:=range report.Arms{
  source:=parent.Arms[i]
  if arm.Seed!=source.Seed||arm.Policy!=source.Policy||
   arm.F5FeedbackSHA256!=f6FeedbackSHA(source,parent){t.Fatal("missing F5 source provenance")}
  var parentReceipt string
  for n,g:=range arm.Generations{
   expectedCount:=F7FirstProbeCount
   if n==1{expectedCount=F5ProbeBudget}
   if g.Seed!=source.Seed||g.Policy!=source.Policy||
    g.Generation!=n+1||g.InitialTrainObservations!=F2TrainCount||
    g.ObservedProbes!=expectedCount||g.AddedProbes!=F7FirstProbeCount||
    g.ScoredDevelopmentDecisions!=F2EvaluationCount||
    len(g.Candidates)!=F6Families||g.ParentGenerationReceiptSHA256==""||
    g.GenerationReceiptSHA256!=f7Receipt(g)||
    g.FeedbackPrefixSHA256!=f7FeedbackHash(arm.Seed,arm.Policy,source.Probes[:expectedCount])||
    !g.ColdReadbackIdentical||g.ColdStateByteCount<10||g.ColdStateByteCount>4096||
    g.OriginalWorldAfterPct!=g.OriginalWorldBeforePct||
    g.OriginalWorldAfterPct!=g.OriginalWorldColdPct{
    t.Fatalf("bad generation %d source chain/retention: %+v",n+1,g)
   }
   if n==0 {
    if g.ParentGenerationReceiptSHA256!=parent.F4GeneratedSourceSHA256{
     t.Fatal("G1 did not derive from frozen F5 source")
    }
   }else if g.ParentGenerationReceiptSHA256!=parentReceipt||
    g.SourceChangedSincePrevious!=(g.SelectedSourceSHA256!=arm.Generations[0].SelectedSourceSHA256)||
    g.GainOverPreviousGenerationPP!=g.SelectedDevAccuracyPct-arm.Generations[0].SelectedDevAccuracyPct{
    t.Fatal("G2 historical lineage or generational gain forged")
   }
   parentReceipt=g.GenerationReceiptSHA256
   proposals,err:=f6ProposeN(source.Probes[:expectedCount],expectedCount)
   if err!=nil{t.Fatal(err)}
   winner:=0
   for j,proposal:=range proposals{
    candidate:=g.Candidates[j]
    if proposal.Family!=candidate.Family||proposal.Phase!=candidate.Phase||
     proposal.TrainingCorrect!=candidate.TrainingCorrect||
     proposal.TrainingTotal!=candidate.TrainingTotal||
     proposal.SourceSHA256!=candidate.SourceSHA256||
     proposal.GeneratedGoSource!=candidate.GeneratedGoSource||
     candidate.SourceSHA256!=f3Hash([]byte(candidate.GeneratedGoSource))||
     candidate.DevChangedWorldAccuracyPct<0||candidate.DevChangedWorldAccuracyPct>100{
     t.Fatal("candidate evidence, negative or source missing")
    }
    if candidate.TrainingCorrect>g.Candidates[winner].TrainingCorrect{winner=j}
   }
   chosen:=g.Candidates[winner]
   if g.SelectedFamily!=chosen.Family||g.SelectedPhase!=chosen.Phase||
    g.SelectedSourceSHA256!=chosen.SourceSHA256||
    g.SelectedTrainingCorrect!=chosen.TrainingCorrect||
    g.SelectedDevAccuracyPct!=chosen.DevChangedWorldAccuracyPct{
    t.Fatal("selected by development score rather than training feedback")
   }
   strongest:=g.TabularAccuracyPct
   if g.FactorizedAccuracyPct>strongest{strongest=g.FactorizedAccuracyPct}
   if g.ExistingNativeAccuracyPct>strongest{strongest=g.ExistingNativeAccuracyPct}
   if g.StrongestControlAccuracyPct!=strongest||
    g.GainOverStrongestControlPP!=g.SelectedDevAccuracyPct-strongest||
    g.TabularAccuracyPct<0||g.TabularAccuracyPct>100||
    g.FactorizedAccuracyPct<0||g.FactorizedAccuracyPct>100||
    g.ExistingNativeAccuracyPct<0||g.ExistingNativeAccuracyPct>100{
    t.Fatal("matched strong conventional comparator omitted or distorted")
   }
   if g.GainOverStrongestControlPP<=0&&g.DevelopmentClassification!="F7_DEV_NO_GO"||
    g.GainOverStrongestControlPP>0&&g.DevelopmentClassification!="F7_DEV_AHEAD_UNVERIFIED"{
    t.Fatal("failed/tied candidate laundered as improvement")
   }
   t.Logf("F7_DEV seed=%d policy=%s gen=%d source=%s family=%s train=%d/%d accuracy=%.3f strongest=%.3f delta_pp=%.3f delta_over_G1_pp=%.3f cold=%.3f outcome=%s",
    arm.Seed,arm.Policy,g.Generation,g.SelectedSourceSHA256,g.SelectedFamily,g.SelectedTrainingCorrect,
    expectedCount,g.SelectedDevAccuracyPct,g.StrongestControlAccuracyPct,g.GainOverStrongestControlPP,
    g.GainOverPreviousGenerationPP,g.OriginalWorldColdPct,g.DevelopmentClassification)
  }
 }
}

func TestF7TwoGenerationsFullFeedbackChainAndOriginalControls(t *testing.T){
 report,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 replay,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(report,replay){t.Fatal("nondeterministic two-generation archive")}
 old,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 f7VerifyArchive(t,report,old)
 if err:=F7ValidatePreview(report);err!=nil{t.Fatal("source-exact replay denied",err)}
}

func TestF7CausalFeedbackChangesSourceAndSecondGenerationDoesNotLeakFuture(t *testing.T){
 p,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 original:=p.Arms[1] // fixed policy begins cue 0,1,2, enabling a causal split.
 if original.Policy!="fixed"{t.Fatal("frozen F5 policy order changed")}
 selectBest:=func(rows []F6GeneratedCandidate) F6GeneratedCandidate{
  idx:=0
  for i:=1;i<len(rows);i++{
   if rows[i].TrainingCorrect>rows[idx].TrainingCorrect{idx=i}
  }
  return rows[idx]
 }
 makeFeedback:=func(cueRule bool)[]F5Probe{
  rows:=append([]F5Probe(nil),original.Probes[:3]...)
  for i:=range rows{
   effect:=1
   if cueRule&&rows[i].Cue%2==1{effect= -1}
   if rows[i].Action==1{effect= -effect}
   rows[i].ObservedEffect=effect
  }
  return rows
 }
 c,err:=f6ProposeN(makeFeedback(false),3)
 if err!=nil{t.Fatal(err)}
 q,err:=f6ProposeN(makeFeedback(true),3)
 if err!=nil{t.Fatal(err)}
 constant,parity:=selectBest(c),selectBest(q)
 if constant.Family!="constant"||parity.Family!="cue-parity"||
  constant.TrainingCorrect!=3||parity.TrainingCorrect!=3||
  constant.SourceSHA256==parity.SourceSHA256||
  constant.GeneratedGoSource==parity.GeneratedGoSource{
  t.Fatal("action consequences failed to change generated mechanism structure")
 }
 g1,err:=f7BuildGeneration(original,p,nil,3)
 if err!=nil{t.Fatal(err)}
 altered:=original
 altered.Probes=append([]F5Probe(nil),original.Probes...)
 for i:=3;i<6;i++{altered.Probes[i].ObservedEffect*= -1}
 sameG1,err:=f7BuildGeneration(altered,p,nil,3)
 if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(g1,sameG1){t.Fatal("G1 leaked three later intervention effects")}
 g2,err:=f7BuildGeneration(original,p,&g1,6)
 if err!=nil{t.Fatal(err)}
 newG2,err:=f7BuildGeneration(altered,p,&g1,6)
 if err!=nil{t.Fatal(err)}
 if g2.FeedbackPrefixSHA256==newG2.FeedbackPrefixSHA256||
  g2.GenerationReceiptSHA256==newG2.GenerationReceiptSHA256{
  t.Fatal("G2 archive did not incorporate newly observed consequences")
 }
 for _,invalid:=range []int{0,1,2,4,5,7,8}{
  if _,err:=f6ProposeN(original.Probes[:3],invalid);err==nil{
   t.Fatalf("wrong probe count admitted %d",invalid)
  }
 }
 if _,err:=f6Propose(original.Probes[:3]);err==nil{t.Fatal("F6 full six-input contract weakened")}
 // A false G1 receipt cannot be used as the G2 parent.
 bad:=g1
 bad.GenerationReceiptSHA256="forged"
 if _,err:=f7BuildGeneration(original,p,&bad,6);err==nil{
  t.Fatal("forged historical parent promoted into next generation")
 }
}

func TestF7RejectsForgedArchiveScienceClaimsAndLostCandidates(t *testing.T){
 original,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 clone:=func()F7Report{
  raw,err:=json.Marshal(original)
  if err!=nil{t.Fatal(err)}
  var dst F7Report
  if err:=json.Unmarshal(raw,&dst);err!=nil{t.Fatal(err)}
  return dst
 }
 changes:=[]struct{name string;apply func(*F7Report)}{
  {"source",func(x *F7Report){x.F5SourceSHA256="bad"}},
  {"seeds",func(x *F7Report){x.TrainingSeeds[1]=59}},
  {"firstuse",func(x *F7Report){x.IndependentHoldoutConsumed=true}},
  {"science",func(x *F7Report){x.ScientificAccepted=true}},
  {"rsi",func(x *F7Report){x.GeneralRSIProven=true}},
  {"owner",func(x *F7Report){x.OwnerActivation=true}},
  {"dispatch",func(x *F7Report){x.DispatchAuthorized=true}},
  {"api",func(x *F7Report){x.PaidAPICalls=1}},
  {"new observation",func(x *F7Report){x.NewExperimentObservations=1}},
  {"missing candidate",func(x *F7Report){x.Arms[0].Generations[0].Candidates=x.Arms[0].Generations[0].Candidates[:3]}},
  {"source forged",func(x *F7Report){x.Arms[0].Generations[1].Candidates[0].GeneratedGoSource+="// injected"}},
  {"receipt forged",func(x *F7Report){x.Arms[0].Generations[1].GenerationReceiptSHA256="bad"}},
  {"gain fabricated",func(x *F7Report){x.Arms[0].Generations[1].GainOverStrongestControlPP+=10}},
  {"selection drift",func(x *F7Report){x.Arms[0].Generations[0].SelectedSourceSHA256="bad"}},
  {"cold false",func(x *F7Report){x.Arms[0].Generations[0].ColdReadbackIdentical=false}},
  {"missing arm",func(x *F7Report){x.Arms=x.Arms[:5]}},
 }
 for _,test:=range changes{t.Run(test.name,func(t *testing.T){
  bad:=clone()
  test.apply(&bad)
  if err:=F7ValidatePreview(bad);err==nil{t.Fatal("forged development feedback accepted")}
 })}
}

// Actual generated source is compiled AND run in disposable, offline packages.
// No arbitrary source: each byte and SHA must match the approved F6 grammar.
// This tests the **actual generated Go implementation**, not only f6Repair.
func TestF7RealGeneratedGoProgramsCompileAndMatchTypedReadout(t *testing.T){
 report,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 parent,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 root:=t.TempDir()
 seen:=map[string]bool{}
 packages:=0
 for i,arm:=range report.Arms{
  source:=parent.Arms[i]
  for gIndex,g:=range arm.Generations{
   count:=F7FirstProbeCount
   if gIndex==1{count=F5ProbeBudget}
   rows,err:=f7ObservedTransitions(source.Probes[:count])
   if err!=nil{t.Fatal(err)}
   for _,candidate:=range g.Candidates{
    canonical,err:=f6Source(candidate.Family,candidate.Phase)
    if err!=nil||canonical!=candidate.GeneratedGoSource||
     candidate.SourceSHA256!=f3Hash([]byte(canonical)){t.Fatal("unknown generated program")}
    if seen[candidate.SourceSHA256]{continue}
    seen[candidate.SourceSHA256]=true
    model:=&f6Repair{Family:candidate.Family,Phase:candidate.Phase}
    if err:=f2teach([]f2Observer{model},f2training(source.Seed));err!=nil{t.Fatal(err)}
    if err:=f2teach([]f2Observer{model},rows);err!=nil{t.Fatal(err)}
    var want [2][4][2]int
    for reg:=0;reg<2;reg++{for cue:=0;cue<4;cue++{for mode:=0;mode<2;mode++{
     want[reg][cue][mode]=model.Predict(f2Context{Regime:reg,Cue:cue,Mode:mode})
    }}}
    countsJSON,err:=json.Marshal(model.Counts)
    if err!=nil{t.Fatal(err)}
    wantJSON,err:=json.Marshal(want)
    if err!=nil{t.Fatal(err)}
    dir:=filepath.Join(root,fmt.Sprintf("candidate%02d",packages))
    if err:=os.MkdirAll(dir,0700);err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(filepath.Join(dir,"candidate.go"),[]byte(canonical),0600);err!=nil{t.Fatal(err)}
    // Mirrors the original f2 major-vote rule and f3 observation counts
    // exactly; builds each generated type without importing this package.
    support:=`package nativediscovery
type f2Context struct{Regime,Cue,Mode int}
type f2Counts [2][4][2][2]int
type f3Core struct{Counts f2Counts}
func f2major(v [2]int)(int,bool){
 if v[0]+v[1]==0{return 1,false}
 if v[0]>v[1]{return -1,true}
 return 1,true
}
`
    if err:=os.WriteFile(filepath.Join(dir,"support.go"),[]byte(support),0600);err!=nil{t.Fatal(err)}
    fixture:=fmt.Sprintf(`package nativediscovery
import("encoding/json";"testing")
func TestActualCompiledGeneratedPrediction(t *testing.T){
 var counts f2Counts
 var expected [2][4][2]int
 if err:=json.Unmarshal([]byte(%q),&counts);err!=nil{t.Fatal(err)}
 if err:=json.Unmarshal([]byte(%q),&expected);err!=nil{t.Fatal(err)}
 m:=&f6RepairCandidate{f3Core{Counts:counts}}
 for r:=0;r<2;r++{for c:=0;c<4;c++{for mode:=0;mode<2;mode++{
  ctx:=f2Context{Regime:r,Cue:c,Mode:mode}
  if got:=m.Predict(ctx);got!=expected[r][c][mode]{
   t.Fatalf("ACTUAL_COMPILED_SOURCE_DIVERGES r=%%d c=%%d mode=%%d got=%%d want=%%d",r,c,mode,got,expected[r][c][mode])
  }
 }}}
}
`,string(countsJSON),string(wantJSON))
    if err:=os.WriteFile(filepath.Join(dir,"candidate_test.go"),[]byte(fixture),0600);err!=nil{t.Fatal(err)}
    packages++
   }
  }
 }
 if packages<2||packages>F6Families*2{
  t.Fatalf("unexpected actual source variants, compiled=%d",packages)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),110*time.Second)
 defer cancel()
 cmd:=exec.CommandContext(ctx,"go","test","-count=1","./...")
 cmd.Dir=root
 cmd.Env=append(os.Environ(),
  "GO111MODULE=off","GOPROXY=off","GOSUMDB=off","GOWORK=off",
  "GOFLAGS=-p=1","GOMAXPROCS=1","GOTOOLCHAIN=local")
 output,err:=cmd.CombinedOutput()
 if ctx.Err()!=nil{t.Fatalf("offline actual source compile timeout: %v",ctx.Err())}
 if err!=nil{t.Fatalf("actual generated source Go compile/execute failed: %v\n%s",err,string(output))}
 lines:=strings.Split(strings.TrimSpace(string(output)),"\n")
 if len(lines)!=packages{t.Fatalf("not every actual Go source package compiled: got=%d want=%d\n%s",len(lines),packages,string(output))}
 for _,line:=range lines{
  if !strings.HasPrefix(line,"ok")||!strings.Contains(line,"candidate"){
   t.Fatalf("generated source failed compilation/behavior or test count: %s",line)
  }
 }
 t.Logf("F7_OFFLINE_COMPILED_SOURCE_VARIANTS_PASS=%d; network=OFF; original_owner=INACTIVE",packages)
}
