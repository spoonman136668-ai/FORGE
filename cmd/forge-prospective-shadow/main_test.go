package main
import (
 "bytes"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestR25ReadOnlySourceRequiresBothFiles(t *testing.T){
 var output bytes.Buffer
 for _,flags:=range [][]string{
  nil,{"--owner-evidence","."},{"--owner-evidence","x","--independent-pins","y"},
  {"--owner-evidence","/not-a-file","--independent-pins","/not-a-file"},
 }{
  output.Reset()
  if err:=run(flags,&output);err==nil||output.Len()!=0{
   t.Fatalf("missing owner/witness source emitted data: args=%v",flags)
  }
 }
}
func TestR25RejectsUntrustedFilesAndAliases(t *testing.T){
 dir:=t.TempDir()
 owner:=filepath.Join(dir,"owner.json")
 pins:=filepath.Join(dir,"pins.json")
 link:=filepath.Join(dir,"symlink.json")
 if err:=os.WriteFile(owner,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(pins,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 for _,flags:=range [][]string{
  {"--owner-evidence",owner,"--independent-pins",owner},
  {"--owner-evidence",owner,"--independent-pins",pins},
  {"--owner-evidence",dir,"--independent-pins",pins},
 }{
  var out bytes.Buffer
  if run(flags,&out)==nil||out.Len()!=0{
   t.Fatalf("unqualified source accepted: %v",flags)
  }
 }
 if err:=os.Symlink(owner,link);err==nil{
  var out bytes.Buffer
  if run([]string{"--owner-evidence",link,"--independent-pins",pins},&out)==nil||out.Len()!=0{
   t.Fatal("source symlink was followed")
  }
 }
}
func TestR25FailureDoesNotEchoRawPrivateEvidence(t *testing.T){
 dir:=t.TempDir()
 owner:=filepath.Join(dir,"owner.json")
 pins:=filepath.Join(dir,"pins.json")
 sensitive:="PRIVATE_OWNER_SOURCE_NEVER_PRINT"
 if err:=os.WriteFile(owner,[]byte(sensitive),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(pins,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 var out bytes.Buffer
 err:=run([]string{"--owner-evidence",owner,"--independent-pins",pins},&out)
 if err==nil||out.Len()>0||strings.Contains(err.Error(),sensitive){
  t.Fatal("incomplete real source leaked or became positive")
 }
}
