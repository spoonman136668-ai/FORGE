package main
import("encoding/json";"fmt";"os";"github.com/spoonman136668-ai/forge/evoportfolio")
func main(){
 var r evoportfolio.R7SourceReceipt
 if json.NewDecoder(os.Stdin).Decode(&r)!=nil{os.Exit(2)}
 if evoportfolio.ValidateR7ArchivedSource(r)!=nil{fmt.Println("REJECT");return}
 fmt.Println("ADVISORY_ONLY")
}