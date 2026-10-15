package mindgraph

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "strings"
)

// WriteNew creates an entirely NEW private output root. No existing vault,
// Mind-Palace .ice directory, source repository or researcher note is altered.
// Intermediate dirs are owner-only; files are never overwritten.
func WriteNew(destination string, bundle Bundle)error{
 if destination==""||!filepath.IsAbs(destination)||len(bundle.Files)==0{
  return ErrBlocked
 }
 dest:=filepath.Clean(destination)
 parent:=filepath.Dir(dest)
 info,err:=os.Lstat(parent)
 if err!=nil||!info.IsDir()||info.Mode()&os.ModeSymlink!=0{
  return fmt.Errorf("%w: private destination parent must be existing real directory",ErrBlocked)
 }
 if err:=os.Mkdir(dest,0700);err!=nil{
  return fmt.Errorf("%w: private destination must be unused",ErrBlocked)
 }
 succeeded:=false
 defer func(){if !succeeded{_ = os.RemoveAll(dest)}}()
 for rel,payload:=range bundle.Files{
  path:=filepath.Clean(rel)
  if (filepath.IsAbs(path)||path=="."||path==".."||
      strings.HasPrefix(path,".."+string(os.PathSeparator))||
      strings.Contains(path,":")||len(payload)==0||len(payload)>2<<20){
   return errors.Join(ErrBlocked,errors.New("invalid output file"))
  }
  full:=filepath.Join(dest,path)
  if err:=os.MkdirAll(filepath.Dir(full),0700);err!=nil{return err}
  file,err:=os.OpenFile(full,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
  if err!=nil{return err}
  count,e:=file.Write(payload)
  if e==nil&&count!=len(payload){e=os.ErrInvalid}
  if e==nil{e=file.Sync()}
  cerr:=file.Close()
  if e!=nil{return e}
  if cerr!=nil{return cerr}
 }
 // Already generated folders are private even under unusual process umasks.
 succeeded=true
 return nil
}
