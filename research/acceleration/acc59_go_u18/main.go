package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"flag";"fmt";"math/bits";"os";"os/exec";"runtime";"sort";"time")
const schema="acc59-u18-native-v1"
type vector [32]uint64
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func signature(seed uint64,episode,id int,tag uint64)(v vector){h:=mix(seed^uint64(episode)*0xbf58476d1ce4e5b9^uint64(id)*0x94d049bb133111eb^tag);for i:=range v{h=mix(h+uint64(i));v[i]=h};return}
func xor(a,b vector)(c vector){for i:=range a{c[i]=a[i]^b[i]};return}
func distance(a,b vector)int{n:=0;for i:=range a{n+=bits.OnesCount64(a[i]^b[i])};return n}
func val(seed uint64,episode,key int)int{return int(mix(seed^uint64(episode)*0x71cf0bd3^uint64(key)*0xa0761d6478bd642f)%256)}
func nitems(regime string)int{switch regime{case "SPARSE":return 8;case "MEDIUM","OOD":return 32;case "DENSE":return 128};return 0}
func qkey(seed uint64,ep,i,n int,regime string)int{if regime=="OOD"&&i%2==1{return 1000+int(mix(seed^uint64(ep)^uint64(i)*0x71cf0bd3)%1024)};return int(mix(seed^uint64(ep)*0x9e3779b97f4a7c15^uint64(i)*0xe7037ed1a0b428db)%uint64(n))}
func put(h interface{Write([]byte)(int,error)},v uint64){var b[8]byte;binary.LittleEndian.PutUint64(b[:],v);h.Write(b[:])}
type receipt struct{Schema,Mode,Regime,SourceSHA,TruthSHA,OutputSHA string;Seed uint64;Episodes,Queries,Known,Correct,FalsePositive,LogicalBytes int;PeakRSSBytes uint64;Accuracy float64}
func worker(seed uint64,regime,mode string)(receipt,error){var out receipt;n:=nitems(regime);if n==0{return out,fmt.Errorf("regime")};switch mode{case "DIRECT_INDEX","BIT_SIGNATURE","COUNTING_BLOOM","VSA_SUM":default:return out,fmt.Errorf("mode")}
 src,truth,pred:=sha256.New(),sha256.New(),sha256.New();correct,known,fp:=0,0,0;logical:=0
 for ep:=0;ep<64;ep++{keys:=make([]vector,n);vals:=make([]int,n);dict:=make([]vector,256);var votes[2048]int16;var bundle vector;var bloom[64]uint8
  for i:=range dict{dict[i]=signature(seed,ep,i,0x8170)}
  for i:=0;i<n;i++{keys[i]=signature(seed,ep,i,0x6b65);vals[i]=val(seed,ep,i);put(src,uint64(i));put(src,uint64(vals[i]));for _,v:=range keys[i]{put(src,v)};for _,v:=range dict[vals[i]]{put(src,v)}
   if mode=="VSA_SUM"{z:=xor(keys[i],dict[vals[i]]);for j:=0;j<2048;j++{if z[j/64]&(1<<uint(j%64))!=0{votes[j]++}else{votes[j]--}}}
   if mode=="COUNTING_BLOOM"{h:=mix(uint64(i)^seed^uint64(ep));bloom[h%64]++}
  }
  if mode=="VSA_SUM"{for j,c:=range votes{if c>0||c==0&&mix(seed^uint64(ep)^uint64(j))&1==1{bundle[j/64]|=1<<uint(j%64)}}}
  for i:=0;i<256;i++{key:=qkey(seed,ep,i,n,regime);want,exists:=0,key<n;if exists{known++;want=val(seed,ep,key)};put(src,uint64(key));put(truth,uint64(want));if exists{put(truth,1)}else{put(truth,0)}
   got,found:=0,false
   if mode=="VSA_SUM"{z:=xor(bundle,signature(seed,ep,key,0x6b65));best,d:=0,2049;for id:=0;id<256;id++{q:=distance(z,dict[id]);if q<d{best,d=id,q}};if d<=760{got,found=best,true}}
   if mode=="DIRECT_INDEX"&&exists{got,found=vals[key],true}
   if mode=="BIT_SIGNATURE"&&exists&&distance(signature(seed,ep,key,0x6b65),keys[key])==0{got,found=vals[key],true}
   if mode=="COUNTING_BLOOM"&&exists{h:=mix(uint64(key)^seed^uint64(ep));if bloom[h%64]>0{got,found=vals[key],true}}
   put(pred,uint64(got));if found{put(pred,1)}else{put(pred,0)};if exists&&found&&got==want||!exists&&!found{correct++};if !exists&&found{fp++}
  }
 }
 switch mode{case "DIRECT_INDEX":logical=n*16;case "BIT_SIGNATURE":logical=n*256+n*2;case "COUNTING_BLOOM":logical=n*16+64;case "VSA_SUM":logical=256+256*256}
 rss,e:=peakResidentBytes();if e!=nil{return out,e};if rss==0{return out,fmt.Errorf("RSS")};return receipt{Schema:schema,Mode:mode,Regime:regime,Seed:seed,Episodes:64,Queries:16384,Known:known,Correct:correct,FalsePositive:fp,LogicalBytes:logical,PeakRSSBytes:rss,Accuracy:float64(correct)/16384,SourceSHA:hex.EncodeToString(src.Sum(nil)),TruthSHA:hex.EncodeToString(truth.Sum(nil)),OutputSHA:hex.EncodeToString(pred.Sum(nil))},nil}
