package evoportfolio

import "errors"

// AuditSourceBinding proves completion metadata matches the exact frozen
// candidate source identities, even when the supplied evidence body hashes.
func AuditSourceBinding(f Frozen,pin string,h Handoff,checkpoints []Checkpoint,receipts []Receipt)error{
 if err:=RecoveryAudit(f,pin,h,checkpoints,receipts);err!=nil{return err}
 byID:=make(map[string]Candidate,len(f.Candidates))
 for _,c:=range f.Candidates{
  if _,duplicate:=byID[c.ID];duplicate{return ErrFrozen}
  byID[c.ID]=c
 }
 for i,r:=range receipts{
  c,ok:=byID[r.CandidateID]
  if !ok||c.SourceSHA!=r.SourceSHA||
   checkpoints[i].Completions[i].SourceSHA!=c.SourceSHA{
   return errors.New("FORGE_RECOVERY_SOURCE_NOT_FROZEN_CANDIDATE")
  }
  if c.HistoricalClass=="INVALID"||c.HistoricalClass=="CONSUMED_INDETERMINATE"{
   return errors.New("FORGE_RECOVERY_UNADMITTED_CANDIDATE")
  }
 }
 return nil
}
