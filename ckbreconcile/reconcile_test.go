package ckbreconcile

import(
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/ckbhistory"
)
type reader struct{
 report ckbhistory.Report
 err error
 beforeReturn func()
}
func(r reader)InspectS14(context.Context)(ckbhistory.Report,error){
 if r.beforeReturn!=nil{r.beforeReturn()}
 return r.report,r.err
}
func github(ids,artifacts []int64)ckbhistory.Report{
 gh:=ckbhistory.Report{Schema:ckbhistory.Schema,Repository:"spoonman136668-ai/ckb-plane",
  OriginalWorkflow:ckbhistory.OriginalPath,
  OriginalRunIDs:ids,OriginalAttemptCount:len(ids),
  IntentArtifactIDs:artifacts,IntentArtifactCount:len(artifacts),
  Classification:"NO_GITHUB_RECORD_IS_NOT_FIRST_USE_CLEARANCE",
  FirstUseReplayAuthorized:false,ScientificExecutionActivated:false}
 if len(ids)>0{gh.Classification="ORIGINAL_ATTEMPT_RECORDED_NO_REPLAY"
 }else if len(artifacts)>0{gh.Classification="ISSUER_INTENT_ARCHIVED_ORIGINAL_UNKNOWN_NO_REPLAY"}
 b,_:=json.Marshal(gh)
 hash:=sha256.Sum256(append([]byte("FORGE-CKB-S14-HISTORY-V1\n"),b...))
 gh.EvidenceSHA256=hex.EncodeToString(hash[:])
 return gh
}
func fixture(t *testing.T)(string,map[string]string){
 t.Helper();root:=t.TempDir();pins:=map[string]string{};prior:=map[string]string{}
 rows:=[]struct{gen,file,schema string}{
  {"S09","s09-first-use-consumed.v1.json","ckb.r216-s21-s09-first-use-permanent-ledger.v1"},
  {"S10","s10-first-use-consumed.v1.json","ckb.r216-s26-s10-first-use-permanent-ledger.v1"},
  {"S11","s11-first-use-consumed.v1.json","ckb.r216-s33-s11-first-use-permanent-ledger.v1"},
  {"S12","s12-first-use-consumed.v1.json","ckb.r216-s44-s12-first-use-permanent-ledger.v1"},
  {"S13","s13-first-use-consumed.v1.json","ckb.r216-s52-s13-first-use-permanent-ledger.v1"},
  {"S14","s14-first-use-consumed.v1.json","ckb.r216-s71-s14-first-use-permanent-ledger.v1"},
 }
 for _,r:=range rows{
  m:=map[string]any{"generation":r.gen,"schema":r.schema,"replay_authorized":false}
  if r.gen=="S09"{
   m["consumption"]="IRREVERSIBLE_FIRST_USE_INTENT_CONSUMED"
   m["scientific_acceptance"]=false
  }else{m["state"]="IRREVERSIBLE_FIRST_USE_INTENT_CONSUMED";m["scientific_accepted"]=false}
  if r.gen=="S12"{
   m["prereg_git_blob"]="220cffa155d1277715078b55ffacd057b8229737"
   m["production_authority"]=false;m["broker_access"]=false;m["ktrade_access"]=false
  }
  if r.gen=="S13"{m["prereg_git_blob"]="645700167176f176073a411b154a697554cdf1db"}
  if r.gen=="S14"{
   m["prereg_git_blob"]="05d2bf3bf1f488b605b54037a94b9ca3cffc0e9c"
   m["wake_run_id"]=int64(38281455598);m["wake_main_sha"]=strings.Repeat("a",40)
   m["controller_sha"]=strings.Repeat("b",40)
   m["scientific_result"]="UNOBSERVED"
   m["production_authority"]=false;m["broker_access"]=false
   m["ktrade_access"]=false;m["accepted_ref_mutation"]=false
   m["prior_first_use_sha256"]=prior
  }
  raw,e:=json.Marshal(m);if e!=nil{t.Fatal(e)}
  raw=append(raw,'\n')
  if e=os.WriteFile(filepath.Join(root,r.file),raw,0600);e!=nil{t.Fatal(e)}
  h:=sha256.Sum256(raw);pins[r.gen]=hex.EncodeToString(h[:])
  if r.gen!="S14"{prior[r.file]=pins[r.gen]}
 }
 return root,pins
}
func TestDualSourceMissingGHRecordNeverClearsConsumedFirstUse(t *testing.T){
 root,pins:=fixture(t)
 out,err:=Reconcile(context.Background(),reader{report:github([]int64{},[]int64{})},root,pins)
 if err!=nil{t.Fatal(err)}
 if !out.FirstUseConsumed||out.OriginalReplayAuthorized||out.CutoverAuthorized||
  out.ScientificCyclesVerified!=0||out.Mode!=Mode||
  out.OriginalStatus!="GITHUB_ABSENCE_DOES_NOT_CLEAR_PERMANENT_S14_FIRST_USE"{
  t.Fatal("missing GH run reauthorized old S14",out)
 }
}
func TestCompletedOriginalStillNeverReplayed(t *testing.T){
 root,pins:=fixture(t)
 out,e:=Reconcile(context.Background(),reader{report:github([]int64{38310000000},[]int64{38290000000})},root,pins)
 if e!=nil||out.OriginalStatus!="ORIGINAL_ATTEMPT_REQUIRES_SIGNED_RAW_EVIDENCE_NO_REPLAY"||
  out.OriginalReplayAuthorized||len(out.GitHubOriginalRunIDs)!=1{t.Fatal(out,e)}
}
func TestMissingLedgerOrUnpinnedHistoryBlocks(t *testing.T){
 root,pins:=fixture(t)
 if e:=os.Remove(filepath.Join(root,"s14-first-use-consumed.v1.json"));e!=nil{t.Fatal(e)}
 if _,e:=Reconcile(context.Background(),reader{report:github([]int64{},[]int64{})},root,pins);e==nil{
  t.Fatal("absent S14 incorrectly treated as unused")
 }
 root,pins=fixture(t)
 pins["S13"]=strings.Repeat("f",64)
 if _,e:=Reconcile(context.Background(),reader{report:github([]int64{},[]int64{})},root,pins);e==nil{
  t.Fatal("source identity drift ignored")
 }
}
func TestCorruptGHOrSourceDriftDuringReadBlocks(t *testing.T){
 root,pins:=fixture(t)
 report:=github([]int64{},[]int64{})
 report.EvidenceSHA256=strings.Repeat("0",64)
 if _,e:=Reconcile(context.Background(),reader{report:report},root,pins);e==nil{t.Fatal("forged GitHub evidence accepted")}
 original:=github([]int64{},[]int64{})
 localPath:=filepath.Join(root,"s13-first-use-consumed.v1.json")
 mutating:=reader{report:original,beforeReturn:func(){
  _=os.WriteFile(localPath,[]byte("{}\n"),0600)
 }}
 if _,e:=Reconcile(context.Background(),mutating,root,pins);e==nil{t.Fatal("mutable CKB custody accepted")}
 root,pins=fixture(t)
 if _,e:=Reconcile(context.Background(),reader{err:errors.New("GitHub unavailable")},root,pins);e==nil{
  t.Fatal("missing remote history accepted")
 }
}
