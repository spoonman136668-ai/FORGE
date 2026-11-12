package main

// forge-f2 is the one-shot sandbox experiment launcher and later postraw
// classifier. The workflow, not this tool, guards irreversible first-use.
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/pilotf2"
)
func readRegular(path string)([]byte,error){
 if !filepath.IsAbs(path){return nil,pilotf2.ErrInvalid}
 s,err:=os.Lstat(path)
 if err!=nil||!s.Mode().IsRegular()||s.Size()==0||s.Size()>262144{
  return nil,pilotf2.ErrInvalid
 }
 return os.ReadFile(path)
}
func writeOnce(path string,value any)error{
 if !filepath.IsAbs(path){return pilotf2.ErrInvalid}
 raw,err:=json.MarshalIndent(value,"","  ")
 if err!=nil||len(raw)>262144{return pilotf2.ErrInvalid}
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return err}
 if _,err=f.Write(append(raw,'\n'));err!=nil{_ = f.Close();return err}
 if err=f.Sync();err!=nil{_ = f.Close();return err}
 return f.Close()
}
func main(){
 mode:=flag.String("mode","","validate, primary, classify")
 lane:=flag.String("lane","","Wingless or Yggdrasil")
 prereg:=flag.String("prereg","","absolute path to original frozen JSON")
 run:=flag.String("run","","original GitHub run ID")
 source:=flag.String("source","","immutable commit SHA")
 out:=flag.String("output","","new absolute output path")
 wing:=flag.String("wingless","","Wingless original evidence")
 ygg:=flag.String("yggdrasil","","Yggdrasil original evidence")
 flag.Parse()
 fail:=func(){fmt.Fprintln(os.Stderr,"FORGE_F2_SANDBOX_BLOCKED");os.Exit(2)}
 if flag.NArg()!=0||pilotf2.ConfirmFreeze(*prereg)!=nil{fail()}
 switch *mode {
 case "validate":
  if *lane!=""||*run!=""||*out!=""||*wing!=""||*ygg!=""{fail()}
  fmt.Println("FORGE_F2_PINNED_PREREG=PASS")
 case "primary":
  if *out==""||*wing!=""||*ygg!=""{fail()}
  var raw pilotf2.Raw
  var err error
  switch *lane {
  case "Wingless":raw,err=pilotf2.RunWingless(*run,*source)
  case "Yggdrasil":raw,err=pilotf2.RunYggdrasil(*run,*source)
  default:fail()
  }
  if err!=nil||writeOnce(*out,raw)!=nil{fail()}
  fmt.Println("FORGE_F2_ORIGINAL_RAW_RETAINED lane="+*lane)
 case "classify":
  if *out==""||*lane!=""||*wing==""||*ygg==""{fail()}
  w,err:=readRegular(*wing);if err!=nil{fail()}
  y,err:=readRegular(*ygg);if err!=nil{fail()}
  d,err:=pilotf2.Reconcile(w,y)
  if err!=nil||writeOnce(*out,d)!=nil{fail()}
  fmt.Println("FORGE_F2_SYNTHETIC_ONLY_POSTRAW_CLASSIFIED")
 default:fail()
 }
}
