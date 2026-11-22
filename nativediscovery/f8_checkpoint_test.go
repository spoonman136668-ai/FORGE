package nativediscovery

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "reflect"
 "testing"
)

func TestF8ColdResumeActuallyCarriesLearnedStateAcrossTwoGenerations(t *testing.T){
 report,err:=F8Development()
 if err!=nil{t.Fatal(err)}
 f7,err:=F7Development()
 if err!=nil{t.Fatal(err)}
 f5,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 if report.Schema!=F8Schema||report.TotalSteps!=12||len(report.Arms)!=6||
  report.TrainingSeeds!=[2]uint32{17,31}||report.Policies!=f5Policies()||
  !report.DevelopmentOnly||report.GeneratedSourceExecuted||
  report.ScientificAccepted||report.IndependentFirstUseConsumed||
  report.RSIProven||report.OwnerActivation||report.DispatchAuthorized||
  report.NewGeneratedObservations!=0||report.AgentCalls!=0||
  report.PaidAPICalls!=0||report.CheckpointSHA256!=f8CheckpointDigest(report){
  t.Fatal("F8 source/budget/authority drift")
 }
 for i,arm:=range report.Arms{
  if arm.Seed!=f5.Arms[i].Seed||arm.Policy!=f5.Arms[i].Policy||
   arm.F5FeedbackSHA256!=f6FeedbackSHA(f5.Arms[i],f5){t.Fatal("parent feedback custody mismatch")}
  var prior string
  for g,row:=range arm.Steps{
   original:=f7.Arms[i].Generations[g]
   expectedCount:=(g+1)*F7FirstProbeCount
   if row.Generation!=g+1||row.Seed!=arm.Seed||row.Policy!=arm.Policy||
    row.F7GenerationReceiptSHA256!=original.GenerationReceiptSHA256||
    row.SelectedFamily!=original.SelectedFamily||
    row.SelectedPhase!=original.SelectedPhase||
    row.SelectedSourceSHA256!=original.SelectedSourceSHA256||
    row.SelectedTrainingCorrect!=original.SelectedTrainingCorrect||
    row.SelectedDevelopmentClassification!=original.DevelopmentClassification||
    row.TotalObservedEvidence!=F2TrainCount+expectedCount||
    row.OriginalTrainObservationCount!=F2TrainCount||
    row.NewlyAppliedObservations!=3||row.PriorObservationsReapplied!=0||
    len(row.SnapshotBytes)!=original.ColdStateByteCount||
    row.SnapshotSHA256!=f3Hash(row.SnapshotBytes)||
    row.RecordSHA256!=f8StepDigest(row)||
    !row.ExactFullReplayMatches||!row.ColdStateReadbackMatches||
    row.PredictionSHA256==""{t.Fatal("no true cold cumulative state preservation")}
   if g==0{
    if row.PreviousStepSHA256!=original.ParentGenerationReceiptSHA256||
     row.PreviouslyLearnedObservations!=0{t.Fatal("G1 source chain/observation counts")}
   }else if row.PreviousStepSHA256!=prior||
    row.PreviouslyLearnedObservations!=F2TrainCount+3{
    t.Fatal("G2 failed to inherit cold G1 without reapplying training")
   }
   prior=row.RecordSHA256
   for j,c:=range original.Candidates{
    if row.GeneratedCandidateSources[j]!=c.SourceSHA256{
     t.Fatal("negative candidate or selected source evidence dropped")
    }
   }
   recovered,err:=F8Restore(report,arm.Seed,arm.Policy,g+1,row.RecordSHA256)
   if err!=nil{t.Fatal(err)}
   direct,err:=f8ExactModel(arm.Seed,
    f5.Arms[i].Probes[:expectedCount],row.SelectedFamily,row.SelectedPhase)
   if err!=nil||!f8Matches(recovered,direct){t.Fatal("cold model disagrees with full historical replay")}
   saved,err:=recovered.Snapshot()
   if err!=nil||!bytes.Equal(saved,row.SnapshotBytes){t.Fatal("actual learned observation counts lost")}
   t.Logf("F8_DEV seed=%d policy=%s gen=%d selected=%s cold_sha=%s original_train=%d newly_applied=%d inherited=%d reapplied=%d status=%s",
    arm.Seed,arm.Policy,g+1,row.SelectedFamily,row.SnapshotSHA256,
    row.OriginalTrainObservationCount,row.NewlyAppliedObservations,
    row.PreviouslyLearnedObservations,row.PriorObservationsReapplied,
    row.SelectedDevelopmentClassification)
  }
 }
}

