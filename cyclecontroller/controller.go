// Package cyclecontroller provides a persistent, non-authorizing,
// two-lane SYNTHETIC controller with bounded parallel workers and immutable
// intent-before-dispatch evidence. It is NOT a science scheduler.
package cyclecontroller

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "sort"
 "strings"
 "sync"
 "time"
)

const (
 Schema="forge.synthetic.parallel-controller.v1"
 IntentSchema="forge.synthetic.controller-intent.v1"
 TerminalSchema="forge.synthetic.controller-terminal.v1"
 IdentitySchema="forge.synthetic.controller-identity.v1"
 MaxCycles=4
)
var (
 ErrBlocked=errors.New("FORGE_SYNTHETIC_CONTROLLER_BLOCKED")
 ErrQuarantine=errors.New("FORGE_SYNTHETIC_CONTROLLER_UNCERTAIN_ORIGINAL_NO_REPLAY")
)
type Identity struct {
 Schema string `json:"schema"`
 WorkerSHA256 string `json:"worker_sha256"`
 FrozenPlanSHA256 string `json:"frozen_plan_sha256"`
 LaneNames [2]string `json:"lane_names"`
 ExecutionAuthorized bool `json:"execution_authorized"`
}
type Intent struct{
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 PriorTerminalSHA256 string `json:"prior_terminal_sha256"`
 IdentitySHA256 string `json:"identity_sha256"`
}
type Terminal struct{
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 IntentSHA256 string `json:"intent_sha256"`
 WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`
 WinglessVerified bool `json:"wingless_verified"`
 YggdrasilVerified bool `json:"yggdrasil_verified"`
 ScientificOriginalsExecuted uint64 `json:"scientific_originals_executed"`
 ExecutionAuthorized bool `json:"execution_authorized"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Completed uint64 `json:"completed"`
 LastTerminalSHA256 string `json:"last_terminal_sha256"`
 WinglessCycles uint64 `json:"wingless_cycles"`
 YggdrasilCycles uint64 `json:"yggdrasil_cycles"`
 OriginalScientificRuns uint64 `json:"original_scientific_runs"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,ch:=range s{if !(ch>='0'&&ch<='9'||ch>='a'&&ch<='f'){return false}}
 return true
}
func hash(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func canonical(v any)([]byte,error){
 b,err:=json.Marshal(v);if err!=nil{return nil,ErrBlocked}
 return append(b,'\n'),nil
}
func readCanonical(path string,v any)([]byte,error){
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()==0||st.Size()>8192{return nil,ErrQuarantine}
 b,err:=os.ReadFile(path);if err!=nil{return nil,ErrQuarantine}
 if json.Unmarshal(b,v)!=nil{return nil,ErrQuarantine}
 enc,err:=canonical(v)
 if err!=nil||string(enc)!=string(b){return nil,ErrQuarantine}
 return b,nil
}
func syncDirectory(path string)error{
 f,err:=os.Open(path);if err!=nil{return err};defer f.Close()
 if err=f.Sync();err!=nil&&runtime.GOOS!="windows"{return err}
 return nil
}
func writeOnce(path string,v any)error{
 b,err:=canonical(v);if err!=nil{return err}
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return ErrQuarantine}
 n,err:=f.Write(b)
 if err==nil&&n!=len(b){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil||closeErr!=nil{return ErrQuarantine}
 if err=syncDirectory(filepath.Dir(path));err!=nil{return ErrQuarantine}
 return nil
}
func digestBinary(p string)(string,error){
 if !filepath.IsAbs(p){return "",ErrBlocked}
 st,err:=os.Lstat(p)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>128<<20{return "",ErrBlocked}
 f,err:=os.Open(p);if err!=nil{return "",ErrBlocked};defer f.Close()
 h:=sha256.New()
 if _,err=io.Copy(h,f);err!=nil{return "",ErrBlocked}
 return hex.EncodeToString(h.Sum(nil)),nil
}
func cycleName(seq uint64)string{return fmt.Sprintf("generation-%04d",seq)}
func laneEvidenceDigest(gendir string)(string,error){
 h:=sha256.New()
 files:=0
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  base:=filepath.Join(gendir,"forge-synthetic-processes",strings.ToLower(lane),"forge-synthetic-worker")
  dir,err:=os.Lstat(base)
  if err!=nil||!dir.IsDir()||dir.Mode()&os.ModeSymlink!=0{return "",ErrQuarantine}
  entries,err:=os.ReadDir(base)
  if err!=nil||len(entries)!=3{return "",ErrQuarantine}
  sort.Slice(entries,func(i,j int)bool{return entries[i].Name()<entries[j].Name()})
  start,terminal,attempt:=0,0,0
  for _,entry:=range entries{
   name:=entry.Name()
   if strings.HasPrefix(name,"start-")&&strings.HasSuffix(name,".json"){start++
   }else if strings.HasPrefix(name,"terminal-")&&strings.HasSuffix(name,".json"){terminal++
   }else if len(name)==69&&strings.HasSuffix(name,".json"){attempt++
   }else{return "",ErrQuarantine}
   if entry.IsDir()||entry.Type()&os.ModeSymlink!=0{return "",ErrQuarantine}
   p:=filepath.Join(base,name);st,err:=os.Lstat(p)
   if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>8192{return "",ErrQuarantine}
   raw,err:=os.ReadFile(p);if err!=nil{return "",ErrQuarantine}
   h.Write([]byte(lane+"/"+name+"\x00"));h.Write(raw);files++
  }
  if start!=1||terminal!=1||attempt!=1{return "",ErrQuarantine}
 }
 if files!=6{return "",ErrQuarantine}
 return hex.EncodeToString(h.Sum(nil)),nil
}
func readState(root string,id Identity,floor uint64)(Report,error){
 var zero Report
 if floor>MaxCycles{return zero,ErrBlocked}
 var pinned Identity
 if _,err:=readCanonical(filepath.Join(root,"identity.json"),&pinned);err!=nil||pinned!=id{
  return zero,ErrQuarantine
 }
 identityRaw,_:=canonical(id)
 previous:=strings.Repeat("0",64)
 count:=uint64(0)
 for seq:=uint64(1);seq<=MaxCycles;seq++{
  gen:=filepath.Join(root,cycleName(seq))
  intentPath:=filepath.Join(root,cycleName(seq)+".intent.json")
  terminalPath:=filepath.Join(root,cycleName(seq)+".terminal.json")
  _,intentErr:=os.Lstat(intentPath)
  _,terminalErr:=os.Lstat(terminalPath)
  _,folderErr:=os.Lstat(gen)
  if os.IsNotExist(intentErr)&&os.IsNotExist(terminalErr)&&os.IsNotExist(folderErr){break}
  if intentErr!=nil||terminalErr!=nil||folderErr!=nil{return zero,ErrQuarantine}
  var intent Intent
  rawIntent,err:=readCanonical(intentPath,&intent)
  if err!=nil||intent.Schema!=IntentSchema||intent.Sequence!=seq||
   intent.PriorTerminalSHA256!=previous||intent.IdentitySHA256!=hash(identityRaw){
   return zero,ErrQuarantine
  }
  var terminal Terminal
  rawTerminal,err:=readCanonical(terminalPath,&terminal)
  if err!=nil||terminal.Schema!=TerminalSchema||terminal.Sequence!=seq||
   terminal.IntentSHA256!=hash(rawIntent)||!terminal.WinglessVerified||
   !terminal.YggdrasilVerified||terminal.ScientificOriginalsExecuted!=0||
   terminal.ExecutionAuthorized||!hex64(terminal.WorkerEvidenceSHA256){
   return zero,ErrQuarantine
  }
  observed,err:=laneEvidenceDigest(gen)
  if err!=nil||observed!=terminal.WorkerEvidenceSHA256{return zero,ErrQuarantine}
  previous=hash(rawTerminal)
  count++
 }
 if count<floor{return zero,ErrQuarantine}
 entries,err:=os.ReadDir(root)
 if err!=nil{return zero,ErrQuarantine}
 expected:=1+int(count)*3
 if len(entries)==expected+1 {
  info,err:=os.Lstat(filepath.Join(root,"controller.active"))
  if err!=nil||!info.Mode().IsRegular(){return zero,ErrQuarantine}
 }else if len(entries)!=expected{return zero,ErrQuarantine}
 return Report{Schema:Schema,Mode:"DURABLE_PARALLEL_SYNTHETIC_NO_SCIENCE",
  Completed:count,LastTerminalSHA256:previous,WinglessCycles:count,
  YggdrasilCycles:count},nil
}
type workerReply struct{
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 Recovery string `json:"recovery"`
 RealScientificCycles int `json:"real_scientific_cycles"`
}
func runLane(ctx context.Context,worker,lane,root string)error{
 bounded,cancel:=context.WithTimeout(ctx,10*time.Second)
 defer cancel()
 childDir:=filepath.Join(root,"forge-synthetic-processes",strings.ToLower(lane),"forge-synthetic-worker")
 cmd:=exec.CommandContext(bounded,worker,"--synthetic-only","--lane",lane,"--new-dir",childDir)
 cmd.Env=[]string{"PATH="+os.Getenv("PATH"),"HOME="+os.Getenv("HOME"),"SystemRoot="+os.Getenv("SystemRoot"),"TMPDIR="+os.Getenv("TMPDIR")}
 raw,err:=cmd.Output()
 if err!=nil||len(raw)>4096{return ErrQuarantine}
 var got workerReply
 if json.Unmarshal(raw,&got)!=nil||got.Mode!="INACTIVE_SYNTHETIC_ONLY"||
  got.Lane!=lane||got.Recovery!="TERMINAL_REVIEW_REQUIRED"||
  got.RealScientificCycles!=0{return ErrQuarantine}
 return nil
}
// Run begins at most MaxCycles synthetic generations. Exactly one durable
// generation intent is synced BEFORE each pair of parallel child processes.
// A crashed or partial generation is quarantined, NEVER dispatched again.
// Other controller instances are serialized by exclusive lock; abandoned
// locks are never silently deleted. No cleanup or external grant exists.
func Run(ctx context.Context,worker,workerSHA,planSHA,root string,cycles uint64,floor uint64)(Report,error){
 var zero Report
 if ctx==nil||ctx.Err()!=nil||!filepath.IsAbs(root)||
  filepath.Base(filepath.Clean(root))!="forge-synthetic-controller"||
  !hex64(workerSHA)||!hex64(planSHA)||cycles==0||cycles>MaxCycles||floor>cycles{
  return zero,ErrBlocked
 }
 actual,err:=digestBinary(worker);if err!=nil||actual!=workerSHA{return zero,ErrBlocked}
 id:=Identity{Schema:IdentitySchema,WorkerSHA256:workerSHA,FrozenPlanSHA256:planSHA,
  LaneNames:[2]string{"Wingless","Yggdrasil"}}
 if _,err:=os.Lstat(root);os.IsNotExist(err){
  if err=os.Mkdir(root,0700);err!=nil{return zero,ErrBlocked}
  if err=writeOnce(filepath.Join(root,"identity.json"),id);err!=nil{return zero,ErrQuarantine}
 }else if err!=nil{return zero,ErrBlocked}
 lock:=filepath.Join(root,"controller.active")
 lf,err:=os.OpenFile(lock,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return zero,ErrQuarantine}
 if err=lf.Close();err!=nil{return zero,ErrQuarantine}
 // An uncertain worker step leaves a persistent controller lock. No retry.
 report,err:=readState(root,id,floor)
 if err!=nil{return zero,err}
 if report.Completed>cycles{return zero,ErrBlocked}
 for seq:=report.Completed+1;seq<=cycles;seq++{
  if ctx.Err()!=nil{return zero,ErrQuarantine}
  dir:=filepath.Join(root,cycleName(seq))
  if err=os.Mkdir(dir,0700);err!=nil{return zero,ErrQuarantine}
  workRoot:=filepath.Join(dir,"forge-synthetic-processes")
  if err=os.Mkdir(workRoot,0700);err!=nil{return zero,ErrQuarantine}
  for _,name:=range []string{"wingless","yggdrasil"}{
   if err=os.Mkdir(filepath.Join(workRoot,name),0700);err!=nil{return zero,ErrQuarantine}
  }
  identityRaw,_:=canonical(id)
  intent:=Intent{Schema:IntentSchema,Sequence:seq,
   PriorTerminalSHA256:report.LastTerminalSHA256,IdentitySHA256:hash(identityRaw)}
  if err=writeOnce(filepath.Join(root,cycleName(seq)+".intent.json"),intent);err!=nil{return zero,ErrQuarantine}
  if digest,hashErr:=digestBinary(worker);hashErr!=nil||digest!=workerSHA{return zero,ErrQuarantine}
  failures:=make(chan error,2)
  var wg sync.WaitGroup
  for _,lane:=range []string{"Wingless","Yggdrasil"}{
   wg.Add(1)
   go func(l string){defer wg.Done();failures<-runLane(ctx,worker,l,dir)}(lane)
  }
  wg.Wait();close(failures)
  for failure:=range failures{if failure!=nil{return zero,ErrQuarantine}}
  evidence,err:=laneEvidenceDigest(dir)
  if err!=nil{return zero,ErrQuarantine}
  rawIntent,_:=canonical(intent)
  terminal:=Terminal{Schema:TerminalSchema,Sequence:seq,
   IntentSHA256:hash(rawIntent),WorkerEvidenceSHA256:evidence,
   WinglessVerified:true,YggdrasilVerified:true}
  if err=writeOnce(filepath.Join(root,cycleName(seq)+".terminal.json"),terminal);err!=nil{return zero,ErrQuarantine}
  // Verify every previously committed cycle before advancing again.
  report,err=readState(root,id,floor)
  if err!=nil{return zero,ErrQuarantine}
 }
 if err=os.Remove(lock);err!=nil{return zero,ErrQuarantine}
 if err=syncDirectory(root);err!=nil{return zero,ErrQuarantine}
 return report,nil
}
