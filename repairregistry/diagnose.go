package repairregistry

import (
 "errors"
 "os"
 "path/filepath"
 "sort"
 "strings"
)

// Query is an exact, advisory diagnostic lookup. It never approves repairs.
type Query struct {
 Repository string
 Component string
 FailureSignature string
 Scope string
 Preconditions []string
}
type Finding struct {
 RecordSHA256 string `json:"record_sha256"`
 IncidentID string `json:"incident_id"`
 RepairCommit string `json:"repair_commit"`
 QualifiedRun string `json:"qualified_run"`
 Disposition string `json:"disposition"`
}
const AdvisoryOnly="REFERENCE_ONLY_INDEPENDENT_QUALIFICATION_REQUIRED"

// Diagnose fails closed if ANY registry entry is malformed, renamed,
// unexpected, or cannot be validated. Never silently skip broken evidence.
func Diagnose(root string,q Query)([]Finding,error){
 if !safe(q.Repository)||!safe(q.Component)||!safe(q.FailureSignature)||
 !safe(q.Scope)||!validStrings(q.Preconditions){return nil,ErrBlocked}
 info,err:=os.Lstat(root)
 if err!=nil||!info.IsDir()||info.Mode()&os.ModeSymlink!=0{return nil,ErrBlocked}
 entries,err:=os.ReadDir(root);if err!=nil||len(entries)>4096{return nil,ErrBlocked}
 found:=make([]Finding,0)
 for _,entry:=range entries{
  name:=entry.Name()
  if entry.IsDir()||!strings.HasSuffix(name,".json")||!lowerHex(strings.TrimSuffix(name,".json"),64){return nil,ErrBlocked}
  incident,err:=ReadFile(filepath.Join(root,name))
  if err!=nil||incident.RecordSHA256+".json"!=name{return nil,ErrBlocked}
  if !Match(incident,q.Repository,q.Component,q.FailureSignature,q.Scope,q.Preconditions){continue}
  found=append(found,Finding{RecordSHA256:incident.RecordSHA256,IncidentID:incident.ID,
   RepairCommit:incident.RepairCommit,QualifiedRun:incident.QualifiedRun,Disposition:AdvisoryOnly})
 }
 sort.Slice(found,func(i,j int)bool{return found[i].RecordSHA256<found[j].RecordSHA256})
 if len(found)>64{return nil,errors.Join(ErrBlocked,errors.New("too many advisory matches"))}
 return found,nil
}
