package pilotf4
import("os";"path/filepath";"testing")
func TestPinnedF4NoHeldoutEvaluation(t *testing.T){
 b,err:=os.ReadFile(filepath.Join("..","research","pilot-f4","frozen.json"))
 if err!=nil{t.Fatal(err)}
 p:=filepath.Join(t.TempDir(),"freeze.json")
 if err=os.WriteFile(p,b,0600);err!=nil{t.Fatal(err)}
 if _,err=LoadFrozen(p);err!=nil{t.Fatal(err)}
 if err=os.WriteFile(p,append(b,' '),0600);err!=nil{t.Fatal(err)}
 if _,err=LoadFrozen(p);err==nil{t.Fatal("changed prereg accepted")}
}
