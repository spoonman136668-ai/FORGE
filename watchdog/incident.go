package watchdog

// Incident ties a deterministic diagnostic to the exact authenticated
// observation that caused it. It is an advisory shadow-mode record only.
type Incident struct {
 Lane string
 OriginalExperimentID string
 JournalHeadSHA256 string
 OwnerEpoch uint64
 Action Action
 FirstUseRisk bool
}
// IncidentKey deliberately excludes wall clock, so repeated polling of the
// same exact observed state does not create an unbounded recovery queue.
func IncidentKey(i Incident) string {
 return i.Lane+":"+i.OriginalExperimentID+":"+i.JournalHeadSHA256+":"+
  formatEpoch(i.OwnerEpoch)+":"+string(i.Action)
}
func formatEpoch(v uint64)string {
 if v==0{return ""}
 const digits="0123456789"
 var b [20]byte;n:=len(b)
 for v>0{n--;b[n]=digits[v%10];v/=10}
 return string(b[n:])
}
func DiagnoseBoth(now uint64, observations []Observation)([]Incident,error){
 _,err:=AssessBoth(now,observations)
 if err!=nil{return nil,err}
 // Preserve deterministic ordering, regardless of input order.
 lanes:=[]string{"Wingless","Yggdrasil"}
 incidents:=[]Incident{}
 for _,lane:=range lanes{
  for _,o:=range observations{
   if o.Lane!=lane{continue}
   r,err:=Assess(now,o);if err!=nil{return nil,err}
   if r.Action==Healthy{continue}
   incidents=append(incidents,Incident{Lane:lane,OriginalExperimentID:o.OriginalExperimentID,
    JournalHeadSHA256:o.JournalHeadSHA256,OwnerEpoch:o.OwnerEpoch,
    Action:r.Action,FirstUseRisk:o.FirstUseRisk})
  }
 }
 return incidents,nil
}
