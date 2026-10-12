package watchdog

import (
 "errors"
 "os"
 "path/filepath"
 "sort"
)

// SelectAndCommit gives the shadow observer restart-stable, idempotent
// incident selection. An exclusive lock prevents simultaneous local writers;
// a stale crash lock blocks until separately reconciled. It cannot grant
// scientific authority or automatically launch recovery.
func SelectAndCommit(directory string, incidents []Incident)([]Incident,error) {
 if directory==""||!filepath.IsAbs(directory){return nil,ErrPersistentLedger}
 if err:=os.MkdirAll(directory,0700);err!=nil{return nil,err}
 lockPath:=filepath.Join(directory,".shadow-writer.lock")
 lock,err:=os.OpenFile(lockPath,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return nil,ErrPersistentLedger}
 if err:=lock.Close();err!=nil{return nil,ErrPersistentLedger}
 // Only a normal, complete return releases ownership. On an uncertain
 // persistent write, retain the lock and fail closed for reconciliation.
 release:=false
 defer func(){if release{_ = os.Remove(lockPath)}}()
 ledger,err:=LoadPersistentForWriter(directory)
 if err!=nil{return nil,err}
 batch:=map[string]bool{}
 for _,incident:=range incidents{
  if incident.Lane!="Wingless"&&incident.Lane!="Yggdrasil"{return nil,ErrPersistentLedger}
  if incident.OriginalExperimentID==""||incident.OwnerEpoch==0||
   !validHash(incident.JournalHeadSHA256)||incident.Action==Healthy||
   incident.Action==""||incident.Action==Isolate{return nil,ErrPersistentLedger}
  key:=IncidentKey(incident)
  if batch[key]{return nil,ErrPersistentLedger}
  batch[key]=true
 }
 newIncidents:=[]Incident{}
 for _,incident:=range incidents{
  if !ledger.seen[IncidentKey(incident)]{newIncidents=append(newIncidents,incident)}
 }
 keys:=make([]string,0,len(ledger.seen)+len(newIncidents))
 for k:=range ledger.seen{keys=append(keys,k)}
 for _,incident:=range newIncidents{keys=append(keys,IncidentKey(incident))}
 sort.Strings(keys)
 if err:=ledger.CommitSnapshot(keys);err!=nil{return nil,err}
 release=true
 return newIncidents,nil
}
// Existing reader refuses unexpected files; accept the expected exclusive
// writer sentinel only when this call itself holds the sentinel.
func LoadPersistentForWriter(directory string)(*PersistentLedger,error){
 p,err:=LoadPersistent(directory)
 if err!=nil{return nil,err}
 if _,err=os.Stat(filepath.Join(directory,".shadow-writer.lock"));err!=nil{
  return nil,errors.Join(ErrPersistentLedger,err)
 }
 return p,nil
}
