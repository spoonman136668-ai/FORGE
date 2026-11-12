package main

// ACC35: standalone real Go reversible memory-fusion falsification.
// Source-free public synthetic histories, no LLM/native model or hidden reward oracle.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "strconv"
 "strings"
 "time"
)

const Schema="forge.acc35.acd3.native-go-memory-fusion.v1"
const Identities=256
const Rounds=16
const Events=Identities*Rounds
const Sessions=16
const Repetitions=5

var modes=[]string{"raw","dict","fusion","lossy"}
var scenarios=[]string{"nonconflicting","delayed_counterexample"}

type Event struct{
 ID uint16 `json:"id"`
 Round uint8 `json:"round"`
 Observation string `json:"observation"`
 Outcome uint8 `json:"outcome"`
}
func publicObservation(group int)string{
 return strings.Repeat(fmt.Sprintf("PUBLIC_FAMILY_%02d_",group),4)
}
func event(id,round int,scenario string)Event{
 group:=id%8
 val:=uint8((group+round/4)%2)
 // A delayed identity-only exception, deliberately invisible in the first 8 rounds.
 if scenario=="delayed_counterexample"&&round>=8&&id%17==15{val^=1}
 return Event{uint16(id),uint8(round),publicObservation(group),val}
}
func canonical(x any)[]byte{
 b,e:=json.Marshal(x);if e!=nil{panic(e)}
 return b
}
func digestEvents(events []Event)string{
 h:=sha256.New()
 for _,e:=range events{_,_=h.Write(canonical(e));_,_=h.Write([]byte{10})}
 return hex.EncodeToString(h.Sum(nil))
}
type Memory struct{
 Mode string `json:"mode"`
 Raw []Event `json:"raw,omitempty"`
 IDs []uint16 `json:"ids,omitempty"`
 Groups []uint8 `json:"groups,omitempty"`
 Outcomes []uint8 `json:"outcomes,omitempty"`
 Dictionary []string `json:"dictionary,omitempty"`
 Templates map[string]uint8 `json:"templates,omitempty"`
 Exceptions map[string]uint8 `json:"exceptions,omitempty"`
}
func New(mode string)(*Memory,error){
 found:=false;for _,v:=range modes{if v==mode{found=true}}
 if !found{return nil,errors.New("ACC35_UNREGISTERED_MEMORY_ARM")}
 return &Memory{Mode:mode,Templates:map[string]uint8{},Exceptions:map[string]uint8{}},nil
}
func (m *Memory) size()int{
 if m.Mode=="raw"{return len(m.Raw)}
 return len(m.IDs)
}
func (m *Memory) intern(observation string)(uint8,error){
 for index,s:=range m.Dictionary{if s==observation{return uint8(index),nil}}
 if len(m.Dictionary)>=8{return 0,errors.New("ACC35_PUBLIC_GROUP_BOUND")}
 m.Dictionary=append(m.Dictionary,observation)
 return uint8(len(m.Dictionary)-1),nil
}
func templateKey(round int,group uint8)string{return fmt.Sprintf("%02d:%02d",round,group)}
func overrideKey(index int)string{return strconv.Itoa(index)}
func (m *Memory) Push(v Event)error{
 index:=m.size()
 if index>=Events||int(v.ID)!=index%Identities||int(v.Round)!=index/Identities ||
   v.Outcome>1||len(v.Observation)==0||len(v.Observation)>128{
  return errors.New("ACC35_PUBLIC_EVENT_ID_ORDER_OR_TYPE_INVALID")
 }
 if m.Mode=="raw"{
  m.Raw=append(m.Raw,v);return nil
 }
 group,err:=m.intern(v.Observation);if err!=nil{return err}
 m.IDs=append(m.IDs,v.ID)
 m.Groups=append(m.Groups,group)
 if m.Mode=="dict"{
  m.Outcomes=append(m.Outcomes,v.Outcome)
 }else{
  key:=templateKey(int(v.Round),group)
  existing,ok:=m.Templates[key]
  if !ok{m.Templates[key]=v.Outcome
  }else if existing!=v.Outcome && m.Mode=="fusion"{
   m.Exceptions[overrideKey(index)]=v.Outcome
  }
 }
 return nil
}
func (m *Memory) Replay()([]Event,error){
 if m.Mode=="raw"{return append([]Event(nil),m.Raw...),nil}
 if len(m.IDs)!=len(m.Groups){return nil,errors.New("ACC35_IDENTITY_GROUP_DRIFT")}
 if m.Mode=="dict"&&len(m.Outcomes)!=len(m.IDs){
  return nil,errors.New("ACC35_DICTIONARY_OUTCOME_DRIFT")
 }
 events:=make([]Event,0,len(m.IDs))
 for i,id:=range m.IDs{
  group:=m.Groups[i]
  if int(group)>=len(m.Dictionary){return nil,errors.New("ACC35_MISSING_PUBLIC_FAMILY")}
  var outcome uint8
  if m.Mode=="dict"{outcome=m.Outcomes[i]
  }else{
   key:=templateKey(i/Identities,group)
   val,ok:=m.Templates[key]
   if !ok{return nil,errors.New("ACC35_TEMPLATE_MISSING")}
   outcome=val
   if exception,ok:=m.Exceptions[overrideKey(i)];ok{outcome=exception}
  }
  events=append(events,Event{ID:id,Round:uint8(i/Identities),
     Observation:m.Dictionary[group],Outcome:outcome})
 }
 return events,nil
}
type Envelope struct{
 State Memory `json:"state"`
 SHA string `json:"sha"`
}
func (m *Memory) Snapshot()[]byte{
 return canonical(Envelope{State:*m,SHA:hashBytes(canonical(m))})
}
func hashBytes(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func Restore(b []byte)(*Memory,error){
 if len(b)==0||len(b)>3000000{return nil,errors.New("ACC35_CHECKPOINT_TOO_LARGE")}
 var env Envelope
 if err:=json.Unmarshal(b,&env);err!=nil{return nil,errors.New("ACC35_CHECKPOINT_DECODE")}
 if hashBytes(canonical(env.State))!=env.SHA{
  return nil,errors.New("ACC35_CHECKPOINT_HASH_INVALID")
 }
 m:=env.State
 if m.size()>Events{return nil,errors.New("ACC35_CHECKPOINT_EVENT_LIMIT")}
 if _,err:=m.Replay();err!=nil{return nil,err}
 if string(m.Snapshot())!=string(b){
  return nil,errors.New("ACC35_CHECKPOINT_NONCANONICAL")
 }
 return &m,nil
}
type Worker struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Sessions int `json:"cold_sessions"`
 TotalEvents int `json:"event_insertions"`
 CheckedReplayExact bool `json:"replay_exact"`
 ColdRestoreExact bool `json:"cold_restore_exact"`
 WrongReplayedOutcomes int `json:"wrong_replayed_outcomes"`
 DelayedExceptionCount int `json:"delayed_exceptions_recorded"`
 SerializedCheckpointBytes int `json:"serialized_checkpoint_bytes"`
 RuntimeSysBytes uint64 `json:"go_runtime_sys_bytes"`
 AllocatedBytes uint64 `json:"go_total_alloc_bytes"`
 TraceSHA string `json:"trace_sha256"`
 OriginalSourceEpisodes int `json:"original_source_episodes"`
 ScientificFirstUse bool `json:"scientific_first_use"`
}
func valid(s string,allowed []string)bool{
 for _,x:=range allowed{if x==s{return true}}
 return false
}
func once(mode,scenario string)(exact,cold bool,wrong,exceptions,checkpointBytes int,trace string,err error){
 m,e:=New(mode);if e!=nil{return false,false,0,0,0,"",e}
 h:=sha256.New()
 for round:=0;round<Rounds;round++{
  for id:=0;id<Identities;id++{
   v:=event(id,round,scenario)
   _,_=h.Write(canonical(v));_,_=h.Write([]byte{10})
   if e=m.Push(v);e!=nil{return false,false,0,0,0,"",e}
  }
 }
 expected:=hex.EncodeToString(h.Sum(nil))
 current,e:=m.Replay();if e!=nil{return false,false,0,0,0,"",e}
 exact=digestEvents(current)==expected
 for i,v:=range current{
  if v.Outcome!=event(i%Identities,i/Identities,scenario).Outcome{wrong++}
 }
 snapshot:=m.Snapshot()
 checkpointBytes=len(snapshot)
 restored,e:=Restore(snapshot);if e!=nil{return false,false,0,0,0,"",e}
 replay,e:=restored.Replay();if e!=nil{return false,false,0,0,0,"",e}
 cold=digestEvents(replay)==expected&&string(restored.Snapshot())==string(snapshot)
 exceptions=len(m.Exceptions)
 return exact,cold,wrong,exceptions,checkpointBytes,expected,nil
}
func worker(mode,scenario string)(Worker,error){
 if !valid(mode,modes)||!valid(scenario,scenarios){
  return Worker{},errors.New("ACC35_UNFROZEN_WORKER_SCOPE")
 }
 w:=Worker{Schema:Schema,Mode:mode,Scenario:scenario,Sessions:Sessions,
  TotalEvents:Sessions*Events,CheckedReplayExact:true,ColdRestoreExact:true}
 for i:=0;i<Sessions;i++{
  exact,cold,wrong,exceptions,bytes,trace,err:=once(mode,scenario)
  if err!=nil{return Worker{},err}
  w.CheckedReplayExact=w.CheckedReplayExact&&exact
  w.ColdRestoreExact=w.ColdRestoreExact&&cold
  w.WrongReplayedOutcomes+=wrong
  w.DelayedExceptionCount+=exceptions
  w.SerializedCheckpointBytes=bytes
  if i==0{w.TraceSHA=trace
  }else if w.TraceSHA!=trace{return Worker{},errors.New("ACC35_COLD_SESSION_DRIFT")}
 }
 var mem runtime.MemStats
 runtime.ReadMemStats(&mem)
 w.RuntimeSysBytes=mem.Sys
 w.AllocatedBytes=mem.TotalAlloc
 return w,nil
}
type Trial struct {
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Rep int `json:"rep"`
 WholeChildCPUNs int64 `json:"whole_child_cpu_ns"`
 SpawnWallNs int64 `json:"spawn_wall_ns"`
 Worker Worker `json:"worker"`
}
func child(mode,scenario string,rep int)(Trial,error){
 t:=time.Now()
 command:=exec.Command(os.Args[0],"worker",mode,scenario)
 command.Env=append(os.Environ(),"GOMAXPROCS=1")
 b,e:=command.Output()
 if e!=nil{return Trial{},fmt.Errorf("ACC35_CHILD_%s_%s:%w",mode,scenario,e)}
 var w Worker
 if e=json.Unmarshal(b,&w);e!=nil{return Trial{},e}
 if w.Schema!=Schema||w.Mode!=mode||w.Scenario!=scenario||
   w.TotalEvents!=Sessions*Events||w.OriginalSourceEpisodes!=0||w.ScientificFirstUse{
  return Trial{},errors.New("ACC35_CHILD_SOURCE_EVIDENCE_DRIFT")
 }
 cpu:=command.ProcessState.UserTime()+command.ProcessState.SystemTime()
 if cpu<=0{return Trial{},errors.New("ACC35_ZERO_CHILD_CPU_METER")}
 return Trial{Mode:mode,Scenario:scenario,Rep:rep,
  WholeChildCPUNs:cpu.Nanoseconds(),SpawnWallNs:time.Since(t).Nanoseconds(),Worker:w},nil
}
func median(values []float64)float64{
 x:=append([]float64(nil),values...)
 sort.Float64s(x)
 if len(x)%2==1{return x[len(x)/2]}
 return (x[len(x)/2-1]+x[len(x)/2])/2
}
type Summary struct{
 Scenario string `json:"scenario"`
 FusionCPUOverDict float64 `json:"fusion_cpu_over_dict"`
 FusionBytesOverDict float64 `json:"fusion_checkpoint_bytes_over_dict"`
 FusionSysOverDict float64 `json:"fusion_go_sys_over_dict"`
 FusionExact bool `json:"fusion_exact"`
 DictionaryExact bool `json:"dictionary_exact"`
 LossyWrongOutcomes int `json:"lossy_wrong_outcomes"`
 EngineeringPass bool `json:"engineering_pass"`
}
type Report struct{
 Schema string `json:"schema"`
 Candidate string `json:"candidate"`
 GoOS string `json:"go_os"`
 Repetitions int `json:"repetitions"`
 ColdSessions int `json:"cold_sessions_per_worker"`
 EventsPerSession int `json:"events_per_session"`
 Classification string `json:"classification"`
 Summaries []Summary `json:"summaries"`
 Trials []Trial `json:"trials"`
 OriginalSourceEpisodes int `json:"original_source_episodes"`
 NativeModelAccelerationProven bool `json:"native_model_acceleration_proven"`
 ScientificFirstUse bool `json:"scientific_first_use"`
}
func benchmark()(Report,error){
 r:=Report{Schema:Schema,Candidate:"AC-D3",GoOS:runtime.GOOS,Repetitions:Repetitions,
   ColdSessions:Sessions,EventsPerSession:Events}
 success:=true
 for _,scenario:=range scenarios{
  for _,mode:=range modes{if _,e:=child(mode,scenario,-1);e!=nil{return Report{},e}}
  byMode:=map[string][]Trial{}
  for i:=0;i<Repetitions;i++{
   order:=[]string{"dict","fusion","raw","lossy"}
   if i%2==1{order=[]string{"fusion","dict","lossy","raw"}}
   for _,mode:=range order{
    trial,e:=child(mode,scenario,i);if e!=nil{return Report{},e}
    byMode[mode]=append(byMode[mode],trial)
    r.Trials=append(r.Trials,trial)
   }
  }
  for _,mode:=range modes{
   if len(byMode[mode])!=Repetitions{return Report{},errors.New("ACC35_MISSING_PAIRED_WORKERS")}
  }
  ref:=byMode["raw"][0].Worker.TraceSHA
  summary:=Summary{Scenario:scenario,FusionExact:true,DictionaryExact:true}
  cpuF,cpuD:=[]float64{},[]float64{}
  bytesF,bytesD:=[]float64{},[]float64{}
  sysF,sysD:=[]float64{},[]float64{}
  for i:=0;i<Repetitions;i++{
   f:=byMode["fusion"][i];d:=byMode["dict"][i];lost:=byMode["lossy"][i];raw:=byMode["raw"][i]
   for _,w:=range []Worker{f.Worker,d.Worker,lost.Worker,raw.Worker}{
    if w.TraceSHA!=ref{return Report{},errors.New("ACC35_SOURCE_SCHEDULE_NOT_MATCHED")}
   }
   summary.FusionExact=summary.FusionExact&&f.Worker.CheckedReplayExact&&f.Worker.ColdRestoreExact
   summary.DictionaryExact=summary.DictionaryExact&&d.Worker.CheckedReplayExact&&d.Worker.ColdRestoreExact&&raw.Worker.ColdRestoreExact
   summary.LossyWrongOutcomes+=lost.Worker.WrongReplayedOutcomes
   cpuF=append(cpuF,float64(f.WholeChildCPUNs));cpuD=append(cpuD,float64(d.WholeChildCPUNs))
   bytesF=append(bytesF,float64(f.Worker.SerializedCheckpointBytes))
   bytesD=append(bytesD,float64(d.Worker.SerializedCheckpointBytes))
   sysF=append(sysF,float64(f.Worker.RuntimeSysBytes))
   sysD=append(sysD,float64(d.Worker.RuntimeSysBytes))
  }
  summary.FusionCPUOverDict=median(cpuF)/median(cpuD)
  summary.FusionBytesOverDict=median(bytesF)/median(bytesD)
  summary.FusionSysOverDict=median(sysF)/median(sysD)
  if !summary.FusionExact||!summary.DictionaryExact{
   return Report{},errors.New("ACC35_REVERSIBLE_SOURCE_REPLAY_NOT_EXACT")
  }
  if scenario=="delayed_counterexample"&&summary.LossyWrongOutcomes==0{
   return Report{},errors.New("ACC35_LOSSY_DELAYED_COUNTEREXAMPLE_MISSING")
  }
  summary.EngineeringPass=summary.FusionCPUOverDict<=0.90&&
     summary.FusionBytesOverDict<=0.90&&summary.FusionSysOverDict<=1.10
  success=success&&summary.EngineeringPass
  r.Summaries=append(r.Summaries,summary)
 }
 r.Classification="ACC35_ACD3_NO_AMORTIZED_NATIVE_GO_WIN"
 if success{r.Classification="ACC35_ACD3_BOUNDED_GO_MEMORY_ENGINEERING_POSITIVE_NO_SCIENCE"}
 return r,nil
}
func main(){
 if len(os.Args)>=2&&os.Args[1]=="worker"{
  if len(os.Args)!=4{os.Exit(2)}
  w,e:=worker(os.Args[2],os.Args[3]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  _=json.NewEncoder(os.Stdout).Encode(w);return
 }
 if len(os.Args)!=2||os.Args[1]!="benchmark"{fmt.Fprintln(os.Stderr,"ACC35_USAGE");os.Exit(2)}
 r,e:=benchmark();if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 _=json.NewEncoder(os.Stdout).Encode(r)
}
