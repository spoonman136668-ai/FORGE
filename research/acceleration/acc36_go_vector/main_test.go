package main
import (
 "bytes"
 "encoding/json"
 "testing"
)

func TestACC36OriginalCandidateDimensionsAndDisjointQueries(t *testing.T){
 if VectorDims!=512||Labels!=16||KnownQueries!=256||UnknownQueries!=64||ColdSessions!=32||Repetitions!=5{
  t.Fatal("preregistered original U07/U18 source-free experiment changed")
 }
 for _,seed:=range Seeds{
  for _,count:=range Sizes{
   keys:=make(map[uint32]bool)
   for i:=0;i<count;i++{
    key:=keyFor(seed,i)
    if keys[key]{t.Fatal("duplicate source FIT key")}
    keys[key]=true
   }
   for j:=0;j<UnknownQueries;j++{
    if keys[absentKeyFor(seed,j)]{t.Fatal("unseen query was leaked to FIT")}
   }
  }
 }
}
func TestACC36ExactDictionaryAndBundledPublicQueryContracts(t *testing.T){
 for _,seed:=range Seeds{
  for _,count:=range Sizes{
   a,e:=train(exact,seed,count);if e!=nil{t.Fatal(e)}
   b,e:=train(bundled,seed,count);if e!=nil{t.Fatal(e)}
   c,e:=train(membership,seed,count);if e!=nil{t.Fatal(e)}
   if len(a.Exact)!=count||len(b.Exact)!=0||len(c.Exact)!=0||len(c.Keys)!=count{
    t.Fatal("candidate was given exact labels or failed to fit genuine source inputs")
   }
   for i:=0;i<count;i++{
    key:=keyFor(seed,i)
    if got:=lookup(a,key);got!=int(valueFor(seed,i)){t.Fatal("dictionary wrong")}
   }
   for i:=0;i<UnknownQueries;i++{
    key:=absentKeyFor(seed,i)
    if lookup(a,key)!=-1||lookup(c,key)!=-1{
     t.Fatal("exact dictionary or membership falsely answered unknown source key")
    }
    if got:=lookup(b,key);got<0||got>=Labels{
     t.Fatal("membership-blind vector unexpectedly abstained")
    }
   }
  }
 }
}
func TestACC36BundleActuallyLosesSourceKnownInformationAtCapacity(t *testing.T){
 a,e:=train(bundled,11,512);if e!=nil{t.Fatal(e)}
 missed:=0
 for i:=0;i<512;i++{
  if lookup(a,keyFor(11,i))!=int(valueFor(11,i)){missed++}
 }
 if missed==0{t.Fatal("bound 512-dimensional bundle unexpectedly gives exact 512-key codebook")}
 shuffled,e:=train("SHUFFLED",29,64);if e!=nil{t.Fatal(e)}
 wrong:=0
 for i:=0;i<64;i++{if lookup(shuffled,keyFor(29,i))!=int(valueFor(29,i)){wrong++}}
 if wrong==0{t.Fatal("shuffled source-training negative failed to falsify retrieval")}
}
func TestACC36ExactSerializedColdRestoreAndTamperRefusal(t *testing.T){
 for _,mode:=range Modes {
  state,e:=train(mode,11,64);if e!=nil{t.Fatal(e)}
  bytes1,e:=snapshot(state);if e!=nil{t.Fatal(e)}
  cold,e:=restore(bytes1);if e!=nil{t.Fatal(e)}
  bytes2,e:=snapshot(cold)
  if e!=nil||!bytes.Equal(bytes1,bytes2){t.Fatal("cold source memory serialized state drift")}
  if lookup(state,keyFor(11,8))!=lookup(cold,keyFor(11,8)){
   t.Fatal("cold source-native selected retrieval changed")
  }
  forged:=append(append([]byte(nil),bytes1...),byte('x'))
  if _,e:=restore(forged);e==nil{t.Fatal("trailing forged snapshot accepted")}
  var env map[string]any
  if e:=json.Unmarshal(bytes1,&env);e!=nil{t.Fatal(e)}
  env["SHA256"]="00"
  wrong,_:=json.Marshal(env)
  if _,e:=restore(wrong);e==nil{t.Fatal("wrong checksum accepted")}
 }
}
func TestACC36OriginalUnseenFalsePositivesAndCPUAccountingShape(t *testing.T){
 dict,e:=work(exact,11,16);if e!=nil{t.Fatal(e)}
 vector,e:=work(bundled,11,16);if e!=nil{t.Fatal(e)}
 member,e:=work(membership,11,16);if e!=nil{t.Fatal(e)}
 if dict.KnownCorrect!=KnownQueries*ColdSessions||dict.KnownWrong!=0||
    dict.UnknownAbstentions!=UnknownQueries*ColdSessions{
  t.Fatal("strong equal-source exact dictionary incomplete")
 }
 if vector.UnknownFalsePositives!=UnknownQueries*ColdSessions{
  t.Fatal("unsafe vector false-positive control missing")
 }
 if member.UnknownAbstentions!=UnknownQueries*ColdSessions||
    member.KnownCorrect+member.KnownWrong!=KnownQueries*ColdSessions{
  t.Fatal("membership source negative or known outputs missing")
 }
 if dict.SourceQuestionSHA256!=vector.SourceQuestionSHA256||
    vector.SourceQuestionSHA256!=member.SourceQuestionSHA256{
  t.Fatal("candidate or baseline received different source queries")
 }
 for _,w:=range []Worker{dict,vector,member}{
  if w.Sessions!=32||w.TrainExamples!=16*32||w.CheckpointBytes<=0||
     !w.ColdCheckpointsExact||w.OriginalSourceEpisodes!=0||
     w.ScientificFirstUse||w.NativeModelIntegration{
    t.Fatal("unmetered or falsely scientific source-free worker")
  }
 }
}
func TestACC36FailClosedUnregisteredModeAndNoScience(t *testing.T){
 if _,e:=work("MAGIC",11,16);e==nil{t.Fatal("unregistered actor accepted")}
 if _,e:=work(exact,17,16);e==nil{t.Fatal("unregistered seed accepted")}
 if _,e:=work(exact,11,15);e==nil{t.Fatal("unregistered capacity accepted")}
 if Schema!="forge.acc36.u07u18.bipolar-memory-go.v1"{
  t.Fatal("new claim scope expanded without prereg")
 }
}
