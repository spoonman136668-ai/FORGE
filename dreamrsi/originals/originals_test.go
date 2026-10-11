package originals

import (
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "testing"
)
var originalNames=[5]string{"wingless-started.zip","yggdrasil-started.zip","wingless-raw.zip","yggdrasil-raw.zip","postraw-classified.zip"}
func loadTestBundle(t *testing.T,dir string)Bundle{
 t.Helper()
 var b Bundle
 data,err:=os.ReadFile(filepath.Join(dir,"run.json"))
 if err!=nil{t.Fatal(err)}
 b.RunAPI=data
 for i,n:=range originalNames{
  b.Archives[i],err=os.ReadFile(filepath.Join(dir,n))
  if err!=nil{t.Fatal(err)}
 }
 return b
}
func actual(t *testing.T)(map[string]Bundle,bool){
 t.Helper()
 f1:=os.Getenv("FORGE_R2_F1_DIR")
 f2:=os.Getenv("FORGE_R2_F2_DIR")
 if f1==""&&f2==""{return nil,false}
 if f1==""||f2==""{t.Fatal("partial original evidence environment")}
 return map[string]Bundle{"F1":loadTestBundle(t,f1),"F2":loadTestBundle(t,f2)},true
}
func TestPinnedRealF1F2OriginalsPreserveSyntheticHistory(t *testing.T){
 bundles,ok:=actual(t);if !ok{t.Skip("hosted original archives required; source-only tests never invent real outcomes")}
 got,err:=Import(bundles)
 if err!=nil{t.Fatal(err)}
 if got.Schema!=Schema||len(got.Records)!=4||len(got.OriginalRuns)!=2||
  got.ExecutablePolicyReplay||got.ScientificIssuerIndependentlyAttested||
  got.ScientificAccepted||got.DispatchAuthorized||got.CatalogSHA256==""{
  t.Fatalf("archived evidence granted authority %+v",got)
 }
 if got.Records[0].Generation!="F1"||got.Records[2].Generation!="F2"{
  t.Fatal("temporal history order changed")
 }
 for _,rec:=range got.Records{
  if rec.OriginalDisposition!="SUPPORTED"||rec.DataClass!="SYNTHETIC_ONLY"||
   rec.PolicyDecisionMenuRecorded||rec.LoggedActionPropensityRecorded||
   rec.ScientificComputeCostRecorded||rec.CounterfactualReplayEligible||
   rec.ScientificAccepted||rec.DispatchAuthorized||rec.RecordSHA256==""{
   t.Fatalf("invented exploration evidence: %+v",rec)
  }
  for _,c:=range rec.OriginalClauses{if !c{t.Fatal("retained clause drift")}}
 }
 if !errors.Is(ToPolicyReplay(got),ErrNoCounterfactual){
  t.Fatal("original without logged exploration converted to IPS")
 }
 again,err:=Import(bundles);if err!=nil||again.CatalogSHA256!=got.CatalogSHA256{
  t.Fatal("real evidence import nondeterministic")
 }
 t.Logf("AUTHENTIC_ORIGINALS records=%d runs=%v classes_original=true zero_historical_propensity=true catalog_sha=%s",
  len(got.Records),got.OriginalRuns,got.CatalogSHA256)
}
func TestArtifactForgeryAndMissingHistoryFailClosed(t *testing.T){
 if _,err:=Import(nil);err==nil{t.Fatal("empty source accepted")}
 bundles,ok:=actual(t);if !ok{t.Skip("native tests omit direct archived originals")}
 base,err:=Import(bundles);if err!=nil{t.Fatal(err)}
 _=base
 x:=bundles["F1"]
 archive:=append([]byte(nil),x.Archives[2]...)
 archive[len(archive)-12]^=1
 x.Archives[2]=archive
 bundles["F1"]=x
 if _,err:=Import(bundles);err==nil{t.Fatal("corrupt genuine raw accepted")}
 bundles,ok=actual(t);if !ok{t.Fatal("original evidence vanished")}
 x=bundles["F2"]
 var run Run
 if err=json.Unmarshal(x.RunAPI,&run);err!=nil{t.Fatal(err)}
 run.RunAttempt=2
 changed,_:=json.Marshal(run);x.RunAPI=changed;bundles["F2"]=x
 if _,err:=Import(bundles);err==nil{t.Fatal("consumed replay attempt accepted")}
 bundles,ok=actual(t);if !ok{t.Fatal("original evidence vanished")}
 x=bundles["F1"];x.RunAPI=[]byte("{")
 bundles["F1"]=x
 if _,err:=Import(bundles);err==nil{t.Fatal("unparseable live-run witness accepted")}
}
func TestSourceOnlyNoFakeCostOrDecisionHistory(t *testing.T){
 for _,p:=range Pins{
  if p.Generation==""||p.RunID==0||p.SourceSHA==""||p.FrozenBlob==""{
   t.Fatal("historical pins missing")
  }
  for _,s:=range p.ArchiveSHA{if len(s)!=64{t.Fatal("incomplete archive identity")}}
 }
 if !errors.Is(ToPolicyReplay(Catalog{}),ErrNoCounterfactual){
  t.Fatal("missing propensity became an optimizer input")
 }
}
