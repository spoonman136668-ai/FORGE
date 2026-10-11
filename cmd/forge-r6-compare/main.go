package main
import("crypto/sha256";"encoding/hex";"encoding/json";"fmt";"os";"github.com/spoonman136668-ai/forge/evoportfolio")
type Packet struct{Frozen evoportfolio.Frozen `json:"frozen"`; Groups [][]int `json:"groups"`}
func main(){
 var p Packet
 if json.NewDecoder(os.Stdin).Decode(&p)!=nil{os.Exit(2)}
 pin:=evoportfolio.Digest(p.Frozen)
 batches:=[]evoportfolio.Batch{}
 for _,group:=range p.Groups{
  b:=evoportfolio.Batch{Lane:p.Frozen.Lane,FrozenSHA256:pin,Candidates:[]evoportfolio.Candidate{}}
  for _,idx:=range group{if idx<0||idx>=len(p.Frozen.Candidates){os.Exit(3)};b.Candidates=append(b.Candidates,p.Frozen.Candidates[idx])}
  raw,_:=json.Marshal(b);sum:=sha256.Sum256(raw);b.BatchSHA256=hex.EncodeToString(sum[:]);batches=append(batches,b)
 }
 d,err:=evoportfolio.SelectBatches(p.Frozen,pin,batches);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 ids:=[]string{};for _,c:=range d.Finalists{ids=append(ids,c.ID)}
 out,_:=json.Marshal(struct{IDs []string `json:"ids"`;Spent int64 `json:"spent"`;Reserved int64 `json:"reserved"`}{ids,d.ScreenComputeSpent,d.SealedComputeReserved});fmt.Println(string(out))
}