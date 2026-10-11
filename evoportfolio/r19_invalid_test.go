package evoportfolio
import("strings";"testing")
func TestR196InvalidMustBlockFinalistProgression(t *testing.T){
 f:=fixture();h,err:=BuildHandoff(f,Digest(f));if err!=nil{t.Fatal(err)}
 invalid:=Completion{CandidateID:"alpha",SourceSHA:strings.Repeat("a",40),EvidenceSHA256:strings.Repeat("c",64),FrozenSHA256:h.FrozenSHA256,DecisionSHA256:h.DecisionSHA256,Outcome:"INVALID"}
 if _,err:=AdvanceCheckpoint(h,Checkpoint{},invalid);err==nil{t.Fatal("R196 semantic violation: INVALID cannot be completed")}
 negative:=invalid;negative.Outcome="NEGATIVE"
 cp,err:=AdvanceCheckpoint(h,Checkpoint{},negative);if err!=nil{t.Fatal(err)}
 invalid.CandidateID="gamma"
 if _,err:=AdvanceCheckpoint(h,cp,invalid);err==nil{t.Fatal("INVALID cannot allow follow-on progression")}
}
