// K4U read-only process bridge to ORIGINAL Wingless native source.
//
// Compiled in a disposable temp module with original, git-blob-authenticated
// Wingless policy.go. JSONL is IPC, not an alternate learning algorithm.
package main
import (
 "bufio"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "os"
 wing "k4u/wingless"
)
type Request struct {
 Op string `json:"op"`
 Before wing.PublicGrid `json:"before"`
 After wing.PublicGrid `json:"after"`
 Action int `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 State string `json:"state"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 State string `json:"state,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Error string `json:"error,omitempty"`
}
func main(){
 scanner:=bufio.NewScanner(os.Stdin)
 scanner.Buffer(make([]byte,4096),1024*1024)
 writer:=bufio.NewWriter(os.Stdout)
 defer writer.Flush()
 policy:=wing.New()
 for scanner.Scan(){
  var req Request
  var resp Reply
  if err:=json.Unmarshal(scanner.Bytes(),&req);err!=nil{
   resp.Error="BAD_JSON:"+err.Error()
  }else {
   switch req.Op{
   case "choose":
    a,e:=policy.Choose(req.Before)
    if e!=nil{resp.Error=e.Error()} else {resp.OK=true;resp.Action=&a}
   case "learn":
    e:=policy.Observe(req.Before,req.Action,req.After,req.Reward,req.Terminal)
    if e!=nil{resp.Error=e.Error()} else {resp.OK=true;resp.Updates=policy.Updates}
   case "snapshot":
    raw,e:=policy.Snapshot()
    if e!=nil{resp.Error=e.Error()}else {resp.OK=true;resp.State=base64.StdEncoding.EncodeToString(raw);resp.Updates=policy.Updates}
   case "load":
    raw,e:=base64.StdEncoding.DecodeString(req.State)
    if e==nil{policy,e=wing.Restore(raw)}
    if e!=nil{resp.Error=e.Error()}else{resp.OK=true;resp.Updates=policy.Updates}
   case "quit":
    resp.OK=true
   default:resp.Error="UNKNOWN_NATIVE_BRIDGE_COMMAND"
   }
  }
  b,e:=json.Marshal(resp)
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=writer.Write(append(b,'\n'));e!=nil{os.Exit(2)}
  if e=writer.Flush();e!=nil{os.Exit(2)}
  if req.Op=="quit" {break}
 }
 if err:=scanner.Err();err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
