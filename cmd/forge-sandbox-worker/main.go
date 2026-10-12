// forge-sandbox-worker exercises one real OS process with synthetic-only
// computation and durable signed receipts. NEVER uses CKB science authority.
package main

import (
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strings"

 "github.com/spoonman136668-ai/forge/attemptjournal"
 "github.com/spoonman136668-ai/forge/sandboxworker"
 "github.com/spoonman136668-ai/forge/syntheticsupervisor"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
type Output struct {
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 Recovery syntheticsupervisor.State `json:"recovery"`
 RealScientificCycles int `json:"real_scientific_cycles"`
}
func run(args []string)(Output,error){
 f:=flag.NewFlagSet("forge-sandbox-worker",flag.ContinueOnError)
 root:=f.String("new-dir","","new dedicated directory")
 lane:=f.String("lane","","Wingless or Yggdrasil (synthetic names only)")
 ack:=f.Bool("synthetic-only",false,"mandatory offline sandbox approval")
 if err:=f.Parse(args);err!=nil{return Output{},err}
 if !*ack||f.NArg()!=0||(*lane!="Wingless"&&*lane!="Yggdrasil")||
  !filepath.IsAbs(*root)||filepath.Base(filepath.Clean(*root))!="forge-synthetic-worker"{
  return Output{},errors.New("FORGE_SYNTHETIC_WORKER_EXPLICIT_NEW_DIRECTORY_REQUIRED")
 }
 if err:=os.Mkdir(*root,0700);err!=nil{return Output{},err}
 // Per-invocation key: not a real authority key and never exported. Tests
 // validate the returned signed custody within this synthetic process only.
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{return Output{},err}
 entropy:=make([]byte,16);if _,err:=rand.Read(entropy);err!=nil{return Output{},err}
 experimentID:="synthetic_"+hex.EncodeToString(entropy)
 frozen:=sha256.Sum256([]byte("FORGE-SANDBOX-FROZEN:"+experimentID))
 intent:=sha256.Sum256([]byte("FORGE-SANDBOX-INTENT:"+experimentID))
 expected:=workerreconcile.Expected{Lane:*lane,ExperimentID:experimentID,
  FrozenSHA256:hex.EncodeToString(frozen[:]),IntentSHA256:hex.EncodeToString(intent[:]),
  OriginalRunID:"synthetic_original",WorkerID:"synthetic_worker",OwnerEpoch:1,WorkerPublicKey:pub}
 ctx,cancel:=sandboxworker.BoundedContext(context.Background());defer cancel()
 if err:=sandboxworker.ExecuteOnce(ctx,*root,sandboxworker.Task{
  Expected:expected,OwnerID:"SYNTHETIC_TEST_OWNER",Epoch:1},priv);err!=nil{return Output{},err}
 entries,err:=os.ReadDir(*root);if err!=nil{return Output{},err}
 var custody attemptjournal.Record
 found:=0
 for _,entry:=range entries{
  if strings.HasPrefix(entry.Name(),"start-")||strings.HasPrefix(entry.Name(),"terminal-"){continue}
  data,err:=os.ReadFile(filepath.Join(*root,entry.Name()));if err!=nil{return Output{},err}
  if err:=json.Unmarshal(data,&custody);err!=nil{return Output{},err}
  found++
 }
 if found!=1{return Output{},errors.New("FORGE_SYNTHETIC_CUSTODY_AMBIGUOUS")}
 state,err:=syntheticsupervisor.Recover(*root,custody,expected)
 if err!=nil||state!=syntheticsupervisor.Terminal{return Output{},errors.New("FORGE_SYNTHETIC_TERMINAL_UNVERIFIED")}
 return Output{Mode:"INACTIVE_SYNTHETIC_ONLY",Lane:*lane,Recovery:state,RealScientificCycles:0},nil
}
func main(){o,err:=run(os.Args[1:]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)};_ = json.NewEncoder(os.Stdout).Encode(o)}
