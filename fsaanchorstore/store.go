// Package fsaanchorstore provides a write-once disk implementation of the
// FORGE Scientific Authority (FSA) monotonic checkpoint interface.
// This is a source-only storage primitive. It is NOT a deployed independent
// authority, nor a substitute for protected off-host trust or signer custody.
package fsaanchorstore

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

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 FolderName = "forge-fsa-trust"
 Marker = "FORGE_FSA_CHECKPOINT_STORE_V1\n"
 Schema = "forge.fsa.trust-receipt.v1"
 MaxFileBytes = 4096
)

type receipt struct {
 Schema string `json:"schema"`
 Ordinal uint64 `json:"ordinal"`
 PreviousReceiptSHA256 string `json:"previous_receipt_sha256"`
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 PublicKeyHex string `json:"public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
 ReceiptSHA256 string `json:"receipt_sha256"`
}
type Store struct {
 root string
 pinnedGenesis fsahead.Anchor
}
func digest(b []byte)string{v:=sha256.Sum256(b);return hex.EncodeToString(v[:])}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'||c=='-'){return false}}
 return true
}
func validAnchor(a fsahead.Anchor)bool{
 return validHex(a.ArchiveID,64)&&validID(a.KeyID)&&
  len(a.PublicKey)==ed25519.PublicKeySize&&a.AuthorityEpoch>0&&
  a.Sequence<=researchlog.MaxEntries&&validHex(a.HeadSHA256,64)&&
  ((a.Sequence==0&&a.HeadSHA256==researchlog.Genesis)||
  (a.Sequence>0&&a.HeadSHA256!=researchlog.Genesis))
}
func equal(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
  bytes.Equal(a.PublicKey,b.PublicKey)&&a.AuthorityEpoch==b.AuthorityEpoch&&
  a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
func clone(a fsahead.Anchor)fsahead.Anchor{
 a.PublicKey=append(ed25519.PublicKey(nil),a.PublicKey...)
 return a
}
func safeRoot(root string)(string,error){
 if !filepath.IsAbs(root)||filepath.Base(filepath.Clean(root))!=FolderName{return "",errors.New("FORGE_FSA_DEDICATED_ABSOLUTE_ROOT_REQUIRED")}
 clean:=filepath.Clean(root)
 for _,piece:=range strings.FieldsFunc(strings.ToLower(clean),func(c rune)bool{return c=='/'||c=='\\'}){
  switch piece{
  case "ckbr","ckb-plane","ktrade","ktrade-external","mind-palace","forge-research-archive","research-write-proxy":
   return "",errors.New("FORGE_FSA_FOREIGN_DIRECTORY_FORBIDDEN")
  }
 }
 for p:=filepath.Dir(clean);;{
  stat,err:=os.Lstat(p)
  if err!=nil||!stat.IsDir()||stat.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{
   return "",errors.New("FORGE_FSA_PARENT_PATH_UNSAFE")
  }
  next:=filepath.Dir(p);if next==p{break};p=next
 }
 return clean,nil
}
func safeDir(p string)error{
 stat,err:=os.Lstat(p)
 if err!=nil{return err}
 if !stat.IsDir()||stat.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return errors.New("FORGE_FSA_DIRECTORY_UNSAFE")}
 return nil
}
func safeFile(p string)error{
 stat,err:=os.Lstat(p)
 if err!=nil{return err}
 if !stat.Mode().IsRegular()||stat.Mode()&os.ModeSymlink!=0{return errors.New("FORGE_FSA_FILE_UNSAFE")}
 return nil
}
func syncDir(p string)error{
 f,err:=os.Open(p);if err!=nil{return err}
 defer f.Close()
 if err=f.Sync();err!=nil&&runtime.GOOS!="windows"{return err}
 return nil
}
func writeOnce(p string,b []byte)error{
 if len(b)==0||len(b)>MaxFileBytes{return errors.New("FORGE_FSA_RECEIPT_BOUNDS")}
 f,err:=os.OpenFile(p,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return err}
 // Never remove an incomplete receipt. A crash becomes an explicit
 // reconciliation blocker, not a silent write retry.
 n,err:=f.Write(b);if err==nil&&n!=len(b){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil{return err}
 if closeErr!=nil{return closeErr}
 return syncDir(filepath.Dir(p))
}
func (r receipt)anchor()(fsahead.Anchor,error){
 b,err:=hex.DecodeString(r.PublicKeyHex)
 if err!=nil{return fsahead.Anchor{},err}
 a:=fsahead.Anchor{ArchiveID:r.ArchiveID,KeyID:r.KeyID,PublicKey:ed25519.PublicKey(b),
  AuthorityEpoch:r.AuthorityEpoch,Sequence:r.Sequence,HeadSHA256:r.HeadSHA256}
 if !validAnchor(a){return fsahead.Anchor{},errors.New("FORGE_FSA_RECEIPT_ANCHOR_INVALID")}
 return a,nil
}
func wrap(a fsahead.Anchor,ordinal uint64,priorSHA string)(receipt,error){
 r:=receipt{Schema:Schema,Ordinal:ordinal,PreviousReceiptSHA256:priorSHA,
  ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKeyHex:hex.EncodeToString(a.PublicKey),
  AuthorityEpoch:a.AuthorityEpoch,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256}
 raw,err:=json.Marshal(r);if err!=nil{return receipt{},err}
 r.ReceiptSHA256=digest(raw)
 return r,nil
}
func receiptBytes(r receipt)([]byte,error){return json.Marshal(r)}
func checkReceipt(r receipt,ordinal uint64,priorSHA string)(fsahead.Anchor,error){
 if r.Schema!=Schema||r.Ordinal!=ordinal||r.PreviousReceiptSHA256!=priorSHA||
  !validHex(r.ReceiptSHA256,64){return fsahead.Anchor{},errors.New("FORGE_FSA_RECEIPT_ORDER_OR_IDENTITY_INVALID")}
 candidate:=r;candidate.ReceiptSHA256=""
 raw,err:=json.Marshal(candidate)
 if err!=nil||digest(raw)!=r.ReceiptSHA256{return fsahead.Anchor{},errors.New("FORGE_FSA_RECEIPT_HASH_MISMATCH")}
 return r.anchor()
}
func layout(root string)error{
 if err:=safeDir(root);err!=nil{return err}
 if err:=safeDir(filepath.Join(root,"receipts"));err!=nil{return err}
 marker:=filepath.Join(root,".forge-fsa-store-v1")
 if err:=safeFile(marker);err!=nil{return err}
 b,err:=os.ReadFile(marker)
 if err!=nil||string(b)!=Marker{return errors.New("FORGE_FSA_MARKER_MISMATCH")}
 rows,err:=os.ReadDir(root);if err!=nil{return err}
 if len(rows)!=2{return errors.New("FORGE_FSA_ROOT_EXTRA_ENTRY")}
 for _,e:=range rows{if e.Name()!=".forge-fsa-store-v1"&&e.Name()!="receipts"{return errors.New("FORGE_FSA_ROOT_SCOPE_DRIFT")}}
 return nil
}
// Provision creates a brand-new dedicated directory and pins operator-supplied
// genesis. It does not generate keys or infer identity from archive contents.
// Call only in an isolated, separately authorized FORGE trust environment.
func Provision(root string,genesis fsahead.Anchor)(*Store,error){
 if !validAnchor(genesis)||genesis.Sequence!=0||genesis.HeadSHA256!=researchlog.Genesis{
  return nil,errors.New("FORGE_FSA_GENESIS_EXTERNAL_PIN_REQUIRED")
 }
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 if err:=os.Mkdir(clean,0700);err!=nil{return nil,err}
 if err=writeOnce(filepath.Join(clean,".forge-fsa-store-v1"),[]byte(Marker));err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"receipts"),0700);err!=nil{return nil,err}
 initial,err:=wrap(genesis,0,researchlog.Genesis);if err!=nil{return nil,err}
 b,err:=receiptBytes(initial);if err!=nil{return nil,err}
 if err=writeOnce(filepath.Join(clean,"receipts","00000000.json"),b);err!=nil{return nil,err}
 return Open(clean,genesis)
}
// Open requires an independently pinned genesis on every restart. The local
// store cannot be used to manufacture its own trust anchor.
func Open(root string,pinnedGenesis fsahead.Anchor)(*Store,error){
 if !validAnchor(pinnedGenesis)||pinnedGenesis.Sequence!=0||pinnedGenesis.HeadSHA256!=researchlog.Genesis{
  return nil,errors.New("FORGE_FSA_GENESIS_EXTERNAL_PIN_REQUIRED")
 }
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 s:=&Store{root:clean,pinnedGenesis:clone(pinnedGenesis)}
 if _,err:=s.load();err!=nil{return nil,err}
 return s,nil
}
func (s *Store)load()(fsahead.Anchor,error){
 var zero fsahead.Anchor
 if s==nil{return zero,errors.New("FORGE_FSA_STORE_UNCONFIGURED")}
 if _,err:=safeRoot(s.root);err!=nil{return zero,err}
 if err:=layout(s.root);err!=nil{return zero,err}
 dir:=filepath.Join(s.root,"receipts")
 entries,err:=os.ReadDir(dir);if err!=nil{return zero,err}
 if len(entries)==0||len(entries)>researchlog.MaxEntries+1{return zero,errors.New("FORGE_FSA_RECEIPT_COUNT_INVALID")}
 var previous fsahead.Anchor
 priorSHA:=researchlog.Genesis
 for i:=0;i<len(entries);i++{
  name:=fmt.Sprintf("%08d.json",i)
  path:=filepath.Join(dir,name)
  if err:=safeFile(path);err!=nil{return zero,fmt.Errorf("FORGE_FSA_RECEIPT_HOLE_OR_SYMLINK_%d: %w",i,err)}
  f,err:=os.Open(path);if err!=nil{return zero,err}
  raw,readErr:=io.ReadAll(io.LimitReader(f,MaxFileBytes+1));closeErr:=f.Close()
  if readErr!=nil||closeErr!=nil||len(raw)==0||len(raw)>MaxFileBytes{return zero,errors.New("FORGE_FSA_RECEIPT_INCOMPLETE")}
  var r receipt
  if err=json.Unmarshal(raw,&r);err!=nil{return zero,errors.New("FORGE_FSA_RECEIPT_JSON_INVALID")}
  canonical,err:=receiptBytes(r)
  if err!=nil||!bytes.Equal(raw,canonical){return zero,errors.New("FORGE_FSA_RECEIPT_NOT_CANONICAL")}
  a,err:=checkReceipt(r,uint64(i),priorSHA);if err!=nil{return zero,err}
  if i==0 {
   if !equal(a,s.pinnedGenesis){return zero,errors.New("FORGE_FSA_GENESIS_DRIFT")}
  }else{
   if a.ArchiveID!=previous.ArchiveID||a.KeyID!=previous.KeyID||
    !bytes.Equal(a.PublicKey,previous.PublicKey)||a.AuthorityEpoch!=previous.AuthorityEpoch||
    a.Sequence<=previous.Sequence||a.HeadSHA256==previous.HeadSHA256{
    return zero,errors.New("FORGE_FSA_MONOTONIC_OR_AUTHORITY_DRIFT")
   }
  }
  previous=a;priorSHA=r.ReceiptSHA256
 }
 return clone(previous),nil
}
func (s *Store) ReadAnchor(ctx context.Context)(fsahead.Anchor,error){
 if ctx==nil||ctx.Err()!=nil{return fsahead.Anchor{},errors.New("FORGE_FSA_CONTEXT_UNAVAILABLE")}
 a,err:=s.load();if err!=nil{return fsahead.Anchor{},err}
 if ctx.Err()!=nil{return fsahead.Anchor{},ctx.Err()}
 return a,nil
}
// This confirms the *provisioned ID*, not the physical archive instance.
// Remote deployment must bind that ID independently in its protected control
// plane. The filesystem alone cannot establish off-store independence.
func (s *Store) ConfirmArchiveBinding(ctx context.Context,archiveID string)(bool,error){
 a,err:=s.ReadAnchor(ctx);if err!=nil{return false,err}
 return archiveID==s.pinnedGenesis.ArchiveID&&a.ArchiveID==archiveID,nil
}
func (s *Store) CompareAndSwap(ctx context.Context,prev,next fsahead.Anchor)(bool,error){
 if ctx==nil||ctx.Err()!=nil{return false,errors.New("FORGE_FSA_CONTEXT_UNAVAILABLE")}
 current,err:=s.load();if err!=nil{return false,err}
 if !equal(current,prev){return false,nil}
 if !validAnchor(next)||next.ArchiveID!=prev.ArchiveID||next.KeyID!=prev.KeyID||
  !bytes.Equal(next.PublicKey,prev.PublicKey)||next.AuthorityEpoch!=prev.AuthorityEpoch||
  next.Sequence<=prev.Sequence||next.HeadSHA256==prev.HeadSHA256{return false,errors.New("FORGE_FSA_CAS_MONOTONIC_IDENTITY_INVALID")}
 if ctx.Err()!=nil{return false,ctx.Err()}
 dir:=filepath.Join(s.root,"receipts")
 entries,err:=os.ReadDir(dir);if err!=nil{return false,err}
 previousName:=fmt.Sprintf("%08d.json",len(entries)-1)
 previousPath:=filepath.Join(dir,previousName)
 if err:=safeFile(previousPath);err!=nil{return false,err}
 raw,err:=os.ReadFile(previousPath);if err!=nil||len(raw)>MaxFileBytes{return false,errors.New("FORGE_FSA_CAS_PREDECESSOR_UNREADABLE")}
 var last receipt
 if err:=json.Unmarshal(raw,&last);err!=nil{return false,err}
 // Snapshot validation and ordinal discovery are separate operations.
 // A competing writer can finish after load() but before ReadDir().
 // Rebind the filename to the exact immutable predecessor, otherwise two
 // writers could each create a DIFFERENT sequence and both report success.
 oldHead,err:=last.anchor()
 if err!=nil{return false,err}
 if last.Ordinal!=uint64(len(entries)-1)||!equal(oldHead,prev){
  return false,nil
 }
 r,err:=wrap(next,uint64(len(entries)),last.ReceiptSHA256);if err!=nil{return false,err}
 b,err:=receiptBytes(r);if err!=nil{return false,err}
 path:=filepath.Join(dir,fmt.Sprintf("%08d.json",len(entries)))
 if err:=writeOnce(path,b);err!=nil{
  if os.IsExist(err){return false,nil}
  // A failed write can already have created the next receipt: do not retry.
  return false,err
 }
 return true,nil
}
var _ fsatrust.Authority = (*Store)(nil)
