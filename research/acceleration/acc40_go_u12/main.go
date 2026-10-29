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
	"path/filepath"
	"runtime"
	"sort"
	"time"
)
type record struct {
	Worker workerResult `json:"worker"`
	CPUSeconds float64 `json:"cpu_seconds"`
	WallSeconds float64 `json:"wall_seconds"`
	ExitCode int `json:"exit_code"`
	Trial int `json:"trial"`
	PairOrder string `json:"pair_order"`
}
type cell struct {
	FileBytes int64 `json:"file_bytes"`
	Schedule string `json:"schedule"`
	SourceSHA256 string `json:"source_sha256"`
	TraceEqual bool `json:"trace_equal"`
	SelectedControl string `json:"selected_control"`
	WallRatio float64 `json:"wall_ratio"`
	CPURatio float64 `json:"cpu_ratio"`
	RSSRatio float64 `json:"rss_ratio"`
	PredictiveRSSBytes float64 `json:"predictive_median_rss_bytes"`
	Pass bool `json:"pass"`
}
type report struct {
	Schema string `json:"schema"`
	OS string `json:"os"`
	GoVersion string `json:"go_version"`
	Environment string `json:"environment"`
	PortfolioOriginalCount int `json:"portfolio_original_count"`
	PortfolioAdditionalCount int `json:"portfolio_additional_count"`
	ScientificFirstUse bool `json:"scientific_first_use"`
	NativeModelAccelerationProven bool `json:"native_model_acceleration_proven"`
	DatasetSetupSeconds float64 `json:"dataset_setup_seconds"`
	Records []record `json:"records"`
	Comparisons []cell `json:"comparisons"`
	Classification string `json:"classification"`
	CacheAttribution string `json:"cache_attribution"`
}
func median(v []float64)float64{
	x:=append([]float64(nil),v...);sort.Float64s(x)
	if len(x)==0{return math.NaN()}
	if len(x)%2==1{return x[len(x)/2]}
	return (x[len(x)/2-1]+x[len(x)/2])/2
}
func performChild(exe,file,mode,schedule string,seed uint64,trial int,order string)(record,error){
	cmd:=exec.Command(exe,"-worker","-file",file,"-mode",mode,"-schedule",schedule,"-seed",fmt.Sprint(seed))
	var stdout,stderr bytes.Buffer
	cmd.Stdout=&stdout;cmd.Stderr=&stderr
	start:=time.Now()
	err:=cmd.Run()
	elapsed:=time.Since(start).Seconds()
	if err!=nil{return record{},fmt.Errorf("%s %s %d: %w: %s",mode,schedule,seed,err,stderr.String())}
	if cmd.ProcessState==nil{return record{},errors.New("missing process state")}
	cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds()
	if cpu<=0 || elapsed<=0{return record{},fmt.Errorf("missing/zero child CPU or wall: %s %.7f %.7f",mode,cpu,elapsed)}
	var w workerResult
	if err=json.Unmarshal(stdout.Bytes(),&w);err!=nil{return record{},fmt.Errorf("malformed worker: %w: %s",err,stdout.String())}
	if w.Schema!=schema || w.Mode!=mode || w.Schedule!=schedule || w.Seed!=seed || w.PeakRSSBytes==0 ||
		w.TraceDigest=="" || w.ArithmeticChecksum=="" || w.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES" {
		return record{},errors.New("invalid worker result / missing RSS")
	}
	return record{Worker:w,CPUSeconds:cpu,WallSeconds:elapsed,ExitCode:0,Trial:trial,PairOrder:order},nil
}
func cellFor(records []record,size int64,schedule,sha string)(cell,error){
	c:=cell{FileBytes:size,Schedule:schedule,SourceSHA256:sha,TraceEqual:true}
	groups:=map[string][]record{}
	expected:=map[uint64]workerResult{}
	for _,r:=range records {
		w:=r.Worker
		if w.SourceBytes!=size || w.Schedule!=schedule {continue}
		groups[w.Mode]=append(groups[w.Mode],r)
		if w.RequestedBytes!=2*size || w.UserReadBytes<0 || w.PrefetchedBytes<0 || w.WastedPrefetchBytes<0{return c,errors.New("truncated/invalid read accounting")}
		if prior,ok:=expected[w.Seed];ok {
			if prior.TraceDigest!=w.TraceDigest || prior.ArithmeticChecksum!=w.ArithmeticChecksum {c.TraceEqual=false}
		}else{expected[w.Seed]=w}
	}
	for _,mode:=range modes{
		if len(groups[mode])!=len(trialSeeds){return c,fmt.Errorf("incomplete mode %s, %d trials",mode,len(groups[mode]))}
	}
	if !c.TraceEqual || len(expected)!=len(trialSeeds){return c,errors.New("incomplete or incorrect parity")}
	metrics:=func(mode string)(float64,float64,float64){
		var walls,cpus,rsses []float64
		for _,r:=range groups[mode]{walls=append(walls,r.WallSeconds);cpus=append(cpus,r.CPUSeconds);rsses=append(rsses,float64(r.Worker.PeakRSSBytes))}
		return median(walls),median(cpus),median(rsses)
	}
	best:=math.Inf(1)
	for _,ctrl:=range []string{"SYNC","MMAP","STATIC"}{
		w,_,_:=metrics(ctrl)
		if w<best{best=w;c.SelectedControl=ctrl}
	}
	cw,cc,cr:=metrics(c.SelectedControl)
	pw,pc,pr:=metrics("PREDICTIVE")
	if cw<=0 || cc<=0 || cr<=0{return c,errors.New("invalid control medians")}
	c.WallRatio=pw/cw;c.CPURatio=pc/cc;c.RSSRatio=pr/cr;c.PredictiveRSSBytes=pr
	// Performance classification comes from frozen protocol, not CI success.
	if size==192*1024*1024 && schedule!="SHUFFLED" {
		c.Pass=c.WallRatio<=0.90 && c.CPURatio<=1.05 && c.PredictiveRSSBytes<=rssBudget && c.RSSRatio<=1.10
	}else{
		c.Pass=c.WallRatio<=1.10 && c.CPURatio<=1.10 && c.RSSRatio<=1.10
	}
	return c,nil
}
func drive(output string)error{
	start:=time.Now()
	dir,err:=os.MkdirTemp("","acc40-u12-data-*");if err!=nil{return err}
	defer os.RemoveAll(dir)
	exe,err:=os.Executable();if err!=nil{return err}
	// The source setup phase is measured separately and never attributed to a candidate speedup.
	rep:=report{Schema:schema,OS:runtime.GOOS,GoVersion:runtime.Version(),Environment:os.Getenv("RUNNER_NAME"),
		PortfolioOriginalCount:30,PortfolioAdditionalCount:6,Records:make([]record,0,150),
		ScientificFirstUse:false,NativeModelAccelerationProven:false,
		CacheAttribution:"FIRST_TOUCH_WITH_UNKNOWN_OS_CACHE / WARM_OR_UNCONTROLLED_CACHE; NO_PHYSICAL_COLD_DISK_CLAIM"}
	for _,size:=range []int64{24*1024*1024,192*1024*1024}{
		file:=filepath.Join(dir,fmt.Sprintf("source-%d.bin",size))
		for _,scenario:=range schedules{
			var sha string
			for trial,seed:=range trialSeeds{
				// Restage before every matched trial block; record setup independently.
				setupStart:=time.Now()
				newSHA,e:=makeSource(file,size);if e!=nil{return e}
				rep.DatasetSetupSeconds+=time.Since(setupStart).Seconds()
				if sha!="" && sha!=newSHA{return errors.New("source identity changed across paired trials")}
				sha=newSHA
				// AB/BA: candidate last on even trials, first on odd trials.
				order:=[]string{"RESIDENT","SYNC","MMAP","STATIC","PREDICTIVE"}
				ab:="AB"
				if trial%2==1{order=[]string{"RESIDENT","PREDICTIVE","STATIC","MMAP","SYNC"};ab="BA"}
				for _,mode:=range order{
					rec,e:=performChild(exe,file,mode,scenario,seed,trial,ab)
					if e!=nil{return e}
					rep.Records=append(rep.Records,rec)
				}
			}
			c,e:=cellFor(rep.Records,size,scenario,sha);if e!=nil{return e}
			rep.Comparisons=append(rep.Comparisons,c)
		}
	}
	elapsed:=time.Since(start).Seconds()
	rep.Classification="U12_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN"
	allPass:=len(rep.Comparisons)==6
	for _,c:=range rep.Comparisons{allPass=allPass&&c.Pass&&c.TraceEqual}
	if allPass{rep.Classification="U12_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY"}
	payload,e:=json.MarshalIndent(rep,"","  ");if e!=nil{return e}
	if err=os.WriteFile(output,append(payload,'\n'),0644);err!=nil{return err}
	fmt.Printf("%s; OS=%s; workers=%d; wall=%.3fs\n",rep.Classification,rep.OS,len(rep.Records),elapsed)
	return nil
}
func main(){
	child:=flag.Bool("worker",false,"run one original source-free Go worker")
	file:=flag.String("file","","original staged file")
	mode:=flag.String("mode","SYNC","one of five predeclared arms")
	schedule:=flag.String("schedule","SEQUENTIAL","one of three frozen workloads")
	seed:=flag.Uint64("seed",49101,"preregistered trial seed")
	out:=flag.String("out","acc40-report.json","driver report path")
	flag.Parse()
	var err error
	if *child{
		var w workerResult
		w,err=work(*file,*mode,*schedule,*seed)
		if err==nil{err=json.NewEncoder(os.Stdout).Encode(w)}
	}else{err=drive(*out)}
	if err!=nil{fmt.Fprintln(os.Stderr,"ACC40_U12_BLOCKED:",err);os.Exit(1)}
}
