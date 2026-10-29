package main
import (
 "bytes"
 "crypto/sha256"
 "fmt"
 "testing"
)
func TestACC39ExactPublicSourceDeterministic(t *testing.T){
 for _,c:=range []Cohort{REPEATED,RANDOM}{
  a,e:=source(c);if e!=nil{t.Fatal(e)}
  b,e:=source(c);if e!=nil{t.Fatal(e)}
  if len(a)!=RawBytes||!bytes.Equal(a,b){t.Fatalf("source drift %s",c)}
 }
}
func TestACC39RealCompressionAndEntropyCounterexample(t *testing.T){
 repeated,_:=source(REPEATED);random,_:=source(RANDOM)
 compR,e:=encode(repeated);if e!=nil{t.Fatal(e)}
 compN,e:=encode(random);if e!=nil{t.Fatal(e)}
 if len(compR)*4>=len(repeated){t.Fatalf("repeat compression too weak %d",len(compR))}
 if len(compN)*100<=len(random)*95{t.Fatalf("random information falsely compressible %d",len(compN))}
 for _,item:=range []struct{encoded,raw []byte}{{compR,repeated},{compN,random}}{
  recovered,e:=decode(item.encoded);if e!=nil||!bytes.Equal(recovered,item.raw){t.Fatalf("lost source bytes: %v",e)}
 }
}
func TestACC39CorruptAndTruncatedSourceFailClosed(t *testing.T){
 data,_:=source(REPEATED);compressed,e:=encode(data);if e!=nil{t.Fatal(e)}
 for _,bad:=range [][]byte{nil,[]byte("not-zlib"),compressed[:len(compressed)/2]}{
  if _,e=decode(bad);e==nil{t.Fatal("corrupt/truncated codec accepted")}
  if _,e=scanStream(bad,sha256.Sum256(data));e==nil{t.Fatal("stream accepted corrupt input")}
 }
 wrong:=sha256.Sum256([]byte("not the source"))
 if _,e=scanWhole(data,wrong);e==nil{t.Fatal("wrong public source checksum accepted")}
 if _,e=scanStream(compressed,wrong);e==nil{t.Fatal("wrong source checksum in streaming accepted")}
}
func TestACC39AllFourRealGoArmsExactInferenceTrace(t *testing.T){
 for _,c:=range []Cohort{REPEATED,RANDOM}{
  var truth string
  for _,arm:=range []Mode{RAW,JIT,CACHED,STREAM}{
   w,e:=runWorker(arm,c);if e!=nil{t.Fatal(e)}
   if w.Sessions!=Sessions||w.Passes!=Passes||w.SourceBytes!=RawBytes||w.TraceDigest==""{
    t.Fatalf("worker %s/%s not complete",c,arm)
   }
   if arm==RAW {truth=w.TraceDigest
   }else{
    if w.TraceDigest!=truth{t.Fatalf("source distortion %s/%s: %s!=%s",c,arm,w.TraceDigest,truth)}
    if w.CompressedBytesTotal<=0||w.DecodedBytesTotal!=Sessions*Passes*RawBytes{
     t.Fatalf("work not charged %s/%s",c,arm)
    }
   }
  }
 }
}
func TestACC39RejectUnknownModesAndSource(t *testing.T){
 if _,e:=source(Cohort("unregistered"));e==nil{t.Fatal("unregistered cohort accepted")}
 if _,e:=runWorker(Mode("UNVERIFIED"),REPEATED);e==nil{t.Fatal("unregistered candidate accepted")}
 if _,e:=runWorker(RAW,Cohort("unknown"));e==nil{t.Fatal("unregistered source accepted")}
}
func TestACC39FrozenProtocolAndClassifications(t *testing.T){
 if RawBytes!=262144||Sessions!=8||Passes!=16||Trials!=5||BufferBytes!=32768{
  t.Fatal("pre-registered source/resources changed")
 }
 if fmt.Sprint(RAW,JIT,CACHED,STREAM)!="RAWJITCACHEDSTREAM"{
  t.Fatal("arm order changed")
 }
}
