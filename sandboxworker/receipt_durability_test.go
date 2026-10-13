package sandboxworker

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "testing"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)

// Local signed-receipt persistence is write-once; the caller cannot
// reinterpret an ambiguous receipt write as fresh scientific capacity.
func TestSyntheticSignedReceiptWriteOnceAndReadback(t *testing.T) {
 root:=t.TempDir()
 first:=workerreconcile.Signed{Receipt:workerreconcile.Receipt{
  Schema:workerreconcile.Schema,Lane:"Wingless",Stage:"STARTED",
 }}
 if err:=writeExclusive(root,"start-evidence.json",first);err!=nil{t.Fatal(err)}
 got,err:=os.ReadFile(filepath.Join(root,"start-evidence.json"))
 if err!=nil{t.Fatal(err)}
 expected,err:=json.Marshal(first)
 if err!=nil{t.Fatal(err)}
 expected=append(expected,'\n')
 if !bytes.Equal(got,expected){t.Fatal("first write not exact canonical receipt")}
 second:=first
 second.Receipt.Stage="TERMINAL"
 if err:=writeExclusive(root,"start-evidence.json",second);err==nil{
  t.Fatal("write-once receipt was overwritten")
 }
 after,err:=os.ReadFile(filepath.Join(root,"start-evidence.json"))
 if err!=nil||!bytes.Equal(after,got){t.Fatal("failed second write changed first custody",err)}
}
