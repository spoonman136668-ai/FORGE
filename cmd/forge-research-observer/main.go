// forge-research-observer ingests two required and one optional, bounded
// workflow-list snapshots without inferring scientific acceptance.
// There is no network, secret, queue, result promotion or dispatch API.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/researchobserver"
)
var ErrBlocked=errors.New("FORGE_LIVE_RESEARCH_METADATA_INPUT_BLOCKED")
func run(args []string)(researchobserver.Report,error){
 var zero researchobserver.Report
 f:=flag.NewFlagSet("forge-research-observer",flag.ContinueOnError)
 w:=f.String("wingless","","absolute path to GitHub Wingless workflow_runs JSON")
 y:=f.String("yggdrasil","","absolute path to GitHub Yggdrasil workflow_runs JSON")
 h:=f.String("hybrid","","optional absolute path to pinned TTT-Hybrid-Lab workflow_runs JSON")
 if err:=f.Parse(args);err!=nil{return zero,err}
 if f.NArg()!=0||!filepath.IsAbs(*w)||!filepath.IsAbs(*y)||*w==*y||
  (*h!=""&&(!filepath.IsAbs(*h)||*h==*w||*h==*y)){return zero,ErrBlocked}
 read:=func(path string)([]byte,error){
  stat,err:=os.Lstat(path)
  if err!=nil||!stat.Mode().IsRegular()||stat.Size()<=0||
   stat.Size()>researchobserver.MaximumBytes{return nil,ErrBlocked}
  return os.ReadFile(path)
 }
 a,err:=read(*w);if err!=nil{return zero,ErrBlocked}
 b,err:=read(*y);if err!=nil{return zero,ErrBlocked}
 if *h==""{return researchobserver.Build(a,b)}
 c,err:=read(*h);if err!=nil{return zero,ErrBlocked}
 return researchobserver.BuildWithHybrid(a,b,c)
}
func main(){
 result,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
