package evoportfolio

import "errors"

// RecoveryAudit re-verifies the full append-only checkpoint prefix against
// independently supplied evidence bodies. It does not certify their origin.
func RecoveryAudit(f Frozen,pin string,h Handoff,checkpoints []Checkpoint,receipts []Receipt)error {
 if len(checkpoints)==0||len(checkpoints)>5||len(receipts)!=len(checkpoints) {
  return errors.New("FORGE_RECOVERY_INCOMPLETE_PREFIX")
 }
 for i,cp:=range checkpoints {
  if len(cp.Completions)!=i+1 {
   return errors.New("FORGE_RECOVERY_NONCONTIGUOUS")
  }
  if i>0&&cp.PriorCheckpointSHA256!=checkpoints[i-1].DigestSHA256 {
   return errors.New("FORGE_RECOVERY_BROKEN_LINK")
  }
  if err:=VerifyCheckpointEvidence(f,pin,h,cp,receipts[:i+1]);err!=nil{return err}
 }
 return nil
}
