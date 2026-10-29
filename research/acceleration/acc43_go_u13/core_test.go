package main

import (
 "testing"
 "unsafe"
)
func TestSourceDisjointAndDeterministic(t *testing.T){
 for _,c:=range cohorts{
  a,e:=makeEpisode(c,86101,3);if e!=nil{t.Fatal(e)}
  b,e:=makeEpisode(c,86101,3);if e!=nil{t.Fatal(e)}
  if len(a.Inserts)!=writes||len(a.Queries)!=queries{t.Fatal("incomplete data")}
  for i:=range a.Inserts{if a.Inserts[i]!=b.Inserts[i]||a.Inserts[i].Key>>63!=0{t.Fatal("source or top bit drift")}}
  for i:=range a.Queries{if a.Queries[i]!=b.Queries[i]{t.Fatal("nondeterministic query")};if i%2==1&&a.Queries[i].Key>>63!=1{t.Fatal("absent key domain violated")}}
  if c=="COLLISION-ADVERSARY"{
   for i:=1;i<=7;i+=2{
    q:=a.Queries[i].Key;ok:=false
    for _,entry:=range a.Inserts{if fp(entry.Key)==fp(q)&&b1(entry.Key,2048)==b1(q,2048){ok=true;break}}
    if !ok{t.Fatal("adversarial unknown key lacks tag-and-bucket match")}
   }
  }
 }
}
func TestNeverReuseMisidentifiedACC42Source(t *testing.T){
 oldBase:=split(uint64(86101)^uint64(3)*0x9e3779b97f4a7c15^0xcaffeebad)
 oldKey:=keyFor(oldBase,0,2048)
 fresh,e:=makeEpisode("HOT",86101,3);if e!=nil{t.Fatal(e)}
 if fresh.Inserts[0].Key==oldKey{t.Fatal("ACC42 source namespace accidentally reused")}
}
func TestPackedBudgetAndTagZero(t *testing.T){
 if unsafe.Sizeof(exactSlot{})!=16{t.Fatal("unexpected exact slot layout")}
 for _,m:=range modes{
  x,e:=newTable(m);if e!=nil{t.Fatal(e)}
  if m!="FULL_MAP"&&x.LogicalBytes()!=65536{t.Fatal("budget wrong")}
 }
 if pack(0,123,1)==0{t.Fatal("zero tag must still be populated")}
 a,b,c:=unpack(pack(0,123,1))
 if a!=0||b!=123||c!=1{t.Fatal("tag zero lost")}
}
func TestLastWriteWinsAndAbsence(t *testing.T){
 for _,m:=range modes{
  t1,e:=newTable(m);if e!=nil{t.Fatal(e)}
  t1.Put(7,11,1);t1.Put(7,12,2)
  v,ok:=t1.Get(7);if !ok||v!=12{t.Fatalf("%s overwrite broken",m)}
  if _,ok:=t1.Get(uint64(1)<<63);ok{t.Fatalf("%s absent key returned",m)}
 }
}
func TestCandidateFingerprintFalsePositiveIsVisible(t *testing.T){
 // Same two bucket addresses and same 16-bit tag, distinct keys; audit must report error.
 seen:=map[[2]int]uint64{}
 for k:=uint64(0);k<100000;k++{
  // Same primary bucket and tag is sufficient for an unknown-key false positive.
  // With 134,217,728 combined possibilities, collision is deterministic by pigeonhole at larger ranges.
  key:=[2]int{b1(k,2048),int(fp(k))}
  if prior,ok:=seen[key];ok&&prior!=k{
   tab,_:=newTable("SKETCH_TWO");tab.Put(prior,11,1)
   v,exists:=tab.Get(k);if !exists||v!=11{t.Fatal("candidate collision not exposed")}
   return
  }
  seen[key]=k
 }
 t.Fatal("could not construct source-free fingerprint false positive")
}
func TestEveryArmSameInputAndAudit(t *testing.T){
 for _,c:=range cohorts{
  var prev workerResult
  for i,m:=range modes{
   r,e:=work(m,c,86101);if e!=nil{t.Fatal(c,m,e)}
   if r.PresentCount!=queries*episodes/2||r.AbsentCount!=queries*episodes/2||r.PeakRSSBytes==0{t.Fatal("broken audit")}
   if m=="FULL_MAP"&&(r.Recall!=1||r.FalsePositiveAbsent!=0||r.WrongPresentValue!=0){t.Fatal("oracle diagnostic not exact")}
   if i>0&&(r.SourceDigest!=prev.SourceDigest||r.OracleDigest!=prev.OracleDigest){t.Fatal("source or oracle split")}
   prev=r
  }
 }
}
func TestStrongControlThresholdNotAccidentallyPositive(t *testing.T){
 var rows []record
 for _,m:=range modes{for i,s:=range seeds{
  w:=workerResult{Mode:m,Cohort:"HOT",Seed:s,SourceDigest:"src",OracleDigest:"truth",Recall:1,PeakRSSBytes:30000000}
  cpu:=1.0;if m=="SKETCH_TWO"{cpu=0.95}
  rows=append(rows,record{Worker:w,CPUSeconds:cpu,WallSeconds:2,Trial:i})
 }}
 c,e:=compare(rows,"HOT");if e!=nil{t.Fatal(e)}
 if c.Pass{t.Fatal("0.95x CPU should fail frozen gate")}
 rows[0].Worker.OracleDigest="wrong"
 if _,e:=compare(rows,"HOT");e==nil{t.Fatal("mismatched oracle admitted")}
}
