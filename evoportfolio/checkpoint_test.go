package evoportfolio
import ("strings";"testing")
func TestRestartCheckpointIntegrity(t *testing.T){
 f:=fixture();h,err:=BuildHandoff(f,Digest(f));if err!=nil{t.Fatal(err)}
 complete:=func(id string)Completion{return Completion{CandidateID:id,SourceSHA:strings.Repeat("a",40),EvidenceSHA256:strings.Repeat("c",64),FrozenSHA256:h.FrozenSHA256,DecisionSHA256:h.DecisionSHA256,Outcome:"NEGATIVE"}}
 one,err:=AdvanceCheckpoint(h,Checkpoint{},complete("alpha"));if err!=nil{t.Fatal(err)}
 two,err:=AdvanceCheckpoint(h,one,complete("gamma"));if err!=nil{t.Fatal(err)}
 if two.PriorCheckpointSHA256!=one.DigestSHA256||two.DispatchAuthorized||len(two.Completions)!=2{t.Fatalf("%+v",two)}
 if _,err:=AdvanceCheckpoint(h,one,complete("beta"));err==nil{t.Fatal("skipped order")}
 if _,err:=AdvanceCheckpoint(h,one,complete("alpha"));err==nil{t.Fatal("replayed completion")}
 tampered:=one;tampered.Completions=append([]Completion(nil),one.Completions...)
 tampered.Completions[0].Outcome="SUPPORTED"
 if _,err:=AdvanceCheckpoint(h,tampered,complete("gamma"));err==nil{t.Fatal("accepted mutated prior receipt")}
 bad:=complete("gamma");bad.EvidenceSHA256="bad"
 if _,err:=AdvanceCheckpoint(h,one,bad);err==nil{t.Fatal("accepted missing evidence identity")}
}
