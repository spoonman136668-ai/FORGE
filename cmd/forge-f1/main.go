// forge-f1 is a sandbox-only, one-generation science primary and postraw
// classifier. External GitHub workflow owns first-use and artifact ordering.
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

 "github.com/spoonman136668-ai/forge/pilotf1"
)
func readFile(path string)([]byte,error){
 if !filepath.IsAbs(path){return nil,errors.New("FORGE_F1_ABSOLUTE_EVIDENCE_PATH_REQUIRED")}
 fi,err:=os.Lstat(path)
 if err!=nil||!fi.Mode().IsRegular()||fi.Size()>262144||fi.Size()==0{
  return nil,errors.New("FORGE_F1_EVIDENCE_UNAVAILABLE")
 }
 return os.ReadFile(path)
}
func writeFile(path string,v any)error{
 if !filepath.IsAbs(path){return errors.New("FORGE_F1_OUTPUT_NOT_ABSOLUTE")}
 b,err:=json.MarshalIndent(v,"","  ")
 if err!=nil||len(b)>262144{return errors.New("FORGE_F1_OUTPUT_UNSAFE")}
 out,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return err}
 defer out.Close()
 if _,err=out.Write(append(b,'\n'));err!=nil{return err}
 if err=out.Sync();err!=nil{return err}
 return nil
}
func main(){
 mode:=flag.String("mode","","validate, primary, or classify")
 lane:=flag.String("lane","","Wingless or Yggdrasil")
 prereg:=flag.String("prereg","","frozen JSON absolute path")
 src:=flag.String("source","","source SHA")
 run:=flag.String("run","","GitHub original run ID")
 out:=flag.String("output","","new output JSON absolute path")
 w:=flag.String("wingless","","Wingless archived raw")
 y:=flag.String("yggdrasil","","Yggdrasil archived raw")
 flag.Parse()
 fail:=func(){fmt.Fprintln(os.Stderr,"FORGE_F1_SANDBOX_FAIL_CLOSED");os.Exit(2)}
 if flag.NArg()!=0||pilotf1.ConfirmFreeze(*prereg)!=nil{fail()}
 switch *mode{
 case "validate":
  if *out!=""||*lane!=""||*w!=""||*y!=""{fail()}
  fmt.Println("FORGE_F1_FROZEN_PREREG_IDENTITY=PASS")
 case "primary":
  if *out==""||*w!=""||*y!=""{fail()}
  var raw pilotf1.Raw
  var err error
  switch *lane{
  case "Wingless":raw,err=pilotf1.RunWingless(*run,*src)
  case "Yggdrasil":raw,err=pilotf1.RunYggdrasil(*run,*src)
  default:fail()
  }
  if err!=nil||writeFile(*out,raw)!=nil{fail()}
  fmt.Println("FORGE_F1_ORIGINAL_RAW_WRITTEN_NOT_CLASSIFIED lane="+*lane)
 case "classify":
  if *lane!=""||*out==""||*w==""||*y==""{fail()}
  left,err:=readFile(*w)
  if err!=nil{fail()}
  right,err:=readFile(*y)
  if err!=nil{fail()}
  disposition,err:=pilotf1.Reconcile(left,right)
  if err!=nil||writeFile(*out,disposition)!=nil{fail()}
  fmt.Println("FORGE_F1_POSTRAW_CLASSIFIED_SYNTHETIC_ONLY")
 default:fail()
 }
}
var _ = bytes.Compare
var _ = io.EOF
