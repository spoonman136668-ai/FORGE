// forge-hybrid-readiness summarizes bounded, locally supplied Hybrid workflow
// metadata; it never fetches GitHub, starts experiments, or accepts science.
package main

import(
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/hybridintegration"
 "github.com/spoonman136668-ai/forge/researchobserver"
)
func run(args []string)(hybridintegration.Readiness,error){
 var empty hybridintegration.Readiness
 f:=flag.NewFlagSet("forge-hybrid-readiness",flag.ContinueOnError)
 path:=f.String("snapshot","","absolute path to approved Hybrid workflow_runs JSON")
 sha:=f.String("source-sha","","exact 40-character Hybrid source commit")
 experiment:=f.String("experiment","","G7-S24, G7-S25 or development-only G7-S26")
 if err:=f.Parse(args);err!=nil{return empty,err}
 if f.NArg()!=0||!filepath.IsAbs(*path){return empty,hybridintegration.ErrBlocked}
 stat,err:=os.Lstat(*path)
 if err!=nil||!stat.Mode().IsRegular()||stat.Size()<1||
  stat.Size()>researchobserver.MaximumBytes{return empty,hybridintegration.ErrBlocked}
 raw,err:=os.ReadFile(*path)
 if err!=nil{return empty,hybridintegration.ErrBlocked}
 return hybridintegration.DiagnoseHybrid(raw,*sha,*experiment)
}
func main(){
 out,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 if err:=json.NewEncoder(os.Stdout).Encode(out);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(2)
 }
}
