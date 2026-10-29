package main

import("testing";"unsafe")
func TestOriginalSourceIndependent(t *testing.T){
 for _,c:=range cohorts{
  a,e:=makeSource(c,92201,2);if e!=nil{t.Fatal(e)}
  b,e:=makeSource(c,92201,2);if e!=nil{t.Fatal(e)}
  n,_:=size(c);if len(a.Inserts)!=n||len(a.Queries)!=queries{t.Fatal("source count")}
  seen:=map[uint32]bool{}
  for i,p:=range a.Inserts{
   if p!=b.Inserts[i]||p.Key>>31!=0||p.Class>=classes||seen[p.Key]{t.Fatal("invalid or nondeterministic distinct key/value")}
   seen[p.Key]=true
  }
  for i,k:=range a.Queries{
   if k!=b.Queries[i]{t.Fatal("nondeterministic query")}
   if i%2==0&&!seen[k]{t.Fatal("missing present key")}
   if i%2==1&&k>>31!=1{t.Fatal("absent key overlaps")}
  }
 }
}
func Test512ByteExactSlots(t *testing.T){
 if unsafe.Sizeof(exactSlot{})!=8{t.Fatal("exact slots not eight bytes")}
 for _,m:=range modes{v,e:=newMemory(m);if e!=nil{t.Fatal(e)};if v.Mode!=m{t.Fatal("arm mismatch")}}
}
func TestCircularConvolutionNotElementwiseBinding(t *testing.T){
 var k,v [dimensions]int64
 k[1]=1;v[2]=1
 bound:=circularBound(k,v)
 if bound[3]!=1||bound[1]!=0||bound[2]!=0{t.Fatal("circular bind not convolution")}
 r:=circularCorrelate(bound,k)
 if r[2]!=1{t.Fatal("circular correlate reversed or incorrect")}
}
func TestCandidateHasNoExactKeyIndex(t *testing.T){
 for _,m:=range []string{"HRR_CCONV","XOR_SUPERPOSE"}{
  mem,_:=newMemory(m)
  mem.Insert(71,3,1)
  for _,s:=range mem.Slots{if s.Used!=0{t.Fatal("superposition smuggled in exact slots")}}
 }
}
func TestExactLookupAbsenceAndEviction(t *testing.T){
 for _,m:=range []string{"EXACT_ONE","EXACT_TWO"}{
  mem,_:=newMemory(m);mem.Insert(31,7,1)
  a,ok:=mem.Retrieve(31);if !ok||a!=7{t.Fatal("exact inserted key lost")}
  if _,ok=mem.Retrieve(31|0x80000000);ok{t.Fatal("exact false positive")}
  for i:=0;i<128;i++{mem.Insert(uint32(i+100),uint8(i%16),uint16(i+2))}
  if mem.Occupied()>64{t.Fatal("exact capacity breached")}
 }
}
func TestPairedSourceTruthAndResources(t *testing.T){
 prev:=worker{}
 for i,m:=range modes{
  x,e:=work(m,"LIGHT",92201);if e!=nil{t.Fatal(m,e)}
  if x.Episodes!=episodes||x.InsertCount!=episodes*24||x.QueryCount!=episodes*queries||x.StateBytes!=512||x.PeakRSSBytes==0{t.Fatal("broken accounting")}
  if i>0&&(x.SourceSHA256!=prev.SourceSHA256||x.TruthSHA256!=prev.TruthSHA256){t.Fatal("arm source/oracle leak")}
  prev=x
 }
}
func TestConservativeAcceptance(t *testing.T){
 var rows []record
 for _,m:=range modes{for _,seed:=range trials{
  w:=worker{Mode:m,Cohort:"LIGHT",Seed:seed,SourceSHA256:"source",TruthSHA256:"truth",Recall:1,PeakRSSBytes:9000000}
  cpu:=1.0;if m=="HRR_CCONV"{cpu=0.95}
  rows=append(rows,record{Worker:w,CPUSeconds:cpu,WallSeconds:2})
 }}
 c,e:=compare(rows,"LIGHT");if e!=nil{t.Fatal(e)}
 if c.Pass{t.Fatal("95 percent CPU ratio qualified")}
 rows[0].Worker.TruthSHA256="wrong"
 if _,e=compare(rows,"LIGHT");e==nil{t.Fatal("accepted drifted truth")}
}
