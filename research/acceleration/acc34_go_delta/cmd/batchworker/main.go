// ACC-35 32-session source-free native-Go child: no original source or model.
package main
import(
 "crypto/sha256"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "runtime"
 "strings"
 a "example.org/acc34delta/isolated_core"
)
const Batch=32
type BatchReport struct{
 a.Report
 SessionChecksums []string `json:"session_checksums"`
 PerSessionRepairs []uint64 `json:"per_session_repairs"`
}
func main(){
 mode:=flag.String("mode","","arm")
 scenario:=flag.String("scenario","","scenario")
 seed:=flag.Int("seed",0,"original paired development identity")
 events:=flag.Int("events",a.Events,"public events per independent session")
 batch:=flag.Int("batch",Batch,"independently cold restarted sessions")
 flag.Parse()
 if *events!=a.Events||*batch!=Batch||*seed<1{
  fmt.Fprintln(os.Stderr,"ACC35_FROZEN_SESSION_COUNT_DRIFT");os.Exit(2)
 }
 row:=BatchReport{
  Report:a.Report{Schema:"forge.acc35.batched-acd1-native-go-lifecycle.v1",
  Mode:*mode,Scenario:*scenario,Seed:*seed,Events:*events*Batch,
  NativeModelsChanged:false,ScientificFirstUse:false},
  SessionChecksums:make([]string,0,Batch),
  PerSessionRepairs:make([]uint64,0,Batch),
 }
 for k:=0;k<Batch;k++{
  r,e:=a.Run(*mode,*scenario,*seed+k,*events)
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
  row.SessionChecksums=append(row.SessionChecksums,r.Checksum)
  row.PerSessionRepairs=append(row.PerSessionRepairs,r.VerificationRepairs)
  row.FitEvaluations+=r.FitEvaluations
  row.ActionEvaluations+=r.ActionEvaluations
  row.VerificationEvaluations+=r.VerificationEvaluations
  row.VerificationRepairs+=r.VerificationRepairs
 }
 digest:=sha256.Sum256([]byte(strings.Join(row.SessionChecksums,"|")))
 row.Checksum=fmt.Sprintf("%x",digest[:])
 var mem runtime.MemStats
 runtime.ReadMemStats(&mem)
 row.RuntimeSysBytes=mem.Sys
 row.RuntimeTotalAllocBytes=mem.TotalAlloc
 if e:=json.NewEncoder(os.Stdout).Encode(row);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(4)}
}
