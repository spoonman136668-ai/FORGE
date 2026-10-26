// ITD-02 R8 original Wingless source IPC; actual FIT and selected feedback train native R8.
// No substituted environment physics: only chosen action and actual observed
// public consequence enter episode memory, the original R5 source learning and legal selected-action custody remain authoritative.
package main

import(
 "bufio"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "os"
 r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
 r8 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r8"
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
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,4096),8*1024*1024)
 bw:=bufio.NewWriter(os.Stdout);defer bw.Flush()
 learner:=r8.New()
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
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.FitSeen;out.Steps=learner.EpisodeSteps}
   case "learn":
    e:=learner.ObserveFit(r.Before,r.Action,r.After,r.Reward,r.Terminal)
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.FitSeen}
   case "episode_start":
    e:=learner.BeginEpisode()
    if e!=nil{out.Error=e.Error()}else{out.OK=true}
   case "snapshot":
    b,e:=learner.Snapshot()
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.State=base64.StdEncoding.EncodeToString(b);out.Updates=learner.FitSeen;out.Steps=learner.EpisodeSteps}
   case "snapshot_base":
    b,e:=learner.Core.Core.Core.Snapshot()
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.State=base64.StdEncoding.EncodeToString(b);out.Updates=learner.FitSeen}
   case "load":
    b,e:=base64.StdEncoding.DecodeString(r.State)
    if e==nil{var restored *r8.Policy; restored,e=r8.Restore(b);if e==nil{learner=restored}}
    if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=learner.FitSeen;out.Steps=learner.EpisodeSteps}
   case "quit":out.OK=true
   default:out.Error="ITD02_R8_INVALID_NATIVE_BRIDGE_OP"
   }
  }
  b,e:=json.Marshal(out);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=bw.Write(append(b,'\n'));e!=nil{os.Exit(2)}
  if e=bw.Flush();e!=nil{os.Exit(2)}
  if r.Op=="quit"{break}
 }
 if e:=sc.Err();e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
