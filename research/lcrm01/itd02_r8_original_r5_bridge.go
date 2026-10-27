// Native R5 source IPC for FIT training and future intact selected-action episodes.
// This bridge imports pinned original R5; no action override capability.
package main
import (
 "bufio"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "os"
 r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
 r5 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r5"
)
type request struct {
 Op string `json:"op"`
 Before r1.PublicGrid `json:"before"`
 After r1.PublicGrid `json:"after"`
 Action int `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 State string `json:"state"`
}
type reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 State string `json:"state,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Steps uint32 `json:"steps,omitempty"`
 Error string `json:"error,omitempty"`
}
func main() {
 scanner:=bufio.NewScanner(os.Stdin);scanner.Buffer(make([]byte,4096),8*1024*1024)
 writer:=bufio.NewWriter(os.Stdout);defer writer.Flush()
 learner:=r5.New()
 var updates uint64
 var steps uint32
 for scanner.Scan() {
  var req request
  var out reply
  if e:=json.Unmarshal(scanner.Bytes(),&req);e!=nil {out.Error=e.Error()} else {
   switch req.Op {
   case "learn":
    if e:=learner.ObserveFit(req.Before,req.Action,req.After,req.Reward,req.Terminal);e!=nil {
     out.Error=e.Error()
    } else {updates++;out.OK=true;out.Updates=updates}
   case "episode_start":
    if e:=learner.BeginEpisode();e!=nil {out.Error=e.Error()} else {steps=0;out.OK=true}
   case "choose":
    action,e:=learner.Choose(req.Before)
    if e!=nil {out.Error=e.Error()} else {out.OK=true;out.Action=&action}
   case "feedback":
    if e:=learner.Feedback(req.Before,req.Action,req.After);e!=nil {
     out.Error=e.Error()
    } else {steps++;out.OK=true;out.Steps=steps}
   case "snapshot":
    bytes,e:=learner.Snapshot()
    if e!=nil {out.Error=e.Error()} else {
     out.OK=true;out.State=base64.StdEncoding.EncodeToString(bytes);out.Updates=updates;out.Steps=steps
    }
   case "load":
    bytes,e:=base64.StdEncoding.DecodeString(req.State)
    if e==nil {var restored *r5.Policy;restored,e=r5.Restore(bytes);if e==nil {learner=restored;steps=0}}
    if e!=nil {out.Error=e.Error()} else {out.OK=true}
   case "quit":
    out.OK=true
   default:out.Error="ITD02_R5_UNRECOGNIZED_OP"
   }
  }
  raw,e:=json.Marshal(out);if e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=writer.Write(append(raw,'\n'));e!=nil {os.Exit(2)}
  if e=writer.Flush();e!=nil {os.Exit(2)}
  if req.Op=="quit" {break}
 }
 if e:=scanner.Err();e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
