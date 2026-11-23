package watchdog
import("path/filepath";"strings";"testing")
func TestShadowSelectionSurvivesRestart(t *testing.T){
 root:=filepath.Join(t.TempDir(),"shadow")
 a:=Incident{Lane:"Wingless",OriginalExperimentID:"old_w",OwnerEpoch:1,JournalHeadSHA256:strings.Repeat("a",64),Action:DiagnoseOrchestration}
 first,err:=SelectAndCommit(root,[]Incident{a});if err!=nil||len(first)!=1{t.Fatal(first,err)}
 second,err:=SelectAndCommit(root,[]Incident{a});if err!=nil||len(second)!=0{t.Fatal(second,err)}
 b:=a;b.Lane="Yggdrasil";b.OriginalExperimentID="old_y"
 next,err:=SelectAndCommit(root,[]Incident{a,b});if err!=nil||len(next)!=1||next[0].Lane!="Yggdrasil"{t.Fatal(next,err)}
}
func TestInvalidShadowBatchDoesNotRecord(t *testing.T){
 root:=filepath.Join(t.TempDir(),"shadow")
 a:=Incident{Lane:"Wingless",OriginalExperimentID:"w",OwnerEpoch:1,JournalHeadSHA256:strings.Repeat("a",64),Action:DiagnoseOrchestration}
 if _,err:=SelectAndCommit(root,[]Incident{a,a});err==nil{t.Fatal("duplicate accepted")}
 records,err:=SelectAndCommit(root,[]Incident{a});if err!=nil||len(records)!=1{t.Fatal(records,err)}
}
