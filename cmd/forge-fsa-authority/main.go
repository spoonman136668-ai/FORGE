// forge-fsa-authority is a separately provisioned, read-only checkpoint
// observer. It cannot sign science, issue permits or execute workers.
package main

import (
 "context"
 "flag"
 "fmt"
 "os"
 "os/signal"
 "syscall"

 "github.com/spoonman136668-ai/forge/authorityhost"
)
func run(ctx context.Context,args []string)error{
 f:=flag.NewFlagSet("forge-fsa-authority",flag.ContinueOnError)
 configPath:=f.String("config","","absolute path to operator-pinned read-only authority config")
 if err:=f.Parse(args);err!=nil{return err}
 if *configPath==""||f.NArg()!=0{return authorityhost.ErrUnprovisioned}
 config,err:=authorityhost.Load(*configPath)
 if err!=nil{return err}
 return authorityhost.Run(ctx,config)
}
func main(){
 ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer stop()
 if err:=run(ctx,os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,err)
  os.Exit(1)
 }
}
