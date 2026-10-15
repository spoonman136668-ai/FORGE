package optimizerbridge

import (
 "bytes"
 "encoding/json"
 "os"
 "reflect"
 "testing"
)

func externalFixture(t *testing.T)[]byte{
 t.Helper()
 raw,err:=os.ReadFile("../research/optimizer-external/f42-f45-observations.json")
 if err!=nil{t.Fatal(err)}
 return raw
}
func TestExternalTrainingEightGenuineObservationsRemainNonAuthorizing(t *testing.T){
 raw:=externalFixture(t)
 a,err:=ObserveExternalTraining(raw)
 if err!=nil{t.Fatal(err)}
 b,err:=ObserveExternalTraining(raw)
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatalf("non-idempotent read: %v",err)}
 if len(a.Observations)!=12||a.WinglessCount!=6||a.YggdrasilCount!=6||
  a.NegativeGateCount!=12||a.PositiveAccuracySignalCount!=4{
  t.Fatalf("lost historical failed gates or mixed gains: %+v",a)
 }
 if a.SignedPolicyHistoryAvailable||a.DreamRSIProspectiveUseQualified||
  a.ParetoPromotionAuthorized||a.ThetaAcceptedOutcomeUpdateAllowed||
  a.PromptGenenvLiveDispatchAuthorized||a.ScientificImprovementEstablished||
  a.SourceRunArtifactMetadataRechecked||a.ExperimentResultBytesIndependentlyVerified||
  a.ScientificAccepted||a.FirstUseConsumed||a.DispatchAuthorized||a.AcceptedRefMutation{
  t.Fatal("ordinary GitHub TRAIN evidence fabricated optimizer or scientific authority")
 }
 for i,study:=range a.Observations{
  if !study.TrainingOnlyNegative||len(study.FailedChecks)==0||
   study.CandidateCorrect>study.Total||study.StrongestFairCorrect>study.Total{
   t.Fatalf("invalid historical record %d: %+v",i,study)
  }
 }
 if !a.Observations[2].PositiveAccuracySignal||!a.Observations[4].PositiveAccuracySignal||
  !a.Observations[7].PositiveAccuracySignal||!a.Observations[9].PositiveAccuracySignal{
  t.Fatal("failed to preserve positive partial findings inside negative gates")
 }
}
func TestExternalTrainingRejectsTamperedEvidenceAndPseudoRandomization(t *testing.T){
 base:=externalFixture(t)
 var original ExternalTrainingManifest
 if err:=json.Unmarshal(base,&original);err!=nil{t.Fatal(err)}
 mutate:=func(t *testing.T,change func(*ExternalTrainingManifest)){
  t.Helper()
  var m ExternalTrainingManifest
  if err:=json.Unmarshal(base,&m);err!=nil{t.Fatal(err)}
  change(&m)
  raw,_:=json.Marshal(m)
  got,err:=ObserveExternalTraining(raw)
  if err==nil||!reflect.DeepEqual(got,ExternalTrainingReport{}){
    t.Fatalf("did not fail closed: %+v",got)
  }
 }
 tests:=[]struct{name string;change func(*ExternalTrainingManifest)}{
  {"mark signed assignment",func(m *ExternalTrainingManifest){m.Studies[0].RandomizedOptimizerAssignment=true}},
  {"mark original first use",func(m *ExternalTrainingManifest){m.Studies[1].OriginalFirstUse=true}},
  {"claim accepted",func(m *ExternalTrainingManifest){m.Studies[2].ScientificAccepted=true}},
  {"fake independent custody",func(m *ExternalTrainingManifest){m.Studies[4].IndependentSourceCustody=true}},
  {"fake passed scientific gate",func(m *ExternalTrainingManifest){m.Studies[3].ScientificGate="PASSED"}},
  {"drop scientific negative",func(m *ExternalTrainingManifest){m.Studies[7].FailedChecks=nil}},
  {"cross lane swap",func(m *ExternalTrainingManifest){m.Studies[6].Lane="Wingless"}},
  {"duplicate artifact",func(m *ExternalTrainingManifest){m.Studies[1].ArtifactID=m.Studies[0].ArtifactID}},
  {"duplicate head",func(m *ExternalTrainingManifest){m.Studies[1].HeadSHA=m.Studies[0].HeadSHA}},
  {"duplicate run",func(m *ExternalTrainingManifest){m.Studies[1].RunID=m.Studies[0].RunID}},
  {"bad workflow",func(m *ExternalTrainingManifest){m.Studies[0].WorkflowPath=".github/workflows/another.yml"}},
  {"bad digest",func(m *ExternalTrainingManifest){m.Studies[0].ArtifactSHA256="abc"}},
  {"nonphysical score",func(m *ExternalTrainingManifest){m.Studies[3].CandidateCorrect=m.Studies[3].Total+1}},
  {"unknown failure flag",func(m *ExternalTrainingManifest){m.Studies[0].FailedChecks=[]string{"passed"}}},
  {"wrong experiment epoch",func(m *ExternalTrainingManifest){m.Studies[0].Gate="F45"}},
  {"missing lane original",func(m *ExternalTrainingManifest){m.Studies=m.Studies[:11]}},
 }
 for _,test:=range tests{t.Run(test.name,func(t *testing.T){mutate(t,test.change)})}
 injected:=bytes.Replace(base,[]byte(`"mode": "READ_ONLY_GITHUB_TRAIN_ONLY_NOT_SIGNED_POLICY_HISTORY"`),
 []byte(`"mode": "READ_ONLY_GITHUB_TRAIN_ONLY_NOT_SIGNED_POLICY_HISTORY", "MODE":"SIGNED_RANDOMIZED"`),1)
 if bytes.Equal(injected,base){t.Fatal("test must inject an ambiguous JSON field")}
 if _,err:=ObserveExternalTraining(injected);err==nil{t.Fatal("duplicate mixed-case mode was accepted")}
 unknown:=bytes.Replace(base,[]byte(`"original_first_use": false`),
 []byte(`"original_first_use": false, "original_first_use_signed": true`),1)
 if bytes.Equal(unknown,base){t.Fatal("test must introduce an unrecognized privilege flag")}
 if _,err:=ObserveExternalTraining(unknown);err==nil{t.Fatal("unknown authority field was accepted")}
}
