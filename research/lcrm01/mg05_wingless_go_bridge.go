// Research-only Go-to-original-Farama bridge. Native chooser is separately
// pinned Wingless DK8U. It does not implement any action policy here.
// DK7 native Go JSON IPC. Strict same original MiniGrid 7x7 public wire as
// Yggdrasil R10/R12; model is newly opt-in and NOT R8's sixfield policy.
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
 wing "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk7"
 exp "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk8"
)
type Request struct {
 Op string `json:"op"`
 Before json.RawMessage `json:"before,omitempty"`
 After json.RawMessage `json:"after,omitempty"`
 Action int `json:"action,omitempty"`
 Reward float64 `json:"reward,omitempty"`
 Terminal bool `json:"terminal,omitempty"`
 State string `json:"state,omitempty"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 Status string `json:"status,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Live uint64 `json:"live,omitempty"`
 State string `json:"state,omitempty"`
 Public *wing.Public `json:"public,omitempty"`
 Error string `json:"error,omitempty"`
}
func decodeRequest(raw []byte)(Request,error){
 var x Request
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e:=d.Decode(&x);e!=nil{return x,e}
 if e:=d.Decode(new(any));e!=io.EOF{return x,errors.New("DK7_REQUEST_TRAILING")}
 return x,nil
}
func decodePublic(raw json.RawMessage)(wing.Public,error){
 var x wing.Public
 if len(raw)==0{return x,errors.New("DK7_PUBLIC_REQUIRED")}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e:=d.Decode(&x);e!=nil{return x,e}
 if e:=d.Decode(new(any));e!=io.EOF{return x,errors.New("DK7_PUBLIC_TRAILING")}
 if e:=x.Valid();e!=nil{return x,e}
 return x,nil
}
func process(p **exp.Explorer,req Request)(Reply,bool){
 m:=*p
 r:=Reply{}
 var e error
 switch req.Op{
 case "public_echo":
  var before wing.Public
  before,e=decodePublic(req.Before)
  if e==nil{r.Public=&before}
 case "choose":
  var before wing.Public
  before,e=decodePublic(req.Before)
  if e==nil{r.Action,r.Status,e=m.Choose(before)}
 case "commit":
  var before wing.Public
  before,e=decodePublic(req.Before)
  if e==nil{e=m.Commit(before,req.Action)}
 case "feedback","learn":
  var before,after wing.Public
  before,e=decodePublic(req.Before)
  if e==nil{after,e=decodePublic(req.After)}
  if e==nil{
   if req.Op=="learn"{e=m.ObserveFit(before,req.Action,after,req.Reward,req.Terminal)
   }else{e=m.Feedback(before,req.Action,after,req.Reward,req.Terminal)}
  }
 case "begin_episode":
  e=m.BeginEpisode()
 case "snapshot":
  var b []byte
  b,e=m.Snapshot()
  if e==nil{r.State=base64.StdEncoding.EncodeToString(b)}
 case "load":
  var b []byte
  b,e=base64.StdEncoding.DecodeString(req.State)
  if e==nil{
   var candidate *exp.Explorer
   candidate,e=exp.Restore(b)
   if e==nil {*p=candidate;m=candidate}
  }
 case "quit":
  r.OK=true
  return r,true
 default:e=errors.New("DK7_UNSUPPORTED_SOURCE_OP")
 }
 if e!=nil{r.Error=e.Error();return r,false}
 r.OK=true
 r.Updates=m.Native.Samples
 r.Live=m.Native.Live
 return r,false
}
func serve(in io.Reader,out io.Writer)error{
 sc:=bufio.NewScanner(in);sc.Buffer(make([]byte,4096),8<<20)
 w:=bufio.NewWriter(out)
 p:=exp.New()
 for sc.Scan(){
  req,e:=decodeRequest(sc.Bytes())
  var r Reply;quit:=false
  if e!=nil{r.Error=e.Error()}else{r,quit=process(&p,req)}
  raw,e:=json.Marshal(r);if e!=nil{return e}
  if _,e=w.Write(append(raw,'\n'));e!=nil{return e}
  if e=w.Flush();e!=nil{return e}
  if quit{return nil}
 }
 return sc.Err()
}
func main(){
 if e:=serve(os.Stdin,os.Stdout);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
