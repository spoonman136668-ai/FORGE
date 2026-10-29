package main

import(
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "time"
)
type record struct{
 Worker worker
 CPUSeconds float64
 WallSeconds float64
 Order string
}
type comparison struct{
 Cohort string
 MedianRecall map[string]float64
 MedianCPU map[string]float64
 MedianRSS map[string]float64
 MedianFPR map[string]float64
 FastestControl string
 RecallControl string
 CPUratio float64
 RSSratio float64
 RecallGap float64
 WrongZero bool
 Pass bool
}
type report struct{
 Schema string
 OS string
 GoVersion string
 RunnerName string
 OriginalHypotheses int
 AddedHypotheses int
 NativeChildCount int
 ScientificFirstUse bool
 NativeModelSpeedupProven bool
 Records []record
 Comparisons []comparison
 Classification string
}
func median(x []float64)float64{
 if len(x)==0{return math.NaN()}
 y:=append([]float64(nil),x...);sort.Float64s(y)
 if len(y)%2!=0{return y[len(y)/2]}
 return (y[len(y)/2-1]+y[len(y)/2])/2
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func runChild(exe,mode,cohort string,seed uint64,order string)(record,error){
 var r record
 cmd:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer;cmd.Stdout=&stdout;cmd.Stderr=&stderr
 start:=time.Now();err:=cmd.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return r,fmt.Errorf("native child failed %s/%s/%d: %w %s",mode,cohort,seed,err,stderr.String())}
 if cmd.ProcessState==nil{return r,errors.New("missing child process accounting")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return r,fmt.Errorf("unavailable child CPU/wall: %g %g",cpu,wall)}
 var w worker
 if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return r,fmt.Errorf("bad child JSON: %w",err)}
 n,_:=size(cohort)
 if w.Schema!=schema||w.Mode!=mode||w.Cohort!=cohort||w.Seed!=seed||
  w.Episodes!=episodes||w.InsertCount!=episodes*n||w.QueryCount!=episodes*queries||
  w.Present!=episodes*queries/2||w.Absent!=episodes*queries/2||
  w.StateBytes!=logicalBudget||w.PeakRSSBytes==0||
  w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"||
  len(w.SourceSHA256)!=64||len(w.TruthSHA256)!=64||len(w.OutputSHA256)!=64||
  w.CorrectPresent>w.Present||w.WrongPresent>w.Present||w.FalsePositiveAbsent>w.Absent||
  !finite(w.Recall)||!finite(w.AbsentFPR){return r,errors.New("corrupt measured worker identity, counters or resources")}
 return record{Worker:w,CPUSeconds:cpu,WallSeconds:wall,Order:order},nil
}
func compare(rows []record,cohort string)(comparison,error){
 x:=comparison{Cohort:cohort,MedianRecall:map[string]float64{},MedianCPU:map[string]float64{},MedianRSS:map[string]float64{},MedianFPR:map[string]float64{},WrongZero:true}
 grouped:=map[string][]record{}
 paired:=map[uint64]worker{}
 for _,r:=range rows{
  w:=r.Worker;if w.Cohort!=cohort{continue}
  grouped[w.Mode]=append(grouped[w.Mode],r)
  if prev,ok:=paired[w.Seed];ok{if prev.SourceSHA256!=w.SourceSHA256||prev.TruthSHA256!=w.TruthSHA256{return x,errors.New("paired source or truth mismatch")}}else{paired[w.Seed]=w}
  if w.Mode=="HRR_CCONV"&&w.WrongPresent!=0{x.WrongZero=false}
 }
 if len(paired)!=len(trials){return x,errors.New("missing paired seed")}
 for _,mode:=range modes{
  rs:=grouped[mode];if len(rs)!=len(trials){return x,fmt.Errorf("missing %s samples",mode)}
  var mse,cpu,rss,fpr []float64
  for _,r:=range rs{mse=append(mse,r.Worker.Recall);cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes));fpr=append(fpr,r.Worker.AbsentFPR)}
  x.MedianRecall[mode]=median(mse);x.MedianCPU[mode]=median(cpu);x.MedianRSS[mode]=median(rss);x.MedianFPR[mode]=median(fpr)
  if !finite(x.MedianRecall[mode])||!finite(x.MedianCPU[mode])||x.MedianCPU[mode]<=0||x.MedianRSS[mode]<=0{return x,errors.New("nonfinite or zero measured resource")}
 }
 controls:=[]string{"EXACT_ONE","EXACT_TWO","XOR_SUPERPOSE"}
 x.FastestControl=controls[0];x.RecallControl=controls[0]
 for _,mode:=range controls[1:]{
  if x.MedianCPU[mode]<x.MedianCPU[x.FastestControl]{x.FastestControl=mode}
  if x.MedianRecall[mode]>x.MedianRecall[x.RecallControl]{x.RecallControl=mode}
 }
 x.CPUratio=x.MedianCPU["HRR_CCONV"]/x.MedianCPU[x.FastestControl]
 x.RSSratio=x.MedianRSS["HRR_CCONV"]/x.MedianRSS[x.FastestControl]
 x.RecallGap=x.MedianRecall["HRR_CCONV"]-x.MedianRecall[x.RecallControl]
 x.Pass=x.WrongZero&&x.MedianFPR["HRR_CCONV"]<=0.005&&x.RecallGap>=-0.01&&x.CPUratio<=0.90&&x.RSSratio<=1.10
 if cohort=="LIGHT"{x.Pass=x.Pass&&x.MedianRecall["HRR_CCONV"]>=0.95}
 return x,nil
}
func drive(path string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),RunnerName:os.Getenv("RUNNER_NAME"),
  OriginalHypotheses:30,AddedHypotheses:6,Records:make([]record,0,60)}
 for _,cohort:=range cohorts{
  for i,seed:=range trials{
   order:=[]string{"EXACT_ONE","EXACT_TWO","XOR_SUPERPOSE","HRR_CCONV"};label:="AB"
   if i%2==1{order=[]string{"HRR_CCONV","XOR_SUPERPOSE","EXACT_TWO","EXACT_ONE"};label="BA"}
   for _,mode:=range order{
    row,err:=runChild(exe,mode,cohort,seed,label);if err!=nil{return err}
    r.Records=append(r.Records,row)
   }
  }
  c,err:=compare(r.Records,cohort);if err!=nil{return err}
  r.Comparisons=append(r.Comparisons,c)
 }
 r.NativeChildCount=len(r.Records);if r.NativeChildCount!=60||len(r.Comparisons)!=3{return errors.New("incomplete hosted workers")}
 r.Classification="U10_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN"
 pass:=true;for _,c:=range r.Comparisons{pass=pass&&c.Pass}
 if pass{r.Classification="U10_RESTRICTED_NATIVE_GO_ENGINEERING_POSITIVE_ONLY"}
 b,err:=json.MarshalIndent(r,"","  ");if err!=nil{return err}
 if err=os.WriteFile(path,append(b,byte(10)),0644);err!=nil{return err}
 fmt.Println("ACC44_NATIVE_60_COLD_CHILDREN=PASS; CLASSIFICATION="+r.Classification)
 return nil
}
func main(){
 child:=flag.Bool("worker",false,"run one child process")
 mode:=flag.String("mode","HRR_CCONV","arm")
 cohort:=flag.String("cohort","LIGHT","source cohort")
 seed:=flag.Uint64("seed",92201,"paired seed")
 out:=flag.String("out","acc44-report.json","raw receipt path")
 flag.Parse()
 var err error
 if *child{var w worker;w,err=work(*mode,*cohort,*seed);if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}
 }else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC44_U10_BLOCKED:",err);os.Exit(1)}
}
