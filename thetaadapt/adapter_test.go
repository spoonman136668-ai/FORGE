package thetaadapt
import (
 "reflect"
 "strings"
 "testing"
)
func fixture()(Frozen,Training){
 tr:=Training{Schema:TrainingSchema,Lane:"Wingless",SourceSHA:strings.Repeat("a",40),Records:[]TrainingRecord{
  {Sequence:1,EvidenceSHA256:strings.Repeat("b",64),Classification:"NEGATIVE",TrainingOnly:true,Compute:3,Direction:[]int64{1,-1,0}},
  {Sequence:2,EvidenceSHA256:strings.Repeat("c",64),Classification:"MIXED",TrainingOnly:true,Compute:4,Direction:[]int64{1,1,0}},
  {Sequence:3,EvidenceSHA256:strings.Repeat("d",64),Classification:"INVALID",TrainingOnly:true,Compute:2,Direction:[]int64{0,0,0}},
  {Sequence:4,EvidenceSHA256:strings.Repeat("e",64),Classification:"CONSUMED_INDETERMINATE",TrainingOnly:true,Compute:1,Direction:[]int64{0,0,0}},
 }}
 f:=Frozen{Schema:FrozenSchema,Lane:"Wingless",Epoch:1,SourceSHA:tr.SourceSHA,TrainingSHA256:TrainingDigest(tr),
  FeatureCount:3,InitialWeights:[]int64{2,-2,0},MaxAbsWeight:5,LearningStep:3,MaxUpdates:4,MaxTrainingCompute:10}
 return f,tr
}
func TestPinnedTrainOnlyReplayKeepsNegativesAndInvalids(t *testing.T){
 f,tr:=fixture()
 a,err:=Adapt(f,FrozenDigest(f),tr,TrainingDigest(tr))
 if err!=nil{t.Fatal(err)}
 b,err:=Adapt(f,FrozenDigest(f),tr,TrainingDigest(tr))
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("not deterministic",err)}
 if !reflect.DeepEqual(a.Weights,[]int64{5,-2,0})||
  a.UpdatesApplied!=4||a.RecordsPreserved!=4||a.ComputeSpent!=10||
  a.NegativeCount!=1||a.MixedCount!=1||a.InvalidCount!=1||a.IndeterminateCount!=1||
  a.LineageHeadSHA256==Genesis||!hexLower(a.LineageHeadSHA256,64)||
  a.ScientificAccepted||a.DispatchAuthorized||a.SealedHoldoutConsumed{
  t.Fatalf("unsafe advisory result: %+v",a)
 }
}
func TestTrainingAndFrozenDriftBlocked(t *testing.T){
 f,tr:=fixture();frozenPin,trainingPin:=FrozenDigest(f),TrainingDigest(tr)
 f.LearningStep++
 if _,err:=Adapt(f,frozenPin,tr,trainingPin);err==nil{t.Fatal("accepted frozen drift")}
 f,tr=fixture();tr.Records[0].Direction[0]=-1
 if _,err:=Adapt(f,frozenPin,tr,trainingPin);err==nil{t.Fatal("accepted history drift")}
}
func TestMaliciousRepinStillRejectsBadContracts(t *testing.T){
 cases:=map[string]func(*Frozen,*Training){
  "lane":func(f *Frozen,t *Training){f.Lane="KTRADE"},
  "cross-lane":func(f *Frozen,t *Training){t.Lane="Yggdrasil"},
  "unmatched-source":func(f *Frozen,t *Training){t.SourceSHA=strings.Repeat("f",40)},
  "bad-source":func(f *Frozen,t *Training){f.SourceSHA=strings.Repeat("A",40)},
  "duplicate":func(f *Frozen,t *Training){t.Records[1].EvidenceSHA256=t.Records[0].EvidenceSHA256},
  "not-training":func(f *Frozen,t *Training){t.Records[1].TrainingOnly=false},
  "invalid-direction":func(f *Frozen,t *Training){t.Records[2].Direction[0]=1},
  "consumed-direction":func(f *Frozen,t *Training){t.Records[3].Direction[0]=1},
  "gradient-growth":func(f *Frozen,t *Training){t.Records[0].Direction[1]=2},
  "sequence":func(f *Frozen,t *Training){t.Records[1].Sequence=7},
  "classification":func(f *Frozen,t *Training){t.Records[1].Classification="HELDOUT"},
  "budget":func(f *Frozen,t *Training){f.MaxTrainingCompute=9},
  "updates":func(f *Frozen,t *Training){f.MaxUpdates=3},
  "hidden-capacity":func(f *Frozen,t *Training){f.FeatureCount=4},
  "invalid-weight":func(f *Frozen,t *Training){f.InitialWeights[0]=500},
  "huge-step":func(f *Frozen,t *Training){f.LearningStep=101},
  "capacity-ceiling":func(f *Frozen,t *Training){f.FeatureCount=17},
  "epoch":func(f *Frozen,t *Training){f.Epoch=0},
  "evidence":func(f *Frozen,t *Training){t.Records[0].EvidenceSHA256=""},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   f,tr:=fixture();mutate(&f,&tr)
   f.TrainingSHA256=TrainingDigest(tr)
   if _,err:=Adapt(f,FrozenDigest(f),tr,TrainingDigest(tr));err==nil{t.Fatal("accepted unqualified training")}
  })
 }
}
func TestCrossLaneLineageIdentity(t *testing.T){
 a,at:=fixture();b,bt:=fixture()
 b.Lane="Yggdrasil";bt.Lane="Yggdrasil";b.TrainingSHA256=TrainingDigest(bt)
 ar,ae:=Adapt(a,FrozenDigest(a),at,TrainingDigest(at))
 br,be:=Adapt(b,FrozenDigest(b),bt,TrainingDigest(bt))
 if ae!=nil||be!=nil||ar.LineageHeadSHA256==br.LineageHeadSHA256{t.Fatal("cross-lane collision",ae,be)}
}
