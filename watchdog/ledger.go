package watchdog

import (
 "errors"
 "sync"
)
// IncidentLedger prevents repeated shadow observations from exhausting a
// recovery queue. It is a process-local advisory state, not the authoritative
// durable recovery database or an action executor.
type IncidentLedger struct{
 mu sync.Mutex
 seen map[string]bool
}
var ErrIncidentLedger=errors.New("FORGE_SHADOW_INCIDENT_LEDGER_INVALID")
func NewIncidentLedger()*IncidentLedger{return &IncidentLedger{seen:map[string]bool{}}}
// SelectNew is idempotent within a supervisor process. For deployment,
// decisions must be committed through independently fenced durable storage.
func(l *IncidentLedger)SelectNew(incidents []Incident)([]Incident,error){
 if l==nil{return nil,ErrIncidentLedger}
 l.mu.Lock();defer l.mu.Unlock()
 if l.seen==nil{return nil,ErrIncidentLedger}
 local:=map[string]bool{}
 for _,incident:=range incidents{
  if (incident.Lane!="Wingless"&&incident.Lane!="Yggdrasil")||
   incident.OriginalExperimentID==""||!validHash(incident.JournalHeadSHA256)||
   incident.OwnerEpoch==0||incident.Action==Healthy||incident.Action==""{
   return nil,ErrIncidentLedger
  }
  key:=IncidentKey(incident)
  if local[key]{return nil,ErrIncidentLedger}
  local[key]=true
 }
 out:=[]Incident{}
 for _,incident:=range incidents{
  k:=IncidentKey(incident)
  if l.seen[k]{continue}
  l.seen[k]=true
  out=append(out,incident)
 }
 return out,nil
}
