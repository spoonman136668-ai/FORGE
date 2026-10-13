package recoverycoordinator
import (
 "context"
 "testing"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
type silent struct{}
func(silent)LoadStarted(context.Context,string)(*workerreconcile.Signed,error){return nil,nil}
func(silent)LoadTerminal(context.Context,string)(*workerreconcile.Signed,error){return nil,nil}
func TestSilentOriginalNeverBecomesNewDispatch(t *testing.T){
 r:=Request{Expected:workerreconcile.Expected{Lane:"Wingless",OriginalRunID:"existing_original",OwnerEpoch:11}}
 d,err:=Evaluate(context.Background(),Dependencies{Receipts:silent{}},r)
 if err!=nil||d!=Quarantine{t.Fatal(d,err)}
 r.Expected.Lane="NEW_WINGLESS"
 if _,err:=Evaluate(context.Background(),Dependencies{Receipts:silent{}},r);err==nil{t.Fatal("replacement lane accepted")}
}