type trial struct{Receipt receipt;CPUSeconds,WallSeconds float64}
type cohort struct{Regime,Fastest string;Accuracy,CPU,RSS,Bytes map[string]float64;CPURatio,RSSRatio,BytesRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;Workers int;Trials []trial;Cohorts []cohort}
func med(a []float64)float64{sort.Float64s(a);return a[len(a)/2]}
func child(exe,mode,regime string,seed uint64)(trial,error){var t trial;c:=exec.Command(exe,"-child","-mode",mode,"-regime",regime,"-seed",fmt.Sprint(seed));var o,e bytes.Buffer;c.Stdout=&o;c.Stderr=&e;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds();if err!=nil{return t,fmt.Errorf("%s/%s: %w %s",regime,mode,err,e.String())};cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return t,fmt.Errorf("zero CPU")};var w receipt;if err=json.Unmarshal(o.Bytes(),&w);err!=nil{return t,err};if w.Schema!=schema||w.Mode!=mode||w.Regime!=regime||w.Seed!=seed||w.Queries!=16384||w.PeakRSSBytes==0{return t,fmt.Errorf("child invalid")};return trial{w,cpu,wall},nil}
func cohortFor(rows []trial,regime string)(cohort,error){c:=cohort{Regime:regime,Accuracy:map[string]float64{},CPU:map[string]float64{},RSS:map[string]float64{},Bytes:map[string]float64{}};modes:=[]string{"DIRECT_INDEX","BIT_SIGNATURE","COUNTING_BLOOM","VSA_SUM"};paired:=map[uint64]string{};for _,mode:=range modes{var accuracy,cpu,rss,bytes []float64;for _,t:=range rows{w:=t.Receipt;if w.Regime!=regime||w.Mode!=mode{continue};h:=w.SourceSHA+"/"+w.TruthSHA;if old,ok:=paired[w.Seed];ok&&old!=h{return c,fmt.Errorf("unpaired source")};paired[w.Seed]=h;accuracy=append(accuracy,w.Accuracy);cpu=append(cpu,t.CPUSeconds);rss=append(rss,float64(w.PeakRSSBytes));bytes=append(bytes,float64(w.LogicalBytes))};if len(accuracy)!=5{return c,fmt.Errorf("missing mode")};c.Accuracy[mode],c.CPU[mode],c.RSS[mode],c.Bytes[mode]=med(accuracy),med(cpu),med(rss),med(bytes)}
 c.Fastest="DIRECT_INDEX";for _,m:=range []string{"BIT_SIGNATURE","COUNTING_BLOOM"}{if c.CPU[m]<c.CPU[c.Fastest]{c.Fastest=m}};c.CPURatio=c.CPU["VSA_SUM"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["VSA_SUM"]/c.RSS[c.Fastest];c.BytesRatio=c.Bytes["VSA_SUM"]/c.Bytes["DIRECT_INDEX"];c.Pass=c.Accuracy["VSA_SUM"]>=.95&&c.CPURatio<=1.10&&c.RSSRatio<=1.10&&c.BytesRatio<=.25;return c,nil}
func drive(path string)error{exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS};seeds:=[]uint64{109101,109103,109107,109109,109111};for _,regime:=range []string{"SPARSE","MEDIUM","DENSE","OOD"}{for i,seed:=range seeds{modes:=[]string{"DIRECT_INDEX","BIT_SIGNATURE","COUNTING_BLOOM","VSA_SUM"};if i%2==1{modes=[]string{"VSA_SUM","COUNTING_BLOOM","BIT_SIGNATURE","DIRECT_INDEX"}};for _,mode:=range modes{t,e:=child(exe,mode,regime,seed);if e!=nil{return e};r.Trials=append(r.Trials,t)}};c,e:=cohortFor(r.Trials,regime);if e!=nil{return e};r.Cohorts=append(r.Cohorts,c)}
 r.Workers=len(r.Trials);if r.Workers!=80{return fmt.Errorf("missing children")};r.Classification="U18_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true;for _,c:=range r.Cohorts{pass=pass&&c.Pass};if pass{r.Classification="U18_RESTRICTED_SYNTHETIC_GO_RETRIEVAL_POSITIVE_ONLY"};b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,b,0644);e!=nil{return e};fmt.Println("ACC59_U18_NATIVE_80_PASS");fmt.Println("ACC59_U18_CLASSIFICATION="+r.Classification);return nil}
func main(){isChild:=flag.Bool("child",false,"");seed:=flag.Uint64("seed",109101,"");mode:=flag.String("mode","VSA_SUM","");regime:=flag.String("regime","SPARSE","");out:=flag.String("out","acc59-report.json","");flag.Parse();var e error;if *isChild{var r receipt;r,e=worker(*seed,*regime,*mode);if e==nil{e=json.NewEncoder(os.Stdout).Encode(r)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC59_U18_BLOCKED:",e);os.Exit(1)}}
