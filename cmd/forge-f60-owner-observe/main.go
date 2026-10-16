// forge-f60-owner-observe consumes EXISTING independently pinned and signed
// two-lane research export inputs. It only writes an unpromoted historical
// candidate observation. No Cloudflare request, new signer, experiment or
// controller is created by this command.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/optimizerbridge"
)
var errInput=errors.New("F60_SIGNED_OWNER_INPUT_NOT_QUALIFIED")
func readExisting(path string,limit int64)([]byte,error){
 if !filepath.IsAbs(path){return nil,errInput}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<1||info.Size()>limit{return nil,errInput}
 b,err:=os.ReadFile(path)
 if err!=nil||int64(len(b))>limit||len(b)==0{return nil,errInput}
 return b,nil
}
func unmarshalStrict(b []byte,out any)error {
 dec:=json.NewDecoder(bytes.NewReader(b))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(out);err!=nil{return errInput}
 var extra any
 if dec.Decode(&extra)!=io.EOF{return errInput}
 return nil
}
func observe(args []string)error{
 fs:=flag.NewFlagSet("forge-f60-owner-observe",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 paths:=[]*string{
  fs.String("wingless-evidence","",""),
  fs.String("yggdrasil-evidence","",""),
  fs.String("signed-export","",""),
  fs.String("independent-anchor","",""),
  fs.String("independent-lane-pins","",""),
  fs.String("wingless-selection-audit","",""),
  fs.String("yggdrasil-selection-audit","",""),
  fs.String("independent-audit-pins","",""),
 }
 output:=fs.String("observation-out","","")
 if fs.Parse(args)!=nil||fs.NArg()!=0||*output==""{return errInput}
 // File paths may not alias an evidence input, and output cannot overwrite.
 seen:=map[string]bool{}
 for _,name:=range append(paths,output){
  if !filepath.IsAbs(*name){return errInput}
  value:=filepath.Clean(*name)
  if seen[value]{return errInput}
  seen[value]=true
 }
 var contents [8][]byte
 for i,name:=range paths{
  limit:=int64(optimizerbridge.MaxLaneEvidenceBytes)
  if i==2||i==4 {limit=256*1024}
  if i==3||i==7 {limit=64*1024}
  bytes,err:=readExisting(*name,limit)
  if err!=nil{return errInput}
  contents[i]=bytes
 }
 var export optimizerbridge.SignedExport
 var trust optimizerbridge.ExternalTrust
 var pins []optimizerbridge.LanePins
 if unmarshalStrict(contents[2],&export)!=nil||
  unmarshalStrict(contents[3],&trust)!=nil||
  unmarshalStrict(contents[4],&pins)!=nil{return errInput}
 var audits [2]optimizerbridge.SignedSelectionAudit
 if unmarshalStrict(contents[5],&audits[0])!=nil||
  unmarshalStrict(contents[6],&audits[1])!=nil{return errInput}
 var auditPins []optimizerbridge.SelectionAuditPin
 if unmarshalStrict(contents[7],&auditPins)!=nil||len(auditPins)!=2{return errInput}
 var pair [2]optimizerbridge.SelectionAuditPin
 copy(pair[:],auditPins)
 frozen,err:=optimizerbridge.FreezeF58()
 if err!=nil{return errInput}
 observation,err:=optimizerbridge.ObserveF60FromSignedExport(frozen,export,trust,
  [2][]byte{contents[0],contents[1]},pins,audits,pair)
 if err!=nil{return errInput}
 serialized,err:=json.MarshalIndent(observation,"","  ")
 if err!=nil{return errInput}
 file,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return errInput}
 if _,err=file.Write(append(serialized,'\n'));err!=nil{_ = file.Close();return errInput}
 if file.Sync()!=nil||file.Close()!=nil{return errInput}
 fmt.Println("FORGE_F60_SIGNED_HISTORICAL_CANDIDATE_OBSERVATION=PASS")
 fmt.Println("OWNER_PROSPECTIVE_FIRST_USE=NOT_VERIFIED")
 fmt.Println("DREAM_PARETO_POLICY_ACTIVATION=BLOCKED")
 fmt.Println("THETA_EVOLVE_UPDATE=BLOCKED")
 return nil
}
func main(){
 if err:=observe(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_F60_SIGNED_OWNER_INPUT_BLOCKED")
  os.Exit(2)
 }
}
