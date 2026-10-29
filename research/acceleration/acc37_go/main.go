// ACC-37 source-free compiled Go U11/U15 original-portfolio falsification.
// Never a Wingless/Yggdrasil production model or actual token-inference benchmark.
package main
import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "time"
)
const (N=128; K=256; Batches=64; Sessions=8; Trials=5)
const Schema="forge.acc37.u11-u15.actual-go-kernel.v1"
type Row [K]int8
type Inputs [K]int16
type Weights [N]Row
type Batch struct{In Inputs; W Weights; Bias [N]int32}
type Rec struct{Mode string; Scene string; SHA256 string; Rows int; GoRuntimeSysBytes uint64; TotalAllocBytes uint64}
type Trial struct{Mode string; Scene string; Trial int; ProcessCPUNanoseconds int64; SpawnWallNanoseconds int64; Rec Rec}
type Summary struct{
 Scene string
 TernaryCPUOverBase float64
 FusedCPUOverBase float64
 BothCPUOverBase float64
 TernarySysOverBase float64
 FusedSysOverBase float64
 BothSysOverBase float64
 Exact bool
}
type Report struct{
 Schema string
 OS string
 CandidateIDs []string
 OriginalSourceEpisodes int
 ScientificFirstUse bool
 NativeModelIntegrated bool
 Classification map[string]string
 Summaries []Summary
 Trials []Trial
}
func next(x *uint64) uint64{
 *x^=*x>>12; *x^=*x<<25; *x^=*x>>27
 return *x*2685821657736338717
}
func data(scene string,session,batch int)Batch{
 seed:=uint64(0x123a9e7f)+uint64(session*131+batch*17)
 var b Batch
 for k:=0;k<K;k++{b.In[k]=int16(next(&seed)%255)-127}
 for n:=0;n<N;n++{
  b.Bias[n]=int32(next(&seed)%2001)-1000
  for k:=0;k<K;k++{
   x:=int(next(&seed)%100)
   if scene=="sparse"{
    if x<82{b.W[n][k]=0}else if x<91{b.W[n][k]=-1}else{b.W[n][k]=1}
   }else{
    if x<15{b.W[n][k]=0}else if x<58{b.W[n][k]=-1}else{b.W[n][k]=1}
   }
  }
 }
 return b
}
func clamp(x int32)int32{if x<0{return 0};if x>32767{return 32767};return x}
func evaluate(b *Batch,mode string)*[N]int32{
 var out [N]int32
 fused:=mode=="fused"||mode=="both"
 ternary:=mode=="ternary"||mode=="both"
 if fused{
  for n:=0;n<N;n++{
   sum:=b.Bias[n]
   for k:=0;k<K;k++{
    if ternary{
     if b.W[n][k]>0{sum+=int32(b.In[k])}else if b.W[n][k]<0{sum-=int32(b.In[k])}
    }else{sum+=int32(b.W[n][k])*int32(b.In[k])}
   }
   out[n]=clamp(sum)
  }
 }else{
  for n:=0;n<N;n++{
   var sum int32
   for k:=0;k<K;k++{
    if ternary{
     if b.W[n][k]>0{sum+=int32(b.In[k])}else if b.W[n][k]<0{sum-=int32(b.In[k])}
    }else{sum+=int32(b.W[n][k])*int32(b.In[k])}
   }
   out[n]=sum
  }
  for n:=0;n<N;n++{out[n]=clamp(out[n]+b.Bias[n])}
 }
 return &out
}
func worker(mode,scene string)(Rec,error){
 if !(mode=="base"||mode=="ternary"||mode=="fused"||mode=="both")||
  !(scene=="dense"||scene=="sparse"){return Rec{},errors.New("ACC37_FROZEN_ARM_OR_SCENE")}
 h:=sha256.New()
 var buf [4]byte
 for s:=0;s<Sessions;s++{
  for i:=0;i<Batches;i++{
   b:=data(scene,s,i)
   out:=evaluate(&b,mode)
   for _,v:=range out{
    binary.LittleEndian.PutUint32(buf[:],uint32(v))
    _,_=h.Write(buf[:])
   }
  }
 }
 var mem runtime.MemStats;runtime.ReadMemStats(&mem)
 return Rec{mode,scene,hex.EncodeToString(h.Sum(nil)),N*Batches*Sessions,mem.Sys,mem.TotalAlloc},nil
}
func child(exe,mode,scene string,trial int)(Trial,error){
 started:=time.Now()
 cmd:=exec.Command(exe,"worker",mode,scene)
 out,err:=cmd.CombinedOutput()
 if err!=nil{return Trial{},fmt.Errorf("ACC37_CHILD_%s_%s: %w: %s",mode,scene,err,string(out))}
 var r Rec
 if err=json.Unmarshal(out,&r);err!=nil{return Trial{},err}
 if r.Mode!=mode||r.Scene!=scene||r.Rows!=N*Batches*Sessions{
  return Trial{},errors.New("ACC37_CHILD_RESULT_IDENTITY_DRIFT")
 }
 if cmd.ProcessState==nil{return Trial{},errors.New("ACC37_CPU_METER_MISSING")}
 cpu:=cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()
 if cpu<=0{return Trial{},errors.New("ACC37_CHILD_CPU_COUNTER_UNAVAILABLE")}
 return Trial{mode,scene,trial,cpu.Nanoseconds(),time.Since(started).Nanoseconds(),r},nil
}
func median(a []float64)float64{
 b:=append([]float64(nil),a...)
 sort.Float64s(b)
 return b[len(b)/2]
}
func makeReport(exe string)(Report,error){
 r:=Report{Schema:Schema,OS:runtime.GOOS,CandidateIDs:[]string{"U11","U15"},
  Classification:map[string]string{}}
 pass11,pass15,passBoth:=true,true,true
 for _,scene:=range []string{"dense","sparse"}{
  cpu:=map[string][]float64{"ternary":{},"fused":{},"both":{}}
  sys:=map[string][]float64{"ternary":{},"fused":{},"both":{}}
  for trial:=0;trial<Trials;trial++{
   modes:=[]string{"base","ternary","fused","both"}
   if trial%2!=0{modes=[]string{"both","fused","ternary","base"}}
   one:=map[string]Trial{}
   for _,mode:=range modes{
    x,err:=child(exe,mode,scene,trial)
    if err!=nil{return r,err}
    r.Trials=append(r.Trials,x);one[mode]=x
   }
   base:=one["base"]
   for _,mode:=range []string{"ternary","fused","both"}{
    x:=one[mode]
    if x.Rec.SHA256!=base.Rec.SHA256{return r,errors.New("ACC37_EXACT_OUTPUT_MISMATCH")}
    cpu[mode]=append(cpu[mode],float64(x.ProcessCPUNanoseconds)/float64(base.ProcessCPUNanoseconds))
    sys[mode]=append(sys[mode],float64(x.Rec.GoRuntimeSysBytes)/float64(base.Rec.GoRuntimeSysBytes))
   }
  }
  s:=Summary{scene,median(cpu["ternary"]),median(cpu["fused"]),median(cpu["both"]),
   median(sys["ternary"]),median(sys["fused"]),median(sys["both"]),true}
  r.Summaries=append(r.Summaries,s)
  if s.TernaryCPUOverBase>0.90||s.TernarySysOverBase>1.10{pass11=false}
  if s.FusedCPUOverBase>0.90||s.FusedSysOverBase>1.10{pass15=false}
  if s.BothCPUOverBase>0.80||s.BothSysOverBase>1.10{passBoth=false}
 }
 if pass11{r.Classification["U11"]="GO_KERNEL_ENGINEERING_POSITIVE_NOT_MODEL"
 }else{r.Classification["U11"]="NO_VERIFIED_GO_KERNEL_CPU_WIN"}
 if pass15{r.Classification["U15"]="GO_KERNEL_ENGINEERING_POSITIVE_NOT_MODEL"
 }else{r.Classification["U15"]="NO_VERIFIED_GO_KERNEL_CPU_WIN"}
 if passBoth{r.Classification["U11_U15"]="GO_KERNEL_COMBINED_POSITIVE_NOT_MODEL"
 }else{r.Classification["U11_U15"]="NO_VERIFIED_COMBINED_CPU_WIN"}
 return r,nil
}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"ACC37_MODE_REQUIRED");os.Exit(2)}
 switch os.Args[1]{
 case "worker":
  if len(os.Args)!=4{os.Exit(2)}
  x,e:=worker(os.Args[2],os.Args[3]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  _=json.NewEncoder(os.Stdout).Encode(x)
 case "report":
  exe,_:=os.Executable();x,e:=makeReport(exe)
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  _=json.NewEncoder(os.Stdout).Encode(x)
 default:
  os.Exit(2)
 }
}