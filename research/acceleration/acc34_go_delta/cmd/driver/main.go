// ACC34 paired full-process Go resource/quality meter, no model source imports.
package main
import("bytes";"encoding/json";"errors";"flag";"fmt";"math";"os";"os/exec";"runtime";"sort";"time";a "example.org/acc34delta")
var Seeds=[]int{91101,91103,91107,91109,91111}
var Scenarios=[]string{"benign","hidden_interaction"}
var Modes=[]string{"full","verified","unverified","oracle"}
type Sample struct{
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Seed int `json:"seed"`
 ChildCPUNanos int64 `json:"child_process_cpu_ns"`
 SpawnWallNanos int64 `json:"spawn_to_exit_wall_ns"`
 Worker a.Report `json:"worker"`
}
type Pair struct{
 Seed int `json:"seed"`
 FullCPU int64 `json:"full_child_cpu_ns"`
 VerifiedCPU int64 `json:"verified_child_cpu_ns"`
 RatioCPU float64 `json:"verified_over_full_cpu"`
 RatioSys float64 `json:"verified_over_full_go_runtime_sys"`
 VerifiedRepairs uint64 `json:"verified_repairs"`
 UnsafeUnverifiedDiverged bool `json:"unverified_diverged_from_full"`
 OracleMatches bool `json:"unavailable_oracle_matches_full"`
}
type Summary struct{
 Scenario string `json:"scenario"`
 Pairs []Pair `json:"pairs"`
 MedianCPU float64 `json:"median_verified_over_full_cpu"`
 MedianSys float64 `json:"median_verified_over_full_runtime_sys"`
 MaxVerifiedErrors uint64 `json:"max_verified_repairs"`
 VerifiedExact bool `json:"verified_output_exact"`
 HiddenFitMiss bool `json:"undercovered_fit_hidden_interaction_observed"`
 ResourceAcceptance bool `json:"sourcefree_resource_criteria_pass"`
}
type Evidence struct{
 Schema string `json:"schema"`
 WorkerSource string `json:"worker_source_class"`
 RunnerOS string `json:"runner_goos"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 NativeModelsChanged bool `json:"native_models_changed"`
 FullPortfolioIDs int `json:"registered_candidate_count"`
 Outcome string `json:"classification"`
 Samples []Sample `json:"all_measured_worker_samples"`
 ByScenario []Summary `json:"by_scenario"`
 OriginalSourceEpisodes int `json:"original_source_episodes"`
 ProcessCPUIncludesFIT bool `json:"process_cpu_includes_fit_and_verification"`
 MemoryNotOSRSS bool `json:"go_runtime_sys_is_not_os_peak_rss"`
}
func median(x []float64)float64{
 y:=append([]float64(nil),x...);sort.Float64s(y)
 if len(y)%2==1{return y[len(y)/2]}
 return(y[len(y)/2-1]+y[len(y)/2])/2
}
func child(worker,mode,scenario string,seed int)(Sample,error){
 cmd:=exec.Command(worker,"-mode",mode,"-scenario",scenario,"-seed",fmt.Sprint(seed),"-events",fmt.Sprint(a.Events))
 var output,stderr bytes.Buffer;cmd.Stdout=&output;cmd.Stderr=&stderr
 start:=time.Now();err:=cmd.Run();wall:=time.Since(start).Nanoseconds()
 if err!=nil{return Sample{},fmt.Errorf("ACC34_WORKER_FAILURE %s/%s/%d: %w %s",mode,scenario,seed,err,stderr.String())}
 cpu:=cmd.ProcessState.UserTime().Nanoseconds()+cmd.ProcessState.SystemTime().Nanoseconds()
 if cpu<=0||wall<=0{return Sample{},errors.New("ACC34_MISSING_CHILD_PROCESS_CPU_OR_WALL")}
 var r a.Report
 if e:=json.Unmarshal(output.Bytes(),&r);e!=nil{return Sample{},fmt.Errorf("ACC34_BAD_WORKER_RECEIPT:%w",e)}
 if r.Schema!="forge.acc34.acd1.native-go-lifecycle.v1"||r.Mode!=mode||r.Scenario!=scenario||
 r.Seed!=seed||r.Events!=a.Events||len(r.Checksum)!=16||
 r.RuntimeSysBytes==0||r.RuntimeTotalAllocBytes==0||r.SourceOwnedEpisodes!=0||
 r.NativeModelsChanged||r.ScientificFirstUse{return Sample{},errors.New("ACC34_MALFORMED_OR_FORGED_WORKER_RESULT")}
 return Sample{mode,scenario,seed,cpu,wall,r},nil
}
func measured(worker string)(Evidence,error){
 result:=Evidence{Schema:"forge.acc34.paired-acd1-sourcefree-native-go-development.v1",
 WorkerSource:"REAL_GO_1_25_PROCESS_FULL_LIFECYCLE",RunnerOS:runtime.GOOS,FullPortfolioIDs:36,
 ScientificFirstUse:false,NativeModelsChanged:false,OriginalSourceEpisodes:0,
 ProcessCPUIncludesFIT:true,MemoryNotOSRSS:true}
 for _,scenario:=range Scenarios{
  for _,mode:=range Modes{if _,e:=child(worker,mode,scenario,91101);e!=nil{return result,e}}
  rows:=[]Pair{}
  for i,seed:=range Seeds{
   observed:=map[string]Sample{}
   order:=[]string{"full","verified","unverified","oracle"}
   if i%2!=0{order=[]string{"verified","full","unverified","oracle"}}
   for _,mode:=range order{
    one,e:=child(worker,mode,scenario,seed);if e!=nil{return result,e}
    observed[mode]=one;result.Samples=append(result.Samples,one)
   }
   f,v,u,o:=observed["full"],observed["verified"],observed["unverified"],observed["oracle"]
   if v.Worker.Checksum!=f.Worker.Checksum||o.Worker.Checksum!=f.Worker.Checksum||
    v.Worker.VerificationEvaluations!=a.Events*a.Nodes||
    v.Worker.FitEvaluations!=a.Nodes*(a.Inputs+1)||
    f.Worker.FitEvaluations!=0||f.Worker.VerificationEvaluations!=0||
    v.Worker.ActionEvaluations>=f.Worker.ActionEvaluations||
    o.Worker.VerificationEvaluations!=0||u.Worker.FitEvaluations!=v.Worker.FitEvaluations{
    return result,fmt.Errorf("ACC34_INCOMPLETE_VERIFICATION_OR_OUTPUT_DISCREPANCY %s %d",scenario,seed)
   }
   unsafe:=u.Worker.Checksum!=f.Worker.Checksum
   if(scenario=="hidden_interaction"&&!unsafe)||
    (scenario=="benign"&&unsafe)||
    (scenario=="benign"&&v.Worker.VerificationRepairs!=0)||
    (scenario=="hidden_interaction"&&v.Worker.VerificationRepairs==0){
    return result,fmt.Errorf("ACC34_HIDDEN_INTERACTION_FALSIFIER_LOST %s %d",scenario,seed)
   }
   rows=append(rows,Pair{seed,f.ChildCPUNanos,v.ChildCPUNanos,
    float64(v.ChildCPUNanos)/float64(f.ChildCPUNanos),
    float64(v.Worker.RuntimeSysBytes)/float64(f.Worker.RuntimeSysBytes),
    v.Worker.VerificationRepairs,unsafe,true})
  }
  cr,sr:=[]float64{},[]float64{};var repairs uint64
  for _,p:=range rows{
   cr=append(cr,p.RatioCPU);sr=append(sr,p.RatioSys)
   if p.VerifiedRepairs>repairs{repairs=p.VerifiedRepairs}
  }
  c,s:=median(cr),median(sr)
  if math.IsNaN(c)||math.IsInf(c,0)||math.IsNaN(s)||math.IsInf(s,0){return result,errors.New("ACC34_INVALID_RESOURCE_RATIO")}
  result.ByScenario=append(result.ByScenario,Summary{scenario,rows,c,s,repairs,true,
   scenario=="hidden_interaction",c<=0.90&&s<=1.10})
 }
 if len(result.Samples)!=40||len(result.ByScenario)!=2{return result,errors.New("ACC34_INCOMPLETE_REPETITIONS")}
 if result.ByScenario[0].ResourceAcceptance&&result.ByScenario[1].ResourceAcceptance{
  result.Outcome="ACC34_ACD1_VERIFIED_TOTAL_NATIVE_GO_CPU_RESOURCE_POSITIVE__ENGINEERING_ONLY"
 }else{result.Outcome="ACC34_ACD1_NO_TOTAL_VERIFIED_NATIVE_GO_CPU_WIN__NO_SCIENCE"}
 return result,nil
}
func main(){
 worker:=flag.String("worker","","compiled Go worker binary");out:=flag.String("out","","report JSON");flag.Parse()
 if *worker==""||*out==""{fmt.Fprintln(os.Stderr,"ACC34_REQUIRED_WORKER_AND_OUT");os.Exit(2)}
 evidence,e:=measured(*worker);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
 raw,e:=json.MarshalIndent(evidence,"","  ");if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(4)}
 if e=os.WriteFile(*out,append(raw,'\n'),0644);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(5)}
 fmt.Println("ACC34_36_PORTFOLIO_IDS_PRESERVED=36")
 fmt.Println("ACC34_VERIFIED_GO_OUTPUT_PARITY=PASS")
 for _,s:=range evidence.ByScenario{
  fmt.Printf("ACC34_SCENARIO=%s MEDIAN_VERIFIED_TOTAL_CPU_RATIO=%.6f MEDIAN_GO_SYS_RATIO=%.6f VERIFIED_REPAIRS=%d RESOURCE_PASS=%t\n",
   s.Scenario,s.MedianCPU,s.MedianSys,s.MaxVerifiedErrors,s.ResourceAcceptance)
 }
 fmt.Println("ACC34_ENGINEERING_CLASSIFICATION="+evidence.Outcome)
 fmt.Println("ACC34_SCIENTIFIC_FIRST_USE=FALSE")
}
