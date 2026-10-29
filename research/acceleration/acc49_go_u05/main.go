package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"math";"os";"os/exec";"runtime";"sort";"time")
const(schema="forge.acc49.original-u05.nativego.v1";sessions=32;steps=8192)
var seeds=[]uint64{99101,99103,99107,99109,99111}
var cohorts=[]string{"REPEATED_INPUT","RECURRENT_STATE","NOVEL"}
var modes=[]string{"DIRECT","LRU64","LRU1024","U05_LOOKUP"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func transition(state uint64,input uint32)uint64{x:=state^(uint64(input)<<32)^0x85157eaa21db5a3e;for n:=0;n<64;n++{x=mix(x^uint64(n)*0xd6e8feb86659fd93)};return x}
func source(cohort string,seed uint64,session,step int)(uint64,uint32){
 base:=mix(seed^uint64(session)*0x9e3779b97f4a7c15)
 state:=mix(base^uint64(step)*0xbf58476d1ce4e5b9)
 input:=uint32(mix(base^uint64(step)*0x94d049bb133111eb))
 switch cohort{
 case "REPEATED_INPUT":input=uint32(mix(base^uint64(step%16)))
 case "RECURRENT_STATE":state=mix(base^uint64(step%64));input=uint32(mix(base^uint64(step%64)*0x94d049bb133111eb))
 }
 return state,input
}
type key struct{State uint64;Input uint32}
type entry struct{Key key;Value uint64;Last uint64;Present bool}
type cache struct{Mode string;Entries []entry;Clock uint64;Hits,Misses int}
func newCache(mode string)*cache{
 n:=0;switch mode{case "LRU64":n=64;case "LRU1024":n=1024;case "U05_LOOKUP":n=256}
 return &cache{Mode:mode,Entries:make([]entry,n)}
}
func(c *cache)Apply(k key)uint64{
 if c.Mode=="DIRECT"{c.Misses++;return transition(k.State,k.Input)}
 c.Clock++
 if c.Mode=="U05_LOOKUP"{
  n:=len(c.Entries);start:=int(mix(k.State^uint64(k.Input))%uint64(n))
  first:=start
  for i:=0;i<n;i++{index:=(start+i)%n;e:=&c.Entries[index]
   if e.Present&&e.Key==k{c.Hits++;return e.Value}
   if !e.Present{first=index;break}
  }
  c.Misses++;v:=transition(k.State,k.Input);c.Entries[first]=entry{Key:k,Value:v,Present:true}
  return v
 }
 oldest:=uint64(^uint64(0));index:=0
 for i:=range c.Entries{e:=&c.Entries[i]
  if e.Present&&e.Key==k{c.Hits++;e.Last=c.Clock;return e.Value}
  if !e.Present{index=i;oldest=0;break}
  if e.Last<oldest{oldest=e.Last;index=i}
 }
 c.Misses++;v:=transition(k.State,k.Input);c.Entries[index]=entry{Key:k,Value:v,Last:c.Clock,Present:true};return v
}
func(c *cache)LogicalBytes()int{return len(c.Entries)*32}
func writeHash(h interface{Write([]byte)(int,error)},state uint64,input uint32,result uint64){var b[20]byte;binary.LittleEndian.PutUint64(b[:8],state);binary.LittleEndian.PutUint32(b[8:12],input);binary.LittleEndian.PutUint64(b[12:20],result);_,_=h.Write(b[:])}
type worker struct{Schema,Mode,Cohort,SourceSHA256,OutputSHA256,TruthSHA256 string;Seed uint64;Sessions,Queries,Hits,Misses,LogicalBytes int;PeakRSSBytes uint64;MemoryMetric string}
func single(mode,cohort string,seed uint64)(worker,error){
 var out worker
 found:=false;for _,x:=range modes{if x==mode{found=true}};if !found{return out,errors.New("unknown mode")}
 found=false;for _,x:=range cohorts{if x==cohort{found=true}};if !found{return out,errors.New("unknown cohort")}
 src,truth,pred:=sha256.New(),sha256.New(),sha256.New();hits,misses:=0,0
 for ep:=0;ep<sessions;ep++{
  c:=newCache(mode)
  for t:=0;t<steps;t++{
   state,input:=source(cohort,seed,ep,t)
   actual:=transition(state,input)
   got:=c.Apply(key{state,input})
   if actual!=got{return out,errors.New("incorrect cached transition")}
   writeHash(src,state,input,0);writeHash(truth,state,input,actual);writeHash(pred,state,input,got)
  }
  hits+=c.Hits;misses+=c.Misses
 }
 rss,err:=peakResidentBytes();if err!=nil{return out,err};if rss==0{return out,errors.New("missing physical RSS")}
 return worker{Schema:schema,Mode:mode,Cohort:cohort,Seed:seed,Sessions:sessions,Queries:sessions*steps,Hits:hits,Misses:misses,LogicalBytes:newCache(mode).LogicalBytes(),PeakRSSBytes:rss,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",SourceSHA256:hex.EncodeToString(src.Sum(nil)),TruthSHA256:hex.EncodeToString(truth.Sum(nil)),OutputSHA256:hex.EncodeToString(pred.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type comparison struct{Cohort,Fastest string;MedianCPU,MedianRSS map[string]float64;CPURatio,RSSRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelAcceleration bool;Records []trial;Comparisons []comparison}
func median(a []float64)float64{b:=append([]float64(nil),a...);sort.Float64s(b);n:=len(b);if n==0{return math.NaN()};if n%2==0{return 0.5*(b[n/2-1]+b[n/2])};return b[n/2]}
func child(exe,mode,cohort string,seed uint64)(trial,error){
 var row trial
 c:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var out,errout bytes.Buffer;c.Stdout=&out;c.Stderr=&errout
 start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return row,fmt.Errorf("failed %s/%s/%d: %w %s",mode,cohort,seed,err,errout.String())}
 if c.ProcessState==nil{return row,errors.New("missing child state")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return row,errors.New("zero child CPU or wall")}
 var w worker;if err=json.Unmarshal(out.Bytes(),&w);err!=nil{return row,err}
 if w.Schema!=schema||w.Mode!=mode||w.Cohort!=cohort||w.Seed!=seed||w.Queries!=sessions*steps||w.Sessions!=sessions||w.PeakRSSBytes==0||w.Hits+w.Misses!=w.Queries||w.TruthSHA256!=w.OutputSHA256||len(w.SourceSHA256)!=64{return row,errors.New("invalid receipt")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil
}
func compare(all []trial,cohort string)(comparison,error){
 z:=comparison{Cohort:cohort,MedianCPU:map[string]float64{},MedianRSS:map[string]float64{}}
 group:=map[string][]trial{};paired:=map[uint64]string{}
 for _,r:=range all{w:=r.Worker;if w.Cohort!=cohort{continue};group[w.Mode]=append(group[w.Mode],r)
  if h,ok:=paired[w.Seed];ok&&h!=w.SourceSHA256{return z,errors.New("unmatched public inputs")};paired[w.Seed]=w.SourceSHA256
 }
 if len(paired)!=len(seeds){return z,errors.New("missing seed pairs")}
 for _,mode:=range modes{
  rr:=group[mode];if len(rr)!=len(seeds){return z,errors.New("missing mode")}
  var cpu,rss []float64;for _,r:=range rr{cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes))}
  z.MedianCPU[mode]=median(cpu);z.MedianRSS[mode]=median(rss)
 }
 z.Fastest="DIRECT";for _,m:=range []string{"LRU64","LRU1024"}{if z.MedianCPU[m]<z.MedianCPU[z.Fastest]{z.Fastest=m}}
 z.CPURatio=z.MedianCPU["U05_LOOKUP"]/z.MedianCPU[z.Fastest]
 z.RSSRatio=z.MedianRSS["U05_LOOKUP"]/z.MedianRSS[z.Fastest]
 z.Pass=z.CPURatio<=0.90&&z.RSSRatio<=1.10
 return z,nil
}
func drive(path string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,Records:make([]trial,0,60)}
 for _,cohort:=range cohorts{for i,seed:=range seeds{
  order:=[]string{"DIRECT","LRU64","LRU1024","U05_LOOKUP"}
  if i%2==1{order=[]string{"U05_LOOKUP","LRU1024","LRU64","DIRECT"}}
  for _,mode:=range order{row,e:=child(exe,mode,cohort,seed);if e!=nil{return e};r.Records=append(r.Records,row)}
 }
 c,e:=compare(r.Records,cohort);if e!=nil{return e};r.Comparisons=append(r.Comparisons,c)}
 r.NativeChildCount=len(r.Records);if r.NativeChildCount!=60{return errors.New("missing cold workers")}
 pass:=true;for _,c:=range r.Comparisons{pass=pass&&c.Pass}
 r.Classification="U05_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";if pass{r.Classification="U05_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC49_U05_60_NATIVE_WORKERS=PASS");fmt.Println("ACC49_U05_CLASSIFICATION="+r.Classification);return nil
}
func main(){childFlag:=flag.Bool("worker",false,"");mode:=flag.String("mode","U05_LOOKUP","");cohort:=flag.String("cohort","NOVEL","");seed:=flag.Uint64("seed",99101,"");out:=flag.String("out","acc49-report.json","");flag.Parse()
 var err error;if *childFlag{var w worker;w,err=single(*mode,*cohort,*seed);if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}}else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC49_U05_BLOCKED:",err);os.Exit(1)}
}
