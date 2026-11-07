// Package researchstatepreview models a third, prospective Hybrid lane without
// modifying the immutable two-lane researchstate v1 schema or replay rules.
// All outputs are offline, advisory and non-executing.
package researchstatepreview

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "sort"
 "github.com/spoonman136668-ai/forge/researchstate"
)

const (
 Schema = "forge.science.three-lane-preview.v1"
 EventSchema = "forge.science.hybrid-preview-event.v1"
 Mode = "READ_ONLY_PROSPECTIVE_NO_EXECUTION_OR_SCIENCE"
 MaxEvents = 1024
)
var ErrBlocked = errors.New("FORGE_HYBRID_PROSPECTIVE_LIFECYCLE_BLOCKED")

type Phase string
const (
 Observed Phase = "OBSERVED"
 ProtocolFrozen Phase = "PROTOCOL_FROZEN"
 EngineeringChecked Phase = "ENGINEERING_CHECKED"
 Blocked Phase = "BLOCKED"
)
type LegacyRecord struct {
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 Phase researchstate.Phase `json:"phase"`
}
type Event struct {
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 PreviousSHA256 string `json:"previous_sha256"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 From Phase `json:"from"`
 To Phase `json:"to"`
 RecordSHA256 string `json:"record_sha256"`
}
type Preview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 LegacyHeadSHA256 string `json:"legacy_head_sha256"`
 LegacyJournalSHA256 string `json:"legacy_journal_sha256"`
 LegacyCount uint64 `json:"legacy_count"`
 Legacy []LegacyRecord `json:"legacy"`
 Hybrid []Event `json:"hybrid"`
 HybridHeadSHA256 string `json:"hybrid_head_sha256"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 FirstUseAuthenticated bool `json:"first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
func hex64(s string)bool {
 if len(s)!=64{return false}
 for _,c:=range s {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func validID(s string)bool {
 if len(s)==0||len(s)>96{return false}
 for _,c:=range s {
  if !((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'){return false}
 }
 return true
}
func sha(prefix string,b []byte)string {
 s:=sha256.Sum256(append([]byte(prefix),b...))
 return hex.EncodeToString(s[:])
}
func eventSHA(e Event)string {
 e.RecordSHA256=""
 b,_:=json.Marshal(e)
 return sha("FORGE-HYBRID-V1-EVENT\n",b)
}
func allowed(from,to Phase)bool {
 switch from{
 case "":return to==Observed
 case Observed:return to==ProtocolFrozen||to==Blocked
 case ProtocolFrozen:return to==EngineeringChecked||to==Blocked
 case EngineeringChecked:return to==Blocked
 default:return false
 }
}
func legacyDigest(j researchstate.Journal,head string)(string,[]LegacyRecord,error){
 if !hex64(head)||researchstate.Verify(j)!=nil{return "",nil,ErrBlocked}
 actual,err:=researchstate.Head(j)
 if err!=nil||actual!=head{return "",nil,ErrBlocked}
 encoded,err:=json.Marshal(j)
 if err!=nil{return "",nil,ErrBlocked}
 latest:=map[string]LegacyRecord{}
 for _,e:=range j.Entries{
  latest[e.Lane+":"+e.ExperimentID]=LegacyRecord{e.Lane,e.ExperimentID,e.To}
 }
 keys:=make([]string,0,len(latest))
 for key:=range latest{keys=append(keys,key)}
 sort.Strings(keys)
 records:=make([]LegacyRecord,0,len(keys))
 for _,key:=range keys{records=append(records,latest[key])}
 return sha("FORGE-LEGACY-TWO-LANE-JOURNAL-V1\n",encoded),records,nil
}
// Build validates the entire legacy journal and independently chained Hybrid
// events. Its phases cannot grant scientific status or execution eligibility.
func Build(j researchstate.Journal,expectedHead string,events []Event)(Preview,error){
 var zero Preview
 digest,old,err:=legacyDigest(j,expectedHead)
 if err!=nil||len(events)>MaxEvents{return zero,ErrBlocked}
 head:=sha("FORGE-HYBRID-V1-GENESIS\n",[]byte(expectedHead+":"+digest))
 type state struct{phase Phase; protocol string}
 seen:=map[string]state{}
 copied:=make([]Event,0,len(events))
 for i,e:=range events{
  if e.Schema!=EventSchema||e.Sequence!=uint64(i+1)||
   e.PreviousSHA256!=head||e.Lane!="Hybrid"||!validID(e.ExperimentID)||
   !hex64(e.ProtocolSHA256)||!hex64(e.RecordSHA256)||e.RecordSHA256!=eventSHA(e){
   return zero,ErrBlocked
  }
  prev,exists:=seen[e.ExperimentID]
  if (!exists&&e.From!="")||(exists&&(prev.phase!=e.From||prev.protocol!=e.ProtocolSHA256))||
   !allowed(e.From,e.To){return zero,ErrBlocked}
  seen[e.ExperimentID]=state{e.To,e.ProtocolSHA256}
  copied=append(copied,e)
  head=e.RecordSHA256
 }
 return Preview{
  Schema:Schema,Mode:Mode,LegacyHeadSHA256:expectedHead,
  LegacyJournalSHA256:digest,LegacyCount:uint64(len(j.Entries)),
  Legacy:old,Hybrid:copied,HybridHeadSHA256:head,
 },nil
}
// Advance produces a new advisory preview; it does not persist or dispatch.
// A mutated/stale input preview, irreversible replay or protocol change fails.
func Advance(j researchstate.Journal,expectedHead string,prior Preview,e Event)(Preview,error){
 var zero Preview
 canonical,err:=Build(j,expectedHead,prior.Hybrid)
 if err!=nil{return zero,ErrBlocked}
 a,err:=json.Marshal(canonical);if err!=nil{return zero,ErrBlocked}
 b,err:=json.Marshal(prior);if err!=nil||!bytes.Equal(a,b){return zero,ErrBlocked}
 if len(prior.Hybrid)>=MaxEvents||e.Lane!="Hybrid"||
  !validID(e.ExperimentID)||!hex64(e.ProtocolSHA256){return zero,ErrBlocked}
 e.Schema=EventSchema
 e.Sequence=uint64(len(prior.Hybrid)+1)
 e.PreviousSHA256=prior.HybridHeadSHA256
 e.RecordSHA256=eventSHA(e)
 next:=append(append([]Event{},prior.Hybrid...),e)
 return Build(j,expectedHead,next)
}
