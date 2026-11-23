package executionbridge
import(
 "context"
 "errors"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
type emptyWitness struct{failure bool}
func(w emptyWitness)LoadStarted(context.Context,string)(*workerreconcile.Signed,error){if w.failure{return nil,errors.New("transport lost")};return nil,nil}
func(w emptyWitness)LoadTerminal(context.Context,string)(*workerreconcile.Signed,error){return nil,nil}
func TestWorkerSilenceNeverAuthorizesOriginalReplay(t *testing.T){
 expected:=workerreconcile.Expected{Lane:"Wingless",OriginalRunID:"existing_original",OwnerEpoch:5}
 d,err:=ReconcileOriginal(context.Background(),emptyWitness{},"existing_original",expected)
 if err!=nil||d!=workerreconcile.Unknown{t.Fatal(d,err)}
 d,err=ReconcileOriginal(context.Background(),emptyWitness{failure:true},"existing_original",expected)
 if err==nil||d!=workerreconcile.Unknown{t.Fatal(d,err)}
 _,err=ReconcileOriginal(context.Background(),emptyWitness{},"unrelated",expected)
 if err==nil{t.Fatal("unrelated run accepted")}
 _=strings.Repeat("a",64)
}
