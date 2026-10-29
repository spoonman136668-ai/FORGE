// MG20 quarantined engineering bridge for independent MG19 Wingless candidate.
// Keeps original environment mission unmodified; no action oracle or fallback.
package main
import(
 "bufio"
 "bytes"
 "encoding/base64"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 native "github.com/spoonman136668-ai/Wingless/research/native/itd02/mg19"
)
type Request struct{
 Op string `json:"op"`
 Before json.RawMessage `json:"before,omitempty"`
 After json.RawMessage `json:"after,omitempty"`
 Action int `json:"action,omitempty"`
 Reward float64 `json:"reward,omitempty"`
 Terminal bool `json:"terminal,omitempty"`
 State string `json:"state,omitempty"`
}
type Reply struct{
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 Status string `json:"status,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 State string `json:"state,omitempty"`
 Error string `json:"error,omitempty"`
}
func strict(raw []byte,out any)error{
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e:=d.Decode(out);e!=nil{return e}
 if d.Decode(new(any))!=io.EOF{return errors.New("MG20_TRAILING_JSON")}
 return nil
}
func original(raw json.RawMessage)(native.Public,error){
 var p native.Public
 if len(raw)==0{return p,errors.New("MG20_MISSING_SOURCE_PUBLIC")}
 if e:=strict(raw,&p);e!=nil{return p,e}
 // Validate source image/direction without projecting the delivered mission.
 v:=p;v.Mission="use the key to open the door and then get to the goal"
 if e:=v.Valid();e!=nil{return p,e}
 return p,nil
}
func process(model **native.Model,q Request)(Reply,bool){
 var r Reply;m:=*model;var e error
 switch q.Op{
 case "begin_episode":e=m.BeginEpisode()
 case "choose":
  var b native.Public;b,e=original(q.Before)
  if e==nil{r.Action,r.Status,e=m.Choose(b)}
 case "commit":
  var b native.Public;b,e=original(q.Before)
  if e==nil{e=m.Commit(b,q.Action)}
 case "feedback":
  var b,n native.Public;b,e=original(q.Before)
  if e==nil{n,e=original(q.After)}
  if e==nil{e=m.Feedback(b,q.Action,n,q.Reward,q.Terminal)}
 case "snapshot":
  var raw []byte;raw,e=m.Snapshot()
  if e==nil{r.State=base64.StdEncoding.EncodeToString(raw)}
 case "load":
  var raw []byte;raw,e=base64.StdEncoding.DecodeString(q.State)
  if e==nil{var next *native.Model;next,e=native.Restore(raw);if e==nil{*model=next;m=next}}
 case "quit":r.OK=true;return r,true
 default:e=errors.New("MG20_UNSUPPORTED_BRIDGE_OP")
 }
 if e!=nil{r.Error=e.Error();return r,false}
 r.OK=true;r.Updates=m.Parent.Agent.Samples
 return r,false
}
func serve(in io.Reader,out io.Writer)error{
 scanner:=bufio.NewScanner(in);scanner.Buffer(make([]byte,4096),8<<20)
 writer:=bufio.NewWriter(out)
 model:=native.New()
 for scanner.Scan(){
  var q Request;var r Reply;done:=false
  if e:=strict(scanner.Bytes(),&q);e!=nil{r.Error=e.Error()
  }else{r,done=process(&model,q)}
  raw,e:=json.Marshal(r);if e!=nil{return e}
  if _,e=writer.Write(append(raw,'\n'));e!=nil{return e}
  if e=writer.Flush();e!=nil{return e}
  if done{return nil}
 }
 return scanner.Err()
}
func main(){if e:=serve(os.Stdin,os.Stdout);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
