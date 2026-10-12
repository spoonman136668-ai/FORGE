package watchdog
import("path/filepath";"testing")
func TestShadowLedgerSurvivesProcessRestart(t *testing.T){
 root:=filepath.Join(t.TempDir(),"shadow")
 p,err:=LoadPersistent(root);if err!=nil{t.Fatal(err)}
 if err:=p.CommitSnapshot([]string{"incident-a","incident-b"});err!=nil{t.Fatal(err)}
 q,err:=LoadPersistent(root);if err!=nil{t.Fatal(err)}
 if !q.seen["incident-a"]||!q.seen["incident-b"]{t.Fatal("lost incident state")}
 if err:=q.CommitSnapshot([]string{"incident-a","incident-a"});err==nil{t.Fatal("duplicate accepted")}
}
