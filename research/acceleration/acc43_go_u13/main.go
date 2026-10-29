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
 Worker workerResult
 CPUSeconds float64
 WallSeconds float64
 Trial int
 PairOrder string
}
type comparison struct{
 Cohort string
 MedianRecall map[string]float64
 MedianFPR map[string]float64
 MedianCPU map[string]float64
 MedianWall map[string]float64
 MedianRSS map[string]float64
 SpeedControl string
 RecallControl string
 CPUratio float64
 RSSratio float64
 RecallGap float64
 ZeroWrongValues bool
 Pass bool
}
type report struct{
 Schema string
 OS string
 GoVersion string
 RunnerName string
 NativeChildCount int
 OriginalCount int
 AddedCount int
 ScientificFirstUse bool
 NativeModelSpeedupProven bool
 Records []record
 Comparisons []comparison
 Classification string
}
func med(x []float64)float64{
 if len(x)==0{return math.NaN()}
 a:=append([]float64(nil),x...);sort.Float64s(a)
 if len(a)%2==1{return a[len(a)/2]}
 return (a[len(a)/2-1]+a[len(a)/2])/2
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func runChild(exe,mode,cohort string,seed uint64,trial int,order string)(record,error){
 var r record
 cmd:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer;cmd.Stdout=&stdout;cmd.Stderr=&stderr
 started:=time.Now();err:=cmd.Run();wall:=time.Since(started).Seconds()
 if err!=nil{return r,fmt.Errorf("failed worker %s/%s/%d: %w: %s",mode,cohort,seed,err,stderr.String())}
 if cmd.ProcessState==nil{return r,errors.New("missing process state")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return r,fmt.Errorf("missing positive child process CPU/wall %.6f %.6f",cpu,wall)}
 var w workerResult
 if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return r,fmt.Errorf("bad worker JSON: %w",err)}
 if w.Schema!=schema||w.Cohort!=cohort||w.Mode!=mode||w.Seed!=seed||w.Episodes!=episodes||
 w.InsertCount!=writes*episodes||w.QueryCount!=queries*episodes||
 w.PresentCount!=queries*episodes/2||w.AbsentCount!=queries*episodes/2||
 w.SourceDigest==""||w.OracleDigest==""||w.ResultDigest==""||w.PeakRSSBytes==0||
 w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"{return r,errors.New("invalid worker schema/count/source/RSS")}
 if w.CorrectPresent>w.PresentCount||w.FalsePositiveAbsent>w.AbsentCount||w.WrongPresentValue>w.PresentCount{return r,errors.New("invalid accuracy counts")}
 if !finite(w.Recall)||!finite(w.FalsePositiveRate){return r,errors.New("nonfinite retrieval quality")}
 return record{Worker:w,CPUSeconds:cpu,WallSeconds:wall,Trial:trial,PairOrder:order},nil
}
func compare(rows []record,cohort string)(comparison,error){
 c:=comparison{Cohort:cohort,MedianRecall:map[string]float64{},MedianFPR:map[string]float64{},MedianCPU:map[string]float64{},MedianWall:map[string]float64{},MedianRSS:map[string]float64{},ZeroWrongValues:true}
 groups:=map[string][]record{}
 paired:=map[uint64]workerResult{}
 for _,row:=range rows{
  w:=row.Worker;if w.Cohort!=cohort{continue}
  groups[w.Mode]=append(groups[w.Mode],row)
  if first,ok:=paired[w.Seed];ok{
   if first.SourceDigest!=w.SourceDigest||first.OracleDigest!=w.OracleDigest{return c,errors.New("different source or oracle across arms")}
  }else{paired[w.Seed]=w}
  if w.WrongPresentValue!=0{c.ZeroWrongValues=false}
 }
 if len(paired)!=len(seeds){return c,errors.New("missing seed pair")}
 for _,m:=range modes{
  x:=groups[m];if len(x)!=len(seeds){return c,fmt.Errorf("incomplete control %s: %d",m,len(x))}
  var recall,fpr,cpu,wall,rss []float64
  for _,row:=range x{w:=row.Worker;recall=append(recall,w.Recall);fpr=append(fpr,w.FalsePositiveRate);cpu=append(cpu,row.CPUSeconds);wall=append(wall,row.WallSeconds);rss=append(rss,float64(w.PeakRSSBytes))}
  c.MedianRecall[m]=med(recall);c.MedianFPR[m]=med(fpr);c.MedianCPU[m]=med(cpu);c.MedianWall[m]=med(wall);c.MedianRSS[m]=med(rss)
  if !finite(c.MedianCPU[m])||c.MedianCPU[m]<=0||c.MedianRSS[m]<=0{return c,errors.New("invalid CPU or peak RSS")}
 }
 c.SpeedControl="EXACT_SINGLE";if c.MedianCPU["EXACT_TWO"]<c.MedianCPU["EXACT_SINGLE"]{c.SpeedControl="EXACT_TWO"}
 c.RecallControl="EXACT_SINGLE";if c.MedianRecall["EXACT_TWO"]>c.MedianRecall["EXACT_SINGLE"]{c.RecallControl="EXACT_TWO"}
 c.CPUratio=c.MedianCPU["SKETCH_TWO"]/c.MedianCPU[c.SpeedControl]
 c.RSSratio=c.MedianRSS["SKETCH_TWO"]/c.MedianRSS[c.SpeedControl]
 c.RecallGap=c.MedianRecall["SKETCH_TWO"]-c.MedianRecall[c.RecallControl]
 c.Pass=c.ZeroWrongValues&&c.MedianFPR["SKETCH_TWO"]<=0.002&&c.RecallGap>=-0.01&&c.CPUratio<=0.90&&c.RSSratio<=1.10
 if cohort=="HOT"{c.Pass=c.Pass&&c.MedianRecall["SKETCH_TWO"]>=0.98}
 return c,nil
}
func drive(out string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),RunnerName:os.Getenv("RUNNER_NAME"),OriginalCount:30,AddedCount:6,Records:make([]record,0,80)}
 for _,cohort:=range cohorts{
  for trial,seed:=range seeds{
   order:=[]string{"FULL_MAP","EXACT_SINGLE","EXACT_TWO","SKETCH_TWO"};label:="AB"
   if trial%2==1{order=[]string{"SKETCH_TWO","EXACT_TWO","EXACT_SINGLE","FULL_MAP"};label="BA"}
   for _,m:=range order{
    row,e:=runChild(exe,m,cohort,seed,trial,label);if e!=nil{return e}
    r.Records=append(r.Records,row)
   }
  }
  c,e:=compare(r.Records,cohort);if e!=nil{return e}
  r.Comparisons=append(r.Comparisons,c)
 }
 r.NativeChildCount=len(r.Records)
 if r.NativeChildCount!=80||len(r.Comparisons)!=4{return errors.New("incomplete native workers")}
 r.Classification="U13_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN"
 passed:=true;for _,c:=range r.Comparisons{passed=passed&&c.Pass}
 if passed{r.Classification="U13_RESTRICTED_GO_KV_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e}
 if e=os.WriteFile(out,append(b,byte(10)),0644);e!=nil{return e}
 fmt.Printf("ACC43_NATIVE_80_COMPLETE=PASS; CLASSIFICATION=%s\n",r.Classification)
 return nil
}
func main(){
 worker:=flag.Bool("worker",false,"run one native child")
 mode:=flag.String("mode","SKETCH_TWO","which arm")
 cohort:=flag.String("cohort","HOT","which workload")
 seed:=flag.Uint64("seed",86101,"source seed")
 output:=flag.String("out","acc42-report.json","output report")
 flag.Parse()
 var err error
 if *worker{
  var r workerResult;r,err=work(*mode,*cohort,*seed)
  if err==nil{err=json.NewEncoder(os.Stdout).Encode(r)}
 }else{err=drive(*output)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC43_U13_BLOCKED:",err);os.Exit(1)}
}
