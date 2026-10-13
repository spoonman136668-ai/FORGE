// Package fsastepcustody retains independently signed, immutable worker-step
// receipts in a dedicated local filesystem store. It is not an FSA authority,
// signer, distributed CAS, lease owner or worker execution permit.
package fsastepcustody

import (
 "bytes"
 "context"
 "crypto/ed25519"
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
 "sync"

 "github.com/spoonman136668-ai/forge/workerfence"
)

const (
 FolderName="forge-fsa-step-custody"
 Marker="FORGE_FSA_STEP_CUSTODY_V1\n"
 Schema="forge.fsa.step-custody-receipt.v1"
 MaxReceiptBytes=4096
 MaxEntries=100000
)
var (
 ErrBlocked=errors.New("FORGE_FSA_STEP_CUSTODY_BLOCKED")
 ErrConsumed=errors.New("FORGE_FSA_STEP_CUSTODY_ALREADY_CONSUMED_NO_REPLAY")
 ErrIndeterminate=errors.New("FORGE_FSA_STEP_CUSTODY_INDETERMINATE_NO_RETRY")
)
type record struct {
 Schema string `json:"schema"`
 Key string `json:"key"`
 Receipt workerfence.SignedStepReceipt `json:"receipt"`
 SHA256 string `json:"sha256"`
}
type Store struct {
 root string
 pin ed25519.PublicKey
 floor uint64
 mu sync.Mutex
 observed uint64
 poisoned bool
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)==0||len(s)>96{return false}
 for _,c:=range s{
  if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='-'||c=='_'){return false}
 }
 return true
}
func digest(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func key(c workerfence.StepClaim)string{
 raw,_:=json.Marshal(struct{
  ArchiveID string `json:"archive_id"`
  Lane string `json:"lane"`
  OriginalID string `json:"original_id"`
  StepSHA256 string `json:"step_sha256"`
 }{c.ArchiveID,c.Lane,c.OriginalID,c.StepSHA256})
 return digest(append([]byte("FORGE-FSA-STEP-IDENTITY-V1\n"),raw...))
}
func verify(r workerfence.SignedStepReceipt,pin ed25519.PublicKey)bool{
 c:=r.Claim
 if len(pin)!=ed25519.PublicKeySize||r.Schema!=workerfence.StepReceiptSchema||
  r.Status!=workerfence.Consumed||c.Schema!=workerfence.StepSchema||
  !validHex(c.ArchiveID,64)||!validHex(c.AuthorityHeadSHA256,64)||
  !validHex(c.IntentSHA256,64)||!validHex(c.WorkerBinarySHA256,64)||
  !validHex(c.StepSHA256,64)||c.AuthoritySequence>100000||
  (c.Lane!="Wingless"&&c.Lane!="Yggdrasil")||
  !validID(c.OriginalID)||!validID(c.OwnerID)||!validID(c.WorkerID)||
  c.OwnerEpoch==0||c.LeaseSequence==0||c.ExpiresAtUnix==0||
  !validHex(r.SignatureHex,128){return false}
 sig,err:=hex.DecodeString(r.SignatureHex);if err!=nil{return false}
 r.SignatureHex=""
 raw,err:=json.Marshal(r);if err!=nil{return false}
 return ed25519.Verify(pin,append([]byte(workerfence.StepReceiptDomain),raw...),sig)
}
func sameRoot(root string)(string,error){
 if !filepath.IsAbs(root)||filepath.Base(filepath.Clean(root))!=FolderName{return "",ErrBlocked}
 clean:=filepath.Clean(root)
 for _,seg:=range strings.FieldsFunc(strings.ToLower(clean),func(c rune)bool{return c=='/'||c=='\\'}){
  switch seg {
  case "ckbr","ckb-plane","ktrade","ktrade-external","mind-palace",
    "forge-research-archive","forge-fsa-trust","forge-fsa-witness":
   return "",ErrBlocked
  }
 }
 for p:=filepath.Dir(clean);;{
  info,err:=os.Lstat(p)
  if err!=nil||!info.IsDir()||info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return "",ErrBlocked}
  next:=filepath.Dir(p);if next==p{break};p=next
 }
 return clean,nil
}
func regular(path string,dir bool)bool{
 info,err:=os.Lstat(path);if err!=nil||info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return false}
 if dir{return info.IsDir()}
 return info.Mode().IsRegular()
}
func syncDir(path string)error{
 f,err:=os.Open(path);if err!=nil{return err}
 defer f.Close()
 if err=f.Sync();err!=nil&&runtime.GOOS!="windows"{return err}
 return nil
}
func create(path string,data []byte)error{
 if len(data)==0||len(data)>MaxReceiptBytes{return ErrBlocked}
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return err}
 n,err:=f.Write(data)
 if err==nil&&n!=len(data){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closed:=f.Close()
 if err!=nil{return err}
 if closed!=nil{return closed}
 return syncDir(filepath.Dir(path))
}
func seal(r record)(record,error){
 r.SHA256=""
 b,err:=json.Marshal(r);if err!=nil{return record{},err}
 r.SHA256=digest(append([]byte("FORGE-FSA-STEP-CUSTODY-RECORD-V1\n"),b...))
 return r,nil
}
func(check *Store)load()(uint64,error){
 if check==nil{return 0,ErrBlocked}
 if _,err:=sameRoot(check.root);err!=nil{return 0,ErrBlocked}
 if !regular(check.root,true)||!regular(filepath.Join(check.root,"records"),true)||
  !regular(filepath.Join(check.root,".forge-fsa-step-v1"),false){return 0,ErrBlocked}
 marker,err:=os.ReadFile(filepath.Join(check.root,".forge-fsa-step-v1"))
 if err!=nil||string(marker)!=Marker{return 0,ErrBlocked}
 entries,err:=os.ReadDir(check.root)
 if err!=nil||len(entries)!=2{return 0,ErrBlocked}
 for _,e:=range entries{
  if e.Name()!="records"&&e.Name()!=".forge-fsa-step-v1"{return 0,ErrBlocked}
 }
 folder:=filepath.Join(check.root,"records")
 files,err:=os.ReadDir(folder)
 if err!=nil||len(files)>MaxEntries{return 0,ErrBlocked}
 for _,e:=range files{
  name:=e.Name()
  if len(name)!=69||!strings.HasSuffix(name,".json")||!validHex(name[:64],64){return 0,ErrBlocked}
  path:=filepath.Join(folder,name)
  if !regular(path,false){return 0,ErrBlocked}
  f,err:=os.Open(path);if err!=nil{return 0,ErrBlocked}
  raw,readErr:=io.ReadAll(io.LimitReader(f,MaxReceiptBytes+1))
  closeErr:=f.Close()
  if readErr!=nil||closeErr!=nil||len(raw)==0||len(raw)>MaxReceiptBytes{return 0,ErrBlocked}
  var r record
  if json.Unmarshal(raw,&r)!=nil{return 0,ErrBlocked}
  canonical,err:=json.Marshal(r)
  if err!=nil||!bytes.Equal(canonical,raw)||r.Schema!=Schema||
   r.Key!=name[:64]||key(r.Receipt.Claim)!=r.Key||!verify(r.Receipt,check.pin)||
   !validHex(r.SHA256,64){return 0,ErrBlocked}
  calc,err:=seal(r)
  if err!=nil||r.SHA256!=calc.SHA256{return 0,ErrBlocked}
 }
 if uint64(len(files))<check.floor{return 0,ErrBlocked}
 return uint64(len(files)),nil
}
// Provision requires a BRAND NEW root and a separately supplied trusted public
// key. No signer or environment credential is created or loaded.
func Provision(root string,pin ed25519.PublicKey)(*Store,error){
 if len(pin)!=ed25519.PublicKeySize{return nil,ErrBlocked}
 clean,err:=sameRoot(root);if err!=nil{return nil,err}
 if err=os.Mkdir(clean,0700);err!=nil{return nil,err}
 if err=create(filepath.Join(clean,".forge-fsa-step-v1"),[]byte(Marker));err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"records"),0700);err!=nil{return nil,err}
 if err=syncDir(clean);err!=nil{return nil,err}
 return Open(clean,pin,0)
}
// Open needs an externally supplied minimum record count on EVERY restart.
// It cannot prove the count is current, or prevent a privileged rollback,
// without a separately protected monotonic high-water witness.
func Open(root string,pin ed25519.PublicKey,minimumCount uint64)(*Store,error){
 if len(pin)!=ed25519.PublicKeySize||minimumCount>MaxEntries{return nil,ErrBlocked}
 clean,err:=sameRoot(root);if err!=nil{return nil,err}
 s:=&Store{root:clean,pin:append(ed25519.PublicKey(nil),pin...),floor:minimumCount}
 n,err:=s.load();if err!=nil{return nil,err}
 s.observed=n
 return s,nil
}
// Retain stores an ALREADY SIGNED receipt. It cannot attest lease freshness,
// issue a grant, atomically consume a remote step, or authorize execution.
// Ambiguous write outcomes poison this store instance; never retry the step.
func(s *Store)Retain(ctx context.Context,r workerfence.SignedStepReceipt)error{
 if s==nil||ctx==nil||ctx.Err()!=nil{return ErrBlocked}
 s.mu.Lock();defer s.mu.Unlock()
 if s.poisoned||!verify(r,s.pin){return ErrBlocked}
 n,err:=s.load()
 if err!=nil||n<s.observed{s.poisoned=true;return ErrIndeterminate}
 s.observed=n
 if n>=MaxEntries{return ErrBlocked}
 id:=key(r.Claim)
 row,err:=seal(record{Schema:Schema,Key:id,Receipt:r})
 if err!=nil{return ErrBlocked}
 raw,err:=json.Marshal(row);if err!=nil{return ErrBlocked}
 if ctx.Err()!=nil{return ErrBlocked}
 path:=filepath.Join(s.root,"records",fmt.Sprintf("%s.json",id))
 if err=create(path,raw);err!=nil{
  if errors.Is(err,os.ErrExist){return ErrConsumed}
  s.poisoned=true
  return ErrIndeterminate
 }
 observed,err:=s.load()
 if err!=nil||observed!=n+1{
  s.poisoned=true
  return ErrIndeterminate
 }
 s.observed=observed
 return nil
}
// ReadCount is a diagnostic, not evidence of absence or authority. It pins
// the largest count observed by THIS process and rejects disappearance.
func(s *Store)ReadCount(ctx context.Context)(uint64,error){
 if s==nil||ctx==nil||ctx.Err()!=nil{return 0,ErrBlocked}
 s.mu.Lock();defer s.mu.Unlock()
 if s.poisoned{return 0,ErrBlocked}
 n,err:=s.load()
 if err!=nil||n<s.observed{s.poisoned=true;return 0,ErrBlocked}
 s.observed=n
 return n,nil
}
