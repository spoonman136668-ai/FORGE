package main
import("bytes";"compress/zlib";"crypto/sha256";"encoding/binary";"encoding/hex";"errors";"fmt";"io";"math";"os";"os/exec";"runtime";"sort";"time";"encoding/json";"flag")
const(schema="forge.acc48.original-u17.nativego.v1";sessions=32;historySize=262144)
var seeds=[]uint64{98101,98103,98107,98109,98111}
var cohorts=[]string{"REPEATED","BURST","ENTROPIC"}
var modes=[]string{"RAW","ZLIB","FIXED","GRAMMAR"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func member(s string,a []string)bool{for _,x:=range a{if s==x{return true}};return false}
func source(kind string,seed uint64,ep int)[]byte{
 out:=make([]byte,historySize);root:=mix(seed^uint64(ep)*0xb5ad4eceda1ce2a9^0x1714d53fd7ce8c09)
 var phrases [16][16]byte
 for n:=0;n<16;n++{for j:=0;j<16;j++{phrases[n][j]=byte(mix(root^uint64(n)*0x9e3779b97f4a7c15^uint64(j)*0xbf58476d1ce4e5b9))}}
 if kind=="ENTROPIC"{for i:=range out{out[i]=byte(mix(root^uint64(i)*0x94d049bb133111eb))};return out}
 for block:=0;block<historySize/16;block++{
  id:=int((uint64(block/7)+mix(root^uint64(block/91)))%16)
  if kind=="REPEATED"{id=int((uint64(block/47)+uint64(block/17))%16)}
  if kind=="BURST"&&block%97==0{
   for j:=0;j<16;j++{out[block*16+j]=byte(mix(root^uint64(block)*0xa0761d6478bd642f^uint64(j)))}
  }else{copy(out[block*16:block*16+16],phrases[id][:])}
 }
 return out
}
func serialize(kind string,data []byte)([]byte,int,error){
 if len(data)%16!=0{return nil,0,errors.New("misaligned input")}
 if kind=="RAW"{return append([]byte(nil),data...),0,nil}
 if kind=="ZLIB"{
  var b bytes.Buffer;z,e:=zlib.NewWriterLevel(&b,zlib.BestSpeed);if e!=nil{return nil,0,e}
  if _,e=z.Write(data);e!=nil{return nil,0,e};if e=z.Close();e!=nil{return nil,0,e}
  return b.Bytes(),0,nil
 }
 if kind!="FIXED"&&kind!="GRAMMAR"{return nil,0,errors.New("unknown arm")}
 dict:=make(map[[16]byte]uint16);rules:=make([][16]byte,0,256)
 tokens:=make([]uint16,0,len(data)/16)
 escapes:=make([][16]byte,0)
 for i:=0;i<len(data);i+=16{
  var phrase [16]byte;copy(phrase[:],data[i:i+16])
  index,ok:=dict[phrase]
  if !ok&&len(rules)<255{index=uint16(len(rules));rules=append(rules,phrase);dict[phrase]=index;ok=true}
  if !ok{tokens=append(tokens,65535);escapes=append(escapes,phrase)}else{tokens=append(tokens,index)}
 }
 var output bytes.Buffer
 var header [2]byte;binary.LittleEndian.PutUint16(header[:],uint16(len(rules)));output.Write(header[:])
 for _,rule:=range rules{output.Write(rule[:])}
 escapeIndex:=0
 for _,index:=range tokens{
  if kind=="GRAMMAR"{
   if index==65535{output.WriteByte(255);output.Write(escapes[escapeIndex][:]);escapeIndex++}else{output.WriteByte(byte(index))}
  }else{
   binary.LittleEndian.PutUint16(header[:],index);output.Write(header[:])
   if index==65535{output.Write(escapes[escapeIndex][:]);escapeIndex++}
  }
 }
 return output.Bytes(),len(rules),nil
}
func restore(kind string,encoded []byte)([]byte,error){
 if kind=="RAW"{return append([]byte(nil),encoded...),nil}
 if kind=="ZLIB"{z,e:=zlib.NewReader(bytes.NewReader(encoded));if e!=nil{return nil,e};decoded,e:=io.ReadAll(z);closeErr:=z.Close();if e!=nil{return nil,e};if closeErr!=nil{return nil,closeErr};return decoded,nil}
 if kind!="FIXED"&&kind!="GRAMMAR"{return nil,errors.New("invalid method")}
 if len(encoded)<2{return nil,errors.New("missing rule count")}
 n:=int(binary.LittleEndian.Uint16(encoded[:2]));if n>256||len(encoded)<2+n*16{return nil,errors.New("rule table invalid")}
 rules:=make([][16]byte,n);for i:=0;i<n;i++{copy(rules[i][:],encoded[2+i*16:2+(i+1)*16])}
 tokens:=encoded[2+n*16:];width:=1;if kind=="FIXED"{width=2}
 out:=make([]byte,0,historySize)
 for i:=0;i<len(tokens);{
  if len(tokens)-i<width{return nil,errors.New("truncated token")}
  index:=int(tokens[i]);if width==2{index=int(binary.LittleEndian.Uint16(tokens[i:i+2]))};i+=width
  if index==255&&width==1||index==65535&&width==2{
   if len(tokens)-i<16{return nil,errors.New("truncated escape")}
   out=append(out,tokens[i:i+16]...);i+=16
  }else{
   if index>=n{return nil,errors.New("undefined grammar reference")}
   out=append(out,rules[index][:]...)
  }
 }
 return out,nil
}
type worker struct{Schema,Mode,Cohort,SourceSHA256,OutputSHA256,MemoryMetric string;Seed uint64;Sessions,OriginalBytes,EncodedBytes,LastRuleCount int;PeakRSSBytes uint64}
func single(mode,cohort string,seed uint64)(worker,error){
 var w worker;if !member(mode,modes)||!member(cohort,cohorts){return w,errors.New("unknown arm/cohort")}
 src,output:=sha256.New(),sha256.New();encodedSize,ruleCount:=0,0
 for i:=0;i<sessions;i++{
  input:=source(cohort,seed,i);src.Write(input)
  encoded,number,e:=serialize(mode,input);if e!=nil{return w,e}
  reconstructed,e:=restore(mode,encoded);if e!=nil{return w,e}
  if !bytes.Equal(input,reconstructed){return w,errors.New("nonlossless history")}
  output.Write(reconstructed);encodedSize+=len(encoded);ruleCount=number
 }
 rss,e:=peakResidentBytes();if e!=nil{return w,e};if rss==0{return w,errors.New("unavailable real RSS")}
 return worker{Schema:schema,Mode:mode,Cohort:cohort,Seed:seed,Sessions:sessions,OriginalBytes:sessions*historySize,EncodedBytes:encodedSize,LastRuleCount:ruleCount,PeakRSSBytes:rss,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",SourceSHA256:hex.EncodeToString(src.Sum(nil)),OutputSHA256:hex.EncodeToString(output.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type cell struct{Cohort,Fastest string;MedianCPU,MedianRSS,MedianBytes map[string]float64;CPURatio,RSSRatio,RawBytesRatio,ZlibBytesRatio,FixedBytesRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelSpeedup bool;Trials []trial;Cohorts []cell}
func med(xs []float64)float64{a:=append([]float64(nil),xs...);sort.Float64s(a);n:=len(a);if n==0{return math.NaN()};if n%2==0{return(a[n/2-1]+a[n/2])/2};return a[n/2]}
func child(exe,mode,cohort string,seed uint64)(trial,error){
 var t trial;c:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return t,fmt.Errorf("%s/%s/%d: %w %s",mode,cohort,seed,err,stderr.String())}
 if c.ProcessState==nil{return t,errors.New("missing process state")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return t,fmt.Errorf("missing process CPU %.9f wall %.9f",cpu,wall)}
 var w worker;if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return t,err}
 if w.Schema!=schema||w.Mode!=mode||w.Cohort!=cohort||w.Seed!=seed||w.Sessions!=sessions||w.OriginalBytes!=sessions*historySize||w.EncodedBytes<=0||w.PeakRSSBytes==0||w.SourceSHA256!=w.OutputSHA256||len(w.SourceSHA256)!=64{return t,errors.New("incomplete or lossy worker")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil
}
func evaluate(rows []trial,cohort string)(cell,error){
 z:=cell{Cohort:cohort,MedianCPU:map[string]float64{},MedianRSS:map[string]float64{},MedianBytes:map[string]float64{}}
 group:=map[string][]trial{};sourceHash:=map[uint64]string{}
 for _,r:=range rows{w:=r.Worker;if w.Cohort!=cohort{continue};group[w.Mode]=append(group[w.Mode],r)
  if a,ok:=sourceHash[w.Seed];ok&&a!=w.SourceSHA256{return z,errors.New("different public source")};sourceHash[w.Seed]=w.SourceSHA256
 }
 if len(sourceHash)!=len(seeds){return z,errors.New("missing seeds")}
 for _,mode:=range modes{
  rows:=group[mode];if len(rows)!=len(seeds){return z,errors.New("missing arm")}
  var cpu,rss,bytes []float64
  for _,r:=range rows{cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes));bytes=append(bytes,float64(r.Worker.EncodedBytes))}
  z.MedianCPU[mode]=med(cpu);z.MedianRSS[mode]=med(rss);z.MedianBytes[mode]=med(bytes)
  if z.MedianCPU[mode]<=0||z.MedianRSS[mode]<=0||z.MedianBytes[mode]<=0{return z,errors.New("invalid medians")}
 }
 z.Fastest="RAW";for _,m:=range []string{"ZLIB","FIXED"}{if z.MedianCPU[m]<z.MedianCPU[z.Fastest]{z.Fastest=m}}
 z.CPURatio=z.MedianCPU["GRAMMAR"]/z.MedianCPU[z.Fastest];z.RSSRatio=z.MedianRSS["GRAMMAR"]/z.MedianRSS[z.Fastest]
 z.RawBytesRatio=z.MedianBytes["GRAMMAR"]/z.MedianBytes["RAW"];z.ZlibBytesRatio=z.MedianBytes["GRAMMAR"]/z.MedianBytes["ZLIB"];z.FixedBytesRatio=z.MedianBytes["GRAMMAR"]/z.MedianBytes["FIXED"]
 z.Pass=z.CPURatio<=0.9&&z.RSSRatio<=1.1&&z.RawBytesRatio<=0.75&&z.ZlibBytesRatio<=0.95&&z.FixedBytesRatio<=0.95
 return z,nil
}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e}
 r:=report{Schema:schema,OS:runtime.GOOS,Trials:make([]trial,0,60)}
 for _,cohort:=range cohorts{
  for i,seed:=range seeds{order:=[]string{"RAW","ZLIB","FIXED","GRAMMAR"};if i%2==1{order=[]string{"GRAMMAR","FIXED","ZLIB","RAW"}};for _,mode:=range order{row,err:=child(exe,mode,cohort,seed);if err!=nil{return err};r.Trials=append(r.Trials,row)}}
  z,err:=evaluate(r.Trials,cohort);if err!=nil{return err};r.Cohorts=append(r.Cohorts,z)
 }
 r.NativeChildCount=len(r.Trials);if r.NativeChildCount!=60{return errors.New("incomplete trials")}
 r.Classification="U17_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,z:=range r.Cohorts{pass=pass&&z.Pass}
 if pass{r.Classification="U17_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC48_U17_60_COLD_WORKERS=PASS");fmt.Println("ACC48_U17_CLASSIFICATION="+r.Classification);return nil
}
func main(){isWorker:=flag.Bool("worker",false,"");mode:=flag.String("mode","GRAMMAR","");cohort:=flag.String("cohort","REPEATED","");seed:=flag.Uint64("seed",98101,"");out:=flag.String("out","acc48-report.json","");flag.Parse();var e error
 if *isWorker{var w worker;w,e=single(*mode,*cohort,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(w)}}else{e=drive(*out)}
 if e!=nil{fmt.Fprintln(os.Stderr,"ACC48_U17_BLOCKED:",e);os.Exit(1)}
}
