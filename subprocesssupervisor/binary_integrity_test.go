package subprocesssupervisor
import (
 "os"
 "path/filepath"
 "testing"
)
func TestDigestRefusesEmptyAndOversizedBinary(t *testing.T) {
 root:=t.TempDir()
 path:=filepath.Join(root,"worker")
 if err:=os.WriteFile(path,nil,0700);err!=nil{t.Fatal(err)}
 if _,err:=digestFile(path);err==nil{t.Fatal("empty worker admitted")}
 f,err:=os.OpenFile(path,os.O_WRONLY,0600);if err!=nil{t.Fatal(err)}
 if err:=f.Truncate((128<<20)+1);err!=nil{t.Fatal(err)}
 if err:=f.Close();err!=nil{t.Fatal(err)}
 if _,err:=digestFile(path);err==nil{t.Fatal("oversized worker admitted using truncated hash")}
}
