// K4T-F2 IPC harness for *unaltered original* Wingless R3 learning source.
// Only completed MiniGrid public before/selected action/after/reward transitions.
// The "choose_core" command is a planning-off ablation, not another native learner.
package main
import(
 "bufio"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "os"
 r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
 r3 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r3"
)
type Request struct{
 Op string `json:"op"`
 Before r1.PublicGrid `json:"before"`
 After r1.PublicGrid `json:"after"`
 Action int `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 State string `json:"state"`
}
type Reply struct{
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 State string `json:"state,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Error string `json:"error,omitempty"`
}
func main(){
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,4096),1024*1024)
 bw:=bufio.NewWriter(os.Stdout);defer bw.Flush()
 learner:=r3.New()
 for sc.Scan(){
  var r Request
  var out Reply
  if e:=json.Unmarshal(sc.Bytes(),&r);e!=nil{out.Error=e.Error()}else {
   switch r.Op{
   case "choose":
    a,e:=learner.Choose(r.Before)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Action=&a}
   case "choose_core":
    // Same trained R3 checkpoint, ablate ONLY the R3 action-model planner.
    a,e:=learner.Core.Choose(r.Before)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Action=&a}
   case "learn":
    e:=learner.Observe(r.Before,r.Action,r.After,r.Reward,r.Terminal)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.Events}
   case "snapshot":
    b,e:=learner.Snapshot()
    if e!=nil{out.Error=e.Error()}else{
     out.OK=true;out.State=base64.StdEncoding.EncodeToString(b);out.Updates=learner.Events
    }
   case "load":
    b,e:=base64.StdEncoding.DecodeString(r.State)
    if e==nil{learner,e=r3.Restore(b)}
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.Events}
   case "quit":out.OK=true
   default:out.Error="K4T_F2_INVALID_NATIVE_TRANSPORT_OP"
   }
  }
  b,e:=json.Marshal(out);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=bw.Write(append(b,'\n'));e!=nil{os.Exit(2)}
  if e=bw.Flush();e!=nil{os.Exit(2)}
  if r.Op=="quit"{break}
 }
 if e:=sc.Err();e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
