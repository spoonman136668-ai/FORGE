package main
import(
 "bytes"
 "context"
 "testing"
)
func TestReadOnlyHistoryToolRequiresAuthenticatedGitHub(t *testing.T){
 var out bytes.Buffer
 if err:=run(context.Background(),"",&out);err==nil{t.Fatal("anonymous S14 history accepted")}
 if out.Len()>0{t.Fatal("failed source emitted a misleading report")}
}
