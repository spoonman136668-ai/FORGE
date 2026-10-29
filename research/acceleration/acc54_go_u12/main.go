package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"io";"os";"os/exec";"path/filepath";"runtime";"sort";"time")
const(schema="forge.acc54.u12.go.v1";pages=16384;pageSize=4096;requests=131072)
var seeds=[]uint64{104101,104103,104107,104109,104111}
var worlds=[]string{"SEQUENTIAL","HOTSET","STRIDED","RANDOM"}
var modes=[]string{"RESIDENT","MMAP","DIRECT_READ","STREAM64"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func value(seed uint64,index int)uint64{return mix(seed^uint64(index)*0xbf58476d1ce4e5b9)}
func indexAt(seed uint64,step int,world string)int{
 switch world{
 case "SEQUENTIAL":return step%(pages*512)
 case "HOTSET":return int(mix(seed^uint64(step)*0x94d049bb133111eb)%uint64(256*512))
 case "STRIDED":return ((step*997)%pages)*512+step%512
 case "RANDOM":return int(mix(seed^uint64(step)*0xa0761d6478bd642f)%uint64(pages*512))
 };panic("invalid workload")
}
func createFile(path string,seed uint64)error{
 f,e:=os.Create(path);if e!=nil{return e};defer f.Close()
 buf:=make([]byte,65536);for start:=0;start<pages*512;start+=len(buf)/8{
  for i:=0;i<len(buf)/8;i++{binary.LittleEndian.PutUint64(buf[i*8:],value(seed,start+i))}
  if _,e=f.Write(buf);e!=nil{return e}
 };return f.Sync()
}
type page struct{ID int;Data [pageSize]byte;Tick uint64;Valid bool}
type reader struct{Mode string;File *os.File;Resident []byte;Mapped []byte;Cache [64]page;Tick uint64;Hits,Misses int;ReadBytes uint64}
func openReader(path,mode string)(*reader,error){
 f,e:=os.Open(path);if e!=nil{return nil,e}
 r:=&reader{Mode:mode,File:f}
 if mode=="RESIDENT"{r.Resident,e=io.ReadAll(f);if e==nil&&len(r.Resident)!=pages*pageSize{e=errors.New("resident size mismatch")};r.ReadBytes=uint64(len(r.Resident))}
 if mode=="MMAP"{r.Mapped,e=mapFile(f,pages*pageSize)}
 if e!=nil{f.Close();return nil,e};return r,nil
}
func(r *reader)Close()error{if r.Mapped!=nil{if e:=unmapFile(r.Mapped);e!=nil{return e}};return r.File.Close()}
func(r *reader)Get(index int)(uint64,error){
 if index<0||index>=pages*512{return 0,errors.New("out of bounds")}
 at:=index*8
 switch r.Mode{
 case "RESIDENT":return binary.LittleEndian.Uint64(r.Resident[at:]),nil
 case "MMAP":return binary.LittleEndian.Uint64(r.Mapped[at:]),nil
 case "DIRECT_READ":
  var b [8]byte;n,e:=r.File.ReadAt(b[:],int64(at));r.ReadBytes+=uint64(n);if e!=nil{return 0,e};return binary.LittleEndian.Uint64(b[:]),nil
 case "STREAM64":
  id:=at/pageSize;r.Tick++
  for i:=range r.Cache{e:=&r.Cache[i];if e.Valid&&e.ID==id{e.Tick=r.Tick;r.Hits++;return binary.LittleEndian.Uint64(e.Data[at%pageSize:]),nil}}
  victim:=0;oldest:=uint64(^uint64(0))
  for i:=range r.Cache{e:=r.Cache[i];if !e.Valid{victim=i;break};if e.Tick<oldest{oldest=e.Tick;victim=i}}
  dst:=&r.Cache[victim];n,e:=r.File.ReadAt(dst.Data[:],int64(id*pageSize));r.ReadBytes+=uint64(n);if e!=nil{return 0,e};if n!=pageSize{return 0,errors.New("short page")}
  *dst=page{ID:id,Data:dst.Data,Tick:r.Tick,Valid:true};r.Misses++
  return binary.LittleEndian.Uint64(dst.Data[at%pageSize:]),nil
 };return 0,errors.New("unknown reader")
}
func hash(h interface{Write([]byte)(int,error)},x uint64){var b [8]byte;binary.LittleEndian.PutUint64(b[:],x);h.Write(b[:])}
type worker struct{Schema,Mode,World,SourceSHA256,AccessSHA256,OutputSHA256 string;Seed uint64;Requests,PageHits,PageMisses,LogicalStateBytes int;ReadBytes,WriteBytes,PeakRSSBytes uint64}
func work(mode,world string,seed uint64)(worker,error){
 var out worker;valid:=false;for _,s:=range modes{if s==mode{valid=true}};if !valid{return out,errors.New("invalid method")}
 valid=false;for _,s:=range worlds{if s==world{valid=true}};if !valid{return out,errors.New("invalid world")}
 dir,e:=os.MkdirTemp("","acc54-u12-");if e!=nil{return out,e};defer os.RemoveAll(dir)
 path:=filepath.Join(dir,"weights.bin");if e=createFile(path,seed);e!=nil{return out,e}
 r,e:=openReader(path,mode);if e!=nil{return out,e};defer r.Close()
 src,access,output:=sha256.New(),sha256.New(),sha256.New()
 for i:=0;i<pages*512;i++{hash(src,value(seed,i))}
 for i:=0;i<requests;i++{
  index:=indexAt(seed,i,world);hash(access,uint64(index));got,e:=r.Get(index);if e!=nil{return out,e}
  expected:=value(seed,index);if got!=expected{return out,errors.New("not exact source parameter")}
  hash(output,got)
 }
 if e=r.Close();e!=nil{return out,e}
 rss,e:=peakResidentBytes();if e!=nil{return out,e};if rss==0{return out,errors.New("no physical RSS")}
 logical:=pages*pageSize;if mode=="STREAM64"{logical=64*pageSize};if mode=="DIRECT_READ"{logical=8};if mode=="MMAP"{logical=0}
 return worker{Schema:schema,Mode:mode,World:world,Seed:seed,Requests:requests,PageHits:r.Hits,PageMisses:r.Misses,LogicalStateBytes:logical,ReadBytes:r.ReadBytes,WriteBytes:uint64(pages*pageSize),PeakRSSBytes:rss,SourceSHA256:hex.EncodeToString(src.Sum(nil)),AccessSHA256:hex.EncodeToString(access.Sum(nil)),OutputSHA256:hex.EncodeToString(output.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type cell struct{World,Fastest,FastestWall string;CPU,Wall,RSS,Read map[string]float64;CPURatio,WallRatio,RSSRatio,IORatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelSpeedup bool;Trials []trial;Cohorts []cell}
func med(a []float64)float64{b:=append([]float64(nil),a...);sort.Float64s(b);return b[len(b)/2]}
func child(exe,mode,world string,seed uint64)(trial,error){
 var out trial;c:=exec.Command(exe,"-worker","-mode",mode,"-world",world,"-seed",fmt.Sprint(seed));var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return out,fmt.Errorf("%s/%s/%d: %w %s",mode,world,seed,err,stderr.String())}
 if c.ProcessState==nil{return out,errors.New("missing process state")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return out,errors.New("unavailable CPU/wall")}
 var w worker;if e:=json.Unmarshal(stdout.Bytes(),&w);e!=nil{return out,e}
 if w.Schema!=schema||w.Mode!=mode||w.World!=world||w.Seed!=seed||w.Requests!=requests||w.PeakRSSBytes==0||w.WriteBytes!=pages*pageSize||w.ReadBytes==0&&mode!="MMAP"||len(w.SourceSHA256)!=64||len(w.AccessSHA256)!=64||len(w.OutputSHA256)!=64{return out,errors.New("invalid process receipt")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil
}
func compare(all []trial,world string)(cell,error){
 c:=cell{World:world,CPU:map[string]float64{},Wall:map[string]float64{},RSS:map[string]float64{},Read:map[string]float64{}};groups:=map[string][]trial{};paired:=map[uint64]string{}
 for _,t:=range all{w:=t.Worker;if w.World!=world{continue};groups[w.Mode]=append(groups[w.Mode],t);v:=w.SourceSHA256+"/"+w.AccessSHA256+"/"+w.OutputSHA256;if old,ok:=paired[w.Seed];ok&&old!=v{return c,errors.New("unmatched data/outputs")};paired[w.Seed]=v}
 if len(paired)!=len(seeds){return c,errors.New("missing seeds")}
 for _,mode:=range modes{rr:=groups[mode];if len(rr)!=len(seeds){return c,errors.New("missing arm")};var cpu,wall,rss,reads []float64;for _,t:=range rr{cpu=append(cpu,t.CPUSeconds);wall=append(wall,t.WallSeconds);rss=append(rss,float64(t.Worker.PeakRSSBytes));reads=append(reads,float64(t.Worker.ReadBytes))};c.CPU[mode]=med(cpu);c.Wall[mode]=med(wall);c.RSS[mode]=med(rss);c.Read[mode]=med(reads)}
 c.Fastest="RESIDENT";c.FastestWall="RESIDENT"
 for _,m:=range []string{"MMAP","DIRECT_READ"}{if c.CPU[m]<c.CPU[c.Fastest]{c.Fastest=m};if c.Wall[m]<c.Wall[c.FastestWall]{c.FastestWall=m}}
 c.CPURatio=c.CPU["STREAM64"]/c.CPU[c.Fastest];c.WallRatio=c.Wall["STREAM64"]/c.Wall[c.FastestWall];c.RSSRatio=c.RSS["STREAM64"]/c.RSS["RESIDENT"]
 c.IORatio=c.Read["STREAM64"]/c.Read["DIRECT_READ"]
 c.Pass=c.CPURatio<=1.10&&c.WallRatio<=1.20&&c.RSSRatio<=.50&&c.IORatio<=1.50;return c,nil
}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS,Trials:make([]trial,0,80)}
 for _,world:=range worlds{for i,seed:=range seeds{order:=[]string{"RESIDENT","MMAP","DIRECT_READ","STREAM64"};if i%2==1{order=[]string{"STREAM64","DIRECT_READ","MMAP","RESIDENT"}}
  for _,m:=range order{t,e:=child(exe,m,world,seed);if e!=nil{return e};r.Trials=append(r.Trials,t)}}
  c,e:=compare(r.Trials,world);if e!=nil{return e};r.Cohorts=append(r.Cohorts,c)}
 r.NativeChildCount=len(r.Trials);if r.NativeChildCount!=80{return errors.New("incomplete child count")}
 r.Classification="U12_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,c:=range r.Cohorts{pass=pass&&c.Pass};if pass{r.Classification="U12_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC54_U12_COLD_CHILDREN_80=PASS");fmt.Println("ACC54_U12_CLASSIFICATION="+r.Classification);return nil
}
func main(){w:=flag.Bool("worker",false,"");mode:=flag.String("mode","STREAM64","");world:=flag.String("world","HOTSET","");seed:=flag.Uint64("seed",104101,"");out:=flag.String("out","acc54-report.json","");flag.Parse();var e error;if *w{var r worker;r,e=work(*mode,*world,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(r)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC54_U12_BLOCKED:",e);os.Exit(1)}}
