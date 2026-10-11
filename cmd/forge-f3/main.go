// forge-f3 is a sandbox-only research executable; source test mode never runs heldout.
package main
import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/pilotf3"
)
func main(){
 mode:=flag.String("mode","","validate, primary or classify")
 prereg:=flag.String("prereg","","frozen first-commit absolute pathname")
 lane:=flag.String("lane","","Wingless or Yggdrasil")
 run:=flag.String("run","","one-shot GitHub Actions run identifier")
 source:=flag.String("source","","qualified immutable source SHA")
 wing:=flag.String("wingless","","archived Wingless original")
 ygg:=flag.String("yggdrasil","","archived Yggdrasil original")
 output:=flag.String("output","","exclusive new artifact destination")
 flag.Parse()
 if !filepath.IsAbs(*prereg)||pilotf3.ConfirmFreeze(*prereg)!=nil{
  fatal("FORGE_F3_PREREG_PIN_MISMATCH")
 }
 if *mode=="validate"{
  if *output!=""||*lane!=""||*run!=""||*wing!=""||*ygg!=""{
   fatal("FORGE_F3_VALIDATE_NO_EXPERIMENT")
  }
  fmt.Println("FORGE_F3_SOURCE_FROZEN=PASS heldout_evaluated=false")
  return
 }
 if !filepath.IsAbs(*output)||*output==""||*run!=""&&*mode=="classify"{
  fatal("FORGE_F3_INVALID_OR_ABSENT_OUTPUT")
 }
 var value any
 switch *mode{
 case "primary":
  if *wing!=""||*ygg!=""||(*lane!="Wingless"&&*lane!="Yggdrasil")||
   len(*run)==0||len(*source)!=40{
   fatal("FORGE_F3_UNAUTHORIZED_PRIMARY_INPUT")
  }
  if *lane=="Wingless"{
   v,err:=pilotf3.RunWingless(*run,*source);if err!=nil{fatal("FORGE_F3_PRIMARY_INVALID")}
   value=v
  }else{
   v,err:=pilotf3.RunYggdrasil(*run,*source);if err!=nil{fatal("FORGE_F3_PRIMARY_INVALID")}
   value=v
  }
 case "classify":
  if *lane!=""||*source!=""||!filepath.IsAbs(*wing)||!filepath.IsAbs(*ygg){
   fatal("FORGE_F3_UNAUTHORIZED_CLASSIFICATION_INPUT")
  }
  w,ew:=os.ReadFile(*wing);y,ey:=os.ReadFile(*ygg)
  if ew!=nil||ey!=nil{fatal("FORGE_F3_ORIGINAL_EVIDENCE_MISSING")}
  v,err:=pilotf3.Reconcile(w,y)
  if err!=nil{fatal("FORGE_F3_ORIGINAL_EVIDENCE_INVALID")}
  value=v
 default:
  fatal("FORGE_F3_MODE_INVALID")
 }
 data,err:=json.MarshalIndent(value,"","  ")
 if err!=nil{fatal("FORGE_F3_ENCODING_ERROR")}
 data=append(data,'\n')
 f,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{fatal("FORGE_F3_WRITE_ONCE_FAILED")}
 if _,err=f.Write(data);err!=nil{_ = f.Close();fatal("FORGE_F3_RAW_WRITE_FAILURE")}
 if err=f.Sync();err!=nil{_ = f.Close();fatal("FORGE_F3_FSYNC_FAILURE")}
 if err=f.Close();err!=nil{fatal("FORGE_F3_CLOSE_FAILURE")}
 fmt.Println("FORGE_F3_"+*mode+"_WRITE_ONCE=PASS sha256="+pilotf3.Digest(data))
 if *mode=="primary"{fmt.Println("FORGE_F3_PRIMARY_SYNTHETIC_ONLY=TRUE")}
 if *mode=="classify"{fmt.Println("FORGE_F3_POSTRAW_CLASSIFICATION=COMPLETE")}
}
func fatal(msg string){fmt.Fprintln(os.Stderr,msg);os.Exit(1)}
var _=errors.Is
