// forge-fsa-witness serves ONLY independently signed FSA high-water evidence.
// It cannot sign science, issue owner authority, consume steps, or launch work.
package main

import (
 "context"
 "flag"
 "fmt"
 "os"
 "os/signal"
 "syscall"

 "github.com/spoonman136668-ai/forge/witnesshost"
)

func run(ctx context.Context,args []string)error{
 f:=flag.NewFlagSet("forge-fsa-witness",flag.ContinueOnError)
 configPath:=f.String("config","","absolute path to independently provisioned public pins and mTLS file references")
 if err:=f.Parse(args);err!=nil{return err}
 if *configPath==""||f.NArg()!=0{return witnesshost.ErrUnprovisioned}
 config,err:=witnesshost.Load(*configPath)
 if err!=nil{return err}
 return witnesshost.Run(ctx,config)
}
func main(){
 ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer stop()
 if err:=run(ctx,os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,err)
  os.Exit(1)
 }
}
