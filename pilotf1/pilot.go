// Package pilotf1 is a single-consumption, synthetic-only experimental
// mechanism library. Its simulations never issue scientific acceptance.
package pilotf1

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

const Schema="forge.f1.original-raw.v1"
const DispositionSchema="forge.f1.postraw-disposition.v1"
const FreezeBlob="be0d5b1eafbbd65573bbdabdfcc42c88c807f7c1"
var WTrain=[]int{4103,4127,4133,4153}
var WHeld=[]int{4177,4199,4201,4211}
var YTrain=[]int{5101,5107,5113,5119,5147,5153,5167,5171}
var YHeld=[]int{5189,5197,5209,5227,5231,5233,5237,5261}

type WinglessRow struct {
 TrainSeed int
 HeldoutSeed int
 Cases int
 OrderedCorrect int
 ReversedCorrect int
 SortedCorrect int
 FittingRows int
 DisjointInputs bool
}
type YggdrasilRow struct {
 TrainSeed int
 HeldoutSeed int
 HotKeys int
 ColdKeys int
 ProtectedColdCorrect int
 LRUSlotColdCorrect int
 ProtectedHotCorrect int
 LRUSlotHotCorrect int
 Slots int
 AcquisitionRows int
 HotEvents int
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
 FrozenClauses [4]bool
 Metrics map[string]float64
 RawSHA256 string
 Cases int
}
type Disposition struct {
 Schema string
 Generation string
 SyntheticOnly bool
 ScientificAccepted bool
 ExternalSourceAdmitted bool
 ExecutionAuthority bool
 AcceptedRefMutation bool
 SourceSHA string
 RunID string
 Outcomes []Outcome
 NextStep string
}
var ErrInvalid=errors.New("FORGE_F1_FROZEN_SCIENTIFIC_EVIDENCE_INVALID")
func hash(raw []byte)string{h:=sha256.Sum256(raw);return hex.EncodeToString(h[:])}
func lower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func ConfirmFreeze(path string)error{
 b,err:=os.ReadFile(path)
 if err!=nil||len(b)>16384||len(b)==0{return ErrInvalid}
 h:=sha1.New()
 _,_=fmt.Fprintf(h,"blob %d\x00",len(b))
 _,_=h.Write(b)
 if hex.EncodeToString(h.Sum(nil))!=FreezeBlob{return ErrInvalid}
 dec:=json.NewDecoder(bytes.NewReader(b))
 var data map[string]any
 if err=dec.Decode(&data);err!=nil{return ErrInvalid}
 if data["schema"]!="forge.sandbox.pilot-f1.prereg.v1"||
  data["phase"]!="FROZEN_BEFORE_IMPLEMENTATION_OR_HELDOUT"||
  data["data_class"]!="SYNTHETIC_ONLY"||data["generation"]!="F1"||
  data["authority"]!="ISOLATED_EXPERIMENT_ONLY_NOT_FSA" {
  return ErrInvalid
 }
 return nil
}
func StartMetadata(lane,run,sourceSHA string)(Raw,error){
 if lane!="Wingless"&&lane!="Yggdrasil"||run==""||len(run)>30||
  !lower(sourceSHA,40){return Raw{},ErrInvalid}
 for _,c:=range run{if c<'0'||c>'9'{return Raw{},ErrInvalid}}
 return Raw{Schema:Schema,Generation:"F1",Lane:lane,FreezeBlob:FreezeBlob,
  SourceSHA:sourceSHA,RunID:run,SyntheticOnly:true},nil
}

