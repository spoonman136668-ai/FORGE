// forge-research-intake performs explicit, offline, bounded PR metadata import.
// No GitHub network call, runner, scheduler, scientific execution, or file writes.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "github.com/spoonman136668-ai/forge/researchintake"
)
func main(){
 f:=flag.NewFlagSet("forge-research-intake",flag.ExitOnError)
 source:=f.String("snapshot","","absolute path to pinned cross-lane PR snapshot JSON")
 previous:=f.String("prior","","optional absolute path to prior intake report JSON")
 if f.Parse(os.Args[1:])!=nil||f.NArg()!=0||!filepath.IsAbs(*source)||(*previous!=""&&(!filepath.IsAbs(*previous)||*source==*previous)){
  fmt.Fprintln(os.Stderr,researchintake.ErrBlocked);os.Exit(2)
 }
 read:=func(name string,cap int)([]byte,error){
  info,err:=os.Lstat(name);if err!=nil||!info.Mode().IsRegular()||info.Size()<1||info.Size()>int64(cap){return nil,researchintake.ErrBlocked}
  return os.ReadFile(name)
 }
 raw,err:=read(*source,researchintake.MaxSnapshotBytes);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 var old []byte
 if *previous!=""{old,err=read(*previous,researchintake.MaxReportBytes);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}}
 report,err:=researchintake.Ingest(raw,old);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 if err=json.NewEncoder(os.Stdout).Encode(report);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