func TestF8PortableCheckpointAcrossIndependentOfflineFileOpen(t *testing.T){
 report,err:=F8Development()
 if err!=nil{t.Fatal(err)}
 raw,expected,err:=F8Export(report)
 if err!=nil{t.Fatal(err)}
 if len(raw)<100||len(raw)>F8MaxBytes||expected!=f3Hash(raw){
  t.Fatal("portable artifact checksum/size mismatch")
 }
 path:=filepath.Join(t.TempDir(),"f8-cumulative-inactive.json")
 if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 newProcessBytes,err:=os.ReadFile(path)
 if err!=nil{t.Fatal(err)}
 restored,err:=F8Import(newProcessBytes,expected)
 if err!=nil||!reflect.DeepEqual(restored,report){t.Fatal("portable offline checkpoint did not roundtrip",err)}
 for _,generation:=range []int{1,2}{
  old:=restored.Arms[0].Steps[generation-1]
  m,err:=F8Restore(restored,restored.Arms[0].Seed,
   restored.Arms[0].Policy,generation,old.RecordSHA256)
  if err!=nil{t.Fatal(err)}
  snapshot,err:=m.Snapshot()
  if err!=nil||f3Hash(snapshot)!=old.SnapshotSHA256{t.Fatal("different fresh process learned state",err)}
 }
 // A historic local self-hash of a truncated tail does not establish
 // the external authenticated most-recent head.
 for _,bad:=range [][]byte{newProcessBytes[:len(newProcessBytes)-1],
  append([]byte(nil),newProcessBytes[:len(newProcessBytes)-40]...),
  append(append([]byte{},newProcessBytes...),byte('x'))}{
  if _,err:=F8Import(bad,expected);err==nil{t.Fatal("broken/truncated archive accepted")}
 }
 if _,err:=F8Import(newProcessBytes,"");err==nil{t.Fatal("missing expected external digest accepted")}
 if _,err:=F8Import(newProcessBytes,f3Hash([]byte("historic older head")));err==nil{
  t.Fatal("stale external head accepted")
 }
 if _,err:=F8Restore(restored,17,"fixed",1,restored.Arms[0].Steps[0].RecordSHA256);err==nil{
  t.Fatal("cross-policy checkpoint mismatch accepted")
 }
 if _,err:=F8Restore(restored,59,"disagreement",1,restored.Arms[0].Steps[0].RecordSHA256);err==nil{
  t.Fatal("reserved independent test seed used")
 }
}

