// forge-hybrid-advisory inspects one offline hybrid candidate snapshot.
// It has no network, queue, scheduler, scientific authority or output files.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/hybridresearch"
)

func run(args []string) (hybridresearch.Report,error) {
 var empty hybridresearch.Report
 flags:=flag.NewFlagSet("forge-hybrid-advisory",flag.ContinueOnError)
 path:=flags.String("snapshot","","absolute path to bounded hybrid candidate metadata")
 if err:=flags.Parse(args);err!=nil {return empty,hybridresearch.ErrUnverified}
 if flags.NArg()!=0||!filepath.IsAbs(*path) {return empty,hybridresearch.ErrUnverified}
 stat,err:=os.Lstat(*path)
 if err!=nil||!stat.Mode().IsRegular()||stat.Size()<=0||stat.Size()>hybridresearch.MaximumBytes {
  return empty,hybridresearch.ErrUnverified
 }
 raw,err:=os.ReadFile(*path)
 if err!=nil {return empty,hybridresearch.ErrUnverified}
 report,err:=hybridresearch.Inspect(raw)
 if err!=nil {return empty,err}
 if err:=hybridresearch.VerifyOutput(report);err!=nil {return empty,err}
 return report,nil
}
func main(){
 report,err:=run(os.Args[1:])
 if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 if err:=json.NewEncoder(os.Stdout).Encode(report);err!=nil {
  fmt.Fprintln(os.Stderr,err);os.Exit(2)
 }
}
