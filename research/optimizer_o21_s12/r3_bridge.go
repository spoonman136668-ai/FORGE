// O21-S12 source-only IPC bridge to UNMODIFIED original Wingless native R3.
// No simulator, source action, learning algorithm, hidden goal, or evaluation here.
package main

import (
 "bufio"
 "bytes"
 "encoding/base64"
 "encoding/json"
 "fmt"
 "io"
 "os"

 r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
 r3 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r3"
)

type Request struct {
 Op string `json:"op"`
 Before r1.PublicGrid `json:"before"`
 After r1.PublicGrid `json:"after"`
 Action int `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 State string `json:"state"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 State string `json:"state,omitempty"`
 Updates uint64 `json:"updates"`
 Predicted *r1.PublicGrid `json:"predicted,omitempty"`
 Reliable *bool `json:"reliable,omitempty"`
 Error string `json:"error,omitempty"`
}
func decode(raw []byte)(Request,error){
 var v Request
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 if e:=d.Decode(&v);e!=nil{return v,e}
 if e:=d.Decode(new(struct{}));e!=io.EOF{
  if e==nil{return v,fmt.Errorf("R3_BRIDGE_MULTIPLE_JSON_VALUES")}
  return v,e
 }
 return v,nil
}
func serve(r Request,p **r3.Policy) Reply {
 out:=Reply{}
 switch r.Op {
 case "choose":
  a,e:=(*p).Choose(r.Before)
  if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Action=&a;out.Updates=(*p).Events}
 case "learn":
  e:=(*p).Observe(r.Before,r.Action,r.After,r.Reward,r.Terminal)
  if e!=nil{out.Error=e.Error()}else{out.OK=true;out.Updates=(*p).Events}
 case "predict":
  s,ok,e:=(*p).Predict(r.Before,r.Action)
  if e!=nil{out.Error=e.Error()}else{
   out.OK=true;out.Reliable=&ok;out.Updates=(*p).Events
   if ok{out.Predicted=&s}
  }
 case "snapshot":
  raw,e:=(*p).Snapshot()
  if e!=nil{out.Error=e.Error()}else{
   out.OK=true;out.State=base64.StdEncoding.EncodeToString(raw)
   out.Updates=(*p).Events
  }
 case "load":
  raw,e:=base64.StdEncoding.DecodeString(r.State)
  if e!=nil{out.Error=e.Error();break}
  candidate,e:=r3.Restore(raw)
  if e!=nil{out.Error=e.Error()}else{
   // Never replace the live policy on a rejected or unauthenticated checkpoint.
   *p=candidate;out.OK=true;out.Updates=candidate.Events
  }
 case "quit":
  out.OK=true;out.Updates=(*p).Events
 default:
  out.Error="R3_UNKNOWN_OR_UNAUTHORIZED_TRANSPORT_OP"
 }
 return out
}
func main(){
 scanner:=bufio.NewScanner(os.Stdin)
 scanner.Buffer(make([]byte,4096),1024*1024)
 writer:=bufio.NewWriter(os.Stdout)
 defer writer.Flush()
 model:=r3.New()
 for scanner.Scan(){
  req,e:=decode(scanner.Bytes())
  reply:=Reply{}
  if e!=nil{reply.Error="R3_INVALID_JSON_REQUEST:"+e.Error()}else{
   reply=serve(req,&model)
  }
  encoded,e:=json.Marshal(reply)
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=writer.Write(append(encoded,'\n'));e!=nil{os.Exit(2)}
  if e=writer.Flush();e!=nil{os.Exit(2)}
  if reply.OK&&req.Op=="quit"{break}
 }
 if e:=scanner.Err();e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
