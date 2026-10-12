// Package researchstate implements an offline, append-only scientific lifecycle.
// No writer lease, authority service, worker launcher, or activation is provided.
package researchstate

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
)
const Schema="forge.science.lifecycle.v1"
const Genesis="0000000000000000000000000000000000000000000000000000000000000000"
var ErrBlocked=errors.New("FORGE_SCIENCE_TRANSITION_BLOCKED")
type Phase string
const (
 Proposed Phase="PROPOSED"
 Preregistered Phase="PREREGISTERED"
 Qualifying Phase="QUALIFYING"
 Qualified Phase="QUALIFIED"
 Authorized Phase="AUTHORIZED"
 Executing Phase="EXECUTING"
 EvidenceSealed Phase="EVIDENCE_SEALED"
 Classified Phase="CLASSIFIED"
 SuccessorReady Phase="SUCCESSOR_READY"
 Blocked Phase="BLOCKED"
 Quarantined Phase="QUARANTINED"
 Failed Phase="FAILED"
)
type Event struct {
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 PreviousSHA256 string `json:"previous_sha256"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 From Phase `json:"from"`
 To Phase `json:"to"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 IrreversibleRisk bool `json:"irreversible_risk"`
 RecordSHA256 string `json:"record_sha256"`
}
type Journal struct {Schema string `json:"schema"`; Entries []Event `json:"entries"`}
func New()Journal{return Journal{Schema:Schema,Entries:[]Event{}}}
func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='_'||c=='-'){return false}}
 return true
}
func permitted(from,to Phase)bool{
 switch from {
 case "":return to==Proposed
 case Proposed:return to==Preregistered||to==Blocked||to==Failed
 case Preregistered:return to==Qualifying||to==Blocked||to==Failed
 case Qualifying:return to==Qualified||to==Blocked||to==Failed
 case Qualified:return to==Authorized||to==Blocked
 case Authorized:return to==Executing||to==Quarantined
 case Executing:return to==EvidenceSealed||to==Quarantined
 case EvidenceSealed:return to==Classified||to==Quarantined
 case Classified:return to==SuccessorReady
 case Blocked:return to==Qualifying||to==Quarantined||to==Failed
 default:return false
 }
}
func digest(e Event)(string,error){
 e.RecordSHA256=""
 b,err:=json.Marshal(e);if err!=nil{return "",err}
 sum:=sha256.Sum256(append([]byte("FORGE-SCIENCE-LIFECYCLE-V1\n"),b...))
 return hex.EncodeToString(sum[:]),nil
}
type identity struct{lane,id,frozen string;phase Phase;risk bool}
func replay(j Journal)(map[string]identity,string,error){
 if j.Schema!=Schema||j.Entries==nil||len(j.Entries)>100000{return nil,"",ErrBlocked}
 known:=map[string]identity{}
 prev:=Genesis
 for n,e:=range j.Entries{
  if e.Schema!=Schema||e.Sequence!=uint64(n+1)||e.PreviousSHA256!=prev||
   !validID(e.ExperimentID)||!hex64(e.FrozenSHA256)||!hex64(e.RecordSHA256)||
   (e.Lane!="Wingless"&&e.Lane!="Yggdrasil") {return nil,"",fmt.Errorf("%w: malformed record %d",ErrBlocked,n)}
  hash,err:=digest(e);if err!=nil||hash!=e.RecordSHA256{return nil,"",ErrBlocked}
  key:=e.Lane+":"+e.ExperimentID
  old,exists:=known[key]
  if exists&&(old.frozen!=e.FrozenSHA256||old.phase!=e.From){return nil,"",ErrBlocked}
  if !exists&&e.From!=""{return nil,"",ErrBlocked}
  if !permitted(e.From,e.To){return nil,"",ErrBlocked}
  // Durable dispatch-risk MUST be recorded BEFORE any external first-use
  // attempt. Once seen, no transition back to authorization or execution.
  if e.To==Executing && (!e.IrreversibleRisk||!hex64(e.EvidenceSHA256)){return nil,"",ErrBlocked}
  if e.To==Quarantined&&(!hex64(e.EvidenceSHA256)||!e.IrreversibleRisk){return nil,"",ErrBlocked}
  if e.To==EvidenceSealed&&(!hex64(e.EvidenceSHA256)||!old.risk){return nil,"",ErrBlocked}
  if e.To==Classified&&(!hex64(e.EvidenceSHA256)||e.IrreversibleRisk){return nil,"",ErrBlocked}
  if (e.To==Qualified||e.To==Authorized||e.To==SuccessorReady)&&!hex64(e.EvidenceSHA256){return nil,"",ErrBlocked}
  if e.IrreversibleRisk&&e.To!=Executing&&e.To!=Quarantined{return nil,"",ErrBlocked}
  known[key]=identity{lane:e.Lane,id:e.ExperimentID,frozen:e.FrozenSHA256,phase:e.To,risk:old.risk||e.IrreversibleRisk}
  prev=hash
 }
 return known,prev,nil
}
func Verify(j Journal)error{_,_,err:=replay(j);return err}
func Append(j Journal, e Event, expectedHead string)(Journal,error){
 known,head,err:=replay(j);if err!=nil||!hex64(expectedHead)||head!=expectedHead{return Journal{},ErrBlocked}
 if len(j.Entries)>=100000{return Journal{},ErrBlocked}
 key:=e.Lane+":"+e.ExperimentID
 old,ok:=known[key]
 if ok&&(old.phase!=e.From||old.frozen!=e.FrozenSHA256){return Journal{},ErrBlocked}
 if !ok&&e.From!=""{return Journal{},ErrBlocked}
 e.Schema=Schema;e.Sequence=uint64(len(j.Entries)+1);e.PreviousSHA256=head;e.RecordSHA256=""
 e.RecordSHA256,err=digest(e);if err!=nil{return Journal{},err}
 out:=Journal{Schema:Schema,Entries:append(append([]Event{},j.Entries...),e)}
 if Verify(out)!=nil{return Journal{},ErrBlocked}
 return out,nil
}
func Head(j Journal)(string,error){_,head,err:=replay(j);return head,err}
// Status is observational only. It does not grant execution or acceptance.
func Status(j Journal,lane,id string)(Phase,bool,error){
 known,_,err:=replay(j);if err!=nil{return "",false,err}
 v,ok:=known[lane+":"+id];return v.phase,ok,nil
}
