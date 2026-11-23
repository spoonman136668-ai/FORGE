// forge-fsa-probe independently checks pre-provisioned dual FSA read-only
// endpoints. Successful observation never authorizes scientific execution.
package main

import (
 "context"
 "encoding/json"
 "flag"
 "fmt"
 "os"

 "github.com/spoonman136668-ai/forge/fsaprobe"
)
func run(ctx context.Context,args []string)(fsaprobe.Report,error){
 var zero fsaprobe.Report
 f:=flag.NewFlagSet("forge-fsa-probe",flag.ContinueOnError)
 configPath:=f.String("config","","absolute path to immutable remote trust pins and mTLS file paths")
 if err:=f.Parse(args);err!=nil{return zero,err}
 if *configPath==""||f.NArg()!=0{return zero,fsaprobe.ErrBlocked}
 cfg,err:=fsaprobe.Load(*configPath)
 if err!=nil{return zero,err}
 return fsaprobe.Check(ctx,cfg)
}
func main(){
 report,err:=run(context.Background(),os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err:=json.NewEncoder(os.Stdout).Encode(report);err!=nil{os.Exit(1)}
}
