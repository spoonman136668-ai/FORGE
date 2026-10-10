// Package researchlog validates FORGE's offline scientific journal. This is
// structural recordkeeping, not evidence authentication, science acceptance,
// execution, scheduling, durable writing, or Mind-Palace ingestion.
package researchlog

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strings"
)

const (
 Schema = "forge.research-journal.v1"
 MemoryCandidateSchema = "forge.memory-milestone-candidate.v1"
 Genesis = "0000000000000000000000000000000000000000000000000000000000000000"
 MaxEntries = 2048
)
type Kind string
const (
 Hypothesis Kind = "HYPOTHESIS"
 Preregister Kind = "PREREGISTERED"
 SourceQualified Kind = "SOURCE_QUALIFIED"
 SourceRepair Kind = "SOURCE_REPAIR_REQUIRES_REQUALIFICATION"
 PrimaryStarted Kind = "PRIMARY_STARTED"
 PrimaryTerminal Kind = "PRIMARY_TERMINAL"
 IndependentReview Kind = "INDEPENDENT_REVIEW"
 FinalArchive Kind = "FINAL_ARCHIVE"
)
type Event struct {
 Lane string `json:"lane"`
 Generation uint64 `json:"generation"`
 ExperimentID string `json:"experiment_id"`
 Kind Kind `json:"kind"`
 SourceCommitSHA string `json:"source_commit_sha"`
 PreregSHA256 string `json:"prereg_sha256,omitempty"`
 CohortSHA256 string `json:"cohort_sha256,omitempty"`
 WitnessSHA256 string `json:"witness_sha256,omitempty"`
 OriginalEvidenceSHA256 string `json:"original_evidence_sha256,omitempty"`
 RunID uint64 `json:"run_id,omitempty"`
 Outcome string `json:"outcome,omitempty"`
 Note string `json:"note,omitempty"`
}
type Record struct {
 Schema string `json:"schema"`
 Sequence uint64 `json:"sequence"`
 PreviousSHA256 string `json:"previous_sha256"`
 Event Event `json:"event"`
 RecordSHA256 string `json:"record_sha256"`
}
type Journal struct {
 Schema string `json:"schema"`
 Entries []Record `json:"entries"`
}
type phase struct {
 kind Kind
 prereg,cohort,qualifiedSource,evidence,outcome string
 startedRun,generation uint64
}
func validHex(s string,n int)bool {
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func validID(s string)bool {
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{
  if !((c>='0'&&c<='9')||(c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'||c=='-'){return false}
 }
 return true
}
func hashRecord(r Record)(string,error){
 r.RecordSHA256=""
 b,err:=json.Marshal(r);if err!=nil{return "",err}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil
}
func validOutcome(x string)bool {
 switch x {case "SUPPORTED","MIXED","NEGATIVE","INVALID","CONSUMED_INDETERMINATE":return true}
 return false
}
func validateEvent(e Event)error{
 if (e.Lane!="Wingless"&&e.Lane!="Yggdrasil")||e.Generation==0||e.Generation>1000000000||!validID(e.ExperimentID)||!validHex(e.SourceCommitSHA,40){return errors.New("FORGE_JOURNAL_EVENT_IDENTITY")}
 if len(e.Note)>240||strings.ContainsAny(e.Note,"\r\n\x00"){return errors.New("FORGE_JOURNAL_NOTE_BOUNDS")}
 for _,h:=range []string{e.PreregSHA256,e.CohortSHA256,e.WitnessSHA256,e.OriginalEvidenceSHA256}{
  if h!=""&&!validHex(h,64){return errors.New("FORGE_JOURNAL_EVIDENCE_DIGEST_INVALID")}
 }
 switch e.Kind {
 case Hypothesis:
  if e.PreregSHA256!=""||e.CohortSHA256!=""||e.WitnessSHA256!=""||e.OriginalEvidenceSHA256!=""||e.RunID!=0||e.Outcome!=""{return errors.New("FORGE_JOURNAL_HYPOTHESIS_OVERREACH")}
 case Preregister:
  if e.PreregSHA256==""||e.CohortSHA256==""||e.WitnessSHA256!=""||e.OriginalEvidenceSHA256!=""||e.RunID!=0||e.Outcome!=""{return errors.New("FORGE_JOURNAL_FREEZE_INCOMPLETE")}
 case SourceQualified,SourceRepair:
  if e.PreregSHA256==""||e.CohortSHA256==""||e.WitnessSHA256==""||e.OriginalEvidenceSHA256!=""||e.RunID!=0||e.Outcome!=""{return errors.New("FORGE_JOURNAL_SOURCE_WITNESS_REQUIRED")}
 case PrimaryStarted:
  if e.PreregSHA256==""||e.CohortSHA256==""||e.WitnessSHA256==""||e.RunID==0||e.OriginalEvidenceSHA256!=""||e.Outcome!=""{return errors.New("FORGE_JOURNAL_START_RECEIPT_REQUIRED")}
 case PrimaryTerminal,IndependentReview,FinalArchive:
  if e.PreregSHA256==""||e.CohortSHA256==""||e.WitnessSHA256==""||e.RunID==0||e.OriginalEvidenceSHA256==""||!validOutcome(e.Outcome){return errors.New("FORGE_JOURNAL_ORIGINAL_TERMINAL_WITNESS_REQUIRED")}
 default:return errors.New("FORGE_JOURNAL_KIND_INVALID")
 }
 return nil
}
func checkTransition(e Event,current phase,cohorts map[string]string,key string)(phase,error){
 next:=current
 if current.kind==""{
  if e.Kind!=Hypothesis{return phase{},errors.New("FORGE_JOURNAL_HYPOTHESIS_REQUIRED")}
  next.kind=Hypothesis;next.generation=e.Generation;return next,nil
 }
 if current.generation!=e.Generation{return phase{},errors.New("FORGE_JOURNAL_GENERATION_DRIFT")}
 switch e.Kind{
 case Preregister:
  if current.kind!=Hypothesis{return phase{},errors.New("FORGE_JOURNAL_FREEZE_ORDER")}
  if owner,ok:=cohorts[e.CohortSHA256];ok&&owner!=key{return phase{},errors.New("FORGE_JOURNAL_COHORT_ALREADY_RESERVED")}
  next.prereg=e.PreregSHA256;next.cohort=e.CohortSHA256
 case SourceQualified:
  if current.kind!=Preregister&&current.kind!=SourceRepair{return phase{},errors.New("FORGE_JOURNAL_QUALIFICATION_ORDER")}
  next.qualifiedSource=e.SourceCommitSHA
 case SourceRepair:
  if current.kind!=SourceQualified{return phase{},errors.New("FORGE_JOURNAL_REPAIR_NOT_ALLOWED_AFTER_START")}
 case PrimaryStarted:
  if current.kind!=SourceQualified||e.SourceCommitSHA!=current.qualifiedSource{return phase{},errors.New("FORGE_JOURNAL_PRIMARY_MUST_BE_QUALIFIED")}
  next.startedRun=e.RunID
 case PrimaryTerminal:
  if current.kind!=PrimaryStarted||e.RunID!=current.startedRun{return phase{},errors.New("FORGE_JOURNAL_PRIMARY_NOT_STARTED_OR_RUN_CHANGED")}
  next.evidence=e.OriginalEvidenceSHA256;next.outcome=e.Outcome
 case IndependentReview:
  if current.kind!=PrimaryTerminal||e.RunID!=current.startedRun||e.OriginalEvidenceSHA256!=current.evidence||e.Outcome!=current.outcome{return phase{},errors.New("FORGE_JOURNAL_REVIEW_ORIGINAL_EVIDENCE_DRIFT")}
 case FinalArchive:
  if current.kind!=IndependentReview||e.RunID!=current.startedRun||e.OriginalEvidenceSHA256!=current.evidence||e.Outcome!=current.outcome{return phase{},errors.New("FORGE_JOURNAL_ARCHIVE_ORIGINAL_EVIDENCE_DRIFT")}
 default:return phase{},errors.New("FORGE_JOURNAL_TRANSITION_INVALID")
 }
 if e.Kind!=Preregister&&(e.PreregSHA256!=current.prereg||e.CohortSHA256!=current.cohort){return phase{},errors.New("FORGE_JOURNAL_PREREG_OR_COHORT_CHANGED")}
 next.kind=e.Kind;return next,nil
}
func New()Journal{return Journal{Schema:Schema,Entries:[]Record{}}}
// Verify checks hash order, legal scientific transitions, one-shot starts, and
// frozen identities. It cannot authenticate a purported external witness.
func Verify(j Journal)error{
 if j.Schema!=Schema||j.Entries==nil||len(j.Entries)>MaxEntries{return errors.New("FORGE_JOURNAL_SCHEMA_OR_BOUNDS")}
 phases:=map[string]phase{};cohorts:=map[string]string{};prev:=Genesis
 for i,r:=range j.Entries{
  if r.Schema!=Schema||r.Sequence!=uint64(i+1)||r.PreviousSHA256!=prev||!validHex(r.RecordSHA256,64){return fmt.Errorf("FORGE_JOURNAL_CHAIN_LINK_%d",i+1)}
  if err:=validateEvent(r.Event);err!=nil{return err}
  expected,err:=hashRecord(r);if err!=nil||expected!=r.RecordSHA256{return fmt.Errorf("FORGE_JOURNAL_HASH_MISMATCH_%d",i+1)}
  key:=r.Event.Lane+":"+r.Event.ExperimentID
  next,err:=checkTransition(r.Event,phases[key],cohorts,key);if err!=nil{return err}
  phases[key]=next
  if r.Event.Kind==Preregister{cohorts[r.Event.CohortSHA256]=key}
  prev=r.RecordSHA256
 }
 return nil
}
// Append produces a new in-memory journal. A future persistent store must
// atomically compare-and-swap the head, retain originals, and check trust.
func Append(j Journal,e Event)(Journal,error){
 if err:=Verify(j);err!=nil{return Journal{},err}
 if err:=validateEvent(e);err!=nil{return Journal{},err}
 if len(j.Entries)>=MaxEntries{return Journal{},errors.New("FORGE_JOURNAL_CAP_REACHED")}
 phases:=map[string]phase{};cohorts:=map[string]string{}
 for _,r:=range j.Entries{
  key:=r.Event.Lane+":"+r.Event.ExperimentID
  next,err:=checkTransition(r.Event,phases[key],cohorts,key);if err!=nil{return Journal{},err}
  phases[key]=next
  if r.Event.Kind==Preregister{cohorts[r.Event.CohortSHA256]=key}
 }
 key:=e.Lane+":"+e.ExperimentID
 if _,err:=checkTransition(e,phases[key],cohorts,key);err!=nil{return Journal{},err}
 prev:=Genesis;if len(j.Entries)>0{prev=j.Entries[len(j.Entries)-1].RecordSHA256}
 record:=Record{Schema:Schema,Sequence:uint64(len(j.Entries)+1),PreviousSHA256:prev,Event:e}
 var err error;record.RecordSHA256,err=hashRecord(record);if err!=nil{return Journal{},err}
 out:=Journal{Schema:Schema,Entries:make([]Record,len(j.Entries)+1)}
 copy(out.Entries,j.Entries);out.Entries[len(j.Entries)]=record
 return out,nil
}
type MemoryMilestone struct {
 Schema string `json:"schema"`
 Project string `json:"project"`
 ExperimentID string `json:"experiment_id"`
 Kind Kind `json:"kind"`
 Outcome string `json:"outcome"`
 Summary string `json:"summary"`
 ResearchRecordSHA256 string `json:"research_record_sha256"`
 OriginalEvidenceSHA256 string `json:"original_evidence_sha256"`
 IngestionStatus string `json:"ingestion_status"`
}
// ProposeMemoryMilestone is purely advisory; it cannot stage or commit a
// Mind-Palace record. The existing private classifier/checkpoint is mandatory.
func ProposeMemoryMilestone(j Journal,recordSHA string)(MemoryMilestone,error){
 if err:=Verify(j);err!=nil{return MemoryMilestone{},err}
 for _,r:=range j.Entries{
  if r.RecordSHA256!=recordSHA{continue}
  if r.Event.Kind!=IndependentReview&&r.Event.Kind!=FinalArchive{return MemoryMilestone{},errors.New("FORGE_MEMORY_PREMATURE_MILESTONE")}
  if r.Event.Note==""{return MemoryMilestone{},errors.New("FORGE_MEMORY_SUMMARY_MISSING")}
  return MemoryMilestone{Schema:MemoryCandidateSchema,Project:r.Event.Lane,ExperimentID:r.Event.ExperimentID,Kind:r.Event.Kind,Outcome:r.Event.Outcome,
   Summary:r.Event.Note,ResearchRecordSHA256:r.RecordSHA256,OriginalEvidenceSHA256:r.Event.OriginalEvidenceSHA256,IngestionStatus:"REVIEW_REQUIRED_NOT_STAGED"},nil
 }
 return MemoryMilestone{},errors.New("FORGE_MEMORY_RECORD_NOT_FOUND")
}
