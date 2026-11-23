// Package shadowoutbox persists bounded, inactive recovery work candidates.
// Nothing here grants scientific authority, launches execution, or starts an original.
package shadowoutbox
import(
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
)
var ErrUnsafe=errors.New("FORGE_SHADOW_OUTBOX_UNSAFE")
const Schema="forge.shadow.recovery-outbox.v1"
type Entry struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 OriginalID string `json:"original_id"`
 IncidentSHA256 string `json:"incident_sha256"`
 RecoveryManifestSHA256 string `json:"recovery_manifest_sha256"`
 Scope string `json:"scope"`
 FirstUseRisk bool `json:"first_use_risk"`
 RequiresRequalification bool `json:"requires_requalification"`
}
func isHash(s string)bool {
 if len(s)!=64{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func valid(e Entry)bool{
 if e.Schema!=Schema||(e.Lane!="Wingless"&&e.Lane!="Yggdrasil")||
  e.OriginalID==""||len(e.OriginalID)>96||
  !isHash(e.IncidentSHA256)||!isHash(e.RecoveryManifestSHA256)||
  e.Scope==""||len(e.Scope)>128||e.FirstUseRisk||!e.RequiresRequalification{return false}
 for _,s:=range []string{e.OriginalID,e.Scope}{
  for _,r:=range s{
   if !(r>='a'&&r<='z'||r>='A'&&r<='Z'||r>='0'&&r<='9'||r=='-'||r=='_'||r=='.'){return false}
  }
 }
 return true
}
func identity(e Entry)(string,[]byte,error){
 if !valid(e){return "",nil,ErrUnsafe}
 b,err:=json.Marshal(e);if err!=nil{return "",nil,ErrUnsafe}
 h:=sha256.Sum256(append([]byte("FORGE-SHADOW-OUTBOX-V1\n"),b...))
 return hex.EncodeToString(h[:]),append(b,'\n'),nil
}
// Enqueue is content-addressed and create-only. Unknown write outcomes require
// external reconciliation; an existing path is checked byte-for-byte, never
// overwritten. An outbox item is NOT an executable dispatch request.
func Enqueue(dir string,e Entry)(string,error){
 if !filepath.IsAbs(dir)||strings.TrimSpace(dir)==""{return "",ErrUnsafe}
 id,b,err:=identity(e);if err!=nil{return "",err}
 if err:=os.MkdirAll(dir,0700);err!=nil{return "",err}
 path:=filepath.Join(dir,id+".json")
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if errors.Is(err,os.ErrExist){
  existing,readErr:=os.ReadFile(path)
  if readErr!=nil||string(existing)!=string(b){return "",ErrUnsafe}
  return id,nil
 }
 if err!=nil{return "",err}
 if _,err=f.Write(b);err!=nil{f.Close();return "",ErrUnsafe}
 if err=f.Sync();err!=nil{f.Close();return "",ErrUnsafe}
 if err=f.Close();err!=nil{return "",ErrUnsafe}
 return id,nil
}
// Load permits only exact immutable records and rejects unexpected directory
// entries. No replay, task leasing, or worker-side execution is possible.
func Load(dir string)([]Entry,error){
 names,err:=os.ReadDir(dir);if err!=nil{return nil,err}
 if len(names)>1024{return nil,ErrUnsafe}
 out:=[]Entry{}
 for _,name:=range names{
  if name.IsDir()||!strings.HasSuffix(name.Name(),".json")||len(name.Name())!=69{return nil,ErrUnsafe}
  raw,err:=os.ReadFile(filepath.Join(dir,name.Name()))
  if err!=nil||len(raw)==0||len(raw)>4096{return nil,ErrUnsafe}
  var e Entry
  if err:=json.Unmarshal(raw,&e);err!=nil{return nil,ErrUnsafe}
  id,canonical,err:=identity(e)
  if err!=nil||name.Name()!=id+".json"||string(raw)!=string(canonical){return nil,ErrUnsafe}
  out=append(out,e)
 }
 return out,nil
}
