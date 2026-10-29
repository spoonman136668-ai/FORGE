// ACC-34 source-free native Go falsification of AC-D1 verified causal delta.
// This is an isolated kernel, not a Wingless/Yggdrasil implementation.
package main

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "hash/fnv"
 "math"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "time"
)

const (
 nodes=32
 inputs=24
 events=4096
 rounds=96
 schema="forge.acc34.acd1.native-go-verified-delta-sourcefree.v1"
)
type Arm string
const (
 Full Arm="FULL"
 Unverified Arm="UNVERIFIED"
 Verified Arm="VERIFIED"
 Oracle Arm="ORACLE"
)
type Worker struct {
 Schema string `json:"schema"`
 Arm Arm `json:"arm"`
 Scenario string `json:"scenario"`
 EventCount int `json:"event_count"`
 FITProbes int `json:"fit_probes"`
 RecomputedNodes int `json:"recomputed_nodes"`
 VerifiedNodes int `json:"verified_nodes"`
 VerifiedRepairs int `json:"verified_repairs"`
 OutputTraceSHA256 string `json:"output_trace_sha256"`
 OutputTrace []uint64 `json:"output_trace"`
 RuntimeSysBytes uint64 `json:"runtime_sys_bytes"`
 TotalAllocBytes uint64 `json:"runtime_total_alloc_bytes"`
 PrivateInputsUsed bool `json:"private_inputs_used"`
 ScientificFirstUse bool `json:"scientific_first_use"`
}
type Observed struct {
 Worker Worker `json:"worker"`
 ChildCPUSeconds float64 `json:"child_cpu_seconds"`
 ChildWallSeconds float64 `json:"child_wall_seconds"`
}
type ScenarioSummary struct {
 Scenario string `json:"scenario"`
 FivePairedCPU []float64 `json:"five_paired_verified_full_cpu_ratios"`
 FivePairedSys []float64 `json:"five_paired_verified_full_sys_ratios"`
 MedianCPURatio float64 `json:"median_verified_full_cpu_ratio"`
 MedianSysRatio float64 `json:"median_verified_full_sys_ratio"`
 OutputEqual bool `json:"verified_exact_output_equal"`
 UnverifiedMismatchEvents int `json:"unverified_mismatched_events"`
 OracleEqual bool `json:"oracle_exact_output_equal"`
 FullMeasuredEvents int `json:"full_measured_events"`
 VerifiedMeasuredEvents int `json:"verified_measured_events"`
 VerifiedRepairs int `json:"verified_repairs_total"`
 UnverifiedWorker Observed `json:"unverified_diagnostic"`
 OracleWorker Observed `json:"oracle_diagnostic"`
}
type Report struct {
 Schema string `json:"schema"`
 AccelerationCandidate string `json:"acceleration_candidate"`
 PortfolioTotal int `json:"portfolio_total"`
 NativeGoKernelOnly bool `json:"native_go_kernel_only"`
 OriginalNativeModelsUntouched bool `json:"original_native_models_untouched"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 ScientificAdmission bool `json:"scientific_admission"`
 CPUIncludesFITAndVerification bool `json:"cpu_includes_fit_and_verification"`
 TrueOSPeakRSSMeasured bool `json:"true_os_peak_rss_measured"`
 PreRegisteredCPUThreshold float64 `json:"pre_registered_cpu_threshold"`
 PreRegisteredSysThreshold float64 `json:"pre_registered_sys_threshold"`
 Classification string `json:"classification"`
 Scenarios []ScenarioSummary `json:"scenarios"`
}
func deps(i int)(int,int){return (i*7+3)%inputs,(i*11+5)%inputs}
func node(i int,x [inputs]bool)uint64{
 p,s:=deps(i)
 var pa,sa,conj uint64
 if x[p]{pa=1};if x[s]{sa=1}
 if i==0&&x[0]&&x[1]{conj=1}
 z:=uint64(i+1)*0x9e3779b97f4a7c15 ^ pa*0xbf58476d1ce4e5b9 ^ sa*0x94d049bb133111eb ^ conj*0x369dea0f31a53f85
 for r:=0;r<rounds;r++{
  z ^= z>>30
  z *= 0xbf58476d1ce4e5b9
  z ^= z>>27
  z *= 0x94d049bb133111eb
  z ^= z>>31
 }
 return z
}
func recompute(x [inputs]bool)[nodes]uint64{
 var a [nodes]uint64
 for n:=0;n<nodes;n++{a[n]=node(n,x)}
 return a
}
func fit()([nodes][inputs]bool,int){
 var d [nodes][inputs]bool
 empty:=[inputs]bool{}
 baseline:=recompute(empty)
 for i:=0;i<inputs;i++{
  x:=empty;x[i]=true
  probe:=recompute(x)
  for j:=0;j<nodes;j++{d[j][i]=probe[j]!=baseline[j]}
 }
 return d,inputs
}
func trueDeps()[nodes][inputs]bool{
 var d [nodes][inputs]bool
 for i:=0;i<nodes;i++{p,s:=deps(i);d[i][p]=true;d[i][s]=true}
 d[0][0]=true;d[0][1]=true // ORACLE ONLY: unknown conjunction.
 return d
}
func toggleIndex(step int,scenario string)int{
 index:=step%inputs
 if scenario=="BENIGN"&&index==1{return 2} // bit 1 never turns on
 return index
}
func traceHash(a [nodes]uint64)uint64{
 h:=fnv.New64a();var b [8]byte
 for _,v:=range a{binary.LittleEndian.PutUint64(b[:],v);_,_=h.Write(b[:])}
 return h.Sum64()
}
func traceSHA(trace []uint64)string{
 h:=sha256.New();var b [8]byte
 for _,v:=range trace{binary.LittleEndian.PutUint64(b[:],v);_,_=h.Write(b[:])}
 return hex.EncodeToString(h.Sum(nil))
}
func execute(arm Arm,scenario string)(Worker,error){
 if scenario!="BENIGN"&&scenario!="HIDDEN_INTERACTION"{return Worker{},errors.New("ACC34_INVALID_SCENARIO")}
 if arm!=Full&&arm!=Verified&&arm!=Unverified&&arm!=Oracle{return Worker{},errors.New("ACC34_INVALID_ARM")}
 result:=Worker{Schema:schema,Arm:arm,Scenario:scenario,EventCount:events,OutputTrace:make([]uint64,0,events)}
 var d [nodes][inputs]bool
 if arm==Unverified||arm==Verified{d,result.FITProbes=fit()}else if arm==Oracle{d=trueDeps()}
 var x [inputs]bool
 outputs:=recompute(x)
 for i:=0;i<events;i++{
  which:=toggleIndex(i,scenario);x[which]=!x[which]
  if arm==Full{
   outputs=recompute(x);result.RecomputedNodes+=nodes
  }else{
   for j:=0;j<nodes;j++{if d[j][which]{outputs[j]=node(j,x);result.RecomputedNodes++}}
   if arm==Verified{
    // Always check ALL 32 nodes; no unpriced safety or skipped correctness.
    expected:=recompute(x);result.VerifiedNodes+=nodes
    for j:=0;j<nodes;j++{if outputs[j]!=expected[j]{outputs[j]=expected[j];result.VerifiedRepairs++}}
   }
  }
  result.OutputTrace=append(result.OutputTrace,traceHash(outputs))
 }
 result.OutputTraceSHA256=traceSHA(result.OutputTrace)
 var mem runtime.MemStats;runtime.ReadMemStats(&mem)
 result.RuntimeSysBytes=mem.Sys;result.TotalAllocBytes=mem.TotalAlloc
 return result,nil
}
func worker()error{
 arm:=Arm(os.Getenv("ACC34_ARM"));scenario:=os.Getenv("ACC34_SCENARIO")
 if arm==""||scenario==""{return errors.New("ACC34_MISSING_WORKER_CONFIGURATION")}
 r,e:=execute(arm,scenario);if e!=nil{return e}
 return json.NewEncoder(os.Stdout).Encode(r)
}
func startChild(executable string,arm Arm,scenario string)(Observed,error){
 cmd:=exec.Command(executable,"--worker")
 cmd.Env=append(os.Environ(),"ACC34_ARM="+string(arm),"ACC34_SCENARIO="+scenario)
 start:=time.Now();raw,e:=cmd.Output();wall:=time.Since(start)
 if e!=nil{return Observed{},fmt.Errorf("ACC34_CHILD_%s_%s:%w",arm,scenario,e)}
 if cmd.ProcessState==nil{return Observed{},errors.New("ACC34_MISSING_CHILD_PROCESS_STATE")}
 cpu:=cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()
 if cpu<=0{return Observed{},errors.New("ACC34_UNMEASURABLE_PROCESS_CPU")}
 var w Worker
 if e:=json.Unmarshal(raw,&w);e!=nil{return Observed{},fmt.Errorf("ACC34_INVALID_WORKER_JSON:%w",e)}
 if w.Schema!=schema||w.Scenario!=scenario||w.Arm!=arm||len(w.OutputTrace)!=events||
    w.OutputTraceSHA256!=traceSHA(w.OutputTrace)||w.EventCount!=events||w.ScientificFirstUse||w.PrivateInputsUsed{
  return Observed{},errors.New("ACC34_WORKER_SOURCE_OR_TRACE_CONTRACT")
 }
 return Observed{Worker:w,ChildCPUSeconds:cpu.Seconds(),ChildWallSeconds:wall.Seconds()},nil
}
func compareTrace(a,b []uint64)int{
 if len(a)!=len(b){return -1}
 mismatches:=0
 for i:=range a{if a[i]!=b[i]{mismatches++}}
 return mismatches
}
func median(v []float64)float64{
 s:=append([]float64(nil),v...);sort.Float64s(s)
 return s[len(s)/2]
}
func measure()(Report,error){
 path,e:=os.Executable();if e!=nil{return Report{},e}
 report:=Report{Schema:schema,AccelerationCandidate:"AC-D1",PortfolioTotal:36,
  NativeGoKernelOnly:true,OriginalNativeModelsUntouched:true,ScientificFirstUse:false,
  ScientificAdmission:false,CPUIncludesFITAndVerification:true,TrueOSPeakRSSMeasured:false,
  PreRegisteredCPUThreshold:0.90,PreRegisteredSysThreshold:1.10}
 qualify:=true
 for _,sc:=range []string{"BENIGN","HIDDEN_INTERACTION"}{
  ss:=ScenarioSummary{Scenario:sc,OutputEqual:true,OracleEqual:true,
   FivePairedCPU:make([]float64,0,5),FivePairedSys:make([]float64,0,5)}
  for trial:=0;trial<5;trial++{
   var a,b Observed
   if trial%2==0{
    a,e=startChild(path,Full,sc);if e!=nil{return Report{},e}
    b,e=startChild(path,Verified,sc);if e!=nil{return Report{},e}
   }else{
    b,e=startChild(path,Verified,sc);if e!=nil{return Report{},e}
    a,e=startChild(path,Full,sc);if e!=nil{return Report{},e}
   }
   if compareTrace(a.Worker.OutputTrace,b.Worker.OutputTrace)!=0||b.Worker.VerifiedNodes!=nodes*events{
    return Report{},errors.New("ACC34_VERIFIED_CORRECTNESS_FAILURE")
   }
   ss.FivePairedCPU=append(ss.FivePairedCPU,b.ChildCPUSeconds/a.ChildCPUSeconds)
   ss.FivePairedSys=append(ss.FivePairedSys,float64(b.Worker.RuntimeSysBytes)/float64(a.Worker.RuntimeSysBytes))
   ss.FullMeasuredEvents+=a.Worker.EventCount;ss.VerifiedMeasuredEvents+=b.Worker.EventCount
   ss.VerifiedRepairs+=b.Worker.VerifiedRepairs
  }
  ss.MedianCPURatio=median(ss.FivePairedCPU)
  ss.MedianSysRatio=median(ss.FivePairedSys)
  reference,e:=startChild(path,Full,sc);if e!=nil{return Report{},e}
  ss.UnverifiedWorker,e=startChild(path,Unverified,sc);if e!=nil{return Report{},e}
  ss.OracleWorker,e=startChild(path,Oracle,sc);if e!=nil{return Report{},e}
  ss.UnverifiedMismatchEvents=compareTrace(reference.Worker.OutputTrace,ss.UnverifiedWorker.Worker.OutputTrace)
  ss.OracleEqual=compareTrace(reference.Worker.OutputTrace,ss.OracleWorker.Worker.OutputTrace)==0
  if !ss.OracleEqual{return Report{},errors.New("ACC34_ORACLE_SOURCE_PARITY_FAILURE")}
  if sc=="BENIGN"&&ss.UnverifiedMismatchEvents!=0{return Report{},errors.New("ACC34_BENIGN_DISCOVERY_UNEXPECTED_MISS")}
  if sc=="HIDDEN_INTERACTION"&&ss.UnverifiedMismatchEvents==0{return Report{},errors.New("ACC34_UNDERCOVERED_FIT_MISSED_HIDDEN_FAILURE_NOT_DEMONSTRATED")}
  if math.IsNaN(ss.MedianCPURatio)||math.IsInf(ss.MedianCPURatio,0)||ss.MedianCPURatio<=0||
   math.IsNaN(ss.MedianSysRatio)||ss.MedianSysRatio<=0{return Report{},errors.New("ACC34_INVALID_RESOURCE_SAMPLE")}
  if ss.MedianCPURatio>report.PreRegisteredCPUThreshold||ss.MedianSysRatio>report.PreRegisteredSysThreshold{qualify=false}
  report.Scenarios=append(report.Scenarios,ss)
 }
 if qualify{report.Classification="ACC34_ACD1_VERIFIED_GO_KERNEL_CPU_AND_SYS_POSITIVE__NO_SCIENCE"}else{
  report.Classification="ACC34_ACD1_NO_TOTAL_VERIFIED_NATIVE_GO_CPU_WIN__NO_SCIENCE"
 }
 return report,nil
}
func main(){
 workerFlag:=flag.Bool("worker",false,"run isolated native Go worker")
 flag.Parse()
 var err error
 if *workerFlag{err=worker()}else{
  var r Report;r,err=measure()
  if err==nil{err=json.NewEncoder(os.Stdout).Encode(r)}
 }
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
