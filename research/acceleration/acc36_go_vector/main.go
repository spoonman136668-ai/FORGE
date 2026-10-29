// ACC-36: genuine compiled native-Go source-free U07/U18 bipolar vector
// memory interference falsification; no real LLM or native model integration.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "strconv"
 "time"
)

const (
 VectorDims=512
 Labels=16
 KnownQueries=256
 UnknownQueries=64
 ColdSessions=32
 Repetitions=5
)
const (
 exact="DICT"
 bundled="BUNDLE"
 membership="BUNDLE_MEMBERSHIP"
 shuffled="SHUFFLED"
 Schema="forge.acc36.u07u18.bipolar-memory-go.v1"
)
var Sizes=[]int{16,64,256,512}
var Seeds=[]int{11,29,47}
var Modes=[]string{exact,bundled,membership,shuffled}

func splitmix(x uint64)uint64{
 x+=0x9e3779b97f4a7c15
 x=(x^(x>>30))*0xbf58476d1ce4e5b9
 x=(x^(x>>27))*0x94d049bb133111eb
 return x^(x>>31)
}
func keyFor(seed,i int)uint32{return uint32(100000+seed*1000+i*37)}
func absentKeyFor(seed,i int)uint32{return uint32(900000+seed*1000+i*43)}
func valueFor(seed,i int)uint8{
 return uint8(splitmix(uint64(seed)*0x243f6a8885a308d3+uint64(i)*0x9e3779b97f4a7c15)%Labels)
}
func signKey(key uint32,d int)int32{
 if splitmix((uint64(key)<<32)^uint64(d+1)*0xc2b2ae3d27d4eb4f)&1==0{return 1}
 return -1
}
func signValue(label int,d int)int32{
 if splitmix(uint64(label+1)*0x165667b19e3779f9^uint64(d+1)*0xd6e8feb86659fd93)&1==0{return 1}
 return -1
}
type State struct{
 Mode string
 Seed int
 Items int
 Vector []int32
 Keys []uint32
 Exact map[uint32]uint8
}
type Envelope struct{
 State State
 SHA256 string
}
func marshalCanonical(obj any)([]byte,error){return json.Marshal(obj)}
func digest(data []byte)string{v:=sha256.Sum256(data);return hex.EncodeToString(v[:])}
func snapshot(s State)([]byte,error){
 stateBytes,err:=marshalCanonical(s);if err!=nil{return nil,err}
 return marshalCanonical(Envelope{State:s,SHA256:digest(stateBytes)})
}
func restore(raw []byte)(State,error){
 if len(raw)==0||len(raw)>250000{return State{},errors.New("ACC36_BAD_SNAPSHOT_BYTES")}
 var e Envelope
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&e);err!=nil{return State{},errors.New("ACC36_BAD_SNAPSHOT_FORMAT")}
 var extra any
 if err:=decoder.Decode(&extra);err==nil{return State{},errors.New("ACC36_SNAPSHOT_EXTRA_JSON")}
 stateBytes,err:=marshalCanonical(e.State)
 if err!=nil||digest(stateBytes)!=e.SHA256{return State{},errors.New("ACC36_SNAPSHOT_DIGEST_MISMATCH")}
 s:=e.State
 if s.Items!=16&&s.Items!=64&&s.Items!=256&&s.Items!=512{return State{},errors.New("ACC36_BAD_FROZEN_KEY_COUNT")}
 if s.Seed!=11&&s.Seed!=29&&s.Seed!=47{return State{},errors.New("ACC36_BAD_FROZEN_SEED")}
 switch s.Mode {
 case exact:
  if len(s.Exact)!=s.Items||len(s.Vector)!=0||len(s.Keys)!=0{return State{},errors.New("ACC36_EXACT_REPRESENTATION_MISMATCH")}
 case bundled,shuffled:
  if len(s.Vector)!=VectorDims||len(s.Exact)>0||len(s.Keys)>0{return State{},errors.New("ACC36_BUNDLE_REPRESENTATION_MISMATCH")}
 case membership:
  if len(s.Vector)!=VectorDims||len(s.Exact)>0||len(s.Keys)!=s.Items{return State{},errors.New("ACC36_MEMBERSHIP_REPRESENTATION_MISMATCH")}
  for i,k:=range s.Keys{
   if k!=keyFor(s.Seed,i) {return State{},errors.New("ACC36_MEMBERSHIP_PRIVATE_LABEL_OR_KEY_DRIFT")}
  }
 default:return State{},errors.New("ACC36_UNREGISTERED_MODE")
 }
 repacked,err:=snapshot(s)
 if err!=nil||!bytes.Equal(raw,repacked){return State{},errors.New("ACC36_NONCANONICAL_SNAPSHOT")}
 return s,nil
}
func train(mode string,seed,count int)(State,error){
 if (seed!=11&&seed!=29&&seed!=47)||(count!=16&&count!=64&&count!=256&&count!=512){
  return State{},errors.New("ACC36_NOT_FROZEN_FIT")
 }
 s:=State{Mode:mode,Seed:seed,Items:count}
 if mode==exact {s.Exact=make(map[uint32]uint8,count)}
 if mode!=exact {s.Vector=make([]int32,VectorDims)}
 if mode==membership {s.Keys=make([]uint32,0,count)}
 if mode!=exact&&mode!=bundled&&mode!=membership&&mode!=shuffled{
  return State{},errors.New("ACC36_UNREGISTERED_MODE")
 }
 for i:=0;i<count;i++ {
  key:=keyFor(seed,i)
  value:=valueFor(seed,i)
  if mode==shuffled {value=valueFor(seed,(i+1)%count)} // deliberate falsifier, not a model label
  if mode==exact {
   s.Exact[key]=value
  }else{
   if mode==membership{s.Keys=append(s.Keys,key)}
   for d:=0;d<VectorDims;d++{s.Vector[d]+=signKey(key,d)*signValue(int(value),d)}
  }
 }
 return s,nil
}
func lookup(s State,key uint32)int{
 if s.Mode==exact {
  v,ok:=s.Exact[key];if !ok{return -1};return int(v)
 }
 if s.Mode==membership {
  i:=sort.Search(len(s.Keys),func(i int)bool{return s.Keys[i]>=key})
  if i==len(s.Keys)||s.Keys[i]!=key{return -1}
 }
 var scores [Labels]int64
 for d,weight:=range s.Vector {
  x:=int64(weight*signKey(key,d))
  for lab:=0;lab<Labels;lab++ {scores[lab]+=x*int64(signValue(lab,d))}
 }
 best:=0
 for l:=1;l<Labels;l++{if scores[l]>scores[best]{best=l}}
 return best
}
type Worker struct{
 Schema string
 Mode string
 Seed int
 Items int
 Sessions int
 TrainExamples int
 KnownQuestions int
 KnownCorrect int
 KnownWrong int
 UnknownQuestions int
 UnknownAbstentions int
 UnknownFalsePositives int
 ColdCheckpointsExact bool
 CheckpointBytes int
 CheckpointSHA256 string
 SourceQuestionSHA256 string
 PredictionsSHA256 string
 GoRuntimeSysBytes uint64
 GoTotalAllocBytes uint64
 OriginalSourceEpisodes int
 NativeModelIntegration bool
 ScientificFirstUse bool
}
func work(mode string,seed,count int)(Worker,error){
 out:=Worker{Schema:Schema,Mode:mode,Seed:seed,Items:count,Sessions:ColdSessions,ColdCheckpointsExact:true}
 queryHash:=sha256.New()
 predHash:=sha256.New()
 var payload [12]byte
 var canonicalSnapshot []byte
 for session:=0;session<ColdSessions;session++ {
  fit,err:=train(mode,seed,count);if err!=nil{return out,err}
  cold,err:=snapshot(fit);if err!=nil{return out,err}
  restored,err:=restore(cold);if err!=nil{return out,err}
  if session==0{canonicalSnapshot=cold}
  if !bytes.Equal(cold,canonicalSnapshot){return out,errors.New("ACC36_SNAPSHOT_NONDETERMINISTIC")}
  out.TrainExamples+=count
  for query:=0;query<KnownQueries+UnknownQueries;query++{
   key:=uint32(0);truth:=-1
   if query<KnownQueries{
    i:=(query*37+seed*11)%count
    key=keyFor(seed,i)
    truth=int(valueFor(seed,i))
   }else{key=absentKeyFor(seed,query-KnownQueries)}
   // Question truth lives exclusively in the scoring harness. The trained
   // candidate receives only key and its own serialized source-free state.
   actual:=lookup(restored,key)
   if actual< -1||actual>=Labels{return out,errors.New("ACC36_INVALID_MEMORY_ANSWER")}
   binary.LittleEndian.PutUint32(payload[0:4],key)
   binary.LittleEndian.PutUint32(payload[4:8],uint32(truth+1))
   _,_=queryHash.Write(payload[:8])
   binary.LittleEndian.PutUint32(payload[8:12],uint32(actual+1))
   _,_=predHash.Write(payload[:12])
   if truth>=0{
    out.KnownQuestions++
    if actual==truth{out.KnownCorrect++}else{out.KnownWrong++}
   }else{
    out.UnknownQuestions++
    if actual==-1{out.UnknownAbstentions++}else{out.UnknownFalsePositives++}
   }
  }
 }
 out.CheckpointBytes=len(canonicalSnapshot)
 out.CheckpointSHA256=digest(canonicalSnapshot)
 out.SourceQuestionSHA256=hex.EncodeToString(queryHash.Sum(nil))
 out.PredictionsSHA256=hex.EncodeToString(predHash.Sum(nil))
 var mem runtime.MemStats
 runtime.ReadMemStats(&mem)
 out.GoRuntimeSysBytes=mem.Sys
 out.GoTotalAllocBytes=mem.TotalAlloc
 return out,nil
}
type Trial struct{
 Mode string
 Seed int
 Items int
 Repetition int
 ProcessCPUNanoseconds int64
 ParentWallNanoseconds int64
 Worker Worker
}
func runChild(executable,mode string,seed,count,rep int)(Trial,error){
 started:=time.Now()
 cmd:=exec.Command(executable,"worker",mode,strconv.Itoa(seed),strconv.Itoa(count))
 cmd.Env=append(os.Environ(),"GOMAXPROCS=1")
 stdout,err:=cmd.Output()
 wall:=time.Since(started)
 if err!=nil{return Trial{},fmt.Errorf("ACC36_CHILD_%s_%d_%d_FAILED:%w",mode,seed,count,err)}
 if cmd.ProcessState==nil{return Trial{},errors.New("ACC36_CHILD_CPU_UNAVAILABLE")}
 cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Nanoseconds()
 if cpu<=0{return Trial{},errors.New("ACC36_CHILD_CPU_UNAVAILABLE")}
 var w Worker
 if err=json.Unmarshal(stdout,&w);err!=nil{return Trial{},err}
 if w.Schema!=Schema||w.Mode!=mode||w.Seed!=seed||w.Items!=count||w.Sessions!=ColdSessions||
    !w.ColdCheckpointsExact||w.KnownQuestions!=ColdSessions*KnownQueries||
    w.UnknownQuestions!=ColdSessions*UnknownQueries||w.TrainExamples!=ColdSessions*count||
    w.CheckpointBytes<=0||w.OriginalSourceEpisodes!=0||w.ScientificFirstUse||w.NativeModelIntegration{
  return Trial{},errors.New("ACC36_INCOMPLETE_WORKER_RECEIPT")
 }
 return Trial{mode,seed,count,rep,cpu,wall.Nanoseconds(),w},nil
}
func median(x []float64)float64{
 y:=append([]float64(nil),x...);sort.Float64s(y)
 return y[len(y)/2]
}
func ratios(allTrials []Trial,seed,count int)(map[string]any,error){
 arms:=map[string][]Trial{}
 for _,v:=range allTrials{if v.Seed==seed&&v.Items==count{arms[v.Mode]=append(arms[v.Mode],v)}}
 for _,name:=range Modes{if len(arms[name])!=Repetitions{return nil,errors.New("ACC36_MISSING_PAIRED_SOURCEFREE_ARM")}}
 baseline:=arms[exact][0].Worker
 for _,name:=range Modes {
  for _,trial:=range arms[name]{
   w:=trial.Worker
   if w.SourceQuestionSHA256!=baseline.SourceQuestionSHA256||w.KnownCorrect+w.KnownWrong!=w.KnownQuestions||
      w.UnknownAbstentions+w.UnknownFalsePositives!=w.UnknownQuestions{
    return nil,errors.New("ACC36_QUERY_INFORMATION_OR_OUTPUT_ACCOUNTING_DRIFT")
   }
   if name==exact&&(w.KnownWrong>0||w.UnknownFalsePositives>0||w.KnownCorrect!=w.KnownQuestions){
    return nil,errors.New("ACC36_STRONG_DICTIONARY_CONTROL_INVALID")
   }
  }
 }
 cpuMed:=func(mode string)float64{
  vals:=make([]float64,Repetitions);for i,v:=range arms[mode]{vals[i]=float64(v.ProcessCPUNanoseconds)}
  return median(vals)
 }
 sysMed:=func(mode string)float64{
  vals:=make([]float64,Repetitions);for i,v:=range arms[mode]{vals[i]=float64(v.Worker.GoRuntimeSysBytes)}
  return median(vals)
 }
 cpuRatio:=cpuMed(membership)/cpuMed(exact)
 sysRatio:=sysMed(membership)/sysMed(exact)
 bytesRatio:=float64(arms[membership][0].Worker.CheckpointBytes)/float64(baseline.CheckpointBytes)
 safe:=true
 for _,v:=range arms[membership]{
  if v.Worker.KnownWrong!=0||v.Worker.UnknownFalsePositives!=0{safe=false}
 }
 neg:=arms[shuffled][0].Worker.KnownWrong>0
 if !neg{return nil,errors.New("ACC36_SHUFFLED_SOURCE_NEGATIVE_NOT_OBSERVED")}
 return map[string]any{
   "seed":seed,"items":count,
   "bundle_known_correct":arms[bundled][0].Worker.KnownCorrect,
   "bundle_known_wrong":arms[bundled][0].Worker.KnownWrong,
   "bundle_unknown_false_positives":arms[bundled][0].Worker.UnknownFalsePositives,
   "membership_known_correct":arms[membership][0].Worker.KnownCorrect,
   "membership_known_wrong":arms[membership][0].Worker.KnownWrong,
   "membership_unknown_abstentions":arms[membership][0].Worker.UnknownAbstentions,
   "shuffled_known_wrong":arms[shuffled][0].Worker.KnownWrong,
   "dictionary_checkpoint_bytes":baseline.CheckpointBytes,
   "membership_checkpoint_bytes":arms[membership][0].Worker.CheckpointBytes,
   "bundle_checkpoint_bytes":arms[bundled][0].Worker.CheckpointBytes,
   "membership_cpu_over_dictionary":cpuRatio,
   "membership_runtime_sys_over_dictionary":sysRatio,
   "membership_checkpoint_bytes_over_dictionary":bytesRatio,
   "full_utility_retained":safe,
   "engineering_acceptance":safe&&cpuRatio<=0.90&&bytesRatio<=0.90&&sysRatio<=1.10,
 },nil
}
func benchmark()(map[string]any,error){
 executable,err:=os.Executable();if err!=nil{return nil,err}
 all:=make([]Trial,0,4*3*4*Repetitions)
 reports:=make([]map[string]any,0,12)
 for _,count:=range Sizes{
  for _,seed:=range Seeds{
   for rep:=0;rep<Repetitions;rep++{
    sequence:=append([]string(nil),Modes...)
    if rep%2==1{sequence=[]string{membership,exact,shuffled,bundled}}
    for _,mode:=range sequence {
     trial,err:=runChild(executable,mode,seed,count,rep);if err!=nil{return nil,err}
     all=append(all,trial)
    }
   }
   v,err:=ratios(all,seed,count);if err!=nil{return nil,err}
   reports=append(reports,v)
  }
 }
 pass:=true
 for _,v:=range reports{if v["engineering_acceptance"]!=true{pass=false}}
 classification:="ACC36_U07_U18_NO_EXACT_NATIVE_GO_MEMORY_RESOURCE_WIN__NO_SCIENCE"
 if pass{classification="ACC36_U07_U18_BOUNDED_GO_RESOURCE_POSITIVE__NO_SCIENCE"}
 return map[string]any{
 "schema":Schema,"portfolio_original_claims":30,"portfolio_additional_mechanisms":6,
 "tested_original_candidates":[]string{"U07","U18"},
 "not_fully_tested_candidates":[]string{"U08","U10","U22","U24"},
 "platform":runtime.GOOS,"go_version":runtime.Version(),
 "classification":classification,"repetitions_per_cohort_arm":Repetitions,
 "cold_sessions_per_child":ColdSessions,
 "native_llm_model_accelerated":false,"scientific_first_use":false,
 "independent_learning_success":false,"original_source_episodes":0,
 "cohorts":reports,"trials":all,
 },nil
}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"ACC36_SUBCOMMAND_REQUIRED");os.Exit(2)}
 var result any
 var err error
 switch os.Args[1]{
 case "worker":
  if len(os.Args)!=5{err=errors.New("ACC36_WORKER_NEEDS_MODE_SEED_ITEMS")}else{
   seed,e:=strconv.Atoi(os.Args[3]);count,e2:=strconv.Atoi(os.Args[4])
   if e!=nil{err=e}else if e2!=nil{err=e2}else{result,err=work(os.Args[2],seed,count)}
  }
 case "benchmark":
  if len(os.Args)!=2{err=errors.New("ACC36_FIXED_BENCHMARK_NO_OVERRIDE")}else{result,err=benchmark()}
 default:err=errors.New("ACC36_UNREGISTERED_COMMAND")
 }
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetEscapeHTML(false)
 if err=encoder.Encode(result);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
