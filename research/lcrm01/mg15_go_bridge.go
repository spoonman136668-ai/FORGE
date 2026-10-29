// Independent source-only DK14 Go public 7-action observable effect JSONL IPC.
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
 native "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk14"
)
type Request struct {
 Op string `json:"op"`
 Before json.RawMessage `json:"before,omitempty"`
 After json.RawMessage `json:"after,omitempty"`
 Action int `json:"action,omitempty"`
 Reward float64 `json:"reward,omitempty"`
 Terminal bool `json:"terminal,omitempty"`
 Objective string `json:"objective,omitempty"`
 State string `json:"state,omitempty"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 Status string `json:"status,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 Live uint64 `json:"live,omitempty"`
 State string `json:"state,omitempty"`
 Public *native.Public `json:"public,omitempty"`
 Error string `json:"error,omitempty"`
}
func strict(in []byte, v any)error{
 d:=json.NewDecoder(bytes.NewReader(in));d.DisallowUnknownFields()
 if e:=d.Decode(v);e!=nil{return e}
 if e:=d.Decode(new(any));e!=io.EOF{return errors.New("DK8_TRAILING_JSON")}
 return nil
}
func public(input json.RawMessage)(native.Public,error){
 var p native.Public
 if len(input)==0{return p,errors.New("DK8_PUBLIC_REQUIRED")}
 if e:=strict(input,&p);e!=nil{return p,e}
 if p.Mission!=native.DoorKey&&p.Mission!=native.GoalOnly{
  return p,errors.New("MG15_BRIDGE_UNREGISTERED_REAL_ORIGINAL_MISSION")
 }
 checked:=p;checked.Mission=native.DoorKey
 return p,checked.Valid()
}
func process(p **native.Policy,request Request)(Reply,bool){
 r:=Reply{};m:=*p
 var err error
 switch request.Op{
 case "choose":
  var b native.Public;b,err=public(request.Before)
  if err==nil{r.Action,r.Status,err=m.Choose(b)}
 case "public_echo":
  var b native.Public;b,err=public(request.Before)
  if err==nil{r.Public=&b}
 case "begin_episode":
  err=m.BeginEpisode()
 case "commit":
  var b native.Public;b,err=public(request.Before)
  if err==nil{err=m.Commit(b,request.Action)}
 case "learn","feedback":
  var b,a native.Public
  b,err=public(request.Before)
  if err==nil{a,err=public(request.After)}
  if err==nil{
   if request.Op=="learn"{err=m.ObserveFit(b,request.Action,a,request.Reward,request.Terminal)
   }else{err=m.Feedback(b,request.Action,a,request.Reward,request.Terminal)}
  }
 case "snapshot":
  var data []byte;data,err=m.Snapshot()
  if err==nil{r.State=base64.StdEncoding.EncodeToString(data)}
 case "load":
  var data []byte;data,err=base64.StdEncoding.DecodeString(request.State)
  if err==nil{
   var next *native.Policy
   next,err=native.Restore(data)
   if err==nil{*p=next;m=next}
  }
 case "quit":
  r.OK=true;return r,true
 default:err=errors.New("DK8_UNSUPPORTED_OPERATION")
 }
 if err!=nil{r.Error=err.Error();return r,false}
 r.OK=true;r.Updates=m.Samples;r.Live=m.Agent.Live
 return r,false
}
func serve(in io.Reader,out io.Writer)error{
 scanner:=bufio.NewScanner(in);scanner.Buffer(make([]byte,4096),8<<20)
 writer:=bufio.NewWriter(out)
 m:=native.New()
 for scanner.Scan(){
  var request Request
  err:=strict(scanner.Bytes(),&request)
  var result Reply;exit:=false
  if err!=nil{result.Error=err.Error()}else{result,exit=process(&m,request)}
  data,err:=json.Marshal(result);if err!=nil{return err}
  if _,err=writer.Write(append(data,'\n'));err!=nil{return err}
  if err=writer.Flush();err!=nil{return err}
  if exit{return nil}
 }
 return scanner.Err()
}
func main(){if e:=serve(os.Stdin,os.Stdout);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
