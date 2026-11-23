package watchdog
import("strings";"testing")
func TestIncidentChainRejectsTamperingAndStaleHead(t *testing.T){
 a:=Incident{Lane:"Wingless",OriginalExperimentID:"original",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:2,Action:DiagnoseOrchestration}
 rows,err:=AppendIncidentChain(nil,a,zeroHead);if err!=nil{t.Fatal(err)}
 h,err:=VerifyIncidentChain(rows);if err!=nil{t.Fatal(err)}
 if _,err:=AppendIncidentChain(rows,a,zeroHead);err==nil{t.Fatal("stale head accepted")}
 b:=a;b.Lane="Yggdrasil"
 rows,err=AppendIncidentChain(rows,b,h);if err!=nil{t.Fatal(err)}
 rows[0].Incident.Lane="Yggdrasil"
 if _,err:=VerifyIncidentChain(rows);err==nil{t.Fatal("tampering accepted")}
}
