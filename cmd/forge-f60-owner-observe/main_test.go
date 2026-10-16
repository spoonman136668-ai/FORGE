package main
import (
 "errors"
 "os"
 "path/filepath"
 "testing"
)
func TestF60RealOwnerInputsAreMandatory(t *testing.T){
 if !errors.Is(observe(nil),errInput){t.Fatal("missing real source accepted")}
 if !errors.Is(observe([]string{"--observation-out",filepath.Join(t.TempDir(),"fake.json")}),errInput){
  t.Fatal("fake pre-created output accepted")
 }
}
func TestF60DoesNotOverwriteProspectiveObservationOrInput(t *testing.T){
 root:=t.TempDir()
 path:=filepath.Join(root,"source.json")
 if err:=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 flags:=[]string{
  "--wingless-evidence",path,
  "--yggdrasil-evidence",path,
  "--signed-export",path,
  "--independent-anchor",path,
  "--independent-lane-pins",path,
  "--wingless-selection-audit",path,
  "--yggdrasil-selection-audit",path,
  "--independent-audit-pins",path,
  "--observation-out",path,
 }
 if !errors.Is(observe(flags),errInput){t.Fatal("aliasing shadow inputs accepted")}
 got,err:=os.ReadFile(path)
 if err!=nil||string(got)!="{}"{t.Fatal("F60 CLI changed existing data")}
}
func TestF60RejectsRelativeEvidenceAndSymlinks(t *testing.T){
 root:=t.TempDir()
 path:=filepath.Join(root,"original.json")
 if err:=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 link:=filepath.Join(root,"alias.json")
 if err:=os.Symlink(path,link);err!=nil{t.Fatal(err)}
 if _,err:=readExisting(link,4096);!errors.Is(err,errInput){t.Fatal("symlink accepted")}
 if _,err:=readExisting("relative.json",4096);!errors.Is(err,errInput){t.Fatal("relative accepted")}
}
