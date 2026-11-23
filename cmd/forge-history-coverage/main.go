// forge-history-coverage reports observable GitHub Actions archive gaps offline.
// Network transport belongs to the existing read-only GitHub Actions workflow.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "github.com/spoonman136668-ai/forge/historycoverage"
)
func main(){
 f:=flag.NewFlagSet("forge-history-coverage",flag.ExitOnError)
 wr:=f.String("wingless-runs","","absolute NDJSON run snapshot")
 wa:=f.String("wingless-artifacts","","absolute NDJSON artifact snapshot")
 yr:=f.String("yggdrasil-runs","","absolute NDJSON run snapshot")
 ya:=f.String("yggdrasil-artifacts","","absolute NDJSON artifact snapshot")
 wrN:=f.Uint64("wingless-runs-total",0,"first page total")
 waN:=f.Uint64("wingless-artifacts-total",0,"first page total")
 yrN:=f.Uint64("yggdrasil-runs-total",0,"first page total")
 yaN:=f.Uint64("yggdrasil-artifacts-total",0,"first page total")
 if err:=f.Parse(os.Args[1:]);err!=nil||f.NArg()!=0{fmt.Fprintln(os.Stderr,historycoverage.ErrBlocked);os.Exit(1)}
 read:=func(p string)([]byte,error){if !filepath.IsAbs(p){return nil,historycoverage.ErrBlocked};stat,err:=os.Lstat(p);if err!=nil||!stat.Mode().IsRegular()||stat.Size()<=0||stat.Size()>historycoverage.MaxInputBytes{return nil,historycoverage.ErrBlocked};return os.ReadFile(p)}
 x,err:=read(*wr);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 y,err:=read(*wa);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 z,err:=read(*yr);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 t,err:=read(*ya);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 out,err:=historycoverage.Build(
  historycoverage.Source{Lane:"Wingless",Runs:x,Artifacts:y,DeclaredRuns:*wrN,DeclaredArtifacts:*waN},
  historycoverage.Source{Lane:"Yggdrasil",Runs:z,Artifacts:t,DeclaredRuns:*yrN,DeclaredArtifacts:*yaN})
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
