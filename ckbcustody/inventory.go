// Package ckbcustody reads CKB-plane's permanent S09-S14 first-use ledgers.
// It is strictly read-only and never infers that an absent S14 file permits
// an original scientific dispatch. CKB remains execution authority.
package ckbcustody

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "strconv"
)
var ErrUnsafe=errors.New("FORGE_CKB_FIRST_USE_CUSTODY_UNVERIFIED")
const Schema="forge.ckb.first-use.inventory.v1"
type Ledger struct{
 Generation string `json:"generation"`
 Filename string `json:"filename"`
 SHA256 string `json:"sha256"`
 Consumed bool `json:"consumed"`
}
type Snapshot struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Generations []Ledger `json:"generations"`
 S14Disposition string `json:"s14_disposition"`
 FirstUseReplayAuthorized bool `json:"first_use_replay_authorized"`
 FullyPinned bool `json:"fully_pinned"`
 InventorySHA256 string `json:"inventory_sha256"`
}
type spec struct{generation,filename,schema string}
var history=[]spec{
 {"S09","s09-first-use-consumed.v1.json","ckb.r216-s21-s09-first-use-permanent-ledger.v1"},
 {"S10","s10-first-use-consumed.v1.json","ckb.r216-s26-s10-first-use-permanent-ledger.v1"},
 {"S11","s11-first-use-consumed.v1.json","ckb.r216-s33-s11-first-use-permanent-ledger.v1"},
 {"S12","s12-first-use-consumed.v1.json","ckb.r216-s44-s12-first-use-permanent-ledger.v1"},
 {"S13","s13-first-use-consumed.v1.json","ckb.r216-s52-s13-first-use-permanent-ledger.v1"},
 {"S14","s14-first-use-consumed.v1.json","ckb.r216-s71-s14-first-use-permanent-ledger.v1"},
}
const consumed="IRREVERSIBLE_FIRST_USE_INTENT_CONSUMED"
func hexLower(s string,n int)bool {
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func str(m map[string]any,k,v string)bool {s,ok:=m[k].(string);return ok&&s==v}
func falseBool(m map[string]any,k string)bool {v,ok:=m[k].(bool);return ok&&!v}
func number(m map[string]any,k string)bool {
 v,ok:=m[k].(json.Number);if !ok{return false}
 s:=string(v);if s==""||s[0]=='0'||s[0]=='-'{return false}
 n,err:=strconv.ParseUint(s,10,64);return err==nil&&n>0
}
func strictJSON(raw []byte)(map[string]any,error){
 // Go's ordinary Unmarshal permits duplicate keys; a provenance verifier
 // MUST reject duplicates recursively, including in predecessor hashes.
 d:=json.NewDecoder(bytes.NewReader(raw));d.UseNumber()
 var scan func()error
 scan=func()error{
  token,err:=d.Token();if err!=nil{return ErrUnsafe}
  delim,ok:=token.(json.Delim);if !ok{return nil}
  if delim!='{'&&delim!='['{return ErrUnsafe}
  seen:=map[string]bool{}
  for d.More(){
   if delim=='{'{
    keyToken,err:=d.Token();if err!=nil{return ErrUnsafe}
    key,ok:=keyToken.(string);if !ok||seen[key]{return ErrUnsafe}
    seen[key]=true
   }
   if err:=scan();err!=nil{return err}
  }
  end,err:=d.Token()
  if err!=nil||end!=json.Delim('}')&&delim=='{'||end!=json.Delim(']')&&delim=='['{return ErrUnsafe}
  return nil
 }
 if err:=scan();err!=nil{return nil,err}
 if _,err:=d.Token();!errors.Is(err,io.EOF){return nil,ErrUnsafe}
 d2:=json.NewDecoder(bytes.NewReader(raw));d2.UseNumber()
 var obj map[string]any
 if err:=d2.Decode(&obj);err!=nil||obj==nil{return nil,ErrUnsafe}
 canonical,err:=json.Marshal(obj)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n')){return nil,ErrUnsafe}
 return obj,nil
}
func readLedger(path string)(map[string]any,string,error){
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<2||st.Size()>8192{return nil,"",ErrUnsafe}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>8192{return nil,"",ErrUnsafe}
 doc,err:=strictJSON(raw)
 if err!=nil{return nil,"",ErrUnsafe}
 h:=sha256.Sum256(raw)
 return doc,hex.EncodeToString(h[:]),nil
}
func validate(doc map[string]any,s spec,prior map[string]string)bool{
 if !str(doc,"generation",s.generation)||!str(doc,"schema",s.schema)||
  !falseBool(doc,"replay_authorized"){return false}
 if s.generation=="S09"{
  return str(doc,"consumption",consumed)&&falseBool(doc,"scientific_acceptance")
 }
 if !str(doc,"state",consumed)||!falseBool(doc,"scientific_accepted"){return false}
 switch s.generation{
 case "S12":
  return str(doc,"prereg_git_blob","220cffa155d1277715078b55ffacd057b8229737")&&
   falseBool(doc,"production_authority")&&falseBool(doc,"broker_access")&&falseBool(doc,"ktrade_access")
 case "S13":
  return str(doc,"prereg_git_blob","645700167176f176073a411b154a697554cdf1db")
 case "S14":
  if !str(doc,"prereg_git_blob","05d2bf3bf1f488b605b54037a94b9ca3cffc0e9c")||
   !str(doc,"scientific_result","UNOBSERVED")||!number(doc,"wake_run_id")||
   !falseBool(doc,"production_authority")||!falseBool(doc,"broker_access")||
   !falseBool(doc,"ktrade_access")||!falseBool(doc,"accepted_ref_mutation"){return false}
  main,okMain:=doc["wake_main_sha"].(string)
  ctl,okCtl:=doc["controller_sha"].(string)
  if !okMain||!okCtl||!hexLower(main,40)||!hexLower(ctl,40){return false}
  ancestors,ok:=doc["prior_first_use_sha256"].(map[string]any)
  if !ok||len(ancestors)!=len(prior){return false}
  for k,h:=range prior{v,ok:=ancestors[k].(string);if !ok||v!=h{return false}}
 }
 return true
}
func safeDir(root string)bool{
 if root==""||!filepath.IsAbs(root){return false}
 for p:=filepath.Clean(root);;p=filepath.Dir(p){
  st,err:=os.Lstat(p)
  if err!=nil||!st.IsDir()||st.Mode()&os.ModeSymlink!=0{return false}
  if filepath.Dir(p)==p{break}
 }
 return true
}
// Inspect reads the installed old controller's existing state only. The
// public source tree cannot attest that this state was collected by CKB:
// independent source-of-truth pins are checked separately by VerifyPins.
func Inspect(stateDirectory string)(Snapshot,error){
 if !safeDir(stateDirectory){return Snapshot{},ErrUnsafe}
 report:=Snapshot{Schema:Schema,Mode:"READ_ONLY_CKB_HISTORY_NO_FORGE_AUTHORITY",
  Generations:[]Ledger{},S14Disposition:"ABSENT_OR_UNKNOWN_NO_REPLAY",
  FirstUseReplayAuthorized:false,FullyPinned:false}
 prior:=map[string]string{}
 for n,s:=range history{
  path:=filepath.Join(stateDirectory,s.filename)
  if n==5 {
   _,err:=os.Lstat(path)
   if errors.Is(err,os.ErrNotExist){break}
   if err!=nil{return Snapshot{},ErrUnsafe}
  }
  doc,sha,err:=readLedger(path)
  if err!=nil||!validate(doc,s,prior){return Snapshot{},fmt.Errorf("%w: %s",ErrUnsafe,s.generation)}
  prior[s.filename]=sha
  report.Generations=append(report.Generations,Ledger{Generation:s.generation,Filename:s.filename,SHA256:sha,Consumed:true})
  if n==5 {report.S14Disposition="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"}
 }
 if len(report.Generations)<5||len(report.Generations)>6{return Snapshot{},ErrUnsafe}
 tmp:=report;tmp.InventorySHA256=""
 raw,err:=json.Marshal(tmp);if err!=nil{return Snapshot{},ErrUnsafe}
 sum:=sha256.Sum256(append([]byte("FORGE-CKB-FIRSTUSE-INVENTORY-V1\n"),raw...))
 report.InventorySHA256=hex.EncodeToString(sum[:])
 return report,nil
}
// VerifyPins ensures every historical ledger digest matches an out-of-band,
// independently acquired immutable CKB source identity. It never grants a
// scientific start even if the S14 ledger is absent.
func VerifyPins(report Snapshot,pins map[string]string)error{
 if report.Schema!=Schema||report.Mode!="READ_ONLY_CKB_HISTORY_NO_FORGE_AUTHORITY"||
  report.FirstUseReplayAuthorized||report.FullyPinned||!hexLower(report.InventorySHA256,64)||
  len(report.Generations)<5||len(report.Generations)>6||len(pins)!=len(report.Generations){return ErrUnsafe}
 for n,g:=range report.Generations{
  if g.Generation!=history[n].generation||g.Filename!=history[n].filename||
   !g.Consumed||!hexLower(g.SHA256,64)||pins[g.Generation]!=g.SHA256{return ErrUnsafe}
 }
 expected:="ABSENT_OR_UNKNOWN_NO_REPLAY"
 if len(report.Generations)==6{expected="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"}
 if report.S14Disposition!=expected{return ErrUnsafe}
 original:=report.InventorySHA256;report.InventorySHA256=""
 raw,err:=json.Marshal(report);if err!=nil{return ErrUnsafe}
 sum:=sha256.Sum256(append([]byte("FORGE-CKB-FIRSTUSE-INVENTORY-V1\n"),raw...))
 if hex.EncodeToString(sum[:])!=original{return ErrUnsafe}
 return nil
}
