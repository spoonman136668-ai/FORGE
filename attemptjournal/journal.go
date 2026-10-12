// Package attemptjournal implements write-once original-attempt custody.
// It is inactive and never launches experiments. A missing record is NOT
// evidence that a remote first-use is available for dispatch.
package attemptjournal
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
)
var ErrUnsafe=errors.New("FORGE_ORIGINAL_ATTEMPT_CUSTODY_UNSAFE")
const Schema="forge.original-attempt.v1"
type Record struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 OriginalRunID string `json:"original_run_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 IntentSHA256 string `json:"intent_sha256"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 WorkerID string `json:"worker_id"`
 ReceiptSHA256 string `json:"receipt_sha256"`
 State string `json:"state"`
}
func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func valid(s string)bool{
 if len(s)==0||len(s)>96{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='_'||c=='-'){return false}}
 return true
}
func check(r Record)error{
 if r.Schema!=Schema||(r.Lane!="Wingless"&&r.Lane!="Yggdrasil")||
 !valid(r.ExperimentID)||!valid(r.OriginalRunID)||!valid(r.WorkerID)||
 !hex64(r.FrozenSHA256)||!hex64(r.IntentSHA256)||r.OwnerEpoch==0||
 !hex64(r.ReceiptSHA256)||(r.State!="ORIGINAL_RISK_RECORDED"&&r.State!="TERMINAL_RECONCILED"){
 return ErrUnsafe
 }
 return nil
}
func filename(r Record)string{
 h:=sha256.Sum256([]byte(r.Lane+"\x00"+r.ExperimentID+"\x00"+r.OriginalRunID))
 return hex.EncodeToString(h[:])+".json"
}
// WriteOnce is only a local write-once record, NOT a linearizable distributed
// authority. On I/O ambiguity never delete or retry a consumed original.
func WriteOnce(root string,r Record)error{
 if err:=check(r);err!=nil{return err}
 stat,err:=os.Lstat(root)
 if err!=nil||!stat.IsDir()||stat.Mode()&os.ModeSymlink!=0{return ErrUnsafe}
 raw,err:=json.Marshal(r);if err!=nil{return ErrUnsafe}
 f,err:=os.OpenFile(filepath.Join(root,filename(r)),os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return ErrUnsafe}
 raw=append(raw,'\n')
 n,writeErr:=f.Write(raw)
 if writeErr==nil&&n!=len(raw){writeErr=io.ErrShortWrite}
 if writeErr==nil{writeErr=f.Sync()}
 closeErr:=f.Close()
 if writeErr!=nil||closeErr!=nil{return ErrUnsafe}
 dir,err:=os.Open(root);if err!=nil{return ErrUnsafe}
 syncErr:=dir.Sync();closeErr=dir.Close()
 if syncErr!=nil||closeErr!=nil{return ErrUnsafe}
 return nil
}
// Read checks exact original identity and canonical bytes. A missing entry
// always returns ErrUnsafe rather than granting replay eligibility.
func Read(root string,expected Record)(Record,error){
 if err:=check(expected);err!=nil{return Record{},err}
 path:=filepath.Join(root,filename(expected))
 stat,err:=os.Lstat(path)
 if err!=nil||!stat.Mode().IsRegular(){return Record{},ErrUnsafe}
 b,err:=os.ReadFile(path);if err!=nil||len(b)>4096{return Record{},ErrUnsafe}
 var got Record
 if err:=json.Unmarshal(b,&got);err!=nil{return Record{},ErrUnsafe}
 canonical,err:=json.Marshal(got);if err!=nil||string(b)!=string(append(canonical,'\n')){return Record{},ErrUnsafe}
 if err:=check(got);err!=nil{return Record{},err}
 if got!=expected{return Record{},fmt.Errorf("%w: custody drift",ErrUnsafe)}
 return got,nil
}
