package main
import("crypto/sha256";"encoding/binary";"encoding/hex";"errors";"math";"math/bits")
const(schema="forge.acc47.original-u19.nativego.v1";episodes=32;fitN=1024;testN=1024)
var seeds=[]uint64{97101,97103,97107,97109,97111}
var worlds=[]string{"SPARSE_OR","CONJUNCTION","DRIFT","PARITY"}
var arms=[]string{"FREQ16","PERCEPTRON","LUT4","TSETLIN16"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func member(x string,collection []string)bool{for _,v:=range collection{if v==x{return true}};return false}
func features(seed uint64,episode,step int,held bool)uint16{
 ns:=uint64(0x479c66e21e08a5f3);if held{ns=0x870d21fea9b3654c}
 return uint16(mix(seed^uint64(episode)*0x9e3779b97f4a7c15^uint64(step)*0xbf58476d1ce4e5b9^ns))
}
func bit(x uint16,i int)int{return int((x>>uint(i))&1)}
func target(world string,x uint16,fitStep int)uint8{
 switch world{
 case "SPARSE_OR":if bit(x,0)|bit(x,3)|bit(x,7)!=0{return 1}
 case "CONJUNCTION":if (bit(x,0)&bit(x,1))^bit(x,4)!=0{return 1}
 case "DRIFT":
  if fitStep<fitN/2{return target("SPARSE_OR",x,fitStep)}
  return target("CONJUNCTION",x,fitStep)
 case "PARITY":return uint8(bits.OnesCount16(x)&1)
 };return 0
}
func digest(h interface{Write([]byte)(int,error)},tag byte,x uint16,y uint8){var b [4]byte;b[0]=tag;binary.LittleEndian.PutUint16(b[1:3],x);b[3]=y;_,_=h.Write(b[:])}
type model struct{
 Arm string
 Freq [2][16][2]uint32
 Priors [2]uint32
 Weights [17]int32
 LUT [16][2]uint32
 States [16]uint16
}
func newModel(arm string)*model{m:=&model{Arm:arm};for i:=range m.States{m.States[i]=32768};return m}
func bucket(x uint16)int{return bit(x,0)|(bit(x,1)<<1)|(bit(x,3)<<2)|(bit(x,4)<<3)}
func(m *model)Predict(x uint16)uint8{
 switch m.Arm{
 case "FREQ16":
  best:=math.Inf(-1);winner:=uint8(0)
  total:=float64(m.Priors[0]+m.Priors[1])
  for cl:=0;cl<2;cl++{
   n:=float64(m.Priors[cl]);score:=math.Log((n+1)/(total+2))
   for i:=0;i<16;i++{v:=bit(x,i);score+=math.Log((float64(m.Freq[cl][i][v])+1)/(n+2))}
   if score>best{best=score;winner=uint8(cl)}
  };return winner
 case "PERCEPTRON":
  score:=m.Weights[16];for i:=0;i<16;i++{score+=int32(bit(x,i))*m.Weights[i]}
  if score>0{return 1};return 0
 case "LUT4":
  c:=m.LUT[bucket(x)];if c[1]>c[0]{return 1};return 0
 case "TSETLIN16":
  count:=0;for i:=0;i<16;i++{if m.States[i]>=32768&&bit(x,i)==1{count++}}
  if count>=4{return 1};return 0
 };return 0
}
func(m *model)Fit(x uint16,y uint8){
 pred:=m.Predict(x)
 switch m.Arm{
 case "FREQ16":
  m.Priors[y]++;for i:=0;i<16;i++{m.Freq[y][i][bit(x,i)]++}
 case "PERCEPTRON":
  if pred!=y{delta:=int32(-1);if y==1{delta=1};m.Weights[16]+=delta
   for i:=0;i<16;i++{m.Weights[i]+=delta*int32(bit(x,i))}}
 case "LUT4":m.LUT[bucket(x)][y]++
 case "TSETLIN16":
  for i:=0;i<16;i++{
   matched:=bit(x,i)==int(y)
   state:=m.States[i]
   if pred!=y{
    if matched&&state<65535{state++}
    if !matched&&state>0{state--}
   }else if matched&&state<65535{state++}
   m.States[i]=state
  }
 }
}
func(m *model)Bytes()int{switch m.Arm{case "FREQ16":return 2*16*2*4+2*4;case "PERCEPTRON":return 17*4;case "LUT4":return 16*2*4;case "TSETLIN16":return 16*2};return -1}
type result struct{Schema,Arm,World,SourceSHA256,FitSHA256,TruthSHA256,PredictionSHA256,MemoryMetric string;Seed uint64;Episodes,FitRows,HeldoutRows,Correct,StateBytes int;HeldoutError float64;PeakRSSBytes uint64}
func work(arm,world string,seed uint64)(result,error){
 var out result;if !member(arm,arms)||!member(world,worlds){return out,errors.New("invalid source or arm")}
 src,fit,truth,pred:=sha256.New(),sha256.New(),sha256.New(),sha256.New()
 correct:=0
 for ep:=0;ep<episodes;ep++{
  m:=newModel(arm)
  for i:=0;i<fitN;i++{x:=features(seed,ep,i,false);y:=target(world,x,i);digest(src,1,x,y);digest(fit,2,x,y);m.Fit(x,y)}
  for i:=0;i<testN;i++{x:=features(seed,ep,i,true);digest(src,3,x,0);got:=m.Predict(x);y:=target(world,x,fitN+i);digest(truth,4,x,y);digest(pred,5,x,got);if got==y{correct++}}
 }
 peak,err:=peakResidentBytes();if err!=nil{return out,err};if peak==0{return out,errors.New("zero RSS")}
 return result{Schema:schema,Arm:arm,World:world,SourceSHA256:hex.EncodeToString(src.Sum(nil)),FitSHA256:hex.EncodeToString(fit.Sum(nil)),TruthSHA256:hex.EncodeToString(truth.Sum(nil)),PredictionSHA256:hex.EncodeToString(pred.Sum(nil)),MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",Seed:seed,Episodes:episodes,FitRows:fitN*episodes,HeldoutRows:testN*episodes,Correct:correct,StateBytes:newModel(arm).Bytes(),HeldoutError:1-float64(correct)/float64(testN*episodes),PeakRSSBytes:peak},nil
}
