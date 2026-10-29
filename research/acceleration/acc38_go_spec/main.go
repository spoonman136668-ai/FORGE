// ACC-38 original U02: exact scalar target verification versus nonparametric draft.
// Source-free native Go engineering, not a real LLM or native model acceleration.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "hash"
 "math"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "time"
)

const Sessions=64
const OutputsPerSession=2048
const FitCallsPerDraftSession=128
const DraftBlock=8
var Seeds=[]int{11,29,47,61,79}
var Arms=[]string{"full","verified","unsafe","oracle"}
var Regimes=[]string{"repeatable","shifted"}

type Worker struct {
 Schema string `json:"schema"`
 Arm string `json:"arm"`
 Regime string `json:"regime"`
 Seed int `json:"seed"`
 Sessions int `json:"sessions"`
 Outputs int `json:"outputs"`
 SourceCalls int `json:"source_calls"`
 FitCalls int `json:"fit_calls"`
 VerificationCalls int `json:"verification_calls"`
 Proposals int `json:"draft_proposals"`
 Matches int `json:"verified_matches"`
 Mismatches int `json:"verified_mismatches"`
 TranscriptSHA256 string `json:"transcript_sha256"`
 WorkChecksum uint64 `json:"work_checksum"`
 GoSysBytes uint64 `json:"go_sys_bytes"`
 GoTotalAllocBytes uint64 `json:"go_total_alloc_bytes"`
}
type Sample struct {
 Worker
 CPUUserSystemNS int64 `json:"child_user_system_cpu_ns"`
 ParentWallNS int64 `json:"parent_spawn_exit_wall_ns"`
}
type Ratio struct {
 Regime string `json:"regime"`
 VerifiedOverFullCPU float64 `json:"verified_over_full_cpu_median"`
 VerifiedOverFullGoSys float64 `json:"verified_over_full_go_sys_median"`
 UnsafeWrongTrials int `json:"unsafe_wrong_trials"`
 VerifiedMismatches int `json:"verified_mismatches"`
 FullTranscriptAgreement bool `json:"full_verified_oracle_transcripts_match"`
 FullVerificationCharged bool `json:"full_scalar_verification_charged"`
}
type Report struct{
 Schema string `json:"schema"`
 Scope string `json:"scope"`
 Status string `json:"status"`
 Runs []Sample `json:"runs"`
 Ratios []Ratio `json:"ratios"`
 All36Retained bool `json:"all_36_original_portfolio_retained"`
 NoOriginalEnv bool `json:"original_external_environment_called"`
 NativeModelImprovementProven bool `json:"native_model_inference_improvement_proven"`
}

