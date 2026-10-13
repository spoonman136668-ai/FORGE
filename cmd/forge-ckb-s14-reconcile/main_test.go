package main
import(
 "bytes"
 "context"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestDualSourceRequiresCompleteAuthenticatedInput(t *testing.T){
 var out bytes.Buffer
 if e:=run(context.Background(),nil,&out,"");e==nil{t.Fatal("missing pins and CKB state accepted")}
 if out.Len()!=0{t.Fatal("failed gate emitted candidate")}
 path:=filepath.Join(t.TempDir(),"pins.json")
 pins:=pinsFile{Schema:pinsSchema,SHA256:map[string]string{
  "S09":strings.Repeat("a",64),"S10":strings.Repeat("b",64),
  "S11":strings.Repeat("c",64),"S12":strings.Repeat("d",64),
  "S13":strings.Repeat("e",64),"S14":strings.Repeat("f",64)}}
 b,e:=json.Marshal(pins);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Fatal(e)}
 if _,e=readPins(path);e!=nil{t.Fatal(e)}
 if e=run(context.Background(),[]string{"--state",t.TempDir(),"--pinned",path},&out,"");e==nil{
  t.Fatal("unauthenticated remote client allowed")
 }
 if e=os.WriteFile(path,append(b,[]byte("{}")...),0600);e!=nil{t.Fatal(e)}
 if _,e=readPins(path);e==nil{t.Fatal("trailing JSON accepted")}
}
