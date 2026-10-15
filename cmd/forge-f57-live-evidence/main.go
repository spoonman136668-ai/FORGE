// forge-f57-live-evidence records public, pinned TRAIN metadata only.
package main
import(
 "context"
 "encoding/json"
 "fmt"
 "net/http"
 "os"
 "time"
 "github.com/spoonman136668-ai/forge/liveevidence"
)
func main(){
 if len(os.Args)!=1{fmt.Fprintln(os.Stderr,"FORGE_F57_NO_ARGUMENTS_ALLOWED");os.Exit(2)}
 client:=&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
 ctx,cancel:=context.WithTimeout(context.Background(),110*time.Second)
 defer cancel()
 report,err:=liveevidence.Observe(ctx,client,os.Getenv("GITHUB_TOKEN"))
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(report);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
