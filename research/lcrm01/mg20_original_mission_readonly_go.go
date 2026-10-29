// MG20 original source-only public mission admission: never train from quarantined smoke.
package main
import (
 "bytes"
 "encoding/json"
 "fmt"
 "io"
 "os"
 native "github.com/spoonman136668-ai/Wingless/research/native/itd02/mg19"
)
type Row struct {
 Action int `json:"action"`
 Status string `json:"status"`
 Mission string `json:"mission"`
}
type Result struct {
 Schema string `json:"schema"`
 Count int `json:"count"`
 Rows []Row `json:"rows"`
 NoMemoryMutation bool `json:"no_memory_mutation"`
}
func run()error{
 dec:=json.NewDecoder(io.LimitReader(os.Stdin,3000000))
 dec.DisallowUnknownFields()
 var frames []native.Public
 if err:=dec.Decode(&frames);err!=nil{return fmt.Errorf("MG20_BAD_SOURCE_FRAMES: %w",err)}
 var extra any
 if dec.Decode(&extra)!=io.EOF{return fmt.Errorf("MG20_TRAILING_INPUT")}
 if len(frames)!=96{return fmt.Errorf("MG20_FRAME_COUNT_%d",len(frames))}
 model:=native.New()
 if err:=model.BeginEpisode();err!=nil{return fmt.Errorf("MG20_BEGIN: %w",err)}
 original,err:=model.Snapshot()
 if err!=nil{return fmt.Errorf("MG20_PRE_SNAPSHOT: %w",err)}
 output:=Result{Schema:"itd02.mg20.go-original-mission-readonly.v1",Count:len(frames),Rows:make([]Row,0,len(frames))}
 for i,frame:=range frames{
  action,status,err:=model.Choose(frame)
  if err!=nil{return fmt.Errorf("MG20_NATIVE_SOURCE_MISSION_%d_%q: %w",i,frame.Mission,err)}
  if action==nil||*action<0||*action>6||status==""{return fmt.Errorf("MG20_NATIVE_ABSTAIN_%d_%q",i,frame.Mission)}
  output.Rows=append(output.Rows,Row{Action:*action,Status:status,Mission:frame.Mission})
 }
 after,err:=model.Snapshot()
 if err!=nil{return fmt.Errorf("MG20_POST_SNAPSHOT: %w",err)}
 output.NoMemoryMutation=bytes.Equal(original,after)
 if !output.NoMemoryMutation{return fmt.Errorf("MG20_ILLICIT_QUARANTINE_MEMORY_WRITE")}
 return json.NewEncoder(os.Stdout).Encode(output)
}
func main(){if err:=run();err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