func targetNext(s byte,shift bool) byte {
 if shift { return (7*s+3)&31 }
 return (5*s+1)&31
}
func targetStep(s byte,shift bool,w *Worker) byte {
 // Scalar target work is mandatory and never elided by the verified arm.
 x:=uint64(s)+0x9e3779b97f4a7c15
 for i:=uint64(1);i<=192;i++{
  x^=x<<13; x^=x>>7; x^=x<<17
  x+=i*0x100000001b3
 }
 w.WorkChecksum^=x
 w.SourceCalls++
 return targetNext(s,shift)
}
func fit(s byte,learned *[32]byte,seen *[32]bool,w *Worker){
 for i:=0;i<FitCallsPerDraftSession;i++ {
  next:=targetStep(s,false,w)
  learned[s]=next
  seen[s]=true
  s=next
  w.FitCalls++
 }
}
func propose(state byte,learned *[32]byte,seen *[32]bool,count int,w *Worker) []byte {
 guesses:=make([]byte,count)
 for i:=0;i<count;i++{
  if !seen[state] {guesses[i]=0} else {guesses[i]=learned[state]}
  state=guesses[i]
  w.Proposals++
 }
 return guesses
}
func runWorker(arm,regime string,seed int)(Worker,error){
 r:=Worker{Schema:"forge.acc38.u02.scalar-go.worker.v1",
  Arm:arm,Regime:regime,Seed:seed,Sessions:Sessions,Outputs:Sessions*OutputsPerSession}
 if seed<0 || (regime!="repeatable"&&regime!="shifted") {return r,errors.New("ACC38_INVALID_WORKER_INPUT")}
 switch arm {case "full","verified","unsafe","oracle":default:return r,errors.New("ACC38_INVALID_ARM")}
 stream:=sha256.New()
 for session:=0;session<Sessions;session++{
  state:=byte((seed+session*17)&31)
  var learned [32]byte
  var seen [32]bool
  if arm=="verified"||arm=="unsafe" {fit(state,&learned,&seen,&r)}
  // Identical target evaluation initial conditions for all arms.
  state=byte((seed*3+session*11)&31)
  shift:=regime=="shifted"
  for pos:=0;pos<OutputsPerSession;{
   if arm=="full"{
    state=targetStep(state,shift,&r)
    writeToken(stream,state)
    pos++
   } else if arm=="oracle" {
    // Deliberately privileged upper bound; never an eligible CPU winner.
    state=targetNext(state,shift)
    writeToken(stream,state)
    pos++
   } else {
    block:=DraftBlock
    if OutputsPerSession-pos<block {block=OutputsPerSession-pos}
    draft:=propose(state,&learned,&seen,block,&r)
    for i:=0;i<len(draft);i++{
     if arm=="unsafe"{
      state=draft[i]
     }else{
      actual:=targetStep(state,shift,&r)
      r.VerificationCalls++
      if draft[i]==actual {r.Matches++}else{r.Mismatches++}
      state=actual
     }
     writeToken(stream,state)
     pos++
     if arm=="verified"&&draft[i]!=state { break } // rollback remaining guesses
    }
   }
  }
 }
 r.TranscriptSHA256=hex.EncodeToString(stream.Sum(nil))
 var mem runtime.MemStats
 runtime.ReadMemStats(&mem)
 r.GoSysBytes=mem.Sys
 r.GoTotalAllocBytes=mem.TotalAlloc
 return r,nil
}
func writeToken(h hash.Hash,b byte) {var one=[1]byte{b};_,_=h.Write(one[:])}
func child(arm,regime string,seed int)(Sample,error) {
 var report Sample
 exe,e:=os.Executable();if e!=nil{return report,e}
 cmd:=exec.Command(exe,"-run=worker","-arm="+arm,"-regime="+regime,fmt.Sprintf("-seed=%d",seed))
 start:=time.Now()
 data,e:=cmd.Output()
 wall:=time.Since(start)
 if e!=nil{return report,fmt.Errorf("ACC38_WORKER_FAILED:%s:%v",arm,e)}
 if cmd.ProcessState==nil{return report,errors.New("ACC38_MISSING_CHILD_CPU_STATE")}
 cpu:=cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()
 if e=json.Unmarshal(data,&report.Worker);e!=nil{return report,e}
 if report.Arm!=arm||report.Regime!=regime||report.Seed!=seed||
    report.Schema!="forge.acc38.u02.scalar-go.worker.v1"{
  return report,errors.New("ACC38_WORKER_IDENTITY_DRIFT")
 }
 report.CPUUserSystemNS=cpu.Nanoseconds()
 report.ParentWallNS=wall.Nanoseconds()
 return report,nil
}
func med(v []float64)float64{
 sort.Float64s(v)
 if len(v)==0{return math.NaN()}
 if len(v)%2>0{return v[len(v)/2]}
 return (v[len(v)/2-1]+v[len(v)/2])/2
}
func indexRuns(rows []Sample)map[string]Sample{
 out:=map[string]Sample{}
 for _,v:=range rows {out[fmt.Sprintf("%s/%s/%d",v.Regime,v.Arm,v.Seed)]=v}
 return out
}
func runDriver()(Report,error) {
 out:=Report{Schema:"forge.acc38.u02.scalar-go.crossos.v1",
  Scope:"ORIGINAL_U02_ONLY_SOURCEFREE_NATIVE_GO_NOT_LLM",
  All36Retained:true,NoOriginalEnv:false,NativeModelImprovementProven:false}
 for _,regime:=range Regimes {
  for j,seed:=range Seeds {
   arms:=append([]string{},Arms...)
   if j%2==1 { // AB/BA pair rotation, then negative arms
    arms=[]string{"verified","full","oracle","unsafe"}
   }
   for _,arm:=range arms {
    row,e:=child(arm,regime,seed);if e!=nil{return out,e}
    out.Runs=append(out.Runs,row)
   }
  }
 }
 idx:=indexRuns(out.Runs)
 if len(idx)!=40||len(out.Runs)!=40{return out,errors.New("ACC38_MISSING_40_SOURCE_WORKERS")}
 allOK:=true
 zeroCPU:=false
 for _,regime:=range Regimes {
  ratiosCPU:=[]float64{};ratiosSys:=[]float64{}
  unsafeWrong:=0; mismatches:=0; transcriptOK:=true; charged:=true
  for _,seed:=range Seeds{
   k:=func(arm string)string{return fmt.Sprintf("%s/%s/%d",regime,arm,seed)}
   full:=idx[k("full")];verified:=idx[k("verified")]
   unsafe:=idx[k("unsafe")];oracle:=idx[k("oracle")]
   if verified.TranscriptSHA256!=full.TranscriptSHA256||
      oracle.TranscriptSHA256!=full.TranscriptSHA256 {transcriptOK=false}
   if unsafe.TranscriptSHA256!=full.TranscriptSHA256 {unsafeWrong++}
   if (verified.VerificationCalls!=Sessions*OutputsPerSession||
       full.SourceCalls!=Sessions*OutputsPerSession||
       verified.SourceCalls!=Sessions*(OutputsPerSession+FitCallsPerDraftSession)||
       verified.FitCalls!=Sessions*FitCallsPerDraftSession||
       unsafe.VerificationCalls!=0||oracle.SourceCalls!=0){
     charged=false
   }
   mismatches+=verified.Mismatches
   if full.CPUUserSystemNS<=0||verified.CPUUserSystemNS<=0{zeroCPU=true}
   if full.CPUUserSystemNS>0{
    ratiosCPU=append(ratiosCPU,float64(verified.CPUUserSystemNS)/float64(full.CPUUserSystemNS))
   }
   if full.GoSysBytes==0{charged=false}else{
    ratiosSys=append(ratiosSys,float64(verified.GoSysBytes)/float64(full.GoSysBytes))
   }
  }
  if regime=="shifted"&&(unsafeWrong!=5||mismatches==0){charged=false}
  if regime=="repeatable"&&unsafeWrong!=0{charged=false}
  r:=Ratio{Regime:regime,UnsafeWrongTrials:unsafeWrong,
    VerifiedMismatches:mismatches,FullTranscriptAgreement:transcriptOK,
    FullVerificationCharged:charged}
  if len(ratiosCPU)==5{r.VerifiedOverFullCPU=med(ratiosCPU)}
  if len(ratiosSys)==5{r.VerifiedOverFullGoSys=med(ratiosSys)}
  out.Ratios=append(out.Ratios,r)
  if !transcriptOK||!charged {return out,errors.New("ACC38_SOURCE_FIDELITY_OR_VERIFICATION_FAILED")}
  if r.VerifiedOverFullCPU>0.90||r.VerifiedOverFullGoSys>1.10 {allOK=false}
 }
 if zeroCPU {out.Status="ACC38_PROTOCOL_OR_METER_BLOCKED"} else if allOK {
  out.Status="ACC38_U02_SCALAR_VERIFIED_GO_CPU_WIN_ENGINEERING_ONLY"
 } else {out.Status="ACC38_U02_NO_VERIFIED_SCALAR_CPU_GAIN"}
 return out,nil
}
func main() {
 run:=flag.String("run","worker","worker or driver")
 arm:=flag.String("arm","full","worker arm")
 regime:=flag.String("regime","repeatable","source regime")
 seed:=flag.Int("seed",11,"source seed")
 output:=flag.String("output","","driver report path")
 flag.Parse()
 if *run=="worker"{
  x,e:=runWorker(*arm,*regime,*seed);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if e=json.NewEncoder(os.Stdout).Encode(x);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 }else if *run=="driver"{
  x,e:=runDriver()
  if *output==""{fmt.Fprintln(os.Stderr,"ACC38_OUTPUT_PATH_REQUIRED");os.Exit(2)}
  b,jerr:=json.MarshalIndent(x,"","  ")
  if jerr==nil{jerr=os.WriteFile(*output,append(b,'\n'),0644)}
  if jerr!=nil{fmt.Fprintln(os.Stderr,jerr);os.Exit(2)}
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  fmt.Printf("ACC38_CLASSIFICATION=%s\n",x.Status)
  for _,r:=range x.Ratios{fmt.Printf("ACC38_%s_VERIFIED_CPU_RATIO=%.6f GO_SYS_RATIO=%.6f MISMATCHES=%d UNSAFE_WRONG=%d\n",r.Regime,r.VerifiedOverFullCPU,r.VerifiedOverFullGoSys,r.VerifiedMismatches,r.UnsafeWrongTrials)}
 }else {fmt.Fprintln(os.Stderr,"ACC38_UNKNOWN_MODE");os.Exit(2)}
}
