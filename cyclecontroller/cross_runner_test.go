package cyclecontroller

import (
 "context"
 "errors"
 "io"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func copySyntheticSnapshot(t *testing.T,src,dst string){
 t.Helper()
 if err:=os.Mkdir(dst,0700);err!=nil{t.Fatal(err)}
 err:=filepath.WalkDir(src,func(path string,e os.DirEntry,walkErr error)error{
  if walkErr!=nil{return walkErr}
  if path==src{return nil}
  if e.Type()&os.ModeSymlink!=0{return ErrQuarantine}
  rel,err:=filepath.Rel(src,path);if err!=nil{return err}
  target:=filepath.Join(dst,rel)
  if e.IsDir(){return os.Mkdir(target,0700)}
  if !e.Type().IsRegular(){return ErrQuarantine}
  in,err:=os.Open(path);if err!=nil{return err}
  defer in.Close()
  out,err:=os.OpenFile(target,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
  if err!=nil{return err}
  _,err=io.Copy(out,in)
  if err==nil{err=out.Sync()}
  cErr:=out.Close();if err!=nil{return err}
  return cErr
 })
 if err!=nil{t.Fatal(err)}
}
func TestAnchoredRestoreToSeparateDirectoryThenTwoMoreGenerations(t *testing.T){
 src:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 first,worker,sha:=runTwo(t,src)
 if first.Completed!=2{t.Fatal("incorrect source generation")}
 target:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 copySyntheticSnapshot(t,src,target)
 before,err:=os.ReadFile(filepath.Join(target,cycleName(1)+".terminal.json"))
 if err!=nil{t.Fatal(err)}
 resumed,err:=RunAnchored(context.Background(),worker,sha,strings.Repeat("e",64),target,4,2,first.LastTerminalSHA256)
 if err!=nil{t.Fatal("valid full verified synthetic cross-runner restore blocked",err)}
 if resumed.Completed!=4||resumed.WinglessCycles!=4||resumed.YggdrasilCycles!=4||
  resumed.LastTerminalSHA256==first.LastTerminalSHA256||
  resumed.ScientificExecutionAuthorized||resumed.AcceptedRefMutation||
  resumed.OriginalScientificRuns!=0{t.Fatalf("unsafe resumed state: %+v",resumed)}
 preserved,err:=os.ReadFile(filepath.Join(target,cycleName(1)+".terminal.json"))
 if err!=nil||string(preserved)!=string(before){t.Fatal("earlier original terminal was mutated",err)}
 noReplay,err:=RunAnchored(context.Background(),worker,sha,strings.Repeat("e",64),target,4,4,resumed.LastTerminalSHA256)
 if err!=nil||noReplay!=resumed{t.Fatal("completed independent restore not replay-safe",noReplay,err)}
}
func TestAnchoredRestoreRejectsRollbackAndWrongHeadBeforeWorker(t *testing.T){
 src:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 first,worker,sha:=runTwo(t,src)
 for name,tc:=range map[string]struct{head string;floor uint64}{
  "different head":{strings.Repeat("f",64),2},
  "lower count":{first.LastTerminalSHA256,1},
  "higher floor":{first.LastTerminalSHA256,3},
 }{
  t.Run(name,func(t *testing.T){
   target:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
   copySyntheticSnapshot(t,src,target)
   _,err:=RunAnchored(context.Background(),worker,sha,strings.Repeat("e",64),target,4,tc.floor,tc.head)
   if !errors.Is(err,ErrQuarantine){t.Fatal("external head/ordinal drift admitted",err)}
   if _,err:=os.Lstat(filepath.Join(target,cycleName(3)));!os.IsNotExist(err){
    t.Fatal("original launched before independently anchored head")
   }
   if _,err:=os.Lstat(filepath.Join(target,"controller.active"));err!=nil{
    t.Fatal("unsafe restore failed to retain quarantine lock",err)
   }
  })
 }
}
func TestAnchoredRestoreRejectsLostHistoryEvenIfFloorPresent(t *testing.T){
 src:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 first,worker,sha:=runTwo(t,src)
 target:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 copySyntheticSnapshot(t,src,target)
 path:=filepath.Join(target,cycleName(1)+".terminal.json")
 if err:=os.Remove(path);err!=nil{t.Fatal(err)}
 if _,err:=RunAnchored(context.Background(),worker,sha,strings.Repeat("e",64),target,4,2,first.LastTerminalSHA256);
  !errors.Is(err,ErrQuarantine){t.Fatal("partial restored original unexpectedly cleared",err)}
 if _,err:=os.Lstat(filepath.Join(target,cycleName(3)));!os.IsNotExist(err){
  t.Fatal("resumed despite missing original scientific evidence")
 }
}
func TestAnchoredRestoreNeverAcceptsMissingIndependentHead(t *testing.T){
 worker,sha:=testBinary(t)
 path:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 for _,bad:=range []string{"",strings.Repeat("0",63),"malformed"}{
  if _,err:=RunAnchored(context.Background(),worker,sha,strings.Repeat("e",64),path,4,2,bad);
   !errors.Is(err,ErrBlocked){t.Fatal("missing pinned head accepted",err)}
 }
 if _,err:=os.Stat(path);!os.IsNotExist(err){
  t.Fatal("missing independent anchor created worker directory",err)
 }
}
