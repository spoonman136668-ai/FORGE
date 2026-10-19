package pilotf1

import (
 "encoding/json"
 "strings"
 "testing"
)

// Deliberately NEVER call RunWingless or RunYggdrasil in source qualification.
// Those functions consume prospective original heldout seeds only in the
// once-only hosted primary workflow.
func fixture(lane string) Raw {
 x:=Raw{Schema:Schema,Generation:"F1",Lane:lane,FreezeBlob:FreezeBlob,
  SourceSHA:strings.Repeat("a",40),RunID:"1234",SyntheticOnly:true}
 if lane=="Wingless" {
  for i:=range WTrain{x.Wingless=append(x.Wingless,WinglessRow{
   TrainSeed:WTrain[i],HeldoutSeed:WHeld[i],Cases:192,
   OrderedCorrect:192,ReversedCorrect:0,SortedCorrect:0,
   FittingRows:24,DisjointInputs:true})}
 }else {
  for i:=range YTrain{x.Yggdrasil=append(x.Yggdrasil,YggdrasilRow{
   TrainSeed:YTrain[i],HeldoutSeed:YHeld[i],HotKeys:9,ColdKeys:3,
   Slots:9,AcquisitionRows:12,HotEvents:72,
   ProtectedColdCorrect:3,LRUSlotColdCorrect:0,
   ProtectedHotCorrect:9,LRUSlotHotCorrect:9})}
 }
 return x
}
func raw(v Raw)[]byte{b,_:=json.Marshal(v);return b}
func TestStructuralClassifierFixtureOnly(t *testing.T){
 w:=raw(fixture("Wingless"))
 y:=raw(fixture("Yggdrasil"))
 d,err:=Reconcile(w,y)
 if err!=nil{t.Fatal(err)}
 if d.Schema!=DispositionSchema||d.ScientificAccepted||d.ExecutionAuthority||
  d.ExternalSourceAdmitted||d.AcceptedRefMutation||!d.SyntheticOnly||
  len(d.Outcomes)!=2||d.Outcomes[0].Disposition!="SUPPORTED"||
  d.Outcomes[1].Disposition!="SUPPORTED"{t.Fatalf("fixture disposition invalid %+v",d)}
}
func TestFrozenThresholdsKeepMixedWithoutRelabeling(t *testing.T){
 p:=fixture("Wingless")
 for i:=range p.Wingless{
  p.Wingless[i].OrderedCorrect=0
  p.Wingless[i].ReversedCorrect=192
  p.Wingless[i].SortedCorrect=192
 }
 d,err:=Classify(raw(p),"Wingless")
 if err!=nil||d.Disposition!="MIXED"{t.Fatalf("frozen mixed disposition: %+v %v",d,err)}
}
func TestFailClosedOnInvalidRawAndPromotion(t *testing.T) {
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  p:=fixture(lane)
  p.ScientificAccepted=true
  if _,err:=Classify(raw(p),lane);err==nil{t.Fatal("forged acceptance trusted")}
  p=fixture(lane);p.ExternalSourceAdmitted=true
  if _,err:=Classify(raw(p),lane);err==nil{t.Fatal("forged external source trusted")}
  p=fixture(lane);p.SourceSHA=""
  if _,err:=Classify(raw(p),lane);err==nil{t.Fatal("missing source trusted")}
 }
 p:=fixture("Wingless")
 p.Wingless=p.Wingless[:3]
 if _,err:=Classify(raw(p),"Wingless");err==nil{t.Fatal("missing raw row trusted")}
 p=fixture("Yggdrasil")
 p.Yggdrasil[0].Slots=10
 if _,err:=Classify(raw(p),"Yggdrasil");err==nil{t.Fatal("capacity overrun accepted")}
}
func TestSeedAndCaseDriftBlocks(t *testing.T){
 p:=fixture("Wingless");p.Wingless[0].HeldoutSeed=WHeld[1]
 if _,err:=Classify(raw(p),"Wingless");err==nil{t.Fatal("seed drift trusted")}
 p=fixture("Wingless");p.Wingless[0].Cases=191
 if _,err:=Classify(raw(p),"Wingless");err==nil{t.Fatal("case loss trusted")}
 p=fixture("Yggdrasil");p.Yggdrasil[0].HotEvents++
 if _,err:=Classify(raw(p),"Yggdrasil");err==nil{t.Fatal("training budget drift trusted")}
}
func TestNoExperimentOnSourceQualification(t *testing.T) {
 // Intentional: this test never invokes prospective evaluators.
 if len(WTrain)!=4||len(WHeld)!=4||len(YTrain)!=8||len(YHeld)!=8{
  t.Fatal("frozen seed cardinality drift")
 }
 seen:=map[int]bool{}
 for _,row:=range [][]int{WTrain,WHeld,YTrain,YHeld} {
  for _,seed:=range row {
   if seen[seed]{t.Fatal("cross-lane or train/heldout seed collision")}
   seen[seed]=true
  }
 }
 if !lower(strings.Repeat("a",40),40)||lower(strings.Repeat("A",40),40){
  t.Fatal("source SHA validation broken")
 }
}