func TestF8RejectsTamperedSnapshotRecomputedHashAndFalseScience(t *testing.T){
 original,err:=F8Development()
 if err!=nil{t.Fatal(err)}
 clone:=func()F8Checkpoint{
  raw,err:=json.Marshal(original);if err!=nil{t.Fatal(err)}
  var v F8Checkpoint
  if err:=json.Unmarshal(raw,&v);err!=nil{t.Fatal(err)}
  return v
 }
 modifications:=[]struct{name string;fn func(*F8Checkpoint)}{
  {"source parent",func(x *F8Checkpoint){x.F7ReportSHA256="tampered"}},
  {"source bytes",func(x *F8Checkpoint){x.Arms[0].Steps[0].SnapshotBytes[0]^=1}},
  {"source hash",func(x *F8Checkpoint){x.Arms[0].Steps[1].SelectedSourceSHA256="false"}},
  {"source family",func(x *F8Checkpoint){x.Arms[0].Steps[1].SelectedFamily="unreviewed"}},
  {"source phase",func(x *F8Checkpoint){x.Arms[0].Steps[1].SelectedPhase=0}},
  {"added observations",func(x *F8Checkpoint){x.Arms[0].Steps[1].NewlyAppliedObservations=51}},
  {"training replay",func(x *F8Checkpoint){x.Arms[0].Steps[1].PriorObservationsReapplied=51}},
  {"removed negative",func(x *F8Checkpoint){x.Arms[0].Steps[1].GeneratedCandidateSources[3]=""}},
  {"G1-g2 swap",func(x *F8Checkpoint){x.Arms[0].Steps[0],x.Arms[0].Steps[1]=x.Arms[0].Steps[1],x.Arms[0].Steps[0]}},
  {"remove arm",func(x *F8Checkpoint){x.Arms=x.Arms[:5]}},
  {"seed 59",func(x *F8Checkpoint){x.Arms[0].Seed=59}},
  {"false no-go",func(x *F8Checkpoint){x.Arms[0].Steps[1].SelectedDevelopmentClassification="SCIENTIFIC_PASS"}},
  {"false science",func(x *F8Checkpoint){x.ScientificAccepted=true}},
  {"RSI claim",func(x *F8Checkpoint){x.RSIProven=true}},
  {"owner activation",func(x *F8Checkpoint){x.OwnerActivation=true}},
  {"dispatch claim",func(x *F8Checkpoint){x.DispatchAuthorized=true}},
  {"first use",func(x *F8Checkpoint){x.IndependentFirstUseConsumed=true}},
  {"source execution",func(x *F8Checkpoint){x.GeneratedSourceExecuted=true}},
  {"paid model",func(x *F8Checkpoint){x.PaidAPICalls=1}},
  {"new observations",func(x *F8Checkpoint){x.NewGeneratedObservations=1}},
 }
 for _,tc:=range modifications{t.Run(tc.name,func(t *testing.T){
  bad:=clone();tc.fn(&bad)
  // An attacker may recompute every *local* untrusted checksum.
  for i:=range bad.Arms{
   for j:=range bad.Arms[i].Steps{
    bad.Arms[i].Steps[j].RecordSHA256=f8StepDigest(bad.Arms[i].Steps[j])
   }
  }
  bad.CheckpointSHA256=f8CheckpointDigest(bad)
  if err:=F8Validate(bad);err==nil{t.Fatal("forged but self-hashed checkpoint accepted")}
 })}
 raw,expected,err:=F8Export(original)
 if err!=nil{t.Fatal(err)}
 // Canonicalization rejects duplicate JSON keys even if the untrusted sender
 // recalculates its own hash.
 injected:=bytes.Replace(raw,[]byte(`"schema":`),[]byte(`"schema":"forged","schema":`),1)
 if _,err:=F8Import(injected,f3Hash(injected));err==nil{
  t.Fatal("duplicate/conflicting JSON key accepted")
 }
 if _,err:=F8Import(raw,expected);err!=nil{t.Fatal(err)}
}

func TestF8RealG1ContinuationDoesNotRepeatOriginalEvidence(t *testing.T){
 report,err:=F8Development()
 if err!=nil{t.Fatal(err)}
 f5,err:=F5Development()
 if err!=nil{t.Fatal(err)}
 for i,arm:=range report.Arms{
  g1:=arm.Steps[0];g2:=arm.Steps[1]
  fresh:=&f6Repair{Family:g2.SelectedFamily,Phase:g2.SelectedPhase}
  if err:=fresh.Load(g1.SnapshotBytes);err!=nil{t.Fatal(err)}
  next,err:=f7ObservedTransitions(f5.Arms[i].Probes)
  if err!=nil{t.Fatal(err)}
  // A genuine new 3-step update (no original 48+3 replay):
  if err:=f2teach([]f2Observer{fresh},next[3:]);err!=nil{t.Fatal(err)}
  result,err:=fresh.Snapshot()
  if err!=nil||!bytes.Equal(result,g2.SnapshotBytes){t.Fatal("new three-step cumulative update differs",err)}
  if bytes.Equal(g1.SnapshotBytes,g2.SnapshotBytes){t.Fatal("G2 did not actually learn any new observations")}
  // Re-applying prior observations must be detected by source-exact snapshot
  // comparison, rather than silently counted as a valid extra generation.
  if err:=f2teach([]f2Observer{fresh},next[:3]);err!=nil{t.Fatal(err)}
  overtrained,err:=fresh.Snapshot()
  if err!=nil||bytes.Equal(overtrained,g2.SnapshotBytes){t.Fatal("replayed original evidence went undetected")}
 }
}
