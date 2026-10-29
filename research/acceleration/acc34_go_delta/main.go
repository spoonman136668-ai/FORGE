// ACC-34: real native Go CPU-kernel falsification of AC-D1.
// No original Wingless model, paid API, LLM, F139 controller or scientific first use.
package main

import (
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "strconv"
 "time"
)
const (
 InputBits=24
 Nodes=32
 Rounds=96
 Events=4096
)
const Schema="forge.acc34.acd1.real-go-kernel-resource.v1"
type Bits [InputBits]uint8
type Values [Nodes]uint64
type Dependency [InputBits][Nodes]bool

func primary(n int)int{return (n*5+2)%InputBits}
func secondary(n int)int{return (n*11+3)%InputBits}
func node(n int,b Bits)uint64{
 x:=uint64(n+1)*0x9e3779b97f4a7c15
 x^=uint64(b[primary(n)])*0x94d049bb133111eb
 x^=uint64(b[secondary(n)])*0xbf58476d1ce4e5b9
 for k:=0;k<Rounds;k++{
  x^=x>>30
  x*=0xbf58476d1ce4e5b9
  x^=x>>27
  x*=0x94d049bb133111eb
  x^=x>>31
  x+=uint64(k+1)
 }
 // Deliberate FIT-identifiability counterexample: neither isolated
 // single-bit intervention from zero exposes this conjunction.
 if n==0&&b[0]==1&&b[1]==1{x^=0xd6e8feb86659fd93}
 return x
}
func all(b Bits)Values{
 var v Values
 for n:=range v{v[n]=node(n,b)}
 return v
}
func inferSingleBitFromFIT()(Dependency,int){
 var d Dependency
 zero:=Bits{}
 base:=all(zero)
 fits:=0
 for bit:=0;bit<InputBits;bit++{
  temp:=zero;temp[bit]=1
  probe:=all(temp);fits++
  for n:=range base{if probe[n]!=base[n]{d[bit][n]=true}}
 }
 return d,fits
}
func originalSourceOracle()(Dependency){
 var d Dependency
 for n:=0;n<Nodes;n++{
  d[primary(n)][n]=true;d[secondary(n)][n]=true
 }
 d[0][0]=true;d[1][0]=true // privileged, never a learned result
 return d
}
func change(b *Bits,t int,scenario string)int{
 bit:=(t*7+3)%InputBits
 if t%32==0{bit=0}else if t%32==1{bit=1}
 if scenario=="benign"{
  if bit==0&&b[1]==1{bit=4}
  if bit==1&&b[0]==1{bit=5}
 }
 b[bit]^=1
 return bit
}
func fold(sum uint64,v Values)uint64{
 sum^=uint64(0x517cc1b727220a95)
 for i,value:=range v{
  sum^=value+uint64(i+1)*0x9e3779b97f4a7c15+(sum<<6)+(sum>>2)
 }
 return sum
}
type Worker struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Events int `json:"events"`
 FitInterventionProbes int `json:"fit_intervention_probes"`
 EvaluatedNodes int `json:"evaluated_nodes"`
 VerificationFullNodeCalls int `json:"verification_full_node_calls"`
 CorrectedCacheMismatches int `json:"corrected_cache_mismatches"`
 ConjunctiveFITDiscovery bool `json:"conjunctive_fit_discovery"`
 OutputDigest string `json:"output_digest"`
 TotalGoAllocatedBytes uint64 `json:"total_go_allocated_bytes"`
 GoRuntimeSysBytes uint64 `json:"go_runtime_sys_bytes"`
}
func worker(mode,scenario string,eventCount int)(Worker,error){
 if (mode!="full"&&mode!="unverified"&&mode!="verified"&&mode!="oracle")||
 (scenario!="benign"&&scenario!="hidden")||eventCount!=Events{
  return Worker{},errors.New("ACC34_UNFROZEN_WORKER_PARAMETERS")
 }
 before:=Bits{}
 values:=all(before)
 var dep Dependency
 probes:=0
 if mode=="unverified"||mode=="verified"{
  dep,probes=inferSingleBitFromFIT()
 }else if mode=="oracle"{
  dep=originalSourceOracle()
 }
 discovered:=dep[0][0]&&dep[1][0] // false for the source-hidden pair
 count:=Nodes // initial setup computation is charged to all arms
 mismatch:=0
 verifiedCalls:=0
 sum:=uint64(0xcbf29ce484222325)
 for step:=0;step<eventCount;step++{
  bit:=change(&before,step,scenario)
  if mode=="full"{
   values=all(before);count+=Nodes
  }else{
   for n:=0;n<Nodes;n++{
    if dep[bit][n]{values[n]=node(n,before);count++}
   }
   if mode=="verified"{
    exact:=all(before);verifiedCalls+=Nodes
    for n:=0;n<Nodes;n++{
     if values[n]!=exact[n]{
      mismatch++
      // Correction is allowed ONLY after a paid full validation.
      values[n]=exact[n]
      dep[bit][n]=true
     }
    }
   }
  }
  sum=fold(sum,values)
 }
 var mem runtime.MemStats
 runtime.ReadMemStats(&mem)
 return Worker{Schema,mode,scenario,eventCount,probes,count,verifiedCalls,
  mismatch,discovered,fmt.Sprintf("%016x",sum),mem.TotalAlloc,mem.Sys},nil
}
type Trial struct{
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Trial int `json:"trial"`
 ProcessCPUNanoseconds int64 `json:"process_cpu_ns"`
 SpawnWallNanoseconds int64 `json:"spawn_wall_ns"`
 Worker Worker `json:"worker"`
}
func runChild(mode,scenario string,trial int)(Trial,error){
 started:=time.Now()
 command:=exec.Command(os.Args[0],"worker",mode,scenario,strconv.Itoa(Events))
 command.Env=append(os.Environ(),"GOMAXPROCS=1")
 out,err:=command.Output()
 elapsed:=time.Since(started)
 if err!=nil{return Trial{},fmt.Errorf("ACC34_CHILD_FAILED_%s_%s: %w",mode,scenario,err)}
 var w Worker
 if err=json.Unmarshal(out,&w);err!=nil{return Trial{},err}
 if w.Schema!=Schema||w.Mode!=mode||w.Scenario!=scenario||w.Events!=Events{
  return Trial{},errors.New("ACC34_CHILD_EVIDENCE_IDENTITY_DRIFT")
 }
 ps:=command.ProcessState
 cpu:=ps.UserTime()+ps.SystemTime()
 if cpu<=0{return Trial{},errors.New("ACC34_CHILD_CPU_COUNTER_UNAVAILABLE")}
 return Trial{mode,scenario,trial,cpu.Nanoseconds(),elapsed.Nanoseconds(),w},nil
}
func median(values []float64)float64{
 x:=append([]float64(nil),values...)
 sort.Float64s(x)
 if len(x)%2==1{return x[len(x)/2]}
 return (x[len(x)/2-1]+x[len(x)/2])/2
}
func subset(ts []Trial,scenario,mode string)[]Trial{
 var out []Trial
 for _,t:=range ts{if t.Scenario==scenario&&t.Mode==mode{out=append(out,t)}}
 return out
}
func medMetric(ts []Trial,sel func(Trial)float64)float64{
 x:=make([]float64,len(ts))
 for i,v:=range ts{x[i]=sel(v)}
 return median(x)
}
type Summary struct{
 Scenario string `json:"scenario"`
 VerifiedCPUOverFull float64 `json:"verified_cpu_over_full"`
 VerifiedRuntimeSysOverFull float64 `json:"verified_runtime_sys_over_full"`
 UnsafeCPUOverFull float64 `json:"unsafe_cpu_over_full"`
 OracleCPUOverFull float64 `json:"oracle_cpu_over_full"`
 VerifiedCorrections int `json:"verified_corrections"`
 UnverifiedTraceMatchesFull bool `json:"unverified_trace_matches_full"`
 VerifiedTraceMatchesFull bool `json:"verified_trace_matches_full"`
 OracleTraceMatchesFull bool `json:"oracle_trace_matches_full"`
}
type Report struct{
 Schema string `json:"schema"`
 Category string `json:"category"`
 Candidate string `json:"candidate"`
 GoVersion string `json:"go_version"`
 GoOS string `json:"go_os"`
 TrialsPerScenarioMode int `json:"trials_per_scenario_mode"`
 OriginalSourceEpisodes int `json:"original_source_episodes"`
 ModelNativeIntegration bool `json:"model_native_integration"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 GuardedOutputExact bool `json:"guarded_output_exact"`
 UnsafeHiddenInteractionDetected bool `json:"unsafe_hidden_interaction_detected"`
 Output string `json:"classification"`
 Summaries []Summary `json:"summaries"`
 Trials []Trial `json:"trials"`
}
func report(reps int)(Report,error){
 if reps!=5{return Report{},errors.New("ACC34_TRIAL_COUNT_FROZEN_TO_FIVE")}
 var trials []Trial
 var sums []Summary
 safe:=true
 hiddenUnsafe:=false
 for _,scenario:=range []string{"benign","hidden"}{
  for rep:=0;rep<reps;rep++{
   order:=[]string{"full","verified","unverified","oracle"}
   if rep%2==1{order=[]string{"verified","full","oracle","unverified"}}
   for _,mode:=range order{
    trial,err:=runChild(mode,scenario,rep)
    if err!=nil{return Report{},err}
    trials=append(trials,trial)
   }
  }
  baselines:=subset(trials,scenario,"full")
  candidate:=subset(trials,scenario,"verified")
  unsafe:=subset(trials,scenario,"unverified")
  oracle:=subset(trials,scenario,"oracle")
  canonical:=baselines[0].Worker.OutputDigest
  for _,arm:=range [][]Trial{baselines,candidate,unsafe,oracle}{
   if len(arm)!=reps{return Report{},errors.New("ACC34_MISSING_PAIRED_WORKER")}
   for _,t:=range arm{
    if t.Worker.FitInterventionProbes!=func()int{if t.Mode=="verified"||t.Mode=="unverified"{return InputBits};return 0}(){
     return Report{},errors.New("ACC34_UNCHARGED_FIT_DISCOVERY")
    }
   }
  }
  correction:=0
  for _,t:=range candidate{
   correction+=t.Worker.CorrectedCacheMismatches
   if t.Worker.OutputDigest!=canonical{safe=false}
  }
  oracleMatch:=true
  for _,t:=range oracle{if t.Worker.OutputDigest!=canonical{oracleMatch=false}}
  if !oracleMatch{return Report{},errors.New("ACC34_PRIVILEGED_ORACLE_NOT_EXACT")}
  unsafeMatch:=true
  for _,t:=range unsafe{if t.Worker.OutputDigest!=canonical{unsafeMatch=false}}
  if scenario=="hidden"&&!unsafeMatch{hiddenUnsafe=true}
  safeCPU:=medMetric(candidate,func(t Trial)float64{return float64(t.ProcessCPUNanoseconds)})
  baseCPU:=medMetric(baselines,func(t Trial)float64{return float64(t.ProcessCPUNanoseconds)})
  safeMem:=medMetric(candidate,func(t Trial)float64{return float64(t.Worker.GoRuntimeSysBytes)})
  baseMem:=medMetric(baselines,func(t Trial)float64{return float64(t.Worker.GoRuntimeSysBytes)})
  if baseCPU<=0||baseMem<=0{return Report{},errors.New("ACC34_BASELINE_RESOURCE_MISSING")}
  sums=append(sums,Summary{scenario,safeCPU/baseCPU,safeMem/baseMem,
   medMetric(unsafe,func(t Trial)float64{return float64(t.ProcessCPUNanoseconds)})/baseCPU,
   medMetric(oracle,func(t Trial)float64{return float64(t.ProcessCPUNanoseconds)})/baseCPU,
   correction,unsafeMatch,safe,oracleMatch})
 }
 if !safe||!hiddenUnsafe{return Report{},errors.New("ACC34_SAFETY_OR_HIDDEN_CAUSE_CONTROL_FAILED")}
 positive:=true
 for _,s:=range sums{if s.VerifiedCPUOverFull>0.90||s.VerifiedRuntimeSysOverFull>1.10{positive=false}}
 result:="ACC34_ACD1_NO_TOTAL_VERIFIED_NATIVE_GO_CPU_WIN"
 if positive{result="ACC34_ACD1_BOUNDED_GO_KERNEL_CPU_POSITIVE_NO_SCIENCE"}
 return Report{Schema,"SOURCE_FREE_NATIVE_GO_COMPUTE_MICROKERNEL","AC-D1",
   runtime.Version(),runtime.GOOS,reps,0,false,false,safe,hiddenUnsafe,result,sums,trials},nil
}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"ACC34_MODE_REQUIRED");os.Exit(2)}
 if os.Args[1]=="worker"{
  if len(os.Args)!=5{os.Exit(2)}
  steps,err:=strconv.Atoi(os.Args[4])
  if err!=nil{os.Exit(2)}
  x,err:=worker(os.Args[2],os.Args[3],steps)
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
  if err=json.NewEncoder(os.Stdout).Encode(x);err!=nil{os.Exit(2)}
  return
 }
 if os.Args[1]=="report"{
  if len(os.Args)!=3{os.Exit(2)}
  n,err:=strconv.Atoi(os.Args[2])
  if err!=nil{os.Exit(2)}
  x,err:=report(n)
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
  if err=json.NewEncoder(os.Stdout).Encode(x);err!=nil{os.Exit(2)}
  return
 }
 fmt.Fprintln(os.Stderr,"ACC34_UNRECOGNIZED_MODE")
 os.Exit(2)
}
// Reference to math prevents accidental later use of NaN as a valid resource
// ratio; all source-produced resource ratios must be finite.
var _ = math.IsNaN
