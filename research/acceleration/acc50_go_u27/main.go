package main
import("crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"flag";"fmt";"errors";"math";"os";"os/exec";"bytes";"sort";"time";"runtime")
const(schema="forge.acc50.original-u27.nativego.v1";episodes=32;queries=2048)
var seeds=[]uint64{100101,100103,100107,100109,100111}
var cohorts=[]string{"REPEATED","COMMUTED","NOVEL","CONSTANT"}
var modes=[]string{"DIRECT","STRUCT_CACHE","FOLDED","TYPED_REWRITE"}
func mix(v uint64)uint64{v+=0x9e3779b97f4a7c15;v=(v^(v>>30))*0xbf58476d1ce4e5b9;v=(v^(v>>27))*0x94d049bb133111eb;return v^(v>>31)}
type node struct{Kind uint8;Value uint64;L,R *node}
func makeTree(seed uint64,ep,index,depth int,kind string)*node{
 b:=mix(seed^uint64(ep)*0xbf58476d1ce4e5b9^uint64(index)*0x94d049bb133111eb^uint64(depth)*0xa0761d6478bd642f)
 if depth==0{return &node{Value:b%101}}
 left:=makeTree(seed,ep,index*2+1,depth-1,kind)
 right:=makeTree(seed,ep,index*2+2,depth-1,kind)
 op:=uint8(1+b%2)
 if kind=="CONSTANT" {op=1}
 return &node{Kind:op,L:left,R:right}
}
func source(seed uint64,ep,q int,kind string)*node{
 index:=q
 if kind=="REPEATED"{index=q%32}
 if kind=="COMMUTED"{index=q%32}
 root:=makeTree(seed,ep,index,4,kind)
 if kind=="COMMUTED"&&q%2==1{root.L,root.R=root.R,root.L}
 return root
}
func eval(n *node)uint64{
 if n.Kind==0{return n.Value}
 a,b:=eval(n.L),eval(n.R)
 if n.Kind==1{return a+b};return a*b
}
func exactByPostorder(n *node)uint64{
 stack:=[]*node{n};visited:=map[*node]bool{};v:=map[*node]uint64{}
 for len(stack)>0{
  cur:=stack[len(stack)-1]
  if cur.Kind==0{v[cur]=cur.Value;stack=stack[:len(stack)-1];continue}
  if !visited[cur]{visited[cur]=true;stack=append(stack,cur.L,cur.R);continue}
  a,b:=v[cur.L],v[cur.R];if cur.Kind==1{v[cur]=a+b}else{v[cur]=a*b}
  stack=stack[:len(stack)-1]
 }
 return v[n]
}
type ck struct{Op uint8;A,B uint64}
func fold(n *node)*node{
 if n.Kind==0{return &node{Value:n.Value}}
 l,r:=fold(n.L),fold(n.R)
 if l.Kind==0&&r.Kind==0{
  if n.Kind==1{return &node{Value:l.Value+r.Value}};return &node{Value:l.Value*r.Value}
 }
 return &node{Kind:n.Kind,L:l,R:r}
}
func signature(n *node)uint64{
 if n.Kind==0{return mix(n.Value^0x71cf0bd3)}
 return mix(uint64(n.Kind)^signature(n.L)*0x9e3779b97f4a7c15^signature(n.R)*0xbf58476d1ce4e5b9)
}
func rewrite(n *node,seen map[ck]*node)*node{
 if n.Kind==0{return &node{Value:n.Value}}
 a,b:=rewrite(n.L,seen),rewrite(n.R,seen)
 if a.Kind==0&&b.Kind==0{
  if n.Kind==1{return &node{Value:a.Value+b.Value}}
  return &node{Value:a.Value*b.Value}
 }
 la,lb:=signature(a),signature(b);if lb<la{a,b=b,a;la,lb=lb,la}
 key:=ck{Op:n.Kind,A:la,B:lb}
 if old,ok:=seen[key];ok{return old}
 out:=&node{Kind:n.Kind,L:a,R:b};seen[key]=out;return out
}
func hashTree(n *node,h interface{Write([]byte)(int,error)}){
 var b[9]byte;b[0]=n.Kind;binary.LittleEndian.PutUint64(b[1:],n.Value);h.Write(b[:])
 if n.Kind!=0{hashTree(n.L,h);hashTree(n.R,h)}
}
func hashOutput(h interface{Write([]byte)(int,error)},y uint64){var b[8]byte;binary.LittleEndian.PutUint64(b[:],y);h.Write(b[:])}
type outcome struct{Schema,Mode,Cohort,SourceSHA256,TruthSHA256,OutputSHA256,MemoryMetric string;Seed uint64;Episodes,Queries,CacheHits,LogicalBytes int;PeakRSSBytes uint64}
func work(mode,cohort string,seed uint64)(outcome,error){
 var z outcome;valid:=false;for _,s:=range modes{if mode==s{valid=true}};if !valid{return z,errors.New("mode")}
 valid=false;for _,s:=range cohorts{if cohort==s{valid=true}};if !valid{return z,errors.New("cohort")}
 src,truth,pred:=sha256.New(),sha256.New(),sha256.New();hits:=0
 var persisted int
 for ep:=0;ep<episodes;ep++{
  seen:=make(map[uint64]uint64);rewritten:=make(map[ck]*node)
  for q:=0;q<queries;q++{
   tree:=source(seed,ep,q,cohort);hashTree(tree,src)
   expected:=exactByPostorder(tree)
   hashOutput(truth,expected)
   var got uint64
   switch mode{
   case "DIRECT":got=eval(tree)
   case "FOLDED":got=eval(fold(tree))
   case "STRUCT_CACHE":
    k:=signature(tree);if v,ok:=seen[k];ok{hits++;got=v}else{got=eval(tree);seen[k]=got}
   case "TYPED_REWRITE":
    canonical:=rewrite(tree,rewritten)
    k:=signature(canonical)
    if v,ok:=seen[k];ok{hits++;got=v}else{got=eval(canonical);seen[k]=got}
   }
   if got!=expected{return z,errors.New("not exact")}
   hashOutput(pred,got)
  }
  stateBytes:=len(seen)*16+len(rewritten)*32
  if mode=="DIRECT"||mode=="FOLDED"{stateBytes=0}
  persisted+=stateBytes
 }
 peak,e:=peakResidentBytes();if e!=nil{return z,e};if peak==0{return z,errors.New("missing physical RSS")}
 return outcome{Schema:schema,Mode:mode,Cohort:cohort,SourceSHA256:hex.EncodeToString(src.Sum(nil)),TruthSHA256:hex.EncodeToString(truth.Sum(nil)),OutputSHA256:hex.EncodeToString(pred.Sum(nil)),MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",Seed:seed,Episodes:episodes,Queries:episodes*queries,CacheHits:hits,LogicalBytes:persisted,PeakRSSBytes:peak},nil
}
type trial struct{Worker outcome;CPUSeconds,WallSeconds float64}
type resultCell struct{Cohort,Fastest string;MedianCPU,MedianRSS,MedianBytes map[string]float64;CPURatio,RSSRatio,BytesRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelAcceleration bool;Records []trial;Cohorts []resultCell}
func med(a []float64)float64{z:=append([]float64(nil),a...);sort.Float64s(z);n:=len(z);if n==0{return math.NaN()};if n%2==0{return(z[n/2-1]+z[n/2])/2};return z[n/2]}
func child(exe,mode,cohort string,seed uint64)(trial,error){
 var t trial
 c:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var o,e bytes.Buffer;c.Stdout=&o;c.Stderr=&e;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return t,fmt.Errorf("%s/%s failed: %w %s",mode,cohort,err,e.String())}
 if c.ProcessState==nil{return t,errors.New("missing child process")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return t,errors.New("zero child CPU")}
 var w outcome;if err=json.Unmarshal(o.Bytes(),&w);err!=nil{return t,err}
 if w.Schema!=schema||w.Mode!=mode||w.Cohort!=cohort||w.Seed!=seed||w.Episodes!=episodes||w.Queries!=episodes*queries||w.PeakRSSBytes==0||w.TruthSHA256!=w.OutputSHA256||len(w.SourceSHA256)!=64{return t,errors.New("invalid source or worker")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil
}
func compare(rows []trial,cohort string)(resultCell,error){
 c:=resultCell{Cohort:cohort,MedianCPU:map[string]float64{},MedianRSS:map[string]float64{},MedianBytes:map[string]float64{}}
 groups:=map[string][]trial{};paired:=map[uint64]string{}
 for _,r:=range rows{w:=r.Worker;if w.Cohort!=cohort{continue}
  groups[w.Mode]=append(groups[w.Mode],r)
  if v,ok:=paired[w.Seed];ok&&v!=w.SourceSHA256{return c,errors.New("unmatched source")};paired[w.Seed]=w.SourceSHA256
 }
 if len(paired)!=len(seeds){return c,errors.New("missing seeds")}
 for _,m:=range modes{
  a:=groups[m];if len(a)!=len(seeds){return c,errors.New("missing method")}
  var cpu,rss,by []float64;for _,r:=range a{cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes));by=append(by,float64(r.Worker.LogicalBytes))}
  c.MedianCPU[m]=med(cpu);c.MedianRSS[m]=med(rss);c.MedianBytes[m]=med(by)
 }
 c.Fastest="DIRECT";for _,m:=range []string{"STRUCT_CACHE","FOLDED"}{if c.MedianCPU[m]<c.MedianCPU[c.Fastest]{c.Fastest=m}}
 c.CPURatio=c.MedianCPU["TYPED_REWRITE"]/c.MedianCPU[c.Fastest];c.RSSRatio=c.MedianRSS["TYPED_REWRITE"]/c.MedianRSS[c.Fastest]
 // Direct evaluator stores no persistent cache. Compare candidate to the equivalent conventional persistent structural cache instead.
 b:=c.MedianBytes["STRUCT_CACHE"];if b==0{b=1};c.BytesRatio=c.MedianBytes["TYPED_REWRITE"]/b
 c.Pass=c.CPURatio<=.90&&c.RSSRatio<=1.10&&c.BytesRatio<=.75
 return c,nil
}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e}
 r:=report{Schema:schema,OS:runtime.GOOS,Records:make([]trial,0,80)}
 for _,cohort:=range cohorts{for i,seed:=range seeds{
  order:=[]string{"DIRECT","STRUCT_CACHE","FOLDED","TYPED_REWRITE"}
  if i%2==1{order=[]string{"TYPED_REWRITE","FOLDED","STRUCT_CACHE","DIRECT"}}
  for _,m:=range order{row,e:=child(exe,m,cohort,seed);if e!=nil{return e};r.Records=append(r.Records,row)}
 }
 cell,e:=compare(r.Records,cohort);if e!=nil{return e};r.Cohorts=append(r.Cohorts,cell)}
 r.NativeChildCount=len(r.Records);if r.NativeChildCount!=80{return errors.New("missing workers")}
 pass:=true;for _,c:=range r.Cohorts{pass=pass&&c.Pass}
 r.Classification="U27_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";if pass{r.Classification="U27_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC50_U27_80_NATIVE_WORKERS=PASS");fmt.Println("ACC50_U27_CLASSIFICATION="+r.Classification);return nil
}
func main(){workerFlag:=flag.Bool("worker",false,"");mode:=flag.String("mode","TYPED_REWRITE","");cohort:=flag.String("cohort","NOVEL","");seed:=flag.Uint64("seed",100101,"");out:=flag.String("out","acc50-report.json","");flag.Parse()
 var e error;if *workerFlag{var w outcome;w,e=work(*mode,*cohort,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(w)}}else{e=drive(*out)}
 if e!=nil{fmt.Fprintln(os.Stderr,"ACC50_U27_BLOCKED:",e);os.Exit(1)}
}
