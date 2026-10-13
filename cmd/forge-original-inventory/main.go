// forge-original-inventory accepts only exact externally pinned original
// scientific artifact bytes. It does not qualify science or start workers.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/originalinventory"
)
var ErrBlocked=errors.New("FORGE_ORIGINAL_INVENTORY_INPUT_BLOCKED")
func run(args []string)(originalinventory.Report,error){
 var zero originalinventory.Report
 f:=flag.NewFlagSet("forge-original-inventory",flag.ContinueOnError)
 manifest:=f.String("manifest","","absolute immutable externally pinned source manifest")
 wingless:=f.String("wingless","","absolute raw original Wingless artifact")
 yggdrasil:=f.String("yggdrasil","","absolute raw original Yggdrasil artifact")
 if err:=f.Parse(args);err!=nil{return zero,err}
 if f.NArg()!=0||!filepath.IsAbs(*manifest)||!filepath.IsAbs(*wingless)||
  !filepath.IsAbs(*yggdrasil)||*wingless==*yggdrasil||
  *manifest==*wingless||*manifest==*yggdrasil{return zero,ErrBlocked}
 read:=func(path string,max int64)([]byte,error){
  st,err:=os.Lstat(path)
  if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>max{return nil,ErrBlocked}
  raw,err:=os.ReadFile(path)
  if err!=nil||int64(len(raw))!=st.Size(){return nil,ErrBlocked}
  return raw,nil
 }
 m,err:=read(*manifest,8192);if err!=nil{return zero,err}
 w,err:=read(*wingless,1<<20);if err!=nil{return zero,err}
 y,err:=read(*yggdrasil,1<<20);if err!=nil{return zero,err}
 return originalinventory.Build(m,w,y)
}
func main(){
 output,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(output);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
