package main
import("bytes";"crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"os";"os/exec";"runtime";"sort";"time")
const schema="forge.acc55.u20.go.v1"
var seeds=[]uint64{105101,105103,105107,105109,105111}
var families=[]string{"AFFINE","QUADRATIC","CONSTANT","NOISY"}
var modes=[]string{"ENUM","COMPLEXITY","FIT_FIRST","MDL"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
type program struct{Kind int;A,B int64;Text string;Ops int}
func grammar()[]program{
 p:=[]program{{Kind:0,Text:"x",Ops:0}}
 for a:=-3;a<=3;a++{p=append(p,program{Kind:1,A:int64(a),Text:fmt.Sprintf("%d",a),Ops:0});p=append(p,program{Kind:2,A:int64(a),Text:fmt.Sprintf("(x+%d)",a),Ops:1});p=append(p,program{Kind:3,A:int64(a),Text:fmt.Sprintf("(x*%d)",a),Ops:1})}
 for a:=-3;a<=3;a++{for b:=-3;b<=3;b++{p=append(p,program{Kind:4,A:int64(a),B:int64(b),Text:fmt.Sprintf("((x+%d)*%d)",a,b),Ops:2});p=append(p,program{Kind:5,A:int64(a),B:int64(b),Text:fmt.Sprintf("((x*%d)+%d)",a,b),Ops:2});p=append(p,program{Kind:6,A:int64(a),B:int64(b),Text:fmt.Sprintf("((x+%d)*(x+%d))",a,b),Ops:3})}}
 sort.Slice(p,func(i,j int)bool{return p[i].Text<p[j].Text});return p
}
func eval(p program,x uint64)uint64{a,b:=uint64(p.A),uint64(p.B);switch p.Kind{case 0:return x;case 1:return a;case 2:return x+a;case 3:return x*a;case 4:return(x+a)*b;case 5:return x*a+b;case 6:return(x+a)*(x+b)};panic("kind")}
func target(seed uint64,task int,family string)program{
 a:=int64(int(mix(seed^uint64(task)*0x71cf0bd3)%7)-3)
 b:=int64(int(mix(seed^uint64(task)*0xbf58476d1ce4e5b9)%7)-3)
 if family=="CONSTANT"{return program{Kind:1,A:a}}
 if family=="QUADRATIC"{return program{Kind:6,A:a,B:b}}
 if family=="NOISY"{return program{Kind:5,A:a,B:b}}
 return program{Kind:4,A:a,B:b}
}
func xAt(seed uint64,task,j int,test bool)uint64{
 h:=mix(seed^uint64(task)*0xa0761d6478bd642f^uint64(j)*0xe7037ed1a0b428db)
 if test{return uint64(int64(100+(h%257)))};return uint64(int64(-40+int64(h%81)))
}
func hashUint(h interface{Write([]byte)(int,error)},x uint64){var b[8]byte;binary.LittleEndian.PutUint64(b[:],x);h.Write(b[:])}
type worker struct{Schema,Family,Mode,InputSHA256,TruthSHA256,PredictionSHA256,SelectedSHA256 string;Seed uint64;Tasks,TrainPoints,TestPoints,Candidates,Evaluations,CorrectHeldout,CorrectTrain int;PeakRSSBytes uint64;HeldoutAccuracy float64}
func work(mode,family string,seed uint64)(worker,error){
 var z worker;found:=false;for _,x:=range modes{if x==mode{found=true}};if !found{return z,errors.New("mode")}
 found=false;for _,x:=range families{if x==family{found=true}};if !found{return z,errors.New("family")}
 programs:=grammar();src,truth,pred,selected:=sha256.New(),sha256.New(),sha256.New(),sha256.New()
 totalGood,totalTrain,evaluations:=0,0,0
 for task:=0;task<64;task++{
  answer:=target(seed,task,family);var xs [12]uint64;var ys [12]uint64
  for j:=0;j<12;j++{x:=xAt(seed,task,j,false);y:=eval(answer,x)
   if family=="NOISY"&&j%8==0{y++};xs[j]=x;ys[j]=y;hashUint(src,x);hashUint(src,y)}
  var testX [32]uint64;var testY [32]uint64
  for j:=0;j<32;j++{testX[j]=xAt(seed,task,j,true);testY[j]=eval(answer,testX[j]);hashUint(src,testX[j]);hashUint(truth,testX[j]);hashUint(truth,testY[j])}
  best:=0;bestPrimary,bestSecondary:=int(^uint(0)>>1),int(^uint(0)>>1)
  for i,p:=range programs{
   mismatch:=0;for j,x:=range xs{evaluations++;if eval(p,x)!=ys[j]{mismatch++}}
   primary,secondary:=mismatch,len(p.Text)
   switch mode{
   case "ENUM":if mismatch==0{primary=0}else{primary=1+mismatch};secondary=i
   case "COMPLEXITY":primary=p.Ops;secondary=i
   case "FIT_FIRST":primary=mismatch;secondary=i
   case "MDL":primary=len(p.Text)+8*mismatch;secondary=i
   }
   if primary<bestPrimary||primary==bestPrimary&&secondary<bestSecondary{best=i;bestPrimary=primary;bestSecondary=secondary}
  }
  picked:=programs[best]
  for _,c:=range []byte(picked.Text){hashUint(selected,uint64(c))}
  hashUint(selected,uint64(len(picked.Text)))
  for j,x:=range xs{if eval(picked,x)==ys[j]{totalTrain++}}
  for j,x:=range testX{y:=eval(picked,x);hashUint(pred,x);hashUint(pred,y);if y==testY[j]{totalGood++}}
 }
 rss,err:=peakResidentBytes();if err!=nil{return z,err};if rss==0{return z,errors.New("missing RSS")}
 return worker{Schema:schema,Family:family,Mode:mode,Seed:seed,Tasks:64,TrainPoints:64*12,TestPoints:64*32,Candidates:len(programs),Evaluations:evaluations,CorrectHeldout:totalGood,CorrectTrain:totalTrain,PeakRSSBytes:rss,HeldoutAccuracy:float64(totalGood)/float64(64*32),InputSHA256:hex.EncodeToString(src.Sum(nil)),TruthSHA256:hex.EncodeToString(truth.Sum(nil)),PredictionSHA256:hex.EncodeToString(pred.Sum(nil)),SelectedSHA256:hex.EncodeToString(selected.Sum(nil))},nil
}
type trial struct{Worker worker;CPUSeconds,WallSeconds float64}
type cohort struct{Family,Fastest string;Accuracy,CPU,RSS map[string]float64;AccuracyGain,CPURatio,RSSRatio float64;Regressed,Improved bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelAcceleration bool;Trials []trial;Cohorts []cohort}
func median(v []float64)float64{a:=append([]float64(nil),v...);sort.Float64s(a);return a[len(a)/2]}
func child(exe,mode,family string,seed uint64)(trial,error){var t trial;c:=exec.Command(exe,"-worker","-mode",mode,"-family",family,"-seed",fmt.Sprint(seed));var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr;start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds();if err!=nil{return t,fmt.Errorf("%s/%s %w %s",mode,family,err,stderr.String())};if c.ProcessState==nil{return t,errors.New("missing process state")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds();if cpu<=0||wall<=0{return t,errors.New("zero cpu/wall")}
 var w worker;if e:=json.Unmarshal(stdout.Bytes(),&w);e!=nil{return t,e};if w.Schema!=schema||w.Mode!=mode||w.Family!=family||w.Seed!=seed||w.Tasks!=64||w.TrainPoints!=768||w.TestPoints!=2048||w.Candidates<=0||w.Evaluations!=w.Candidates*768||w.PeakRSSBytes==0||len(w.TruthSHA256)!=64{return t,errors.New("invalid worker")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil}
func compare(all []trial,family string)(cohort,error){
 c:=cohort{Family:family,Accuracy:map[string]float64{},CPU:map[string]float64{},RSS:map[string]float64{}}
 groups:=map[string][]trial{};paired:=map[uint64]string{}
 for _,r:=range all{w:=r.Worker;if w.Family!=family{continue};groups[w.Mode]=append(groups[w.Mode],r);h:=w.InputSHA256+"/"+w.TruthSHA256;if old,ok:=paired[w.Seed];ok&&old!=h{return c,errors.New("unpaired task source")};paired[w.Seed]=h}
 if len(paired)!=5{return c,errors.New("missing seeds")}
 for _,m:=range modes{rr:=groups[m];if len(rr)!=5{return c,errors.New("missing mode")};var ac,cp,rss []float64;for _,r:=range rr{ac=append(ac,r.Worker.HeldoutAccuracy);cp=append(cp,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes))};c.Accuracy[m]=median(ac);c.CPU[m]=median(cp);c.RSS[m]=median(rss)}
 c.Fastest="ENUM";bestAccuracy:=c.Accuracy["ENUM"]
 for _,m:=range []string{"COMPLEXITY","FIT_FIRST"}{if c.CPU[m]<c.CPU[c.Fastest]{c.Fastest=m};if c.Accuracy[m]>bestAccuracy{bestAccuracy=c.Accuracy[m]}}
 c.AccuracyGain=c.Accuracy["MDL"]-bestAccuracy;c.CPURatio=c.CPU["MDL"]/c.CPU[c.Fastest];c.RSSRatio=c.RSS["MDL"]/c.RSS[c.Fastest];c.Improved=c.AccuracyGain>=.05;c.Regressed=c.AccuracyGain<-.02
 return c,nil}
func drive(path string)error{
 exe,e:=os.Executable();if e!=nil{return e};r:=report{Schema:schema,OS:runtime.GOOS,Trials:make([]trial,0,80)}
 for _,family:=range families{for i,seed:=range seeds{order:=[]string{"ENUM","COMPLEXITY","FIT_FIRST","MDL"};if i%2==1{order=[]string{"MDL","FIT_FIRST","COMPLEXITY","ENUM"}}
  for _,mode:=range order{t,e:=child(exe,mode,family,seed);if e!=nil{return e};r.Trials=append(r.Trials,t)}}
  c,e:=compare(r.Trials,family);if e!=nil{return e};r.Cohorts=append(r.Cohorts,c)}
 r.NativeChildCount=len(r.Trials);if r.NativeChildCount!=80{return errors.New("incomplete evidence")}
 improvements,pass:=0,true;for _,c:=range r.Cohorts{if c.Improved{improvements++};if c.Regressed||c.CPURatio>1.10||c.RSSRatio>1.10{pass=false}}
 r.Classification="U20_NO_GENERAL_VERIFIED_NATIVE_GO_LEARNING_WIN";if pass&&improvements>=2{r.Classification="U20_RESTRICTED_SYNTHETIC_GO_LEARNING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC55_U20_NATIVE_CHILDREN_80_PASS");fmt.Println("ACC55_U20_CLASSIFICATION="+r.Classification);return nil
}
func main(){w:=flag.Bool("worker",false,"");mode:=flag.String("mode","MDL","");family:=flag.String("family","AFFINE","");seed:=flag.Uint64("seed",105101,"");out:=flag.String("out","acc55-report.json","");flag.Parse();var e error;if *w{var z worker;z,e=work(*mode,*family,*seed);if e==nil{e=json.NewEncoder(os.Stdout).Encode(z)}}else{e=drive(*out)};if e!=nil{fmt.Fprintln(os.Stderr,"ACC55_U20_BLOCKED:",e);os.Exit(1)}}
