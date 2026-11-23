// forge-synthetic-supervisor launches exactly two separate offline synthetic
// worker processes. There is no real-science dispatch or CKB authority path.
package main
import(
 "context"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/spoonman136668-ai/forge/subprocesssupervisor"
)
func run(args []string)(subprocesssupervisor.Result,error){
 f:=flag.NewFlagSet("forge-synthetic-supervisor",flag.ContinueOnError)
 worker:=f.String("worker-executable","","absolute worker binary path")
 hash:=f.String("worker-sha256","","pinned binary SHA256")
 root:=f.String("new-dir","","brand-new dedicated synthetic output directory")
 ack:=f.Bool("synthetic-only",false,"required explicit synthetic mode")
 if err:=f.Parse(args);err!=nil{return subprocesssupervisor.Result{},err}
 if !*ack||f.NArg()!=0{return subprocesssupervisor.Result{},fmt.Errorf("FORGE_SYNTHETIC_SUPERVISOR_ACK_REQUIRED")}
 return subprocesssupervisor.Run(context.Background(),*worker,*hash,*root)
}
func main(){v,err:=run(os.Args[1:]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)};_ = json.NewEncoder(os.Stdout).Encode(v)}
