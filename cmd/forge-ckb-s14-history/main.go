// forge-ckb-s14-history reads exactly the original CKB S14 workflow and
// issuer artifact listings. It cannot retry, dispatch or authorize science.
package main
import(
 "context"
 "encoding/json"
 "fmt"
 "io"
 "os"
 "time"
 "github.com/spoonman136668-ai/forge/ckbhistory"
)
func run(ctx context.Context,token string,out io.Writer)error{
 c,err:=ckbhistory.New(token)
 if err!=nil{return err}
 report,err:=c.InspectS14(ctx)
 if err!=nil{return err}
 return json.NewEncoder(out).Encode(report)
}
func main(){
 ctx,cancel:=context.WithTimeout(context.Background(),50*time.Second)
 defer cancel()
 if err:=run(ctx,os.Getenv("GH_TOKEN"),os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_CKB_S14_ORIGINAL_HISTORY_UNVERIFIED_NO_REPLAY")
  os.Exit(1)
 }
}
