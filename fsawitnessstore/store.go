// Package fsawitnessstore retains independently signed FSA high-water records
// in an append-only, crash-inspected filesystem log. It is a SOURCE-ONLY
// storage primitive, not an independent deployed signer or scientific authority.
package fsawitnessstore

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
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
)

const (
 FolderName = "forge-fsa-witness"
 Marker = "FORGE_FSA_WITNESS_STORE_V1\n"
 Schema = "forge.fsa.witness-receipt.v1"
 MaxReceiptBytes = 4096
 MaxReceipts = 100000
)
var (
 ErrBlocked = errors.New("FORGE_FSA_WITNESS_STORE_BLOCKED")
 ErrConflict = errors.New("FORGE_FSA_WITNESS_REVISION_CONFLICT")
 ErrIndeterminate = errors.New("FORGE_FSA_WITNESS_WRITE_INDETERMINATE")
)
type receipt struct {
 Schema string `json:"schema"`
 Ordinal uint64 `json:"ordinal"`
 PreviousSHA256 string `json:"previous_sha256"`
 Witness fsaremote.SignedWitness `json:"witness"`
 ReceiptSHA256 string `json:"receipt_sha256"`
}
type Store struct {
 root string
 pin fsaremote.Pin
}
func digest(data []byte)string{sum:=sha256.Sum256(data);return hex.EncodeToString(sum[:])}
func pinned(p fsaremote.Pin)bool{
 return len(p.ArchiveID)==64&&len(p.BindingSHA256)==64&&
  len(p.PublicKey)==ed25519.PublicKeySize&&len(p.WitnessPublicKey)==ed25519.PublicKeySize&&
  !bytes.Equal(p.PublicKey,p.WitnessPublicKey)&&p.AuthorityEpoch!=0&&
  p.KeyID!=""&&p.MinimumRevision!=0
}
func clonePin(p fsaremote.Pin)fsaremote.Pin{
 p.PublicKey=append(ed25519.PublicKey(nil),p.PublicKey...)
 p.WitnessPublicKey=append(ed25519.PublicKey(nil),p.WitnessPublicKey...)
 return p
}
func anchor(p fsaremote.Pin,w fsaremote.SignedWitness)fsahead.Anchor{
 h:=w.Head
 return fsahead.Anchor{ArchiveID:h.ArchiveID,KeyID:h.KeyID,
  PublicKey:p.PublicKey,AuthorityEpoch:h.AuthorityEpoch,
  Sequence:h.Sequence,HeadSHA256:h.HeadSHA256}
}
func verify(p fsaremote.Pin,w fsaremote.SignedWitness)error{
 if !pinned(p)||fsaremote.VerifyWitness(p,w,anchor(p,w))!=nil{return ErrBlocked}
 return nil
}
func safeRoot(path string)(string,error){
 if !filepath.IsAbs(path)||filepath.Base(filepath.Clean(path))!=FolderName{return "",ErrBlocked}
 root:=filepath.Clean(path)
 for _,segment:=range strings.FieldsFunc(strings.ToLower(root),func(c rune)bool{return c=='/'||c=='\\'}){
  switch segment{
  case "ckbr","ckb-plane","ktrade","mind-palace","forge-research-archive","forge-fsa-trust":
   return "",ErrBlocked
  }
 }
 for p:=filepath.Dir(root);;{
  info,err:=os.Lstat(p)
  if err!=nil||!info.IsDir()||info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return "",ErrBlocked}
  next:=filepath.Dir(p);if next==p{break};p=next
 }
 return root,nil
}
func regular(path string,dir bool)error{
 info,err:=os.Lstat(path)
 if err!=nil{return ErrBlocked}
 if info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return ErrBlocked}
 if dir&& !info.IsDir()||!dir&& !info.Mode().IsRegular(){return ErrBlocked}
 return nil
}
func syncDir(path string)error{
 f,err:=os.Open(path);if err!=nil{return err};defer f.Close()
 if err=f.Sync();err!=nil&&runtime.GOOS!="windows"{return err}
 return nil
}
func createOnce(path string,data []byte)error{
 if len(data)==0||len(data)>MaxReceiptBytes{return ErrBlocked}
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return err}
 n,err:=f.Write(data)
 if err==nil&&n!=len(data){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil{return err};if closeErr!=nil{return closeErr}
 return syncDir(filepath.Dir(path))
}
func fileName(ordinal int)string{return fmt.Sprintf("%08d.json",ordinal)}
func seal(r receipt)(receipt,error){
 r.ReceiptSHA256=""
 raw,err:=json.Marshal(r);if err!=nil{return receipt{},err}
 r.ReceiptSHA256=digest(raw)
 return r,nil
}
func canonical(r receipt)([]byte,error){return json.Marshal(r)}
func layout(root string)error{
 if regular(root,true)!=nil||regular(filepath.Join(root,"receipts"),true)!=nil||
  regular(filepath.Join(root,".forge-fsa-witness-v1"),false)!=nil{return ErrBlocked}
 marker,err:=os.ReadFile(filepath.Join(root,".forge-fsa-witness-v1"))
 if err!=nil||string(marker)!=Marker{return ErrBlocked}
 entries,err:=os.ReadDir(root)
 if err!=nil||len(entries)!=2{return ErrBlocked}
 for _,e:=range entries{
  if e.Name()!="receipts"&&e.Name()!=".forge-fsa-witness-v1"{return ErrBlocked}
 }
 return nil
}
// Provision requires a BRAND NEW separate root and independently signed
// genesis witness; it never generates or possesses the witness signing key.
// Test roots do not establish separate physical failure domains.
func Provision(root string,pin fsaremote.Pin,genesis fsaremote.SignedWitness)(*Store,error){
 if verify(pin,genesis)!=nil{return nil,ErrBlocked}
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 if err=os.Mkdir(clean,0700);err!=nil{return nil,err}
 if err=createOnce(filepath.Join(clean,".forge-fsa-witness-v1"),[]byte(Marker));err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"receipts"),0700);err!=nil{return nil,err}
 r,err:=seal(receipt{Schema:Schema,Ordinal:0,PreviousSHA256:researchlog.Genesis,Witness:genesis})
 if err!=nil{return nil,err}
 raw,err:=canonical(r);if err!=nil{return nil,err}
 if err=createOnce(filepath.Join(clean,"receipts",fileName(0)),raw);err!=nil{return nil,err}
 return Open(clean,pin)
}
// Open requires a separately pinned MINIMUM revision on EVERY restart.
// A locally restored older but otherwise valid receipt directory cannot
// prove rollback resistance without an external current revision floor.
func Open(root string,pin fsaremote.Pin)(*Store,error){
 if !pinned(pin){return nil,ErrBlocked}
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 s:=&Store{root:clean,pin:clonePin(pin)}
 if _,_,err:=s.load();err!=nil{return nil,err}
 return s,nil
}
func (s *Store)load()(fsaremote.SignedWitness,int,error){
 if s==nil{return fsaremote.SignedWitness{},0,ErrBlocked}
 if _,err:=safeRoot(s.root);err!=nil{return fsaremote.SignedWitness{},0,err}
 if layout(s.root)!=nil{return fsaremote.SignedWitness{},0,ErrBlocked}
 dir:=filepath.Join(s.root,"receipts")
 entries,err:=os.ReadDir(dir)
 if err!=nil||len(entries)==0||len(entries)>MaxReceipts{return fsaremote.SignedWitness{},0,ErrBlocked}
 previousSHA:=researchlog.Genesis
 var last fsaremote.SignedWitness
 for i:=0;i<len(entries);i++{
  path:=filepath.Join(dir,fileName(i))
  if regular(path,false)!=nil{return fsaremote.SignedWitness{},0,ErrBlocked}
  f,err:=os.Open(path);if err!=nil{return fsaremote.SignedWitness{},0,ErrBlocked}
  raw,readErr:=io.ReadAll(io.LimitReader(f,MaxReceiptBytes+1));closeErr:=f.Close()
  if readErr!=nil||closeErr!=nil||len(raw)==0||len(raw)>MaxReceiptBytes{return fsaremote.SignedWitness{},0,ErrBlocked}
  var r receipt
  if json.Unmarshal(raw,&r)!=nil{return fsaremote.SignedWitness{},0,ErrBlocked}
  normalized,err:=canonical(r)
  if err!=nil||!bytes.Equal(raw,normalized)||r.Schema!=Schema||
   r.Ordinal!=uint64(i)||r.PreviousSHA256!=previousSHA||
   len(r.ReceiptSHA256)!=64{return fsaremote.SignedWitness{},0,ErrBlocked}
  computed,err:=seal(r)
  historicalPin:=s.pin
  historicalPin.MinimumRevision=1 // independently pinned floor applies to the LAST retained revision
  if err!=nil||computed.ReceiptSHA256!=r.ReceiptSHA256||verify(historicalPin,r.Witness)!=nil{
   return fsaremote.SignedWitness{},0,ErrBlocked
  }
  if i>0&&!advances(last,r.Witness){return fsaremote.SignedWitness{},0,ErrBlocked}
  previousSHA=r.ReceiptSHA256
  last=r.Witness
 }
 if last.Head.Revision<s.pin.MinimumRevision{return fsaremote.SignedWitness{},0,ErrBlocked}
 return last,len(entries),nil
}
func advances(old,next fsaremote.SignedWitness)bool{
 a,b:=old.Head,next.Head
 if b.Revision<=a.Revision||b.Sequence<a.Sequence{return false}
 if b.Sequence==a.Sequence{return b.HeadSHA256==a.HeadSHA256}
 return b.HeadSHA256!=a.HeadSHA256
}
// ReadWitness implements fsaservice.WitnessStore. Each read fully verifies
// canonical receipts, hash continuity, monotonic revisions, and signatures.
func (s *Store)ReadWitness(ctx context.Context,archiveID string)(fsaremote.SignedWitness,error){
 if ctx==nil||ctx.Err()!=nil||s==nil||archiveID!=s.pin.ArchiveID{
  return fsaremote.SignedWitness{},ErrBlocked
 }
 w,_,err:=s.load()
 if err!=nil||ctx.Err()!=nil{return fsaremote.SignedWitness{},ErrBlocked}
 return w,nil
}
// Append retains an already signed, independently issued revision exactly
// once. Any ambiguous write outcome is terminal until read-only reconciliation;
// it MUST NOT cause automatic signing, retry, or scientific execution.
func (s *Store)Append(ctx context.Context,next fsaremote.SignedWitness)error{
 if ctx==nil||ctx.Err()!=nil||s==nil||verify(s.pin,next)!=nil{return ErrBlocked}
 old,n,err:=s.load()
 if err!=nil{return ErrBlocked}
 if n>=MaxReceipts||!advances(old,next){return ErrConflict}
 // Recheck the immutable predecessor immediately before exclusive creation.
 current,count,err:=s.load()
 if err!=nil{return ErrBlocked}
 if count!=n||current.Head!=old.Head||current.SignatureHex!=old.SignatureHex{return ErrConflict}
 previousPath:=filepath.Join(s.root,"receipts",fileName(n-1))
 raw,err:=os.ReadFile(previousPath)
 if err!=nil||len(raw)>MaxReceiptBytes{return ErrBlocked}
 var previous receipt
 if json.Unmarshal(raw,&previous)!=nil||previous.Witness.Head!=old.Head||
  previous.Witness.SignatureHex!=old.SignatureHex{return ErrConflict}
 r,err:=seal(receipt{Schema:Schema,Ordinal:uint64(n),
  PreviousSHA256:previous.ReceiptSHA256,Witness:next})
 if err!=nil{return ErrBlocked}
 data,err:=canonical(r);if err!=nil{return ErrBlocked}
 if ctx.Err()!=nil{return ErrBlocked}
 path:=filepath.Join(s.root,"receipts",fileName(n))
 if err=createOnce(path,data);err!=nil{
  if errors.Is(err,os.ErrExist){return ErrConflict}
  return ErrIndeterminate
 }
 // Recheck exactly the expected committed witness on disk before success.
 current,count,err=s.load()
 if err!=nil||count!=n+1||current.Head!=next.Head||
  current.SignatureHex!=next.SignatureHex{return ErrIndeterminate}
 return nil
}
