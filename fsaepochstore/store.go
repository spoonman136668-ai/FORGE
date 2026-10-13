// Package fsaepochstore models a single-writer, append-only FSA owner-epoch
// and one-shot step journal. It is SOURCE-ONLY: local storage, not a deployed
// independent authority or a worker-side execution interlock.
package fsaepochstore

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
 FolderName = "forge-fsa-epoch-steps"
 Marker = "FORGE_FSA_EPOCH_STEP_JOURNAL_V1\n"
 JournalSchema = "forge.fsa.epoch-step-record.v1"
 TransferSchema = "forge.fsa.owner-transfer.v1"
 TransferDomain = "FORGE-FSA-OWNER-EPOCH-TRANSFER-V1\n"
 MaxRecordBytes = 8192
 MaxRecords = 4096
)
var (
 ErrBlocked = errors.New("FORGE_FSA_EPOCH_STEP_BLOCKED")
 ErrConsumed = errors.New("FORGE_FSA_EPOCH_STEP_ALREADY_CONSUMED")
 ErrIndeterminate = errors.New("FORGE_FSA_EPOCH_STEP_INDETERMINATE_NO_RETRY")
)
// Pin MUST be independently operator provisioned outside this directory.
// Neither a worker nor the recorded journal is allowed to supply this root.
type Pin struct {
 ArchiveID string
 AuthoritySequence uint64
 AuthorityHeadSHA256 string
 OwnerID string
 OwnerEpoch uint64
 TransferPublicKey ed25519.PublicKey
 StepReceiptPublicKey ed25519.PublicKey
 MinimumOrdinal uint64
}
// SignedTransfer must come from an independently provisioned transfer root.
// A transfer is not proof of CKB-plane revocation or authorization to run.
type SignedTransfer struct {
 Schema string
 ArchiveID string
 FromOwnerID string
 FromEpoch uint64
 ToOwnerID string
 ToEpoch uint64
 NonceSHA256 string
 SignatureHex string
}
type Snapshot struct {
 OwnerID string
 OwnerEpoch uint64
 Ordinal uint64
}
type record struct {
 Schema string
 Ordinal uint64
 PreviousSHA256 string
 Kind string
 Transfer *SignedTransfer
 Step *workerfence.SignedStepReceipt
 ReceiptSHA256 string
}
// TrustedClock MUST be implemented by a separately qualified authority
// service, never by an untrusted worker. Missing clock rejects consumption.
type TrustedClock interface { NowUnix(context.Context)(uint64,error) }
// ReceiptSigner MUST be separately provisioned; no keys or signing service
// are packaged in this public module. Signing errors forbid retry.
type ReceiptSigner interface { Sign(context.Context,[]byte)([]byte,error) }
type Store struct {
 root string
 pin Pin
 clock TrustedClock
 signer ReceiptSigner
 mu sync.Mutex
 observed uint64
 poisoned bool
}
func sha(data []byte)string{sum:=sha256.Sum256(data);return hex.EncodeToString(sum[:])}
func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func identifier(s string)bool{
 if len(s)<3||len(s)>96{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='_'||c=='-'){return false}}
 return true
}
func validPin(p Pin)bool{
 return hexLower(p.ArchiveID,64)&&hexLower(p.AuthorityHeadSHA256,64)&&
  p.OwnerEpoch>0&&strings.HasPrefix(p.OwnerID,"FORGE_")&&identifier(p.OwnerID)&&
  len(p.TransferPublicKey)==ed25519.PublicKeySize&&
  len(p.StepReceiptPublicKey)==ed25519.PublicKeySize&&
  !bytes.Equal(p.TransferPublicKey,p.StepReceiptPublicKey)&&
  p.MinimumOrdinal<=MaxRecords
}
func copyPin(p Pin)Pin{
 p.TransferPublicKey=append(ed25519.PublicKey(nil),p.TransferPublicKey...)
 p.StepReceiptPublicKey=append(ed25519.PublicKey(nil),p.StepReceiptPublicKey...)
 return p
}
func safeRoot(p string)(string,error){
 if !filepath.IsAbs(p)||filepath.Base(filepath.Clean(p))!=FolderName{return "",ErrBlocked}
 root:=filepath.Clean(p)
 for _,seg:=range strings.FieldsFunc(strings.ToLower(root),func(r rune)bool{return r=='/'||r=='\\'}){
  switch seg{
  case "ckbr","ckb-plane","ktrade","ktrade-external","mind-palace",
   "forge-research-archive","forge-fsa-trust","forge-fsa-witness","forge-fsa-step-custody":
   return "",ErrBlocked
  }
 }
 for parent:=filepath.Dir(root);;{
  info,err:=os.Lstat(parent)
  if err!=nil||!info.IsDir()||info.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return "",ErrBlocked}
  next:=filepath.Dir(parent);if next==parent{break};parent=next
 }
 return root,nil
}
func regular(path string,dir bool)bool{
 st,err:=os.Lstat(path)
 if err!=nil||st.Mode()&(os.ModeSymlink|os.ModeIrregular)!=0{return false}
 if dir{return st.IsDir()}
 return st.Mode().IsRegular()
}
func syncDir(p string)error{
 f,err:=os.Open(p);if err!=nil{return err}
 defer f.Close()
 if err=f.Sync();err!=nil&&runtime.GOOS!="windows"{return err}
 return nil
}
func writeOnce(p string,data []byte)error{
 if len(data)==0||len(data)>MaxRecordBytes{return ErrBlocked}
 f,err:=os.OpenFile(p,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return err}
 n,err:=f.Write(data)
 if err==nil&&n!=len(data){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closed:=f.Close()
 if err!=nil{return err}
 if closed!=nil{return closed}
 return syncDir(filepath.Dir(p))
}
func validateTransfer(p Pin,x SignedTransfer,owner string,epoch uint64)bool{
 if x.Schema!=TransferSchema||x.ArchiveID!=p.ArchiveID||
  x.FromOwnerID!=owner||x.FromEpoch!=epoch||
  !strings.HasPrefix(x.ToOwnerID,"FORGE_")||!identifier(x.ToOwnerID)||
  x.ToOwnerID==x.FromOwnerID||x.ToEpoch!=epoch+1||
  !hexLower(x.NonceSHA256,64)||!hexLower(x.SignatureHex,128){return false}
 sig,err:=hex.DecodeString(x.SignatureHex);if err!=nil{return false}
 x.SignatureHex=""
 b,err:=json.Marshal(x);if err!=nil{return false}
 return ed25519.Verify(p.TransferPublicKey,append([]byte(TransferDomain),b...),sig)
}
func validateStep(p Pin,r workerfence.SignedStepReceipt)bool{
 c:=r.Claim
 if r.Schema!=workerfence.StepReceiptSchema||r.Status!=workerfence.Consumed||
  c.Schema!=workerfence.StepSchema||c.ArchiveID!=p.ArchiveID||
  c.AuthoritySequence!=p.AuthoritySequence||
  c.AuthorityHeadSHA256!=p.AuthorityHeadSHA256||
  (c.Lane!="Wingless"&&c.Lane!="Yggdrasil")||!identifier(c.OriginalID)||
  !identifier(c.WorkerID)||!hexLower(c.IntentSHA256,64)||
  !hexLower(c.WorkerBinarySHA256,64)||!hexLower(c.StepSHA256,64)||
  c.OwnerEpoch==0||c.LeaseSequence==0||c.ExpiresAtUnix==0||
  !hexLower(r.SignatureHex,128){return false}
 sig,err:=hex.DecodeString(r.SignatureHex);if err!=nil{return false}
 r.SignatureHex=""
 b,err:=json.Marshal(r);if err!=nil{return false}
 return ed25519.Verify(p.StepReceiptPublicKey,append([]byte(workerfence.StepReceiptDomain),b...),sig)
}
func seal(r record)(record,error){
 r.ReceiptSHA256=""
 raw,err:=json.Marshal(r);if err!=nil{return record{},err}
 r.ReceiptSHA256=sha(append([]byte("FORGE-FSA-EPOCH-STEP-RECEIPT-V1\n"),raw...))
 return r,nil
}
func claimIdentity(c workerfence.StepClaim)string{
 // A step digest cannot be consumed by either lane more than once, even
 // if a worker presents a different lease or owner epoch after revocation.
 return c.StepSHA256
}
type loaded struct {
 owner string
 epoch uint64
 count uint64
 lastSHA string
 consumed map[string]bool
 lastLease map[string]uint64
 usedTransfers map[string]bool
}
func(s *Store)load()(loaded,error){
 var zero loaded
 if s==nil{return zero,ErrBlocked}
 if _,err:=safeRoot(s.root);err!=nil{return zero,ErrBlocked}
 if !regular(s.root,true)||!regular(filepath.Join(s.root,"records"),true)||
  !regular(filepath.Join(s.root,".forge-fsa-epoch-v1"),false){return zero,ErrBlocked}
 marker,err:=os.ReadFile(filepath.Join(s.root,".forge-fsa-epoch-v1"))
 if err!=nil||string(marker)!=Marker{return zero,ErrBlocked}
 dirs,err:=os.ReadDir(s.root)
 if err!=nil||len(dirs)!=2{return zero,ErrBlocked}
 for _,e:=range dirs{if e.Name()!="records"&&e.Name()!=".forge-fsa-epoch-v1"{return zero,ErrBlocked}}
 items,err:=os.ReadDir(filepath.Join(s.root,"records"))
 if err!=nil||len(items)>MaxRecords||uint64(len(items))<s.pin.MinimumOrdinal{return zero,ErrBlocked}
 state:=loaded{owner:s.pin.OwnerID,epoch:s.pin.OwnerEpoch,lastSHA:strings.Repeat("0",64),
  consumed:map[string]bool{},lastLease:map[string]uint64{},usedTransfers:map[string]bool{}}
 for i:=0;i<len(items);i++{
  path:=filepath.Join(s.root,"records",fmt.Sprintf("%08d.json",i+1))
  if !regular(path,false){return zero,ErrBlocked}
  f,err:=os.Open(path);if err!=nil{return zero,ErrBlocked}
  raw,readErr:=io.ReadAll(io.LimitReader(f,MaxRecordBytes+1));closeErr:=f.Close()
  if readErr!=nil||closeErr!=nil||len(raw)==0||len(raw)>MaxRecordBytes{return zero,ErrBlocked}
  var rec record
  if json.Unmarshal(raw,&rec)!=nil{return zero,ErrBlocked}
  canonical,err:=json.Marshal(rec)
  if err!=nil||!bytes.Equal(raw,canonical)||rec.Schema!=JournalSchema||
   rec.Ordinal!=uint64(i+1)||rec.PreviousSHA256!=state.lastSHA||
   !hexLower(rec.ReceiptSHA256,64){return zero,ErrBlocked}
  computed,err:=seal(rec)
  if err!=nil||computed.ReceiptSHA256!=rec.ReceiptSHA256{return zero,ErrBlocked}
  switch rec.Kind {
  case "TRANSFER":
   if rec.Transfer==nil||rec.Step!=nil||
    !validateTransfer(s.pin,*rec.Transfer,state.owner,state.epoch)||
    state.usedTransfers[rec.Transfer.NonceSHA256]{return zero,ErrBlocked}
   state.usedTransfers[rec.Transfer.NonceSHA256]=true
   state.owner=rec.Transfer.ToOwnerID
   state.epoch=rec.Transfer.ToEpoch
  case "STEP":
   if rec.Transfer!=nil||rec.Step==nil||!validateStep(s.pin,*rec.Step){return zero,ErrBlocked}
   c:=rec.Step.Claim
   id:=claimIdentity(c)
   worker:=c.Lane+":"+c.OriginalID+":"+c.WorkerID
   if c.OwnerID!=state.owner||c.OwnerEpoch!=state.epoch||
    state.consumed[id]||c.LeaseSequence<=state.lastLease[worker]{return zero,ErrBlocked}
   state.consumed[id]=true
   state.lastLease[worker]=c.LeaseSequence
  default:return zero,ErrBlocked
  }
  state.count++
  state.lastSHA=rec.ReceiptSHA256
 }
 return state,nil
}
func Provision(root string,pin Pin,clock TrustedClock,signer ReceiptSigner)(*Store,error){
 if !validPin(pin)||pin.MinimumOrdinal!=0{return nil,ErrBlocked}
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 if err=os.Mkdir(clean,0700);err!=nil{return nil,err}
 if err=writeOnce(filepath.Join(clean,".forge-fsa-epoch-v1"),[]byte(Marker));err!=nil{return nil,err}
 if err=os.Mkdir(filepath.Join(clean,"records"),0700);err!=nil{return nil,err}
 if err=syncDir(clean);err!=nil{return nil,err}
 return Open(clean,pin,clock,signer)
}
// Open requires the externally provided exact genesis, independent public
// keys, AND an externally verified minimum ordinal on every restart.
func Open(root string,pin Pin,clock TrustedClock,signer ReceiptSigner)(*Store,error){
 if !validPin(pin){return nil,ErrBlocked}
 clean,err:=safeRoot(root);if err!=nil{return nil,err}
 s:=&Store{root:clean,pin:copyPin(pin),clock:clock,signer:signer}
 state,err:=s.load();if err!=nil{return nil,err}
 s.observed=state.count
 return s,nil
}
func(s *Store)inspect()(loaded,error){
 var zero loaded
 if s.poisoned{return zero,ErrBlocked}
 state,err:=s.load()
 if err!=nil||state.count<s.observed{
  s.poisoned=true
  return zero,ErrBlocked
 }
 s.observed=state.count
 return state,nil
}
func(s *Store)append(ctx context.Context,state loaded,kind string,
 transfer *SignedTransfer,step *workerfence.SignedStepReceipt)error{
 if ctx.Err()!=nil{return ErrBlocked}
 rec,err:=seal(record{Schema:JournalSchema,Ordinal:state.count+1,
  PreviousSHA256:state.lastSHA,Kind:kind,Transfer:transfer,Step:step})
 if err!=nil{return ErrBlocked}
 raw,err:=json.Marshal(rec);if err!=nil{return ErrBlocked}
 path:=filepath.Join(s.root,"records",fmt.Sprintf("%08d.json",state.count+1))
 if err=writeOnce(path,raw);err!=nil{
  s.poisoned=true
  return ErrIndeterminate
 }
 verified,err:=s.load()
 if err!=nil||verified.count!=state.count+1{
  s.poisoned=true
  return ErrIndeterminate
 }
 s.observed=verified.count
 return nil
}
func(s *Store)Read(ctx context.Context)(Snapshot,error){
 if s==nil||ctx==nil||ctx.Err()!=nil{return Snapshot{},ErrBlocked}
 s.mu.Lock();defer s.mu.Unlock()
 state,err:=s.inspect()
 if err!=nil||ctx.Err()!=nil{return Snapshot{},ErrBlocked}
 return Snapshot{OwnerID:state.owner,OwnerEpoch:state.epoch,Ordinal:state.count},nil
}
// TransferOwner serializes the independently signed epoch promotion with
// competing step consumption in the same journal. A real old-owner revocation
// must be proven independently before issuing an authorization.
func(s *Store)TransferOwner(ctx context.Context,t SignedTransfer)error{
 if s==nil||ctx==nil||ctx.Err()!=nil{return ErrBlocked}
 s.mu.Lock();defer s.mu.Unlock()
 state,err:=s.inspect();if err!=nil{return ErrBlocked}
 if state.count>=MaxRecords||state.usedTransfers[t.NonceSHA256]||
  !validateTransfer(s.pin,t,state.owner,state.epoch){return ErrBlocked}
 return s.append(ctx,state,"TRANSFER",&t,nil)
}
// ConsumeOnce implements only the SOURCE-LEVEL contract. A local process
// mutex and filesystem O_EXCL are NOT a multi-node linearizable FSA backend.
func(s *Store)ConsumeOnce(ctx context.Context,c workerfence.StepClaim)(workerfence.SignedStepReceipt,error){
 var empty workerfence.SignedStepReceipt
 if s==nil||ctx==nil||ctx.Err()!=nil{return empty,ErrBlocked}
 s.mu.Lock();defer s.mu.Unlock()
 state,err:=s.inspect();if err!=nil{return empty,ErrBlocked}
 if s.signer==nil||s.clock==nil||state.count>=MaxRecords||
  c.Schema!=workerfence.StepSchema||c.ArchiveID!=s.pin.ArchiveID||
  c.AuthoritySequence!=s.pin.AuthoritySequence||
  c.AuthorityHeadSHA256!=s.pin.AuthorityHeadSHA256||
  c.OwnerID!=state.owner||c.OwnerEpoch!=state.epoch||
  !strings.HasPrefix(c.OwnerID,"FORGE_")||
  (c.Lane!="Wingless"&&c.Lane!="Yggdrasil")||
  !identifier(c.OriginalID)||!identifier(c.WorkerID)||
  !hexLower(c.IntentSHA256,64)||!hexLower(c.WorkerBinarySHA256,64)||
  !hexLower(c.StepSHA256,64)||c.LeaseSequence==0||c.ExpiresAtUnix==0{
  return empty,ErrBlocked
 }
 worker:=c.Lane+":"+c.OriginalID+":"+c.WorkerID
 if state.consumed[claimIdentity(c)]{return empty,ErrConsumed}
 if c.LeaseSequence<=state.lastLease[worker]{return empty,ErrBlocked}
 now,err:=s.clock.NowUnix(ctx)
 if err!=nil||now==0||now>=c.ExpiresAtUnix||ctx.Err()!=nil{return empty,ErrBlocked}
 rec:=workerfence.SignedStepReceipt{Schema:workerfence.StepReceiptSchema,
  Claim:c,Status:workerfence.Consumed}
 raw,err:=json.Marshal(rec);if err!=nil{return empty,ErrBlocked}
 signature,err:=s.signer.Sign(ctx,append([]byte(workerfence.StepReceiptDomain),raw...))
 if err!=nil||ctx.Err()!=nil{
  s.poisoned=true
  return empty,ErrIndeterminate
 }
 rec.SignatureHex=hex.EncodeToString(signature)
 if !validateStep(s.pin,rec){
  s.poisoned=true
  return empty,ErrIndeterminate
 }
 if err=s.append(ctx,state,"STEP",nil,&rec);err!=nil{return empty,err}
 return rec,nil
}
var _ workerfence.StepAuthority = (*Store)(nil)
