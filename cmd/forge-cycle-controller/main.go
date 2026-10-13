// forge-cycle-controller exercises bounded, parallel synthetic research
// succession with write-before-dispatch custody. It cannot run real science.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/cyclecontroller"
)
var ErrInput=errors.New("FORGE_SYNTHETIC_CYCLE_INPUT_BLOCKED")
func run(ctx context.Context,args []string)(cyclecontroller.Report,error){
 var empty cyclecontroller.Report
 f:=flag.NewFlagSet("forge-cycle-controller",flag.ContinueOnError)
 synthetic:=f.Bool("synthetic-only",false,"mandatory no-science mode")
 worker:=f.String("worker","","absolute immutable synthetic worker executable")
 workerSHA:=f.String("worker-sha256","","exact prebuilt synthetic worker SHA256")
 planSHA:=f.String("frozen-plan-sha256","","external frozen pair of lane plans SHA256")
 root:=f.String("journal-dir","","absolute persistent forge-synthetic-controller directory")
 generations:=f.Uint64("generations",2,"bounded succession count")
 floor:=f.Uint64("min-completed",0,"externally retained prior complete-cycle floor")
 priorHead:=f.String("min-terminal-sha256","","exact externally retained prior terminal head; required for cross-runner resume")
 if err:=f.Parse(args);err!=nil{return empty,err}
 if !*synthetic||f.NArg()!=0||!filepath.IsAbs(*worker)||
  !filepath.IsAbs(*root)||ctx==nil||ctx.Err()!=nil{return empty,ErrInput}
 if *priorHead!=""{
  return cyclecontroller.RunAnchored(ctx,*worker,*workerSHA,*planSHA,*root,*generations,*floor,*priorHead)
 }
 return cyclecontroller.Run(ctx,*worker,*workerSHA,*planSHA,*root,*generations,*floor)
}
func main(){
 result,err:=run(context.Background(),os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
