package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "os/exec"
 "runtime"
 "time"
)
type Receipt struct {
 Schema string `json:"schema"`
 OS string `json:"os"`
 Mode string `json:"mode"`
 ChildCount int `json:"child_count"`
 ChildCPUSeconds float64 `json:"child_cpu_seconds"`
 PeakChildRSSBytes uint64 `json:"peak_child_rss_bytes"`
 OutputSHA256 string `json:"output_sha256"`
 Scope string `json:"scope"`
}
func main(){
 role:=flag.String("role","parent",""); mode:=flag.String("mode","busy",""); flag.Parse()
 if *role=="worker" {
  var x uint64=1469598103934665603
  n:=uint64(0);if *mode=="busy"{n=30000000}
  for i:=uint64(0);i<n;i++ {x=(x^i)*1099511628211}
  b:=[]byte(fmt.Sprintf("%016x",x))
  digest:=sha256.Sum256(b)
  mem,err:=peakRSS(); if err!=nil{panic(err)}
  out:=Receipt{Schema:"forge.rar.g29.cooperative-meter.v1",OS:runtime.GOOS,Mode:*mode,ChildCount:0,PeakChildRSSBytes:mem,OutputSHA256:hex.EncodeToString(digest[:]),Scope:"WORKER_SELF_PHYSICAL_PEAK_RSS"}
  if err=json.NewEncoder(os.Stdout).Encode(out);err!=nil{panic(err)}
  return
 }
 if *role!="parent"{panic("unknown role")}
 exe,err:=os.Executable();if err!=nil{panic(err)}
 count:=1;if *mode=="parallel"{count=2}
 combined:=Receipt{Schema:"forge.rar.g29.cooperative-meter.v1",OS:runtime.GOOS,Mode:*mode,ChildCount:count,Scope:"COOPERATIVE_DIRECT_CHILD_SUM_CPU_AND_MAX_PEAK_RSS_NOT_KERNEL_JOB_TREE"}
 seed:=""
 for i:=0;i<count;i++{
  workerMode:=*mode;if *mode=="parallel"{workerMode="busy"}
  cmd:=exec.Command(exe,"-role=worker","-mode="+workerMode)
  t:=time.Now()
  data,err:=cmd.Output();if err!=nil{panic(err)}
  if cmd.ProcessState==nil{panic("missing process state")}
  cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
  if cpu<0||time.Since(t)<=0{panic("bad process CPU")}
  var child Receipt;if err=json.Unmarshal(data,&child);err!=nil{panic(err)}
  if child.OS!=runtime.GOOS||child.PeakChildRSSBytes==0||len(child.OutputSHA256)!=64{panic("child resource missing")}
  combined.ChildCPUSeconds+=cpu
  if child.PeakChildRSSBytes>combined.PeakChildRSSBytes{combined.PeakChildRSSBytes=child.PeakChildRSSBytes}
  seed+=child.OutputSHA256
 }
 h:=sha256.Sum256([]byte(seed))
 combined.OutputSHA256=hex.EncodeToString(h[:])
 if combined.ChildCPUSeconds<=0{panic("ZERO_CHILD_CPU_INCREASE_WORKLOAD")}
 if err=json.NewEncoder(os.Stdout).Encode(combined);err!=nil{panic(err)}
}
