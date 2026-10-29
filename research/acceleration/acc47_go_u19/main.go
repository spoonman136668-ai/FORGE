package main
import("bytes";"encoding/json";"errors";"flag";"fmt";"math";"os";"os/exec";"runtime";"sort";"time")
type trial struct{Worker result;CPUSeconds,WallSeconds float64}
type cell struct{World string;MedianError,MedianCPU,MedianRSS map[string]float64;BestError,Fastest string;ErrorGap,CPURatio,RSSRatio float64;Pass bool}
type report struct{Schema,OS,Classification string;NativeChildCount int;ScientificFirstUse,NativeModelSpeedup bool;Trials []trial;Cohorts []cell}
func med(a []float64)float64{b:=append([]float64(nil),a...);sort.Float64s(b);n:=len(b);if n==0{return math.NaN()};if n%2==0{return (b[n/2-1]+b[n/2])/2};return b[n/2]}
func runChild(exe,arm,world string,seed uint64)(trial,error){
 var t trial;c:=exec.Command(exe,"-worker","-arm",arm,"-world",world,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer;c.Stdout=&stdout;c.Stderr=&stderr
 start:=time.Now();err:=c.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return t,fmt.Errorf("%s/%s/%d failed %w %s",arm,world,seed,err,stderr.String())}
 if c.ProcessState==nil{return t,errors.New("missing process state")}
 cpu:=(c.ProcessState.UserTime()+c.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return t,fmt.Errorf("unavailable native CPU %f wall %f",cpu,wall)}
 var w result;if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return t,err}
 if w.Schema!=schema||w.Arm!=arm||w.World!=world||w.Seed!=seed||w.Episodes!=episodes||w.FitRows!=fitN*episodes||w.HeldoutRows!=testN*episodes||w.Correct>w.HeldoutRows||w.StateBytes<=0||w.PeakRSSBytes==0||w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"||len(w.SourceSHA256)!=64||len(w.FitSHA256)!=64||len(w.TruthSHA256)!=64||len(w.PredictionSHA256)!=64||math.IsNaN(w.HeldoutError){return t,errors.New("invalid worker provenance")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall},nil
}
func compare(rows []trial,world string)(cell,error){
 z:=cell{World:world,MedianError:map[string]float64{},MedianCPU:map[string]float64{},MedianRSS:map[string]float64{}}
 groups:=map[string][]trial{};sources:=map[uint64]result{}
 for _,r:=range rows{w:=r.Worker;if w.World!=world{continue};groups[w.Arm]=append(groups[w.Arm],r)
  if a,ok:=sources[w.Seed];ok{if a.SourceSHA256!=w.SourceSHA256||a.FitSHA256!=w.FitSHA256||a.TruthSHA256!=w.TruthSHA256{return z,errors.New("unmatched source truth")}}else{sources[w.Seed]=w}
 }
 if len(sources)!=len(seeds){return z,errors.New("missing paired seeds")}
 for _,arm:=range arms{
  a:=groups[arm];if len(a)!=len(seeds){return z,fmt.Errorf("missing %s workers",arm)}
  var es,cs,rs []float64
  for _,v:=range a{es=append(es,v.Worker.HeldoutError);cs=append(cs,v.CPUSeconds);rs=append(rs,float64(v.Worker.PeakRSSBytes))}
  z.MedianError[arm]=med(es);z.MedianCPU[arm]=med(cs);z.MedianRSS[arm]=med(rs)
  if z.MedianCPU[arm]<=0||z.MedianRSS[arm]<=0{return z,errors.New("missing resources")}
 }
 z.BestError="FREQ16";z.Fastest="FREQ16"
 for _,arm:=range []string{"PERCEPTRON","LUT4"}{
  if z.MedianError[arm]<z.MedianError[z.BestError]{z.BestError=arm}
  if z.MedianCPU[arm]<z.MedianCPU[z.Fastest]{z.Fastest=arm}
 }
 z.ErrorGap=z.MedianError["TSETLIN16"]-z.MedianError[z.BestError]
 z.CPURatio=z.MedianCPU["TSETLIN16"]/z.MedianCPU[z.Fastest]
 z.RSSRatio=z.MedianRSS["TSETLIN16"]/z.MedianRSS[z.Fastest]
 z.Pass=z.ErrorGap<=0.01&&z.CPURatio<=0.9&&z.RSSRatio<=1.1
 return z,nil
}
func drive(path string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,Trials:make([]trial,0,80)}
 for _,world:=range worlds{
  for i,seed:=range seeds{
   order:=[]string{"FREQ16","PERCEPTRON","LUT4","TSETLIN16"}
   if i%2==1{order=[]string{"TSETLIN16","LUT4","PERCEPTRON","FREQ16"}}
   for _,arm:=range order{t,e:=runChild(exe,arm,world,seed);if e!=nil{return e};r.Trials=append(r.Trials,t)}
  }
  c,e:=compare(r.Trials,world);if e!=nil{return e};r.Cohorts=append(r.Cohorts,c)
 }
 r.NativeChildCount=len(r.Trials);if r.NativeChildCount!=80||len(r.Cohorts)!=4{return errors.New("incomplete worker set")}
 r.Classification="U19_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN";pass:=true
 for _,c:=range r.Cohorts{pass=pass&&c.Pass}
 if pass{r.Classification="U19_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e};if e=os.WriteFile(path,append(b,10),0644);e!=nil{return e}
 fmt.Println("ACC47_80_TRUE_COLD_WORKERS=PASS")
 fmt.Println("ACC47_U19_CLASSIFICATION="+r.Classification)
 return nil
}
func main(){worker:=flag.Bool("worker",false,"worker");arm:=flag.String("arm","TSETLIN16","arm");world:=flag.String("world","SPARSE_OR","world");seed:=flag.Uint64("seed",97101,"seed");out:=flag.String("out","acc47-report.json","report");flag.Parse()
 var err error;if *worker{var w result;w,err=work(*arm,*world,*seed);if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}}else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC47_U19_BLOCKED:",err);os.Exit(1)}
}
