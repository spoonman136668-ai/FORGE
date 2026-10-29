package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"math";"os";"os/exec";"runtime";"sort";"time")
const(schema="forge.acc51.original-u15.nativego.v1";episodes=48;size=65536)
var seeds=[]uint64{101101,101103,101107,101109,101111}
var regimes=[]string{"CHAIN","BRANCH","MIXED","IDENTITY"}
var arms=[]string{"UNFUSED","TILED","INPLACE","FUSED"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func source(seed uint64,ep int,regime string)[]float64{
 out:=make([]float64,size);for i:=range out{u:=mix(seed^uint64(ep)*0xbf58476d1ce4e5b9^uint64(i)*0x94d049bb133111eb)
  v:=float64(int64(u%20001)-10000)/4096
  if regime=="MIXED"&&i%2==1{v=-v};out[i]=v
 };return out
}
func op1(x float64,regime string)float64{if regime=="IDENTITY"{return x*1};return x*1.5}
func op2(x float64,regime string)float64{if regime=="IDENTITY"{return x+0};return x+2}
func op3(x float64,regime string)float64{if regime=="IDENTITY"{return x*1};if regime=="BRANCH"{return x*1.25};return x*0.75}
func op4(x float64,regime string)float64{if regime=="IDENTITY"{return x+0};if regime=="BRANCH"{return x+1.25};return x+1}
func truth(x float64,regime string)float64{return op4(op3(op2(op1(x,regime),regime),regime),regime)}
func apply(in []float64,regime,arm string)([]float64,int,error){
 n:=len(in)
 switch arm{
 case "FUSED":
  out:=make([]float64,n);for i,x:=range in{out[i]=truth(x,regime)};return out,n*8,nil
 case "INPLACE":
  out:=append([]float64(nil),in...);for i:=range out{out[i]=op1(out[i],regime)}
  for i:=range out{out[i]=op2(out[i],regime)}
  for i:=range out{out[i]=op3(out[i],regime)}
  for i:=range out{out[i]=op4(out[i],regime)}
  return out,n*8,nil
 case "TILED":
  out:=make([]float64,n);scratch:=make([]float64,4096)
  for b:=0;b<n;b+=4096{
   m:=4096;if n-b<m{m=n-b}
   for j:=0;j<m;j++{scratch[j]=op1(in[b+j],regime)}
   for j:=0;j<m;j++{scratch[j]=op2(scratch[j],regime)}
   for j:=0;j<m;j++{scratch[j]=op3(scratch[j],regime)}
   for j:=0;j<m;j++{out[b+j]=op4(scratch[j],regime)}
  };return out,(n+4096)*8,nil
 case "UNFUSED":
  a:=make([]float64,n);b:=make([]float64,n);c:=make([]float64,n);out:=make([]float64,n)
  for i,x:=range in{a[i]=op1(x,regime)}
  for i,x:=range a{b[i]=op2(x,regime)}
  for i,x:=range b{c[i]=op3(x,regime)}
  for i,x:=range c{out[i]=op4(x,regime)}
  return out,n*4*8,nil
 };return nil,0,errors.New("invalid arm")
}
func hashFloat(h interface{Write([]byte)(int,error)},x float64){var buf[8]byte;binary.LittleEndian.PutUint64(buf[:],math.Float64bits(x));h.Write(buf[:])}
type worker struct{Schema,Arm,Regime,InputSHA256,TruthSHA256,OutputSHA256,MemoryMetric string;Seed uint64;Episodes,Elements,PeakScratchBytes int;PeakRSSBytes uint64}
func work(arm,regime string,seed uint64)(worker,error){
 var w worker;ok:=false;for _,s:=range arms{if s==arm{ok=true}};if !ok{return w,errors.New("invalid arm")}
 ok=false;for _,s:=range regimes{if s==regime{ok=true}};if !ok{return w,errors.New("invalid regime")}
 input,truthhash,out:=sha256.New(),sha256.New(),sha256.New();peak:=0
 for ep:=0;ep<episodes;ep++{
  data:=source(seed,ep,regime)
  for _,x:=range data{hashFloat(input,x)}
  actual,scratch,err:=apply(data,regime,arm);if err!=nil{return w,err}
  if scratch>peak{peak=scratch}
  for i,x:=range data{expected:=truth(x,regime);hashFloat(truthhash,expected);hashFloat(out,actual[i]);if math.Float64bits(actual[i])!=math.Float64bits(expected){return w,errors.New("not bit-exact")}}
 }
 rss,e:=peakResidentBytes();if e!=nil{return w,e};if rss==0{return w,errors.New("missing OS peak RSS")}
 return worker{Schema:schema,Arm:arm,Regime:regime,Seed:seed,Episodes:episodes,Elements:episodes*size,PeakScratchBytes:peak,PeakRSSBytes:rss,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",InputSHA256:hex.EncodeToString(input.Sum(nil)),TruthSHA256:hex.EncodeToString(truthhash.Sum(nil)),OutputSHA256:hex.EncodeToString(out.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type comparison struct{Regime,Fastest string;CPU,RSS,Scratch map[string]float64;CPURatio,RSSRatio,ScratchRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;NativeModelAcceleration,ScientificFirstUse bool;Records []trial;Comparisons []comparison}
func med(a []float64)float64{v:=append([]float64(nil),a...);sort.Float64s(v);n:=len(v);if n==0{return math.NaN()};if n%2==0{return (v[n/2-1]+v[n/2])/2};return v[n/2]}
func run(exe,arm,regime string,seed uint64)(trial,error){var t trial;c:=exec.Command(exe,"-worker","-arm",arm,"-regime",regime,"-seed",fmt.Sprint(seed));var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return t,fmt.Errorf("%s/%s/%d: %w %s",arm,regime,seed,err,stderr.String())};if c.ProcessState==nil{return t,errors.New("missing child")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return t,errors.New("missing real CPU/wall")}
 var w worker;if e:=json.Unmarshal(stdout.Bytes(),&w);e!=nil{return t,e}
 if w.Schema!=schema||w.Arm!=arm||w.Regime!=regime||w.Seed!=seed||w.Episodes!=episodes||w.Elements!=episodes*size||w.PeakRSSBytes==0||w.PeakScratchBytes<=0||w.TruthSHA256!=w.OutputSHA256||len(w.InputSHA256)!=64{return t,errors.New("invalid receipt")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil}
func compare(rows []trial,regime string)(comparison,error){
 c:=comparison{Regime:regime,CPU:map[string]float64{},RSS:map[string]float64{},Scratch:map[string]float64{}};groups:=map[string][]trial{};paired:=map[uint64]string{}
 for _,r:=range rows{w:=r.Worker;if w.Regime!=regime{continue};groups[w.Arm]=append(groups[w.Arm],r)
  h:=w.InputSHA256+"/"+w.TruthSHA256;if z,ok:=paired[w.Seed];ok&&z!=h{return c,errors.New("source mismatch")};paired[w.Seed]=h
 }
 if len(paired)!=len(seeds){return c,errors.New("missing seed")}
 for _,arm:=range arms{a:=groups[arm];if len(a)!=len(seeds){return c,errors.New("missing arm")};var cpu,rss,scratch []float64
  for _,r:=range a{cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes));scratch=append(scratch,float64(r.Worker.PeakScratchBytes))}
  c.CPU[arm]=med(cpu);c.RSS[arm]=med(rss);c.Scratch[arm]=med(scratch)
 }
 c.Fastest="UNFUSED";for _,a:=range []string{"TILED","INPLACE"}{if c.CPU[a]<c.CPU[c.Fastest]{c.Fastest=a}}
 c.CPURatio=c.CPU["FUSED"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["FUSED"]/c.RSS[c.Fastest];c.ScratchRatio=c.Scratch["FUSED"]/c.Scratch["UNFUSED"]
 c.Pass=c.CPURatio<=.90&&c.RSSRatio<=1.10&&c.ScratchRatio<=.50;return c,nil
}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS,Records:make([]trial,0,80)}
 for _,regime:=range regimes{for i,seed:=range seeds{order:=[]string{"UNFUSED","TILED","INPLACE","FUSED"};if i%2==1{order=[]string{"FUSED","INPLACE","TILED","UNFUSED"}}
  for _,arm:=range order{row,err:=run(exe,arm,regime,seed);if err!=nil{return err};r.Records=append(r.Records,row)}
 }
 c,err:=compare(r.Records,regime);if err!=nil{return err};r.Comparisons=append(r.Comparisons,c)}
 if len(r.Records)!=80{return errors.New("not 80 workers")};r.NativeChildCount=len(r.Records)
 r.Classification="U15_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,v:=range r.Comparisons{pass=pass&&v.Pass};if pass{r.Classification="U15_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC51_U15_80_COLD_WORKERS=PASS");fmt.Println("ACC51_U15_CLASSIFICATION="+r.Classification);return nil
}
func main(){cw:=flag.Bool("worker",false,"");arm:=flag.String("arm","FUSED","");regime:=flag.String("regime","CHAIN","");seed:=flag.Uint64("seed",101101,"");out:=flag.String("out","acc51-report.json","");flag.Parse()
 var err error;if *cw{var w worker;w,err=work(*arm,*regime,*seed);if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}}else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC51_U15_BLOCKED:",err);os.Exit(1)}
}
