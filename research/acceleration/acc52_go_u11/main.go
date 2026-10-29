package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"os";"os/exec";"runtime";"sort";"time")
const(schema="forge.acc52.u11.go.v1";size=4096;episodes=128;dots=256)
var seeds=[]uint64{102101,102103,102107,102109,102111}
var regimes=[]string{"DENSE","SPARSE","POSITIVE","ALTERNATING"}
var modes=[]string{"INT8","BITSET","SPARSE","TERNARY_PACKED"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func input(seed uint64,ep,dot int,regime string)([size]int8,[size]int8){
 var a,w [size]int8;root:=mix(seed^uint64(ep)*0xbf58476d1ce4e5b9^uint64(dot)*0x94d049bb133111eb)
 for i:=0;i<size;i++{
  x:=mix(root^uint64(i)*0xa0761d6478bd642f)
  v:=int8(int(x%3)-1)
  switch regime{case "SPARSE":if x%16!=0{v=0};case "POSITIVE":if x%8!=0{v=1};case "ALTERNATING":if i%2==0{v=1}else{v=-1}}
  a[i]=v;w[i]=int8(int(mix(x^0x3769ac15)%255)-127)
 };return a,w
}
func truth(a,w *[size]int8)int64{var out int64;for i:=range a{out+=int64(a[i])*int64(w[i])};return out}
func execute(mode string,a,w *[size]int8)(int64,int){
 switch mode{
 case "INT8":return truth(a,w),size
 case "BITSET":
  var pos,neg [size/64]uint64
  for i,v:=range a{if v==1{pos[i/64]|=1<<uint(i%64)};if v==-1{neg[i/64]|=1<<uint(i%64)}}
  var sum int64
  for word:=0;word<len(pos);word++{for b:=0;b<64;b++{idx:=word*64+b
   if pos[word]&(uint64(1)<<uint(b))!=0{sum+=int64(w[idx])}
   if neg[word]&(uint64(1)<<uint(b))!=0{sum-=int64(w[idx])}
  }}
  return sum,size/4
 case "SPARSE":
  ids:=make([]uint16,0,size);signs:=make([]int8,0,size)
  for i,v:=range a{if v!=0{ids=append(ids,uint16(i));signs=append(signs,v)}}
  var sum int64;for j,i:=range ids{sum+=int64(signs[j])*int64(w[i])}
  return sum,len(ids)*3
 case "TERNARY_PACKED":
  packed:=make([]byte,size/4)
  for i,v:=range a{code:=byte(v+1);packed[i/4]|=code<<uint(2*(i%4))}
  var sum int64
  for i:=0;i<size;i++{v:=int64((packed[i/4]>>uint(2*(i%4)))&3)-1;sum+=v*int64(w[i])}
  return sum,len(packed)
 }
 panic("invalid mode")
}
func hash(h interface{Write([]byte)(int,error)},x int64){var b[8]byte;binary.LittleEndian.PutUint64(b[:],uint64(x));h.Write(b[:])}
type worker struct{Schema,Mode,Regime,InputSHA256,TruthSHA256,OutputSHA256 string;Seed uint64;Episodes,Dots,LogicalBytes int;PeakRSSBytes uint64}
func work(mode,regime string,seed uint64)(worker,error){
 var r worker;found:=false;for _,m:=range modes{if m==mode{found=true}};if !found{return r,errors.New("bad arm")}
 found=false;for _,m:=range regimes{if m==regime{found=true}};if !found{return r,errors.New("bad regime")}
 src,ref,pred:=sha256.New(),sha256.New(),sha256.New();logical:=0
 for e:=0;e<episodes;e++{for d:=0;d<dots;d++{
  a,w:=input(seed,e,d,regime)
  for i:=0;i<size;i++{src.Write([]byte{byte(a[i]),byte(w[i])})}
  target:=truth(&a,&w)
  result,bytes:=execute(mode,&a,&w)
  if target!=result{return r,errors.New("wrong dot product")}
  if bytes>logical{logical=bytes}
  hash(ref,target);hash(pred,result)
 }}
 rss,err:=peakResidentBytes();if err!=nil{return r,err};if rss==0{return r,errors.New("zero physical RSS")}
 return worker{Schema:schema,Mode:mode,Regime:regime,Seed:seed,Episodes:episodes,Dots:episodes*dots,LogicalBytes:logical,PeakRSSBytes:rss,InputSHA256:hex.EncodeToString(src.Sum(nil)),TruthSHA256:hex.EncodeToString(ref.Sum(nil)),OutputSHA256:hex.EncodeToString(pred.Sum(nil))},nil
}
type row struct{Worker worker;CPUSeconds,WallSeconds float64}
type cohort struct{Regime,Fastest string;CPU,RSS,Bytes map[string]float64;CPURatio,RSSRatio,BytesRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelSpeedup bool;Rows []row;Cohorts []cohort}
func median(v []float64)float64{a:=append([]float64(nil),v...);sort.Float64s(a);return a[len(a)/2]}
func child(exe,mode,regime string,seed uint64)(row,error){var out row;c:=exec.Command(exe,"-worker","-mode",mode,"-regime",regime,"-seed",fmt.Sprint(seed));var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds();if err!=nil{return out,fmt.Errorf("%s/%s/%d: %w %s",mode,regime,seed,err,stderr.String())}
 if c.ProcessState==nil{return out,errors.New("missing CPU state")};cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return out,errors.New("zero CPU or wall")}
 var w worker;if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return out,err};if w.Schema!=schema||w.Mode!=mode||w.Regime!=regime||w.Seed!=seed||w.Episodes!=episodes||w.Dots!=episodes*dots||w.PeakRSSBytes==0||w.TruthSHA256!=w.OutputSHA256||len(w.InputSHA256)!=64{return out,errors.New("invalid worker receipt")}
 return row{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil}
