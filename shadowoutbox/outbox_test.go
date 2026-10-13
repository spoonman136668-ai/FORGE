package shadowoutbox
import("os";"path/filepath";"strings";"testing")
func fixture()Entry{return Entry{Schema:Schema,Lane:"Wingless",OriginalID:"existing_1",IncidentSHA256:strings.Repeat("a",64),RecoveryManifestSHA256:strings.Repeat("b",64),Scope:"bounded_config",RequiresRequalification:true}}
func TestShadowOutboxRestartSafeIdempotence(t *testing.T){
 dir:=t.TempDir();e:=fixture()
 first,err:=Enqueue(dir,e);if err!=nil{t.Fatal(err)}
 second,err:=Enqueue(dir,e);if err!=nil||first!=second{t.Fatal(second,err)}
 entries,err:=Load(dir);if err!=nil||len(entries)!=1||entries[0]!=e{t.Fatal(entries,err)}
 e.FirstUseRisk=true
 if _,err:=Enqueue(dir,e);err==nil{t.Fatal("first-use risk allowed")}
}
func TestShadowOutboxTamperAndUnknownFileFailClosed(t *testing.T){
 dir:=t.TempDir();e:=fixture()
 id,err:=Enqueue(dir,e);if err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(dir,id+".json"),[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Load(dir);err==nil{t.Fatal("tampered entry accepted")}
 if _,err:=Enqueue(dir,e);err==nil{t.Fatal("silently repaired tampered entry")}
}
func TestShadowOutboxRejectsUnexpectedLane(t *testing.T){
 e:=fixture();e.Lane="FORGE-NEW-WINGLESS"
 if _,err:=Enqueue(t.TempDir(),e);err==nil{t.Fatal("replacement lane accepted")}
}
