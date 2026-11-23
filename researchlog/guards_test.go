package researchlog

import ("strings";"testing")
func TestOneShotAndEvidenceContinuity(t *testing.T){
 h:=func(s string,n int)string{return strings.Repeat(s,n)}
 e:=Event{Lane:"Yggdrasil",Generation:2,ExperimentID:"Y02",SourceCommitSHA:h("a",40),Kind:Hypothesis}
 j,err:=Append(New(),e);if err!=nil{t.Fatal(err)}
 e.Kind=Preregister;e.PreregSHA256=h("b",64);e.CohortSHA256=h("c",64)
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=SourceQualified;e.WitnessSHA256=h("d",64)
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=PrimaryStarted;e.RunID=77
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 if _,err=Append(j,e);err==nil{t.Fatal("duplicate primary")}
 repair:=e;repair.Kind=SourceRepair;repair.RunID=0
 if _,err=Append(j,repair);err==nil{t.Fatal("post-start repair")}
 e.Kind=PrimaryTerminal;e.Outcome="MIXED";e.OriginalEvidenceSHA256=h("e",64)
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=IndependentReview;e.Note="Mixed outcome preserved"
 changed:=e;changed.OriginalEvidenceSHA256=h("f",64)
 if _,err=Append(j,changed);err==nil{t.Fatal("changed original evidence")}
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 j.Entries[0].Event.Note="altered"
 if err=Verify(j);err==nil{t.Fatal("altered chain")}
}
