// forge-repair-diagnose is a read-only, evidence-only historical lookup.
// It performs no repairs, code edits, worker starts, or science actions.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "strings"
 "github.com/spoonman136668-ai/forge/repairregistry"
)
type Report struct{
 Status string `json:"status"`
 Matches []repairregistry.Finding `json:"matches"`
}
func run(args []string)(Report,error){
 f:=flag.NewFlagSet("forge-repair-diagnose",flag.ContinueOnError)
 directory:=f.String("registry","","pre-provisioned immutable registry directory")
 repository:=f.String("repository","","exact repository identity")
 component:=f.String("component","","exact failing component")
 signature:=f.String("signature","","exact failure signature")
 scope:=f.String("scope","","exact applicability scope")
 preconditions:=f.String("preconditions","","ordered preconditions joined by semicolon")
 if err:=f.Parse(args);err!=nil{return Report{},err}
 if f.NArg()!=0||*directory==""||*preconditions==""{return Report{},repairregistry.ErrBlocked}
 q:=repairregistry.Query{Repository:*repository,Component:*component,
 FailureSignature:*signature,Scope:*scope,Preconditions:strings.Split(*preconditions,";")}
 findings,err:=repairregistry.Diagnose(*directory,q)
 if err!=nil{return Report{},err}
 return Report{Status:repairregistry.AdvisoryOnly,Matches:findings},nil
}
func main(){r,err:=run(os.Args[1:]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)};_ = json.NewEncoder(os.Stdout).Encode(r)}
