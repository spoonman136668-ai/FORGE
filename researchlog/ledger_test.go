package researchlog
import ("testing";"strings")
func TestNewJournal(t *testing.T){
 j:=New()
 if err:=Verify(j);err!=nil{t.Fatal(err)}
 if j.Schema!=Schema||len(j.Entries)!=0{t.Fatal("new journal invalid")}
}

func TestLifecycle(t *testing.T){
 hash:=strings.Repeat("a",64)
 source:=strings.Repeat("b",40)
 e:=Event{Lane:"Wingless",Generation:1,ExperimentID:"W01",Kind:Hypothesis,SourceCommitSHA:source}
 j,err:=Append(New(),e);if err!=nil{t.Fatal(err)}
 e.Kind=Preregister;e.PreregSHA256=hash;e.CohortSHA256=strings.Repeat("c",64)
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=SourceQualified;e.WitnessSHA256=hash
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=PrimaryStarted;e.RunID=123
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=PrimaryTerminal;e.Outcome="NEGATIVE";e.OriginalEvidenceSHA256=strings.Repeat("d",64)
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=IndependentReview;e.Note="Finding retained"
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 e.Kind=FinalArchive
 j,err=Append(j,e);if err!=nil{t.Fatal(err)}
 if err=Verify(j);err!=nil{t.Fatal(err)}
 m,err:=ProposeMemoryMilestone(j,j.Entries[6].RecordSHA256)
 if err!=nil||m.IngestionStatus!="REVIEW_REQUIRED_NOT_STAGED"{t.Fatal(err)}
}
