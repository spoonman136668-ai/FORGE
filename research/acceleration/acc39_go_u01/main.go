// ACC-39: genuine compiled Go, source-free original U01 JIT decompression
// Original 36-ID portfolio remains independent; no actual LLM/model tensor claims.
package main

import (
 "bytes"
 "compress/zlib"
 "crypto/sha256"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math/bits"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "time"
)
const (RawBytes=262144; Sessions=8; Passes=16; Trials=5; BufferBytes=32768)
type Mode string
const(RAW Mode="RAW"; JIT Mode="JIT"; CACHED Mode="CACHED"; STREAM Mode="STREAM")
type Cohort string
const(REPEATED Cohort="REPEATED"; RANDOM Cohort="RANDOM")
type Worker struct {
 Mode Mode `json:"mode"`
 Cohort Cohort `json:"cohort"`
 Sessions int `json:"sessions"`
 Passes int `json:"passes"`
 SourceBytes int `json:"source_bytes"`
 CompressedBytesTotal int `json:"compressed_bytes_total"`
 DecodedBytesTotal int `json:"decoded_bytes_total"`
 TraceDigest string `json:"trace_digest"`
 GoSysBytes uint64 `json:"go_sys_bytes"`
 GoTotalAllocBytes uint64 `json:"go_total_alloc_bytes"`
}
type Record struct{
 Worker Worker `json:"worker"`
 Trial int `json:"trial"`
 ProcessCPUNS int64 `json:"process_cpu_ns"`
 WallNS int64 `json:"parent_wall_ns"`
}
type Comparison struct {
 JITCPUOverRaw float64 `json:"jit_cpu_over_raw"`
 JITSysOverRaw float64 `json:"jit_sys_over_raw"`
 StreamCPUOverRaw float64 `json:"stream_cpu_over_raw"`
 StreamSysOverRaw float64 `json:"stream_sys_over_raw"`
 CachedCPUOverRaw float64 `json:"cached_cpu_over_raw"`
 StoredCompressedOverRaw float64 `json:"stored_compressed_over_raw"`
 AllTraceEqual bool `json:"all_trace_equal"`
}
type Report struct{
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 OS string `json:"os"`
 Arch string `json:"arch"`
 GoVersion string `json:"go_version"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 RealLLMAccelerationProven bool `json:"real_llm_acceleration_proven"`
 PortfolioOriginalCount int `json:"portfolio_original_count"`
 PortfolioNewCount int `json:"portfolio_new_count"`
 NativeGoChildCount int `json:"native_go_child_count"`
 Comparisons map[string]Comparison `json:"comparisons"`
 Records []Record `json:"records"`
}
func source(c Cohort)([]byte,error){
 if c!=REPEATED&&c!=RANDOM{return nil,errors.New("ACC39_UNREGISTERED_SOURCE")}
 seed:=uint64(431)
 step:=func()byte{
  seed ^= seed<<13;seed ^= seed>>7;seed ^= seed<<17
  return byte(seed>>40)
 }
 data:=make([]byte,RawBytes)
 if c==REPEATED{
  tile:=make([]byte,256)
  for i:=range tile{tile[i]=step()}
  for i:=range data{data[i]=tile[i%len(tile)]}
 }else{
  for i:=range data{data[i]=step()}
 }
 return data,nil
}
func encode(data []byte)([]byte,error){
 var b bytes.Buffer
 z,err:=zlib.NewWriterLevel(&b,zlib.BestSpeed)
 if err!=nil{return nil,err}
 if _,err=z.Write(data);err!=nil{return nil,err}
 if err=z.Close();err!=nil{return nil,err}
 return b.Bytes(),nil
}
func decode(data []byte)([]byte,error){
 z,err:=zlib.NewReader(bytes.NewReader(data))
 if err!=nil{return nil,err}
 result,err:=io.ReadAll(io.LimitReader(z,RawBytes+1))
 closeErr:=z.Close()
 if err!=nil{return nil,err}
 if closeErr!=nil{return nil,closeErr}
 if len(result)!=RawBytes{return nil,errors.New("ACC39_DECODE_SIZE_MISMATCH")}
 return result,nil
}
type Feed struct{Value uint64; Size int}
func newFeed()Feed{return Feed{Value:0xcbf29ce484222325}}
func (f *Feed) update(raw []byte){
 for _,v:=range raw{
  f.Value=bits.RotateLeft64(f.Value^uint64(v),7)*0x9e3779b97f4a7c15
 }
 f.Size+=len(raw)
}
func scanWhole(data []byte,truth [32]byte)(uint64,error){
 if len(data)!=RawBytes||sha256.Sum256(data)!=truth{return 0,errors.New("ACC39_RAW_SOURCE_CORRUPTION")}
 f:=newFeed();f.update(data)
 return f.Value,nil
}
func scanStream(compressed []byte,truth [32]byte)(uint64,error){
 z,e:=zlib.NewReader(bytes.NewReader(compressed))
 if e!=nil{return 0,e}
 var f=newFeed()
 var content bytes.Buffer
 // Buffer is strictly bounded to 32KiB per read; 32-byte SHA verification
 // is performed over the same ordered bytes, not a second decoded copy.
 // Using a bytes.Buffer here would defeat streaming memory advantage, so
 // hash incrementally via sha256.New instead.
 _=content
 h:=sha256.New()
 buf:=make([]byte,BufferBytes)
 for{
  n,err:=z.Read(buf)
  if n>0{
   if f.Size+n>RawBytes{_ =z.Close();return 0,errors.New("ACC39_OVERLONG_STREAM")}
   f.update(buf[:n])
   _,_=h.Write(buf[:n])
  }
  if err==io.EOF{break}
  if err!=nil{_ =z.Close();return 0,err}
  if n==0{_ =z.Close();return 0,errors.New("ACC39_SOURCE_STALLED")}
 }
 if err=z.Close();err!=nil{return 0,err}
 if f.Size!=RawBytes||!bytes.Equal(h.Sum(nil),truth[:]){
  return 0,errors.New("ACC39_STREAM_SOURCE_OR_LENGTH_MISMATCH")
 }
 return f.Value,nil
}
func runWorker(mode Mode,cohort Cohort)(Worker,error){
 if mode!=RAW&&mode!=JIT&&mode!=CACHED&&mode!=STREAM{return Worker{},errors.New("ACC39_UNREGISTERED_ARM")}
 if cohort!=REPEATED&&cohort!=RANDOM{return Worker{},errors.New("ACC39_UNREGISTERED_COHORT")}
 out:=Worker{Mode:mode,Cohort:cohort,Sessions:Sessions,Passes:Passes,SourceBytes:RawBytes}
 trace:=uint64(0x6a09e667f3bcc909)
 for session:=0;session<Sessions;session++{
  data,e:=source(cohort);if e!=nil{return out,e}
  truth:=sha256.Sum256(data)
  var comp,cached []byte
  if mode!=RAW{
   comp,e=encode(data);if e!=nil{return out,e}
   out.CompressedBytesTotal+=len(comp)
  }
  if mode==CACHED{
   cached,e=decode(comp);if e!=nil{return out,e}
   if sha256.Sum256(cached)!=truth{return out,errors.New("ACC39_CACHE_CORRUPTION")}
  }
  for pass:=0;pass<Passes;pass++{
   var value uint64
   switch mode{
   case RAW: value,e=scanWhole(data,truth)
   case CACHED: value,e=scanWhole(cached,truth);out.DecodedBytesTotal+=RawBytes
   case JIT:
    var decoded []byte
    decoded,e=decode(comp)
    if e==nil{value,e=scanWhole(decoded,truth);out.DecodedBytesTotal+=len(decoded)}
   case STREAM:
    value,e=scanStream(comp,truth)
    if e==nil{out.DecodedBytesTotal+=RawBytes}
   }
   if e!=nil{return out,e}
   trace=bits.RotateLeft64(trace,3)^value^uint64(pass+1)*0x9e3779b97f4a7c15^uint64(session+1)
  }
 }
 out.TraceDigest=fmt.Sprintf("%016x",trace)
 var m runtime.MemStats
 runtime.ReadMemStats(&m)
 out.GoSysBytes=m.Sys;out.GoTotalAllocBytes=m.TotalAlloc
 return out,nil
}
func trial(mode Mode,cohort Cohort,index int)(Record,error){
 path,e:=os.Executable();if e!=nil{return Record{},e}
 cmd:=exec.Command(path,"-worker","-mode",string(mode),"-cohort",string(cohort))
 var stdout,stderr bytes.Buffer;cmd.Stdout=&stdout;cmd.Stderr=&stderr
 start:=time.Now()
 e=cmd.Run();wall:=time.Since(start).Nanoseconds()
 if e!=nil{return Record{},fmt.Errorf("ACC39_WORKER_FAILED %v %s",e,stderr.String())}
 if cmd.ProcessState==nil{return Record{},errors.New("ACC39_PROCESS_STATE_MISSING")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Nanoseconds()
 var w Worker
 if e=json.Unmarshal(stdout.Bytes(),&w);e!=nil{return Record{},e}
 if cpu<=0||w.Mode!=mode||w.Cohort!=cohort||w.Sessions!=Sessions||
  w.Passes!=Passes||w.SourceBytes!=RawBytes||w.GoSysBytes==0||
  (mode!=RAW&&w.CompressedBytesTotal==0)||
  (mode==RAW&&w.CompressedBytesTotal!=0){
  return Record{},errors.New("ACC39_INVALID_CPU_OR_SOURCE_RECEIPT")
 }
 return Record{w,index,cpu,wall},nil
}
func median(x []float64)float64{
 if len(x)!=Trials{return 0}
 sort.Float64s(x)
 return x[len(x)/2]
}
func compare(records []Record,scenario Cohort)(Comparison,error){
 m:=map[Mode][]Record{}
 for _,r:=range records{if r.Worker.Cohort==scenario{m[r.Worker.Mode]=append(m[r.Worker.Mode],r)}}
 for _,k:=range []Mode{RAW,JIT,CACHED,STREAM}{
  if len(m[k])!=Trials{return Comparison{},errors.New("ACC39_MISSING_TRIALS")}
 }
 c:=Comparison{AllTraceEqual:true}
 rawTrace:=m[RAW][0].Worker.TraceDigest
 cpuJ,cpuS,cpuC:=[]float64{},[]float64{},[]float64{}
 sysJ,sysS,ratios:=[]float64{},[]float64{},[]float64{}
 for i:=0;i<Trials;i++{
  a,j,s,cache:=m[RAW][i],m[JIT][i],m[STREAM][i],m[CACHED][i]
  for _,v:=range []Record{a,j,s,cache}{
   if v.Worker.TraceDigest!=rawTrace {c.AllTraceEqual=false}
  }
  cpuJ=append(cpuJ,float64(j.ProcessCPUNS)/float64(a.ProcessCPUNS))
  cpuS=append(cpuS,float64(s.ProcessCPUNS)/float64(a.ProcessCPUNS))
  cpuC=append(cpuC,float64(cache.ProcessCPUNS)/float64(a.ProcessCPUNS))
  sysJ=append(sysJ,float64(j.Worker.GoSysBytes)/float64(a.Worker.GoSysBytes))
  sysS=append(sysS,float64(s.Worker.GoSysBytes)/float64(a.Worker.GoSysBytes))
  ratios=append(ratios,float64(j.Worker.CompressedBytesTotal)/(Sessions*RawBytes))
  if j.Worker.CompressedBytesTotal!=s.Worker.CompressedBytesTotal||
     s.Worker.CompressedBytesTotal!=cache.Worker.CompressedBytesTotal{
   return c,errors.New("ACC39_INCONSISTENT_ENCODED_STORAGE")
  }
  if j.Worker.DecodedBytesTotal!=Sessions*Passes*RawBytes||
     s.Worker.DecodedBytesTotal!=Sessions*Passes*RawBytes||
     cache.Worker.DecodedBytesTotal!=Sessions*Passes*RawBytes{
   return c,errors.New("ACC39_INCOMPLETE_DECOMPRESSION")
  }
 }
 if !c.AllTraceEqual{return c,errors.New("ACC39_INCORRECT_BYTE_TRACE")}
 c.JITCPUOverRaw=median(cpuJ)
 c.StreamCPUOverRaw=median(cpuS)
 c.CachedCPUOverRaw=median(cpuC)
 c.JITSysOverRaw=median(sysJ)
 c.StreamSysOverRaw=median(sysS)
 c.StoredCompressedOverRaw=median(ratios)
 return c,nil
}
func report()(Report,error){
 result:=Report{Schema:"forge.acc39.original-u01-native-go-jit-decompression.v1",
  Classification:"ACC39_U01_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN",
  OS:runtime.GOOS,Arch:runtime.GOARCH,GoVersion:runtime.Version(),
  PortfolioOriginalCount:30,PortfolioNewCount:6,
  Comparisons:map[string]Comparison{},Records:[]Record{}}
 for _,c:=range []Cohort{REPEATED,RANDOM}{
  for i:=0;i<Trials;i++{
   order:=[]Mode{RAW,JIT}
   if i%2==1{order=[]Mode{JIT,RAW}}
   order=append(order,CACHED,STREAM)
   for _,m:=range order{
    r,e:=trial(m,c,i);if e!=nil{return result,e}
    result.Records=append(result.Records,r)
   }
  }
  summary,e:=compare(result.Records,c)
  if e!=nil{return result,e}
  result.Comparisons[string(c)]=summary
 }
 result.NativeGoChildCount=len(result.Records)
 if result.NativeGoChildCount!=40{return result,errors.New("ACC39_BAD_WORKER_COUNT")}
 positive:=true
 for _,c:=range []Cohort{REPEATED,RANDOM}{
  q:=result.Comparisons[string(c)]
  if q.JITCPUOverRaw>0.90||q.StreamCPUOverRaw>0.90||
     q.JITSysOverRaw>1.10||q.StreamSysOverRaw>1.10||
     q.StoredCompressedOverRaw>0.75{positive=false}
 }
 if positive{result.Classification="ACC39_U01_GO_JIT_STREAM_BOTH_COHORTS_RESOURCE_POSITIVE__NO_LLM_SCIENCE"}
 return result,nil
}
func main(){
 worker:=flag.Bool("worker",false,"worker")
 mode:=flag.String("mode","","mode")
 cohort:=flag.String("cohort","","cohort")
 out:=flag.String("out","","output")
 flag.Parse()
 if *worker{
  w,e:=runWorker(Mode(*mode),Cohort(*cohort))
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if e=json.NewEncoder(os.Stdout).Encode(w);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  return
 }
 r,e:=report()
 if e!=nil{fmt.Fprintln(os.Stderr,"ACC39_PROTOCOL_BLOCKED",e);os.Exit(2)}
 data,e:=json.MarshalIndent(r,"","  ")
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if *out!=""{if e=os.WriteFile(*out,append(data,'\n'),0644);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
 fmt.Println("ACC39_CLASSIFICATION",r.Classification)
 for k,v:=range r.Comparisons{
  fmt.Printf("ACC39_%s_JIT_CPU=%.6f STREAM_CPU=%.6f CACHED_CPU=%.6f COMPRESSED_BYTES=%.6f\n",
   k,v.JITCPUOverRaw,v.StreamCPUOverRaw,v.CachedCPUOverRaw,v.StoredCompressedOverRaw)
 }
 fmt.Println("ACC39_NATIVE_GO_CHILDREN",r.NativeGoChildCount)
}
