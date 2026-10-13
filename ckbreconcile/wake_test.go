package ckbreconcile

import (
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

type wakeReader struct{
 reader
 evidence ckbhistory.WakeEvidence
 errorWake error
 afterWake func()
}
func(w wakeReader)InspectWake(_ context.Context,_ int64,_ string)(ckbhistory.WakeEvidence,error){
 if w.afterWake!=nil{w.afterWake()}
 return w.evidence,w.errorWake
}
func completedWake()ckbhistory.WakeEvidence{
 w:=ckbhistory.WakeEvidence{
  Schema:ckbhistory.WakeSchema,Repository:"spoonman136668-ai/ckb-plane",
  Workflow:ckbhistory.WakeWorkflowPath,WakeRunID:38281455598,
  WakeMainSHA:strings.Repeat("a",40),Event:"workflow_dispatch",
  RunAttempt:1,Status:"completed",Conclusion:"failure",
  Classification:"FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY",
  FirstUseReplayAuthorized:false,
 }
 raw,_:=json.Marshal(w)
 sum:=sha256.Sum256(append([]byte("FORGE-CKB-S14-ISSUER-WAKE-V1\n"),raw...))
 w.EvidenceSHA256=hex.EncodeToString(sum[:])
 return w
}
func TestThreeSourceCKBFailedIssuerWakeNeverPermitsS14Replay(t *testing.T){
 state,pins:=fixture(t)
 report,err:=ReconcileWake(context.Background(),wakeReader{
  reader:reader{report:github([]int64{},[]int64{})},
  evidence:completedWake(),
 },state,pins)
 if err!=nil{t.Fatal(err)}
 if report.Mode!=WakeMode||report.WakeConclusion!="failure"||
  report.PinnedWakeRunID!=38281455598||report.WakeEvidenceSHA256==""||
  !report.FirstUseConsumed||report.OriginalReplayAuthorized||
  report.FORGEAuthorityTransferred||report.ScienceActivated||
  report.Reconciled.OriginalReplayAuthorized||
  len(report.Outstanding)!=6{
  t.Fatal("failed wake silently allowed original replay",report)
 }
}
func TestWakeWrongIdentityAndForgedDigestFailClosed(t *testing.T){
 cases:=map[string]func(*ckbhistory.WakeEvidence){
  "different wake ID":func(w *ckbhistory.WakeEvidence){w.WakeRunID++},
  "wrong source commit":func(w *ckbhistory.WakeEvidence){w.WakeMainSHA=strings.Repeat("f",40)},
  "changed reported conclusion":func(w *ckbhistory.WakeEvidence){w.Conclusion="success"},
  "permission invented":func(w *ckbhistory.WakeEvidence){w.FirstUseReplayAuthorized=true},
 }
 for name,modify:=range cases{t.Run(name,func(t *testing.T){
  state,pins:=fixture(t)
  wake:=completedWake()
  modify(&wake)
  _,err:=ReconcileWake(context.Background(),wakeReader{
   reader:reader{report:github([]int64{},[]int64{})},evidence:wake,
  },state,pins)
  if err==nil{t.Fatal("forged wake report accepted")}
 })}
}
func TestWakeTamperingPrivateLedgerMidReadBlocks(t *testing.T){
 state,pins:=fixture(t)
 path:=filepath.Join(state,"s14-first-use-consumed.v1.json")
 mutated:=wakeReader{reader:reader{report:github([]int64{},[]int64{})},
  evidence:completedWake(),afterWake:func(){
   _=os.WriteFile(path,[]byte("{}\n"),0600)
  }}
 if _,err:=ReconcileWake(context.Background(),mutated,state,pins);err==nil{
  t.Fatal("CKB permanent consumed ledger drift between GitHub reads accepted")
 }
}
func TestWakeMissingPermanentS14BlocksEvenOnGitHubFailure(t *testing.T){
 state,pins:=fixture(t)
 if err:=os.Remove(filepath.Join(state,"s14-first-use-consumed.v1.json"));err!=nil{t.Fatal(err)}
 if _,err:=ReconcileWake(context.Background(),wakeReader{
  reader:reader{report:github([]int64{},[]int64{})},
  evidence:completedWake(),
 },state,pins);err==nil{
  t.Fatal("wake failure promoted without original first-use custody")
 }
}
