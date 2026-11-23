package main
import("encoding/json";"fmt";"os";"github.com/spoonman136668-ai/forge/evoportfolio")
func main(){
 var rows []evoportfolio.ProgressState
 d:=json.NewDecoder(os.Stdin);d.DisallowUnknownFields()
 if d.Decode(&rows)!=nil{os.Exit(2)}
 result,err:=evoportfolio.R196Disposition(rows)
 if err!=nil{os.Exit(3)}
 fmt.Println(result)
}
