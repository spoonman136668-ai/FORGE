package researchstate

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestArchivePersistRecoveryAndStaleHead(t *testing.T){
 root:=t.TempDir()
 a,err:=OpenArchive(root);if err!=nil{t.Fatal(err)}
 if _,err:=OpenArchive(root);err==nil{t.Fatal("duplicate writer acquired")}
 h:=Genesis
 e:=Event{Lane:"Wingless",ExperimentID:"original_1",FrozenSHA256:strings.Repeat("a",64),To:Proposed}
 newHead,err:=a.Append(e,h);if err!=nil{t.Fatal(err)}
 if _,err:=a.Append(e,h);err==nil{t.Fatal("stale duplicate accepted")}
 loaded,err:=LoadArchive(root);if err!=nil{t.Fatal(err)}
 actual,err:=Head(loaded);if err!=nil||actual!=newHead{t.Fatal("head not persistent",err)}
 if err:=a.Close();err!=nil{t.Fatal(err)}
 reopened,err:=OpenArchive(root);if err!=nil{t.Fatal(err)}
 if err:=reopened.Close();err!=nil{t.Fatal(err)}
}
func TestArchiveTornRecordAndUnknownFileFailClosed(t *testing.T){
 for _,mode:=range []string{"torn","gap","extra"}{t.Run(mode,func(t *testing.T){
  root:=t.TempDir()
  a,err:=OpenArchive(root);if err!=nil{t.Fatal(err)}
  _,err=a.Append(Event{Lane:"Yggdrasil",ExperimentID:"original_2",FrozenSHA256:strings.Repeat("b",64),To:Proposed},Genesis)
  if err!=nil{t.Fatal(err)}
  if err:=a.Close();err!=nil{t.Fatal(err)}
  path:=filepath.Join(root,entryName(1))
  switch mode{
  case "torn":err=os.WriteFile(path,[]byte("{torn"),0600)
  case "gap":err=os.Rename(path,filepath.Join(root,entryName(2)))
  case "extra":err=os.WriteFile(filepath.Join(root,"unexpected"),[]byte("evil"),0600)
  }
  if err!=nil{t.Fatal(err)}
  if _,err:=LoadArchive(root);err==nil{t.Fatal("invalid archive accepted")}
  if _,err:=OpenArchive(root);err==nil{t.Fatal("invalid archive opened")}
  if _,err:=OpenArchive(root);err==nil{t.Fatal("crash lock stolen")}
 })}
}
func TestCrashLockNeverAutoExpires(t *testing.T){
 root:=t.TempDir()
 a,err:=OpenArchive(root);if err!=nil{t.Fatal(err)}
 if err:=a.lock.Close();err!=nil{t.Fatal(err)}
 a.closed=true
 if _,err:=OpenArchive(root);err==nil{t.Fatal("stale owner silently replaced")}
}
