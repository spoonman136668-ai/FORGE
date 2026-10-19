// Package pilotf2 contains a bounded, synthetic-only, once-original FORGE
// experiment. Its unit tests must never invoke these primary evaluators.
package pilotf2

import (
 "bytes"
 "crypto/sha1"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
)

const (
 FreezeBlob="54bccd2f42854f000baccbcb5692faae7aa66057"
 RawSchema="forge.f2.original-raw.v1"
 DispositionSchema="forge.f2.postraw-disposition.v1"
)
var wTrain=[4]int{6101,6113,6121,6131}
var wHold=[4]int{6151,6163,6173,6197}
var yTrain=[8]int{7103,7117,7121,7129,7151,7159,7177,7187}
var yHold=[8]int{7207,7211,7213,7219,7229,7237,7243,7253}
var primitive=[6][2]int{{2,3},{4,1},{7,5},{9,2},{3,8},{5,11}}
const prime=19
var ErrInvalid=errors.New("FORGE_F2_PROSPECTIVE_RAW_INVALID_OR_UNTRUSTED")

type WinglessRow struct {
 TrainSeed int
 HeldoutSeed int
 Cases int
 TrainingExamples int
 DisjointInputs bool
 Correct int
 FixedRoleControl int
 ReversedControl int
}
type YggdrasilRow struct {
 AcquisitionSeed int
 HeldoutSeed int
 Cases int
 ProtectedCold int
 LRUCold int
 ProtectedHot int
 LRUHot int
 MemorySlots int
 ProtectedSlots int
 RecencySlots int
 WorkloadEvents int
}
type Raw struct {
 Schema string
 Generation string
 Lane string
 FreezeBlob string
 SourceSHA string
 RunID string
 SyntheticOnly bool
 ScientificAccepted bool
 ExternalSourceAdmitted bool
 ModelCalls int
 Wingless []WinglessRow
 Yggdrasil []YggdrasilRow
}
type Outcome struct {
 Lane string
 Disposition string
 Clauses [4]bool
 Metrics map[string]float64
 Cases int
 RawSHA256 string
}
type Disposition struct {
 Schema string
 Generation string
 SourceSHA string
 RunID string
 SyntheticOnly bool
 ScientificAccepted bool
 ExternalSourceAdmitted bool
 ExecutionAuthority bool
 AcceptedRefMutation bool
 Outcomes []Outcome
 NextStep string
}
func digest(raw []byte)string{
 h:=sha256.Sum256(raw)
 return hex.EncodeToString(h[:])
}
func validSHA(s string, n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func ConfirmFreeze(path string)error{
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)==0||len(raw)>16384{return ErrInvalid}
 h:=sha1.New()
 _,_=fmt.Fprintf(h,"blob %d\x00",len(raw))
 _,_=h.Write(raw)
 if hex.EncodeToString(h.Sum(nil))!=FreezeBlob{return ErrInvalid}
 var doc struct{ Schema string; Generation string; DataClass string `json:"data_class"`; Program string }
 d:=json.NewDecoder(bytes.NewReader(raw))
 if err=d.Decode(&doc);err!=nil{return ErrInvalid}
 var extra any
 if err=d.Decode(&extra);err!=io.EOF{return ErrInvalid}
 if doc.Schema!="forge.sandbox.f2.preregistered.v1"||doc.Generation!="F2"||
  doc.Program!="FORGE_ONLY_SANDBOX"||doc.DataClass!="SYNTHETIC_ONLY"{return ErrInvalid}
 return nil
}
func newRaw(lane,run,sourceSHA string)(Raw,error){
 if lane!="Wingless"&&lane!="Yggdrasil"||run==""||len(run)>30||
  !validSHA(sourceSHA,40){return Raw{},ErrInvalid}
 for _,r:=range run{if r<'0'||r>'9'{return Raw{},ErrInvalid}}
 return Raw{Schema:RawSchema,Generation:"F2",Lane:lane,FreezeBlob:FreezeBlob,
  SourceSHA:sourceSHA,RunID:run,SyntheticOnly:true},nil
}
func transform(coeff [2]int,x int)int{
 return (coeff[0]*x+coeff[1])%prime
}
func permute(n int,seed int)[]int{
 p:=make([]int,n)
 for i:=range p{p[i]=i}
 state:=uint64(seed)
 for i:=n-1;i>0;i--{
  state=state*6364136223846793005+1442695040888963407
  j:=int((state>>32)%uint64(i+1))
  p[i],p[j]=p[j],p[i]
 }
 return p
}
func contains(values [4]int,x int)bool{
 for _,v:=range values{if v==x{return true}}
 return false
}
func fit(role,trainSeed int)([2]int,[4]int,error){
 var examples [4]int
 for i:=0;i<4;i++{examples[i]=(trainSeed+role*5+i*3)%prime}
 for a:=0;a<prime;a++{
  for b:=0;b<prime;b++{
   coeff:=[2]int{a,b}
   ok:=true
   for _,x:=range examples{
    if transform(coeff,x)!=transform(primitive[role],x){ok=false;break}
   }
   if ok{return coeff,examples,nil}
  }
 }
 return [2]int{},examples,ErrInvalid
}
func RunWingless(run,sourceSHA string)(Raw,error){
 raw,err:=newRaw("Wingless",run,sourceSHA);if err!=nil{return Raw{},err}
 for i,seed:=range wHold{
  binding:=permute(6,seed)
  var learned [6][2]int
  var examples [6][4]int
  for token,role:=range binding{
   learned[token],examples[token],err=fit(role,wTrain[i])
   if err!=nil{return Raw{},err}
  }
  row:=WinglessRow{TrainSeed:wTrain[i],HeldoutSeed:seed,
   Cases:192,TrainingExamples:24,DisjointInputs:true}
  for ep:=0;ep<192;ep++ {
   a:=(seed+ep*5)%6
   b:=(seed*3+ep*7)%5
   if b>=a{b++}
   x:=(seed+ep*7)%prime
   disjoint:=false
   for j:=0;j<prime;j++{
    if !contains(examples[a],x)&&!contains(examples[b],x){
     disjoint=true;break
    }
    x=(x+1)%prime
   }
   if !disjoint{return Raw{},ErrInvalid}
   actual:=transform(primitive[binding[b]],
    transform(primitive[binding[a]],x))
   learnedAnswer:=transform(learned[b],transform(learned[a],x))
   fixed:=transform(primitive[b],transform(primitive[a],x))
   reverse:=transform(learned[a],transform(learned[b],x))
   if learnedAnswer==actual{row.Correct++}
   if fixed==actual{row.FixedRoleControl++}
   if reverse==actual{row.ReversedControl++}
  }
  raw.Wingless=append(raw.Wingless,row)
 }
 return raw,nil
}
type memory struct {
 pinned map[int]bool
 recent map[int]bool
 order []int
 limit int
}
func newMemory(limit int)*memory{
 return &memory{pinned:map[int]bool{},recent:map[int]bool{},limit:limit}
}
func (m *memory)put(key int){
 if m.pinned[key]{return}
 if m.recent[key]{
  for i,k:=range m.order{if k==key{m.order=append(m.order[:i],m.order[i+1:]...);break}}
 }else if len(m.order)>=m.limit{
  delete(m.recent,m.order[0])
  m.order=m.order[1:]
 }
 m.recent[key]=true
 m.order=append(m.order,key)
}
func (m *memory)has(key int)bool{return m.pinned[key]||m.recent[key]}
func RunYggdrasil(run,sourceSHA string)(Raw,error){
 raw,err:=newRaw("Yggdrasil",run,sourceSHA);if err!=nil{return Raw{},err}
 for i,seed:=range yHold{
  acquisition:=permute(15,yTrain[i])
  protected:=newMemory(5)
  baseline:=newMemory(10)
  for index,key:=range acquisition{
   if index<5{protected.pinned[key]=true}else{protected.put(key)}
   baseline.put(key)
  }
  var finalHot [15]bool
  for phase:=0;phase<3;phase++{
   hot:=permute(15,seed+phase*1009)[:10]
   for c:=0;c<5;c++{
    for _,key:=range hot{
     protected.put(key)
     baseline.put(key)
    }
   }
   if phase==2{
    for _,key:=range hot{finalHot[key]=true}
   }
  }
  row:=YggdrasilRow{
   AcquisitionSeed:yTrain[i],HeldoutSeed:seed,Cases:15,
   MemorySlots:10,ProtectedSlots:5,RecencySlots:5,WorkloadEvents:150,
  }
  for key:=0;key<15;key++{
   if finalHot[key]{
    if protected.has(key){row.ProtectedHot++}
    if baseline.has(key){row.LRUHot++}
   }else{
    if protected.has(key){row.ProtectedCold++}
    if baseline.has(key){row.LRUCold++}
   }
  }
  if len(protected.pinned)+len(protected.recent)>10||len(baseline.recent)>10{
   return Raw{},ErrInvalid
  }
  raw.Yggdrasil=append(raw.Yggdrasil,row)
 }
 return raw,nil
}
func classify(bits [4]bool)string{
 count:=0
 for _,ok:=range bits{if ok{count++}}
 if count==4{return "SUPPORTED"}
 if count==0{return "NEGATIVE"}
 return "MIXED"
}
func Classify(raw []byte,lane string)(Outcome,error){
 out:=Outcome{}
 if len(raw)==0||len(raw)>262144{return out,ErrInvalid}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 var r Raw
 if err:=d.Decode(&r);err!=nil{return out,ErrInvalid}
 var extra any
 if err:=d.Decode(&extra);err!=io.EOF{return out,ErrInvalid}
 if r.Schema!=RawSchema||r.Generation!="F2"||r.Lane!=lane||
  r.FreezeBlob!=FreezeBlob||!r.SyntheticOnly||r.ScientificAccepted||
  r.ExternalSourceAdmitted||r.ModelCalls!=0||!validSHA(r.SourceSHA,40)||
  r.RunID==""{return out,ErrInvalid}
 if lane=="Wingless"{
  if len(r.Wingless)!=4||len(r.Yggdrasil)!=0{return out,ErrInvalid}
  correct,fixed,reverse,n:=0,0,0,0
  for i,row:=range r.Wingless{
   if row.TrainSeed!=wTrain[i]||row.HeldoutSeed!=wHold[i]||
    row.Cases!=192||row.TrainingExamples!=24||!row.DisjointInputs||
    row.Correct<0||row.Correct>192||row.FixedRoleControl<0||
    row.FixedRoleControl>192||row.ReversedControl<0||row.ReversedControl>192{return out,ErrInvalid}
   n+=row.Cases;correct+=row.Correct
   fixed+=row.FixedRoleControl;reverse+=row.ReversedControl
  }
  accuracy:=float64(correct)/float64(n)
  fixedGap:=float64(correct-fixed)/float64(n)
  reverseGap:=float64(correct-reverse)/float64(n)
  bits:=[4]bool{accuracy>=.90,fixedGap>=.35,reverseGap>=.20,n==768}
  return Outcome{Lane:lane,Disposition:classify(bits),Clauses:bits,
   Cases:n,RawSHA256:digest(raw),
   Metrics:map[string]float64{"correct_accuracy":accuracy,"gain_over_static_mapping":fixedGap,
    "gain_over_reversed_order":reverseGap,"resource_and_split_integrity":1}},nil
 }
 if lane=="Yggdrasil"{
  if len(r.Yggdrasil)!=8||len(r.Wingless)!=0{return out,ErrInvalid}
  pc,lc,ph,lh,n:=0,0,0,0,0
  for i,row:=range r.Yggdrasil{
   if row.AcquisitionSeed!=yTrain[i]||row.HeldoutSeed!=yHold[i]||
    row.Cases!=15||row.MemorySlots!=10||row.ProtectedSlots!=5||
    row.RecencySlots!=5||row.WorkloadEvents!=150||
    row.ProtectedCold<0||row.ProtectedCold>5||row.LRUCold<0||
    row.LRUCold>5||row.ProtectedHot<0||row.ProtectedHot>10||
    row.LRUHot<0||row.LRUHot>10{return out,ErrInvalid}
   n+=row.Cases;pc+=row.ProtectedCold;lc+=row.LRUCold
   ph+=row.ProtectedHot;lh+=row.LRUHot
  }
  if n!=120{return out,ErrInvalid}
  cold:=float64(pc)/40
  gain:=float64(pc-lc)/40
  hot:=float64(ph)/80
  deficit:=float64(lh-ph)/80
  bits:=[4]bool{cold>=.25,gain>=.20,hot>=.60,deficit<=.40}
  return Outcome{Lane:lane,Disposition:classify(bits),Clauses:bits,
   Cases:n,RawSHA256:digest(raw),
   Metrics:map[string]float64{"dormant_cold_recall":cold,
    "cold_gain_over_equal_capacity_lru":gain,
    "final_hot_recall":hot,"final_hot_deficit_vs_lru":deficit}},nil
 }
 return out,ErrInvalid
}
func Reconcile(w,y []byte)(Disposition,error){
 a,err:=Classify(w,"Wingless");if err!=nil{return Disposition{},err}
 b,err:=Classify(y,"Yggdrasil");if err!=nil{return Disposition{},err}
 var wr,yr Raw
 if json.Unmarshal(w,&wr)!=nil||json.Unmarshal(y,&yr)!=nil||
  wr.SourceSHA!=yr.SourceSHA||wr.RunID!=yr.RunID||wr.FreezeBlob!=yr.FreezeBlob{
  return Disposition{},ErrInvalid
 }
 return Disposition{
  Schema:DispositionSchema,Generation:"F2",
  SourceSHA:wr.SourceSHA,RunID:wr.RunID,SyntheticOnly:true,
  Outcomes:[]Outcome{a,b},
  NextStep:"F3_DESIGN_REQUIRES_NEW_FROZEN_PROSPECTIVE_COHORTS_AND_OWN_QUALIFICATION",
 },nil
}
