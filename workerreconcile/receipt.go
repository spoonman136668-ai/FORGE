// Package workerreconcile verifies original execution receipts without
// granting dispatch authority or treating missing receipts as unused first-use.
package workerreconcile
import("crypto/ed25519";"crypto/sha256";"encoding/hex";"encoding/json";"errors")
const Schema="forge.worker.original-receipt.v1"
const prefix="FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"
var ErrBlocked=errors.New("FORGE_WORKER_RECEIPT_UNTRUSTED")
type Receipt struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 IntentSHA256 string `json:"intent_sha256"`
 OriginalRunID string `json:"original_run_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 WorkerID string `json:"worker_id"`
 Stage string `json:"stage"`
 EvidenceSHA256 string `json:"evidence_sha256"`
}
type Signed struct{Receipt Receipt `json:"receipt"`; SignatureHex string `json:"signature_hex"`}
type Expected struct {
 Lane,ExperimentID,FrozenSHA256,IntentSHA256,OriginalRunID,WorkerID string
 OwnerEpoch uint64
 WorkerPublicKey ed25519.PublicKey
}
func hex64(s string)bool{if len(s)!=64{return false};for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func Verify(s Signed,w Expected)error{
 r:=s.Receipt
 if len(w.WorkerPublicKey)!=ed25519.PublicKeySize||r.Schema!=Schema||
 (r.Lane!="Wingless"&&r.Lane!="Yggdrasil"&&r.Lane!="MassResearch")||r.Lane!=w.Lane||
 r.ExperimentID!=w.ExperimentID||r.ExperimentID==""||
 r.FrozenSHA256!=w.FrozenSHA256||!hex64(r.FrozenSHA256)||
 r.IntentSHA256!=w.IntentSHA256||!hex64(r.IntentSHA256)||
 r.OriginalRunID==""||r.OriginalRunID!=w.OriginalRunID||
 r.OwnerEpoch==0||r.OwnerEpoch!=w.OwnerEpoch||
 r.WorkerID==""||r.WorkerID!=w.WorkerID||
 (r.Stage!="STARTED"&&r.Stage!="TERMINAL")||
 (r.Stage=="STARTED"&&r.EvidenceSHA256!="")||
 (r.Stage=="TERMINAL"&&!hex64(r.EvidenceSHA256)){return ErrBlocked}
 raw,err:=json.Marshal(r);if err!=nil{return ErrBlocked}
 signature,err:=hex.DecodeString(s.SignatureHex)
 if err!=nil||len(signature)!=ed25519.SignatureSize||!ed25519.Verify(w.WorkerPublicKey,append([]byte(prefix),raw...),signature){return ErrBlocked}
 return nil
}
func Fingerprint(s Signed)(string,error){
 if s.Receipt.Schema!=Schema{return "",ErrBlocked}
 b,err:=json.Marshal(s.Receipt);if err!=nil{return "",err}
 sum:=sha256.Sum256(append([]byte(prefix),b...))
 return hex.EncodeToString(sum[:]),nil
}
type Disposition string
const(
 Unknown Disposition="INDETERMINATE_NO_REDISPATCH"
 Started Disposition="STARTED_NO_REDISPATCH"
 Terminal Disposition="TERMINAL_EVIDENCE_REVIEW_REQUIRED"
)
func Reconcile(w Expected,start,end *Signed)(Disposition,error){
 if start==nil&&end==nil{return Unknown,nil}
 if start!=nil{if err:=Verify(*start,w);err!=nil||start.Receipt.Stage!="STARTED"{return Unknown,ErrBlocked}}
 if end!=nil{if err:=Verify(*end,w);err!=nil||end.Receipt.Stage!="TERMINAL"{return Unknown,ErrBlocked};return Terminal,nil}
 return Started,nil
}
