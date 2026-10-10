// Package privatearchive is an offline, write-once FORGE research archive.
// It never contacts GitHub, dispatches experiments, accesses a controller,
// or writes Mind-Palace/KTRADE/CKB state. Hashes are not source authentication.
package privatearchive

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "runtime"
 "strings"

 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 FolderName = "forge-research-archive"
 Marker = "FORGE_PRIVATE_RESEARCH_ARCHIVE_V1\n"
 MaxOriginalBytes = 8 << 20
 MaxRecordBytes = 32768
)
type Store struct { root string }

func checkRoot(root string) (string,error) {
 if !filepath.IsAbs(root) || filepath.Base(filepath.Clean(root))!=FolderName {
  return "",errors.New("FORGE_ARCHIVE_DEDICATED_ABSOLUTE_ROOT_REQUIRED")
 }
 clean:=filepath.Clean(root)
 // Do not place the archive inside any known foreign controller/work tree.
 for _,p:=range strings.FieldsFunc(strings.ToLower(clean),func(r rune)bool{return r=='/'||r=='\\'}) {
  switch p {
  case "ckbr","ckb-plane","ktrade","ktrade-external","mind-palace","research-write-proxy":
   return "",errors.New("FORGE_ARCHIVE_FOREIGN_EXECUTION_BOUNDARY")
  }
 }
 // Inspect every actual ancestor, rather than comparing EvalSymlinks
 // strings: Windows canonicalizes case and short paths even without links.
 for current:=filepath.Dir(clean);; {
  st,err:=os.Lstat(current)
  if err!=nil || !st.IsDir() || st.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0 {
   return "",errors.New("FORGE_ARCHIVE_PARENT_SYMLINK_OR_UNAVAILABLE")
  }
  next:=filepath.Dir(current)
  if next==current {break}
  current=next
 }
 return clean,nil
}
func requireDir(path string)error {
 st,err:=os.Lstat(path)
 if err!=nil{return err}
 if !st.IsDir() || st.Mode()&os.ModeSymlink!=0 {
  return errors.New("FORGE_ARCHIVE_UNSAFE_DIRECTORY")
 }
 return nil
}
func checkFile(path string)error {
 st,err:=os.Lstat(path)
 if err!=nil{return err}
 if !st.Mode().IsRegular()||st.Mode()&os.ModeSymlink!=0 {
  return errors.New("FORGE_ARCHIVE_UNSAFE_FILE")
 }
 return nil
}
func syncDir(path string)error {
 f,err:=os.Open(path);if err!=nil{return err}
 defer f.Close()
 if err=f.Sync();err!=nil && runtime.GOOS!="windows" {return err}
 return nil
}
func putOnce(path string,data []byte)error {
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return fmt.Errorf("FORGE_ARCHIVE_IMMUTABLE_NAME_CONFLICT: %w",err)}
 // A failed write leaves the incomplete file behind, deliberately blocking
 // automatic retry/replay until independent provenance-based recovery.
 written,err:=f.Write(data)
 if err==nil&&written!=len(data){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil{return err}
 if closeErr!=nil{return closeErr}
 return syncDir(filepath.Dir(path))
}
func openLayout(root string)(*Store,error){
 clean,err:=checkRoot(root);if err!=nil{return nil,err}
 if err=requireDir(clean);err!=nil{return nil,err}
 if err=requireDir(filepath.Join(clean,"records"));err!=nil{return nil,err}
 if err=requireDir(filepath.Join(clean,"originals"));err!=nil{return nil,err}
 b,err:=os.ReadFile(filepath.Join(clean,".forge-archive-v1"))
 if err!=nil||string(b)!=Marker {return nil,errors.New("FORGE_ARCHIVE_MARKER_INVALID")}
 if err=checkFile(filepath.Join(clean,".forge-archive-v1"));err!=nil{return nil,err}
 entries,err:=os.ReadDir(clean);if err!=nil{return nil,err}
 if len(entries)!=3{return nil,errors.New("FORGE_ARCHIVE_ROOT_EXTRA_ENTRY")}
 for _,e:=range entries {
  if e.Name()!=".forge-archive-v1"&&e.Name()!="records"&&e.Name()!="originals" {
   return nil,errors.New("FORGE_ARCHIVE_ROOT_SCOPE_DRIFT")
  }
 }
 return &Store{root:clean},nil
}
// Initialize requires a NEW dedicated, empty FORGE-owned directory, never
// an existing controller or research directory. No live service is launched.
func Initialize(root string)(*Store,error) {
 clean,err:=checkRoot(root);if err!=nil{return nil,err}
 if err=os.Mkdir(clean,0700);err!=nil{return nil,err}
 if err=putOnce(filepath.Join(clean,".forge-archive-v1"),[]byte(Marker));err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"records"),0700);err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"originals"),0700);err!=nil{return nil,err}
 if err=syncDir(clean);err!=nil{return nil,err}
 return openLayout(clean)
}
func Open(root string)(*Store,error){return openLayout(root)}
func (s *Store) validate() error {
 if s==nil{return errors.New("FORGE_ARCHIVE_NOT_CONFIGURED")}
 _,err:=openLayout(s.root);return err
}
func digest(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func validDigest(d string)bool{
 if len(d)!=64{return false}
 for _,c:=range d{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// SaveOriginal stores exact original stdout/stderr/exit bundle bytes supplied
// by a future authenticated collector. There is no implicit archive upload.
func (s *Store) SaveOriginal(b []byte)(string,error){
 if err:=s.validate();err!=nil{return "",err}
 if len(b)==0||len(b)>MaxOriginalBytes{return "",errors.New("FORGE_ARCHIVE_ORIGINAL_BOUNDS")}
 sha:=digest(b)
 path:=filepath.Join(s.root,"originals",sha+".raw")
 if err:=checkFile(path);err==nil{
  prior,err:=s.ReadOriginal(sha)
  if err!=nil{return "",err}
  if !bytes.Equal(prior,b){return "",errors.New("FORGE_ARCHIVE_ORIGINAL_COLLISION")}
  return sha,nil
 }else if !os.IsNotExist(err){return "",err}
 if err:=putOnce(path,b);err!=nil{return "",err}
 return sha,nil
}
func (s *Store) ReadOriginal(sha string)([]byte,error){
 if err:=s.validate();err!=nil{return nil,err}
 if !validDigest(sha){return nil,errors.New("FORGE_ARCHIVE_ORIGINAL_ID_INVALID")}
 path:=filepath.Join(s.root,"originals",sha+".raw")
 if err:=checkFile(path);err!=nil{return nil,err}
 f,err:=os.Open(path);if err!=nil{return nil,err}
 defer f.Close()
 b,err:=io.ReadAll(io.LimitReader(f,MaxOriginalBytes+1))
 if err!=nil||len(b)==0||len(b)>MaxOriginalBytes||digest(b)!=sha{
  return nil,errors.New("FORGE_ARCHIVE_ORIGINAL_CORRUPT")
 }
 return b,nil
}
// Load rejects holes, truncated records, unknown files, tampering, and
// inconsistent experiment history. There is no auto-repair or replay.
func (s *Store) Load()(researchlog.Journal,error){
 var zero researchlog.Journal
 if err:=s.validate();err!=nil{return zero,err}
 folder:=filepath.Join(s.root,"records")
 items,err:=os.ReadDir(folder);if err!=nil{return zero,err}
 if len(items)>researchlog.MaxEntries{return zero,errors.New("FORGE_ARCHIVE_ENTRY_CAP")}
 journal:=researchlog.New()
 for index:=1;index<=len(items);index++{
  name:=fmt.Sprintf("%08d.json",index)
  file:=filepath.Join(folder,name)
  if err:=checkFile(file);err!=nil{return zero,fmt.Errorf("FORGE_ARCHIVE_RECORD_GAP_OR_UNSAFE_%d: %w",index,err)}
  f,err:=os.Open(file);if err!=nil{return zero,err}
  raw,readErr:=io.ReadAll(io.LimitReader(f,MaxRecordBytes+1))
  closeErr:=f.Close()
  if readErr!=nil||closeErr!=nil||len(raw)==0||len(raw)>MaxRecordBytes {
   return zero,errors.New("FORGE_ARCHIVE_RECORD_TRUNCATED_OR_OVERSIZED")
  }
  var r researchlog.Record
  if err=json.Unmarshal(raw,&r);err!=nil{return zero,errors.New("FORGE_ARCHIVE_RECORD_JSON_INVALID")}
  canon,err:=json.Marshal(r)
  if err!=nil||!bytes.Equal(raw,canon){return zero,errors.New("FORGE_ARCHIVE_RECORD_NOT_CANONICAL")}
  journal.Entries=append(journal.Entries,r)
 }
 if err=researchlog.Verify(journal);err!=nil{return zero,err}
 return journal,nil
}
// AppendEvent writes ONE immutable record. Its O_EXCL filename is the
// cross-process serialization gate. A racing writer loses, never overwrites.
// An interrupted partial write fails closed rather than risking replay.
func (s *Store) AppendEvent(event researchlog.Event)(researchlog.Record,error){
 if err:=s.validate();err!=nil{return researchlog.Record{},err}
 if event.Kind==researchlog.PrimaryTerminal||event.Kind==researchlog.IndependentReview||event.Kind==researchlog.FinalArchive{
  if _,err:=s.ReadOriginal(event.OriginalEvidenceSHA256);err!=nil{return researchlog.Record{},fmt.Errorf("FORGE_ARCHIVE_RAW_EVIDENCE_REQUIRED: %w",err)}
 }
 old,err:=s.Load();if err!=nil{return researchlog.Record{},err}
 next,err:=researchlog.Append(old,event);if err!=nil{return researchlog.Record{},err}
 row:=next.Entries[len(next.Entries)-1]
 b,err:=json.Marshal(row);if err!=nil{return researchlog.Record{},err}
 if len(b)>MaxRecordBytes{return researchlog.Record{},errors.New("FORGE_ARCHIVE_RECORD_BOUNDS")}
 path:=filepath.Join(s.root,"records",fmt.Sprintf("%08d.json",row.Sequence))
 if err:=putOnce(path,b);err!=nil{return researchlog.Record{},err}
 return row,nil
}
