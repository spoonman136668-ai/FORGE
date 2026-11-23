package main
import(
 "bytes"
 "context"
 "testing"
 "strings"
 "errors"
)
func TestReadOnlyHistoryToolRequiresAuthenticatedGitHub(t *testing.T){
 var out bytes.Buffer
 if err:=run(context.Background(),"",&out);err==nil{t.Fatal("anonymous S14 history accepted")}
 if out.Len()>0{t.Fatal("failed source emitted a misleading report")}
}

func TestRetiredHistoryCLIAlwaysDeniesEvenWithToken(t *testing.T) {
    for _,token:=range []string{"", "synthetic-credential-not-a-real-token", "ghs_"+strings.Repeat("x",40)} {
        var out bytes.Buffer
        err:=run(context.Background(),token,&out)
        if !errors.Is(err,errRetired) {
            t.Fatalf("legacy cross-system command must stay retired: %v",err)
        }
        if out.Len()!=0 {
            t.Fatal("retired command emitted misleading upstream evidence")
        }
    }
}
