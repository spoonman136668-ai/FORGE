package pilotf2

// All scientific heldout generation is prohibited in source tests. These
// tests only exercise adversarial structural evidence built by hand.
import (
 "encoding/json"
 "strings"
 "testing"
)
func fixture(lane string)Raw{
 r:=Raw{Schema:RawSchema,Generation:"F2",Lane:lane,FreezeBlob:FreezeBlob,
  SourceSHA:strings.Repeat("a",40),RunID:"9001",SyntheticOnly:true}
 if lane=="Wingless" {
  for i:=range wTrain {
   r.Wingless=append(r.Wingless,WinglessRow{
    TrainSeed:wTrain[i],HeldoutSeed:wHold[i],Cases:192,
    TrainingExamples:24,DisjointInputs:true,
    Correct:192,FixedRoleControl:0,ReversedControl:0,
   })
  }
 }else{
  for i:=range yTrain {
   r.Yggdrasil=append(r.Yggdrasil,YggdrasilRow{
    AcquisitionSeed:yTrain[i],HeldoutSeed:yHold[i],Cases:15,
    ProtectedCold:5,LRUCold:0,ProtectedHot:10,LRUHot:10,
    MemorySlots:10,ProtectedSlots:5,RecencySlots:5,WorkloadEvents:150,
   })
  }
 }
 return r
}
func encode(r Raw)[]byte{b,_:=json.Marshal(r);return b}
func TestFrozenSyntheticClassificationFixturesOnly(t *testing.T){
 d,err:=Reconcile(encode(fixture("Wingless")),encode(fixture("Yggdrasil")))
 if err!=nil{t.Fatal(err)}
 if d.Schema!=DispositionSchema||!d.SyntheticOnly||
  d.ScientificAccepted||d.ExternalSourceAdmitted||d.ExecutionAuthority||
  d.AcceptedRefMutation||len(d.Outcomes)!=2{
  t.Fatal("qualification fixture claimed authority")
 }
 for _,o:=range d.Outcomes{
  if o.Disposition!="SUPPORTED"||o.RawSHA256==""||o.Metrics==nil{
   t.Fatalf("fixture mismatch %+v",o)
  }
 }
}
func TestAdverseValidResultsStayMixedNotSilentlyRetuned(t *testing.T){
 r:=fixture("Wingless")
 for i:=range r.Wingless{
  r.Wingless[i].Correct=20
  r.Wingless[i].FixedRoleControl=192
  r.Wingless[i].ReversedControl=192
 }
 o,err:=Classify(encode(r),"Wingless")
 if err!=nil||o.Disposition!="MIXED"||!o.Clauses[3]{
  t.Fatalf("capacity-valid poor science must remain mixed %+v %v",o,err)
 }
}
func TestTamperingAndInvalidCapacityFailClosed(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  r:=fixture(lane);r.ScientificAccepted=true
  if _,err:=Classify(encode(r),lane);err==nil{t.Fatal("forged science acceptance trusted")}
  r=fixture(lane);r.ExternalSourceAdmitted=true
  if _,err:=Classify(encode(r),lane);err==nil{t.Fatal("forged external source trusted")}
  r=fixture(lane);r.SourceSHA=""
  if _,err:=Classify(encode(r),lane);err==nil{t.Fatal("no source SHA trusted")}
 }
 r:=fixture("Wingless");r.Wingless[0].HeldoutSeed=wHold[1]
 if _,err:=Classify(encode(r),"Wingless");err==nil{t.Fatal("seed reuse accepted")}
 r=fixture("Yggdrasil");r.Yggdrasil[0].MemorySlots=11
 if _,err:=Classify(encode(r),"Yggdrasil");err==nil{t.Fatal("hidden memory capacity increase accepted")}
 r=fixture("Yggdrasil");r.Yggdrasil[0].WorkloadEvents=149
 if _,err:=Classify(encode(r),"Yggdrasil");err==nil{t.Fatal("budget drift accepted")}
}
func TestNeverRunPrimaryDuringSourceQualification(t *testing.T){
 if len(wTrain)!=4||len(wHold)!=4||len(yTrain)!=8||len(yHold)!=8{
  t.Fatal("frozen cardinalities drifted")
 }
 used:=map[int]bool{}
 for _,list:=range [][]int{wTrain[:],wHold[:],yTrain[:],yHold[:]}{
  for _,seed:=range list{
   if used[seed]{t.Fatal("train/heldout or cross-lane seed collision")}
   used[seed]=true
  }
 }
 if len(used)!=24{t.Fatal("seed inventory unexpected")}
 // This test deliberately never calls RunWingless or RunYggdrasil.
}
