package watchdog
import ("strings";"testing")
func TestIncidentLedgerDeduplicatesAndFailsAtomically(t *testing.T){
 l:=NewIncidentLedger()
 one:=Incident{Lane:"Wingless",OriginalExperimentID:"existing_original",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:7,Action:DiagnoseOrchestration}
 selected,err:=l.SelectNew([]Incident{one});if err!=nil||len(selected)!=1{t.Fatal(selected,err)}
 selected,err=l.SelectNew([]Incident{one});if err!=nil||len(selected)!=0{t.Fatal(selected,err)}
 two:=one;two.Lane="Yggdrasil"
 if _,err=l.SelectNew([]Incident{two,two});err==nil{t.Fatal("duplicate accepted")}
 selected,err=l.SelectNew([]Incident{two});if err!=nil||len(selected)!=1{t.Fatal(selected,err)}
}
