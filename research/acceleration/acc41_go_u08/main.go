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
type record struct{
 Worker workerResult `json:"worker"`
 CPUSeconds float64 `json:"cpu_seconds"`
 WallSeconds float64 `json:"wall_seconds"`
 Trial int `json:"trial"`
 Order string `json:"order"`
}
type comparison struct{
 Scenario string `json:"scenario"`
 MedianMSE map[string]float64 `json:"median_heldout_mse"`
 MedianCPU map[string]float64 `json:"median_cpu_seconds"`
 MedianRSS map[string]float64 `json:"median_peak_rss_bytes"`
 AccuracyControl string `json:"accuracy_control"`
 CPUControl string `json:"cpu_control"`
 MSEMargin float64 `json:"mse_margin_vs_best_fitted"`
 CPURatio float64 `json:"cpu_ratio"`
 RSSRatio float64 `json:"rss_ratio"`
 Pass bool `json:"pass"`
}
type report struct{
 Schema string `json:"schema"`
 OS string `json:"os"`
 GoVersion string `json:"go_version"`
 RunnerName string `json:"runner_name"`
 NativeGoChildCount int `json:"native_go_child_count"`
 OriginalCandidateCount int `json:"original_candidate_count"`
 ExtraCandidateCount int `json:"extra_candidate_count"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 NativeModelAccelerationProven bool `json:"native_model_acceleration_proven"`
 Records []record `json:"records"`
 Comparisons []comparison `json:"comparisons"`
 Classification string `json:"classification"`
}
func median(x []float64)float64{
 if len(x)==0{return math.NaN()}
 q:=append([]float64(nil),x...);sort.Float64s(q)
 if len(q)%2==1{return q[len(q)/2]}
 return (q[len(q)/2-1]+q[len(q)/2])/2
}
func runChild(exe,mode,scenario string,seed uint64,trial int,order string)(record,error){
 var r record
 cmd:=exec.Command(exe,"-worker","-mode",mode,"-scenario",scenario,"-seed",fmt.Sprint(seed))
 var stdout,stderr bytes.Buffer;cmd.Stdout=&stdout;cmd.Stderr=&stderr
 start:=time.Now();err:=cmd.Run();wall:=time.Since(start).Seconds()
 if err!=nil{return r,fmt.Errorf("worker %s/%s/%d: %w: %s",mode,scenario,seed,err,stderr.String())}
 if cmd.ProcessState==nil{return r,errors.New("missing process state")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
 if cpu<=0||wall<=0{return r,fmt.Errorf("CPU or wall not measurable: %g/%g",cpu,wall)}
 var worker workerResult
 if err=json.Unmarshal(stdout.Bytes(),&worker);err!=nil{return r,fmt.Errorf("invalid worker JSON %w",err)}
 if worker.Schema!=schema||worker.Mode!=mode||worker.Scenario!=scenario||worker.Seed!=seed||worker.Sessions!=sessions||worker.HeldoutSamples!=sessions*(seriesLength-memoryLength)||worker.PeakRSSBytes==0||worker.PredictionSHA256==""||worker.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"{return r,errors.New("incomplete worker resource, trace or identity")}
 return record{Worker:worker,CPUSeconds:cpu,WallSeconds:wall,Trial:trial,Order:order},nil
}
func compare(rows []record,scenario string)(comparison,error){
 c:=comparison{Scenario:scenario,MedianMSE:map[string]float64{},MedianCPU:map[string]float64{},MedianRSS:map[string]float64{}}
 data:=map[string][]record{};bySeed:=map[uint64]workerResult{}
 for _,r:=range rows{
  if r.Worker.Scenario!=scenario{continue};w:=r.Worker;data[w.Mode]=append(data[w.Mode],r)
  if prev,ok:=bySeed[w.Seed];ok{if prev.TrainSourceSHA256!=w.TrainSourceSHA256||prev.HeldoutSourceSHA256!=w.HeldoutSourceSHA256{return c,errors.New("source parity violation")}}else{bySeed[w.Seed]=w}
 }
 if len(bySeed)!=len(trialSeeds){return c,errors.New("missing seed pairing")}
 for _,mode:=range modes{
  a:=data[mode];if len(a)!=len(trialSeeds){return c,fmt.Errorf("missing %s trial",mode)}
  var mse,cpu,rss []float64
  for _,r:=range a{mse=append(mse,r.Worker.HeldoutMSE);cpu=append(cpu,r.CPUSeconds);rss=append(rss,float64(r.Worker.PeakRSSBytes))}
  c.MedianMSE[mode]=median(mse);c.MedianCPU[mode]=median(cpu);c.MedianRSS[mode]=median(rss)
 }
 c.AccuracyControl="LAG12";if c.MedianMSE["LINEAR12"]<c.MedianMSE["LAG12"]{c.AccuracyControl="LINEAR12"}
 c.CPUControl="LAG12";if c.MedianCPU["LINEAR12"]<c.MedianCPU["LAG12"]{c.CPUControl="LINEAR12"}
 c.MSEMargin=c.MedianMSE["RESERVOIR12"]-c.MedianMSE[c.AccuracyControl]
 c.CPURatio=c.MedianCPU["RESERVOIR12"]/c.MedianCPU[c.CPUControl]
 c.RSSRatio=c.MedianRSS["RESERVOIR12"]/c.MedianRSS[c.CPUControl]
 c.Pass=c.MSEMargin<=0.01&&c.CPURatio<=0.90&&c.RSSRatio<=1.10
 for _,m:=range modes{if !finite(c.MedianMSE[m])||!finite(c.MedianCPU[m])||!finite(c.MedianRSS[m])||c.MedianCPU[m]<=0||c.MedianRSS[m]<=0{return c,errors.New("nonfinite or zero metric")}}
 return c,nil
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func drive(out string)error{
 exe,err:=os.Executable();if err!=nil{return err}
 r:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),RunnerName:os.Getenv("RUNNER_NAME"),OriginalCandidateCount:30,ExtraCandidateCount:6,Records:make([]record,0,60)}
 for _,scenario:=range scenarios{
  for trial,seed:=range trialSeeds{
   order:=append([]string(nil),modes...);direction:="AB"
   if trial%2==1{order=[]string{"RESERVOIR12","LINEAR12","LAG12","BIAS"};direction="BA"}
   for _,mode:=range order{
    row,err:=runChild(exe,mode,scenario,seed,trial,direction);if err!=nil{return err}
    r.Records=append(r.Records,row)
   }
  }
  c,e:=compare(r.Records,scenario);if e!=nil{return e};r.Comparisons=append(r.Comparisons,c)
 }
 r.NativeGoChildCount=len(r.Records)
 if r.NativeGoChildCount!=60||len(r.Comparisons)!=3{return errors.New("incomplete trial suite")}
 r.Classification="U08_NO_GENERAL_VERIFIED_NATIVE_GO_ACCELERATION"
 passed:=true;for _,c:=range r.Comparisons{passed=passed&&c.Pass}
 if passed{r.Classification="U08_RESTRICTED_NATIVE_GO_ENGINEERING_POSITIVE_ONLY"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return e}
 if e=os.WriteFile(out,append(b,byte(10)),0644);e!=nil{return e}
 fmt.Println("ACC41_MEASURED="+r.Classification)
 return nil
}
func main(){
 child:=flag.Bool("worker",false,"run one metered worker")
 mode:=flag.String("mode","LAG12","experiment arm")
 scenario:=flag.String("scenario","PREVIOUS_BIT","experiment scenario")
 seed:=flag.Uint64("seed",73101,"paired trial seed")
 out:=flag.String("out","acc41-report.json","report path")
 flag.Parse();var err error
 if *child{var w workerResult;w,err=work(*mode,*scenario,*seed);if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}}else{err=drive(*out)}
 if err!=nil{fmt.Fprintln(os.Stderr,"ACC41_U08_BLOCKED:",err);os.Exit(1)}
}
