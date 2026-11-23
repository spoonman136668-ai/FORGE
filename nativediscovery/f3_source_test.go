package nativediscovery

import(
 "bytes"
 "encoding/json"
 "os"
 "reflect"
 "testing"
)
func TestF3CompiledNativeSourceIntegrity(t *testing.T){
 generated,err:=F3Generate();if err!=nil{t.Fatal(err)}
 repeat,err:=F3Generate();if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(generated,repeat){t.Fatal("non-deterministic source grammar")}
 committed,err:=os.ReadFile("f3_generated.go");if err!=nil{t.Fatal(err)}
 if !bytes.Equal(generated.Source,committed){
  t.Fatal("frozen GenEnv grammar source does not match compiled Go implementation")
 }
 if f3Hash(committed)!=generated.SourceSHA256||len(generated.Candidates)!=3{
  t.Fatal("generated-source digest or population size drift")
 }
 expected:=map[string]string{"prior-down":"f3Direct","prior-hold":"f3CueTransfer","prior-up":"f3ModeTransfer"}
 seen:=map[string]bool{}
 for _,c:=range generated.Candidates{
  if seen[c.ID]||expected[c.ID]!=c.GeneratedType||
   len(c.GeneratorDigest)!=64||len(c.StructuralSourceSHA256)!=64{
   t.Fatalf("generated structural mechanism or custody mismatch %+v",c)
  }
  seen[c.ID]=true
 }
 if len(seen)!=3{t.Fatal("missing native-generated executable alternative")}
 tampered:=append([]byte(nil),committed...)
 tampered[len(tampered)-1]^=1
 if f3Hash(tampered)==generated.SourceSHA256{t.Fatal("source tampering ignored")}
}
func TestF3SourceMechanismMatchedAssay(t *testing.T){
 report,err:=F3Development();if err!=nil{t.Fatal(err)}
 second,err:=F3Development();if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(report,second){t.Fatal("native mechanism assay nondeterministic")}
 if report.Schema!=F3Schema||report.AcceptedBase!=F3Base||
  report.SelectionSeeds!=[2]uint32{17,31}||
  report.HeldoutDevelopmentSeeds!=[2]uint32{59,83}||
  report.FrozenRequiredGainPP!=5||report.FrozenMaxRetentionLossPP!=10||
  !report.GeneratedCompiledSource||report.RealWorldData||report.SealedFirstUse||
  report.ScientificAccepted||report.GeneralRSIProven||report.OwnerActivation||
  report.AgentCalls!=0||report.PaidAPICalls!=0||
  len(report.Candidates)!=3||len(report.TrainingResults)!=6||
  len(report.HeldoutResults)!=6{
  t.Fatalf("development/authority/source boundary drift %+v",report)
 }
 seen:=map[string]bool{}
 for _,c:=range report.Candidates{seen[c.ID]=true}
 if !seen[report.SelectedCandidateID]{t.Fatal("parent selected outside frozen generator population")}
 for _,row:=range append(append([]F3Trial(nil),report.TrainingResults...),report.HeldoutResults...){
  if !seen[row.CandidateID]||row.TrainExperiences!=48||row.NewWorldProbes!=6||
   row.InterferenceExperiences!=16||row.ScoredDecisions!=64||
   row.NativeColdBasePct!=row.NativeBaseAfterPct||
   row.NativeBaseBeforePct!=row.NativeBaseAfterPct||
   row.SnapshotBytes<=100||row.SnapshotBytes>4096{
   t.Fatalf("matched action/feedback, retention or cold restore drift %+v",row)
  }
 }
 if report.CriterionMet&&(report.DevelopmentStatus!="SYNTHETIC_PROVISIONAL_ONLY"){
  t.Fatal("provisional science result mislabeled")
 }
 if !report.CriterionMet&&report.DevelopmentStatus!="DEV_NO_GO"{
  t.Fatal("negative science result mislabeled")
 }
 raw,err:=json.Marshal(report);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_NATIVE_DISCOVERY_F3=%s",raw)
}
func TestF3GeneratedProgramsRejectMalformedEvidence(t *testing.T){
 for _,id:=range []string{"prior-down","prior-hold","prior-up"}{
  m,err:=f3New(id);if err!=nil{t.Fatal(err)}
  if err:=m.Observe(f2Transition{Context:f2Context{Regime:2,Cue:0,Mode:0},Action:0,Effect:1});err==nil{
   t.Fatalf("%s admitted unqualified regime",id)
  }
  if err:=m.Observe(f2make(17,0,0,0,0,0));err!=nil{t.Fatal(err)}
  raw,err:=m.Snapshot();if err!=nil{t.Fatal(err)}
  restored,err:=f3New(id);if err!=nil{t.Fatal(err)}
  if err:=restored.Load(raw);err!=nil{t.Fatal(err)}
  if restored.Predict(f2Context{Regime:0,Cue:0,Mode:0})!=m.Predict(f2Context{Regime:0,Cue:0,Mode:0}){
   t.Fatal("native executable source cold output changed")
  }
  bad:=bytes.Replace(raw,[]byte(F3SnapshotSchema),[]byte("INVALID-SCHEMA"),1)
  if err:=restored.Load(bad);err==nil{t.Fatal("tampered source-memory schema accepted")}
  if err:=restored.Load(append(raw,[]byte("{}")...));err==nil{
   t.Fatal("trailing JSON payload accepted")
  }
  if err:=restored.Load(append(raw,[]byte("unparseable")...));err==nil{
   t.Fatal("malformed trailing JSON payload accepted")
  }
  if err:=restored.Load([]byte(`{}`));err==nil{t.Fatal("empty memory accepted")}
 }
 if _,err:=f3New("arbitrary");err==nil{t.Fatal("out of grammar source identity accepted")}
}
