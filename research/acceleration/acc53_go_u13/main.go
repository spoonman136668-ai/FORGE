package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"math";"os";"os/exec";"runtime";"sort";"time")
const(schema="forge.acc53.original-u13.nativego.v1";episodes=32;inserts=8192;queries=8192)
var seeds=[]uint64{103101,103103,103107,103109,103111}
var workloads=[]string{"REPEAT","UNIFORM","SHIFT","COLLISION"}
var arms=[]string{"EXACT","LRU512","HASH512","SKETCH512"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func keyAt(seed uint64,ep,index int,work string)uint64{
 x:=mix(seed^uint64(ep)*0x94d049bb133111eb^uint64(index)*0xbf58476d1ce4e5b9)
 if work=="COLLISION"{return (x&^uint64(511))|uint64(7)}
 return x
}
func val(seed,key uint64)uint64{return mix(key^seed)}
func queryAt(seed uint64,ep,index int,work string)uint64{
 item:=index%inserts
 switch work{
 case "REPEAT":item=index%512
 case "UNIFORM","COLLISION":item=int(mix(seed^uint64(ep)*0xa0761d6478bd642f^uint64(index))%inserts)
 case "SHIFT":
  if index>=queries/2{return keyAt(seed,ep,inserts+index,work)}
  item=int(mix(seed^uint64(ep)*0xe7037ed1a0b428db^uint64(index))%inserts)
 }
 return keyAt(seed,ep,item,work)
}
type entry struct{Key,Value,Stamp uint64;Used bool}
type model struct{Arm string;Exact map[uint64]uint64;Slot []entry;Clock uint64}
func newModel(arm string)*model{
 m:=&model{Arm:arm}
 switch arm{case "EXACT":m.Exact=make(map[uint64]uint64);default:m.Slot=make([]entry,512)}
 return m
}
func(m *model)Add(k,v uint64){
 m.Clock++
 if m.Arm=="EXACT"{m.Exact[k]=v;return}
 if m.Arm=="SKETCH512"{
  h:=int(mix(k)%512)
  m.Slot[h]=entry{Key:k,Value:v,Used:true,Stamp:m.Clock}
  return
 }
 if m.Arm=="HASH512"{
  h:=int(k%512);m.Slot[h]=entry{Key:k,Value:v,Used:true,Stamp:m.Clock};return
 }
 // LRU512 exact associative scan; costly work is part of full-system assessment.
 index:=0;old:=uint64(^uint64(0))
 for i:=range m.Slot{
  e:=m.Slot[i]
  if e.Used&&e.Key==k{index=i;old=0;break}
  if !e.Used{index=i;old=0;break}
  if e.Stamp<old{old=e.Stamp;index=i}
 }
 m.Slot[index]=entry{Key:k,Value:v,Used:true,Stamp:m.Clock}
}
func(m *model)Find(k uint64)(uint64,bool){
 if m.Arm=="EXACT"{v,ok:=m.Exact[k];return v,ok}
 if m.Arm=="SKETCH512"{
  e:=m.Slot[mix(k)%512];if e.Used&&e.Key==k{return e.Value,true};return 0,false
 }
 if m.Arm=="HASH512"{
  e:=m.Slot[k%512];if e.Used&&e.Key==k{return e.Value,true};return 0,false
 }
 for i:=range m.Slot{e:=&m.Slot[i];if e.Used&&e.Key==k{m.Clock++;e.Stamp=m.Clock;return e.Value,true}}
 return 0,false
}
func(m *model)Bytes()int{if m.Arm=="EXACT"{return len(m.Exact)*16};return len(m.Slot)*24}
func digest(h interface{Write([]byte)(int,error)},k,v uint64,exists bool){var b[17]byte;binary.LittleEndian.PutUint64(b[:8],k);binary.LittleEndian.PutUint64(b[8:16],v);if exists{b[16]=1};h.Write(b[:])}
type worker struct{Schema,Arm,Workload,SourceSHA256,TruthSHA256,OutputSHA256 string;Seed uint64;Episodes,Insertions,Queries,PresentQueries,FoundCorrect,FalsePositives,LogicalBytes int;PeakRSSBytes uint64;SuccessfulRetrieval float64}
func work(arm,world string,seed uint64)(worker,error){
 var out worker;ok:=false;for _,a:=range arms{if a==arm{ok=true}};if !ok{return out,errors.New("invalid arm")}
 ok=false;for _,w:=range workloads{if w==world{ok=true}};if !ok{return out,errors.New("invalid workload")}
 sourceHash,truthHash,predHash:=sha256.New(),sha256.New(),sha256.New()
 present,correct,fp,logical:=0,0,0,0
 for ep:=0;ep<episodes;ep++{
  method:=newModel(arm);oracle:=make(map[uint64]uint64,inserts)
  for i:=0;i<inserts;i++{k:=keyAt(seed,ep,i,world);v:=val(seed,k);digest(sourceHash,k,v,true);oracle[k]=v;method.Add(k,v)}
  for i:=0;i<queries;i++{
   k:=queryAt(seed,ep,i,world);expected,exists:=oracle[k]
   digest(sourceHash,k,0,false);digest(truthHash,k,expected,exists)
   got,found:=method.Find(k);digest(predHash,k,got,found)
   if exists{present++;if found&&got==expected{correct++}}
   if found&&(!exists||got!=expected){fp++}
  }
  if method.Bytes()>logical{logical=method.Bytes()}
 }
 rss,err:=peakResidentBytes();if err!=nil{return out,err};if rss==0||present==0{return out,errors.New("missing physical RSS/queries")}
 return worker{Schema:schema,Arm:arm,Workload:world,Seed:seed,Episodes:episodes,Insertions:episodes*inserts,Queries:episodes*queries,PresentQueries:present,FoundCorrect:correct,FalsePositives:fp,LogicalBytes:logical,PeakRSSBytes:rss,SuccessfulRetrieval:float64(correct)/float64(present),SourceSHA256:hex.EncodeToString(sourceHash.Sum(nil)),TruthSHA256:hex.EncodeToString(truthHash.Sum(nil)),OutputSHA256:hex.EncodeToString(predHash.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type cohort struct{Workload,Fastest string;CPU,RSS,State,Recall map[string]float64;CPURatio,RSSRatio,StateRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelSpeedup bool;Trials []trial;Cohorts []cohort}
func median(a []float64)float64{b:=append([]float64(nil),a...);sort.Float64s(b);return b[len(b)/2]}
func run(exe,arm,world string,seed uint64)(trial,error){
 var t trial;c:=exec.Command(exe,"-worker","-arm",arm,"-workload",world,"-seed",fmt.Sprint(seed));var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();elapsed:=time.Since(start).Seconds()
 if err!=nil{return t,fmt.Errorf("%s/%s/%d: %w %s",arm,world,seed,err,stderr.String())}
 if c.ProcessState==nil{return t,errors.New("missing child")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds()
 if cpu<=0||elapsed<=0{return t,errors.New("zero CPU")}
 var w worker;if e:=json.Unmarshal(stdout.Bytes(),&w);e!=nil{return t,e}
 if w.Schema!=schema||w.Arm!=arm||w.Workload!=world||w.Seed!=seed||w.Episodes!=episodes||w.Insertions!=episodes*inserts||w.Queries!=episodes*queries||w.PeakRSSBytes==0||w.PresentQueries<=0||w.FalsePositives!=0||len(w.SourceSHA256)!=64{return t,errors.New("bad worker receipt")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:elapsed},nil
}
func compare(rows []trial,world string)(cohort,error){
 c:=cohort{Workload:world,CPU:map[string]float64{},RSS:map[string]float64{},State:map[string]float64{},Recall:map[string]float64{}}
 group:=map[string][]trial{};pair:=map[uint64]string{}
 for _,row:=range rows{w:=row.Worker;if w.Workload!=world{continue};group[w.Arm]=append(group[w.Arm],row);h:=w.SourceSHA256+"/"+w.TruthSHA256;if old,ok:=pair[w.Seed];ok&&old!=h{return c,errors.New("source mismatch")};pair[w.Seed]=h}
 if len(pair)!=5{return c,errors.New("missing paired seeds")}
 for _,arm:=range arms{a:=group[arm];if len(a)!=5{return c,errors.New("missing arm")};var cpu,rss,state,recall []float64;for _,v:=range a{cpu=append(cpu,v.CPUSeconds);rss=append(rss,float64(v.Worker.PeakRSSBytes));state=append(state,float64(v.Worker.LogicalBytes));recall=append(recall,v.Worker.SuccessfulRetrieval)}
  c.CPU[arm]=median(cpu);c.RSS[arm]=median(rss);c.State[arm]=median(state);c.Recall[arm]=median(recall)
 }
 c.Fastest="EXACT";for _,m:=range []string{"LRU512","HASH512"}{if c.CPU[m]<c.CPU[c.Fastest]{c.Fastest=m}}
 c.CPURatio=c.CPU["SKETCH512"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["SKETCH512"]/c.RSS[c.Fastest];c.StateRatio=c.State["SKETCH512"]/c.State["EXACT"]
 c.Pass=c.Recall["SKETCH512"]>=.95&&c.CPURatio<=.90&&c.RSSRatio<=1.10&&c.StateRatio<=.25
 return c,nil
}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e}
 r:=report{Schema:schema,OS:runtime.GOOS,Trials:make([]trial,0,80)}
 for _,world:=range workloads{for i,seed:=range seeds{
  order:=[]string{"EXACT","LRU512","HASH512","SKETCH512"};if i%2==1{order=[]string{"SKETCH512","HASH512","LRU512","EXACT"}}
  for _,arm:=range order{t,err:=run(exe,arm,world,seed);if err!=nil{return err};r.Trials=append(r.Trials,t)}
 }
 c,err:=compare(r.Trials,world);if err!=nil{return err};r.Cohorts=append(r.Cohorts,c)}
 r.NativeChildCount=len(r.Trials);if r.NativeChildCount!=80{return errors.New("missing workers")}
 r.Classification="U13_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,c:=range r.Cohorts{pass=pass&&c.Pass};if pass{r.Classification="U13_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC53_U13_NATIVE_COLD_WORKERS=80_PASS");fmt.Println("ACC53_U13_CLASSIFICATION="+r.Classification);return nil
}
func main(){w:=flag.Bool("worker",false,"");arm:=flag.String("arm","SKETCH512","");world:=flag.String("workload","REPEAT","");seed:=flag.Uint64("seed",103101,"");out:=flag.String("out","acc53-report.json","");flag.Parse();var e error;if *w{var r worker;r,e=work(*arm,*world,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(r)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC53_U13_BLOCKED:",e);os.Exit(1)}}