func compare(rows []row,regime string)(cohort,error){c:=cohort{Regime:regime,CPU:map[string]float64{},RSS:map[string]float64{},Bytes:map[string]float64{}};group:=map[string][]row{};paired:=map[uint64]string{}
 for _,r:=range rows{w:=r.Worker;if w.Regime!=regime{continue};group[w.Mode]=append(group[w.Mode],r);sig:=w.InputSHA256+"/"+w.TruthSHA256;if old,ok:=paired[w.Seed];ok&&old!=sig{return c,errors.New("source drift")};paired[w.Seed]=sig}
 if len(paired)!=5{return c,errors.New("seeds missing")}
 for _,m:=range modes{rr:=group[m];if len(rr)!=5{return c,errors.New("missing arm")};var cpu,rss,by []float64;for _,r:=range rr{cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes));by=append(by,float64(r.Worker.LogicalBytes))};c.CPU[m]=median(cpu);c.RSS[m]=median(rss);c.Bytes[m]=median(by)}
 c.Fastest="INT8";for _,m:=range []string{"BITSET","SPARSE"}{if c.CPU[m]<c.CPU[c.Fastest]{c.Fastest=m}}
 c.CPURatio=c.CPU["TERNARY_PACKED"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["TERNARY_PACKED"]/c.RSS[c.Fastest];c.BytesRatio=c.Bytes["TERNARY_PACKED"]/c.Bytes["INT8"]
 c.Pass=c.CPURatio<=.90&&c.RSSRatio<=1.10&&c.BytesRatio<=.50;return c,nil}
func drive(path string)error{exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS,Rows:make([]row,0,80)}
 for _,regime:=range regimes{for i,seed:=range seeds{order:=[]string{"INT8","BITSET","SPARSE","TERNARY_PACKED"};if i%2==1{order=[]string{"TERNARY_PACKED","SPARSE","BITSET","INT8"}};for _,mode:=range order{v,e:=child(exe,mode,regime,seed);if e!=nil{return e};r.Rows=append(r.Rows,v)}};v,e:=compare(r.Rows,regime);if e!=nil{return e};r.Cohorts=append(r.Cohorts,v)}
 r.NativeChildCount=len(r.Rows);if r.NativeChildCount!=80{return errors.New("missing workers")}
 r.Classification="U11_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,v:=range r.Cohorts{pass=pass&&v.Pass};if pass{r.Classification="U11_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e};fmt.Println("ACC52_80_NATIVE_CHILDREN=PASS");fmt.Println("ACC52_U11_CLASSIFICATION="+r.Classification);return nil}
func main(){w:=flag.Bool("worker",false,"");m:=flag.String("mode","TERNARY_PACKED","");r:=flag.String("regime","DENSE","");seed:=flag.Uint64("seed",102101,"");out:=flag.String("out","acc52-report.json","");flag.Parse();var e error;if *w{var z worker;z,e=work(*m,*r,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(z)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC52_U11_BLOCKED:",e);os.Exit(1)}}
