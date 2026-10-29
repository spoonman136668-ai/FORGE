package main

import(
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "hash"
 "unsafe"
)
const (
 schema="forge.acc44.original-u10-holographic-associative-go.v1"
 dimensions=64
 classes=16
 episodes=32
 queries=256
 logicalBudget=512
)
var trials=[]uint64{92201,92203,92207,92209,92211}
var cohorts=[]string{"LIGHT","FULL","OVERLOAD"}
var modes=[]string{"EXACT_ONE","EXACT_TWO","XOR_SUPERPOSE","HRR_CCONV"}
func mix(x uint64)uint64{x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>31)}
func contains(a []string,x string)bool{for _,v:=range a{if v==x{return true}};return false}
func size(c string)(int,error){switch c{case "LIGHT":return 24,nil;case "FULL":return 64,nil;case "OVERLOAD":return 128,nil};return 0,fmt.Errorf("bad cohort %q",c)}
type pair struct{Key uint32;Class uint8}
type source struct{Inserts []pair;Queries []uint32}
func makeSource(cohort string,seed uint64,episode int)(source,error){
 n,err:=size(cohort);if err!=nil{return source{},err}
 base:=mix(seed^uint64(episode)*0x9e3779b97f4a7c15^0x19ae6776413bfa52)
 labels:=mix(seed^uint64(episode)*0x9e3779b97f4a7c15^0xc12d0885ee13d5a7)
 in:=make([]pair,0,n);known:=map[uint32]bool{}
 for i:=uint64(0);len(in)<n;i++{
  key:=uint32(mix(base^i*0x7a5f8ce2d1b94a43))&0x7fffffff
  if known[key]{continue}
  known[key]=true
  class:=uint8(mix(labels^i*0xa24baed4963ee407)%classes)
  in=append(in,pair{Key:key,Class:class})
 }
 out:=make([]uint32,queries)
 for i:=range out{
  if i%2==0{out[i]=in[int(mix(base^0x18d45f9b37e6a2c5^uint64(i)*0xfab0e71c64d4e38d)%uint64(n))].Key
  }else{out[i]=uint32(mix(base^0xdfa9b4a761e2c355^uint64(i)*0xd6e8feb86659fd93))|0x80000000}
 }
 return source{Inserts:in,Queries:out},nil
}
func keyVec(key uint32)[dimensions]int64{
 var v [dimensions]int64
 for i:=range v{if mix(uint64(key)^0x4455acce1020fe76^uint64(i)*0xbf58476d1ce4e5b9)>>63!=0{v[i]=1}else{v[i]=-1}}
 return v
}
func valueVec(class uint8)[dimensions]int64{
 var v [dimensions]int64
 for i:=range v{if mix(uint64(class)^0xa6c1f4e2798b035d^uint64(i)*0x94d049bb133111eb)>>63!=0{v[i]=1}else{v[i]=-1}}
 return v
}
type exactSlot struct{Key uint32;Age uint16;Class uint8;Used uint8}
type memory struct{Mode string;Slots [64]exactSlot;Super [dimensions]int64;Evictions int}
func newMemory(mode string)(*memory,error){
 if !contains(modes,mode){return nil,errors.New("unknown arm")}
 if unsafe.Sizeof(exactSlot{})!=8{return nil,errors.New("exact slot not 8 bytes")}
 return &memory{Mode:mode},nil
}
func slotBucket(k uint32,second bool)int{
 salt:=uint64(0x7ce1aa9fb27d0413);if second{salt=0xe4a56c934b2df805}
 return int(mix(uint64(k)^salt)%16)
}
func(m *memory)indices(k uint32)[]int{
 a:=slotBucket(k,false)
 out:=[]int{a*4,a*4+1,a*4+2,a*4+3}
 if m.Mode=="EXACT_TWO"{
  b:=slotBucket(k,true)
  if a!=b{out=append(out,b*4,b*4+1,b*4+2,b*4+3)}
 }
 return out
}
func circularBound(k,v [dimensions]int64)[dimensions]int64{
 var r [dimensions]int64
 for j:=0;j<dimensions;j++{for i:=0;i<dimensions;i++{r[j]+=k[i]*v[(j-i+dimensions)%dimensions]}}
 return r
}
func circularCorrelate(mem,k [dimensions]int64)[dimensions]int64{
 var r [dimensions]int64
 for j:=0;j<dimensions;j++{for i:=0;i<dimensions;i++{r[j]+=mem[(i+j)%dimensions]*k[i]}}
 return r
}
func(m *memory)Insert(k uint32,c uint8,age uint16){
 if m.Mode=="HRR_CCONV"{
  v:=circularBound(keyVec(k),valueVec(c))
  for i:=range m.Super{m.Super[i]+=v[i]}
  return
 }
 if m.Mode=="XOR_SUPERPOSE"{
  a,b:=keyVec(k),valueVec(c)
  for i:=range m.Super{m.Super[i]+=a[i]*b[i]}
  return
 }
 idx:=m.indices(k);chosen:=-1;empty:=-1;oldest:=-1;minAge:=uint16(65535)
 for _,i:=range idx{
  slot:=m.Slots[i]
  if slot.Used!=0&&slot.Key==k{chosen=i;break}
  if slot.Used==0&&empty<0{empty=i}
  if slot.Used!=0&&slot.Age<minAge{minAge=slot.Age;oldest=i}
 }
 if chosen<0{chosen=empty};if chosen<0{chosen=oldest;m.Evictions++}
 m.Slots[chosen]=exactSlot{Key:k,Age:age,Class:c,Used:1}
}
func(m *memory)Retrieve(k uint32)(uint8,bool){
 if m.Mode=="EXACT_ONE"||m.Mode=="EXACT_TWO"{
  for _,i:=range m.indices(k){slot:=m.Slots[i];if slot.Used!=0&&slot.Key==k{return slot.Class,true}}
  return 0,false
 }
 key:=keyVec(k)
 var retrieval [dimensions]int64
 cutoff:=int64(42)
 if m.Mode=="HRR_CCONV"{retrieval=circularCorrelate(m.Super,key);cutoff=2663
 }else{for i:=range retrieval{retrieval[i]=m.Super[i]*key[i]}}
 bestClass:=uint8(0);bestScore:=int64(-1<<62)
 for c:=uint8(0);c<classes;c++{
  v:=valueVec(c);score:=int64(0)
  for i:=range v{score+=retrieval[i]*v[i]}
  if score>bestScore{bestScore=score;bestClass=c}
 }
 if bestScore<cutoff{return 0,false}
 return bestClass,true
}
func(m *memory)Occupied()int{
 if m.Mode=="HRR_CCONV"||m.Mode=="XOR_SUPERPOSE"{return 64}
 n:=0;for _,s:=range m.Slots{if s.Used!=0{n++}};return n
}
func digestEntry(h hash.Hash,kind byte,key uint32,value uint8,found bool){
 var v [7]byte
 v[0]=kind;binary.LittleEndian.PutUint32(v[1:5],key);v[5]=value;if found{v[6]=1}
 _,_=h.Write(v[:])
}
type worker struct{
 Schema string
 Mode string
 Cohort string
 Seed uint64
 Episodes int
 InsertCount int
 QueryCount int
 Present int
 CorrectPresent int
 WrongPresent int
 Absent int
 FalsePositiveAbsent int
 Recall float64
 AbsentFPR float64
 StateBytes int
 OccupiedSum int
 Evictions int
 SourceSHA256 string
 TruthSHA256 string
 OutputSHA256 string
 PeakRSSBytes uint64
 MemoryMetric string
}
func work(mode,cohort string,seed uint64)(worker,error){
 var out worker
 if !contains(modes,mode)||!contains(cohorts,cohort){return out,errors.New("bad mode or cohort")}
 sourceHash,truthHash,outputHash:=sha256.New(),sha256.New(),sha256.New()
 present,correct,wrong,absent,fp,occupied,evictions,inserts:=0,0,0,0,0,0,0,0
 for ses:=0;ses<episodes;ses++{
  s,err:=makeSource(cohort,seed,ses);if err!=nil{return out,err}
  mem,err:=newMemory(mode);if err!=nil{return out,err}
  oracle:=make(map[uint32]uint8,len(s.Inserts))
  for i,p:=range s.Inserts{
   digestEntry(sourceHash,1,p.Key,p.Class,true)
   oracle[p.Key]=p.Class
   mem.Insert(p.Key,p.Class,uint16(i+1))
  }
  inserts+=len(s.Inserts)
  for _,key:=range s.Queries{
   digestEntry(sourceHash,2,key,0,false)
   got,exists:=mem.Retrieve(key)
   expected,presentKey:=oracle[key]
   digestEntry(truthHash,3,key,expected,presentKey)
   digestEntry(outputHash,4,key,got,exists)
   if presentKey{present++;if exists&&got==expected{correct++};if exists&&got!=expected{wrong++}
   }else{absent++;if exists{fp++}}
  }
  occupied+=mem.Occupied();evictions+=mem.Evictions
 }
 peak,err:=peakResidentBytes();if err!=nil{return out,err}
 if peak==0||present==0||absent==0{return out,errors.New("peak RSS or source denominator missing")}
 out=worker{
  Schema:schema,Mode:mode,Cohort:cohort,Seed:seed,Episodes:episodes,
  InsertCount:inserts,QueryCount:episodes*queries,Present:present,CorrectPresent:correct,
  WrongPresent:wrong,Absent:absent,FalsePositiveAbsent:fp,
  Recall:float64(correct)/float64(present),AbsentFPR:float64(fp)/float64(absent),
  StateBytes:logicalBudget,OccupiedSum:occupied,Evictions:evictions,
  SourceSHA256:hex.EncodeToString(sourceHash.Sum(nil)),TruthSHA256:hex.EncodeToString(truthHash.Sum(nil)),
  OutputSHA256:hex.EncodeToString(outputHash.Sum(nil)),PeakRSSBytes:peak,
  MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",
 }
 return out,nil
}
