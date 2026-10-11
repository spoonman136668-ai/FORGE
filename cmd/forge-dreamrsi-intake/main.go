// forge-dreamrsi-intake creates a read-only content-addressed catalog from
// independently retrieved, fixed-identity F1/F2 archives. Never dispatches.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/dreamrsi/originals"
)
var names=[5]string{"wingless-started.zip","yggdrasil-started.zip","wingless-raw.zip","yggdrasil-raw.zip","postraw-classified.zip"}
func regular(path string)([]byte,error){
 if !filepath.IsAbs(path){return nil,originals.ErrEvidence}
 s,err:=os.Lstat(path)
 if err!=nil||!s.Mode().IsRegular()||s.Size()==0||s.Size()>originals.MaxZipBytes{
  return nil,originals.ErrEvidence
 }
 return os.ReadFile(path)
}
func loadBundle(dir string)(originals.Bundle,error){
 var b originals.Bundle
 if !filepath.IsAbs(dir){return b,originals.ErrEvidence}
 var err error
 b.RunAPI,err=regular(filepath.Join(dir,"run.json"))
 if err!=nil{return originals.Bundle{},err}
 for i,name:=range names{
  b.Archives[i],err=regular(filepath.Join(dir,name))
  if err!=nil{return originals.Bundle{},err}
 }
 return b,nil
}
func run(f1,f2,out string)error{
 if !filepath.IsAbs(out){return originals.ErrEvidence}
 a,err:=loadBundle(f1);if err!=nil{return err}
 b,err:=loadBundle(f2);if err!=nil{return err}
 catalog,err:=originals.Import(map[string]originals.Bundle{"F1":a,"F2":b})
 if err!=nil{return err}
 if originals.ToPolicyReplay(catalog)!=originals.ErrNoCounterfactual{
  return originals.ErrEvidence
 }
 raw,err:=json.MarshalIndent(catalog,"","  ")
 if err!=nil||len(raw)>originals.MaxJSONBytes{return originals.ErrEvidence}
 file,err:=os.OpenFile(out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return err}
 if _,err=file.Write(append(raw,'\n'));err!=nil{_ = file.Close();return err}
 if err=file.Sync();err!=nil{_ = file.Close();return err}
 if err=file.Close();err!=nil{return err}
 fmt.Printf("FORGE_DREAMRSI_ORIGINAL_INTAKE=PASS records=%d genuine_runs=2 policy_decisions=0 propensities=0 ips_eligible=false FSA_accepted=false\n",len(catalog.Records))
 return nil
}
func main(){
 f1:=flag.String("f1-dir","","absolute directory of pinned genuine F1 archives and run.json")
 f2:=flag.String("f2-dir","","absolute directory of pinned genuine F2 archives and run.json")
 output:=flag.String("output","","new absolute, exclusive-create catalog JSON")
 flag.Parse()
 if flag.NArg()!=0||run(*f1,*f2,*output)!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_DREAMRSI_ORIGINAL_INTAKE_BLOCKED")
  os.Exit(2)
 }
}
