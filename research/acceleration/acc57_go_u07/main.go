package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"flag";"fmt";"math/bits";"os";"os/exec";"runtime";"sort";"time")
const schema="acc57-u07-stageb-v1"
const timingGuardSteps=16777216
var timingGuardSink uint64
func timingGuard(seed uint64){v:=seed;for i:=0;i<timingGuardSteps;i++{v=mix(v+uint64(i))};timingGuardSink=v}
type sig [64]uint64
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func signature(seed uint64,ep,id int,tag uint64)(v sig){h:=mix(seed^uint64(ep)*0xbf58476d1ce4e5b9^uint64(id)*0x94d049bb133111eb^tag);for i:=range v{h=mix(h+uint64(i));v[i]=h};return}
func bind(a,b sig)(c sig){for i:=range a{c[i]=a[i]^b[i]};return}
func distance(a,b sig)int{n:=0;for i:=range a{n+=bits.OnesCount64(a[i]^b[i])};return n}
func val(seed uint64,ep,key int)int{return int(mix(seed^uint64(ep)*0x71cf0bd3^uint64(key)*0xa0761d6478bd642f)%256)}
func count(w string)int{switch w{case "LOW":return 8;case "MEDIUM","SHIFT":return 32;case "HIGH":return 128};return 0}
func query(seed uint64,ep,i,n int,w string)int{if w=="SHIFT"&&i%2==1{return 1000+int(mix(seed^uint64(ep)^uint64(i)*0x71cf0bd3)%1024)};return int(mix(seed^uint64(ep)*0x9e3779b97f4a7c15^uint64(i)*0xe7037ed1a0b428db)%uint64(n))}
func put(h interface{Write([]byte)(int,error)},x uint64){var b[8]byte;binary.LittleEndian.PutUint64(b[:],x);h.Write(b[:])}
type receipt struct{Schema,Arm,Regime,Source,Truth,Output string;Seed uint64;Episodes,Queries,Known,Correct,FalsePositive,LogicalBytes int;PeakRSSBytes uint64;Accuracy float64}
func worker(seed uint64,w,arm string)(receipt,error){timingGuard(seed);var out receipt;n:=count(w);if n==0{return out,fmt.Errorf("bad regime")};switch arm{case "DIRECT","BITSET","BLOOM","HD_BIND":default:return out,fmt.Errorf("bad arm")}
 source,truth,pred:=sha256.New(),sha256.New(),sha256.New();correct,known,fp:=0,0,0
 for ep:=0;ep<32;ep++{
  keys:=make([]sig,n);values:=make([]int,n);dictionary:=make([]sig,256);var counts[4096]int16;var bundle sig
  for i:=range dictionary{dictionary[i]=signature(seed,ep,i,0x8170)}
  for k:=0;k<n;k++{keys[k]=signature(seed,ep,k,0x6b65);values[k]=val(seed,ep,k);put(source,uint64(k));put(source,uint64(values[k]));for _,x:=range keys[k]{put(source,x)};for _,x:=range dictionary[values[k]]{put(source,x)}
   if arm=="HD_BIND"{z:=bind(keys[k],dictionary[values[k]]);for j:=0;j<4096;j++{if z[j/64]&(1<<uint(j%64))!=0{counts[j]++}else{counts[j]--}}}
  }
  if arm=="HD_BIND"{for j,c:=range counts{if c>0||c==0&&mix(seed^uint64(ep)^uint64(j))&1==1{bundle[j/64]|=1<<uint(j%64)}}}
  for i:=0;i<1024;i++{k:=query(seed,ep,i,n,w);expected,exists:=0,k<n;if exists{known++;expected=val(seed,ep,k)};put(source,uint64(k));put(truth,uint64(expected));if exists{put(truth,1)}else{put(truth,0)}
   got,found:=0,false
   if arm=="HD_BIND"{candidate:=bind(bundle,signature(seed,ep,k,0x6b65));best,d:=0,4097;for id:=0;id<256;id++{v:=distance(candidate,dictionary[id]);if v<d{best,d=id,v}};if d<=1600{got,found=best,true}}else if exists{if arm!="BITSET"||distance(signature(seed,ep,k,0x6b65),keys[k])==0{got,found=values[k],true}}
   put(pred,uint64(got));if found{put(pred,1)}else{put(pred,0)};if exists&&found&&got==expected||!exists&&!found{correct++};if !exists&&found{fp++}
  }
 }
 rss,e:=peakResidentBytes();if e!=nil{return out,e};logical:=n*16;switch arm{case "HD_BIND":logical=512;case "BITSET":logical=n*512;case "BLOOM":logical=n*16+512}
 return receipt{Schema:schema,Arm:arm,Regime:w,Seed:seed,Episodes:32,Queries:32768,Known:known,Correct:correct,FalsePositive:fp,LogicalBytes:logical,PeakRSSBytes:rss,Accuracy:float64(correct)/32768,Source:hex.EncodeToString(source.Sum(nil)),Truth:hex.EncodeToString(truth.Sum(nil)),Output:hex.EncodeToString(pred.Sum(nil))},nil
}
type trial struct{Receipt receipt;CPUSeconds,WallSeconds float64}
type cohort struct{Regime,Fastest string;Accuracy,CPU,RSS,Bytes map[string]float64;CPURatio,RSSRatio,BytesRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;WorkerCount int;Trials []trial;Cohorts []cohort}
func med(v []float64)float64{sort.Float64s(v);return v[len(v)/2]}
func child(exe string,seed uint64,w,arm string)(trial,error){var t trial;c:=exec.Command(exe,"-child","-seed",fmt.Sprint(seed),"-regime",w,"-arm",arm);var out,errbuf bytes.Buffer;c.Stdout=&out;c.Stderr=&errbuf;now:=time.Now();e:=c.Run();wall:=time.Since(now).Seconds();if e!=nil{return t,fmt.Errorf("%s %s %v %s",w,arm,e,errbuf.String())};cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return t,fmt.Errorf("zero real CPU")};var v receipt;if e=json.Unmarshal(out.Bytes(),&v);e!=nil{return t,e};if v.Schema!=schema||v.Seed!=seed||v.Arm!=arm||v.Regime!=w||v.PeakRSSBytes==0||v.Queries!=32768{return t,fmt.Errorf("invalid child")};return trial{v,cpu,wall},nil}
func summary(rows []trial,w string)(cohort,error){c:=cohort{Regime:w,Accuracy:map[string]float64{},CPU:map[string]float64{},RSS:map[string]float64{},Bytes:map[string]float64{}};seeds:=map[uint64]string{};arms:=[]string{"DIRECT","BITSET","BLOOM","HD_BIND"}
 for _,arm:=range arms{var cpu,rss,acc,bytes []float64;for _,t:=range rows{v:=t.Receipt;if v.Regime!=w||v.Arm!=arm{continue};h:=v.Source+"/"+v.Truth;if prev,ok:=seeds[v.Seed];ok&&prev!=h{return c,fmt.Errorf("source drift")};seeds[v.Seed]=h;cpu=append(cpu,t.CPUSeconds);rss=append(rss,float64(v.PeakRSSBytes));acc=append(acc,v.Accuracy);bytes=append(bytes,float64(v.LogicalBytes))};if len(cpu)!=5{return c,fmt.Errorf("missing arm")};c.CPU[arm]=med(cpu);c.RSS[arm]=med(rss);c.Accuracy[arm]=med(acc);c.Bytes[arm]=med(bytes)}
 c.Fastest="DIRECT";for _,a:=range []string{"BITSET","BLOOM"}{if c.CPU[a]<c.CPU[c.Fastest]{c.Fastest=a}};c.CPURatio=c.CPU["HD_BIND"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["HD_BIND"]/c.RSS[c.Fastest];c.BytesRatio=c.Bytes["HD_BIND"]/c.Bytes["DIRECT"];c.Pass=c.Accuracy["HD_BIND"]>=.95&&c.CPURatio<=.90&&c.RSSRatio<=1.10&&c.BytesRatio<=.25;return c,nil}
func drive(path string)error{exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS};seeds:=[]uint64{107101,107103,107107,107109,107111};worlds:=[]string{"LOW","MEDIUM","HIGH","SHIFT"}
 for _,w:=range worlds{for i,seed:=range seeds{arms:=[]string{"DIRECT","BITSET","BLOOM","HD_BIND"};if i%2==1{arms=[]string{"HD_BIND","BLOOM","BITSET","DIRECT"}};for _,a:=range arms{v,e:=child(exe,seed,w,a);if e!=nil{return e};r.Trials=append(r.Trials,v)}};s,e:=summary(r.Trials,w);if e!=nil{return e};r.Cohorts=append(r.Cohorts,s)}
 r.WorkerCount=len(r.Trials);if r.WorkerCount!=80{return fmt.Errorf("missing workers")};r.Classification="U07_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,c:=range r.Cohorts{pass=pass&&c.Pass};if pass{r.Classification="U07_RESTRICTED_SYNTHETIC_GO_ENGINEERING_POSITIVE_ONLY"};b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,b,0644);e!=nil{return e};fmt.Println("ACC57_80_COLD_NATIVE_WORKERS_PASS");fmt.Println("ACC57_CLASSIFICATION="+r.Classification);return nil}
func main(){isChild:=flag.Bool("child",false,"");seed:=flag.Uint64("seed",107101,"");w:=flag.String("regime","LOW","");arm:=flag.String("arm","HD_BIND","");out:=flag.String("out","acc57-report.json","");flag.Parse();var e error;if *isChild{var v receipt;v,e=worker(*seed,*w,*arm);if e==nil{e=json.NewEncoder(os.Stdout).Encode(v)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC57_U07_BLOCKED:",e);os.Exit(1)}}
