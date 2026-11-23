package genenv
import (
 "reflect"
 "strings"
 "testing"
)
func fixture()(Frozen,History){
 h:=History{Schema:HistorySchema,Lane:"Wingless",SourceSHA:strings.Repeat("a",40),Records:[]Record{
  {Sequence:1,EvidenceSHA256:strings.Repeat("b",64),TrainingOnly:true,Classification:"NEGATIVE",Vector:[]int64{0,1,1}},
  {Sequence:2,EvidenceSHA256:strings.Repeat("c",64),TrainingOnly:true,Classification:"INVALID",Vector:[]int64{1,0,1}},
 }}
 f:=Frozen{Schema:FrozenSchema,Lane:"Wingless",SourceSHA:h.SourceSHA,Epoch:1,
  HistorySHA256:HistoryDigest(h),Base:[]int64{1,1,1},MaxLevel:3,MaxCandidates:2,
  MaxOperations:3,Requests:[]Request{
  {ID:"familyA",Changes:[]Change{{Index:2,Delta:1}}},
  {ID:"familyB",Changes:[]Change{{Index:0,Delta:1},{Index:1,Delta:1}}},
 }}
 return f,h
}
func TestFrozenNoveltyPreservesHistoricalNegatives(t *testing.T){
 f,h:=fixture();a,err:=Generate(f,FrozenDigest(f),h,HistoryDigest(h))
 if err!=nil{t.Fatal(err)}
 b,err:=Generate(f,FrozenDigest(f),h,HistoryDigest(h))
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("non-deterministic replay",err)}
 if len(a.Candidates)!=2||a.Candidates[0].HistoricalDistance!=1||
 a.Candidates[1].HistoricalDistance!=2||a.NegativeCount!=1||
 a.InvalidCount!=1||a.HistoricalCount!=2||a.OperationsUsed!=3||
 a.Candidates[0].Classification!="UNTESTED_PROPOSAL"||
 a.ScientificAccepted||a.DispatchAuthorized||a.SealedHoldoutConsumed{
  t.Fatalf("unsafe novelty output: %+v",a)
 }
}
func TestFrozenPlanAndHistoryDrift(t *testing.T){
 f,h:=fixture();fp,hp:=FrozenDigest(f),HistoryDigest(h)
 f.MaxLevel=4
 if _,err:=Generate(f,fp,h,hp);err==nil{t.Fatal("accepted frozen plan drift")}
 f,h=fixture();h.Records[0].Classification="SUPPORTED"
 if _,err:=Generate(f,fp,h,hp);err==nil{t.Fatal("accepted archived history drift")}
}
func TestUnqualifiedCandidateAndHistoricalControls(t *testing.T){
 cases:=map[string]func(*Frozen,*History){
 "bad-lane":func(f *Frozen,h *History){f.Lane="KTRADE"},
 "wrong-lane":func(f *Frozen,h *History){h.Lane="Yggdrasil"},
 "wrong-source":func(f *Frozen,h *History){h.SourceSHA=strings.Repeat("f",40)},
 "not-training":func(f *Frozen,h *History){h.Records[0].TrainingOnly=false},
 "historical-duplicate":func(f *Frozen,h *History){h.Records[1].Vector=h.Records[0].Vector},
 "historical-base":func(f *Frozen,h *History){h.Records[0].Vector=f.Base},
 "historical-evidence-replay":func(f *Frozen,h *History){h.Records[1].EvidenceSHA256=h.Records[0].EvidenceSHA256},
 "outcome-injection":func(f *Frozen,h *History){h.Records[0].Classification="HELDOUT"},
 "wrong-sequence":func(f *Frozen,h *History){h.Records[1].Sequence=1},
 "out-of-budget":func(f *Frozen,h *History){f.MaxOperations=2},
 "bad-index":func(f *Frozen,h *History){f.Requests[0].Changes[0].Index=8},
 "growth":func(f *Frozen,h *History){f.Requests[0].Changes[0].Delta=2},
 "no-op":func(f *Frozen,h *History){f.Requests[0].Changes=[]Change{{Index:2,Delta:1},{Index:2,Delta:-1}}},
 "reused-target":func(f *Frozen,h *History){f.Requests[1]=f.Requests[0]},
 "duplicate-id":func(f *Frozen,h *History){f.Requests[1].ID=f.Requests[0].ID},
 "over-capacity":func(f *Frozen,h *History){f.MaxCandidates=1},
 "bad-maxlevel":func(f *Frozen,h *History){f.MaxLevel=0},
 "zero-epoch":func(f *Frozen,h *History){f.Epoch=0},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   f,h:=fixture();mutate(&f,&h);f.HistorySHA256=HistoryDigest(h)
   if _,err:=Generate(f,FrozenDigest(f),h,HistoryDigest(h));err==nil{t.Fatal("accepted invalid novelty contract")}
  })
 }
}
func TestCrossLaneProposalsCannotShareIdentity(t *testing.T){
 f,h:=fixture();yf,yh:=fixture()
 yf.Lane="Yggdrasil";yh.Lane="Yggdrasil";yf.HistorySHA256=HistoryDigest(yh)
 a,ae:=Generate(f,FrozenDigest(f),h,HistoryDigest(h))
 b,be:=Generate(yf,FrozenDigest(yf),yh,HistoryDigest(yh))
 if ae!=nil||be!=nil||a.Candidates[0].EnvironmentSHA256==b.Candidates[0].EnvironmentSHA256{
  t.Fatal("cross-lane identity collision",ae,be)
 }
}
