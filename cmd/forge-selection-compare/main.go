package main
import("encoding/json";"os";"fmt";"github.com/spoonman136668-ai/forge/evoportfolio")
func main(){
 var f evoportfolio.Frozen
 d:=json.NewDecoder(os.Stdin);d.DisallowUnknownFields()
 if d.Decode(&f)!=nil{os.Exit(2)}
 out,err:=evoportfolio.Select(f,evoportfolio.Digest(f));if err!=nil{os.Exit(3)}
 ids:=[]string{}
 for _,c:=range out.Finalists{ids=append(ids,c.ID)}
 b,_:=json.Marshal(ids);fmt.Println(string(b))
}
