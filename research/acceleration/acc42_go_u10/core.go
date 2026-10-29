package main

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "hash"
 "unsafe"
)

const (
 schema="forge.acc42.original-u10-packed-kv-sketch.v1"
 logicalBudget=65536
 writes=8192
 queries=16384
 episodes=16
)
var cohorts=[]string{"HOT","WIDE","CHURN"}
var modes=[]string{"FULL_MAP","EXACT_SINGLE","EXACT_TWO","SKETCH_TWO"}
var seeds=[]uint64{84101,84103,84107,84109,84111}
type exactSlot struct{Key uint64;Value uint32;Age uint32}
func split(x uint64)uint64{
 x+=0x9e3779b97f4a7c15
 x=(x^(x>>30))*0xbf58476d1ce4e5b9
 x=(x^(x>>27))*0x94d049bb133111eb
 return x^(x>>31)
}
func cohortDomain(c string)(uint64,error){
 switch c{case "HOT":return 2048,nil;case "WIDE":return 8192,nil;case "CHURN":return 16384,nil}
 return 0,fmt.Errorf("invalid cohort %s",c)
}
func keyFor(base uint64,i int,domain uint64)uint64{
 return split(base^uint64(i)*0xa0761d6478bd642f)%domain
}
func valueFor(k uint64,i int)uint32{return uint32(split(k^uint64(i)*0xe7037ed1a0b428db^0xbabe2026))}
type request struct{Key uint64}
type insert struct{Key uint64;Value uint32}
type episodeData struct{Inserts []insert;Queries []request}
func makeEpisode(c string,seed uint64,session int)(episodeData,error){
 d,e:=cohortDomain(c);if e!=nil{return episodeData{},e}
 base:=split(seed^uint64(session)*0x9e3779b97f4a7c15^0xcaffeebad)
 in:=make([]insert,writes)
 for i:=range in{
  k:=keyFor(base,i,d)
  in[i]=insert{Key:k,Value:valueFor(k,i)}
 }
 out:=make([]request,queries)
 for i:=range out{
  if i%2==0{
   ix:=int(split(base^0x8a5cd789^uint64(i)*0xd6e8feb86659fd93)%writes)
   out[i]=request{Key:in[ix].Key}
  }else{
   // Top-bit is disjoint from every genuine inserted key.
   out[i]=request{Key:(uint64(1)<<63)|split(base^0xfedcba1012345678^uint64(i)*0x94d049bb133111eb)}
  }
 }
 return episodeData{Inserts:in,Queries:out},nil
}
func shaAdd(h hash.Hash,k uint64,v uint32,kind byte){
 var b [13]byte;b[0]=kind
 binary.LittleEndian.PutUint64(b[1:9],k)
 binary.LittleEndian.PutUint32(b[9:13],v)
 _,_=h.Write(b[:])
}
func b1(key uint64,count int)int{return int(split(key^0x97c29b3a61da775f)%uint64(count))}
func b2(key uint64,count int)int{return int(split(key^0x43e1ff98a120cdec)%uint64(count))}
func fp(key uint64)uint16{return uint16(split(key^0xc41ca3ce21f983a7)>>48)}
func pack(tag uint16,val uint32,age uint16)uint64{
 return uint64(tag)|(uint64(val)<<16)|(uint64(age)<<48)
}
func unpack(v uint64)(uint16,uint32,uint16){
 return uint16(v),uint32(v>>16),uint16(v>>48)
}
type table struct{
 mode string
 exact []exactSlot
 sketch []uint64
 dict map[uint64]uint32
 evictions int
}
func newTable(mode string)(*table,error){
 t:=&table{mode:mode}
 switch mode{
 case "FULL_MAP":t.dict=make(map[uint64]uint32)
 case "EXACT_SINGLE","EXACT_TWO":
  if unsafe.Sizeof(exactSlot{})!=16{return nil,errors.New("unexpected exact slot layout")}
  t.exact=make([]exactSlot,4096)
 case "SKETCH_TWO":
  t.sketch=make([]uint64,8192)
 default:return nil,fmt.Errorf("bad arm %s",mode)
 }
 return t,nil
}
func(t *table)LogicalBytes()int{
 switch t.mode{case "FULL_MAP":return -1;default:return logicalBudget}
}
func(t *table)Occupied()int{
 if t.dict!=nil{return len(t.dict)}
 n:=0
 for _,e:=range t.exact{if e.Age!=0{n++}}
 for _,e:=range t.sketch{if e>>48!=0{n++}}
 return n
}
func(t *table)indices(k uint64)[]int{
 count:=1024;if t.mode=="SKETCH_TWO"{count=2048}
 x:=b1(k,count);y:=b2(k,count)
 idx:=[]int{x*4,x*4+1,x*4+2,x*4+3}
 if t.mode!="EXACT_SINGLE"&&x!=y{
  idx=append(idx,y*4,y*4+1,y*4+2,y*4+3)
 }
 return idx
}
func(t *table)Put(k uint64,v uint32,age uint16){
 if t.mode=="FULL_MAP"{t.dict[k]=v;return}
 ix:=t.indices(k)
 found:=-1;empty:=-1;oldest:=-1
 minAge:=uint32(1<<31)
 for _,i:=range ix{
  var slotAge uint32
  match:=false
  if t.mode=="SKETCH_TWO"{
   tag,_,a:=unpack(t.sketch[i]);slotAge=uint32(a);match=a!=0&&tag==fp(k)
  }else{
   e:=t.exact[i];slotAge=e.Age;match=e.Age!=0&&e.Key==k
  }
  if match{found=i;break}
  if slotAge==0&&empty<0{empty=i}
  if slotAge!=0&&slotAge<minAge{minAge=slotAge;oldest=i}
 }
 i:=found
 if i<0{i=empty}
 if i<0{i=oldest;t.evictions++}
 if t.mode=="SKETCH_TWO"{t.sketch[i]=pack(fp(k),v,age)}else{t.exact[i]=exactSlot{Key:k,Value:v,Age:uint32(age)}}
}
func(t *table)Get(k uint64)(uint32,bool){
 if t.mode=="FULL_MAP"{v,ok:=t.dict[k];return v,ok}
 for _,i:=range t.indices(k){
  if t.mode=="SKETCH_TWO"{
   tag,v,age:=unpack(t.sketch[i]);if age!=0&&tag==fp(k){return v,true}
  }else{
   e:=t.exact[i];if e.Age!=0&&e.Key==k{return e.Value,true}
  }
 }
 return 0,false
}
type workerResult struct{
 Schema string
 Mode string
 Cohort string
 Seed uint64
 Episodes int
 InsertCount int
 QueryCount int
 PresentCount int
 CorrectPresent int
 FalsePositiveAbsent int
 WrongPresentValue int
 AbsentCount int
 StateBytes int
 OccupiedSlots int
 Evictions int
 Recall float64
 FalsePositiveRate float64
 LogicalBytesPerCorrect float64
 SourceDigest string
 OracleDigest string
 ResultDigest string
 PeakRSSBytes uint64
 MemoryMetric string
}
func work(mode,cohort string,seed uint64)(workerResult,error){
 var w workerResult
 if !contains(modes,mode)||!contains(cohorts,cohort){return w,errors.New("invalid mode/cohort")}
 sourceH,oracleH,resultH:=sha256.New(),sha256.New(),sha256.New()
 var present,correct,fpAbsent,wrong,absent,occupied,evicted int
 for sess:=0;sess<episodes;sess++{
  data,e:=makeEpisode(cohort,seed,sess);if e!=nil{return w,e}
  t,e:=newTable(mode);if e!=nil{return w,e}
  audit:=make(map[uint64]uint32)
  for i,row:=range data.Inserts{
   shaAdd(sourceH,row.Key,row.Value,1)
   audit[row.Key]=row.Value
   t.Put(row.Key,row.Value,uint16(i+1))
  }
  for _,q:=range data.Queries{
   shaAdd(sourceH,q.Key,0,2)
   val,found:=t.Get(q.Key)
   truth,expected:=audit[q.Key]
   if expected{present++;if found&&val==truth{correct++};if found&&val!=truth{wrong++}}else{absent++;if found{fpAbsent++}}
   var expectedTag uint32;if expected{expectedTag=1}
   shaAdd(oracleH,q.Key,truth,byte(expectedTag))
   var gotTag uint32;if found{gotTag=1}
   shaAdd(resultH,q.Key,val,byte(gotTag))
  }
  occupied+=t.Occupied()
  evicted+=t.evictions
 }
 peak,e:=peakResidentBytes();if e!=nil{return w,e}
 if peak==0||present==0||absent==0{return w,errors.New("missing OS peak RSS or truth denominator")}
 state:=logicalBudget;if mode=="FULL_MAP"{state=-1}
 w=workerResult{
  Schema:schema,Mode:mode,Cohort:cohort,Seed:seed,Episodes:episodes,
  InsertCount:writes*episodes,QueryCount:queries*episodes,
  PresentCount:present,CorrectPresent:correct,FalsePositiveAbsent:fpAbsent,
  WrongPresentValue:wrong,AbsentCount:absent,
  StateBytes:state,OccupiedSlots:occupied,Evictions:evicted,
  Recall:float64(correct)/float64(present),
  FalsePositiveRate:float64(fpAbsent)/float64(absent),
  SourceDigest:hex.EncodeToString(sourceH.Sum(nil)),
  OracleDigest:hex.EncodeToString(oracleH.Sum(nil)),
  ResultDigest:hex.EncodeToString(resultH.Sum(nil)),
  PeakRSSBytes:peak,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",
 }
 if correct>0&&state>0{w.LogicalBytesPerCorrect=float64(state*episodes)/float64(correct)}
 return w,nil
}
func contains(a []string,q string)bool{for _,x:=range a{if x==q{return true}};return false}
