// MG01: the ORIGINAL independently authored Wingless Go R1 policy is imported
// unchanged. This program adds an authenticated public-only IPC/echo boundary.
// It does NOT emulate the learner, read world truth or share Yggdrasil state.
package main

import (
 "bufio"
 "bytes"
 "encoding/base64"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 wing "mg01/wingless"
)

type Request struct {
 Op string `json:"op"`
 Before json.RawMessage `json:"before"`
 After json.RawMessage `json:"after"`
 Action int `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 State string `json:"state"`
}
type Reply struct {
 OK bool `json:"ok"`
 Action *int `json:"action,omitempty"`
 Public *wing.PublicGrid `json:"public,omitempty"`
 Updates uint64 `json:"updates,omitempty"`
 State string `json:"state,omitempty"`
 Error string `json:"error,omitempty"`
}
func exactPublic(raw json.RawMessage)(wing.PublicGrid,error){
 var g wing.PublicGrid
 var fields map[string]json.RawMessage
 if len(raw)==0 || !json.Valid(raw) {return g,errors.New("MG01_PUBLIC_JSON_INVALID")}
 if err:=json.Unmarshal(raw,&fields);err!=nil{return g,err}
 required:=[]string{"x","y","goal_x","goal_y","direction","front_blocked"}
 if len(fields)!=len(required){return g,errors.New("MG01_PUBLIC_WIRE_FIELD_COUNT")}
 for _,k:=range required {
  if _,ok:=fields[k];!ok{return g,errors.New("MG01_PUBLIC_WIRE_MISSING_"+k)}
 }
 for _,k:=range []string{"x","y","goal_x","goal_y","direction"} {
  var i int
  if e:=json.Unmarshal(fields[k],&i);e!=nil{return g,errors.New("MG01_NONINT_"+k)}
  if i<0 || i>64{return g,errors.New("MG01_PUBLIC_OUT_OF_BOUNDS_"+k)}
 }
 var blocked bool
 if e:=json.Unmarshal(fields["front_blocked"],&blocked);e!=nil{
  return g,errors.New("MG01_PUBLIC_BLOCKED_NOT_BOOL")
 }
 if e:=json.Unmarshal(raw,&g);e!=nil{return g,e}
 // Mandatory exact lossless round-trip catches Go field/tag drift.
 canonical,e:=json.Marshal(g)
 if e!=nil{return g,e}
 var again map[string]json.RawMessage
 if e=json.Unmarshal(canonical,&again);e!=nil{return g,e}
 for _,k:=range required{
  if !bytes.Equal(bytes.TrimSpace(fields[k]),bytes.TrimSpace(again[k])){
   return g,errors.New("MG01_PUBLIC_GO_FIELD_LOSS_"+k)
  }
 }
 if g.Direction<0 || g.Direction>3{return g,errors.New("MG01_INVALID_ORIENTATION")}
 return g,nil
}
func main(){
 scanner:=bufio.NewScanner(os.Stdin)
 scanner.Buffer(make([]byte,4096),1024*1024)
 out:=bufio.NewWriter(os.Stdout)
 defer out.Flush()
 policy:=wing.New()
 for scanner.Scan() {
  var req Request
  var reply Reply
  dec:=json.NewDecoder(bytes.NewReader(scanner.Bytes()))
  dec.DisallowUnknownFields()
  err:=dec.Decode(&req)
  if err!=nil {reply.Error="MG01_BAD_REQUEST:"+err.Error()} else {
   switch req.Op{
   case "public_echo","choose","learn":
    before,e:=exactPublic(req.Before)
    if e!=nil{reply.Error=e.Error();break}
    if req.Op=="public_echo"{reply.OK=true;reply.Public=&before;break}
    if req.Op=="choose"{
     a,e:=policy.Choose(before)
     if e!=nil{reply.Error=e.Error()}else{reply.OK=true;reply.Action=&a;reply.Updates=policy.Updates}
     break
    }
    after,e:=exactPublic(req.After)
    if e!=nil{reply.Error=e.Error();break}
    e=policy.Observe(before,req.Action,after,req.Reward,req.Terminal)
    if e!=nil{reply.Error=e.Error()}else{reply.OK=true;reply.Updates=policy.Updates}
   case "snapshot":
    b,e:=policy.Snapshot()
    if e!=nil{reply.Error=e.Error()}else{reply.OK=true;reply.State=base64.StdEncoding.EncodeToString(b);reply.Updates=policy.Updates}
   case "load":
    b,e:=base64.StdEncoding.DecodeString(req.State)
    if e==nil{policy,e=wing.Restore(b)}
    if e!=nil{reply.Error=e.Error()}else{reply.OK=true;reply.Updates=policy.Updates}
   case "quit":
    reply.OK=true
   default:
    reply.Error="MG01_UNSUPPORTED_NATIVE_COMMAND"
   }
  }
  body,e:=json.Marshal(reply)
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  if _,e=out.Write(append(body,'\n'));e!=nil{os.Exit(2)}
  if e=out.Flush();e!=nil{os.Exit(2)}
  if req.Op=="quit" && reply.OK {break}
 }
 if err:=scanner.Err();err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
