package main

import (
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
type trial struct {
 Worker workerResult
 CPUSeconds float64
 WallSeconds float64
 PairOrder string
}
type cohortResult struct {
 Cohort string
 MedianRMSE map[string]float64
 MedianCPU map[string]float64
 MedianRSS map[string]float64
 MedianLogicalBytes map[string]float64
 FastestControl string
 CPURatio float64
 RSSRatio float64
 FactorBytesRatio float64
 Pass bool
}
type report struct {
 Schema string
 OS string
 GoVersion string
 NativeChildCount int
 OriginalHypotheses int
 AdditionalHypotheses int
 ScientificFirstUse bool
 NativeModelAcceleration bool
 Records []trial
 Cohorts []cohortResult
 Classification string
}
func median(v []float64)float64{
 s:=append([]float64(nil),v...);sort.Float64s(s)
 if len(s)==0{return math.NaN()}
 if len(s)%2==0{return 0.5*(s[len(s)/2-1]+s[len(s)/2])}
 return s[len(s)/2]
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func runChild(exe,mode,cohort string,seed uint64,order string)(trial,error){
 var record trial
 cmd:=exec.Command(exe,"-worker","-mode",mode,"-cohort",cohort,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer
 cmd.Stdout=&stdout;cmd.Stderr=&stderr
 start:=time.Now();err:=cmd.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return record,fmt.Errorf("%s/%s/%d worker error %w %s",mode,cohort,seed,err,stderr.String())}
 if cmd.ProcessState==nil{return record,errors.New("missing child process state")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return record,fmt.Errorf("CPU wall unusable %.9f %.9f",cpu,wall)}
 var w workerResult
 if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return record,err}
 if w.Schema!=schema||w.Mode!=mode||w.Cohort!=cohort||w.Seed!=seed||
 w.Episodes!=episodes||w.QueryVectors!=episodes*vectorsPerEpisode||
 w.MatrixRows!=dimension||w.PeakRSSBytes==0||w.LogicalBytes<=0||
 len(w.SourceSHA256)!=64||len(w.TruthSHA256)!=64||len(w.OutputSHA256)!=64||
 w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"||
 !finite(w.NormalizedRMSE)||w.NormalizedRMSE<0||!finite(w.MaxAbsError){
  return record,errors.New("invalid worker identity, accuracy, source or physical resources")
 }
 if mode=="LOWRANK16"&&(w.LastFactorRank<0||w.LastFactorRank>rankCap||w.LogicalBytes>dimension*dimension*8/2){return record,errors.New("invalid factorized state")}
 if mode!="LOWRANK16"&&w.LastFactorRank!=0{return record,errors.New("baseline secretly factorized")}
 return trial{Worker:w,CPUSeconds:cpu,WallSeconds:wall,PairOrder:order},nil
}
func compare(records []trial,cohort string)(cohortResult,error){
 c:=cohortResult{Cohort:cohort,MedianRMSE:map[string]float64{},MedianCPU:map[string]float64{},MedianRSS:map[string]float64{},MedianLogicalBytes:map[string]float64{}}
 grouped:=map[string][]trial{}
 source:=map[uint64]workerResult{}
 for _,r:=range records{
  w:=r.Worker;if w.Cohort!=cohort{continue}
  grouped[w.Mode]=append(grouped[w.Mode],r)
  if prev,ok:=source[w.Seed];ok{
   if prev.SourceSHA256!=w.SourceSHA256||prev.TruthSHA256!=w.TruthSHA256{return c,errors.New("paired source/truth mismatch")}
  }else{source[w.Seed]=w}
 }
 if len(source)!=len(seeds){return c,errors.New("missing paired seed")}
 for _,m:=range modes{
  r:=grouped[m]
  if len(r)!=len(seeds){return c,fmt.Errorf("incomplete mode %s",m)}
  var accuracy,cpu,rss,state []float64
  for _,v:=range r{
   accuracy=append(accuracy,v.Worker.NormalizedRMSE)
   cpu=append(cpu,v.CPUSeconds)
   rss=append(rss,float64(v.Worker.PeakRSSBytes))
   state=append(state,float64(v.Worker.LogicalBytes))
  }
  c.MedianRMSE[m]=median(accuracy)
  c.MedianCPU[m]=median(cpu)
  c.MedianRSS[m]=median(rss)
  c.MedianLogicalBytes[m]=median(state)
  if !finite(c.MedianRMSE[m])||!finite(c.MedianCPU[m])||c.MedianCPU[m]<=0||c.MedianRSS[m]<=0{return c,errors.New("invalid medians")}
 }
 c.FastestControl="DENSE"
 for _,m:=range []string{"TILED","CSR"}{if c.MedianCPU[m]<c.MedianCPU[c.FastestControl]{c.FastestControl=m}}
 c.CPURatio=c.MedianCPU["LOWRANK16"]/c.MedianCPU[c.FastestControl]
 c.RSSRatio=c.MedianRSS["LOWRANK16"]/c.MedianRSS[c.FastestControl]
 c.FactorBytesRatio=c.MedianLogicalBytes["LOWRANK16"]/c.MedianLogicalBytes["DENSE"]
 c.Pass=c.MedianRMSE["LOWRANK16"]<=0.01&&c.CPURatio<=0.90&&c.RSSRatio<=1.10&&c.FactorBytesRatio<=0.50
 return c,nil
}
func drive(output string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),OriginalHypotheses:30,AdditionalHypotheses:6,Records:make([]trial,0,60)}
 for _,cohort:=range cohorts{
  for i,seed:=range seeds{
   order:=[]string{"DENSE","TILED","CSR","LOWRANK16"};label:="AB"
   if i%2==1{order=[]string{"LOWRANK16","CSR","TILED","DENSE"};label="BA"}
   for _,mode:=range order{
    result,e:=runChild(exe,mode,cohort,seed,label);if e!=nil{return e}
    r.Records=append(r.Records,result)
   }
  }
  cell,e:=compare(r.Records,cohort);if e!=nil{return e}
  r.Cohorts=append(r.Cohorts,cell)
 }
 r.NativeChildCount=len(r.Records)
 if len(r.Cohorts)!=3||r.NativeChildCount!=60{return errors.New("incomplete trial set")}
 r.Classification="U22_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN"
 qualify:=true
 for _,c:=range r.Cohorts{qualify=qualify&&c.Pass}
 if qualify{r.Classification="U22_RESTRICTED_NATIVE_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e}
 if e=os.WriteFile(output,append(b,byte(10)),0644);e!=nil{return e}
 fmt.Println("ACC45_ORIGINAL_U22_60_COLD_WORKERS=PASS")
 fmt.Println("ACC45_U22_ENGINEERING_CLASSIFICATION="+r.Classification)
 return nil
}
func main(){
 child:=flag.Bool("worker",false,"run metered worker")
 mode:=flag.String("mode","LOWRANK16","benchmark arm")
 cohort:=flag.String("cohort","RANK8","matrix source family")
 seed:=flag.Uint64("seed",94101,"paired source seed")
 out:=flag.String("out","acc45-report.json","output report JSON")
 flag.Parse()
 var err error
 if *child{
  var w workerResult
  w,err=work(*mode,*cohort,*seed)
  if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}
 }else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC45_U22_BLOCKED:",err);os.Exit(1)}
}