const prime=17
var primitive=[6][2]int{{2,1},{3,4},{5,2},{7,6},{4,9},{6,5}}
func affine(coeff [2]int,x int)int {return (coeff[0]*x+coeff[1])%prime}
func fit(role,seed int)([2]int,[4]int,error){
 var sample [4]int
 for i:=0;i<4;i++ {sample[i]=(seed+role*5+3*i)%prime}
 for a:=0;a<prime;a++{for b:=0;b<prime;b++{
  good:=true
  for _,x:=range sample {if affine([2]int{a,b},x)!=affine(primitive[role],x){good=false;break}}
  if good{return [2]int{a,b},sample,nil}
 }}
 return [2]int{},sample,ErrInvalid
}
func contains(sample [4]int,x int)bool{for _,v:=range sample{if v==x{return true}};return false}
func RunWingless(run,sourceSHA string)(Raw,error){
 raw,err:=StartMetadata("Wingless",run,sourceSHA)
 if err!=nil{return Raw{},err}
 for i,seed:=range WHeld{
  var learned [6][2]int
  var trainInputs [6][4]int
  for role:=0;role<6;role++{
   learned[role],trainInputs[role],err=fit(role,WTrain[i])
   if err!=nil{return Raw{},err}
  }
  row:=WinglessRow{TrainSeed:WTrain[i],HeldoutSeed:seed,Cases:192,
   FittingRows:24,DisjointInputs:true}
  for episode:=0;episode<192;episode++{
   a:=(seed+episode*5)%6
   b:=(seed*3+episode*7)%5
   if b>=a{b++}
   // Before any heldout value is consulted, exclude first-input
   // values used for fitting either primitive; the test target stays sealed.
   x:=(seed+episode*7)%prime
   found:=false
   for attempt:=0;attempt<prime;attempt++{
    if !contains(trainInputs[a],x)&&!contains(trainInputs[b],x){found=true;break}
    x=(x+1)%prime
   }
   if !found{return Raw{},ErrInvalid}
   truth:=affine(primitive[b],affine(primitive[a],x))
   ordered:=affine(learned[b],affine(learned[a],x))
   reversed:=affine(learned[a],affine(learned[b],x))
   lo,hi:=a,b
   if lo>hi{lo,hi=hi,lo}
   sorted:=affine(learned[hi],affine(learned[lo],x))
   if ordered==truth{row.OrderedCorrect++}
   if reversed==truth{row.ReversedCorrect++}
   if sorted==truth{row.SortedCorrect++}
  }
  raw.Wingless=append(raw.Wingless,row)
 }
 return raw,nil
}

