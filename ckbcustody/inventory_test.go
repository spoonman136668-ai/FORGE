package ckbcustody

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func putLedger(t *testing.T,root,name string,doc map[string]any){
 t.Helper()
 raw,err:=json.Marshal(doc);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(filepath.Join(root,name),append(raw,'\n'),0600);err!=nil{t.Fatal(err)}
}
func fixtures(t *testing.T,includeS14 bool)(string,map[string]string){
 t.Helper();root:=t.TempDir();pins:=map[string]string{}
 for i,s:=range history{
  if i==5&&!includeS14{break}
  m:=map[string]any{"generation":s.generation,"schema":s.schema,"replay_authorized":false}
  if s.generation=="S09"{
   m["consumption"]=consumed;m["scientific_acceptance"]=false
  }else{
   m["state"]=consumed;m["scientific_accepted"]=false
  }
  if s.generation=="S12"{
   m["prereg_git_blob"]="220cffa155d1277715078b55ffacd057b8229737"
   m["production_authority"]=false;m["broker_access"]=false;m["ktrade_access"]=false
  }
  if s.generation=="S13"{m["prereg_git_blob"]="645700167176f176073a411b154a697554cdf1db"}
  if s.generation=="S14"{
   prior:=map[string]any{}
   for _,p:=range history[:5]{prior[p.filename]=pins[p.generation]}
   m["prior_first_use_sha256"]=prior
   m["prereg_git_blob"]="05d2bf3bf1f488b605b54037a94b9ca3cffc0e9c"
   m["wake_run_id"]=uint64(38281455598)
   m["wake_main_sha"]=strings.Repeat("a",40)
   m["controller_sha"]=strings.Repeat("b",40)
   m["scientific_result"]="UNOBSERVED"
   m["production_authority"]=false;m["broker_access"]=false
   m["ktrade_access"]=false;m["accepted_ref_mutation"]=false
  }
  putLedger(t,root,s.filename,m)
  _,h,err:=readLedger(filepath.Join(root,s.filename));if err!=nil{t.Fatal(err)}
  pins[s.generation]=h
 }
 return root,pins
}
func TestMissingS14IsUnknownNotAvailable(t *testing.T){
 root,pins:=fixtures(t,false)
 before,err:=os.ReadDir(root);if err!=nil{t.Fatal(err)}
 report,err:=Inspect(root)
 if err!=nil||len(report.Generations)!=5{t.Fatal(report,err)}
 if report.FirstUseReplayAuthorized||report.FullyPinned||report.S14Disposition!="ABSENT_OR_UNKNOWN_NO_REPLAY"{
  t.Fatal("missing S14 incorrectly permitted replay",report)
 }
 if err:=VerifyPins(report,pins);err!=nil{t.Fatal(err)}
 after,err:=os.ReadDir(root);if err!=nil||len(before)!=len(after){t.Fatal("read-only inspection mutated CKB state",err)}
 wrong:=map[string]string{}
 for k,v:=range pins{wrong[k]=v};wrong["S12"]=strings.Repeat("0",64)
 if err:=VerifyPins(report,wrong);err==nil{t.Fatal("mismatched authenticated ledger allowed")}
}
func TestConsumedS14LinksAllPriorLedgers(t *testing.T){
 root,pins:=fixtures(t,true)
 report,err:=Inspect(root);if err!=nil{t.Fatal(err)}
 if len(report.Generations)!=6||report.S14Disposition!="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"||
  report.FirstUseReplayAuthorized{t.Fatal("consumed S14 misclassified",report)}
 if err:=VerifyPins(report,pins);err!=nil{t.Fatal(err)}
 rawPath:=filepath.Join(root,history[5].filename)
 data,err:=os.ReadFile(rawPath);if err!=nil{t.Fatal(err)}
 var m map[string]any
 if err=json.Unmarshal(data,&m);err!=nil{t.Fatal(err)}
 m["prior_first_use_sha256"].(map[string]any)[history[0].filename]=strings.Repeat("f",64)
 putLedger(t,root,history[5].filename,m)
 if _,err:=Inspect(root);err==nil{t.Fatal("modified predecessor custody accepted")}
}
func TestRejectDuplicateAndMissingHistoricalFirstUse(t *testing.T){
 root,_:=fixtures(t,false)
 path:=filepath.Join(root,history[0].filename)
 if err:=os.WriteFile(path,[]byte("{\"schema\":\"x\",\"schema\":\"y\"}\n"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Inspect(root);err==nil{t.Fatal("duplicate JSON keys accepted")}
 root,_=fixtures(t,false)
 if err:=os.Remove(filepath.Join(root,history[3].filename));err!=nil{t.Fatal(err)}
 if _,err:=Inspect(root);err==nil{t.Fatal("missing S12 ledger silently ignored")}
}
func TestRejectSymlinkedCKBState(t *testing.T){
 root,_:=fixtures(t,false)
 alias:=filepath.Join(t.TempDir(),"state")
 if err:=os.Symlink(root,alias);err!=nil{t.Skipf("symlink unsupported: %v",err)}
 if _,err:=Inspect(alias);err==nil{t.Fatal("symlinked CKB custody accepted")}
}
