package watchdog

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
)

// PersistentLedger is an INACTIVE shadow-mode, single-process incident ledger.
// It must never grant execution authority, recover an original first-use or
// replace the independent fenced authority planned for FORGE activation.
type PersistentLedger struct{
 directory string
 seen map[string]bool
}
const ledgerFile="shadow-incidents.v1.json"
var ErrPersistentLedger=errors.New("FORGE_SHADOW_INCIDENT_CUSTODY_BLOCKED")
func LoadPersistent(directory string)(*PersistentLedger,error){
 if directory==""||!filepath.IsAbs(directory){return nil,ErrPersistentLedger}
 if err:=os.MkdirAll(directory,0700);err!=nil{return nil,err}
 p:=&PersistentLedger{directory:directory,seen:map[string]bool{}}
 raw,err:=os.ReadFile(filepath.Join(directory,ledgerFile))
 if errors.Is(err,os.ErrNotExist){return p,nil}
 if err!=nil{return nil,ErrPersistentLedger}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 var saved struct{Schema string `json:"schema"`; Keys []string `json:"keys"`}
 if dec.Decode(&saved)!=nil||saved.Schema!="forge.shadow.incidents.v1"{return nil,ErrPersistentLedger}
 tail:=struct{}{};if !errors.Is(dec.Decode(&tail),os.ErrClosed)&&len(raw)==0{return nil,ErrPersistentLedger}
 for _,k:=range saved.Keys{
  if k==""||p.seen[k]{return nil,ErrPersistentLedger}
  p.seen[k]=true
 }
 return p,nil
}
// CommitSnapshot atomically replaces the inactive advisory snapshot by rename.
// No externally authorized work may depend on this single-host persistence.
func(p *PersistentLedger)CommitSnapshot(keys []string)error{
 if p==nil||p.directory==""{return ErrPersistentLedger}
 seen:=map[string]bool{}
 for _,k:=range keys{if k==""||seen[k]{return ErrPersistentLedger};seen[k]=true}
 raw,err:=json.Marshal(struct{Schema string `json:"schema"`;Keys []string `json:"keys"`}{
  Schema:"forge.shadow.incidents.v1",Keys:keys,
 });if err!=nil{return err}
 tmp,err:=os.CreateTemp(p.directory,".incidents-*")
 if err!=nil{return err}
 name:=tmp.Name()
 defer os.Remove(name)
 if _,err=tmp.Write(append(raw,'\n'));err!=nil{tmp.Close();return err}
 if err=tmp.Sync();err!=nil{tmp.Close();return err}
 if err=tmp.Close();err!=nil{return err}
 if err=os.Rename(name,filepath.Join(p.directory,ledgerFile));err!=nil{return err}
 p.seen=seen
 return nil
}
