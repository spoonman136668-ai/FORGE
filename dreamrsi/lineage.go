package dreamrsi

// Local lineage retention is an unprivileged crash-recovery fixture. It is
// deliberately NOT an FSA journal, external monotonic floor, queue or
// scientific acceptance writer.
import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "runtime"
 "path/filepath"
 "sort"
 "strconv"
 "strings"
)
var ErrLineage=errors.New("FORGE_DREAMRSI_LOCAL_LINEAGE_CONFLICT_OR_TORN")
func readLineage(dir,lane string)([]PolicyRecord,error){
 entries,err:=os.ReadDir(dir)
 if errors.Is(err,os.ErrNotExist){return []PolicyRecord{},nil}
 if err!=nil{return nil,ErrLineage}
 var names []string
 for _,e:=range entries{
  if e.IsDir()||e.Type()&os.ModeSymlink!=0||!strings.HasSuffix(e.Name(),".json")||
   len(e.Name())!=11{return nil,ErrLineage}
  names=append(names,e.Name())
 }
 sort.Strings(names)
 records:=make([]PolicyRecord,0,len(names))
 for i,name:=range names{
  if name!=fmt.Sprintf("%06d.json",i+1){return nil,ErrLineage}
  path:=filepath.Join(dir,name)
  info,err:=os.Lstat(path)
  if err!=nil||!info.Mode().IsRegular()||info.Size()==0||info.Size()>100000{
   return nil,ErrLineage
  }
  b,err:=os.ReadFile(path)
  if err!=nil||len(b)>100000{return nil,ErrLineage}
  var r PolicyRecord
  d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
  if err=d.Decode(&r);err!=nil{return nil,ErrLineage}
  records=append(records,r)
 }
 if err:=ValidateRecords(records,lane);err!=nil{return nil,ErrLineage}
 return records,nil
}
func ReadLineage(dir,lane string)([]PolicyRecord,error){
 if !filepath.IsAbs(dir)||lane!="Wingless"&&lane!="Yggdrasil"{
  return nil,ErrLineage
 }
 s,err:=os.Lstat(dir)
 if err!=nil&&!errors.Is(err,os.ErrNotExist){return nil,ErrLineage}
 if err==nil&&(!s.IsDir()||s.Mode()&os.ModeSymlink!=0){return nil,ErrLineage}
 return readLineage(dir,lane)
}
// PersistLineage writes each record at a unique monotonically numbered path
// via exclusive creation. An interrupted write remains visible as torn and
// blocks all future writes; there is deliberately no implicit retry/replay.
// A competing writer may only observe identical content, never overwrite it.
func PersistLineage(dir string,records []PolicyRecord,lane string)error{
 if !filepath.IsAbs(dir)||lane!="Wingless"&&lane!="Yggdrasil"||
  len(records)==0||len(records)>2048||ValidateRecords(records,lane)!=nil{
  return ErrLineage
 }
 s,err:=os.Lstat(dir)
 if errors.Is(err,os.ErrNotExist){
  if err=os.Mkdir(dir,0700);err!=nil&&!errors.Is(err,os.ErrExist){return ErrLineage}
 }else if err!=nil{return ErrLineage}else if !s.IsDir()||s.Mode()&os.ModeSymlink!=0{
  return ErrLineage
 }
 existing,err:=ReadLineage(dir,lane);if err!=nil{return ErrLineage}
 if len(existing)>len(records){return ErrLineage}
 for i,r:=range existing{
  if r.RecordSHA256!=records[i].RecordSHA256{return ErrLineage}
 }
 for i:=len(existing);i<len(records);i++{
  p:=filepath.Join(dir,fmt.Sprintf("%06d.json",i+1))
  raw,err:=json.Marshal(records[i])
  if err!=nil||len(raw)>100000{return ErrLineage}
  f,err:=os.OpenFile(p,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
  if errors.Is(err,os.ErrExist){
   verify,readErr:=ReadLineage(dir,lane)
   if readErr!=nil||len(verify)<i+1||verify[i].RecordSHA256!=records[i].RecordSHA256{
    return ErrLineage
   }
   continue
  }
  if err!=nil{return ErrLineage}
  if _,err=f.Write(append(raw,'\n'));err!=nil{_ = f.Close();return ErrLineage}
  if err=f.Sync();err!=nil{_ = f.Close();return ErrLineage}
  if err=f.Close();err!=nil{return ErrLineage}
 }
 // Ensure directory entries reach disk where the filesystem supports it.
 dirfd,err:=os.Open(dir)
 if err!=nil{return ErrLineage}
 defer dirfd.Close()
 // Windows hosted filesystems do not support directory-handle Sync.
 // The individual exclusive-created files were flushed above; this does
 // NOT claim crash-proof directory persistence or rollback resistance.
 if err=dirfd.Sync();err!=nil&&runtime.GOOS!="windows"{return ErrLineage}
 complete,err:=ReadLineage(dir,lane)
 if err!=nil||len(complete)!=len(records){return ErrLineage}
 for i,r:=range complete{
  if r.RecordSHA256!=records[i].RecordSHA256{return ErrLineage}
 }
 return nil
}
type FSASelectionRequest struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 SourceHistorySHA256 string `json:"source_history_sha256"`
 FrozenSpecSHA256 string `json:"frozen_spec_sha256"`
 OptimizerLineageHeadSHA256 string `json:"optimizer_lineage_head_sha256"`
 PolicySHA256 string `json:"policy_sha256"`
 CandidateID string `json:"candidate_id"`
 CandidateCohortSHA256 string `json:"candidate_cohort_sha256"`
 PreregisteredCandidate bool `json:"preregistered_candidate"`
 ProvenanceVerifiedByFSA bool `json:"provenance_verified_by_fsa"`
 ScientificAdmitted bool `json:"scientific_admitted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 ExternalGeneralizationClaim bool `json:"external_generalization_claim"`
}
func ProposeSelection(o Optimization,decision Decision)(FSASelectionRequest,error){
 var zero FSASelectionRequest
 if ValidateOptimization(o)!=nil||!o.QualifiedForProspectiveTest||
  o.Selected.Lane!=o.Lane||!validHex(decision.ContextSHA256,64){
  return zero,ErrFrozen
 }
 id,err:=Select(o.Selected,decision)
 if err!=nil{return zero,err}
 var option *Option
 for i:=range decision.Options{if decision.Options[i].ID==id{option=&decision.Options[i];break}}
 if option==nil||!validOption(*option){return zero,ErrEvidence}
 // This is intentionally only an external input to a separately installed
 // FORGE Scientific Authority; it cannot itself preregister or schedule.
 return FSASelectionRequest{
  Schema:ContractSchema,Mode:"UNPRIVILEGED_FSA_REVIEW_REQUEST",
  Lane:o.Lane,SourceHistorySHA256:o.ValidationSHA256,
  FrozenSpecSHA256:o.FrozenSpecSHA256,
  OptimizerLineageHeadSHA256:o.LineageHeadSHA256,
  PolicySHA256:o.SelectedPolicySHA256,
  CandidateID:option.ID,CandidateCohortSHA256:option.CohortSHA256,
 },nil
}
func ValidateFSARequest(r FSASelectionRequest)error{
 if r.Schema!=ContractSchema||r.Mode!="UNPRIVILEGED_FSA_REVIEW_REQUEST"||
  r.Lane!="Wingless"&&r.Lane!="Yggdrasil"||!validHex(r.SourceHistorySHA256,64)||
  !validHex(r.FrozenSpecSHA256,64)||!validHex(r.OptimizerLineageHeadSHA256,64)||
  !validHex(r.PolicySHA256,64)||!validID(r.CandidateID)||
  !validHex(r.CandidateCohortSHA256,64)||r.PreregisteredCandidate||
  r.ProvenanceVerifiedByFSA||r.ScientificAdmitted||r.DispatchAuthorized||
  r.AcceptedRefMutation||r.ExternalGeneralizationClaim{return ErrFrozen}
 return nil
}
func AssertLocalLineageName(s string)error{
 n,err:=strconv.Atoi(s)
 if err!=nil||n<1||n>2048{return ErrLineage}
 return nil
}
