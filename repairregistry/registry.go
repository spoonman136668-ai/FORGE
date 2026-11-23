// Package repairregistry preserves bounded infrastructure failure/repair facts.
// Entries are immutable, content-addressed, and never authorize automated
// patches, changed scientific thresholds, worker starts or authority transfer.
package repairregistry

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "strings"
)
const Schema="forge.failure-repair.v1"
var ErrBlocked=errors.New("FORGE_REPAIR_REGISTRY_UNTRUSTED")
type Incident struct {
 Schema string `json:"schema"`
 ID string `json:"id"`
 Repository string `json:"repository"`
 Component string `json:"component"`
 FailureSignature string `json:"failure_signature"`
 Cause string `json:"confirmed_cause"`
 RepairCommit string `json:"repair_commit"`
 FailedRun string `json:"failed_run"`
 QualifiedRun string `json:"qualified_run"`
 Scope string `json:"applicability_scope"`
 Preconditions []string `json:"reuse_preconditions"`
 Prohibited []string `json:"prohibited_uses"`
 Status string `json:"status"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 RecordSHA256 string `json:"record_sha256"`
}
func lowerHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func safe(s string)bool{return len(s)>0&&len(s)<=1024&&strings.TrimSpace(s)==s}
func validStrings(ss []string)bool{
 if len(ss)==0||len(ss)>12{return false}
 for _,s:=range ss{if !safe(s){return false}}
 return true
}
func Digest(r Incident)(string,error){
 r.RecordSHA256=""
 b,err:=json.Marshal(r);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-FAILURE-REPAIR-V1\n"),b...))
 return hex.EncodeToString(h[:]),nil
}
func Verify(r Incident)error{
 if r.Schema!=Schema||!safe(r.ID)||!safe(r.Repository)||!safe(r.Component)||
 !safe(r.FailureSignature)||!safe(r.Cause)||!safe(r.Scope)||
 !safe(r.FailedRun)||!safe(r.QualifiedRun)||!lowerHex(r.RepairCommit,40)||
 !lowerHex(r.EvidenceSHA256,64)||!lowerHex(r.RecordSHA256,64)||
 !validStrings(r.Preconditions)||!validStrings(r.Prohibited)||
 (r.Status!="QUALIFIED_REPAIR"&&r.Status!="FAILED_REPAIR"&&r.Status!="UNRESOLVED"){
 return ErrBlocked
 }
 h,err:=Digest(r);if err!=nil||h!=r.RecordSHA256{return ErrBlocked}
 return nil
}
// Match is advisory and exact; even a match must be independently qualified.
// The return value is never an instruction or an authorization to edit files.
func Match(r Incident,repository,component,signature,scope string,preconditions []string)bool{
 if Verify(r)!=nil||r.Status!="QUALIFIED_REPAIR"||r.Repository!=repository||
 r.Component!=component||r.FailureSignature!=signature||r.Scope!=scope||
 len(preconditions)!=len(r.Preconditions){return false}
 for i,s:=range preconditions{if s!=r.Preconditions[i]{return false}}
 return true
}
// ReadFile denies noncanonical, oversized or unknown-field records.
func ReadFile(path string)(Incident,error){
 stat,err:=os.Lstat(path);if err!=nil||!stat.Mode().IsRegular()||stat.Size()>16384{return Incident{},ErrBlocked}
 raw,err:=os.ReadFile(path);if err!=nil{return Incident{},ErrBlocked}
 var r Incident
 dec:=json.NewDecoder(strings.NewReader(string(raw)));dec.DisallowUnknownFields()
 if err:=dec.Decode(&r);err!=nil{return Incident{},ErrBlocked}
 b,err:=json.MarshalIndent(r,"","  ")
 if err!=nil||string(raw)!=string(append(b,'\n'))||Verify(r)!=nil{return Incident{},ErrBlocked}
 return r,nil
}
// RecordOnce is local evidence custody only (O_EXCL, file sync), not a
// distributed registry or independent attestation.
func RecordOnce(dir string,r Incident)error{
 if Verify(r)!=nil{return ErrBlocked}
 info,err:=os.Lstat(dir);if err!=nil||!info.IsDir()||info.Mode()&os.ModeSymlink!=0{return ErrBlocked}
 name:=filepath.Join(dir,r.RecordSHA256+".json")
 b,err:=json.MarshalIndent(r,"","  ");if err!=nil{return err};b=append(b,'\n')
 f,err:=os.OpenFile(name,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return ErrBlocked}
 n,err:=f.Write(b);if err==nil&&n!=len(b){err=fmt.Errorf("short write")}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil||closeErr!=nil{return ErrBlocked}
 return nil
}
