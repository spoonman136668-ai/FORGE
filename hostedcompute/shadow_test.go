package hostedcompute

import (
 "reflect"
 "runtime"
 "strings"
 "sync"
 "testing"
)
var (
 exampleSource=strings.Repeat("a",40)
 exampleTree=strings.Repeat("b",40)
)
func fixture(t *testing.T)Manifest{
 t.Helper()
 m,err:=MakeManifest(exampleSource,exampleTree,"38150001234",1)
 if err!=nil{t.Fatal(err)}
 return m
}
func TestManifestExactIdentityDeterminismAndForbiddenReplay(t *testing.T){
 a:=fixture(t);b:=fixture(t)
 if !reflect.DeepEqual(a,b)||ValidateManifest(a)!=nil||len(a.Work)!=4{
  t.Fatal("non-reproducible manifest")
 }
 for _,bad:=range []struct{name,source,tree,run string;attempt int}{
  {"empty source","",exampleTree,"38150001234",1},
  {"replayed attempt",exampleSource,exampleTree,"38150001234",2},
  {"empty tree",exampleSource,"","38150001234",1},
  {"no run id",exampleSource,exampleTree,"0",1},
  {"bad run id",exampleSource,exampleTree,"01",1},
 }{
  if _,err:=MakeManifest(bad.source,bad.tree,bad.run,bad.attempt);err==nil{
   t.Fatal("untrusted original identity admitted",bad.name)
  }
 }
 a.Work[0].Units++
 if ValidateManifest(a)==nil{t.Fatal("postfreeze work enlargement accepted")}
 a=b;a.Work[0].InputSHA256=strings.Repeat("0",64)
 if ValidateManifest(a)==nil{t.Fatal("tampered candidate input accepted")}
 a=b;a.ManifestSHA256=strings.Repeat("0",64)
 if ValidateManifest(a)==nil{t.Fatal("fake frozen digest accepted")}
}
func TestRunShadowRejectsCrossLaneWorkerAndChangedSource(t *testing.T){
 m:=fixture(t)
 lane:="Wingless";os:=runtime.GOOS
 receipt,err:=RunShadow(m,m.SourceSHA,m.SourceTreeSHA,m.RunID,1,lane,os,expectedWorker(lane,os))
 if err!=nil||VerifyReceipt(m,receipt)!=nil{
  t.Fatal("legitimate bounded no-FSA compute failed",err)
 }
 if receipt.ScientificOriginal||receipt.FSAAdmission||receipt.DispatchAuthorized{
  t.Fatal("shadow acquired science authority")
 }
 if _,err=RunShadow(m,strings.Repeat("c",40),m.SourceTreeSHA,m.RunID,1,lane,os,expectedWorker(lane,os));err==nil{
  t.Fatal("untrusted source substitution accepted")
 }
 if _,err=RunShadow(m,m.SourceSHA,m.SourceTreeSHA,m.RunID,1,"Yggdrasil",os,expectedWorker(lane,os));err==nil{
  t.Fatal("cross-lane worker attribution accepted")
 }
 if _,err=RunShadow(m,m.SourceSHA,m.SourceTreeSHA,m.RunID,1,lane,os,"self-hosted");err==nil{
  t.Fatal("different worker identity accepted")
 }
 if _,err=RunShadow(m,m.SourceSHA,m.SourceTreeSHA,m.RunID,2,lane,os,expectedWorker(lane,os));err==nil{
  t.Fatal("repeated attempt accepted")
 }
 changed:=receipt;changed.OutputSHA256=strings.Repeat("0",64)
 if VerifyReceipt(m,changed)==nil{t.Fatal("fabricated digest accepted")}
 changed=receipt;changed.FSAAdmission=true
 if VerifyReceipt(m,changed)==nil{t.Fatal("shadow promoted to FSA eligibility")}
}
func TestComputeDeterministicAcrossConcurrentLanes(t *testing.T){
 m:=fixture(t)
 var wg sync.WaitGroup
 receipts:=make(chan Receipt,4)
 for _,work:=range m.Work{
  wg.Add(1)
  go func(w WorkItem){
   defer wg.Done()
   digest,err:=computeDigest(w.InputSHA256,w.Units)
   if err!=nil{t.Error(err);return}
   receipts<-Receipt{Schema:ReceiptSchema,Mode:Mode,
    ManifestSHA256:m.ManifestSHA256,SourceSHA:m.SourceSHA,
    SourceTreeSHA:m.SourceTreeSHA,RunID:m.RunID,RunAttempt:m.RunAttempt,
    Lane:w.Lane,OS:w.OS,WorkerLabel:expectedWorker(w.Lane,w.OS),
    Units:w.Units,InputSHA256:w.InputSHA256,OutputSHA256:digest}
  }(work)
 }
 wg.Wait();close(receipts)
 collected:=[]Receipt{}
 for r:=range receipts{collected=append(collected,r)}
 summary,err:=Reconcile(m,collected)
 if err!=nil||summary.AcceptedShadowJobs!=4||
  summary.OriginalExperimentsConsumed!=0||summary.ScientificallyQualified||
  summary.FSAActivated||summary.ScientificDispatchAuthorized||
  summary.PhysicalTrustIndependenceProven||summary.RetentionDurabilityProven{
  t.Fatal("reconciliation acquired original-science authority",err,summary)
 }
 reversed:=append([]Receipt(nil),collected...)
 for i,j:=0,len(reversed)-1;i<j;i,j=i+1,j-1{reversed[i],reversed[j]=reversed[j],reversed[i]}
 second,err:=Reconcile(m,reversed)
 if err!=nil||!reflect.DeepEqual(summary,second){t.Fatal("nondeterministic evidence ordering")}
 changed:=append([]Receipt(nil),collected...)
 changed[0]=changed[1]
 if _,err:=Reconcile(m,changed);err==nil{t.Fatal("duplicate receipt accepted")}
 if _,err:=Reconcile(m,changed[:3]);err==nil{t.Fatal("missing worker accepted")}
 changed=append([]Receipt(nil),collected...)
 changed[0].RunID="38150009999"
 if _,err:=Reconcile(m,changed);err==nil{t.Fatal("different run spliced into evidence")}
}
func TestNoHiddenMutationOfConsumedScientificRuns(t *testing.T){
 m:=fixture(t)
 if m.Mode!=Mode||strings.Contains(m.Describe(),"FSA_QUALIFIED"){
  t.Fatal("shadow misclassified as accepted science")
 }
 for _,w:=range m.Work{
  if w.Units!=4096||w.Lane!="Wingless"&&w.Lane!="Yggdrasil"||
   w.OS!="linux"&&w.OS!="windows"{
   t.Fatal("cross-lane budget or OS drift")
  }
 }
}
func BenchmarkShadowDigest(b *testing.B){
 m,_:=MakeManifest(exampleSource,exampleTree,"38150001234",1)
 b.ResetTimer()
 for i:=0;i<b.N;i++{
  if _,err:=computeDigest(m.Work[0].InputSHA256,m.Work[0].Units);err!=nil{b.Fatal(err)}
 }
}
