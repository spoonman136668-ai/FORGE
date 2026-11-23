package researchstate

import (
 "bytes"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
)

// Archive is an INACTIVE single-process shadow journal. A process-local
// O_EXCL lock prevents accidental simultaneous writers on a local filesystem.
// Stale crash locks deliberately require external reconciliation and must not
// be interpreted as expired leases or as permission to redispatch.
type Archive struct {
 root string
 lock *os.File
 closed bool
}
func entryName(n uint64) string { return fmt.Sprintf("%020d.json", n) }
func isEntry(s string) bool {
 if len(s)!=25||!strings.HasSuffix(s,".json"){return false}
 for _,c:=range s[:20]{ if c<'0'||c>'9'{return false} }
 return true
}
// LoadArchive rejects gaps, additional files, noncanonical bytes and a
// broken hash chain rather than skipping any partially persisted event.
func LoadArchive(root string)(Journal,error){
 entries,err:=os.ReadDir(root)
 if err!=nil{return Journal{},err}
 count:=uint64(0)
 for _,e:=range entries {
  if e.Name()==".writer.lock" {continue}
  if e.IsDir()||!isEntry(e.Name()){return Journal{},fmt.Errorf("%w: unexpected archive entry",ErrBlocked)}
  count++
 }
 if count>100000{return Journal{},ErrBlocked}
 j:=New()
 for n:=uint64(1);n<=count;n++{
  b,err:=os.ReadFile(filepath.Join(root,entryName(n)))
  if err!=nil||len(b)==0||len(b)>16384{return Journal{},ErrBlocked}
  var ev Event
  d:=json.NewDecoder(bytes.NewReader(b))
  d.DisallowUnknownFields()
  if err:=d.Decode(&ev);err!=nil{return Journal{},ErrBlocked}
  encoded,err:=json.Marshal(ev)
  if err!=nil||!bytes.Equal(b,append(encoded,'\n')){return Journal{},ErrBlocked}
  j.Entries=append(j.Entries,ev)
 }
 if err:=Verify(j);err!=nil{return Journal{},err}
 return j,nil
}
func OpenArchive(root string)(*Archive,error){
 if root==""{return nil,ErrBlocked}
 if err:=os.MkdirAll(root,0700);err!=nil{return nil,err}
 lock,err:=os.OpenFile(filepath.Join(root,".writer.lock"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return nil,fmt.Errorf("%w: writer unavailable",ErrBlocked)}
 a:=&Archive{root:root,lock:lock}
 if _,err:=LoadArchive(root);err!=nil{
  _=lock.Close()
  // Keep the lock after an integrity failure. Never auto-repair custody.
  return nil,err
 }
 return a,nil
}
// Append requires an exact previous logical head; new events are written
// exclusively, file-synced, and re-read. No outside dispatch is permitted
// from this outcome; independently witnessed transactional acceptance is
// an additional future implementation boundary.
func (a *Archive)Append(ev Event,expectedHead string)(string,error){
 if a==nil||a.closed||a.lock==nil{return "",ErrBlocked}
 old,err:=LoadArchive(a.root);if err!=nil{return "",err}
 next,err:=Append(old,ev,expectedHead);if err!=nil{return "",err}
 added:=next.Entries[len(next.Entries)-1]
 b,err:=json.Marshal(added);if err!=nil{return "",err}
 f,err:=os.OpenFile(filepath.Join(a.root,entryName(added.Sequence)),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return "",ErrBlocked}
 b=append(b,'\n')
 _,writeErr:=f.Write(b)
 if writeErr==nil{writeErr=f.Sync()}
 closeErr:=f.Close()
 if writeErr!=nil||closeErr!=nil{return "",ErrBlocked}
 after,err:=LoadArchive(a.root)
 if err!=nil{return "",ErrBlocked}
 head,err:=Head(after)
 if err!=nil||head!=added.RecordSHA256{return "",ErrBlocked}
 return head,nil
}
// Close must not run after a simulated crash. A future service requires a
// fenced, independently durable owner/lease store; file locks are insufficient.
func (a *Archive)Close()error{
 if a==nil||a.closed{return ErrBlocked}
 a.closed=true
 if err:=a.lock.Close();err!=nil{return err}
 return os.Remove(filepath.Join(a.root,".writer.lock"))
}
