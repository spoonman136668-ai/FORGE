// K4T-F5 original Wingless R4 source IPC; ephemeral feedback does NOT train.
// No substituted environment physics: only chosen action and actual observed
// public consequence enter episode memory, original learned R3 remains frozen.
package main

import(
 "bufio"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "os"
 r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
 r7 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r7"
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
 Steps uint32 `json:"steps,omitempty"`
 Error string `json:"error,omitempty"`
}
func main(){
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,4096),1024*1024)
 bw:=bufio.NewWriter(os.Stdout);defer bw.Flush()
 learner:=r7.New()
 for sc.Scan(){
  var r Request
  var out Reply
  if e:=json.Unmarshal(sc.Bytes(),&r);e!=nil{out.Error=e.Error()}else {
   switch r.Op{
   case "choose":
    a,e:=learner.Choose(r.Before)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Action=&a}
   case "feedback":
    e:=learner.Feedback(r.Before,r.Action,r.After)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.Core.Core.Core.Core.Events;out.Steps=learner.Core.Core.Core.Route.Steps}
   case "learn":
    e:=learner.ObserveFit(r.Before,r.Action,r.After,r.Reward,r.Terminal)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.Core.Core.Core.Core.Events}
   case "episode_start":
    e:=learner.BeginEpisode()
    if e!=nil{out.Error=e.Error()}else{out.OK=true}
   case "snapshot":
    b,e:=learner.Snapshot()
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.State=base64.StdEncoding.EncodeToString(b);out.Updates=learner.Core.Core.Core.Core.Events;out.Steps=learner.Core.Core.Core.Route.Steps}
   case "snapshot_base":
    b,e:=learner.Core.Core.Core.Core.Snapshot()
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.State=base64.StdEncoding.EncodeToString(b);out.Updates=learner.Core.Core.Core.Core.Events}
   case "load":
    b,e:=base64.StdEncoding.DecodeString(r.State)
    if e==nil{learner,e=r7.Restore(b)}
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.Core.Core.Core.Core.Events;out.Steps=learner.Core.Core.Core.Route.Steps}
   case "quit":out.OK=true
   default:out.Error="K4T_F6_INVALID_NATIVE_BRIDGE_OP"
   }
  }
  b,e:=json.Marshal(out);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=bw.Write(append(b,'\n'));e!=nil{os.Exit(2)}
  if e=bw.Flush();e!=nil{os.Exit(2)}
  if r.Op=="quit"{break}
 }
 if e:=sc.Err();e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
