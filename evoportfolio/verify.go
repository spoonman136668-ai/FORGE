package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)
// Receipt is immutable evidence metadata; authenticated bytes must come from a
// separately trusted storage reader. No controller or scientific authority.
type Receipt struct{
 CandidateID string `json:"candidate_id"`
 SourceSHA string `json:"source_sha"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 Outcome string `json:"outcome"`
 Body []byte `json:"body"`
}
func VerifyCheckpointEvidence(f Frozen,pin string,h Handoff,cp Checkpoint,receipts []Receipt)error{
 if Digest(f)!=pin||h.FrozenSHA256!=pin||cp.HandoffDecisionSHA256!=h.DecisionSHA256||
  cp.DispatchAuthorized||len(cp.Completions)!=len(receipts){return ErrFrozen}
 expected,err:=BuildHandoff(f,pin)
 if err!=nil||expected.DecisionSHA256!=h.DecisionSHA256{return ErrFrozen}
 if len(expected.OrderedFinalistIDs)!=len(h.OrderedFinalistIDs){return ErrFrozen}
 for i,id:=range expected.OrderedFinalistIDs{if h.OrderedFinalistIDs[i]!=id{return ErrFrozen}}
 var prior Checkpoint
 for i,receipt:=range receipts{
  c:=cp.Completions[i]
  if receipt.CandidateID!=c.CandidateID||receipt.SourceSHA!=c.SourceSHA||
   receipt.EvidenceSHA256!=c.EvidenceSHA256||receipt.Outcome!=c.Outcome||
   len(receipt.Body)==0||len(receipt.Body)>1048576{return ErrFrozen}
  sum:=sha256.Sum256(receipt.Body)
  if hex.EncodeToString(sum[:])!=c.EvidenceSHA256{return ErrFrozen}
  var raw struct{
   CandidateID string `json:"candidate_id"`
   SourceSHA string `json:"source_sha"`
   Outcome string `json:"outcome"`
  }
  if json.Unmarshal(receipt.Body,&raw)!=nil||raw.CandidateID!=c.CandidateID||
   raw.SourceSHA!=c.SourceSHA||raw.Outcome!=c.Outcome{return ErrFrozen}
  next,err:=AdvanceCheckpoint(h,prior,c)
  if err!=nil{return err}
  if i==len(receipts)-1&&next.DigestSHA256!=cp.DigestSHA256{return ErrFrozen}
  prior=next
 }
 if len(receipts)==0{return errors.New("FORGE_EVIDENCE_EMPTY")}
 return nil
}
