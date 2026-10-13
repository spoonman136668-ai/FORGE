package watchdog

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
)
// DurableIncident is a fully identified advisory diagnosis. It is not a
// scientific dispatch or an authorization to repair or retry an original.
type DurableIncident struct {
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 PreviousSHA256 string `json:"previous_sha256"`
 Incident Incident `json:"incident"`
 RecordSHA256 string `json:"record_sha256"`
}
const incidentSchema="forge.shadow.incident.chain.v1"
const zeroHead="0000000000000000000000000000000000000000000000000000000000000000"
func digestRecord(r DurableIncident)(string,error){
 r.RecordSHA256=""
 b,err:=json.Marshal(r);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-SHADOW-INCIDENT-CHAIN-V1\n"),b...))
 return hex.EncodeToString(h[:]),nil
}
// VerifyIncidentChain rejects tampering and gaps before any recovery planner
// may use the historical incident record.
func VerifyIncidentChain(entries []DurableIncident)(string,error){
 head:=zeroHead
 for n,r:=range entries {
  if r.Schema!=incidentSchema||r.Sequence!=uint64(n+1)||
   r.PreviousSHA256!=head||!validHash(r.RecordSHA256)||
   r.Incident.OriginalExperimentID==""||!validHash(r.Incident.JournalHeadSHA256)||
   r.Incident.OwnerEpoch==0||
   (r.Incident.Lane!="Wingless"&&r.Incident.Lane!="Yggdrasil")||
   r.Incident.Action==Healthy||r.Incident.Action==""{return "",ErrPersistentLedger}
  d,err:=digestRecord(r)
  if err!=nil||d!=r.RecordSHA256{return "",ErrPersistentLedger}
  head=d
 }
 return head,nil
}
// AppendIncidentChain has no filesystem side effect; callers must separately
// persist through a real fenced atomic durable authority before action.
func AppendIncidentChain(entries []DurableIncident, incident Incident, expectedHead string)([]DurableIncident,error){
 head,err:=VerifyIncidentChain(entries)
 if err!=nil||head!=expectedHead||!validHash(head){return nil,ErrPersistentLedger}
 r:=DurableIncident{Schema:incidentSchema,Sequence:uint64(len(entries)+1),PreviousSHA256:head,Incident:incident}
 r.RecordSHA256,err=digestRecord(r)
 if err!=nil{return nil,err}
 next:=append(append([]DurableIncident{},entries...),r)
 if _,err:=VerifyIncidentChain(next);err!=nil{return nil,err}
 return next,nil
}
// ExportIncidentChain stores an inactive deterministic snapshot in a new file.
// It refuses overwrite; this is not a shared durable authority database.
func ExportIncidentChain(dir string,entries []DurableIncident)error{
 if dir==""||!filepath.IsAbs(dir){return ErrPersistentLedger}
 if _,err:=VerifyIncidentChain(entries);err!=nil{return err}
 b,err:=json.Marshal(entries);if err!=nil{return err}
 f,err:=os.OpenFile(filepath.Join(dir,"shadow-chain.v1.json"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return errors.Join(ErrPersistentLedger,err)}
 if _,err=f.Write(append(b,'\n'));err!=nil{f.Close();return err}
 if err=f.Sync();err!=nil{f.Close();return err}
 if err=f.Close();err!=nil{return fmt.Errorf("%w: %v",ErrPersistentLedger,err)}
 return nil
}
