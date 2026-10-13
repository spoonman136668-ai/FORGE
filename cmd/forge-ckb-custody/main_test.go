package main
import(
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestFirstUseInspectorRequiresExternallyPinnedHistory(t *testing.T){
 var out bytes.Buffer
 if err:=run(nil,&out);err==nil{t.Fatal("unpinned legacy state accepted")}
 if out.Len()>0{t.Fatal("failed inspection disclosed report")}
 dir:=t.TempDir()
 path:=filepath.Join(dir,"pins.json")
 doc:=pinsDocument{Schema:PinsSchema,SHA256:map[string]string{
 "S09":strings.Repeat("a",64),"S10":strings.Repeat("b",64),
 "S11":strings.Repeat("c",64),"S12":strings.Repeat("d",64),"S13":strings.Repeat("e",64)}}
 raw,err:=json.Marshal(doc);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(path,append(raw,'\n'),0600);err!=nil{t.Fatal(err)}
 if _,err=readPins(path);err!=nil{t.Fatal(err)}
 if err=run([]string{"--pinned",path,"--state",dir},&out);err==nil{
  t.Fatal("missing installed consumed ledgers accepted")
 }
 if err=os.WriteFile(path,append(raw,[]byte("{}")...),0600);err!=nil{t.Fatal(err)}
 if _,err=readPins(path);err==nil{t.Fatal("trailing custody JSON accepted")}
}