type memory struct {
 protect map[int]int
 recent map[int]int
 order []int
 limit int
}
func newMemory(limit int)*memory{return &memory{protect:map[int]int{},recent:map[int]int{},limit:limit}}
func (m *memory)offer(key,val int){
 if _,ok:=m.protect[key];ok{return}
 if _,ok:=m.recent[key];ok{
  m.recent[key]=val
  for i,k:=range m.order{if k==key{m.order=append(m.order[:i],m.order[i+1:]...);break}}
 }else{
  if len(m.order)>=m.limit {
   delete(m.recent,m.order[0])
   m.order=m.order[1:]
  }
  m.recent[key]=val
 }
 m.order=append(m.order,key)
}
func (m *memory)has(key int)bool{if _,ok:=m.protect[key];ok{return true};_,ok:=m.recent[key];return ok}
func perm12(seed int)[12]int{
 values:=[12]int{}
 for i:=0;i<12;i++{values[i]=i}
 state:=uint64(seed)
 for i:=11;i>0;i--{
  state=state*6364136223846793005+1442695040888963407
  j:=int((state>>32)%uint64(i+1))
  values[i],values[j]=values[j],values[i]
 }
 return values
}
func label(key int)int{return (key*7+3)%17}
func RunYggdrasil(run,sourceSHA string)(Raw,error){
 raw,err:=StartMetadata("Yggdrasil",run,sourceSHA)
 if err!=nil{return Raw{},err}
 for i,seed:=range YHeld{
  acquisition:=perm12(YTrain[i])
  protected:=newMemory(3)
  lru:=newMemory(9)
  for index,key:=range acquisition{
   if index<6{protected.protect[key]=label(key)}else{protected.offer(key,label(key))}
   lru.offer(key,label(key))
  }
  // Heldout hot split is constructed only AFTER memory allocation.
  split:=perm12(seed)
  var hot [12]bool
  for _,key:=range split[:9]{hot[key]=true}
  for c:=0;c<8;c++ {
   for _,key:=range split[:9] {
    protected.offer(key,label(key))
    lru.offer(key,label(key))
   }
  }
  row:=YggdrasilRow{TrainSeed:YTrain[i],HeldoutSeed:seed,HotKeys:9,ColdKeys:3,
   Slots:9,AcquisitionRows:12,HotEvents:72}
  for key:=0;key<12;key++ {
   if hot[key]{
    if protected.has(key){row.ProtectedHotCorrect++}
    if lru.has(key){row.LRUSlotHotCorrect++}
   }else{
    if protected.has(key){row.ProtectedColdCorrect++}
    if lru.has(key){row.LRUSlotColdCorrect++}
   }
  }
  if len(protected.protect)+len(protected.recent)>9||len(lru.recent)>9{return Raw{},ErrInvalid}
  raw.Yggdrasil=append(raw.Yggdrasil,row)
 }
 return raw,nil
}
func classifyBits(bits [4]bool)string{
 n:=0;for _,b:=range bits{if b{n++}}
 if n==4{return "SUPPORTED"}
 if n==0{return "NEGATIVE"}
 return "MIXED"
}
func Classify(rawBytes []byte,expectedLane string)(Outcome,error){
 var out Outcome
 if len(rawBytes)==0||len(rawBytes)>262144{return out,ErrInvalid}
 dec:=json.NewDecoder(bytes.NewReader(rawBytes));dec.DisallowUnknownFields()
 var r Raw
 if err:=dec.Decode(&r);err!=nil{return out,ErrInvalid}
 var extra any
 if err:=dec.Decode(&extra);err!=io.EOF{return out,ErrInvalid}
 if r.Schema!=Schema||r.Generation!="F1"||r.Lane!=expectedLane||
  r.FreezeBlob!=FreezeBlob||!r.SyntheticOnly||r.ScientificAccepted||
  r.ExternalSourceAdmitted||r.ModelCalls!=0||!lower(r.SourceSHA,40)||
  r.RunID==""{return out,ErrInvalid}
 if r.Lane=="Wingless"{
  if len(r.Wingless)!=4||len(r.Yggdrasil)!=0{return out,ErrInvalid}
  ordered,reversed,sorted,n:=0,0,0,0
  for i,row:=range r.Wingless{
   if row.TrainSeed!=WTrain[i]||row.HeldoutSeed!=WHeld[i]||row.Cases!=192||
    row.FittingRows!=24||!row.DisjointInputs||
    row.OrderedCorrect<0||row.OrderedCorrect>192||
    row.ReversedCorrect<0||row.ReversedCorrect>192||
    row.SortedCorrect<0||row.SortedCorrect>192{return out,ErrInvalid}
   ordered+=row.OrderedCorrect;reversed+=row.ReversedCorrect
   sorted+=row.SortedCorrect;n+=row.Cases
  }
  accuracy:=float64(ordered)/float64(n)
  rgap:=float64(ordered-reversed)/float64(n)
  sgap:=float64(ordered-sorted)/float64(n)
  bits:=[4]bool{accuracy>=0.9,rgap>=0.2,sgap>=0.15,n==768}
  return Outcome{Lane:r.Lane,Disposition:classifyBits(bits),
   FrozenClauses:bits,Cases:n,RawSHA256:hash(rawBytes),
   Metrics:map[string]float64{"ordered_accuracy":accuracy,"reversed_gap":rgap,
    "sorted_gap":sgap,"resource_bound":1}},nil
 }
 if r.Lane=="Yggdrasil" {
  if len(r.Yggdrasil)!=8||len(r.Wingless)!=0{return out,ErrInvalid}
  pc,lc,ph,n:=0,0,0,0
  for i,row:=range r.Yggdrasil{
   if row.TrainSeed!=YTrain[i]||row.HeldoutSeed!=YHeld[i]||
    row.HotKeys!=9||row.ColdKeys!=3||row.Slots!=9||
    row.AcquisitionRows!=12||row.HotEvents!=72||
    row.ProtectedColdCorrect<0||row.ProtectedColdCorrect>3||
    row.LRUSlotColdCorrect<0||row.LRUSlotColdCorrect>3||
    row.ProtectedHotCorrect<0||row.ProtectedHotCorrect>9||
    row.LRUSlotHotCorrect<0||row.LRUSlotHotCorrect>9{return out,ErrInvalid}
   pc+=row.ProtectedColdCorrect;lc+=row.LRUSlotColdCorrect
   ph+=row.ProtectedHotCorrect;n+=row.HotKeys+row.ColdKeys
  }
  cold:=float64(pc)/24
  gain:=float64(pc-lc)/24
  hot:=float64(ph)/72
  bits:=[4]bool{cold>=0.3,gain>=0.25,hot>=0.55,n==96}
  return Outcome{Lane:r.Lane,Disposition:classifyBits(bits),
   FrozenClauses:bits,Cases:n,RawSHA256:hash(rawBytes),
   Metrics:map[string]float64{"cold_recall_protected":cold,
    "cold_gain_over_lru":gain,"hot_recall_protected":hot,"resource_bound":1}},nil
 }
 return out,ErrInvalid
}
func Reconcile(wingless,yggdrasil []byte)(Disposition,error){
 w,err:=Classify(wingless,"Wingless");if err!=nil{return Disposition{},err}
 y,err:=Classify(yggdrasil,"Yggdrasil");if err!=nil{return Disposition{},err}
 var wr,yr Raw
 if json.Unmarshal(wingless,&wr)!=nil||json.Unmarshal(yggdrasil,&yr)!=nil||
  wr.SourceSHA!=yr.SourceSHA||wr.RunID!=yr.RunID||wr.FreezeBlob!=yr.FreezeBlob{
  return Disposition{},ErrInvalid
 }
 return Disposition{Schema:DispositionSchema,Generation:"F1",
  SyntheticOnly:true,SourceSHA:wr.SourceSHA,RunID:wr.RunID,
  Outcomes:[]Outcome{w,y},
  NextStep:"QUARANTINE_PROSPECTIVE_F2_DESIGN_REQUIRES_INDEPENDENT_FREEZE_NO_EXECUTION"},nil
}
// This source never claims full scientific acceptance, external generalization,
// or an unattended production controller: its reports are research observations.
