package main
import (
 "bytes"
 "encoding/binary"
 "testing"
)

func TestRadixExactLateCounterexampleAndColdRestore(t *testing.T){
 r:=newRadix()
 a:=bytes.Repeat([]byte("A"),64)
 b:=bytes.Clone(a);b[63]='B'
 c:=bytes.Clone(a);c[40]='C'
 r.add(a,0);r.add(a,0);r.add(b,1);r.add(c,1)
 for _,caseData:=range []struct{key []byte;want counts}{
  {a,counts{2,0}},{b,counts{0,1}},{c,counts{0,1}},
 }{
  got,ok:=r.find(caseData.key)
  if !ok||got!=caseData.want{t.Fatalf("exact late split lost %v / %v",got,ok)}
 }
 if r.splits<1{t.Fatal("no dynamically discovered radix split")}
 checkpoint:=r.snapshot()
 cold,e:=restoreRadix(checkpoint);if e!=nil{t.Fatal(e)}
 if !bytes.Equal(checkpoint,cold.snapshot()){t.Fatal("cold restore changed bytes")}
 for _,key:=range [][]byte{a,b,c}{v,ok:=cold.find(key);if !ok||v!=func()counts{w,_:=r.find(key);return w}(){t.Fatal("restored value changed")}}
 absent:=bytes.Clone(a);absent[62]='Z'
 if _,ok:=cold.find(absent);ok{t.Fatal("absent identity falsely present")}
}
func TestInvalidCheckpointMustNotBeReinterpreted(t *testing.T){
 r:=newRadix();r.add(bytes.Repeat([]byte("Z"),64),1)
 b:=r.snapshot()
 for _,bad:=range [][]byte{b[:len(b)-1],append(append([]byte{},b...),7),[]byte("AC35RAW1"),[]byte("")}{
  if _,e:=restoreRadix(bad);e==nil{t.Fatal("corrupted checkpoint accepted")}
 }
}
func TestRawAndZlibRealCompressedRestore(t *testing.T){
 records:=makeRecords("DELAYED",2)
 m:=rawMap(records)
 raw:=rawSnapshot(m)
 cold,e:=rawRestore(raw);if e!=nil{t.Fatal(e)}
 if !bytes.Equal(raw,rawSnapshot(cold)){t.Fatal("raw snapshot not canonical")}
 z,e:=compress(raw);if e!=nil{t.Fatal(e)}
 d,e:=decompress(z);if e!=nil||!bytes.Equal(raw,d){t.Fatal("zlib restored wrong raw bytes",e)}
 if len(z)>=len(raw){t.Fatal("strong zlib control should exploit declared shared-prefix workload")}
 if _,e:=rawRestore(append(append([]byte{},raw...),1));e==nil{t.Fatal("raw restored malformed data")}
}
func TestDelayedScenarioProducesTrueCollisionThatPrefixOnlyLoses(t *testing.T){
 records:=makeRecords("DELAYED",0)
 early:=make(map[string]counts)
 for _,r:=range records{
  k:=string(r.key[:40]);x:=early[k];x[r.label]++;early[k]=x
 }
 collisions:=0
 for _,v:=range early{if v[0]>0&&v[1]>0{collisions++}}
 if collisions==0{t.Fatal("delayed contradictory histories never occurred")}
 r:=newRadix()
 for _,k:=range records{r.add(k.key[:],k.label)}
 if r.splits==0{t.Fatal("no lineage-preserving split")}
 for _,k:=range records{
  v,ok:=r.find(k.key[:]);if !ok||v[k.label]<1{t.Fatal("source identity lost")}
 }
}
func TestAllThreeExactArmsAndUnsafeFalsifier(t *testing.T){
 for _,scenario:=range []string{"BENIGN","DELAYED"}{
  by:=map[string]worker{}
  for _,mode:=range []string{"raw","radix","zlib","unsafe"}{
   w,e:=runWorker(mode,scenario,0);if e!=nil{t.Fatal(e)}
   if w.Sessions!=16||w.Events!=16*1024||w.Queries!=16*512||w.SnapshotBytes<=0{
    t.Fatal("whole-worker source protocol failed")
   }
   by[mode]=w
  }
  for _,mode:=range []string{"radix","zlib"}{
   if by[mode].Wrong!=0||by[mode].Digest!=by["raw"].Digest{
    t.Fatalf("exact arm %s changed original source responses",mode)
   }
  }
  if scenario=="DELAYED"&&(by["unsafe"].Wrong==0||by["radix"].DelayedContradictoryGroups==0){
    t.Fatal("hidden temporal counterexample not materialized")
  }
 }
}
func TestSourceGeneratorDeterminismAndBoundedMemory(t *testing.T){
 a:=makeRecords("BENIGN",0);b:=makeRecords("BENIGN",0)
 if len(a)!=1024||len(b)!=1024{t.Fatal("wrong source sample count")}
 for i:=range a{if a[i]!=b[i]{t.Fatal("original synthetic generator drift")}}
 // History identity is not merely a numerical label or reward hint.
 if binary.LittleEndian.Uint32(a[7].key[40:44])!=7{
  t.Fatal("source suffix identity unexpectedly missing")
 }
}
