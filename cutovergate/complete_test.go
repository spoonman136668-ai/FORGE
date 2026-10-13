package cutovergate

import(
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/ckbhistory"
)

type mockSources struct{
 gh ckbhistory.Report
 wake ckbhistory.WakeEvidence
 afterWake func()
}
func (m mockSources)InspectS14(context.Context)(ckbhistory.Report,error){return m.gh,nil}
func (m mockSources)InspectWake(_ context.Context,id int64,sha string)(ckbhistory.WakeEvidence,error){
 if m.afterWake!=nil{m.afterWake()}
 return m.wake,nil
}
func signedMockSources()mockSources{
 gh:=ckbhistory.Report{Schema:ckbhistory.Schema,
  Repository:"spoonman136668-ai/ckb-plane",
  OriginalWorkflow:ckbhistory.OriginalPath,
  OriginalRunIDs:[]int64{},IntentArtifactIDs:[]int64{},
  Classification:"NO_GITHUB_RECORD_IS_NOT_FIRST_USE_CLEARANCE"}
 raw,_:=json.Marshal(gh)
 sum:=sha256.Sum256(append([]byte("FORGE-CKB-S14-HISTORY-V1\n"),raw...))
 gh.EvidenceSHA256=hex.EncodeToString(sum[:])
 wake:=ckbhistory.WakeEvidence{
  Schema:ckbhistory.WakeSchema,
  Repository:"spoonman136668-ai/ckb-plane",
  Workflow:ckbhistory.WakeWorkflowPath,WakeRunID:38281455598,
  WakeMainSHA:strings.Repeat("a",40),Event:"workflow_dispatch",
  RunAttempt:1,Status:"completed",Conclusion:"failure",
  Classification:"FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"}
 raw,_=json.Marshal(wake)
 sum=sha256.Sum256(append([]byte("FORGE-CKB-S14-ISSUER-WAKE-V1\n"),raw...))
 wake.EvidenceSHA256=hex.EncodeToString(sum[:])
 return mockSources{gh:gh,wake:wake}
}
func TestFullReadOnlyCutoverEvidenceJoinsExistingLanesAndFailedS14(t *testing.T){
 in:=fixture(t)
 sources:=signedMockSources()
 report,err:=AssessWithWake(context.Background(),sources,in)
 if err!=nil{t.Fatal(err)}
 if report.Mode!=CompleteStatus||report.Schema!=CompleteSchema||
  report.CutoverAuthorized||report.OriginalReplayAuthorized||
  report.ScientificExecutionActivated||
  report.S14WakeAndFirstUse.WakeConclusion!="failure"||
  report.S14WakeAndFirstUse.PinnedWakeRunID!=38281455598||
  report.LegacyAndFSA.CKBFirstUseS14SHA256!=report.S14WakeAndFirstUse.Reconciled.LocalS14PermanentFirstUseSHA256{
  t.Fatal("combined authenticated report misclassified as live cutover",report)
 }
}
func TestCompleteAuditRejectsWakeForgeriesAndDrift(t *testing.T){
 cases:=map[string]func(*Input,*mockSources){
  "wrong wake ID":func(_ *Input,m *mockSources){m.wake.WakeRunID++},
  "forged conclusion":func(_ *Input,m *mockSources){m.wake.Conclusion="success"},
  "different wake source":func(_ *Input,m *mockSources){m.wake.WakeMainSHA=strings.Repeat("f",40)},
  "missing S14 consumed":func(i *Input,_ *mockSources){
   _=os.Remove(filepath.Join(i.LegacyStateDirectory,"s14-first-use-consumed.v1.json"))
  },
  "signed old queue drift":func(i *Input,_ *mockSources){
   i.LegacyLaneCustody[0].Custody.ExistingQueueID="new-queue"
  },
  "FSA witness rollback":func(i *Input,_ *mockSources){
   i.FSAPin.MinimumRevision=i.FSAWitness.Head.Revision+1
  },
  "private CKB ledger changes during wake":func(i *Input,m *mockSources){
   path:=filepath.Join(i.LegacyStateDirectory,"s14-first-use-consumed.v1.json")
   m.afterWake=func(){_ = os.WriteFile(path,[]byte("{}\n"),0600)}
  },
 }
 for name,change:=range cases{t.Run(name,func(t *testing.T){
  in:=fixture(t);m:=signedMockSources();change(&in,&m)
  if r,err:=AssessWithWake(context.Background(),m,in);err==nil{
   t.Fatalf("forged old-owner cutover accepted: %+v",r)
  }
 })}
}
