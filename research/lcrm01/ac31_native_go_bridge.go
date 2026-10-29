// AC31 exact original Farama source-only Go DK15 selected-policy JSONL bridge.
// Do not rewrite genuine mission, original native source or external selected actions.
package main
import (
 "bufio"
 "bytes"
 "encoding/base64"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 native "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk15"
 prior "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk13"
 boundary "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk14"
)
type Request struct {
 Op string `json:"op"`
 Before json.RawMessage `json:"before,omitempty"`
 After json.RawMessage `json:"after,omitempty"`
 Action int `json:"action,omitempty"`
 Reward float64 `json:"reward,omitempty"`
 Terminal bool `json:"terminal,omitempty"`
 Truncated bool `json:"truncated,omitempty"`
 State string `json:"state,omitempty"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 Status string `json:"status,omitempty"`
 Mode string `json:"mode,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Live uint64 `json:"live,omitempty"`
 State string `json:"state,omitempty"`
 Public *boundary.Public `json:"public,omitempty"`
 Error string `json:"error,omitempty"`
}
func strict(input []byte,out any)error{
 d:=json.NewDecoder(bytes.NewReader(input));d.DisallowUnknownFields()
 if e:=d.Decode(out);e!=nil{return e}
 if e:=d.Decode(new(any));e!=io.EOF{return errors.New("AC31_JSON_TRAILING_OR_FORGED")}
 return nil
}
func frame(raw json.RawMessage)(boundary.Public,error){
 if len(raw)==0{return boundary.Public{},errors.New("AC31_MISSING_SOURCE_PUBLIC")}
 return boundary.ReadPublic(raw)
}
func process(m **native.Actor,q Request)(Reply,bool){
 r:=Reply{}
 a:=*m
 var err error
 switch q.Op{
 case "learn":
  var b,c boundary.Public
  b,err=frame(q.Before)
  if err==nil{c,err=frame(q.After)}
  if err==nil{
   if b.Mission!=boundary.LegacyMission||c.Mission!=boundary.LegacyMission{
    err=errors.New("AC31_FIT_MUST_BE_ORIGINAL_DOORKEY")
   }else{
    err=a.Original.ObserveFit(prior.Public{Image:b.Image,Direction:b.Direction,Mission:b.Mission},
      q.Action,prior.Public{Image:c.Image,Direction:c.Direction,Mission:c.Mission},
      q.Reward,q.Terminal)
   }
  }
 case "snapshot_parent":
  var snapshot []byte
  snapshot,err=a.Original.Snapshot()
  if err==nil{r.State=base64.StdEncoding.EncodeToString(snapshot)}
 case "load_parent":
  var data []byte
  data,err=base64.StdEncoding.DecodeString(q.State)
  if err==nil{
   var old *prior.Policy
   old,err=prior.Restore(data)
   if err==nil{
    n:=native.New()
    n.Original=old
    *m=n;a=n
   }
  }
 case "begin":
  var b boundary.Public
  b,err=frame(q.Before)
  if err==nil{err=a.Begin(b)}
 case "choose":
  r.Action,r.Status,err=a.Choose()
 case "public_echo":
  var b boundary.Public
  b,err=frame(q.Before)
  if err==nil{r.Public=&b}
 case "commit":
  err=a.Commit(q.Action)
 case "feedback":
  var b boundary.Public
  b,err=frame(q.After)
  if err==nil{err=a.Feedback(q.Action,b,q.Reward,q.Terminal,q.Truncated)}
 case "snapshot":
  var data []byte
  if a.Mode==""{
   data,err=a.Original.Snapshot() // historical FIT-only bridge compatibility
  }else{
   data,err=a.Snapshot()
  }
  if err==nil{r.State=base64.StdEncoding.EncodeToString(data)}
 case "load":
  // ONLY a complete AC30 DK15 actor checkpoint. Never interpret the
  // new actor as an old DK13 fit-only checkpoint merely because the
  // receiving process was freshly constructed with Mode == "".
  var data []byte
  data,err=base64.StdEncoding.DecodeString(q.State)
  if err==nil{
   var next *native.Actor
   next,err=native.Restore(data)
   if err==nil{*m=next;a=next}
  }
 case "quit":
  r.OK=true
  return r,true
 default:
  err=errors.New("AC31_UNREGISTERED_GO_OPERATION")
 }
 if err!=nil{r.Error=err.Error();return r,false}
 r.OK=true
 r.Updates=a.Original.Samples
 if a.Boundary!=nil{r.Live=uint64(len(a.Boundary.Events))}
 r.Mode=a.Mode
 return r,false
}
func serve(in io.Reader,out io.Writer)error{
 scanner:=bufio.NewScanner(in);scanner.Buffer(make([]byte,4096),8<<20)
 writer:=bufio.NewWriter(out)
 m:=native.New()
 for scanner.Scan(){
  var q Request
  err:=strict(scanner.Bytes(),&q)
  var reply Reply;quit:=false
  if err!=nil{reply.Error=err.Error()}else{reply,quit=process(&m,q)}
  b,e:=json.Marshal(reply);if e!=nil{return e}
  if _,e=writer.Write(append(b,'\n'));e!=nil{return e}
  if e=writer.Flush();e!=nil{return e}
  if quit{return nil}
 }
 return scanner.Err()
}
func main(){if e:=serve(os.Stdin,os.Stdout);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
