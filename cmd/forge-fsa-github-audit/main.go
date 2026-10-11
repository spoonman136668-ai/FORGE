// forge-fsa-github-audit queries actual public GitHub protections read-only.
package main
import(
 "context"
 "encoding/json"
 "fmt"
 "os"
 "github.com/spoonman136668-ai/forge/fsagithubcustody"
)
func main(){
 client:=fsagithubcustody.HTTPClient()
 defer client.CloseIdleConnections()
 report,err:=fsagithubcustody.Audit(context.Background(),client)
 if err!=nil{fmt.Fprintln(os.Stderr,"FORGE_FSA_REMOTE_AUDIT=UNAVAILABLE fail_closed=true");os.Exit(1)}
 b,err:=json.Marshal(report);if err!=nil{os.Exit(1)}
 fmt.Println(string(b))
 if fsagithubcustody.DenyAuthority(report)==nil{os.Exit(2)}
 fmt.Println("FORGE_FSA_LIVE_AUDIT=OBSERVED scientific_execution_authorized=false")
}
