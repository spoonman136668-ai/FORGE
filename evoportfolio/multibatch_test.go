package evoportfolio

import("testing")
func TestR19FOneGlobalPortfolioAcrossBatches(t *testing.T){
 f:=fixture();pin:=Digest(f)
 batches:=[]Batch{
  {Lane:f.Lane,FrozenSHA256:pin,Candidates:append([]Candidate(nil),f.Candidates[:2]...)},
  {Lane:f.Lane,FrozenSHA256:pin,Candidates:append([]Candidate(nil),f.Candidates[2:]...)},
 }
 for i:=range batches{batches[i].BatchSHA256=batchDigest(batches[i])}
 got,err:=SelectBatches(f,pin,batches)
 if err!=nil{t.Fatal(err)}
 single,err:=Select(f,pin);if err!=nil{t.Fatal(err)}
 if len(got.Finalists)!=len(single.Finalists)||got.SealedComputeReserved!=single.SealedComputeReserved||got.ScreenComputeSpent!=single.ScreenComputeSpent{t.Fatal("batch resets global compute")}
 for i:=range single.Finalists{if got.Finalists[i].ID!=single.Finalists[i].ID{t.Fatal("batch changed priority")}}
 swapped:=[]Batch{batches[1],batches[0]}
 if _,err:=SelectBatches(f,pin,swapped);err!=nil{t.Fatal("permutation drift",err)}
 if _,err:=SelectBatches(f,pin,[]Batch{batches[0],batches[0]});err==nil{t.Fatal("duplicate batch admitted")}
 tampered:=append([]Batch(nil),batches...)
 tampered[0].Candidates=append([]Candidate(nil),batches[0].Candidates...)
 tampered[0].Candidates[0].Score++
 if _,err:=SelectBatches(f,pin,tampered);err==nil{t.Fatal("tampered screen admitted")}
 rogue:=append([]Batch(nil),batches...)
 rogue[1].Lane="Yggdrasil";rogue[1].BatchSHA256=batchDigest(rogue[1])
 if _,err:=SelectBatches(f,pin,rogue);err==nil{t.Fatal("cross-lane merge admitted")}
 f.MaxScreenCompute=7
 if _,err:=SelectBatches(f,Digest(f),batches);err==nil{t.Fatal("screen budget was enlarged")}
}
