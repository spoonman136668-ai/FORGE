package main

import (
 "testing"
)
func TestSourceRingAndFitNovelty(t *testing.T){
 for _,seed:=range seeds{
  b:=episodeBase(seed,3)
  if b!=episodeBase(seed,3){t.Fatal("nondeterministic source")}
  for i:=0;i<fitStates;i++{
   state:=fitState(b,i)
   if countBits(state)!=2{t.Fatal("FIT must be exactly two adjacent bits")}
   if state!=fitState(b,i){t.Fatal("FIT state not repeatable")}
  }
  independent:=false
  for i:=0;i<testStates;i++{
   if heldoutState(b,i)!=fitState(b,i){independent=true}
  }
  if !independent{t.Fatal("heldout source is FIT source")}
 }
}
func countBits(x uint64)int{n:=0;for x>0{x&=x-1;n++};return n}
func TestNeighborhoodBoundaries(t *testing.T){
 if neighborhood((uint64(1)<<63)|uint64(1),0)!=6{t.Fatal("incorrect wrap at left edge")}
 if neighborhood((uint64(1)<<63)|uint64(1),63)!=3{t.Fatal("incorrect wrap at right edge")}
 if neighborhood(0,31)!=0{t.Fatal("zero state must read zero")}
}
func TestRuleShiftAndPrivateWorld(t *testing.T){
 found:=false
 for _,seed:=range seeds{
  r:=makeRules(episodeBase(seed,7))
  for group:=0;group<4;group++{
   for pattern:=0;pattern<8;pattern++{
    cell:=group*16+2
    if truth(r,"RULE_SHIFT",127,cell,pattern)!=truth(r,"RULE_SHIFT",128,cell,pattern){found=true}
    if truth(r,"FOUR_REGIONS",127,cell,pattern)!=truth(r,"FOUR_REGIONS",192,cell,pattern){t.Fatal("nonshifted rules changed")}
   }
  }
 }
 if !found{t.Fatal("no genuinely shifted causal rule")}
}
func TestCellsNeverAccessFarControls(t *testing.T){
 m:=newLearner("LOCAL_CA")
 m.Learn(0,1,1)
 if m.Predict(0,1)!=1{t.Fatal("local own update not learned")}
 m.Learn(2,1,0)
 if m.Predict(0,1)!=1{t.Fatal("non-neighbor affected local prediction")}
 m.Learn(63,1,0)
 m.Learn(1,1,0)
 if m.Predict(0,1)!=1{t.Fatal("own count must have weight four")}
 if m.LogicalBytes()!=2048||m.MessageReadsPerPrediction()!=4{t.Fatal("local storage or messages wrong")}
 if m.Cell[2][1][0]!=1||m.Cell[0][1][1]!=1{t.Fatal("cell identities not retained")}
}
func TestControlsAreTrainedAndTieDeterministic(t *testing.T){
 for _,mode:=range modes{
  m:=newLearner(mode)
  if m.Predict(0,0)!=0{t.Fatal("untrained tie must predict zero")}
  m.Learn(0,7,1)
  if m.Predict(0,7)!=1{t.Fatalf("%s did not learn public consequence",mode)}
  if m.LogicalBytes()<=0{t.Fatal("missing logical storage")}
  old:=m.Predict(0,7)
  for i:=0;i<10;i++{_ = m.Predict(0,7)}
  if m.Predict(0,7)!=old{t.Fatal("heldout prediction modified learned counts")}
 }
 var max uint16=^uint16(0)
 saturate(&max)
 if max!=^uint16(0){t.Fatal("counter overflow")}
}
func TestActualPublicFITAndHeldoutTruthSameAcrossArms(t *testing.T){
 first,e:=work("GLOBAL_FREQ","UNIFORM",96301);if e!=nil{t.Fatal(e)}
 last,e:=work("LOCAL_CA","UNIFORM",96301);if e!=nil{t.Fatal(e)}
 if first.SourceSHA256!=last.SourceSHA256||first.FitSHA256!=last.FitSHA256||first.TruthSHA256!=last.TruthSHA256{t.Fatal("not paired source and audited truth")}
 if first.UnseenCells<=0||first.UnseenCells!=last.UnseenCells{t.Fatal("unseen patterns not measured")}
 if first.EvaluatedCells!=episodes*testStates*cells||last.PeakRSSBytes==0{t.Fatal("incomplete worker/OS RSS")}
 if last.NeighborMessageReads!=int64(last.EvaluatedCells*4){t.Fatal("unmetered neighbor reads")}
}
func TestNeverAdmitSourceDriftOrMissedCPUGate(t *testing.T){
 var rows []trial
 for _,m:=range modes{
  for _,seed:=range seeds{
   c:=workerResult{Mode:m,Regime:"UNIFORM",Seed:seed,SourceSHA256:"source",FitSHA256:"fit",
     TruthSHA256:"truth",UnseenCells:100,PeakRSSBytes:11*1024*1024,ErrorRate:0.1,UnseenErrorRate:0.2}
   cpu:=1.0;if m=="LOCAL_CA"{cpu=0.95}
   rows=append(rows,trial{Worker:c,CPUSeconds:cpu,WallSeconds:2})
  }
 }
 z,e:=compare(rows,"UNIFORM");if e!=nil{t.Fatal(e)}
 if z.Pass{t.Fatal("95 percent CPU cannot qualify 90 percent criterion")}
 rows[0].Worker.FitSHA256="drift"
 if _,e=compare(rows,"UNIFORM");e==nil{t.Fatal("source FIT change accepted")}
}
