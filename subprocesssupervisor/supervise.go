// Package subprocesssupervisor supervises TWO existing lane names as
// isolated, bounded SYNTHETIC OS worker processes. Never handles CKB authority.
package subprocesssupervisor
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "time"
)
var ErrUnsafe=errors.New("FORGE_SYNTHETIC_SUBPROCESS_SUPERVISOR_UNSAFE")
type Result struct{
 Schema string `json:"schema"`
 WinglessVerified bool `json:"wingless_verified"`
 YggdrasilVerified bool `json:"yggdrasil_verified"`
 RealScientificCycles int `json:"real_scientific_cycles"`
}
type workerOutput struct{
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 Recovery string `json:"recovery"`
 RealScientificCycles int `json:"real_scientific_cycles"`
}
func digestFile(path string)(string,error){
 f,err:=os.Open(path);if err!=nil{return "",err};defer f.Close()
 stat,err:=f.Stat();if err!=nil||!stat.Mode().IsRegular(){return "",ErrUnsafe}
 h:=sha256.New()
 if _,err=io.Copy(h,f);err!=nil{return "",err}
 return hex.EncodeToString(h.Sum(nil)),nil
}
// Run enforces a pinned executable byte identity and launches both lanes
// exactly once. Any ambiguity aborts; no retry exists. Child output is
// checked for zero real scientific cycles and signed-recovery confirmation.
func Run(ctx context.Context,workerExecutable,expectedSHA256,root string)(Result,error){
 var out Result
 if ctx==nil||ctx.Err()!=nil||!filepath.IsAbs(root)||filepath.Base(filepath.Clean(root))!="forge-synthetic-processes"||
 !filepath.IsAbs(workerExecutable)||len(expectedSHA256)!=64{return out,ErrUnsafe}
 for _,c:=range expectedSHA256{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return out,ErrUnsafe}}
 got,err:=digestFile(workerExecutable);if err!=nil||got!=expectedSHA256{return out,ErrUnsafe}
 if err:=os.Mkdir(root,0700);err!=nil{return out,ErrUnsafe}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  laneDir:=filepath.Join(root,strings.ToLower(lane))
  if err:=os.Mkdir(laneDir,0700);err!=nil{return out,ErrUnsafe}
  childDir:=filepath.Join(laneDir,"forge-synthetic-worker")
  // A worker binary changed after preflight must not be dispatched. This
  // recheck is not atomic with exec; deployment needs immutable binaries.
  verified,checkErr:=digestFile(workerExecutable)
  if checkErr!=nil||verified!=expectedSHA256{return out,ErrUnsafe}
  limited,cancel:=context.WithTimeout(ctx,10*time.Second)
  cmd:=exec.CommandContext(limited,workerExecutable,"--synthetic-only","--lane",lane,"--new-dir",childDir)
  cmd.Env=[]string{"PATH="+os.Getenv("PATH"),"SystemRoot="+os.Getenv("SystemRoot"),"HOME="+os.Getenv("HOME"),"TMPDIR="+os.Getenv("TMPDIR")}
  raw,execErr:=cmd.Output()
  cancel()
  if execErr!=nil||len(raw)>4096{return out,ErrUnsafe}
  var reply workerOutput
  if err:=json.Unmarshal(raw,&reply);err!=nil||reply.Mode!="INACTIVE_SYNTHETIC_ONLY"||
  reply.Lane!=lane||reply.Recovery!="TERMINAL_REVIEW_REQUIRED"||
  reply.RealScientificCycles!=0{return out,ErrUnsafe}
  if lane=="Wingless"{out.WinglessVerified=true}else{out.YggdrasilVerified=true}
 }
 out.Schema="forge.synthetic.subprocess-supervision.v1"
 return out,nil
}
