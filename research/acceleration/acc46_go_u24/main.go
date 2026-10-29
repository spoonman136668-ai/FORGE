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
type trial struct{
 Worker workerResult
 CPUSeconds float64
 WallSeconds float64
 PairOrder string
}
type comparison struct{
 Regime string
 MedianError map[string]float64
 MedianUnseenError map[string]float64
 MedianCPU map[string]float64
 MedianRSS map[string]float64
 FastestControl string
 AccuracyControl string
 UnseenControl string
 ErrorGap float64
 UnseenGap float64
 CPURatio float64
 RSSRatio float64
 Pass bool
}
type report struct{
 Schema string
 OS string
 GoVersion string
 OriginalHypotheses int
 AdditionalHypotheses int
 NativeChildCount int
 ScientificFirstUse bool
 NativeModelAcceleration bool
 Records []trial
 Comparisons []comparison
 Classification string
}
func median(values []float64)float64{
 a:=append([]float64(nil),values...)
 sort.Float64s(a)
 if len(a)==0{return math.NaN()}
 n:=len(a)
 if n%2==0{return (a[n/2-1]+a[n/2])*0.5}
 return a[n/2]
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func runChild(exe,mode,regime string,seed uint64,order string)(trial,error){
 var row trial
 cmd:=exec.Command(exe,"-worker","-mode",mode,"-regime",regime,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer
 cmd.Stdout=&stdout;cmd.Stderr=&stderr
 start:=time.Now()
 err:=cmd.Run()
 wall:=time.Since(start).Seconds()
 if err!=nil{return row,fmt.Errorf("worker failed %s/%s/%d: %w %s",mode,regime,seed,err,stderr.String())}
 if cmd.ProcessState==nil{return row,errors.New("missing native child process CPU")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return row,fmt.Errorf("native CPU or wall unavailable %.9f %.9f",cpu,wall)}
 var w workerResult
 if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return row,fmt.Errorf("invalid worker JSON: %w",err)}
 if w.Schema!=schema||w.Mode!=mode||w.Regime!=regime||w.Seed!=seed||
  w.Episodes!=episodes||w.FitStateCount!=episodes*fitStates||
  w.HeldoutStateCount!=episodes*testStates||
  w.EvaluatedCells!=episodes*testStates*cells||
  w.CorrectCells>w.EvaluatedCells||w.UnseenCells<=0||
  w.CorrectUnseen>w.UnseenCells||w.UnseenCells>w.EvaluatedCells||
  w.PeakRSSBytes==0||w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"||
  len(w.SourceSHA256)!=64||len(w.FitSHA256)!=64||
  len(w.TruthSHA256)!=64||len(w.PredictionSHA256)!=64||
  !finite(w.ErrorRate)||!finite(w.UnseenErrorRate)||
  w.ErrorRate<0||w.ErrorRate>1||w.UnseenErrorRate<0||w.UnseenErrorRate>1 {
  return row,errors.New("worker cohort, source, error or OS physical RSS invalid")
 }
 expectedBytes:=2048
 if mode=="GLOBAL_FREQ"{expectedBytes=32}
 if mode=="REGION_FREQ"{expectedBytes=128}
 if w.LogicalBytes!=expectedBytes{return row,errors.New("unbounded or mislabeled learner storage")}
 if mode=="LOCAL_CA"&&w.NeighborMessageReads!=int64(w.EvaluatedCells*4){return row,errors.New("missing local exchange cost")}
 if mode!="LOCAL_CA"&&w.NeighborMessageReads!=0{return row,errors.New("control charged local-message reads")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall,PairOrder:order},nil
}
func compare(rows []trial,regime string)(comparison,error){
 c:=comparison{Regime:regime,MedianError:map[string]float64{},MedianUnseenError:map[string]float64{},MedianCPU:map[string]float64{},MedianRSS:map[string]float64{}}
 grouped:=map[string][]trial{}
 paired:=map[uint64]workerResult{}
 for _,row:=range rows{
  w:=row.Worker
  if w.Regime!=regime{continue}
  grouped[w.Mode]=append(grouped[w.Mode],row)
  if prior,ok:=paired[w.Seed];ok{
   if prior.SourceSHA256!=w.SourceSHA256||prior.FitSHA256!=w.FitSHA256||
    prior.TruthSHA256!=w.TruthSHA256||prior.UnseenCells!=w.UnseenCells{
    return c,errors.New("unequal paired FIT or heldout source/oracle")
   }
  }else{paired[w.Seed]=w}
 }
 if len(paired)!=len(seeds){return c,errors.New("missing paired seed")}
 for _,m:=range modes{
  v:=grouped[m]
  if len(v)!=len(seeds){return c,fmt.Errorf("missing arm %s",m)}
  var errorRate,unseenRate,cpu,rss []float64
  for _,z:=range v{
   errorRate=append(errorRate,z.Worker.ErrorRate)
   unseenRate=append(unseenRate,z.Worker.UnseenErrorRate)
   cpu=append(cpu,z.CPUSeconds)
   rss=append(rss,float64(z.Worker.PeakRSSBytes))
  }
  c.MedianError[m]=median(errorRate)
  c.MedianUnseenError[m]=median(unseenRate)
  c.MedianCPU[m]=median(cpu)
  c.MedianRSS[m]=median(rss)
  if !finite(c.MedianError[m])||!finite(c.MedianUnseenError[m])||
   !finite(c.MedianCPU[m])||c.MedianCPU[m]<=0||c.MedianRSS[m]<=0{
   return c,errors.New("invalid cohort accuracy, CPU or RSS median")
  }
 }
 candidates:=[]string{"GLOBAL_FREQ","REGION_FREQ","CELL_FREQ"}
 c.FastestControl=candidates[0]
 c.AccuracyControl=candidates[0]
 c.UnseenControl=candidates[0]
 for _,m:=range candidates[1:]{
  if c.MedianCPU[m]<c.MedianCPU[c.FastestControl]{c.FastestControl=m}
  if c.MedianError[m]<c.MedianError[c.AccuracyControl]{c.AccuracyControl=m}
  if c.MedianUnseenError[m]<c.MedianUnseenError[c.UnseenControl]{c.UnseenControl=m}
 }
 c.ErrorGap=c.MedianError["LOCAL_CA"]-c.MedianError[c.AccuracyControl]
 c.UnseenGap=c.MedianUnseenError["LOCAL_CA"]-c.MedianUnseenError[c.UnseenControl]
 c.CPURatio=c.MedianCPU["LOCAL_CA"]/c.MedianCPU[c.FastestControl]
 c.RSSRatio=c.MedianRSS["LOCAL_CA"]/c.MedianRSS[c.FastestControl]
 c.Pass=c.ErrorGap<=0.01&&c.UnseenGap<=0.01&&c.CPURatio<=0.90&&c.RSSRatio<=1.10
 return c,nil
}
func drive(output string)error{
 exe,err:=os.Executable()
 if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),OriginalHypotheses:30,
  AdditionalHypotheses:6,Records:make([]trial,0,60)}
 for _,regime:=range regimes{
  for i,seed:=range seeds{
   order:=[]string{"GLOBAL_FREQ","REGION_FREQ","CELL_FREQ","LOCAL_CA"}
   label:="AB"
   if i%2==1{
    order=[]string{"LOCAL_CA","CELL_FREQ","REGION_FREQ","GLOBAL_FREQ"}
    label="BA"
   }
   for _,mode:=range order{
    row,e:=runChild(exe,mode,regime,seed,label)
    if e!=nil{return e}
    r.Records=append(r.Records,row)
   }
  }
  c,e:=compare(r.Records,regime)
  if e!=nil{return e}
  r.Comparisons=append(r.Comparisons,c)
 }
 r.NativeChildCount=len(r.Records)
 if r.NativeChildCount!=60||len(r.Comparisons)!=3{return errors.New("incomplete source or child workers")}
 r.Classification="U24_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN"
 passed:=true
 for _,c:=range r.Comparisons{passed=passed&&c.Pass}
 if passed{r.Classification="U24_RESTRICTED_NATIVE_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ")
 if e!=nil{return e}
 if e=os.WriteFile(output,append(b,byte(10)),0644);e!=nil{return e}
 fmt.Println("ACC46_U24_60_ACTUAL_NATIVE_CHILDREN=PASS")
 fmt.Println("ACC46_U24_ENGINEERING_CLASSIFICATION="+r.Classification)
 return nil
}
func main(){
 child:=flag.Bool("worker",false,"single native cold worker")
 mode:=flag.String("mode","LOCAL_CA","learner arm")
 regime:=flag.String("regime","UNIFORM","source regime")
 seed:=flag.Uint64("seed",96301,"paired deterministic seed")
 out:=flag.String("out","acc46-report.json","record report file")
 flag.Parse()
 var err error
 if *child{
  var w workerResult
  w,err=work(*mode,*regime,*seed)
  if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}
 }else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC46_U24_BLOCKED:",err);os.Exit(1)}
}
