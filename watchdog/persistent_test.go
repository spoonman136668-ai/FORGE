package watchdog
import("os";"path/filepath";"testing")
func TestShadowLedgerSurvivesProcessRestart(t *testing.T){
 root:=filepath.Join(t.TempDir(),"shadow")
 p,err:=LoadPersistent(root);if err!=nil{t.Fatal(err)}
 if err:=p.CommitSnapshot([]string{"incident-a","incident-b"});err!=nil{t.Fatal(err)}
 q,err:=LoadPersistent(root);if err!=nil{t.Fatal(err)}
 if !q.seen["incident-a"]||!q.seen["incident-b"]{t.Fatal("lost incident state")}
 if err:=q.CommitSnapshot([]string{"incident-a","incident-a"});err==nil{t.Fatal("duplicate accepted")}
}

func TestShadowLedgerRejectsTrailingData(t *testing.T){
 root:=filepath.Join(t.TempDir(),"shadow")
 p,err:=LoadPersistent(root);if err!=nil{t.Fatal(err)}
 if err=p.CommitSnapshot([]string{"incident-a"});err!=nil{t.Fatal(err)}
 path:=filepath.Join(root,ledgerFile)
 raw,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 raw=append(raw,[]byte("{}")...)
 if err=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 if _,err=LoadPersistent(root);err==nil{t.Fatal("trailing JSON accepted")}
}
