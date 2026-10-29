package main

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "hash"
 "math"
)
const (
 schema="forge.acc41.original-u08-native-go-fixed-reservoir.v1"
 seriesLength=4096
 memoryLength=12
 sessions=32
 epochs=25
 rate=0.02
)
var trialSeeds=[]uint64{73101,73103,73107,73109,73111}
var modes=[]string{"BIAS","LAG12","LINEAR12","RESERVOIR12"}
var scenarios=[]string{"PREVIOUS_BIT","DELAY_3","XOR_1_3"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func stream(seed uint64,sess int,isEval bool)[]byte{
 key:=uint64(0x1133557799bbddff);if isEval{key=0xddee997755331100}
 x:=mix(seed^key^uint64(sess)*0x9e3779b97f4a7c15)
 out:=make([]byte,seriesLength);for i:=range out{x=mix(x);out[i]=byte(x>>63)}
 return out
}
func label(bits []byte,t int,scenario string)(float64,error){
 if t<memoryLength{return 0,errors.New("target before scored history")}
 switch scenario {
 case "PREVIOUS_BIT":return float64(bits[t-1]),nil
 case "DELAY_3":return float64(bits[t-3]),nil
 case "XOR_1_3":return float64(bits[t-1]^bits[t-3]),nil
 default:return 0,fmt.Errorf("unknown scenario %q",scenario)
 }
}
func uniform(x uint64)float64{return (float64(x>>11)*(1.0/9007199254740992.0))*0.8-0.4}
type model struct{mode string;input [memoryLength]float64;state [memoryLength]float64;coef [memoryLength+1]float64}
func newModel(mode string,seed uint64)(*model,error){
 m:=&model{mode:mode}
 switch mode{case "BIAS","LAG12","LINEAR12","RESERVOIR12":default:return nil,fmt.Errorf("unknown mode %q",mode)}
 for i:=range m.input{m.input[i]=uniform(mix(seed^uint64(i)*0x4af8ddc3d25ea713))}
 return m,nil
}
func(m *model)observe(bit byte){
 if m.mode=="BIAS"{return}
 if m.mode=="LAG12"{for i:=memoryLength-1;i>0;i--{m.state[i]=m.state[i-1]};m.state[0]=float64(bit);return}
 prev:=m.state;x:=float64(bit)*2-1
 for i:=range m.state{
  v:=m.input[i]*x+0.25*prev[i]+0.20*prev[(i+memoryLength-1)%memoryLength]
  if m.mode=="RESERVOIR12"{v=math.Tanh(v)}
  m.state[i]=v
 }
}
type sample struct{x [memoryLength+1]float64;y float64}
func samples(bits []byte,mode,scenario string,seed uint64)([]sample,error){
 if len(bits)!=seriesLength{return nil,errors.New("incomplete source")}
 m,err:=newModel(mode,seed);if err!=nil{return nil,err}
 out:=make([]sample,0,len(bits)-memoryLength)
 for t,bit:=range bits{
  if bit>1{return nil,errors.New("corrupt bit input")}
  if t>=memoryLength{
   y,err:=label(bits,t,scenario);if err!=nil{return nil,err}
   r:=sample{y:y};copy(r.x[:memoryLength],m.state[:]);r.x[memoryLength]=1;out=append(out,r)
  }
  m.observe(bit)
 }
 return out,nil
}
func fitted(train []sample,mode string)([memoryLength+1]float64,error){
 var coef [memoryLength+1]float64
 if len(train)!=seriesLength-memoryLength{return coef,errors.New("incorrect train length")}
 if mode=="BIAS"{for _,r:=range train{coef[memoryLength]+=r.y};coef[memoryLength]/=float64(len(train));return coef,nil}
 for epoch:=0;epoch<epochs;epoch++{for _,row:=range train{
  pred:=dot(coef,row.x);err:=pred-row.y
  for i,v:=range row.x{coef[i]-=rate*err*v}
 }}
 for _,v:=range coef{if math.IsNaN(v)||math.IsInf(v,0){return coef,errors.New("nonfinite trained parameter")}}
 return coef,nil
}
func dot(a,b [memoryLength+1]float64)float64{v:=0.0;for i:=range a{v+=a[i]*b[i]};return v}
func hashBytes(h hash.Hash,b []byte){_,_=h.Write(b)}
func hashPrediction(h hash.Hash,x float64){var b [8]byte;binary.LittleEndian.PutUint64(b[:],math.Float64bits(x));hashBytes(h,b[:])}
type workerResult struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Seed uint64 `json:"seed"`
 Sessions int `json:"sessions"`
 TrainSamples int `json:"train_samples"`
 HeldoutSamples int `json:"heldout_samples"`
 TrainSourceSHA256 string `json:"train_source_sha256"`
 HeldoutSourceSHA256 string `json:"heldout_source_sha256"`
 PredictionSHA256 string `json:"prediction_sha256"`
 TrainMSE float64 `json:"train_mse"`
 HeldoutMSE float64 `json:"heldout_mse"`
 PeakRSSBytes uint64 `json:"peak_rss_bytes"`
 MemoryMetric string `json:"memory_metric"`
}
func work(mode,scenario string,seed uint64)(workerResult,error){
 var r workerResult
 if !contains(modes,mode)||!contains(scenarios,scenario){return r,errors.New("unknown experiment mode/scenario")}
 trainHash:=sha256.New();evalHash:=sha256.New();predHash:=sha256.New()
 trainErr,evalErr:=0.0,0.0;n:=0
 for sess:=0;sess<sessions;sess++{
  train:=stream(seed,sess,false);heldout:=stream(seed,sess,true)
  hashBytes(trainHash,train);hashBytes(evalHash,heldout)
  features,err:=samples(train,mode,scenario,seed);if err!=nil{return r,err}
  eval,err:=samples(heldout,mode,scenario,seed);if err!=nil{return r,err}
  coef,err:=fitted(features,mode);if err!=nil{return r,err}
  for _,row:=range features{e:=dot(coef,row.x)-row.y;trainErr+=e*e}
  for _,row:=range eval{
   p:=dot(coef,row.x);if math.IsNaN(p)||math.IsInf(p,0){return r,errors.New("nonfinite prediction")}
   hashPrediction(predHash,p);e:=p-row.y;evalErr+=e*e
  }
  n+=len(eval)
 }
 peak,err:=peakResidentBytes();if err!=nil{return r,err};if peak==0{return r,errors.New("zero peak RSS")}
 r=workerResult{Schema:schema,Mode:mode,Scenario:scenario,Seed:seed,Sessions:sessions,
  TrainSamples:n,HeldoutSamples:n,TrainSourceSHA256:hex.EncodeToString(trainHash.Sum(nil)),
  HeldoutSourceSHA256:hex.EncodeToString(evalHash.Sum(nil)),PredictionSHA256:hex.EncodeToString(predHash.Sum(nil)),
  TrainMSE:trainErr/float64(n),HeldoutMSE:evalErr/float64(n),PeakRSSBytes:peak,
  MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"}
 if math.IsNaN(r.HeldoutMSE)||math.IsInf(r.HeldoutMSE,0)||r.HeldoutMSE<0{return workerResult{},errors.New("invalid MSE")}
 return r,nil
}
func contains(a []string,x string)bool{for _,s:=range a{if s==x{return true}};return false}
