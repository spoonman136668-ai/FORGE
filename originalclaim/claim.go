// Package originalclaim persistently records irreversible original first-use
// risk BEFORE a caller is allowed to attempt any worker start. It deliberately
// does not grant execution authority or implement network-wide CAS.
package originalclaim

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
 "runtime"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)
const Schema="forge.original.local-first-use-claim.v1"
var ErrBlocked=errors.New("FORGE_ORIGINAL_FIRST_USE_ALREADY_CONSUMED_OR_UNTRUSTED")
type Claim struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 IntentSHA256 string `json:"intent_sha256"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OriginalRunID string `json:"original_run_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 WorkerID string `json:"worker_id"`
 FirstUseConsumed bool `json:"first_use_consumed"`
}
type Assessment struct {
 ClaimVerified bool `json:"claim_verified"`
 Disposition workerreconcile.Disposition `json:"disposition"`
 RedispatchAuthorized bool `json:"redispatch_authorized"`
 IndependentResultAccepted bool `json:"independent_result_accepted"`
}
func hexN(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func valid(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'){return false}}
 return true
}
func validate(c Claim)bool{
 return c.Schema==Schema&&(c.Lane=="Wingless"||c.Lane=="Yggdrasil")&&
 valid(c.ExperimentID)&&valid(c.OriginalRunID)&&valid(c.WorkerID)&&
 hexN(c.FrozenSHA256,64)&&hexN(c.IntentSHA256,64)&&hexN(c.SourceCommitSHA,40)&&
 c.OwnerEpoch>0&&c.FirstUseConsumed
}
func path(root string,c Claim)string{
 digest:=sha256.Sum256([]byte(c.Lane+"\x00"+c.ExperimentID))
 return filepath.Join(root,hex.EncodeToString(digest[:])+".json")
}
func canonical(c Claim)([]byte,error){b,e:=json.Marshal(c);if e!=nil{return nil,ErrBlocked};return append(b,'\n'),nil}
func directory(root string)error{
 st,e:=os.Lstat(root);if e!=nil||!st.IsDir()||st.Mode()&os.ModeSymlink!=0{return ErrBlocked}
 return nil
}
func syncDir(root string)error{
 d,e:=os.Open(root);if e!=nil{return ErrBlocked}
 e=d.Sync();ce:=d.Close()
 if ce!=nil||(e!=nil&&runtime.GOOS!="windows"){return ErrBlocked}
 return nil
}
// Consume is write-once and leaves an uncertain claim in place on any error.
// The filesystem must itself be trusted, durable and single-writer; the
// function is NOT an independently operated distributed authority.
func Consume(root string,c Claim)error{
 if !validate(c)||directory(root)!=nil{return ErrBlocked}
 raw,e:=canonical(c);if e!=nil{return ErrBlocked}
 f,e:=os.OpenFile(path(root,c),os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if e!=nil{return ErrBlocked}
 n,writeErr:=f.Write(raw)
 if writeErr==nil&&n!=len(raw){writeErr=io.ErrShortWrite}
 if writeErr==nil{writeErr=f.Sync()}
 closeErr:=f.Close()
 if writeErr!=nil||closeErr!=nil||syncDir(root)!=nil{return ErrBlocked}
 return nil
}
func Read(root string,expected Claim)(Claim,error){
 if !validate(expected)||directory(root)!=nil{return Claim{},ErrBlocked}
 p:=path(root,expected)
 st,e:=os.Lstat(p);if e!=nil||!st.Mode().IsRegular()||st.Size()<1||st.Size()>4096{return Claim{},ErrBlocked}
 b,e:=os.ReadFile(p);if e!=nil{return Claim{},ErrBlocked}
 var found Claim
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if d.Decode(&found)!=nil||d.Decode(new(any))!=io.EOF||found!=expected{return Claim{},ErrBlocked}
 raw,e:=canonical(found);if e!=nil||!bytes.Equal(raw,b){return Claim{},ErrBlocked}
 return found,nil
}
// Assess confirms claim custody and separately signed STARTED/TERMINAL worker
// receipts. TERMINAL means evidence review is REQUIRED, not accepted science.
func Assess(root string,c Claim,expected workerreconcile.Expected,start,end *workerreconcile.Signed)(Assessment,error){
 if _,err:=Read(root,c);err!=nil{return Assessment{},ErrBlocked}
 if expected.Lane!=c.Lane||expected.ExperimentID!=c.ExperimentID||
 expected.FrozenSHA256!=c.FrozenSHA256||expected.IntentSHA256!=c.IntentSHA256||
 expected.OriginalRunID!=c.OriginalRunID||expected.OwnerEpoch!=c.OwnerEpoch||
 expected.WorkerID!=c.WorkerID{return Assessment{},ErrBlocked}
 state,err:=workerreconcile.Reconcile(expected,start,end)
 if err!=nil{return Assessment{},ErrBlocked}
 return Assessment{ClaimVerified:true,Disposition:state},nil
}
