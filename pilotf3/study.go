// Package pilotf3 implements a frozen, synthetic-only F3 original.
// Its source qualification tests never execute primary or examine heldout results.
package pilotf3

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
 FreezeBlob = "e995301ccb7330ac8f31a0fd4b31611032231fac"
 RawSchema = "forge.f3.synthetic-original-raw.v1"
 DispositionSchema = "forge.f3.synthetic-postraw-classification.v1"
 Prime = 23
)
var ErrInvalid=errors.New("FORGE_F3_FROZEN_ORIGINAL_EVIDENCE_INVALID")
var wingTrain=[4]int{8101,8111,8123,8147}
var wingHold=[4]int{8209,8221,8231,8243}
var yggTrain=[8]int{9101,9113,9127,9133,9149,9157,9161,9173}
var yggHold=[8]int{9301,9311,9323,9337,9341,9359,9371,9377}
var roles=[7][2]int{{2,3},{4,1},{7,5},{9,2},{3,8},{5,11},{11,4}}

type WinglessRow struct {
 TrainSeed int
 HeldoutSeed int
 Cases int
 LabeledExamples int
 InputsDisjoint bool
 Correct int
 StaticControl int
 ReverseControl int
}
type YggdrasilRow struct {
 AcquisitionSeed int
 HeldoutSeed int
 Cases int
 ProtectedCold int
 LRUCold int
 ProtectedHot int
 LRUHot int
 Slots int
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
func Digest(data []byte)string {
 sum:=sha256.Sum256(data)
 return hex.EncodeToString(sum[:])
}
func validSHA(sha string,n int)bool {
 if len(sha)!=n{return false}
 for _,c:=range sha {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func ConfirmFreeze(path string)error {
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)==0||len(raw)>16384{return ErrInvalid}
 h:=sha1.New()
 _,_=fmt.Fprintf(h,"blob %d\x00",len(raw))
 _,_=h.Write(raw)
 if hex.EncodeToString(h.Sum(nil))!=FreezeBlob{return ErrInvalid}
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 decoder.DisallowUnknownFields()
 // The exact blob hash is authoritative for the frozen full scientific plan;
 // decoding only sanity-checks required top-level identities.
 var frozen map[string]any
 if decoder.Decode(&frozen)!=nil{return ErrInvalid}
 var extra any
 if decoder.Decode(&extra)!=io.EOF{return ErrInvalid}
 if frozen["schema"]!="forge.sandbox.f3.preregistered.v1"||
  frozen["generation"]!="F3"||frozen["program"]!="FORGE_ONLY_SYNTHETIC_SCIENCE"||
  frozen["data_class"]!="SYNTHETIC_ONLY"||
  frozen["authority"]!="SANDBOX_MANUAL_RELEASE_ONLY_NO_FSA"{
  return ErrInvalid
 }
 return nil
}
func newRaw(lane,run,sourceSHA string)(Raw,error){
 if lane!="Wingless"&&lane!="Yggdrasil"||len(run)==0||len(run)>30||
  !validSHA(sourceSHA,40){return Raw{},ErrInvalid}
 for _,c:=range run{if c<'0'||c>'9'{return Raw{},ErrInvalid}}
 return Raw{Schema:RawSchema,Generation:"F3",Lane:lane,
  FreezeBlob:FreezeBlob,SourceSHA:sourceSHA,RunID:run,SyntheticOnly:true},nil
}
func affine(coef [2]int,x int)int{return (coef[0]*x+coef[1])%Prime}
func permute(n,seed int)[]int{
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
func has(v [5]int,x int)bool{
 for _,n:=range v{if n==x{return true}}
 return false
}
func fit(role,seed int)([2]int,[5]int,error){
 var support [5]int
 for i:=0;i<5;i++ {support[i]=(seed+role*7+i*4)%Prime}
 for a:=0;a<Prime;a++{
  for b:=0;b<Prime;b++{
   c:=[2]int{a,b}
   matched:=true
   for _,x:=range support{
    if affine(c,x)!=affine(roles[role],x){matched=false;break}
   }
   if matched{return c,support,nil}
  }
 }
 return [2]int{},support,ErrInvalid
}
// RunWingless is exclusively for the unique first-use original workflow,
// never a test or source-qualification step.
func RunWingless(run,sourceSHA string)(Raw,error){
 raw,err:=newRaw("Wingless",run,sourceSHA)
 if err!=nil{return Raw{},err}
 for i,seed:=range wingHold{
  assignment:=permute(7,seed)
  var learned [7][2]int
  var supports [7][5]int
  for token,role:=range assignment{
   learned[token],supports[token],err=fit(role,wingTrain[i])
   if err!=nil{return Raw{},err}
  }
  row:=WinglessRow{TrainSeed:wingTrain[i],HeldoutSeed:seed,Cases:256,LabeledExamples:35,InputsDisjoint:true}
  for caseNo:=0;caseNo<256;caseNo++{
   a:=(seed+caseNo*5)%7
   b:=(seed*3+caseNo*7)%6
   if b>=a{b++}
   c:=(seed*5+caseNo*11)%5
   if c>=minInt(a,b){c++}
   if c>=maxInt(a,b){c++}
   x:=(seed+caseNo*13)%Prime
   found:=false
   for trial:=0;trial<Prime;trial++{
    if !has(supports[a],x)&&!has(supports[b],x)&&!has(supports[c],x){
     found=true;break
    }
    x=(x+1)%Prime
   }
   if !found{return Raw{},ErrInvalid}
   correct:=affine(roles[assignment[c]],
    affine(roles[assignment[b]],affine(roles[assignment[a]],x)))
   predicted:=affine(learned[c],affine(learned[b],affine(learned[a],x)))
   fixed:=affine(roles[c],affine(roles[b],affine(roles[a],x)))
   backwards:=affine(learned[a],affine(learned[b],affine(learned[c],x)))
   if predicted==correct{row.Correct++}
   if fixed==correct{row.StaticControl++}
   if backwards==correct{row.ReverseControl++}
  }
  raw.Wingless=append(raw.Wingless,row)
 }
 return raw,nil
}
func minInt(a,b int)int{if a<b{return a};return b}
func maxInt(a,b int)int{if a>b{return a};return b}

type memory struct{
 pinned map[int]bool
 recency map[int]bool
 order []int
 limit int
}
func newMemory(limit int)*memory{return &memory{pinned:map[int]bool{},recency:map[int]bool{},limit:limit}}
func (m *memory)put(k int){
 if m.pinned[k]{return}
 if m.recency[k]{
  for i,v:=range m.order{if v==k{m.order=append(m.order[:i],m.order[i+1:]...);break}}
 }else if len(m.order)>=m.limit{
  delete(m.recency,m.order[0]);m.order=m.order[1:]
 }
 m.recency[k]=true
 m.order=append(m.order,k)
}
func (m *memory)contains(k int)bool{return m.pinned[k]||m.recency[k]}
// RunYggdrasil is exclusively for the unique first-use original workflow.
func RunYggdrasil(run,sourceSHA string)(Raw,error){
 raw,err:=newRaw("Yggdrasil",run,sourceSHA)
 if err!=nil{return Raw{},err}
 for i,seed:=range yggHold{
  acquisition:=permute(18,yggTrain[i])
  protected:=newMemory(6)
  baseline:=newMemory(12)
  for j,k:=range acquisition{
   if j<6{protected.pinned[k]=true}else{protected.put(k)}
   baseline.put(k)
  }
  var finalHot [18]bool
  for phase:=0;phase<4;phase++{
   hot:=permute(18,seed+phase*1103)[:12]
   for cycle:=0;cycle<6;cycle++{
    for _,k:=range hot{protected.put(k);baseline.put(k)}
   }
   if phase==3{for _,k:=range hot{finalHot[k]=true}}
  }
  row:=YggdrasilRow{
   AcquisitionSeed:yggTrain[i],HeldoutSeed:seed,Cases:18,
   Slots:12,ProtectedSlots:6,RecencySlots:6,WorkloadEvents:288,
  }
  for k:=0;k<18;k++{
   if finalHot[k]{
    if protected.contains(k){row.ProtectedHot++}
    if baseline.contains(k){row.LRUHot++}
   }else{
    if protected.contains(k){row.ProtectedCold++}
    if baseline.contains(k){row.LRUCold++}
   }
  }
  if len(protected.pinned)+len(protected.recency)>12||len(baseline.recency)>12{return Raw{},ErrInvalid}
  raw.Yggdrasil=append(raw.Yggdrasil,row)
 }
 return raw,nil
}
func classify(bits [4]bool)string{
 n:=0;for _,v:=range bits{if v{n++}}
 if n==4{return "SUPPORTED"}
 if n==0{return "NEGATIVE"}
 return "MIXED"
}
func Classify(data []byte,lane string)(Outcome,error){
 var out Outcome
 if len(data)==0||len(data)>262144{return out,ErrInvalid}
 dec:=json.NewDecoder(bytes.NewReader(data));dec.DisallowUnknownFields()
 var r Raw
 if dec.Decode(&r)!=nil{return out,ErrInvalid}
 var extra any
 if dec.Decode(&extra)!=io.EOF{return out,ErrInvalid}
 if r.Schema!=RawSchema||r.Generation!="F3"||r.Lane!=lane||
  r.FreezeBlob!=FreezeBlob||!r.SyntheticOnly||r.ScientificAccepted||
  r.ExternalSourceAdmitted||r.ModelCalls!=0||!validSHA(r.SourceSHA,40)||
  len(r.RunID)==0{return out,ErrInvalid}
 for _,v:=range r.RunID{if v<'0'||v>'9'{return out,ErrInvalid}}
 if lane=="Wingless"{
  if len(r.Wingless)!=4||len(r.Yggdrasil)!=0{return out,ErrInvalid}
  correct,static,reversed,n:=0,0,0,0
  for i,row:=range r.Wingless{
   if row.TrainSeed!=wingTrain[i]||row.HeldoutSeed!=wingHold[i]||
    row.Cases!=256||row.LabeledExamples!=35||!row.InputsDisjoint||
    row.Correct<0||row.Correct>256||row.StaticControl<0||
    row.StaticControl>256||row.ReverseControl<0||row.ReverseControl>256{
    return out,ErrInvalid
   }
   correct+=row.Correct;static+=row.StaticControl;reversed+=row.ReverseControl
   n+=row.Cases
  }
  accuracy:=float64(correct)/float64(n)
  gapStatic:=float64(correct-static)/float64(n)
  gapReverse:=float64(correct-reversed)/float64(n)
  bits:=[4]bool{accuracy>=.92,gapStatic>=.40,gapReverse>=.25,n==1024}
  return Outcome{Lane:lane,Disposition:classify(bits),Clauses:bits,Cases:n,
   RawSHA256:Digest(data),Metrics:map[string]float64{
    "ordered_composition_accuracy":accuracy,
    "advantage_vs_static_role_mapping":gapStatic,
    "advantage_vs_reversed_order":gapReverse,
    "verified_disjoint_support_and_capacity":1,
   }},nil
 }
 if lane=="Yggdrasil"{
  if len(r.Yggdrasil)!=8||len(r.Wingless)!=0{return out,ErrInvalid}
  pc,lc,ph,lh,n:=0,0,0,0,0
  for i,row:=range r.Yggdrasil{
   if row.AcquisitionSeed!=yggTrain[i]||row.HeldoutSeed!=yggHold[i]||
    row.Cases!=18||row.Slots!=12||row.ProtectedSlots!=6||
    row.RecencySlots!=6||row.WorkloadEvents!=288||
    row.ProtectedCold<0||row.ProtectedCold>6||row.LRUCold<0||
    row.LRUCold>6||row.ProtectedHot<0||row.ProtectedHot>12||
    row.LRUHot<0||row.LRUHot>12{return out,ErrInvalid}
   pc+=row.ProtectedCold;lc+=row.LRUCold;ph+=row.ProtectedHot;lh+=row.LRUHot
   n+=row.Cases
  }
  if n!=144{return out,ErrInvalid}
  cold:=float64(pc)/48
  gap:=float64(pc-lc)/48
  hot:=float64(ph)/96
  deficit:=float64(lh-ph)/96
  bits:=[4]bool{cold>=.30,gap>=.25,hot>=.55,deficit<=.40}
  return Outcome{Lane:lane,Disposition:classify(bits),Clauses:bits,Cases:n,
   RawSHA256:Digest(data),Metrics:map[string]float64{
    "dormant_cold_recall":cold,"gain_over_equal_capacity_lru":gap,
    "final_hot_recall":hot,"final_hot_deficit_vs_lru":deficit,
   }},nil
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
 return Disposition{Schema:DispositionSchema,Generation:"F3",
  SourceSHA:wr.SourceSHA,RunID:wr.RunID,SyntheticOnly:true,Outcomes:[]Outcome{a,b},
  NextStep:"F4_REQUIRES_NEW_FROZEN_SOURCE_AND_QUALIFIED_INDEPENDENT_FIRST_USE",
 },nil
}
